#!/usr/bin/env bash
#
# Import db-backup vào MongoDB đang chạy trong Docker.
#
# Cách dùng:
#   ./db-restore.sh
#
set -euo pipefail

CONTAINER="sc-mongodb"
DB_NAME="scchatbot"
BACKUP_PATH="/db-backup/scchatbot"

# Kiểm tra container có đang chạy không
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "❌  Container '${CONTAINER}' chưa chạy."
  echo "    Chạy trước: docker compose up -d"
  exit 1
fi

echo "==> Import database '${DB_NAME}' từ backup..."
docker exec "${CONTAINER}" mongorestore \
  --db "${DB_NAME}" \
  --drop \
  "${BACKUP_PATH}"

echo ""
echo "✅  Xong! Vào http://localhost:8082 để kiểm tra."
