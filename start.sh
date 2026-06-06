#!/usr/bin/env bash
#
# Start toàn bộ SC Chatbot stack:
#   - client-server   : run.py            (port 8001)
#   - chatbot-api      : run.py            (port 8000)
#   - chatbot-api      : telegram_worker.py (Telegram polling)
#   - web-admin        : npm run dev       (port 5173)
#
# Lần đầu chạy (hoặc thiếu môi trường) sẽ tự:
#   - tạo .venv nếu chưa có
#   - pip install requirements cho chatbot-api + client-server
#   - npm install cho web-admin
#   - python seed_data.py (seed knowledge base)
#
# Cách dùng:
#   ./start.sh            # tự phát hiện lần đầu, rồi start tất cả
#   ./start.sh --install  # ép cài lại deps (pip + npm) trước khi start
#   ./start.sh --seed     # ép seed lại dữ liệu trước khi start
#   Ctrl+C                # dừng tất cả service
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$ROOT/.venv"
CHATBOT="$ROOT/services/chatbot-api"
CLIENT="$ROOT/services/client-server"
ADMIN="$ROOT/services/web-admin"
LOGS="$ROOT/logs"

FORCE_INSTALL=0
FORCE_SEED=0
for arg in "$@"; do
  case "$arg" in
    --install) FORCE_INSTALL=1 ;;
    --seed)    FORCE_SEED=1 ;;
    -h|--help)
      grep '^#' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *) echo "Tham số không hợp lệ: $arg (dùng -h để xem help)"; exit 1 ;;
  esac
done

# --- 1. virtualenv (cross-platform: Windows -> Scripts, mac/Linux -> bin) --
venv_python() {
  if [ -f "$VENV_DIR/Scripts/python.exe" ]; then
    echo "$VENV_DIR/Scripts/python.exe"
  elif [ -f "$VENV_DIR/bin/python" ]; then
    echo "$VENV_DIR/bin/python"
  fi
}

VENV_PY="$(venv_python)"
if [ -z "$VENV_PY" ]; then
  echo "==> Chưa có .venv, tạo mới..."
  PYTHON_BIN="$(command -v python3 || command -v python || true)"
  if [ -z "$PYTHON_BIN" ]; then
    echo "Không tìm thấy python3/python trong PATH."; exit 1
  fi
  "$PYTHON_BIN" -m venv "$VENV_DIR"
  FORCE_INSTALL=1
  VENV_PY="$(venv_python)"
fi

# --- 2. pip install (lần đầu / --install) ---------------------------------
if [ "$FORCE_INSTALL" -eq 1 ]; then
  echo "==> Cài Python deps (chatbot-api + client-server)..."
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r "$CHATBOT/requirements.txt"
  "$VENV_PY" -m pip install -r "$CLIENT/requirements.txt"
fi

# --- 3. npm install (lần đầu / --install / thiếu node_modules) -------------
if [ "$FORCE_INSTALL" -eq 1 ] || [ ! -d "$ADMIN/node_modules" ]; then
  echo "==> Cài web-admin deps (npm install)..."
  ( cd "$ADMIN" && npm install )
fi

# --- 4. seed dữ liệu (lần đầu / --seed / thiếu data) -----------------------
if [ "$FORCE_SEED" -eq 1 ] || [ ! -d "$CHATBOT/data" ]; then
  echo "==> Seed knowledge base (seed_data.py)..."
  ( cd "$CHATBOT" && "$VENV_PY" seed_data.py )
fi

# --- 5. start services -----------------------------------------------------
mkdir -p "$LOGS"
pids=()
names=()

start() {
  local name="$1"; shift
  local dir="$1"; shift
  echo "==> Start $name ..."
  ( cd "$dir" && exec "$@" ) >"$LOGS/$name.log" 2>&1 &
  pids+=("$!")
  names+=("$name")
  echo "    $name (PID $!) -> logs/$name.log"
}

cleanup() {
  echo ""
  echo "==> Dừng tất cả service..."
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

start "client-server"   "$CLIENT"  "$VENV_PY" run.py
start "chatbot-api"     "$CHATBOT" "$VENV_PY" run.py
start "telegram-worker" "$CHATBOT" "$VENV_PY" telegram_worker.py
start "web-admin"       "$ADMIN"   npm run dev

echo ""
echo "Tất cả service đã chạy:"
echo "  chatbot-api  : http://localhost:8000   (UI chat + /docs)"
echo "  client-server: http://localhost:8001/docs"
echo "  web-admin    : http://localhost:5173"
echo "  Telegram     : worker đang polling (xem logs/telegram-worker.log)"
echo ""
echo "Log realtime:  tail -f logs/<service>.log"
echo "Nhấn Ctrl+C để dừng tất cả."
wait
