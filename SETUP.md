# Hướng dẫn chạy dự án

## Yêu cầu
Python 3.10+ · Node.js 18+ · Docker

---

## Lần đầu cài đặt

**Bước 1 — Cấu hình**
```bash
cp services/chatbot-api/.env.example services/chatbot-api/.env
```
Mở file `.env` vừa tạo, điền API key:
```
OPENAI_API_KEY=sk-...
```

**Bước 2 — Khởi động MongoDB**
```bash
docker compose up -d
```

**Bước 3 — Import database mẫu**
```bash
./db-restore.sh
```

**Bước 4 — Chạy ứng dụng**
```bash
./start.sh
```

---

## Truy cập

| Service | URL | Tài khoản |
|---|---|---|
| Web Admin | http://localhost:5173 | `admin` / `admin123` |
| API Docs | http://localhost:8000/docs | — |
| Database UI | http://localhost:8082 | — |

---

## Từ lần 2 trở đi

```bash
docker compose up -d   # nếu MongoDB chưa chạy
./start.sh
```

---

## Backup database

```bash
./db-backup.sh
git add db-backup/ && git commit -m "chore: update db backup"
```
