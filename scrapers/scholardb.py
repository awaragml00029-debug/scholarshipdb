"""Scraper for scholarshipdb.net (Cloudflare-protected via Playwright)."""
import asyncio
import random
import re
from datetime import datetime, timezone
from typing import List, Optional, Dict
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from loguru import logger
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

import config
from scrapers import BaseSource, FeedItem
from time_parser import parse_relative_time


def _build_proxy(proxy_url: Optional[str]) -> Optional[dict]:
    """Build Playwright proxy dict from URL.

    Chromium supports:
      - http://[user:pass@]host:port  → auth OK
      - socks5://host:port            → no auth only (auth socks5 is NOT supported)
    Authenticated socks5 should be tunnelled via gost before reaching here.
    """
    if not proxy_url:
        return None
    from urllib.parse import urlparse
    url = proxy_url.replace("socks5h://", "socks5://")
    parsed = urlparse(url)
    proxy: dict = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
    # Only pass credentials for HTTP proxies; socks5 auth is unsupported by Chromium
    if parsed.scheme.startswith("http") and parsed.username:
        proxy["username"] = parsed.username
    if parsed.scheme.startswith("http") and parsed.password:
        proxy["password"] = parsed.password
    return proxy

BASE_URL = "https://scholarshipdb.net"

EXCLUDE_KEYWORDS = [
    "last-24-hours", "last-3-days", "last-7-days", "last-30-days",
    "last-year", "this-week", "this-month", "filter", "category",
    "tag", "archive", "login", "register", "signup", "signin",
    "privacy", "terms", "contact", "about", "search", "home",
    "menu", "uni_job", "research_job",
]
REQUIRED_KEYWORDS = ["scholarship", "phd", "fellowship", "grant", "postdoc", "doctoral"]

# /jobs-in-/ items are only kept if the title contains one of these
JOB_ACADEMIC_KEYWORDS = ["phd", "postdoc", "fellowship", "doctoral", "researcher", "research position", "research fellow"]


