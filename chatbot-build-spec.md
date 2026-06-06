# Chatbot AI — Spec build các service còn lại

Tài liệu spec để xây dựng các service còn lại của hệ thống Chatbot AI (Telegram + RAG + Function Calling). Dùng làm đầu vào cho coding agent.

## 0. Bối cảnh & trạng thái

Hệ thống microservices, chạy bằng Docker. **Đã xong:** `chatbot-api` (Python/FastAPI + LangChain) kết nối LLM và trả lời truy vấn cơ bản.

**Cần build:** chat history (MongoDB), RAG pipeline (vector-db), `client-server` (API nghiệp vụ giả lập), Function Calling, `web-admin`, và đóng gói `docker-compose`.

### Stack đã chốt

| Thành phần | Công nghệ |
|---|---|
| chatbot-api | Python / FastAPI + LangChain (mở rộng từ bản hiện có) |
| client-server | Python / FastAPI, dữ liệu mẫu (SQLite hoặc in-memory) |
| web-admin | React  |
| vector-db | FAISS  |
| nosql-db | MongoDB — lịch sử hội thoại, metadata tài liệu, cấu hình |

### Thứ tự build

`client-server` → chat history (Mongo) → RAG (Qdrant) → Function Calling → `web-admin` → `docker-compose`.

---

## 1. client-server — API nghiệp vụ giả lập

Project FastAPI độc lập. Seed sẵn dữ liệu mẫu cho 2 lĩnh vực **Spa** và **Du lịch** (sản phẩm, dịch vụ spa, tour). Xác thực mọi request bằng header `X-API-Key`.

### Endpoints

```
GET  /products                  -> [{id, name, price, stock}]
GET  /products/{id}/stock       -> {product_id, name, stock, price}
POST /orders                    -> tạo đơn
GET  /orders/{id}               -> trạng thái đơn
POST /bookings                  -> đặt lịch spa / đặt tour
```

### Request/Response chính

```jsonc
// POST /orders
// body:
{ "items": [{"product_id": "p001", "qty": 2}],
  "customer": {"name": "...", "phone": "...", "address": "..."} }
// 201:
{ "order_id": "ORD-0001", "status": "confirmed", "total": 500000 }

// GET /orders/{id} -> 200:
{ "order_id": "ORD-0001", "status": "shipping",
  "items": [...], "total": 500000, "created_at": "..." }

// POST /bookings
// body:
{ "type": "spa",                 // "spa" | "tour"
  "service_id": "s01", "datetime": "2026-06-10T14:00",
  "people": 1,
  "customer": {"name": "...", "phone": "..."} }
// 201:
{ "booking_id": "BK-0001", "status": "confirmed", "datetime": "..." }
```

Lỗi trả mã HTTP chuẩn (400 thiếu field, 404 không tìm thấy, 409 hết hàng) kèm `{"error": "..."}`.

---

## 2. Chat history (MongoDB) — trong chatbot-api

Chatbot đọc lịch sử trước khi gọi LLM, ghi lại sau khi trả lời. Dùng để duy trì ngữ cảnh trong cùng session (Telegram `user_id`).

### Collections

```jsonc
conversations: { _id, session_id, domain, created_at, last_active }
messages:      { _id, session_id, role,        // "user" | "assistant" | "tool"
                 content, tool_name?, created_at }
documents:     { _id, filename, status,        // "processing" | "done" | "failed"
                 chunk_count, uploaded_at }
configs:       { _id,                            // "spa" | "travel"
                 system_prompt, updated_at }
```

### Quy tắc ngữ cảnh

- Build context = lấy các `messages` cùng `session_id` mà `created_at` nằm trong cửa sổ `CONTEXT_TIMEOUT_MIN` (mặc định 30 phút) tính từ hiện tại; nếu quá hạn → coi như phiên mới.
- **Không** dùng TTL index để xóa dữ liệu (admin còn cần xem lại lịch sử). Chỉ lọc theo thời gian khi dựng ngữ cảnh.
- Connector dùng `motor` (async) cho hợp FastAPI; kết nối có retry lúc khởi động.

---

## 3. RAG pipeline (FAISS) — trong chatbot-api

### Ingest (khi admin upload file)

1. Trích text từ PDF / DOCX / TXT.
2. Chunk ~500–1000 ký tự, overlap ~100.
3. Embedding (model qua env, mặc định OpenAI `text-embedding-3-small`).
4. Upsert vào Qdrant với payload metadata `{filename, chunk_index}`.
5. Cập nhật `documents.status`: `processing` → `done` (hoặc `failed`).

Xử lý bất đồng bộ; file ≤ 5MB phải xong ≤ 30 giây (NFR-01).

### Query (khi user hỏi)

