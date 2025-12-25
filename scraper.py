"""Web scraper for scholarshipdb.net using Playwright."""
import asyncio
import random
import re
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page, Browser, BrowserContext
from bs4 import BeautifulSoup
from loguru import logger

from config import settings


class ScholarshipScraper:
    """Scraper for PhD scholarships from scholarshipdb.net."""

    def __init__(self):
        self.base_url = settings.base_url
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def start(self):
        """Initialize the browser."""
        logger.info("Starting Playwright browser...")
        self.playwright = await async_playwright().start()

        # Launch browser with options to bypass Cloudflare and work in server environment
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
                '--single-process',  # Important for Docker/server environments
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
            ],
            chromium_sandbox=False,  # Disable sandbox for server environments
        )

        # Create context with realistic user agent and viewport
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )

        # Add extra headers
        await self.context.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        })

        self.page = await self.context.new_page()

        # Mask automation indicators
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

        logger.info("Browser started successfully")

    async def close(self):
        """Close the browser."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        logger.info("Browser closed")

    async def wait_for_cloudflare(self):
        """Wait for Cloudflare challenge to complete."""
        logger.info("Waiting for Cloudflare challenge...")
        try:
            # Wait for common Cloudflare challenge elements to disappear
            await self.page.wait_for_selector(
                'text="Checking your browser"',
                state='detached',
                timeout=30000
            )
        except Exception:
            # If the selector doesn't exist, that's fine
            pass

        # Additional wait to ensure page is fully loaded
        await asyncio.sleep(3)
        logger.info("Cloudflare challenge passed")

    async def random_delay(self):
        """Add random delay between requests."""
        delay = random.uniform(settings.scraper_delay_min, settings.scraper_delay_max)
        logger.debug(f"Waiting {delay:.2f} seconds...")
        await asyncio.sleep(delay)

    async def navigate_with_retry(self, url: str, max_retries: int = None) -> bool:
        """Navigate to URL with retry logic."""
        if max_retries is None:
            max_retries = settings.scraper_max_retries

        for attempt in range(max_retries):
            try:
                logger.info(f"Navigating to {url} (attempt {attempt + 1}/{max_retries})")
                await self.page.goto(url, timeout=settings.scraper_timeout, wait_until='domcontentloaded')
                await self.wait_for_cloudflare()
                await self.page.wait_for_load_state('networkidle', timeout=10000)
                return True
            except Exception as e:
                logger.warning(f"Navigation attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to navigate to {url} after {max_retries} attempts")
                    return False

    async def get_phd_scholarships_list(self) -> List[Dict]:
        """Get list of PhD scholarships from the main page."""
        scholarships = []

        # Navigate to PhD scholarships page
        phd_url = urljoin(self.base_url, '/phd-scholarships/')
        success = await self.navigate_with_retry(phd_url)

        if not success:
            logger.error("Failed to load PhD scholarships page")
            return scholarships

        page_number = 1
        max_pages = 50  # Safety limit

        while page_number <= max_pages:
            logger.info(f"Scraping page {page_number}...")

            # Get page content
            content = await self.page.content()
            soup = BeautifulSoup(content, 'lxml')

            # Parse scholarship listings
            page_scholarships = self.parse_scholarship_list(soup)

            if not page_scholarships:
                logger.info("No more scholarships found, stopping pagination")
                break

            scholarships.extend(page_scholarships)
            logger.info(f"Found {len(page_scholarships)} scholarships on page {page_number}")

            # Check for next page
            has_next = await self.go_to_next_page()
            if not has_next:
                logger.info("No next page found, stopping pagination")
                break

            page_number += 1
            await self.random_delay()

        return scholarships

    def parse_scholarship_list(self, soup: BeautifulSoup) -> List[Dict]:
        """Parse scholarship listings from the page."""
        scholarships = []

        # Expanded list of common selectors for scholarship listing pages
        article_selectors = [
            # Specific scholarship selectors
            'article.scholarship',
            'div.scholarship-item',
            'div.scholarship-card',
            'div.scholarship',
            'li.scholarship',
            # Post/article selectors
            'article.post',
            'div.post',
            'article',
            # Generic listing selectors
            'div.listing-item',
            'div.item',
            'div.card',
            'li.item',
            # Container-based selectors
            '.scholarship-list > div',
            '.scholarships > div',
            '.results > div',
            '.list > div',
            '.items > div',
            # Attribute-based selectors
            'article[class*="scholarship"]',
            'div[class*="scholarship"]',
            'div[class*="result"]',
            'div[class*="item"]',
            'div[class*="post"]',
            # Table-based layouts
            'table.scholarships tr',
            'tbody tr',
            # List-based layouts
            'ul.scholarships li',
            'ul.list li',
        ]

        articles = []
        selector_used = None

        for selector in article_selectors:
            try:
                articles = soup.select(selector)
                if articles and len(articles) > 0:
                    selector_used = selector
                    logger.info(f"Found {len(articles)} elements with selector: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Selector '{selector}' failed: {e}")
                continue

        if not articles:
            logger.warning("No articles found with any known selector")
            logger.debug("Page structure analysis:")

            # Try to find any links that might be scholarships
            all_links = soup.find_all('a', href=True)
            logger.debug(f"Found {len(all_links)} total links on page")

            # Look for scholarship-related links
            scholarship_links = [
                link for link in all_links
                if any(keyword in link.get('href', '').lower()
                      for keyword in ['scholarship', 'phd', 'fellowship', 'grant'])
            ]

            if scholarship_links:
                logger.info(f"Found {len(scholarship_links)} scholarship-related links")
                # Try to extract from links directly
                for link in scholarship_links[:20]:  # Limit to first 20
                    try:
                        scholarship_data = self.extract_from_link(link)
                        if scholarship_data:
                            scholarships.append(scholarship_data)
                    except Exception as e:
                        logger.debug(f"Error extracting from link: {e}")
                        continue

                return scholarships

        for article in articles:
            try:
                scholarship_data = self.extract_scholarship_data(article)
                if scholarship_data:
                    scholarships.append(scholarship_data)
            except Exception as e:
                logger.error(f"Error parsing scholarship: {e}")
                continue

        logger.info(f"Successfully parsed {len(scholarships)} scholarships")
        return scholarships

    def extract_scholarship_data(self, article) -> Optional[Dict]:
        """Extract scholarship data from an article element."""
        try:
            # Extract title and URL
            title_elem = article.find(['h2', 'h3', 'h4'], class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['title', 'heading', 'post-title']
            ))
            if not title_elem:
                title_elem = article.find(['h2', 'h3', 'h4'])

            if not title_elem:
                return None

            link = title_elem.find('a')
            if not link:
                link = article.find('a')

            if not link or not link.get('href'):
                return None

            title = title_elem.get_text(strip=True)
            url = urljoin(self.base_url, link['href'])

            # Extract other fields
            data = {
                'title': title,
                'url': url,
                'source_id': self.extract_id_from_url(url),
            }

            # Try to extract additional information from the listing
            text_content = article.get_text()

            # Extract university (common patterns)
            university_elem = article.find(class_=lambda x: x and 'university' in str(x).lower())
            if university_elem:
                data['university'] = university_elem.get_text(strip=True)

            # Extract country
            country_elem = article.find(class_=lambda x: x and 'country' in str(x).lower())
            if country_elem:
                data['country'] = country_elem.get_text(strip=True)

            # Extract deadline text
            deadline_elem = article.find(class_=lambda x: x and 'deadline' in str(x).lower())
            if deadline_elem:
                data['application_deadline_text'] = deadline_elem.get_text(strip=True)

            # Extract description/excerpt
            desc_elem = article.find(class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['excerpt', 'summary', 'description']
            ))
            if desc_elem:
                data['description'] = desc_elem.get_text(strip=True)[:1000]

            return data

        except Exception as e:
            logger.error(f"Error extracting scholarship data: {e}")
            return None

    def extract_from_link(self, link) -> Optional[Dict]:
        """Extract scholarship data from a link element (fallback method)."""
        try:
            href = link.get('href', '')
            if not href:
                return None

            # Get the full URL
            url = urljoin(self.base_url, href)

            # Get link text as title
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                return None

            # Create basic scholarship data
            data = {
                'title': title,
                'url': url,
                'source_id': self.extract_id_from_url(url),
            }

            # Try to find parent container with more info
            parent = link.find_parent(['div', 'article', 'li', 'tr'])
            if parent:
                text = parent.get_text()

                # Look for country
                countries = ['USA', 'UK', 'Canada', 'Australia', 'Germany', 'France', 'Netherlands']
                for country in countries:
                    if country in text:
                        data['country'] = country
                        break

                # Look for deadline
                if 'deadline' in text.lower():
                    deadline_text = text[text.lower().find('deadline'):text.lower().find('deadline')+50]
                    data['application_deadline_text'] = deadline_text.strip()

            logger.debug(f"Extracted from link: {title[:50]}")
            return data

        except Exception as e:
            logger.debug(f"Error extracting from link: {e}")
            return None

    def extract_id_from_url(self, url: str) -> str:
        """Extract unique ID from URL."""
        # Try to extract post ID from URL patterns
        patterns = [
            r'/(\d+)/?$',  # Ending with number
            r'[?&]p=(\d+)',  # WordPress post ID
            r'/([^/]+)/?$',  # Last URL segment
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        # Fallback: use the full URL as ID
        return url.split('/')[-2] if url.endswith('/') else url.split('/')[-1]

    async def go_to_next_page(self) -> bool:
        """Navigate to the next page of results."""
        try:
            # Common pagination selectors
            next_selectors = [
                'a.next',
                'a[rel="next"]',
                'a.pagination-next',
                '.pagination .next',
                'a:has-text("Next")',
                'a:has-text("›")',
                'a:has-text("→")',
            ]

            for selector in next_selectors:
                try:
                    next_button = await self.page.query_selector(selector)
                    if next_button:
                        logger.debug(f"Found next button with selector: {selector}")
                        await next_button.click()
                        await self.page.wait_for_load_state('networkidle', timeout=10000)
                        return True
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False

    async def get_scholarship_details(self, url: str) -> Dict:
        """Get detailed information for a specific scholarship."""
        logger.info(f"Fetching details for: {url}")

        success = await self.navigate_with_retry(url)
        if not success:
            return {}

        content = await self.page.content()
        soup = BeautifulSoup(content, 'lxml')

        details = self.parse_scholarship_details(soup)
        return details

    def parse_scholarship_details(self, soup: BeautifulSoup) -> Dict:
        """Parse detailed scholarship information from the detail page."""
        details = {}

        try:
            # Extract main content
            main_content = soup.find(['article', 'main', 'div'], class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['content', 'entry', 'post', 'article']
            ))

            if not main_content:
                main_content = soup

            # Title
            title = main_content.find(['h1', 'h2'])
            if title:
                details['title'] = title.get_text(strip=True)

            # Description
            content_div = main_content.find(['div', 'section'], class_=lambda x: x and any(
                keyword in str(x).lower() for keyword in ['content', 'entry-content', 'description']
            ))
            if content_div:
                details['description'] = content_div.get_text(strip=True)[:5000]

            # Look for structured information
            # This is highly dependent on the actual site structure
            info_sections = main_content.find_all(['dl', 'table', 'ul'])

            for section in info_sections:
                text = section.get_text().lower()

                if 'university' in text or 'institution' in text:
                    details['university'] = self.extract_field_value(section, ['university', 'institution'])

                if 'country' in text or 'location' in text:
                    details['country'] = self.extract_field_value(section, ['country', 'location'])

                if 'deadline' in text:
                    details['application_deadline_text'] = self.extract_field_value(section, ['deadline', 'apply by'])

                if 'field' in text or 'subject' in text:
                    details['field_of_study'] = self.extract_field_value(section, ['field', 'subject', 'discipline'])

                if 'funding' in text or 'amount' in text:
                    details['funding_type'] = self.extract_field_value(section, ['funding', 'amount', 'value'])

            # Application URL
            apply_link = main_content.find('a', text=re.compile(r'apply|application', re.I))
            if apply_link:
                details['application_url'] = urljoin(self.base_url, apply_link.get('href', ''))

        except Exception as e:
            logger.error(f"Error parsing scholarship details: {e}")

        return details

    def extract_field_value(self, element, keywords: List[str]) -> Optional[str]:
        """Extract field value from a structured element."""
        text = element.get_text()

        for keyword in keywords:
            pattern = rf'{keyword}\s*:?\s*(.+?)(?:\n|$)'
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None
