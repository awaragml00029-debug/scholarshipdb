"""Publish/update a Telegra.ph article from FeedItems and return its public URL."""
import json
import os
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from typing import List, Optional

from loguru import logger

from scrapers import FeedItem

_API = "https://api.telegra.ph"


def _post(endpoint: str, data: dict) -> dict:
    body = json.dumps(data).encode()
    req = urllib.request.Request(
        f"{_API}/{endpoint}",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def _load_token_file(token_file: str) -> dict:
    if os.path.exists(token_file):
        try:
            with open(token_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_token_file(token_file: str, data: dict):
    os.makedirs(os.path.dirname(token_file) or ".", exist_ok=True)
    with open(token_file, "w") as f:
        json.dump(data, f)


def get_or_create_token(token_file: str) -> str:
    """Load stored Telegraph access token, or create a new anonymous account."""
    stored = _load_token_file(token_file)
    if stored.get("access_token"):
        return stored["access_token"]

    logger.info("Creating new Telegraph account...")
    result = _post("createAccount", {
        "short_name": "ScholarFeed",
        "author_name": "Scholar Feed Bot",
    })
    token = result["result"]["access_token"]
    _save_token_file(token_file, {"access_token": token})
    logger.info(f"Telegraph token saved → {token_file}")
    return token


MAX_ITEMS_PER_PAGE = 60


def _load_translation_cache(cache_file: str = "docs/translations_cache.json") -> dict:
    if os.path.exists(cache_file):
        try:
            with open(cache_file) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _build_content(items: List[FeedItem], translations: dict) -> tuple[list, int]:
    """Build Telegraph content nodes grouped by label. Returns (content, total)."""
    min_dt = datetime.min.replace(tzinfo=timezone.utc)
    items = sorted(items, key=lambda x: x.published or min_dt, reverse=True)[:MAX_ITEMS_PER_PAGE]

    groups: dict = defaultdict(list)
    for item in items:
        groups[item.extra.get("label", "Other")].append(item)

    content: list = []
    for label, group_items in groups.items():
        content.append({"tag": "h3", "children": [f"📍 {label} ({len(group_items)})"]})
        for idx, item in enumerate(group_items, 1):
            univ = item.extra.get("university", "")
            zh_title = translations.get(item.title, "")
            pub_date = item.published.strftime("%m-%d") if item.published else ""

            parts = [f"{idx}."]
            if univ:
                parts.append(univ)
            if zh_title:
                parts.append(zh_title)
            if pub_date:
                parts.append(pub_date)
            prefix = " | ".join(parts) + " | "

            content.append({
                "tag": "p",
                "children": [
                    prefix,
                    {"tag": "a", "attrs": {"href": item.url}, "children": [item.title]},
                ],
            })
        content.append({"tag": "hr"})

    return content, sum(len(v) for v in groups.values())


def publish_page(items: List[FeedItem], token: str, token_file: str) -> str:
    """Create or update the daily Telegraph page. Returns public URL."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    translations = _load_translation_cache()
    content, total = _build_content(items, translations)
    title = f"PhD Scholarships — {date_str} ({total} new)"

    stored = _load_token_file(token_file)
    page_path = stored.get("page_path")

    if page_path:
        # Update existing page
        logger.info(f"Updating Telegraph page: {page_path}")
        result = _post("editPage", {
            "access_token": token,
            "path": page_path,
            "title": title,
            "author_name": "Scholar Feed Bot",
            "content": content,
            "return_content": False,
        })
    else:
        # First run: create page and save path
        logger.info("Creating new Telegraph page...")
        result = _post("createPage", {
            "access_token": token,
            "title": title,
            "author_name": "Scholar Feed Bot",
            "content": content,
            "return_content": False,
        })
        page_path = result["result"]["path"]
        stored["page_path"] = page_path
        _save_token_file(token_file, stored)
        logger.info(f"Telegraph page path saved: {page_path}")

    return result["result"]["url"]
