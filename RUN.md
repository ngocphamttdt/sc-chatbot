# Hướng dẫn chạy SC Chatbot

Tài liệu này hướng dẫn chạy toàn bộ stack hiện tại: **chatbot-api** (HTTP + Telegram worker), **client-server** (API nghiệp vụ), và **web-admin** (React).

> Yêu cầu: Python 3.10+ đã cài, có `.venv` ở root repo (hoặc tự tạo).

---

## Cấu trúc thư mục

```
sc-chatbot/
├── services/
│   ├── chatbot-api/          # FastAPI + LangChain + Telegram polling + admin endpoints
│   ├── client-server/        # FastAPI mock business (products/orders/bookings)
│   └── web-admin/            # React + Vite admin panel
├── chatbot-build-spec.md
├── README.md
└── RUN.md                    # file này
```

Mỗi service tự chứa `requirements.txt`, `.env.example`, `run.py`. Khởi động độc lập trong từng folder.

---

## Bước 0 — Kích hoạt virtualenv (1 lần / mỗi terminal)

PowerShell:

```powershell
cd c:\code\sc-chatbot
.\.venv\Scripts\Activate.ps1
```

Nếu chưa có `.venv`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

> Tất cả các bước sau **đều** giả định venv đã activate trong terminal đang dùng.

---

## Bước 1 — Cài đặt & cấu hình `chatbot-api`

### 1.1 Cài dependency

```powershell
cd c:\code\sc-chatbot\services\chatbot-api
pip install -r requirements.txt
```

Cài lần đầu sẽ tải `langchain`, `sentence-transformers`, `faiss-cpu`, `python-telegram-bot`... mất vài phút.

### 1.2 Tạo bot Telegram

1. Mở Telegram, chat với **@BotFather**.
2. Gửi `/newbot` → đặt tên bot, đặt username (kết thúc bằng `bot`).
3. BotFather trả về một token dạng `123456789:ABC-DEF...`.

### 1.3 Cấu hình `.env`

File `.env` đã có sẵn trong `services/chatbot-api/.env` (đã được di chuyển từ root cũ). Mở ra và bổ sung 2 dòng cuối:

```dotenv
# --- Telegram bot (polling worker) ---
TELEGRAM_BOT_TOKEN=123456789:ABC-DEF_paste_token_thật_vào_đây
TELEGRAM_DEFAULT_TENANT=demo-beauty
```

Các biến khác (Azure OpenAI / OpenAI) đã có sẵn, giữ nguyên.

> Có thể đổi `TELEGRAM_DEFAULT_TENANT=demo-travel` nếu muốn bot trả lời theo ngành du lịch.

### 1.4 Seed dữ liệu (chỉ chạy 1 lần đầu)

```powershell
python seed_data.py
```

Lệnh này đăng ký 2 tenant `demo-beauty`, `demo-travel`, nạp products + FAQ vào FAISS. Kết quả in ra JSON tóm tắt số chunk đã index.

> Nếu folder `data/` đã có sẵn (đã seed trước đó) thì bỏ qua bước này.

---

## Bước 2 — Cài đặt & cấu hình `client-server`

### 2.1 Cài dependency

```powershell
cd c:\code\sc-chatbot\services\client-server
pip install -r requirements.txt
```

### 2.2 Tạo `.env`

```powershell
copy .env.example .env
```

Mở file `.env` vừa tạo, đổi `INTERNAL_API_KEY` thành chuỗi bất kỳ (sẽ dùng làm header `X-API-Key`):

```dotenv
INTERNAL_API_KEY=dev-key-123
PORT=8001
```

> Lưu lại giá trị này — sau này khi refactor tools chatbot-api gọi sang client-server cần dùng đúng key.

---

## Bước 3 — Chạy stack (3 terminal)

Mở **3 cửa sổ PowerShell**, activate venv ở từng terminal (Bước 0).

### Terminal 1 — chatbot-api HTTP (port 8000)

```powershell
cd c:\code\sc-chatbot\services\chatbot-api
python run.py
```

Log thấy:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2 — Telegram worker (polling)

```powershell
cd c:\code\sc-chatbot\services\chatbot-api
python telegram_worker.py
```

Log thấy:
```
INFO ... Starting Telegram bot (polling) for tenant=demo-beauty
INFO ... Application started
```

### Terminal 3 — client-server (port 8001)

```powershell
cd c:\code\sc-chatbot\services\client-server
python run.py
```

Log thấy:
```
INFO:     Uvicorn running on http://0.0.0.0:8001
```

---

## Bước 4 — Kiểm tra

### 4.1 chatbot-api HTTP

Mở browser: `http://localhost:8000/` → thấy demo chat UI.

Hoặc curl:
```powershell
Invoke-RestMethod http://localhost:8000/health
# -> { "status": "ok" }
```

### 4.2 Telegram bot

