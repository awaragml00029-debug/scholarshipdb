#!/bin/bash
# PhD Scholarship Scraper - Automated Task
# Runs every 12 hours

cd /root/scholar/scholarshipdb

# Activate virtual environment
source ~/scholar/scholar/bin/activate

# Pull latest configuration from GitHub (current branch)
git pull

# Run scraper
python batch_scrape.py

# Generate RSS feed
python generate_rss.py

# Sync to Google Sheets
python sync_to_sheets.py

# Translate titles to Chinese
python translate_titles.py

# Generate daily report (only new scholarships)
python generate_daily_report.py

# Copy data to docs for GitHub Pages
mkdir -p docs/data docs/reports
cp data/*.json docs/data/
cp -r reports/* docs/reports/ 2>/dev/null || true

# Commit and push
git add -A
git commit -m "Auto update $(date '+%Y-%m-%d %H:%M')"
git push

# Deactivate virtual environment
deactivate
