# SC Chatbot — Trợ lý AI cho Thương mại Xã hội

Nền tảng chatbot **multi-tenant** cho SME bán hàng online, xây theo SRS [`SC-Chatbot-SRS.docx`](SC-Chatbot-SRS.docx).
Bot tư vấn sản phẩm/dịch vụ, trả lời FAQ dựa trên tri thức riêng của từng shop (RAG), xử lý đơn hàng & đặt lịch, và có trang quản trị để theo dõi KPI.

Phần Zalo OA trong SRS được thay bằng **HTTP API + UI chat web + bot Telegram** để demo/test trực tiếp.

---

## 1. Kiến trúc tổng quan

Hệ thống gồm **3 service độc lập** trong thư mục [`services/`](services/):

```
                    ┌─────────────────┐
   Telegram  ─────► │                 │
   Web chat UI ───► │   chatbot-api   │ ──(REST + X-API-Key)──► client-server
   (port 8000)      │   (FastAPI)     │                         (port 8001)
                    │   LLM + RAG     │                         products / orders
   web-admin ─────► │                 │                         bookings (mock API)
   (port 5173)      └─────────────────┘
```

| Service | Vai trò | Stack | Port |
|---|---|---|---|
| [**chatbot-api**](services/chatbot-api/) | Bộ não AI: LLM agent, RAG, tools, lịch sử hội thoại, admin API, Telegram worker | Python · FastAPI · LangChain · FAISS · HuggingFace embeddings | 8000 |
| [**client-server**](services/client-server/) | API nghiệp vụ giả lập (sản phẩm/đơn/booking), bảo vệ bằng API key | Python · FastAPI | 8001 |
| [**web-admin**](services/web-admin/) | Trang quản trị: dashboard KPI, knowledge base, system prompt, hội thoại | React · Vite · TypeScript · Tailwind | 5173 |

---

## 2. Công nghệ chính

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ backend | Python 3.10+ (test trên 3.11) |
| LLM orchestration | LangChain (`create_agent` / LangGraph) |
| LLM | Azure OpenAI (mặc định) hoặc OpenAI / OpenAI-compatible (Ollama, vLLM…) |
| Embeddings | HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` (local, offline) — hỗ trợ tiếng Việt |
| Vector DB | FAISS — mỗi tenant 1 index |
| Lưu hội thoại | TinyDB (JSON local, mặc định) **hoặc** MongoDB — switch bằng `STORAGE_BACKEND` |
| Web framework | FastAPI + uvicorn |
| Kênh giao tiếp | Web chat UI (`/`) · Telegram (polling) |
| Frontend admin | React + Vite + TypeScript + Tailwind |

---

## 3. Cấu trúc thư mục

```
sc-chatbot/
├── start.sh                 # khởi động toàn bộ stack (tự cài deps + seed lần đầu)
├── stop.sh                  # dừng toàn bộ stack
├── README.md                # file này
├── RUN.md                   # hướng dẫn chạy chi tiết từng bước
├── chatbot-build-spec.md
├── SC-Chatbot-SRS.docx
│
└── services/
    ├── chatbot-api/         # === Bộ não AI ===
    │   ├── run.py                  # entry point HTTP server (port 8000)
    │   ├── telegram_worker.py      # worker polling Telegram
    │   ├── seed_data.py            # seed tenant demo + prompt + knowledge base
    │   ├── migrate_history_to_mongo.py
    │   ├── app/
    │   │   ├── config.py           # đọc .env
    │   │   ├── tenancy.py          # multi-tenant context
    │   │   ├── core/
    │   │   │   ├── llm.py          # factory Azure / OpenAI / HF
    │   │   │   ├── agent.py        # LangChain agent + RAG
    │   │   │   ├── memory.py       # lịch sử hội thoại
    │   │   │   ├── mongo.py        # kết nối MongoDB (khi STORAGE_BACKEND=mongo)
    │   │   │   └── analytics.py    # tracking KPI
    │   │   ├── knowledge/
    │   │   │   ├── vectorstore.py  # FAISS wrapper per-tenant
    │   │   │   └── ingest.py       # crawl URL / load file / chunk
    │   │   ├── tools/              # Function Calling
    │   │   │   ├── faq.py          # search_knowledge_base
    │   │   │   ├── product.py      # get / search / suggest products
    │   │   │   ├── order.py        # check_stock / create_order / lookup
    │   │   │   └── booking.py      # check_tour_availability / create_booking
    │   │   ├── integrations/
    │   │   │   ├── client_server.py # gọi REST sang client-server
    │   │   │   └── telegram_bot.py  # handler Telegram
    │   │   ├── admin/              # API cho web-admin
    │   │   │   ├── auth.py         # login JWT
    │   │   │   ├── routes.py       # /admin/* endpoints
    │   │   │   ├── documents.py    # upload/quản lý tài liệu KB
    │   │   │   ├── configs.py      # override system prompt theo tenant
    │   │   │   └── aggregations.py # số liệu dashboard
    │   │   └── api/
    │   │       ├── schemas.py      # Pydantic models
    │   │       └── server.py       # FastAPI routes chính
    │   ├── ui/index.html           # chat UI demo
    │   ├── seed/                   # dữ liệu mẫu (beauty / travel)
    │   └── data/                   # runtime — tự tạo, mỗi tenant 1 folder (gitignored)
    │
    ├── client-server/       # === API nghiệp vụ (mock) ===
    │   ├── run.py                  # entry point (port 8001)
    │   ├── seed_data.py
    │   ├── app/
    │   │   ├── main.py             # FastAPI app
    │   │   ├── auth.py             # check header X-API-Key
    │   │   ├── storage.py          # in-memory store
    │   │   ├── schemas.py
    │   │   └── routes/             # products / orders / bookings
    │   └── seed/                   # products.json / spa.json / travel.json
    │
    └── web-admin/           # === Trang quản trị (React) ===
        ├── src/
        │   ├── api.ts              # gọi chatbot-api /admin/*
        │   ├── auth.tsx            # context đăng nhập JWT
        │   ├── pages/              # Login / Stats / Documents / Prompt / Conversations
        │   └── components/         # Layout / Protected / TenantSelector / Icons
        ├── package.json
        └── vite.config.ts