1. Mở Telegram, tìm bot bằng username vừa tạo.
2. Gửi `/start` → bot trả lời chào theo tên tenant.
3. Gửi: `Spa có dịch vụ gì?` → bot dùng FAQ/products trả lời.
4. Gửi tiếp: `cái đó giá bao nhiêu?` → bot vẫn nhớ ngữ cảnh (cùng session `tg-{user_id}`).

### 4.3 client-server

```powershell
$h = @{ "X-API-Key" = "dev-key-123" }

# Không kèm API key → 401
Invoke-RestMethod http://localhost:8001/products
# -> WebRequestException: 401

# Có API key
Invoke-RestMethod http://localhost:8001/products -Headers $h
# -> danh sách 4 sản phẩm beauty

Invoke-RestMethod http://localhost:8001/products/p001/stock -Headers $h
# -> { "product_id": "p001", "name": "Serum Vitamin C 20ml", "stock": 25, ... }

# Tạo đơn
$body = '{"items":[{"product_id":"p001","qty":2}],"customer":{"name":"A","phone":"0901","address":"HN"}}'
Invoke-RestMethod -Method Post http://localhost:8001/orders `
  -Headers $h -ContentType "application/json" -Body $body
# -> { "order_id": "ORD-0001", "status": "confirmed", "total": 960000 }

# Đặt spa
$book = '{"type":"spa","service_id":"s01","datetime":"2026-06-10T14:00","people":1,"customer":{"name":"A","phone":"0901"}}'
Invoke-RestMethod -Method Post http://localhost:8001/bookings `
  -Headers $h -ContentType "application/json" -Body $book
# -> { "booking_id": "BK-0001", "status": "confirmed", "datetime": "2026-06-10T14:00" }
```

Swagger docs có sẵn: `http://localhost:8001/docs`.

---

## Lệnh tham khảo nhanh

| Mục đích | Lệnh |
|---|---|
| HTTP chatbot-api | `cd services\chatbot-api; python run.py` |
| Telegram worker | `cd services\chatbot-api; python telegram_worker.py` |
| client-server | `cd services\client-server; python run.py` |
| web-admin (dev) | `cd services\web-admin; npm run dev` |
| Seed lại knowledge | `cd services\chatbot-api; python seed_data.py` |
| Xem Swagger client-server | `http://localhost:8001/docs` |
| Demo chat UI | `http://localhost:8000/` |
| Web admin | `http://localhost:5173/` |

---

## Bước 5 — Web admin (React)

### 5.1 Bổ sung biến môi trường cho admin (chatbot-api)

Trong `services/chatbot-api/.env`, thêm:

```dotenv
JWT_SECRET=mot-chuoi-ngau-nhien-dai
ADMIN_USER=admin
ADMIN_PASSWORD=admin123
JWT_EXPIRES_MIN=60
```

> Đổi `ADMIN_PASSWORD` thành mật khẩu khác trước khi deploy. JWT_SECRET nên là chuỗi random ≥ 32 ký tự.

Cài thêm deps mới (PyJWT, bcrypt, pypdf, docx2txt, python-multipart):

```powershell
cd c:\code\sc-chatbot\services\chatbot-api
pip install -r requirements.txt
```

Restart `python run.py` để load admin router (`/admin/*` endpoints xuất hiện trong Swagger `http://localhost:8000/docs`).

### 5.2 Cài Node.js (nếu chưa có)

Yêu cầu Node.js ≥ 18. Tải tại https://nodejs.org/.

### 5.3 Cài deps web-admin

```powershell
cd c:\code\sc-chatbot\services\web-admin
copy .env.example .env
npm install
```

Mặc định `.env` đã trỏ tới `VITE_API_BASE_URL=http://localhost:8000` (chatbot-api). Đổi nếu chatbot-api chạy port khác.

### 5.4 Chạy dev server (terminal thứ 4)

```powershell
npm run dev
```

Mở browser: **http://localhost:5173/**

Đăng nhập bằng `ADMIN_USER` / `ADMIN_PASSWORD` trong `.env`.

### 5.5 Các trang

| Trang | Chức năng |
|---|---|
| **Dashboard** | Tổng hội thoại, số câu hỏi, conversion rate, latency, biểu đồ Q&A 7 ngày |
| **Knowledge base** | Upload PDF/DOCX/TXT/MD theo tenant, xem trạng thái embedding (`processing` → `done` / `failed`), xoá doc |
| **System prompt** | Override prompt cho từng tenant. Để trống = dùng template mặc định |
| **Hội thoại** | Phân trang sessions, click vào để xem toàn bộ message của session |

### 5.6 Build production (tùy chọn)

```powershell
npm run build
```

Output ở `services/web-admin/dist/` — serve bằng `nginx` / static host bất kỳ.

---

## Troubleshooting

