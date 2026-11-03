#!/bin/bash
# CRAS Automated Database Backup Script
set -e

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="$BACKUP_DIR/cras_backup_$TIMESTAMP.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Creating compressed database backup: $FILENAME..."

if docker ps | grep -q cras_postgres; then
  docker exec -t cras_postgres pg_dump -U cras_user cras_db | gzip > "$FILENAME"
  echo "Backup successfully created: $FILENAME"
  # Keep only the last 30 daily backups
  find "$BACKUP_DIR" -type f -name "cras_backup_*.sql.gz" -mtime +30 -delete
else
  echo "Error: cras_postgres container is not running."
  exit 1
fi

