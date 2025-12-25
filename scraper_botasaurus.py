#!/usr/bin/env python
"""Botasaurus-based scraper for scholarshipdb.net to bypass Cloudflare."""
import json
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urljoin
from pathlib import Path

from botasaurus.browser import browser, Driver
from botasaurus.request import request, Request
from bs4 import BeautifulSoup
from loguru import logger

from time_parser import parse_relative_time


@browser(
    # Bypass Cloudflare protection
    bypass_cloudflare=True,
    # Use stealth mode
    block_images=True,  # Faster loading
    wait_for_complete_page_load=True,
    # Headless mode
    headless=True,
    # User agent
    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
)
def scrape_scholarship_page(driver: Driver, url: str, max_pages: int = 5) -> List[Dict]:
    """
    Scrape scholarships using Botasaurus with Cloudflare bypass.

    Args:
        driver: Botasaurus driver instance
        url: URL to scrape
        max_pages: Maximum pages to scrape

    Returns:
        List of scholarship dictionaries
    """
    scholarships = []
    base_url = "https://scholarshipdb.net"

    logger.info(f"Navigating to {url} with Cloudflare bypass")

    # Navigate to URL
    driver.get(url)

    # Wait for page load
    driver.wait_for_complete_page_load()

    page_number = 1

    while page_number <= max_pages:
        logger.info(f"Scraping page {page_number}...")

        # Get page HTML
        html = driver.page_html
        soup = BeautifulSoup(html, 'lxml')

        # Parse scholarships
        page_scholarships = parse_scholarships(soup, base_url)

        if not page_scholarships:
            logger.info("No scholarships found, stopping")
            break

        scholarships.extend(page_scholarships)
        logger.info(f"Found {len(page_scholarships)} scholarships on page {page_number}")

        # Try to go to next page
        try:
            # Find next button
            next_button = driver.select('a[rel="next"]') or \
                         driver.select('a.next') or \
                         driver.select('.pagination a:contains("›")')

            if next_button:
                logger.debug(f"Found next button, clicking...")
                next_button.click()
                driver.wait_for_complete_page_load()
                page_number += 1
                driver.sleep(2)  # Delay between pages
            else:
                logger.info("No next page found, stopping")
                break

        except Exception as e:
            logger.error(f"Error in pagination: {e}")
            break

    return scholarships


def parse_scholarships(soup: BeautifulSoup, base_url: str) -> List[Dict]:
    """Parse scholarships from HTML."""
    scholarships = []

    # Find all <li> elements that contain scholarships
    list_items = soup.find_all('li')

    logger.debug(f"Found {len(list_items)} <li> elements")

    for li in list_items:
        try:
            scholarship = extract_from_li(li, base_url)
            if scholarship:
                scholarships.append(scholarship)
        except Exception as e:
            logger.debug(f"Error parsing li: {e}")
            continue

    return scholarships


def extract_from_li(li, base_url: str) -> Optional[Dict]:
    """Extract scholarship data from <li> element."""
    try:
        # Find title and link in <h4><a>
        h_tag = li.find(['h4', 'h3', 'h2'])
        if not h_tag:
            return None

        link = h_tag.find('a')
        if not link or not link.get('href'):
            return None

        title = link.get_text(strip=True)
        url = urljoin(base_url, link['href'])

        # Extract university/school name
        university = None
        all_links = li.find_all('a', href=True)
        for a in all_links:
            if '/scholarships-at-' in a.get('href', ''):
                university = a.get_text(strip=True)
                break

        # Extract location and country
        location = None
        country = None

        # Get location from span
        location_spans = li.find_all('span', class_='text-success')
        if location_spans:
            location = location_spans[0].get_text(strip=True)

        # Get country from link
        for a in all_links:
            if '/scholarships-in-' in a.get('href', '') and 'text-success' in a.get('class', []):
                country = a.get_text(strip=True)
                break

        # Time (class="text-muted")
        posted_time = None
        posted_time_text = None
        time_spans = li.find_all('span', class_='text-muted')
        if time_spans:
            posted_time_text = time_spans[0].get_text(strip=True)
            if posted_time_text:
                posted_time = parse_relative_time(posted_time_text)

        # Description from <p>
        description = None
        p_tag = li.find('p')
        if p_tag:
            description = p_tag.get_text(strip=True)

        # Build result
        result = {
            'title': title,
            'university': university,
            'location': location,
            'country': country,
            'description': description,
            'url': url,
            'posted_time': posted_time.isoformat() if posted_time else None,
            'posted_time_text': posted_time_text,
            'scraped_at': datetime.now(timezone.utc).isoformat(),
        }

        logger.debug(f"Extracted: {title} - {university}")
        return result

    except Exception as e:
        logger.debug(f"Error extracting from li: {e}")
        return None


def export_to_json(scholarships: List[Dict], filename: str = 'scholarships.json'):
    """Export scholarships to JSON file."""
    filepath = Path(filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(scholarships, f, ensure_ascii=False, indent=2)

    logger.info(f"Exported {len(scholarships)} scholarships to {filepath}")
    return str(filepath)


# Example usage
if __name__ == "__main__":
    # Test with a single URL
    url = "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer"

    logger.info(f"Testing Botasaurus scraper with: {url}")

    # Run scraper
    scholarships = scrape_scholarship_page(url, max_pages=2)

    logger.info(f"\n{'='*60}")
    logger.info(f"✓ Scraped {len(scholarships)} scholarships")
    logger.info(f"{'='*60}")

    if scholarships:
        # Export to JSON
        export_to_json(scholarships, 'botasaurus_test.json')

        # Show first few
        logger.info("\nFirst 3 scholarships:")
        for i, sch in enumerate(scholarships[:3], 1):
            logger.info(f"\n{i}. {sch['title']}")
            logger.info(f"   University: {sch.get('university', 'N/A')}")
            logger.info(f"   Location: {sch.get('location', 'N/A')}, {sch.get('country', 'N/A')}")
            logger.info(f"   Posted: {sch.get('posted_time_text', 'N/A')}")
            logger.info(f"   URL: {sch['url']}")