class ScholardbSource(BaseSource):
    name = "scholarshipdb.net"

    def __init__(self, sources: List[Dict]):
        """
        sources: list of dicts with keys: url, label, max_pages
        """
        self.sources = sources
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.playwright = None

    async def __aenter__(self):
        await self._start()
        return self

    async def __aexit__(self, *_):
        await self._close()

    async def fetch(self) -> List[FeedItem]:
        async with self:
            all_items: List[FeedItem] = []
            seen_urls: set = set()
            for src in self.sources:
                label = src.get("label", src["url"])
                max_pages = src.get("max_pages", 5)
                logger.info(f"  Scraping: {label} (max {max_pages} pages)")
                items = await self._scrape_source(src["url"], label, max_pages)
                # deduplicate across sources
                new_items = [i for i in items if i.url not in seen_urls]
                seen_urls.update(i.url for i in new_items)
                all_items.extend(new_items)
                logger.info(f"  {label}: {len(new_items)} new items")
                await self._delay()
            return all_items

    # ── Browser lifecycle ──────────────────────────────────────────────────

    async def _start(self):
        logger.info("Starting Playwright browser...")
        self.playwright = await async_playwright().start()

        proxy = _build_proxy(config.PROXY_URL)

        self.browser = await self.playwright.chromium.launch(
            headless=config.HEADLESS,
            proxy=proxy,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-gpu",
                "--disable-software-rasterizer",
                "--disable-extensions",
            ],
        )

        self.context = await self.browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            timezone_id="America/New_York",
        )
        await self.context.set_extra_http_headers({
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        })

        self.page = await self.context.new_page()
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        """)
        logger.info("Browser ready")

    async def _close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    # ── Navigation ─────────────────────────────────────────────────────────

    async def _navigate(self, url: str) -> bool:
        for attempt in range(config.MAX_RETRIES):
            try:
                logger.info(f"GET {url} (attempt {attempt + 1})")
                await self.page.goto(url, timeout=config.TIMEOUT, wait_until="domcontentloaded")
                await self._wait_cloudflare()
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                except Exception:
                    pass  # networkidle may never fire on Cloudflare pages; content is still usable
                return True
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < config.MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
        logger.error(f"Failed to load {url}")
        return False

    async def _wait_cloudflare(self):
        # Wait up to 60s for Cloudflare challenge ("Just a moment..." / "Checking your browser") to clear
        for _ in range(20):
            title = await self.page.title()
            if title.lower() not in ("just a moment...", "checking your browser"):
                break
            logger.debug(f"Cloudflare challenge active ({title}), waiting...")
            await asyncio.sleep(3)
        await asyncio.sleep(2)

    async def _delay(self):
        await asyncio.sleep(random.uniform(config.DELAY_MIN, config.DELAY_MAX))

    # ── Scraping ───────────────────────────────────────────────────────────

    async def _scrape_source(self, url: str, label: str, max_pages: int) -> List[FeedItem]:
        items: List[FeedItem] = []
        ok = await self._navigate(url)
        if not ok:
            return items

        page_num = 1
        while page_num <= max_pages:
            content = await self.page.content()
            if page_num == 1:
                logger.info(f"    Page title: {await self.page.title()}")

            soup = BeautifulSoup(content, "lxml")
            page_items = self._parse_page(soup)

            if not page_items:
                logger.info("    No items on page, stopping")
                break

            items.extend(page_items)
            logger.info(f"    Page {page_num}/{max_pages}: {len(page_items)} items")

            if not await self._next_page():
                break
            page_num += 1
            await self._delay()

        return items

    async def _next_page(self) -> bool:
        selectors = [
            "a.next", "a[rel='next']", "a.pagination-next",
            ".pagination .next", "a:has-text('Next')",
            "a:has-text('›')", "a:has-text('→')",
        ]
        for sel in selectors:
            try:
                btn = await self.page.query_selector(sel)
                if btn:
                    await btn.click()
                    await self.page.wait_for_load_state("networkidle", timeout=10000)
                    return True
            except Exception:
                continue
        return False

    # ── Parsing ────────────────────────────────────────────────────────────

    def _parse_page(self, soup: BeautifulSoup) -> List[FeedItem]:
        # scholarshipdb.net: listing items have <h4> + <span class="text-muted"> (timestamp)
        # This combination is specific to actual listings, not nav/sidebar items
        li_items = [
            li for li in soup.find_all("li")
            if li.find("h4") and li.find("span", class_="text-muted")
        ]
        if li_items:
            items = [i for li in li_items if (i := self._parse_article(li))]
            if items:
                return items

        article_selectors = [
            "article.scholarship", "div.scholarship-item", "div.scholarship-card",
            "div.scholarship", "article.post", "div.post",
            "article", "div.listing-item", "div.item", "div.card",
            "article[class*='scholarship']", "div[class*='scholarship']",
            "div[class*='result']", "div[class*='item']", "div[class*='post']",
        ]

        articles = []
        for sel in article_selectors:
            articles = soup.select(sel)
            if articles:
                break

        if articles:
            items = []
            for art in articles:
                item = self._parse_article(art)
                if item:
                    items.append(item)
            if items:
                return items

        # Fallback: collect scholarship-related links directly
        all_links = soup.find_all("a", href=True)
        items = []
        seen = set()
        for link in all_links:
            href = link.get("href", "")
            url = urljoin(BASE_URL, href)
            if url in seen:
                continue
            item = self._item_from_link(link, url)
            if item:
                seen.add(url)
                items.append(item)
        return items

    def _parse_article(self, article) -> Optional[FeedItem]:
        try:
            # Title: h4 a
            link = article.select_one("h4 a")
            if not link or not link.get("href"):
                return None

            title = link.get_text(strip=True)
            url = urljoin(BASE_URL, link["href"])

            # Reject nav/category pages and short titles
            url_lower = url.lower()
            title_lower = title.lower()
            if len(title) < 5:
                return None
            if any(k in url_lower for k in EXCLUDE_KEYWORDS):
                return None
            # Must be a specific item page (slug after category segment)
            if len([p for p in url_lower.split("/") if p]) < 2:
                return None
            # /jobs-in-/ items: only keep if title contains academic keywords
            if "jobs-in-" in url_lower:
                if not any(k in title_lower for k in JOB_ACADEMIC_KEYWORDS):
                    return None

            extra: Dict[str, str] = {}

            # University: first <a> in the metadata div (div + div a:nth-child(1))
            univ = article.select_one("div + div a:nth-child(1)")
            if univ:
                extra["university"] = univ.get_text(strip=True)

            # Country (and city): .text-success
            country_elem = article.select_one(".text-success")
            if country_elem:
                extra["country"] = country_elem.get_text(strip=True)

            # Description: first <p>
            p = article.find("p")
            description = p.get_text(strip=True)[:300] if p else ""

            published = self._parse_posted_time(article)

            return FeedItem(
                title=title,
                url=url,
                description=description,
                published=published,
                source=self.name,
                extra=extra,
            )
        except Exception as e:
            logger.debug(f"Error parsing article: {e}")
            return None

    def _item_from_link(self, link, url: str) -> Optional[FeedItem]:
        title = link.get_text(strip=True)
        if not title or len(title) < 5:
            return None

        title_lower = title.lower()
        url_lower = url.lower()

        if any(k in title_lower or k in url_lower for k in EXCLUDE_KEYWORDS):
            return None
        if not any(k in url_lower for k in REQUIRED_KEYWORDS):
            return None

        return FeedItem(
            title=title,
            url=url,
            published=datetime.now(timezone.utc),
            source=self.name,
        )

    def _parse_posted_time(self, article) -> datetime:
        """Return post time from article content, or scrape time as fallback."""
        time_elem = article.find("time")
        if time_elem:
            dt_str = time_elem.get("datetime") or time_elem.get_text(strip=True)
            try:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except Exception:
                pass

        # text-muted is the proven class for scholarshipdb.net timestamps
        text_elem = article.find("span", class_="text-muted") or article.find(
            class_=lambda x: x and any(k in str(x).lower() for k in ["posted", "date", "time", "ago"])
        )
        if text_elem:
            text = text_elem.get_text(strip=True)
            if text:
                try:
                    return parse_relative_time(text)
                except Exception:
                    pass

        return datetime.now(timezone.utc)  # fallback: scrape time
