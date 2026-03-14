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

BASE_URL = "https://scholarshipdb.net"
LIST_URL = f"{BASE_URL}/phd-scholarships/"

EXCLUDE_KEYWORDS = [
    "last-24-hours", "last-3-days", "last-7-days", "last-30-days",
    "last-year", "this-week", "this-month", "filter", "category",
    "tag", "archive", "login", "register", "signup", "signin",
    "privacy", "terms", "contact", "about", "search", "home",
    "menu", "uni_job", "research_job",
]
REQUIRED_KEYWORDS = ["scholarship", "phd", "fellowship", "grant", "postdoc", "doctoral"]


class ScholardbSource(BaseSource):
    name = "scholarshipdb.net"

    def __init__(self):
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
            return await self._scrape_all_pages()

    # ── Browser lifecycle ──────────────────────────────────────────────────

    async def _start(self):
        logger.info("Starting Playwright browser...")
        self.playwright = await async_playwright().start()

        proxy_url = config.PROXY_URL.replace("socks5h://", "socks5://") if config.PROXY_URL else None
        proxy = {"server": proxy_url} if proxy_url else None

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

    async def _scrape_all_pages(self) -> List[FeedItem]:
        items: List[FeedItem] = []
        ok = await self._navigate(LIST_URL)
        if not ok:
            return items

        page_num = 1
        while True:
            content = await self.page.content()
            # Debug: log page title and save HTML on first page
            if page_num == 1:
                title = await self.page.title()
                logger.info(f"Page title: {title}")
                with open("debug_page.html", "w", encoding="utf-8") as f:
                    f.write(content)
                logger.info("Saved page HTML to debug_page.html")

            soup = BeautifulSoup(content, "lxml")
            page_items = self._parse_page(soup)

            if not page_items:
                logger.info("No items on page, stopping")
                break

            items.extend(page_items)
            logger.info(f"Page {page_num}: {len(page_items)} items (total {len(items)})")

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
        article_selectors = [
            "article.scholarship", "div.scholarship-item", "div.scholarship-card",
            "div.scholarship", "li.scholarship", "article.post", "div.post",
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
            title_elem = article.find(
                ["h2", "h3", "h4"],
                class_=lambda x: x and any(k in str(x).lower() for k in ["title", "heading", "post-title"]),
            ) or article.find(["h2", "h3", "h4"])

            if not title_elem:
                return None

            link = title_elem.find("a") or article.find("a")
            if not link or not link.get("href"):
                return None

            title = title_elem.get_text(strip=True)
            url = urljoin(BASE_URL, link["href"])

            extra: Dict[str, str] = {}

            univ = article.find(class_=lambda x: x and "university" in str(x).lower())
            if univ:
                extra["university"] = univ.get_text(strip=True)

            ctry = article.find(class_=lambda x: x and "country" in str(x).lower())
            if ctry:
                extra["country"] = ctry.get_text(strip=True)

            dl = article.find(class_=lambda x: x and "deadline" in str(x).lower())
            if dl:
                extra["deadline"] = dl.get_text(strip=True)

            desc_elem = article.find(
                class_=lambda x: x and any(k in str(x).lower() for k in ["excerpt", "summary", "description"])
            )
            description = desc_elem.get_text(strip=True)[:1000] if desc_elem else ""

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
            source=self.name,
        )

    def _parse_posted_time(self, article) -> Optional[datetime]:
        time_elem = article.find("time")
        if time_elem:
            dt_str = time_elem.get("datetime") or time_elem.get_text(strip=True)
            try:
                return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
            except Exception:
                pass

        text_elem = article.find(
            class_=lambda x: x and any(k in str(x).lower() for k in ["posted", "date", "time", "ago"])
        )
        if text_elem:
            text = text_elem.get_text(strip=True)
            if text:
                try:
                    return parse_relative_time(text)
                except Exception:
                    pass

        return None
