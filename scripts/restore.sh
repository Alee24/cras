#!/bin/bash
# CRAS Database Restoration Script
set -e

if [ -z "$1" ]; then
  echo "Usage: ./scripts/restore.sh <path_to_backup_file.sql.gz>"
  exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Error: Backup file $BACKUP_FILE not found."
  exit 1
fi

echo "WARNING: Restoring will overwrite existing database records in cras_db."
read -p "Are you sure you want to proceed? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Restoration aborted."
  exit 0
fi

echo "Restoring from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | docker exec -i cras_postgres psql -U cras_user -d cras_db

echo "Restoration completed successfully."
