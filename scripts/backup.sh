#!/bin/bash
set -e

echo "=== NAVIORA AI SUPABASE DATABASE BACKUP SCRIPT ==="

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/supabase_backup_${TIMESTAMP}.sql"

mkdir -p ${BACKUP_DIR}

echo "Dumping database from Supabase Cloud..."
PGPASSWORD="NAVIORA2026" pg_dump -h db.grcudjazfyfhjibjlrrj.supabase.co -U postgres -p 5432 -d postgres -F p -f ${BACKUP_FILE}

echo "✅ Backup saved successfully to: ${BACKUP_FILE}"
