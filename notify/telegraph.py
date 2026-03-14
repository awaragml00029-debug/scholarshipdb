"""Create a Telegra.ph article from FeedItems and return its public URL."""
import json
import urllib.request
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


def create_page(items: List[FeedItem], token: str) -> str:
    """Build a Telegraph page from items, return public URL."""
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    content: list = []

    for item in items:
        # Title as hyperlink
        content.append({
            "tag": "p",
            "children": [{"tag": "a", "attrs": {"href": item.url}, "children": [item.title]}],
        })

        # Metadata line: university · location · country
        meta_parts = [
            item.extra.get("university"),
            item.extra.get("location"),
            item.extra.get("country"),
        ]
        meta = " · ".join(p for p in meta_parts if p)
        if meta:
            content.append({"tag": "p", "children": [meta]})

        # Short description
        if item.description:
            content.append({"tag": "p", "children": [item.description[:300]]})

        content.append({"tag": "hr"})

    result = _post("createPage", {
        "access_token": token,
        "title": f"PhD Scholarships — {date_str} ({len(items)} new)",
        "author_name": "Scholar Feed Bot",
        "content": content,
        "return_content": False,
    })
    return result["result"]["url"]