Embedding câu hỏi → search top-k (mặc định k=4) → ghép các đoạn vào prompt cho LLM. Trả kèm nguồn (`filename`) khi có thể.

---

## 4. Function Calling — trong chatbot-api

### Phân loại ý định

Trước khi trả lời: phân loại câu hỏi → **thông tin** (đi RAG) hoặc **nghiệp vụ** (đi Function Calling).

### Tool schema (LLM)

Mỗi tool gọi tới endpoint tương ứng của `client-server`:

| Tool | Tham số | Gọi tới |
|---|---|---|
| `check_stock` | `product_name` hoặc `product_id` | `GET /products/{id}/stock` |
| `create_order` | `items[]`, `customer{name,phone,address}` | `POST /orders` |
| `get_order_status` | `order_id` | `GET /orders/{id}` |
| `create_booking` | `type`, `service_id`, `datetime`, `people`, `customer{name,phone}` | `POST /bookings` |

### Luồng

1. Nếu thiếu tham số bắt buộc → bot hỏi lại qua nhiều lượt (dựa vào chat history) cho đến khi đủ.
2. Gọi REST tới `client-server` (kèm `X-API-Key`).
3. Bắt lỗi (timeout / 5xx / 4xx) → phản hồi tự nhiên, không lộ stack trace.
4. LLM diễn đạt lại kết quả bằng ngôn ngữ tự nhiên (kèm mã đơn / mã booking).

---

## 5. web-admin (React / Next.js)

Gọi các **admin endpoint** trên `chatbot-api` (không truy cập DB trực tiếp).

### Trang

- Đăng nhập (JWT).
- Upload knowledge base (PDF/DOCX/TXT, ≤ 20MB) + danh sách file kèm trạng thái embedding.
- Cấu hình System Prompt theo lĩnh vực (Spa / Du lịch).
- Xem lịch sử hội thoại (phân trang).
- Dashboard thống kê: tổng hội thoại, câu hỏi/ngày, tỷ lệ chuyển đổi. *(biểu đồ + export CSV: ưu tiên thấp)*

### Admin endpoints (thêm vào chatbot-api)

```
POST   /admin/login                 -> {token}
POST   /admin/documents             (multipart) -> ingest + trả document_id
GET    /admin/documents             -> [{id, filename, status, ...}]
DELETE /admin/documents/{id}
GET    /admin/config/prompt?domain= -> {system_prompt}
PUT    /admin/config/prompt         -> cập nhật prompt theo domain
GET    /admin/conversations?page=   -> lịch sử hội thoại (phân trang)
GET    /admin/stats                 -> {total_conversations, qa_per_day, conversion_rate}
```

Mọi `/admin/*` (trừ login) yêu cầu JWT. Session timeout 60 phút.

---

## 6. docker-compose — orchestration

5 service: `chatbot-api`, `client-server`, `web-admin`, `mongo`, `qdrant`.

- Mỗi service một `Dockerfile`; `mongo` và `qdrant` dùng image chính thức + named volume (để không mất dữ liệu).
- Các service gọi nhau qua tên service trên mạng nội bộ Docker; chỉ expose port thật sự cần.
- `restart: unless-stopped` cho mọi service.
- `chatbot-api` retry khi kết nối Mongo/Qdrant lúc khởi động.
- Mục tiêu: `docker-compose up -d` là cả stack chạy.

### Biến môi trường (.env)

```
TELEGRAM_BOT_TOKEN=
LLM_API_KEY=
LLM_MODEL=
EMBEDDING_MODEL=text-embedding-3-small
MONGO_URI=mongodb://mongo:27017/chatbot
QDRANT_URL=http://qdrant:6333
CLIENT_SERVER_URL=http://client-server:8001
INTERNAL_API_KEY=            # X-API-Key giữa chatbot-api <-> client-server
JWT_SECRET=
ADMIN_USER=
ADMIN_PASSWORD=
CONTEXT_TIMEOUT_MIN=30
```

Kèm `.env.example` (không commit `.env` thật).

---

## 7. Tiêu chí nghiệm thu

- **AC-01:** hỏi giờ mở cửa / chính sách → trả đúng nội dung file đã upload, ≤ 5 giây.
- **AC-02:** "mua 2 sản phẩm X" → bot hỏi đủ thông tin → `POST /orders` → xác nhận kèm mã đơn.
- **AC-03:** admin upload PDF → trạng thái `processing` → `done`; chatbot trả lời được nội dung file trong ~2 phút.
- **AC-04:** nhớ ngữ cảnh trong session ("cái đó" hiểu là sản phẩm đã nhắc); reset sau 30 phút không hoạt động.
- **AC-05:** `docker-compose up -d` khởi động toàn bộ; chatbot phản hồi Telegram sau khi deploy.