### `TELEGRAM_BOT_TOKEN is empty`
Bot worker raise lỗi này khi token trong `.env` rỗng. Check:
1. File `services/chatbot-api/.env` có dòng `TELEGRAM_BOT_TOKEN=...` không.
2. Terminal đang chạy từ đúng folder `services/chatbot-api` (vì `.env` load tương đối CWD).

### Bot không trả lời
- Kiểm tra terminal Telegram worker còn live không, có log `Application started` chưa.
- Bot chỉ trả lời `text` message. Sticker / ảnh hiện chưa xử lý.
- Lần đầu sentence-transformers load model có thể mất 30–60 giây — đợi log `message_in` xuất hiện rồi mới gửi tiếp.

### client-server trả 401
Thiếu hoặc sai header `X-API-Key`. Phải khớp giá trị `INTERNAL_API_KEY` trong `services/client-server/.env`.

### Port đã bị chiếm
Đổi port:
- chatbot-api: sửa `port=8000` trong `services/chatbot-api/run.py`.
- client-server: đổi `PORT=8002` trong `.env`.

### Tenant không tồn tại
Lỗi `KeyError: Tenant 'xxx' is not registered` → chạy lại `python seed_data.py` trong `services/chatbot-api/`.

---

## Ghi chú về kiến trúc hiện tại

- **chatbot-api** đang dùng **TinyDB** (file JSON local) cho chat history, **FAISS** cho RAG. MongoDB / Qdrant theo spec sẽ migrate ở iteration sau.
- **client-server** dùng in-memory store. Restart sẽ mất data đơn / booking. Seed (products / spa / tours) tự nạp lại từ JSON.
- Tools trong chatbot-api (`product`, `order`, `booking`) hiện vẫn gọi TinyDB local — **chưa** gọi REST sang client-server. Đó là step tiếp theo.

---

## Bước 6 — Chat history: TinyDB hoặc MongoDB

Chat history hỗ trợ **2 backend**, switch bằng env `STORAGE_BACKEND`:

```dotenv
# Default — không cần cài gì thêm, dùng JSON file local
STORAGE_BACKEND=tinydb

# Hoặc, sau khi setup MongoDB:
STORAGE_BACKEND=mongo
MONGO_URI=mongodb://localhost:27017/scchatbot
```

> Toàn bộ chatbot-api hoạt động bình thường với `tinydb` (default) — bạn có thể bỏ qua Bước 6 nếu chưa cần MongoDB.

Phần dưới đây chỉ áp dụng khi **chuyển sang MongoDB**.

### 6.1 Chạy MongoDB local (Docker — nhanh nhất)

Yêu cầu Docker Desktop đã cài.

```powershell
docker run -d --name sc-mongo -p 27017:27017 -v sc-mongo-data:/data/db mongo:7
```

- Container tên `sc-mongo`, port `27017`, data persist trong named volume `sc-mongo-data`.
- Bật/tắt lại sau này: `docker start sc-mongo` / `docker stop sc-mongo`.
- Không có Docker → tải MongoDB Community từ mongodb.com hoặc dùng MongoDB Atlas (cloud, free tier).

### 6.2 Cài driver

```powershell
cd c:\code\sc-chatbot\services\chatbot-api
pip install -r requirements.txt
```

Cài thêm `pymongo>=4.7`.

### 6.3 Cấu hình `.env`

Thêm vào `services/chatbot-api/.env`:

```dotenv
MONGO_URI=mongodb://localhost:27017/scchatbot
```

Đổi host/port nếu Mongo chạy chỗ khác. Atlas có dạng `mongodb+srv://user:pass@cluster.xxxxx.mongodb.net/scchatbot`.

### 6.4 (Tuỳ chọn) Migrate dữ liệu TinyDB cũ sang Mongo

Nếu trước đó đã chat qua Telegram và muốn giữ lịch sử:

```powershell
python migrate_history_to_mongo.py
```

Output JSON tóm tắt: `found / inserted / skipped / sessions` cho mỗi tenant. Idempotent — chạy nhiều lần cũng OK.

### 6.5 Restart chatbot-api + verify

```powershell
# Ctrl+C terminal run.py rồi:
python run.py
```

Mở web-admin → trang **Hội thoại** → vẫn thấy danh sách (nay từ Mongo). Gửi tin nhắn mới qua Telegram → record mới xuất hiện trong collection `messages`.

Kiểm tra trực tiếp bằng Mongo shell:
```powershell
docker exec -it sc-mongo mongosh scchatbot
> db.messages.countDocuments()
> db.messages.find().sort({ts:-1}).limit(3)
> db.conversations.find()
```

---

## Các phần chưa build (so với spec)

- Refactor `create_order` + `lookup_order` + `create_booking` để gọi sang client-server (hiện chỉ `check_stock` đã wire).
- Migrate analytics + documents + configs sang MongoDB (chỉ chat history đã migrate).
- `docker-compose.yml` orchestration.
- Xoá document chưa xoá được chunks tương ứng trong FAISS (chỉ xoá metadata + file).
