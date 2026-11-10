#!/bin/bash
set -e

echo "Starting Compliance Risk Analytics System (CRAS)..."

# Ensure instance and uploads directories exist
mkdir -p /app/instance /app/uploads

# If PostgreSQL is configured in DATABASE_URL, wait for it to become ready
if [[ "$DATABASE_URL" == *"postgres"* ]]; then
  echo "Waiting for PostgreSQL database to be reachable..."
  while ! nc -z postgres 5432; do
    sleep 1
  done
  echo "PostgreSQL is ready!"
else
  echo "Using SQLite database engine: ${DATABASE_URL:-sqlite:////app/instance/cras.db}"
fi

# Run database setup & statutory seeder
echo "Initializing database tables and statutory regulatory content..."
python -c "
from wsgi import app
print('CRAS schema initialized and statutory content verified.')
"
flask populate-live-data

echo "Executing entrypoint CMD: $@"
exec "$@"

