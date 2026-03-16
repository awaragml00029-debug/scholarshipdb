"""Create a Telegra.ph article from FeedItems and return its public URL."""
import json
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


def get_or_create_token(token_file: str) -> str:
    """Load stored Telegraph access token, or create a new anonymous account."""
    import os
    if os.path.exists(token_file):
        try:
            with open(token_file) as f:
                token = json.load(f).get("access_token")
            if token:
                return token
        except Exception:
            pass

    logger.info("Creating new Telegraph account...")
    result = _post("createAccount", {
        "short_name": "ScholarFeed",
        "author_name": "Scholar Feed Bot",
    })
    token = result["result"]["access_token"]
    os.makedirs(os.path.dirname(token_file) or ".", exist_ok=True)
    with open(token_file, "w") as f:
        json.dump({"access_token": token}, f)
    logger.info(f"Telegraph token saved → {token_file}")
    return token


MAX_ITEMS_PER_PAGE = 60  # total across all sections


def create_page(items: List[FeedItem], token: str) -> str:
    """Build a Telegraph page grouped by source label, newest first."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    min_dt = datetime.min.replace(tzinfo=timezone.utc)

    # Sort newest first, cap total
    items = sorted(items, key=lambda x: x.published or min_dt, reverse=True)[:MAX_ITEMS_PER_PAGE]

    # Group by label (preserving insertion order = newest-first within each group)
    groups: dict = defaultdict(list)
    for item in items:
        label = item.extra.get("label", "Other")
        groups[label].append(item)

    content: list = []

    for label, group_items in groups.items():
        # Section header
        content.append({"tag": "h3", "children": [f"📍 {label} ({len(group_items)})"]})

        for idx, item in enumerate(group_items, 1):
            univ = item.extra.get("university", "")
            # Format: N. University | Title (linked)
            prefix = f"{idx}. {univ} | " if univ else f"{idx}. "
            content.append({
                "tag": "p",
                "children": [
                    prefix,
                    {"tag": "a", "attrs": {"href": item.url}, "children": [item.title]},
                ],
            })

        content.append({"tag": "hr"})

    total = sum(len(v) for v in groups.values())
    result = _post("createPage", {
        "access_token": token,
        "title": f"PhD Scholarships — {date_str} ({total} new)",
        "author_name": "Scholar Feed Bot",
        "content": content,
        "return_content": False,
    })
    return result["result"]["url"]
