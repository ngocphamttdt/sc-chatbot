# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Stack

```bash
# First run (auto-installs deps + seeds data)
./start.sh

# Force reinstall deps
./start.sh --install

# Force re-seed knowledge base
./start.sh --seed
```

Services:
- `chatbot-api` → http://localhost:8000 (FastAPI + Swagger at `/docs`)
- `client-server` → http://localhost:8001 (mock business REST API)
- `web-admin` → http://localhost:5173 (React SPA)
- `telegram-worker` → polling (logs at `logs/telegram-worker.log`)

Logs go to `logs/<service>.log`. Use `tail -f logs/<service>.log` to follow.

## Running Individual Services

```bash
# Python services (requires .venv activated or use full path)
.venv/bin/python services/chatbot-api/run.py
.venv/bin/python services/client-server/run.py
.venv/bin/python services/chatbot-api/telegram_worker.py

# Web admin
cd services/web-admin && npm run dev

# Seed data manually
cd services/chatbot-api && ../.venv/bin/python seed_data.py
```

## Environment Variables

Copy `.env` into `services/chatbot-api/` and `services/client-server/`. Key vars:

| Var | Default | Notes |
|-----|---------|-------|
| `LLM_PROVIDER` | `openai` | `openai` or `azure` |
| `OPENAI_API_KEY` | — | Required for OpenAI/compatible |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Override for Ollama etc. |
| `LLM_MODEL` | `gpt-4o-mini` | Chat model name |
| `EMBEDDING_PROVIDER` | `huggingface` | `huggingface`, `openai`, or `azure` |
| `HF_EMBED_MODEL` | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Local embed (works offline, supports Vietnamese) |
| `STORAGE_BACKEND` | `tinydb` | `tinydb` (local JSON) or `mongo` |
| `MONGO_URI` | `mongodb://localhost:27017/scchatbot` | Only needed if `STORAGE_BACKEND=mongo` |
| `DATA_DIR` | `./data` | Root for all per-tenant files |
| `DEFAULT_TENANT` | `demo-beauty` | Fallback tenant when none specified |
| `JWT_SECRET` | `dev-secret-change-me` | Change in production |
| `ADMIN_USER` / `ADMIN_PASSWORD` | `admin` / `admin123` | Super-admin env credentials |
| `INTERNAL_API_KEY` | — | Shared secret between chatbot-api and client-server |
| `TELEGRAM_BOT_TOKEN` | — | Required for Telegram integration |

## Architecture

The system is a **multi-tenant chatbot platform** with three backend services and one SPA.

### Multi-Tenancy Model

Every request carries a `tenant_id`. `TenantContext` (in `tenancy.py`) provides each tenant with an isolated filesystem layout under `DATA_DIR/{tenant_id}/`:
- `vector/kb.faiss` + `vector/kb.pkl` — FAISS knowledge base index
- `uploads/` — raw uploaded documents
- `conversations.json` (TinyDB) or MongoDB — chat history
- `config.json` — system prompt config

### chatbot-api (`services/chatbot-api/`)

**Request → Reply flow:**
1. `POST /chat` hits `agent.chat()` in `core/agent.py`
2. Loads last 20 messages of history (`core/memory.py`)
3. Does a **light RAG**: queries FAISS for top-3 relevant KB chunks, injects them into the system prompt
4. Builds a LangGraph ReAct agent with 4 tool groups (FAQ, products, orders, bookings)
5. Agent invokes tools as needed (including `search_knowledge_base` for more KB chunks)
6. Persists both turns to history + tracks analytics events

**Knowledge base ingestion pipeline:**
1. `POST /admin/documents` → `admin/documents.py:save_upload()` saves file, inserts MongoDB record with `status=processing`
2. `admin/documents.py:run_ingest()` runs in background → calls `knowledge/ingest.py`
3. `ingest.py` uses LangChain loaders (PDF/DOCX/TXT/HTML) → splits into ~800-char chunks (120 overlap)
4. `knowledge/vectorstore.py:upsert()` calls `get_embeddings()` to convert text → vectors → saves to FAISS
5. MongoDB record updated to `status=done` with `chunk_count`

**LLM / Embeddings:** Configured via env vars in `core/llm.py`. Supports Azure OpenAI, OpenAI-compatible (including Ollama), and local HuggingFace (default). Models are singletons via `@lru_cache`.

**Tools** (assembled per-tenant by `tools/__init__.py:build_tools()`):
- `search_knowledge_base` — FAISS similarity search over KB
- `get_product` — fetch product catalog from client-server
- `create_order` / `get_order` — order management via client-server
- `create_booking` / `get_booking` — booking management via client-server

### client-server (`services/client-server/`)

Mock business REST API (products, orders, bookings). Protected by `X-API-Key: INTERNAL_API_KEY`. The chatbot-api calls this service when tools need business data.

### web-admin (`services/web-admin/`)

React + TypeScript SPA (Vite). Communicates with chatbot-api's `/admin/*` endpoints using a JWT Bearer token.

**RBAC system** (`src/rbac.ts`): Permissions are granular strings (`stats.read`, `conversations.read`, `documents.read`, `documents.write`, `prompt.read`, `prompt.write`). Roles are stored in MongoDB and carry a list of permissions. Two user types:
- **Admin users** (`user_type=admin`): super_admin or support — platform-wide access
- **Tenant users** (`user_type=tenant`): scoped to a single tenant, permissions from their role

Auth flow: `POST /admin/login` checks env-admin first, then MongoDB admin users, then tenant users. Returns a JWT with `user_type`, `role`, `tenant_id`, and `permissions` claims. `auth.enforce_tenant_scope()` ensures tenant users can't cross-tenant.

### Chat History Storage

Dual-backend via `STORAGE_BACKEND` env var. The public API (`append_turn`, `load_history`, `session_summary`) is identical — `core/memory.py` dispatches internally. TinyDB stores per-tenant JSON files; MongoDB stores in `messages` + `conversations` collections and enables cross-tenant aggregations in `admin/aggregations.py`.
