#!/bin/bash
# PhD Scholarship Scraper - Automated Task
# Runs every 12 hours

cd /root/scholar/scholarshipdb

# Pull latest configuration from GitHub (current branch)
git pull

# Run scraper with uv
uv run python batch_scrape.py

# Generate RSS feed
uv run python generate_rss.py

# Sync to Google Sheets
uv run python sync_to_sheets.py

# Translate titles to Chinese
uv run python translate_titles.py

# Generate daily report (only new scholarships)
uv run python generate_daily_report.py

# Copy data to docs for GitHub Pages
mkdir -p docs/data docs/reports
cp data/*.json docs/data/
cp -r reports/* docs/reports/ 2>/dev/null || true

# Commit and push
git add -A
git commit -m "Auto update $(date '+%Y-%m-%d %H:%M')"

# Push with retry on conflict
git push || (git pull --no-rebase && git push)
