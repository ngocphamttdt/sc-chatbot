#!/usr/bin/env bash
#
# Dừng tất cả service do start.sh khởi động.
# Đọc PID từ logs/run.pids; nếu không có thì fallback kill theo port (8000/8001/5173).
#
# Cách dùng:
#   ./stop.sh
#
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$ROOT/logs/run.pids"

kill_pid() {
  local pid="$1" name="$2"
  if kill -0 "$pid" 2>/dev/null; then
    echo "==> Dừng $name (PID $pid)"
    kill "$pid" 2>/dev/null || true
  fi
}

if [ -f "$PID_FILE" ]; then
  while read -r pid name; do
    [ -n "$pid" ] && kill_pid "$pid" "$name"
  done < "$PID_FILE"
  rm -f "$PID_FILE"
  echo "==> Đã dừng theo logs/run.pids."
else
  echo "Không thấy logs/run.pids — fallback kill theo port..."
  for port in 8000 8001 5173; do
    # Windows (Git Bash) có netstat; mac/Linux có lsof
    if command -v lsof >/dev/null 2>&1; then
      for pid in $(lsof -ti tcp:"$port" 2>/dev/null); do
        kill_pid "$pid" "port $port"
      done
    elif command -v netstat >/dev/null 2>&1; then
      for pid in $(netstat -ano 2>/dev/null | grep -E "[:.]$port[[:space:]].*LISTENING" | awk '{print $NF}' | sort -u); do
        echo "==> Dừng process trên port $port (PID $pid)"
        # Windows: dùng taskkill để kill cả cây process
        if command -v taskkill >/dev/null 2>&1; then
          taskkill //PID "$pid" //F //T >/dev/null 2>&1 || true
        else
          kill "$pid" 2>/dev/null || true
        fi
      done
    fi
  done
fi

echo "Done."