```

---

## 4. Chức năng theo service

### 4.1. chatbot-api — Bộ não AI

- **Multi-tenant**: mỗi shop (tenant) có vector index, lịch sử, system prompt riêng — cách ly bởi [`app/tenancy.py`](services/chatbot-api/app/tenancy.py).
- **LLM Agent + Function Calling**: agent tự quyết định gọi tool nào dựa trên câu hỏi ([`app/core/agent.py`](services/chatbot-api/app/core/agent.py)):
  - `search_knowledge_base` — RAG, tìm trong tri thức của tenant
  - `get_product` / `search_products` / `suggest_products` — tra cứu & gợi ý sản phẩm
  - `check_stock` / `create_order` / `lookup_order` — xử lý đơn hàng
  - `check_tour_availability` / `create_booking` — đặt lịch/tour
- **RAG**: nạp tri thức từ text / URL / folder, chunk + embed (HuggingFace) rồi index vào FAISS ([`app/knowledge/`](services/chatbot-api/app/knowledge/)).
- **Lịch sử hội thoại**: nhớ ngữ cảnh theo `session_id`, lưu TinyDB hoặc MongoDB ([`app/core/memory.py`](services/chatbot-api/app/core/memory.py)).
- **Kênh giao tiếp**: chat UI web tại `/`, và bot Telegram chạy nền qua [`telegram_worker.py`](services/chatbot-api/telegram_worker.py).
- **Admin API** (`/admin/*`): login JWT, upload/xoá tài liệu KB, override system prompt, thống kê — phục vụ web-admin.
- **Analytics/KPI**: track message, FAQ hit, đơn, booking, CSAT, latency ([`app/core/analytics.py`](services/chatbot-api/app/core/analytics.py)).

### 4.2. client-server — API nghiệp vụ (mock)

- Giả lập backend của shop: `products`, `orders`, `bookings` ([`app/routes/`](services/client-server/app/routes/)).
- Mọi request phải kèm header `X-API-Key` khớp `INTERNAL_API_KEY` ([`app/auth.py`](services/client-server/app/auth.py)) → trả `401` nếu thiếu/sai.
- Dùng in-memory store (restart mất data đơn/booking; seed sản phẩm/dịch vụ tự nạp lại từ JSON).
- Swagger docs: `http://localhost:8001/docs`.

### 4.3. web-admin — Trang quản trị

Đăng nhập bằng `ADMIN_USER` / `ADMIN_PASSWORD` (cấu hình ở `.env` của chatbot-api). Các trang ([`src/pages/`](services/web-admin/src/pages/)):

| Trang | Chức năng |
|---|---|
| **Dashboard / Stats** | Tổng hội thoại, số câu hỏi, conversion rate, latency, biểu đồ Q&A |
| **Knowledge base** | Upload PDF/DOCX/TXT/MD theo tenant, xem trạng thái embedding, xoá doc |
| **System prompt** | Override prompt cho từng tenant (để trống = template mặc định) |
| **Hội thoại** | Phân trang sessions, click để xem toàn bộ message |

---

## 5. Khởi động nhanh

> Yêu cầu: **Python 3.10+**, **Node.js ≥ 18**. Chạy script bằng **Git Bash** (Windows) hoặc terminal (macOS/Linux).

```bash
# Lần đầu: tự tạo .venv, cài pip deps + npm, seed dữ liệu, rồi chạy cả 4 tiến trình
./start.sh

# Dừng tất cả
./stop.sh        # hoặc nhấn Ctrl+C ở terminal đang chạy start.sh
```

Sau khi chạy:
- chatbot-api : http://localhost:8000 (UI chat + `/docs`)
- client-server : http://localhost:8001/docs
- web-admin : http://localhost:5173
- Telegram : worker polling (log ở `logs/telegram-worker.log`)

Cờ bổ sung:
```bash
./start.sh --install   # ép cài lại deps (pip + npm)
./start.sh --seed      # ép seed lại knowledge base
./start.sh -h          # xem help
```

> Cần cấu hình thủ công (Telegram token, key Azure…), chạy MongoDB, hoặc làm từng bước thay vì dùng script → xem **[RUN.md](RUN.md)**.

---

## 6. Cấu hình `.env`

Mỗi service có `.env.example` riêng — copy thành `.env` và điền giá trị:

- [`services/chatbot-api/.env.example`](services/chatbot-api/.env.example) — LLM provider, Azure/OpenAI key, embeddings, Telegram token, admin JWT, `STORAGE_BACKEND`, Mongo URI.
- [`services/client-server/.env.example`](services/client-server/.env.example) — `INTERNAL_API_KEY`, `PORT`.
- [`services/web-admin/.env.example`](services/web-admin/.env.example) — `VITE_API_BASE_URL` (trỏ tới chatbot-api).

> **Bảo mật:** tất cả file `.env` đã nằm trong `.gitignore`, không commit. Sau demo nên Regenerate key Azure trong portal.

---

## 7. API chatbot-api (tham khảo)

| Method | Path | Mô tả |
|---|---|---|
| GET  | `/` | Web UI chat |
| GET  | `/health` | Healthcheck |
| GET  | `/tenants` | List tenant |
| POST | `/tenants` | Tạo tenant `{tenant_id, name, industry}` |
| POST | `/chat` | Chat `{tenant_id, session_id, message}` |
| GET  | `/sessions/{session_id}?tenant_id=...` | Lịch sử hội thoại |
| POST | `/ingest` | Nạp tri thức `{tenant_id, text\|url\|folder, source}` |
| GET  | `/analytics/{tenant_id}` | Báo cáo KPI |
| POST | `/csat` | Khách chấm điểm `{tenant_id, session_id, score}` |
| *    | `/admin/*` | Endpoints cho web-admin (yêu cầu JWT) |

Ví dụ gọi `/chat`:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"demo-beauty","session_id":"s-test-001","message":"Cho tôi xem các serum dưỡng sáng dưới 500k"}'
```

---

## 8. Kịch bản test

### Tenant `demo-beauty` (mỹ phẩm)
| Câu hỏi | Tool bot gọi |
|---|---|
| "Serum Vitamin C có dùng được cho da nhạy cảm không?" | `search_knowledge_base` |
| "Tư vấn sản phẩm cho da dầu mụn" | `suggest_products` |
| "Đặt 1 kem chống nắng giao Hà Nội" | hỏi tên/SĐT/địa chỉ → `check_stock` → `create_order` |
| "Tra cứu đơn ORD-XXXX" | `lookup_order` |

### Tenant `demo-travel` (du lịch)
| Câu hỏi | Tool bot gọi |
|---|---|
| "Tour Đà Nẵng 3N2Đ giá bao nhiêu?" | `search_knowledge_base` / `get_product` |
| "Tour Phú Quốc còn chỗ ngày 2026-06-15 cho 2 người không?" | `check_tour_availability` |
| "Đặt tour đó luôn, tôi tên Nam, SĐT 0901234567" | `create_booking` |

---

## 9. Onboard tenant mới (SME)

```bash
# 1. Tạo tenant
curl -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{"tenant_id":"shop-abc","name":"Shop ABC","industry":"electronics"}'

# 2. Nạp tri thức (chọn 1 trong 3)
curl -X POST http://localhost:8000/ingest -d '{"tenant_id":"shop-abc","url":"https://shop-abc.vn/about"}'
curl -X POST http://localhost:8000/ingest -d '{"tenant_id":"shop-abc","text":"Chính sách bảo hành: ...","source":"warranty.md"}'
curl -X POST http://localhost:8000/ingest -d '{"tenant_id":"shop-abc","folder":"./seed/shop-abc"}'
```

Hoặc dùng trang **Knowledge base** trong web-admin để upload file trực tiếp.

---

## 10. Tuỳ biến LLM

Đổi provider trong `services/chatbot-api/.env`:

```env
# Azure OpenAI (mặc định)
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_CHAT_DEPLOYMENT=...

# OpenAI thẳng
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Local (Ollama / vLLM)
LLM_PROVIDER=openai
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:7b
```

Thêm tool Function Calling mới: tạo `app/tools/your_tool.py` rồi đăng ký trong [`app/tools/__init__.py`](services/chatbot-api/app/tools/__init__.py).

---

## 11. Troubleshooting

| Triệu chứng | Nguyên nhân & fix |
|---|---|
| `DeploymentNotFound 404` | Sai `AZURE_OPENAI_CHAT_DEPLOYMENT`. Check Azure portal → Deployments. |
| Lần đầu chạy treo lâu | Đang tải HF embedding model (~80MB) / load model. Đợi 30–60s. |
| `TELEGRAM_BOT_TOKEN is empty` | Chưa điền token trong `services/chatbot-api/.env`. |
| client-server trả `401` | Thiếu/sai header `X-API-Key` (phải khớp `INTERNAL_API_KEY`). |
| Port bị chiếm | Đổi port: chatbot-api sửa `run.py`; client-server đổi `PORT` trong `.env`. |
| `Tenant 'xxx' is not registered` | Chạy lại `python seed_data.py` trong `services/chatbot-api/`. |

Chi tiết hơn (MongoDB, migrate, từng bước) xem **[RUN.md](RUN.md)**.

---

## 12. Triển khai production (gợi ý theo SRS)

| Layer | Dev (hiện tại) | Production gợi ý |
|---|---|---|
| LLM | Azure OpenAI | Azure OpenAI / AWS Bedrock |
| Vector DB | FAISS local | Qdrant Cloud / OpenSearch |
| NoSQL | TinyDB / MongoDB local | DynamoDB / MongoDB Atlas |
| Embeddings | HF local | Bedrock Titan / Azure embeddings |
| Server | uvicorn 1 worker | uvicorn + gunicorn, ECS Fargate / EKS |
| Storage `data/` | local filesystem | S3 (vector index) + EFS |
| Secrets | `.env` | AWS Secrets Manager |
