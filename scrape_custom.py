#!/usr/bin/env python
"""CLI tool for scraping custom URLs and exporting to JSON."""
import asyncio
import sys
from pathlib import Path
from loguru import logger

from scraper_v2 import ScholarshipScraperV2, scrape_custom_url


def setup_logging():
    """Setup logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )


async def main():
    """Main CLI function."""
    if len(sys.argv) < 2:
        print_usage()
        return

    command = sys.argv[1]

    if command == 'scrape':
        if len(sys.argv) < 3:
            print("Error: URL required")
            print("Usage: python scrape_custom.py scrape <URL> [output.json] [max_pages]")
            return

        url = sys.argv[2]
        output_file = sys.argv[3] if len(sys.argv) > 3 else 'scholarships.json'
        max_pages = int(sys.argv[4]) if len(sys.argv) > 4 else 10

        logger.info(f"Scraping URL: {url}")
        logger.info(f"Max pages: {max_pages}")
        logger.info(f"Output file: {output_file}")

        scholarships = await scrape_custom_url(url, output_file, max_pages)

        logger.info(f"\n{'='*60}")
        logger.info(f"✓ Scraped {len(scholarships)} scholarships")
        logger.info(f"✓ Saved to {output_file}")
        logger.info(f"{'='*60}")

        # Show first few scholarships
        if scholarships:
            logger.info("\nFirst 3 scholarships:")
            for i, sch in enumerate(scholarships[:3], 1):
                logger.info(f"\n{i}. {sch['title']}")
                logger.info(f"   Location: {sch.get('location', 'N/A')}, {sch.get('country', 'N/A')}")
                logger.info(f"   Posted: {sch.get('posted_time_text', 'N/A')}")
                logger.info(f"   URL: {sch['url']}")

    elif command == 'telegram':
        if len(sys.argv) < 3:
            print("Error: JSON file required")
            print("Usage: python scrape_custom.py telegram <scholarships.json> [per_page]")
            return

        json_file = sys.argv[2]
        per_page = int(sys.argv[3]) if len(sys.argv) > 3 else 17

        import json
        with open(json_file, 'r', encoding='utf-8') as f:
            scholarships = json.load(f)

        messages = ScholarshipScraperV2.format_for_telegram(scholarships, per_page)

        logger.info(f"Generated {len(messages)} Telegram messages")

        # Save to files
        for i, msg in enumerate(messages, 1):
            filename = f"telegram_message_{i}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(msg)
            logger.info(f"Saved: {filename}")

        # Print first message
        logger.info(f"\nFirst message preview:\n{messages[0]}")

    else:
        print(f"Unknown command: {command}")
        print_usage()


def print_usage():
    """Print usage information."""
    print("""
PhD Scholarship Scraper - Custom URL Tool
==========================================

Usage:
    python scrape_custom.py <command> [options]

Commands:
    scrape <URL> [output.json] [max_pages]
        Scrape scholarships from a custom URL

        Examples:
            # Scrape cancer PhD scholarships
            python scrape_custom.py scrape "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer"

            # Save to custom file, limit to 5 pages
            python scrape_custom.py scrape "https://scholarshipdb.net/scholarships/Program-PhD?q=AI" ai_scholarships.json 5

            # Scrape UK scholarships
            python scrape_custom.py scrape "https://scholarshipdb.net/scholarships-in-United-Kingdom"

    telegram <scholarships.json> [per_page]
        Format JSON file for Telegram messages

        Examples:
            python scrape_custom.py telegram scholarships.json
            python scrape_custom.py telegram scholarships.json 20

Output:
    - JSON file with all scholarship data
    - Each scholarship includes:
        * title
        * url
        * location
        * country
        * description
        * posted_time (absolute ISO 8601 format)
        * posted_time_text (original relative time)
        * scraped_at

Example Workflow:
    # 1. Scrape scholarships
    python scrape_custom.py scrape "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer" cancer.json

    # 2. Format for Telegram
    python scrape_custom.py telegram cancer.json 17

    # 3. Use telegram_message_1.txt, telegram_message_2.txt, etc.
    """)


if __name__ == "__main__":
    setup_logging()
    asyncio.run(main())
