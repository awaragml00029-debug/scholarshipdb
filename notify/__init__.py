"""Notification backends."""
import json
import os
from typing import List

from loguru import logger

import config
from scrapers import FeedItem


def load_notified_urls() -> set:
    if os.path.exists(config.NOTIFIED_URLS_FILE):
        try:
            with open(config.NOTIFIED_URLS_FILE) as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()


def save_notified_urls(urls: set, max_keep: int = 2000):
    """Persist urls set, capping at max_keep to prevent unbounded growth."""
    os.makedirs(os.path.dirname(config.NOTIFIED_URLS_FILE) or ".", exist_ok=True)
    url_list = list(urls)[-max_keep:]
    with open(config.NOTIFIED_URLS_FILE, "w") as f:
        json.dump(url_list, f)


def notify_new_items(all_items: List[FeedItem]) -> int:
    """
    Compare all_items against previously notified URLs.
    If new items exist and Telegram is configured, create a Telegraph article
    and send one Telegram message with the link.
    Returns number of new items sent (0 if skipped/failed).
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.info("Telegram not configured — skipping notification.")
        return 0

    notified = load_notified_urls()
    new_items = [i for i in all_items if i.url not in notified]

    if not new_items:
        logger.info("No new items since last notification.")
        # Still update the notified set with current items (catches first-run edge case)
        save_notified_urls(notified | {i.url for i in all_items})
        return 0

    logger.info(f"Notifying {len(new_items)} new items via Telegram...")

    try:
        from notify.telegraph import get_or_create_token, create_page
        from notify.telegram import send_message

        token = get_or_create_token(config.TELEGRAPH_TOKEN_FILE)
        page_url = create_page(new_items, token)
        logger.info(f"Telegraph page: {page_url}")

        text = (
            f"📚 <b>{len(new_items)} new PhD scholarships</b>\n\n"
            f"<a href=\"{page_url}\">Read all on Telegra.ph →</a>"
        )
        ok = send_message(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, text)

        if ok:
            # Mark all current items as notified
            save_notified_urls(notified | {i.url for i in all_items})
            return len(new_items)
    except Exception as e:
        logger.error(f"Notification failed: {e}")

    return 0
