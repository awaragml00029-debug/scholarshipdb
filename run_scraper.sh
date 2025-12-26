#!/bin/bash
# PhD Scholarship Scraper - Automated Task
# Runs every 12 hours

cd /root/scholar/scholarshipdb

# Pull latest configuration from GitHub
git pull origin main

# Run scraper
/usr/bin/python batch_scrape.py

# Generate RSS feed
/usr/bin/python generate_rss.py

# Sync to Google Sheets
/usr/bin/python sync_to_sheets.py

# Copy data to docs for GitHub Pages
mkdir -p docs/data
cp data/*.json docs/data/

# Commit and push
git add -A
git commit -m "Auto update $(date '+%Y-%m-%d %H:%M')"
git push
