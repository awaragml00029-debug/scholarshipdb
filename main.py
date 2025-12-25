"""Main entry point for the scholarship scraper."""
import asyncio
import sys
from datetime import datetime
from loguru import logger

from config import settings
from database import init_db, get_db
from scraper import ScholarshipScraper
from storage import ScholarshipStorage


def setup_logging():
    """Configure logging."""
    logger.remove()  # Remove default handler

    # Console handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True
    )

    # File handler
    logger.add(
        settings.log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=settings.log_level,
        rotation="10 MB",
        retention="30 days",
        compression="zip"
    )

    logger.info("Logging initialized")


async def scrape_scholarships(fetch_details: bool = False):
    """Main scraping function."""
    logger.info("=" * 80)
    logger.info("Starting scholarship scraping session")
    logger.info("=" * 80)

    # Create scraping log
    log_id = ScholarshipStorage.create_scraping_log()
    scholarships_data = []
    total_pages = 0

    try:
        async with ScholarshipScraper() as scraper:
            # Get scholarship listings
            logger.info("Fetching scholarship listings...")
            listings = await scraper.get_phd_scholarships_list()

            logger.info(f"Found {len(listings)} scholarships in total")
            scholarships_data.extend(listings)

            # Optionally fetch detailed information for each scholarship
            if fetch_details and listings:
                logger.info("Fetching detailed information for each scholarship...")
                for i, listing in enumerate(listings, 1):
                    logger.info(f"Fetching details {i}/{len(listings)}: {listing['title']}")

                    try:
                        details = await scraper.get_scholarship_details(listing['url'])
                        # Merge details with listing
                        listing.update(details)
                        await scraper.random_delay()
                    except Exception as e:
                        logger.error(f"Error fetching details for {listing['url']}: {e}")
                        continue

        # Save to database
        logger.info("Saving scholarships to database...")
        stats = ScholarshipStorage.save_scholarships_batch(scholarships_data)

        # Update scraping log
        ScholarshipStorage.update_scraping_log(
            log_id,
            completed_at=datetime.utcnow(),
            status='success',
            total_scholarships=len(scholarships_data),
            new_scholarships=stats['new'],
            updated_scholarships=stats['updated'],
            total_pages=total_pages
        )

        logger.info("=" * 80)
        logger.info("Scraping session completed successfully")
        logger.info(f"Total scholarships: {len(scholarships_data)}")
        logger.info(f"New: {stats['new']}, Updated: {stats['updated']}, Errors: {stats['errors']}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"Scraping session failed: {e}", exc_info=True)
        ScholarshipStorage.update_scraping_log(
            log_id,
            completed_at=datetime.utcnow(),
            status='failed',
            error_message=str(e)
        )
        raise


async def test_scraper():
    """Test the scraper with a single page."""
    logger.info("Running scraper test...")

    async with ScholarshipScraper() as scraper:
        # Try to navigate to the main page
        success = await scraper.navigate_with_retry(f"{settings.base_url}/phd-scholarships/")

        if success:
            logger.info("✓ Successfully navigated to PhD scholarships page")
            logger.info("✓ Cloudflare bypass working")

            # Get page title
            title = await scraper.page.title()
            logger.info(f"Page title: {title}")

            # Try to get first page of listings
            content = await scraper.page.content()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'lxml')

            # Save HTML for inspection
            with open('page_sample.html', 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info("✓ Saved page HTML to page_sample.html for inspection")

            # Try to parse
            scholarships = scraper.parse_scholarship_list(soup)
            logger.info(f"✓ Found {len(scholarships)} scholarships on first page")

            if scholarships:
                logger.info("\nFirst scholarship:")
                for key, value in list(scholarships[0].items())[:5]:
                    logger.info(f"  {key}: {value}")

        else:
            logger.error("✗ Failed to navigate to page")


def show_statistics():
    """Display database statistics."""
    stats = ScholarshipStorage.get_statistics()

    print("\n" + "=" * 80)
    print("DATABASE STATISTICS")
    print("=" * 80)
    print(f"Total scholarships: {stats['total_scholarships']}")
    print(f"Active scholarships: {stats['active_scholarships']}")

    if stats['recent_scrapes']:
        print("\nRecent scraping sessions:")
        for scrape in stats['recent_scrapes']:
            print(f"  - {scrape['started_at']} | Status: {scrape['status']} | "
                  f"Total: {scrape['total']} | New: {scrape['new']}")
    print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    setup_logging()
    init_db()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == 'test':
            logger.info("Running test mode...")
            asyncio.run(test_scraper())

        elif command == 'scrape':
            fetch_details = '--details' in sys.argv
            asyncio.run(scrape_scholarships(fetch_details=fetch_details))

        elif command == 'stats':
            show_statistics()

        elif command == 'search':
            if len(sys.argv) < 3:
                print("Usage: python main.py search <query>")
                return

            query = sys.argv[2]
            results = ScholarshipStorage.search_scholarships(query=query)

            print(f"\nFound {len(results)} scholarships matching '{query}':\n")
            for scholarship in results:
                print(f"- {scholarship.title}")
                print(f"  University: {scholarship.university}")
                print(f"  Country: {scholarship.country}")
                print(f"  URL: {scholarship.url}")
                print()

        else:
            print(f"Unknown command: {command}")
            print_usage()

    else:
        print_usage()


def print_usage():
    """Print usage information."""
    print("""
PhD Scholarship Scraper
=======================

Usage:
    python main.py <command> [options]

Commands:
    test                Run a test scrape (single page only)
    scrape              Scrape all PhD scholarships
    scrape --details    Scrape with detailed information (slower)
    stats               Show database statistics
    search <query>      Search scholarships in database

Examples:
    python main.py test
    python main.py scrape
    python main.py scrape --details
    python main.py stats
    python main.py search "computer science"
    """)


if __name__ == "__main__":
    main()
