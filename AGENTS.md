# SC Chatbot — Agent Guide

## Quick start
```bash
./start.sh               # auto .venv + install + seed + start all 4 processes
./start.sh --install     # force reinstall pip+npm
./start.sh --seed        # force re-seed knowledge base
./stop.sh                # stop all (or Ctrl+C on start.sh)

# Docker (copy .env.example → .env first)
cp .env.example .env
docker compose up --build -d          # TinyDB backend (default)
docker compose --profile seed up --build -d          # with auto-seed
docker compose --profile seed --profile mongo up --build -d  # with MongoDB
docker compose down --volumes         # stop + remove volumes
```

## Services (all in `services/`)
| Directory | Stack | Port | Entry |
|---|---|---|---|
| `chatbot-api/` | FastAPI + LangChain + FAISS + TinyDB | 8000 | `python run.py` + `python telegram_worker.py` |
| `client-server/` | FastAPI (mock business API) | 8001 | `python run.py` |
| `web-admin/` | React + Vite + TypeScript + Tailwind | 5173 | `npm run dev` |

- Shared `.venv` at repo root (not per-service).
- Each service has `run.py` entrypoint, `.env.example` → copy to `.env`, own `requirements.txt`.

## Docker Compose profiles
| Profile | Effect |
|---|---|
| (none) | TinyDB backend, no auto-seed |
| `seed` | Runs `seed_data.py` init container before chatbot-api |
| `mongo` | Adds MongoDB service; set `STORAGE_BACKEND=mongo` in `.env` |

Usage:
```bash
docker compose up --build -d                 # default (TinyDB)
docker compose --profile seed up --build -d  # auto-seed KB + tenants
docker compose --profile seed --profile mongo up --build -d  # MongoDB + seed
```

## Key entrypoints
- `services/chatbot-api/run.py` — HTTP server (`app.api.server:app`)
- `services/chatbot-api/telegram_worker.py` — Telegram polling worker (separate process)
- `services/chatbot-api/seed_data.py` — seed tenants + knowledge base (run once)
- `services/chatbot-api/migrate_history_to_mongo.py` — migrate TinyDB → MongoDB

## Architecture notes
- chatbot-api = multi-tenant AI brain: LangChain agent + RAG (FAISS per tenant) + TinyDB chat history.
- Tools (`product.py`, `order.py`, `booking.py`) still call TinyDB directly, **not** client-server REST (except `check_stock`). Refactoring that is pending.
- client-server is a mock — in-memory store, restart loses orders/bookings.
- web-admin talks to chatbot-api `/admin/*` endpoints (JWT auth).
- Telegram user sessions use `tg-{user_id}` as session_id.

## Config (`.env` per service)
- **LLM**: `LLM_PROVIDER=azure|openai`, `EMBEDDING_PROVIDER=huggingface|openai|azure`
- **Storage**: `STORAGE_BACKEND=tinydb` (default, no infra) or `mongo`
- **Auth**: `INTERNAL_API_KEY` shared between chatbot-api ↔ client-server (header `X-API-Key`); `JWT_SECRET` + `ADMIN_USER`/`ADMIN_PASSWORD` for web-admin login
- **Telegram**: `TELEGRAM_BOT_TOKEN` required for Telegram worker

## CI/CD — GitHub Actions deploy

A deploy workflow (`.github/workflows/deploy.yml`) auto-deploys on push to `main` or `ci-cd-workflow`.

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `SSH_HOST` | Target host IP or domain |
| `SSH_PORT` | SSH port (default `22`) |
| `SSH_USER` | SSH login user |
| `SSH_PRIVATE_KEY` | SSH private key in PEM format |
| `DEPLOY_PATH` | Absolute path to the project directory on the host (default `/opt/sc-chatbot`) |
| `GH_PAT` | GitHub Personal Access Token with repo scope (for private repo pulls) |

Optional secrets for port remapping (defaults in parentheses):
- `WEB_ADMIN_PORT` (`30001`), `CHATBOT_API_PORT` (`30002`), `CLIENT_SERVER_PORT` (`30003`)

### Initial host setup (one-time)

```bash
ssh <user>@<host>
git clone https://github.com/ngocphamttdt/sc-chatbot.git /opt/sc-chatbot
cd /opt/sc-chatbot
cp services/chatbot-api/.env.example services/chatbot-api/.env
cp services/client-server/.env.example services/client-server/.env
cp services/web-admin/.env.example services/web-admin/.env
# edit .env files with production values
```

### Deploy flow

1. Push to `main` triggers the workflow.
2. Workflow SSHes into the host and runs `git pull`.
3. Writes `.env` with port overrides from secrets.
4. Runs `docker compose --profile seed up --build -d`.
5. Health-checks `chatbot-api` (retries up to 60s).
6. Prunes Docker images older than 24h.

## No tests, no linter, no typecheck
- Zero test files or test runner config anywhere in repo.
- No ruff/mypy/ESLint config files.
- Dockerfiles exist per service in `services/*/Dockerfile`; `docker-compose.yml` at root.
- `web-admin` build runs `tsc -b && vite build` (so TypeScript errors surface at build time only).

## Conventions
- All docs and strings are in **Vietnamese**.
- Data at runtime created in `services/chatbot-api/data/` (gitignored).
- Logs go to `logs/` (created by `start.sh`, gitignored).
- Python: no package metadata (`pyproject.toml` / `setup.py` — scripts run via `python <file>.py`).
