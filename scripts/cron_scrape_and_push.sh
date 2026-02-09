#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/root/rss/scholarshipdb"
LOG_DIR="${REPO_DIR}/logs"
mkdir -p "${LOG_DIR}"

cd "${REPO_DIR}"

if [ -f ".venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source ".venv/bin/activate"
fi

# Run scrape (auto sync to Sheets happens only if env is set)
python3 batch_scrape.py >> "${LOG_DIR}/cron_scrape.log" 2>&1

# Commit and push data changes if any
git add data/*.json >> "${LOG_DIR}/cron_scrape.log" 2>&1 || true
if ! git diff --cached --quiet; then
  git commit -m "Auto update $(date '+%Y-%m-%d %H:%M')" >> "${LOG_DIR}/cron_scrape.log" 2>&1 || true
  git push >> "${LOG_DIR}/cron_scrape.log" 2>&1 || true
fi
