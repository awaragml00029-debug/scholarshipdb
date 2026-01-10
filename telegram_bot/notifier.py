#!/usr/bin/env python3
"""
Notification module for sending scholarship alerts.

Features:
- Real-time notifications after scraping
- Daily digest summaries
- Filter-based notifications
- Deduplication to avoid repeat messages
"""
import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.error import TelegramError
from loguru import logger

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
OWNER_ID = int(os.getenv('TELEGRAM_OWNER_ID', '0'))
DATA_DIR = Path(os.getenv('DATA_DIR', 'data'))
BOT_DATA_DIR = Path(os.getenv('BOT_DATA_DIR', 'telegram_bot/data'))

# Rate limiting
MESSAGES_PER_SECOND = 1
MAX_MESSAGES_PER_BATCH = 30


def load_json(file_path: Path, default=None):
    """Load JSON file with default fallback."""
    if default is None:
        default = {}
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
    return default


def save_json(file_path: Path, data):
    """Save data to JSON file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")


def get_sent_ids() -> set:
    """Get set of already sent scholarship URLs."""
    sent_file = BOT_DATA_DIR / 'sent_scholarships.json'
    data = load_json(sent_file, {'sent': []})
    return set(data.get('sent', []))


def mark_as_sent(urls: List[str]):
    """Mark scholarships as sent."""
    sent_file = BOT_DATA_DIR / 'sent_scholarships.json'
    data = load_json(sent_file, {'sent': []})
    sent = set(data.get('sent', []))
    sent.update(urls)
    # Keep only last 2000 entries
    if len(sent) > 2000:
        sent = set(list(sent)[-2000:])
    save_json(sent_file, {'sent': list(sent), 'last_updated': datetime.now(timezone.utc).isoformat()})


def get_filters() -> dict:
    """Get current filter configuration."""
    filters_file = BOT_DATA_DIR / 'filters.json'
    default_filters = {
        'countries': [],
        'keywords': [],
        'exclude_keywords': ['undergraduate', 'bachelor'],
        'enabled': True
    }
    return load_json(filters_file, default_filters)


def matches_filters(scholarship: dict, filters_config: dict) -> bool:
    """Check if a scholarship matches the current filters."""
    if not filters_config.get('enabled', True):
        return True

    # Handle None values safely
    title = (scholarship.get('title') or '').lower()
    location = (scholarship.get('location') or '').lower()
    source_label = (scholarship.get('source_label') or '').lower()
    country = (scholarship.get('country') or '').lower()

    # Check exclude keywords first
    for keyword in filters_config.get('exclude_keywords', []):
        if keyword.lower() in title:
            return False

    # Check country filter
    countries = filters_config.get('countries', [])
    if countries:
        country_match = any(
            c.lower() in location or c.lower() in source_label or c.lower() in country
            for c in countries
        )
        if not country_match:
            return False

    # Check keyword filter
    keywords = filters_config.get('keywords', [])
    if keywords:
        keyword_match = any(k.lower() in title for k in keywords)
        if not keyword_match:
            return False

    return True


def make_hashtag(text: str) -> str:
    """Convert text to a valid hashtag."""
    if not text:
        return ''
    clean = ''.join(c for c in text if c.isalnum() or c == ' ')
    return '#' + clean.replace(' ', '')


def format_scholarship_message(scholarship: dict) -> str:
    """Format a scholarship for Telegram message."""
    title = scholarship.get('title') or 'Unknown'
    url = scholarship.get('url') or '#'
    location = scholarship.get('location') or ''
    university = scholarship.get('university') or ''
    posted = scholarship.get('posted_time_text') or scholarship.get('posted_time') or ''
    source = scholarship.get('source_label') or ''
    country = scholarship.get('country') or ''

    if university and university not in location:
        location = f"{university}, {location}" if location else university
    if not location:
        location = country or 'Unknown'

    # Build hashtags
    tags = []
    if source:
        tags.append(make_hashtag(source))
    if country:
        tags.append(make_hashtag(country))
    tags_str = ' '.join(tags) if tags else ''

    message = f"<b>{title}</b>\n\n"
    message += f"<b>Location:</b> {location}\n"

    if source:
        message += f"<b>Category:</b> {source}\n"

    if country and country not in location:
        message += f"<b>Country:</b> {country}\n"

    if posted:
        message += f"<b>Posted:</b> {posted}\n"

    # Add hashtags
    if tags_str:
        message += f"\n{tags_str}\n"

    message += f"\n<a href=\"{url}\">View Details</a>"

    return message


def get_scholarship_keyboard(url: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for scholarship message."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Apply", url=url),
            InlineKeyboardButton("Save", callback_data=f"save:{url[:60]}"),
        ]
    ])


async def send_new_scholarships(bot: Optional[Bot] = None) -> int:
    """
    Send notifications for new scholarships.

    Args:
        bot: Telegram Bot instance. If None, creates one from BOT_TOKEN.

    Returns:
        Number of scholarships sent.
    """
    if not BOT_TOKEN and not bot:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return 0

    if not OWNER_ID:
        logger.error("TELEGRAM_OWNER_ID not set")
        return 0

    # Create bot if not provided
    if bot is None:
        bot = Bot(token=BOT_TOKEN)

    # Load scholarships
    combined_file = DATA_DIR / 'all_scholarships.json'
    if not combined_file.exists():
        logger.warning("No scholarship data file found")
        return 0

    try:
        with open(combined_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            scholarships = data.get('scholarships', [])
    except Exception as e:
        logger.error(f"Error loading scholarships: {e}")
        return 0

    # Get sent IDs and filters
    sent_ids = get_sent_ids()
    filters_config = get_filters()

    # Find new scholarships that match filters
    new_scholarships = [
        s for s in scholarships
        if s.get('url') not in sent_ids and matches_filters(s, filters_config)
    ]

    if not new_scholarships:
        logger.info("No new scholarships to send")
        return 0

    logger.info(f"Found {len(new_scholarships)} new scholarships matching filters")

    # Limit batch size
    to_send = new_scholarships[:MAX_MESSAGES_PER_BATCH]
    sent_count = 0
    sent_urls = []

    # Send header message
    try:
        header = f"<b>New Scholarships Found ({len(to_send)})</b>\n"
        if len(new_scholarships) > MAX_MESSAGES_PER_BATCH:
            header += f"<i>Showing first {MAX_MESSAGES_PER_BATCH} of {len(new_scholarships)}</i>"

        await bot.send_message(
            chat_id=OWNER_ID,
            text=header,
            parse_mode=ParseMode.HTML
        )
        await asyncio.sleep(1 / MESSAGES_PER_SECOND)
    except TelegramError as e:
        logger.error(f"Failed to send header: {e}")

    # Send each scholarship
    for scholarship in to_send:
        try:
            message = format_scholarship_message(scholarship)
            keyboard = get_scholarship_keyboard(scholarship.get('url', '#'))

            await bot.send_message(
                chat_id=OWNER_ID,
                text=message,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
                disable_web_page_preview=True
            )

            sent_count += 1
            sent_urls.append(scholarship.get('url'))
            await asyncio.sleep(1 / MESSAGES_PER_SECOND)

        except TelegramError as e:
            logger.error(f"Failed to send scholarship: {e}")
            continue

    # Mark as sent
    if sent_urls:
        mark_as_sent(sent_urls)

    logger.info(f"Sent {sent_count} scholarship notifications")
    return sent_count


async def send_daily_digest(bot: Optional[Bot] = None) -> int:
    """
    Send daily digest of all new scholarships.

    Args:
        bot: Telegram Bot instance.

    Returns:
        Number of scholarships in digest.
    """
    if not BOT_TOKEN and not bot:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        return 0

    if not OWNER_ID:
        logger.error("TELEGRAM_OWNER_ID not set")
        return 0

    if bot is None:
        bot = Bot(token=BOT_TOKEN)

    # Load scholarships
    combined_file = DATA_DIR / 'all_scholarships.json'
    if not combined_file.exists():
        return 0

    try:
        with open(combined_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            scholarships = data.get('scholarships', [])
            generated_at = data.get('generated_at', '')
    except Exception as e:
        logger.error(f"Error loading scholarships: {e}")
        return 0

    filters_config = get_filters()

    # Get filtered scholarships
    filtered = [s for s in scholarships if matches_filters(s, filters_config)][:50]

    if not filtered:
        return 0

    # Group by source
    by_source = {}
    for s in filtered:
        source = s.get('source_label', 'Other')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(s)

    # Build digest message
    digest = f"<b>Daily Scholarship Digest</b>\n"
    digest += f"<i>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</i>\n\n"
    digest += f"<b>Total: {len(filtered)} scholarships</b>\n\n"

    for source, items in by_source.items():
        digest += f"<b>{source}</b>: {len(items)}\n"

    digest += f"\n<i>Use /latest to see details</i>"

    try:
        await bot.send_message(
            chat_id=OWNER_ID,
            text=digest,
            parse_mode=ParseMode.HTML
        )
        return len(filtered)
    except TelegramError as e:
        logger.error(f"Failed to send digest: {e}")
        return 0


async def notify_after_scrape():
    """
    Called after scraping completes to send notifications.
    This is the main integration point with batch_scrape.py.
    """
    if not BOT_TOKEN:
        logger.info("Telegram notifications disabled (no BOT_TOKEN)")
        return

    logger.info("Sending Telegram notifications...")
    count = await send_new_scholarships()
    logger.info(f"Telegram: sent {count} notifications")


def run_notify():
    """Synchronous wrapper for notify_after_scrape."""
    asyncio.run(notify_after_scrape())


if __name__ == '__main__':
    # Test run
    asyncio.run(notify_after_scrape())
