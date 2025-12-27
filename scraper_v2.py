"""Enhanced scraper with custom URL support and JSON export."""
import asyncio
import json
import re
from datetime import datetime, timezone
from typing import List, Dict, Optional
from urllib.parse import urljoin
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
from loguru import logger

from config import settings
from time_parser import parse_relative_time


class ScholarshipScraperV2:
    """Enhanced scraper for scholarshipdb.net with custom URL and JSON export."""

    def __init__(self, proxy: Optional[str] = None):
        """
        Initialize scraper.

        Args:
            proxy: Optional proxy URL (e.g., "socks5://user:pass@host:port" or "socks5://host:port")
        """
        self.base_url = settings.base_url
        self.proxy = proxy
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def start(self):
        """Initialize the browser."""
        if self.proxy:
            logger.info(f"Starting Playwright browser with proxy: {self._mask_proxy(self.proxy)}...")
        else:
            logger.info("Starting Playwright browser...")

        self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(
            headless=settings.scraper_headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-extensions',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ],
            chromium_sandbox=False,
        )

        # Prepare context options
        context_options = {
            'viewport': {'width': 1920, 'height': 1080},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'locale': 'en-US',
        }

        # Add proxy if configured
        if self.proxy:
            proxy_config = self._parse_proxy(self.proxy)
            context_options['proxy'] = proxy_config

        self.context = await self.browser.new_context(**context_options)

        await self.context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })

        self.page = await self.context.new_page()

        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        logger.info("Browser started successfully")

    async def close(self):
        """Close the browser."""
        try:
            if self.page:
                try:
                    await self.page.close()
                except Exception as e:
                    logger.debug(f"Error closing page (may already be closed): {e}")

            if self.context:
                try:
                    await self.context.close()
                except Exception as e:
                    logger.debug(f"Error closing context (may already be closed): {e}")

            if self.browser:
                try:
                    await self.browser.close()
                except Exception as e:
                    logger.debug(f"Error closing browser (may already be closed): {e}")

            if hasattr(self, 'playwright'):
                try:
                    await self.playwright.stop()
                except Exception as e:
                    logger.debug(f"Error stopping playwright (may already be stopped): {e}")
        except Exception as e:
            logger.warning(f"Error in close(): {e}")

    def _parse_proxy(self, proxy_url: str) -> dict:
        """
        Parse proxy URL into Playwright proxy config.

        Args:
            proxy_url: Proxy URL (e.g., "socks5://user:pass@host:port" or "socks5://host:port")

        Returns:
            Dict with proxy configuration for Playwright
        """
        from urllib.parse import urlparse

        parsed = urlparse(proxy_url)
        proxy_config = {
            'server': f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
        }

        if parsed.username:
            proxy_config['username'] = parsed.username
        if parsed.password:
            proxy_config['password'] = parsed.password

        return proxy_config

    def _mask_proxy(self, proxy_url: str) -> str:
        """Mask proxy credentials for logging."""
        from urllib.parse import urlparse

        parsed = urlparse(proxy_url)
        if parsed.username:
            return f"{parsed.scheme}://***:***@{parsed.hostname}:{parsed.port}"
        return proxy_url

    async def wait_for_cloudflare(self):
        """Wait for Cloudflare challenge."""
        try:
            await self.page.wait_for_selector(
                'text="Checking your browser"',
                state='detached',
                timeout=30000
            )
        except Exception:
            pass
        # Longer wait for CI/CD environments
        await asyncio.sleep(5)

    async def navigate_with_retry(self, url: str, max_retries: int = 5) -> bool:
        """Navigate to URL with retry and extended timeouts for CI/CD."""
        for attempt in range(max_retries):
            try:
                logger.info(f"Navigating to {url} (attempt {attempt + 1}/{max_retries})")

                # Use longer timeout for initial page load (60s)
                await self.page.goto(url, timeout=60000, wait_until='domcontentloaded')

                # Wait for Cloudflare
                await self.wait_for_cloudflare()

                # Wait for network to be idle with longer timeout
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=30000)
                except Exception as e:
                    logger.debug(f"Network idle timeout, continuing anyway: {e}")

                # Verify page loaded by checking for content
                content = await self.page.content()
                if len(content) > 1000:  # Page has substantial content
                    logger.info(f"✓ Successfully loaded {url} ({len(content)} bytes)")
                    return True
                else:
                    logger.warning(f"Page content too short ({len(content)} bytes), retrying...")

            except Exception as e:
                logger.warning(f"Navigation failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    wait_time = min(2 ** attempt, 10)  # Cap at 10 seconds
                    logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)

        logger.error(f"Failed to load {url} after {max_retries} attempts")
        return False

    async def scrape_url(self, url: str, max_pages: int = 10) -> List[Dict]:
        """
        Scrape scholarships from a specific URL.

        Args:
            url: The URL to scrape
            max_pages: Maximum number of pages to scrape

        Returns:
            List of scholarship dictionaries
        """
        scholarships = []

        success = await self.navigate_with_retry(url)
        if not success:
            logger.error(f"Failed to load {url}")
            return scholarships

        page_number = 1

        while page_number <= max_pages:
            logger.info(f"Scraping page {page_number}...")

            content = await self.page.content()
            soup = BeautifulSoup(content, 'lxml')

            page_scholarships = self.parse_scholarships(soup)

            if not page_scholarships:
                logger.info("No scholarships found, stopping")
                break

            scholarships.extend(page_scholarships)
            logger.info(f"Found {len(page_scholarships)} scholarships on page {page_number}")

            # Try to go to next page
            has_next = await self.go_to_next_page()
            if not has_next:
                logger.info("No next page, stopping")
                break

            page_number += 1
            await asyncio.sleep(5)  # Delay between pages - increased to avoid rate limiting

        return scholarships

    def parse_scholarships(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse scholarships from HTML based on actual structure.

        HTML structure:
        <li>
            <h4><a href="...">Title</a></h4>
            <span class="text-success">Location</span>
            <span class="text-muted">about 22 hours ago</span>
            <p>Description</p>
        </li>
        """
        scholarships = []

        # Find all <li> elements that contain scholarships
        list_items = soup.find_all('li')

        logger.debug(f"Found {len(list_items)} <li> elements")

        for li in list_items:
            try:
                scholarship = self.extract_from_li(li)
                if scholarship:
                    scholarships.append(scholarship)
            except Exception as e:
                logger.debug(f"Error parsing li: {e}")
                continue

        return scholarships

    def extract_from_li(self, li) -> Optional[Dict]:
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
            url = urljoin(self.base_url, link['href'])

            # Extract university/school name
            # Look for <a> with href containing "/scholarships-at-"
            university = None
            all_links = li.find_all('a', href=True)
            for a in all_links:
                if '/scholarships-at-' in a.get('href', ''):
                    university = a.get_text(strip=True)
                    break

            # Extract location and country
            # Location is in <span class="text-success">
            # Country is in <a class="text-success"> with href="/scholarships-in-Country"
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

    async def go_to_next_page(self) -> bool:
        """Navigate to next page."""
        try:
            # Get current URL and first item to detect if page actually changed
            current_url = self.page.url
            first_items = await self.page.query_selector_all('li h5 a, li h4 a')
            old_first_url = await first_items[0].get_attribute('href') if first_items else None

            next_selectors = [
                'a[rel="next"]',
                'a.next',
                'a:has-text("Next")',
                '.pagination a:has-text("›")',
            ]

            for selector in next_selectors:
                try:
                    next_button = await self.page.query_selector(selector)
                    if next_button:
                        # Check if button is disabled
                        is_disabled = await next_button.get_attribute('disabled')
                        class_name = await next_button.get_attribute('class') or ''
                        if is_disabled or 'disabled' in class_name:
                            logger.debug(f"Next button is disabled")
                            return False

                        logger.debug(f"Found next button: {selector}")
                        await next_button.click()

                        # Wait for URL to change or content to update
                        try:
                            await self.page.wait_for_load_state('networkidle', timeout=30000)
                        except Exception as e:
                            logger.debug(f"Network idle timeout: {e}")

                        await asyncio.sleep(3)  # Give page time to settle

                        # Verify page actually changed
                        new_url = self.page.url
                        new_first_items = await self.page.query_selector_all('li h5 a, li h4 a')
                        new_first_url = await new_first_items[0].get_attribute('href') if new_first_items else None

                        if new_url != current_url or new_first_url != old_first_url:
                            logger.debug(f"Page changed: URL or content updated")
                            return True
                        else:
                            logger.warning(f"Page did not change after clicking next button")
                            return False

                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue

            logger.debug("No next button found")
            return False
        except Exception as e:
            logger.error(f"Error in pagination: {e}")
            return False

    @staticmethod
    def export_to_json(scholarships: List[Dict], filename: str = 'scholarships.json'):
        """
        Export scholarships to JSON file.

        Args:
            scholarships: List of scholarship dictionaries
            filename: Output filename
        """
        filepath = Path(filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(scholarships, f, ensure_ascii=False, indent=2)

        logger.info(f"Exported {len(scholarships)} scholarships to {filepath}")
        return str(filepath)

    @staticmethod
    def format_for_telegram(scholarships: List[Dict], per_page: int = 17) -> List[str]:
        """
        Format scholarships for Telegram messages.

        Args:
            scholarships: List of scholarship dictionaries
            per_page: Number of scholarships per page

        Returns:
            List of formatted message strings
        """
        messages = []

        for i in range(0, len(scholarships), per_page):
            page_scholarships = scholarships[i:i + per_page]

            message_parts = [f"📚 PhD Scholarships ({i + 1}-{i + len(page_scholarships)} of {len(scholarships)})\n"]

            for idx, sch in enumerate(page_scholarships, 1):
                title = sch.get('title', 'N/A')
                university = sch.get('university', '')
                location = sch.get('location', 'N/A')
                country = sch.get('country', '')
                location_str = f"{location}, {country}" if country else location

                time_str = sch.get('posted_time_text', 'N/A')
                desc = sch.get('description', 'No description')
                url = sch.get('url', '')

                # Truncate description
                if len(desc) > 100:
                    desc = desc[:97] + '...'

                # Build message
                msg = f"\n{idx}. {title}\n"
                if university:
                    msg += f"   🏛️ {university}\n"
                msg += f"   📍 {location_str}\n"
                msg += f"   ⏰ {time_str}\n"
                msg += f"   📝 {desc}\n"
                msg += f"   🔗 {url}\n"

                message_parts.append(msg)

            messages.append('\n'.join(message_parts))

        return messages


async def scrape_custom_url(url: str, output_file: str = None, max_pages: int = 10) -> List[Dict]:
    """
    Scrape a custom URL and optionally export to JSON.

    Args:
        url: URL to scrape
        output_file: Optional JSON output file
        max_pages: Maximum pages to scrape

    Returns:
        List of scholarships
    """
    async with ScholarshipScraperV2() as scraper:
        scholarships = await scraper.scrape_url(url, max_pages=max_pages)

        if output_file and scholarships:
            scraper.export_to_json(scholarships, output_file)

        return scholarships
