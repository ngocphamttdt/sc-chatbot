# SC Chatbot — Trợ lý AI cho Thương mại Xã hội

Multi-tenant chatbot SaaS theo SRS [`SC-Chatbot-SRS.docx`](SC-Chatbot-SRS.docx).
Đã **bỏ phần Zalo OA**, thay bằng HTTP API + web UI để demo/test trực tiếp.

---

## 1. Tổng quan

| Thành phần | Công nghệ |
|---|---|
| Ngôn ngữ | Python 3.11 |
| LLM orchestration | LangChain 1.2 (`create_agent` / LangGraph) |
| LLM | Azure OpenAI — deployment `gpt-4` (model `gpt-4.1`) |
| Embeddings | HuggingFace `paraphrase-multilingual-MiniLM-L12-v2` (local, offline) |
| Vector DB | FAISS (mỗi tenant 1 index) |
| NoSQL | TinyDB (JSON-backed) cho hội thoại, đơn hàng, booking, analytics |
| Web framework | FastAPI + uvicorn |
| UI demo | HTML/JS single-page tại `/` |

---

## 2. Cấu trúc thư mục

```
sc-chatbot/
├── .env                  # secrets (KHÔNG commit)
├── .env.example          # template
├── requirements.txt
├── run.py                # entry point
├── seed_data.py          # nạp tenant demo
│
├── app/
│   ├── config.py         # đọc env
│   ├── tenancy.py        # multi-tenant context
│   │
│   ├── core/
│   │   ├── llm.py        # Azure / OpenAI / HF factory
│   │   ├── agent.py      # LangChain agent + RAG
│   │   ├── memory.py     # lịch sử hội thoại (TinyDB)
│   │   └── analytics.py  # KPI tracking
│   │
│   ├── knowledge/
│   │   ├── vectorstore.py  # FAISS wrapper per-tenant
│   │   └── ingest.py       # crawl URL / load file / chunk
│   │
│   ├── tools/            # Function Calling
│   │   ├── faq.py        # search_knowledge_base
│   │   ├── product.py    # get / search / suggest
│   │   ├── order.py      # check_stock / create_order / lookup
│   │   └── booking.py    # check_tour_availability / create_booking
│   │
│   └── api/
│       ├── schemas.py    # Pydantic models
│       └── server.py     # FastAPI routes
│
├── ui/index.html         # chat UI
├── seed/                 # dữ liệu mẫu
│   ├── beauty/{products.json, faq.md}
│   └── travel/{products.json, faq.md}
└── data/                 # runtime — tự tạo, mỗi tenant 1 folder
```

---

## 3. Cài đặt

### 3.1. Yêu cầu
- Python 3.10+ (đã test trên 3.11)
- Windows / macOS / Linux
- ~500MB ổ cứng (gồm FAISS + HF embedding model)
- Internet (lần đầu để tải HF model + gọi Azure OpenAI)

### 3.2. Cài dependencies
```powershell
pip install -r requirements.txt
```

### 3.3. Cấu hình `.env`
Đã có sẵn `.env` cho Azure OpenAI:
```env
LLM_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://np-chatbot.openai.azure.com/
AZURE_OPENAI_API_KEY=<your-key>
AZURE_OPENAI_API_VERSION=2024-10-21
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-4
LLM_TEMPERATURE=0.2

EMBEDDING_PROVIDER=huggingface
HF_EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

DATA_DIR=./data
DEFAULT_TENANT=demo-beauty
```

> **Bảo mật:** key Azure trong `.env` đã liệt vào `.gitignore`. Sau demo nên Regenerate Key trong Azure portal.

---

## 4. Khởi động

### Bước 1 — Seed dữ liệu demo *(chỉ chạy 1 lần)*
```powershell
python seed_data.py
```

Output mong đợi:
```json
[
  {"tenant_id": "demo-beauty", "products": 4, "kb_chunks": 9},
  {"tenant_id": "demo-travel", "products": 3, "kb_chunks": 7}
]
```

> Lần đầu sẽ tải model HuggingFace (~80MB). Lần sau cache lại, chạy nhanh.

### Bước 2 — Chạy server
```powershell
python run.py
```

Mở browser: **http://localhost:8000**

UI có:
- Dropdown chọn tenant
- Khung chat
- Nút CSAT 1–5⭐

---

## 5. Kịch bản test

