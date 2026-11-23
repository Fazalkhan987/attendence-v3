#!/usr/bin/env sh
# Daily PostgreSQL backup with 14-day rotation. Cron: 0 2 * * * /path/to/backup.sh
set -e
DIR="${BACKUP_DIR:-./backups}"; mkdir -p "$DIR"
pg_dump "${PG_URL:-postgresql://postgres:postgres@localhost:5432/attendance}" | gzip > "$DIR/attendance_$(date +%F).sql.gz"
find "$DIR" -name 'attendance_*.sql.gz' -mtime +14 -delete
