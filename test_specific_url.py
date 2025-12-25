"""Test script for specific scholarshipdb.net URL."""
import asyncio
from scraper import ScholarshipScraper
from bs4 import BeautifulSoup
from loguru import logger
import sys

# Setup basic logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True
)


async def test_specific_url():
    """Test accessing the specific cancer PhD scholarships URL."""
    test_url = "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer"

    logger.info("=" * 80)
    logger.info(f"Testing URL: {test_url}")
    logger.info("=" * 80)

    async with ScholarshipScraper() as scraper:
        # Navigate to the URL
        logger.info("\n[1] Attempting to navigate to the page...")
        success = await scraper.navigate_with_retry(test_url)

        if not success:
            logger.error("✗ Failed to navigate to the page")
            logger.error("Possible reasons:")
            logger.error("  - Cloudflare blocking")
            logger.error("  - Network issues")
            logger.error("  - URL changed")
            return False

        logger.info("✓ Successfully navigated to the page")

        # Get page title
        logger.info("\n[2] Getting page information...")
        title = await scraper.page.title()
        logger.info(f"Page title: {title}")

        # Get current URL (might redirect)
        current_url = scraper.page.url
        logger.info(f"Current URL: {current_url}")

        # Get page content
        logger.info("\n[3] Fetching page content...")
        content = await scraper.page.content()

        # Save HTML for inspection
        html_file = "test_cancer_phd_page.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"✓ Saved page HTML to {html_file}")

        # Parse with BeautifulSoup
        logger.info("\n[4] Analyzing page structure...")
        soup = BeautifulSoup(content, 'lxml')

        # Check for Cloudflare challenge
        if "Just a moment" in content or "Checking your browser" in content:
            logger.warning("⚠ Cloudflare challenge detected in content")
        else:
            logger.info("✓ No Cloudflare challenge detected")

        # Analyze page structure
        logger.info("\n[5] Looking for scholarship listings...")

        # Try various common selectors
        selectors_to_try = [
            ('article', None),
            ('div.scholarship', None),
            ('div.scholarship-item', None),
            ('div.card', None),
            ('div[class*="scholarship"]', None),
            ('div[class*="result"]', None),
            ('div[class*="item"]', None),
            ('div.row > div', None),
            ('ul.scholarships li', None),
            ('table tr', None),
        ]

        found_elements = {}
        for selector, class_name in selectors_to_try:
            if class_name:
                elements = soup.find_all(selector, class_=class_name)
            else:
                elements = soup.select(selector)

            if elements and len(elements) > 0:
                found_elements[selector] = len(elements)

        if found_elements:
            logger.info("✓ Found potential scholarship containers:")
            for selector, count in found_elements.items():
                logger.info(f"  - {selector}: {count} elements")
        else:
            logger.warning("⚠ No obvious scholarship containers found")

        # Look for specific content
        logger.info("\n[6] Searching for key content...")

        # Check for scholarship-related text
        text_content = soup.get_text().lower()
        keywords = ['scholarship', 'phd', 'cancer', 'deadline', 'university', 'funding']
        found_keywords = [kw for kw in keywords if kw in text_content]

        if found_keywords:
            logger.info(f"✓ Found keywords: {', '.join(found_keywords)}")
        else:
            logger.warning("⚠ No scholarship-related keywords found")

        # Look for links
        links = soup.find_all('a', href=True)
        scholarship_links = [
            link for link in links
            if 'scholarship' in link.get('href', '').lower() or
               'scholarship' in link.get_text().lower()
        ]

        logger.info(f"Total links on page: {len(links)}")
        logger.info(f"Scholarship-related links: {len(scholarship_links)}")

        if scholarship_links:
            logger.info("\nFirst 5 scholarship links:")
            for i, link in enumerate(scholarship_links[:5], 1):
                href = link.get('href', '')
                text = link.get_text(strip=True)[:80]
                logger.info(f"  {i}. {text}")
                logger.info(f"     URL: {href}")

        # Try to parse using existing parser
        logger.info("\n[7] Testing existing parser...")
        scholarships = scraper.parse_scholarship_list(soup)

        if scholarships:
            logger.info(f"✓ Parser found {len(scholarships)} scholarships!")
            logger.info("\nFirst scholarship data:")
            for key, value in scholarships[0].items():
                logger.info(f"  {key}: {value}")
        else:
            logger.warning("⚠ Parser found 0 scholarships - needs adjustment")

        # Take a screenshot
        logger.info("\n[8] Taking screenshot...")
        screenshot_file = "test_cancer_phd_page.png"
        await scraper.page.screenshot(path=screenshot_file, full_page=True)
        logger.info(f"✓ Saved screenshot to {screenshot_file}")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("TEST SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✓ Page accessible: YES")
        logger.info(f"✓ Cloudflare bypassed: {'YES' if 'Just a moment' not in content else 'NO'}")
        logger.info(f"✓ Scholarships found: {len(scholarships)}")
        logger.info(f"✓ HTML saved to: {html_file}")
        logger.info(f"✓ Screenshot saved to: {screenshot_file}")
        logger.info("=" * 80)

        return True


if __name__ == "__main__":
    asyncio.run(test_specific_url())