### Tenant `demo-beauty` (mỹ phẩm)

| Câu hỏi | Tool bot sẽ gọi |
|---|---|
| "Serum Vitamin C có dùng được cho da nhạy cảm không?" | `search_knowledge_base` |
| "Tư vấn sản phẩm cho da dầu mụn" | `suggest_products` |
| "Cho mình thông tin sản phẩm BTY-SR01" | `get_product` |
| "Đặt 1 kem chống nắng giao Hà Nội" | hỏi tên / SĐT / địa chỉ → `check_stock` → `create_order` |
| "Tra cứu đơn ORD-XXXXXXXX" | `lookup_order` |

### Tenant `demo-travel` (du lịch)

| Câu hỏi | Tool bot sẽ gọi |
|---|---|
| "Tour Đà Nẵng 3N2Đ giá bao nhiêu?" | `search_knowledge_base` / `get_product` |
| "Tour Phú Quốc còn chỗ ngày 2026-06-15 cho 2 người không?" | `check_tour_availability` |
| "Đặt tour đó luôn, tôi tên Nam, SĐT 0901234567" | `create_booking` |
| "Chính sách hoàn hủy tour?" | `search_knowledge_base` |

---

## 6. API endpoints

| Method | Path | Mô tả |
|---|---|---|
| GET  | `/` | Web UI chat |
| GET  | `/health` | Healthcheck |
| GET  | `/tenants` | List tenant đã đăng ký |
| POST | `/tenants` | Tạo tenant mới `{tenant_id, name, industry}` |
| POST | `/chat` | Chat: `{tenant_id, session_id, message}` |
| GET  | `/sessions/{session_id}?tenant_id=...` | Xem lịch sử hội thoại |
| POST | `/ingest` | Nạp tri thức: `{tenant_id, text|url|folder, source}` |
| GET  | `/analytics/{tenant_id}` | Báo cáo KPI |
| POST | `/csat` | Khách chấm điểm: `{tenant_id, session_id, score}` |

### Ví dụ gọi `/chat` bằng curl
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-beauty",
    "session_id": "s-test-001",
    "message": "Cho tôi xem các serum dưỡng sáng dưới 500k"
  }'
```

### Ví dụ nạp thêm tri thức từ URL
```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "demo-beauty",
    "url": "https://glow-beauty.vn/blog/cach-cham-soc-da-mua-he"
  }'
```

---

## 7. Onboard tenant mới (SME)

### 7.1. Tạo tenant
```bash
curl -X POST http://localhost:8000/tenants \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "shop-abc",
    "name": "Shop ABC",
    "industry": "electronics"
  }'
```

### 7.2. Nạp tri thức
Có 3 cách:

**Cách A — Crawl trực tiếp 1 URL:**
```bash
curl -X POST http://localhost:8000/ingest \
  -d '{"tenant_id":"shop-abc", "url":"https://shop-abc.vn/about"}'
```

**Cách B — Đẩy text trực tiếp:**
```bash
curl -X POST http://localhost:8000/ingest \
  -d '{"tenant_id":"shop-abc", "text":"Chính sách bảo hành: ...", "source":"warranty.md"}'
```

**Cách C — Load cả folder Markdown / TXT / HTML:**
```bash
curl -X POST http://localhost:8000/ingest \
  -d '{"tenant_id":"shop-abc", "folder":"./seed/shop-abc"}'
