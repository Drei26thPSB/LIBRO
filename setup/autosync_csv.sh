#!/usr/bin/env bash
set -euo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin"
cd /home/librarysys/LIBRO

exec 9>/tmp/libro_autosync.lock
flock -n 9 || exit 0

# only CSV data
git add csv_files backups/daily || true
git diff --cached --quiet && exit 0

git commit -m "Auto-sync CSV: $(date '+%Y-%m-%d %H:%M:%S')"

# sync safely even if remote moved
git pull --rebase --autostash origin main || true
git push origin main
