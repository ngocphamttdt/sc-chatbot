#!/usr/bin/env bash
#
# Backup database scchatbot ra thư mục db-backup/.
#
# Cách dùng:
#   ./db-backup.sh
#
set -euo pipefail

CONTAINER="sc-mongodb"
DB_NAME="scchatbot"
BACKUP_PATH="/db-backup"

# Kiểm tra container có đang chạy không
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
  echo "❌  Container '${CONTAINER}' chưa chạy."
  echo "    Chạy trước: docker compose up -d"
  exit 1
fi

echo "==> Backup database '${DB_NAME}'..."
docker exec "${CONTAINER}" mongodump \
  --db "${DB_NAME}" \
  --out "${BACKUP_PATH}"

echo ""
echo "✅  Xong! Data đã được lưu vào thư mục db-backup/scchatbot/"