```

### 7.3. Nạp sản phẩm
Hiện tại import bằng cách bỏ JSON sản phẩm vào `data/<tenant_id>/products.json` (cùng format với `seed/beauty/products.json`). Có thể mở rộng thành endpoint `/products/bulk` nếu cần.

---

## 8. KPI Dashboard

```bash
curl http://localhost:8000/analytics/demo-beauty
```

Trả về:
```json
{
  "report": {
    "tenant_id": "demo-beauty",
    "events": {
      "message_in": 12,
      "message_out": 12,
      "faq_hit": 5,
      "product_view": 3,
      "order_created": 1,
      "csat_rated": 2,
      "response_latency_ms": 12
    },
    "avg_response_latency_ms": 1483.2,
    "avg_csat": 4.5,
    "messages_in": 12,
    "bookings_created": 0,
    "orders_created": 1,
    "conversion_rate": 0.083
  }
}
```

Các chỉ số khớp với KPI trong SRS:
- Tốc độ phản hồi trung bình → `avg_response_latency_ms`
- Tỷ lệ chuyển đổi → `conversion_rate`
- Số câu hỏi xử lý / ngày → `messages_in`
- CSAT → `avg_csat`

---

## 9. Map yêu cầu SRS → code

| Mục SRS | File |
|---|---|
| Multi-tenant | [app/tenancy.py](app/tenancy.py) |
| Function Calling | [app/core/agent.py](app/core/agent.py) + [app/tools/](app/tools/) |
| FAQ & tư vấn sâu | [app/tools/faq.py](app/tools/faq.py), [app/tools/product.py](app/tools/product.py) |
| Gợi ý sản phẩm | [app/tools/product.py](app/tools/product.py) — `suggest_products` |
| Xử lý đơn hàng + tra cứu | [app/tools/order.py](app/tools/order.py) |
| Thu thập thông tin động + Gọi API | [app/tools/booking.py](app/tools/booking.py), [app/tools/order.py](app/tools/order.py) |
| NoSQL lưu hội thoại | [app/core/memory.py](app/core/memory.py) |
| Vector DB + crawl | [app/knowledge/vectorstore.py](app/knowledge/vectorstore.py), [app/knowledge/ingest.py](app/knowledge/ingest.py) |
| Analytics & KPI | [app/core/analytics.py](app/core/analytics.py), `GET /analytics/{tenant_id}` |
| Bỏ Zalo OA → thay HTTP API + UI | [app/api/server.py](app/api/server.py), [ui/index.html](ui/index.html) |

---

## 10. Tuỳ biến

### Đổi LLM
Hỗ trợ 3 chế độ trong `.env`:

```env
# Azure OpenAI (hiện tại)
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

### Đổi embeddings sang Azure
```env
EMBEDDING_PROVIDER=azure
AZURE_OPENAI_EMBED_DEPLOYMENT=<tên-deployment-embedding>
```
*(cần tạo deployment embedding trên Azure portal trước)*

### Thêm tool Function Calling mới
1. Tạo file `app/tools/your_tool.py`:
```python
from langchain_core.tools import tool
from app.tenancy import TenantContext

def make_your_tools(tenant: TenantContext):
    @tool
    def do_something(param: str) -> str:
        """Mô tả tool này (LLM đọc docstring để biết khi nào gọi)."""
        return "kết quả"
    return [do_something]
```
2. Đăng ký trong [app/tools/__init__.py](app/tools/__init__.py) — thêm vào `build_tools()`.

---

## 11. Troubleshooting

| Triệu chứng | Nguyên nhân & fix |
|---|---|
| `DeploymentNotFound 404` | Sai `AZURE_OPENAI_CHAT_DEPLOYMENT`. Kiểm tra Azure portal → Deployments. |
| Lần đầu chạy treo lâu | Đang tải HF embedding model (~80MB). Đợi 1-2 phút. |
| `ImportError: AgentExecutor` | LangChain 1.2 đã đổi API. Code đã dùng `create_agent` mới — đảm bảo cài đúng `requirements.txt`. |
| Bot trả lời sai sản phẩm | Re-seed: xoá `data/<tenant>/vector/` rồi chạy lại `python seed_data.py`. |
| `ModuleNotFoundError: app.tools.booking` | File bị thiếu — clone lại repo hoặc tạo lại từ template. |

---

## 12. Triển khai production

Theo SRS, target là **AWS multi-tenant**. Lộ trình gợi ý:

| Layer | Dev (hiện tại) | Production gợi ý |
|---|---|---|
| LLM | Azure OpenAI | Azure OpenAI / AWS Bedrock |
| Vector DB | FAISS local | Qdrant Cloud / OpenSearch |
| NoSQL | TinyDB | DynamoDB / MongoDB Atlas |
| Embeddings | HF local | Bedrock Titan / Azure embeddings |
| Server | uvicorn 1 worker | uvicorn + gunicorn, ECS Fargate / EKS |
| Storage `data/` | local filesystem | S3 (vector index) + EFS |
| Secrets | `.env` | AWS Secrets Manager |
| CDN UI | – | CloudFront + S3 |

Bước tiếp tích hợp Zalo OA (giai đoạn 2): thêm route `POST /webhook/zalo` ở [app/api/server.py](app/api/server.py), parse payload Zalo, gọi `agent.chat(...)`, post reply bằng Zalo Send API.
