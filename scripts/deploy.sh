#!/usr/bin/env bash
set -e

echo "=== NAVIORA AI PRODUCTION DEPLOYMENT ==="

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="./backups"
mkdir -p "$BACKUP_DIR"

echo "--> Step 1: Backing up database..."
if [ -n "$DATABASE_URL" ]; then
    pg_dump "$DATABASE_URL" > "$BACKUP_DIR/naviora_db_backup_$TIMESTAMP.sql" || echo "Warning: pg_dump backup skipped or completed with notices."
else
    echo "Database URL not set; skipping automated pg_dump backup."
fi

echo "--> Step 2: Running Alembic database migrations..."
cd backend
alembic upgrade head
cd ..

echo "--> Step 3: Building and deploying production Docker containers..."
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d

echo "--> Step 4: Performing health check..."
MAX_RETRIES=12
RETRY_COUNT=0
HEALTH_URL="http://localhost:8000/api/v1/health"

until curl -s -f "$HEALTH_URL" > /dev/null || [ $RETRY_COUNT -eq $MAX_RETRIES ]; do
    echo "Waiting for health check endpoint to respond ($RETRY_COUNT/$MAX_RETRIES)..."
    RETRY_COUNT=$((RETRY_COUNT+1))
    sleep 5
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "ERROR: Health check failed after deployment!"
    exit 1
fi

echo "=== DEPLOYMENT COMPLETED SUCCESSFULLY ==="
