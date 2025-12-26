#!/bin/bash
set -e

# Default scrape interval (12 hours = 43200 seconds)
SCRAPE_INTERVAL=${SCRAPE_INTERVAL:-43200}

echo "==========================================="
echo "PhD Scholarship Scraper (Docker)"
echo "==========================================="
echo "Scrape interval: ${SCRAPE_INTERVAL} seconds ($(($SCRAPE_INTERVAL / 3600)) hours)"
echo ""

# Function to run the scraping pipeline
run_scraper() {
    echo "----------------------------------------"
    echo "Starting scrape cycle at $(date)"
    echo "----------------------------------------"

    # Pull latest configuration if git is configured
    if [ -d .git ] && git remote -v | grep -q origin; then
        echo "Pulling latest configuration from Git..."
        git pull origin main 2>/dev/null || git pull origin master 2>/dev/null || echo "Git pull skipped (no remote configured)"
    fi

    # Run scraper
    echo "Running batch scraper..."
    python batch_scrape.py

    # Generate RSS feed
    if [ -f generate_rss.py ]; then
        echo "Generating RSS feed..."
        python generate_rss.py
    fi

    # Sync to Google Sheets
    if [ -f sync_to_sheets.py ] && [ -f credentials.json ]; then
        echo "Syncing to Google Sheets..."
        python sync_to_sheets.py
    fi

    # Copy data to docs for GitHub Pages
    echo "Copying data to docs..."
    mkdir -p docs/data
    cp -f data/*.json docs/data/ 2>/dev/null || true

    # Commit and push if git is configured
    if [ -d .git ] && git remote -v | grep -q origin; then
        echo "Committing changes..."
        git add -A
        git commit -m "Auto update $(date '+%Y-%m-%d %H:%M')" 2>/dev/null || echo "No changes to commit"

        echo "Pushing to remote..."
        git push 2>/dev/null || echo "Git push skipped (no credentials or remote configured)"
    fi

    echo "----------------------------------------"
    echo "Scrape cycle completed at $(date)"
    echo "Next run in ${SCRAPE_INTERVAL} seconds"
    echo "----------------------------------------"
    echo ""
}

# Run once immediately
run_scraper

# Continue running on schedule
while true; do
    sleep ${SCRAPE_INTERVAL}
    run_scraper
done
