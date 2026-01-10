#!/usr/bin/env python3
"""
Telegram Bot for PhD Scholarship Notifications.

Features:
- Real-time notifications for new scholarships
- Daily digest summaries
- Interactive commands (/latest, /search, /filters, etc.)
- Inline buttons for quick actions
- Custom filter management
"""
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode
from loguru import logger

# Configuration
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
OWNER_ID = int(os.getenv('TELEGRAM_OWNER_ID', '0'))
DATA_DIR = Path(os.getenv('DATA_DIR', 'data'))
BOT_DATA_DIR = Path(os.getenv('BOT_DATA_DIR', 'telegram_bot/data'))
GITHUB_PAGES_URL = os.getenv('GITHUB_PAGES_URL', 'https://awaragml00029-debug.github.io/scholarshipdb')

# Ensure data directory exists
BOT_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Files for persistence
SENT_FILE = BOT_DATA_DIR / 'sent_scholarships.json'
SAVED_FILE = BOT_DATA_DIR / 'saved_scholarships.json'
FILTERS_FILE = BOT_DATA_DIR / 'filters.json'


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
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")


def get_filters() -> dict:
    """Get current filter configuration."""
    default_filters = {
        'countries': [],  # Empty = all countries
        'keywords': [],   # Empty = no keyword filter
        'exclude_keywords': ['undergraduate', 'bachelor'],
        'enabled': True
    }
    return load_json(FILTERS_FILE, default_filters)


def save_filters(filters_data: dict):
    """Save filter configuration."""
    save_json(FILTERS_FILE, filters_data)


def get_sent_ids() -> set:
    """Get set of already sent scholarship URLs."""
    data = load_json(SENT_FILE, {'sent': []})
    return set(data.get('sent', []))


def mark_as_sent(url: str):
    """Mark a scholarship as sent."""
    data = load_json(SENT_FILE, {'sent': []})
    sent = set(data.get('sent', []))
    sent.add(url)
    # Keep only last 2000 entries to prevent file bloat
    if len(sent) > 2000:
        sent = set(list(sent)[-2000:])
    save_json(SENT_FILE, {'sent': list(sent)})


def get_saved_scholarships() -> list:
    """Get list of saved/bookmarked scholarships."""
    data = load_json(SAVED_FILE, {'saved': []})
    return data.get('saved', [])


def save_scholarship_bookmark(scholarship: dict):
    """Save a scholarship to bookmarks."""
    data = load_json(SAVED_FILE, {'saved': []})
    saved = data.get('saved', [])
    # Check if already saved
    if not any(s.get('url') == scholarship.get('url') for s in saved):
        saved.insert(0, scholarship)
        # Keep only last 100
        saved = saved[:100]
        save_json(SAVED_FILE, {'saved': saved})
        return True
    return False


def remove_bookmark(url: str) -> bool:
    """Remove a scholarship from bookmarks."""
    data = load_json(SAVED_FILE, {'saved': []})
    saved = data.get('saved', [])
    original_len = len(saved)
    saved = [s for s in saved if s.get('url') != url]
    if len(saved) < original_len:
        save_json(SAVED_FILE, {'saved': saved})
        return True
    return False


def load_scholarships() -> list:
    """Load all scholarships from the combined JSON file."""
    combined_file = DATA_DIR / 'all_scholarships.json'
    if not combined_file.exists():
        return []
    try:
        with open(combined_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('scholarships', [])
    except Exception as e:
        logger.error(f"Error loading scholarships: {e}")
        return []


def matches_filters(scholarship: dict, filters_config: dict) -> bool:
    """Check if a scholarship matches the current filters."""
    if not filters_config.get('enabled', True):
        return True  # Filters disabled, match everything

    # Handle None values safely
    title = (scholarship.get('title') or '').lower()
    location = (scholarship.get('location') or '').lower()
    source_label = (scholarship.get('source_label') or '').lower()
    country = (scholarship.get('country') or '').lower()

    # Check exclude keywords first
    exclude_keywords = filters_config.get('exclude_keywords', [])
    for keyword in exclude_keywords:
        if keyword.lower() in title:
            return False

    # Check country filter
    countries = filters_config.get('countries', [])
    if countries:
        country_match = False
        for c in countries:
            c_lower = c.lower()
            if c_lower in location or c_lower in source_label or c_lower in country:
                country_match = True
                break
        if not country_match:
            return False

    # Check keyword filter
    keywords = filters_config.get('keywords', [])
    if keywords:
        keyword_match = False
        for keyword in keywords:
            if keyword.lower() in title:
                keyword_match = True
                break
        if not keyword_match:
            return False

    return True


def make_hashtag(text: str) -> str:
    """Convert text to a valid hashtag."""
    if not text:
        return ''
    # Remove special chars, replace spaces with nothing
    clean = ''.join(c for c in text if c.isalnum() or c == ' ')
    return '#' + clean.replace(' ', '')


def format_scholarship(scholarship: dict, include_buttons: bool = True, index: int = None, total: int = None) -> tuple:
    """Format a scholarship for Telegram message."""
    title = scholarship.get('title') or 'Unknown'
    title_zh = scholarship.get('title_zh') or ''
    url = scholarship.get('url') or '#'
    location = scholarship.get('location') or ''
    university = scholarship.get('university') or ''
    posted = scholarship.get('posted_time_text') or scholarship.get('posted_time') or ''
    source = scholarship.get('source_label') or ''
    country = scholarship.get('country') or ''

    # Clean up location
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

    # Format message with index if provided
    header = ""
    if index is not None and total is not None:
        header = f"📄 <b>[{index}/{total}]</b>\n\n"

    # Show Chinese title if available
    if title_zh and title_zh != title:
        message = (
            f"{header}"
            f"<b>{title_zh}</b>\n"
            f"<i>{title}</i>\n\n"
            f"📍 {location}\n"
        )
    else:
        message = (
            f"{header}"
            f"<b>{title}</b>\n\n"
            f"📍 {location}\n"
        )

    if source:
        message += f"📚 {source}\n"

    if country and country not in location:
        message += f"🌍 {country}\n"

    if posted:
        message += f"🕐 {posted}\n"

    # Add hashtags at the end
    if tags_str:
        message += f"\n{tags_str}\n"

    message += f"\n🔗 <a href=\"{url}\">View Details</a>"

    # Create inline keyboard
    keyboard = None
    if include_buttons:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Apply", url=url),
                InlineKeyboardButton("Save", callback_data=f"save:{url[:60]}"),
            ]
        ])

    return message, keyboard


def is_owner(user_id: int) -> bool:
    """Check if user is the bot owner."""
    return user_id == OWNER_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user = update.effective_user

    if not is_owner(user.id):
        await update.message.reply_text(
            "Sorry, this is a private bot. Access denied."
        )
        return

    await update.message.reply_text(
        f"Welcome to PhD Scholarship Bot!\n\n"
        f"<b>Commands:</b>\n"
        f"/list - Fast view (5 at once, with save buttons)\n"
        f"/latest - Browse one by one\n"
        f"/today - Today's new scholarships\n"
        f"/search &lt;keyword&gt; - Search scholarships\n"
        f"/filters - View/edit your filters\n"
        f"/saved - View saved scholarships\n"
        f"/stats - Scraping statistics\n"
        f"/digest - Trigger manual digest\n"
        f"/help - Show this message\n",
        parse_mode=ParseMode.HTML
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await start(update, context)


async def latest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /latest command - browse all scholarships."""
    if not is_owner(update.effective_user.id):
        return

    scholarships = load_scholarships()
    filters_config = get_filters()
    filtered = [s for s in scholarships if matches_filters(s, filters_config)]

    if not filtered:
        await update.message.reply_text("No scholarships found.")
        return

    context.user_data['browse_list'] = filtered
    context.user_data['browse_index'] = 0
    context.user_data['browse_mode'] = 'latest'
    await show_browse_item(update.message, context, 0)


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /today command - browse new scholarships."""
    if not is_owner(update.effective_user.id):
        return

    scholarships = load_scholarships()
    filters_config = get_filters()
    sent_ids = get_sent_ids()

    # Get new (unsent) scholarships that match filters
    new_scholarships = [
        s for s in scholarships
        if s.get('url') not in sent_ids and matches_filters(s, filters_config)
    ]

    if not new_scholarships:
        await update.message.reply_text("No new scholarships since last check.\nUse /latest to browse all.")
        return

    context.user_data['browse_list'] = new_scholarships
    context.user_data['browse_index'] = 0
    context.user_data['browse_mode'] = 'today'
    await show_browse_item(update.message, context, 0)


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command - search and browse results."""
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /search <keyword>\n"
            "Example: /search cancer"
        )
        return

    query = ' '.join(context.args).lower()
    scholarships = load_scholarships()

    # Search in title and title_zh
    results = [
        s for s in scholarships
        if query in (s.get('title') or '').lower() or query in (s.get('title_zh') or '').lower()
    ]

    if not results:
        await update.message.reply_text(f"No scholarships found for: {query}")
        return

    context.user_data['browse_list'] = results
    context.user_data['browse_index'] = 0
    context.user_data['browse_mode'] = f'search:{query}'
    await show_browse_item(update.message, context, 0)


async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /browse command - browse scholarships inline with navigation."""
    if not is_owner(update.effective_user.id):
        return

    scholarships = load_scholarships()
    filters_config = get_filters()

    # Get filtered scholarships
    filtered = [s for s in scholarships if matches_filters(s, filters_config)]

    if not filtered:
        await update.message.reply_text("No scholarships found matching your filters.")
        return

    # Store in context for navigation
    context.user_data['browse_list'] = filtered
    context.user_data['browse_index'] = 0
    await show_browse_item(update.message, context, 0)


async def list_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /list command - show 5 scholarships at once for fast browsing."""
    if not is_owner(update.effective_user.id):
        return

    scholarships = load_scholarships()
    filters_config = get_filters()
    filtered = [s for s in scholarships if matches_filters(s, filters_config)]

    if not filtered:
        await update.message.reply_text("No scholarships found.")
        return

    context.user_data['list_data'] = filtered
    context.user_data['list_page'] = 0
    await show_list_page(update.message, context, 0)


async def show_list_page(target, context, page: int, edit: bool = False):
    """Show a page of 5 scholarships in list format."""
    data = context.user_data.get('list_data', [])
    if not data:
        return

    page_size = 5
    total_pages = (len(data) + page_size - 1) // page_size
    page = max(0, min(page, total_pages - 1))
    context.user_data['list_page'] = page

    start_idx = page * page_size
    end_idx = min(start_idx + page_size, len(data))
    page_items = data[start_idx:end_idx]

    # Build message with 5 scholarships
    lines = [f"<b>📋 List View</b> (Page {page + 1}/{total_pages}, Total: {len(data)})\n"]

    for i, s in enumerate(page_items):
        num = i + 1
        title_zh = s.get('title_zh') or ''
        title = s.get('title') or 'Unknown'
        location = s.get('location') or s.get('country') or ''

        # Show Chinese title if available, otherwise English
        display_title = title_zh if title_zh else title
        # Truncate if too long
        if len(display_title) > 50:
            display_title = display_title[:47] + "..."

        lines.append(f"<b>{num}.</b> {display_title}")
        if location:
            lines.append(f"   📍 {location[:30]}")
        lines.append("")

    message = "\n".join(lines)

    # Build buttons
    buttons = []

    # Row 1: Number buttons to save (1-5)
    save_row = []
    for i, s in enumerate(page_items):
        url = s.get('url', '')[:40]
        save_row.append(InlineKeyboardButton(f"⭐{i+1}", callback_data=f"lsave:{page}:{i}"))
    buttons.append(save_row)

    # Row 2: Open links (1-5)
    link_row = []
    for i, s in enumerate(page_items):
        url = s.get('url', '#')
        link_row.append(InlineKeyboardButton(f"🔗{i+1}", url=url))
    buttons.append(link_row)

    # Row 3: Navigation
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⏮️ First", callback_data="list:first"))
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data="list:prev"))
    nav_row.append(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="list:noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data="list:next"))
        nav_row.append(InlineKeyboardButton("Last ⏭️", callback_data="list:last"))
    buttons.append(nav_row)

    # Row 4: Jump options
    jump_row = []
    if total_pages > 10:
        jump_row.append(InlineKeyboardButton("-10", callback_data="list:jump:-10"))
    if total_pages > 5:
        jump_row.append(InlineKeyboardButton("-5", callback_data="list:jump:-5"))
    if total_pages > 5:
        jump_row.append(InlineKeyboardButton("+5", callback_data="list:jump:5"))
    if total_pages > 10:
        jump_row.append(InlineKeyboardButton("+10", callback_data="list:jump:10"))
    if jump_row:
        buttons.append(jump_row)

    keyboard = InlineKeyboardMarkup(buttons)

    try:
        if edit:
            await target.edit_text(message, parse_mode=ParseMode.HTML, reply_markup=keyboard, disable_web_page_preview=True)
        else:
            await target.reply_text(message, parse_mode=ParseMode.HTML, reply_markup=keyboard, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error showing list page: {e}")


async def show_browse_item(target, context, index: int, is_saved: bool = False, edit: bool = False):
    """Show a scholarship with navigation buttons."""
    filtered = context.user_data.get('browse_list', [])
    if not filtered:
        return

    # Clamp index
    index = max(0, min(index, len(filtered) - 1))
    context.user_data['browse_index'] = index

    scholarship = filtered[index]
    msg, _ = format_scholarship(scholarship, include_buttons=False, index=index + 1, total=len(filtered))

    url = scholarship.get('url') or '#'

    # Navigation buttons
    buttons = []

    # Row 1: Navigation
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⬅️", callback_data="browse:prev"))
    nav_row.append(InlineKeyboardButton(f"{index + 1}/{len(filtered)}", callback_data="browse:noop"))
    if index < len(filtered) - 1:
        nav_row.append(InlineKeyboardButton("➡️", callback_data="browse:next"))
    buttons.append(nav_row)

    # Row 2: Actions
    if is_saved:
        buttons.append([
            InlineKeyboardButton("🔗 Apply", url=url),
            InlineKeyboardButton("🗑️ Remove", callback_data=f"unsave:{url[:50]}"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton("🔗 Apply", url=url),
            InlineKeyboardButton("⭐ Save", callback_data=f"save:{url[:50]}"),
        ])

    keyboard = InlineKeyboardMarkup(buttons)

    # Edit existing message or send new
    try:
        if edit:
            await target.edit_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard, disable_web_page_preview=True)
        else:
            await target.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=keyboard, disable_web_page_preview=True)
    except Exception as e:
        logger.error(f"Error showing browse item: {e}")


async def show_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /filters command."""
    if not is_owner(update.effective_user.id):
        return

    filters_config = get_filters()

    countries = filters_config.get('countries', [])
    keywords = filters_config.get('keywords', [])
    exclude = filters_config.get('exclude_keywords', [])
    enabled = filters_config.get('enabled', True)

    message = (
        f"<b>Your Filters</b>\n\n"
        f"<b>Status:</b> {'Enabled' if enabled else 'Disabled'}\n\n"
        f"<b>Countries:</b>\n"
        f"{', '.join(countries) if countries else 'All countries'}\n\n"
        f"<b>Keywords:</b>\n"
        f"{', '.join(keywords) if keywords else 'No keyword filter'}\n\n"
        f"<b>Exclude:</b>\n"
        f"{', '.join(exclude) if exclude else 'None'}\n\n"
        f"<i>To modify, use:</i>\n"
        f"/addcountry &lt;name&gt;\n"
        f"/removecountry &lt;name&gt;\n"
        f"/addkeyword &lt;word&gt;\n"
        f"/removekeyword &lt;word&gt;\n"
        f"/togglefilters"
    )

    await update.message.reply_text(message, parse_mode=ParseMode.HTML)


async def add_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addcountry command."""
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /addcountry <country name>")
        return

    country = ' '.join(context.args)
    filters_config = get_filters()
    countries = filters_config.get('countries', [])

    if country not in countries:
        countries.append(country)
        filters_config['countries'] = countries
        save_filters(filters_config)
        await update.message.reply_text(f"Added country filter: {country}")
    else:
        await update.message.reply_text(f"Country already in filters: {country}")


async def remove_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removecountry command."""
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /removecountry <country name>")
        return

    country = ' '.join(context.args)
    filters_config = get_filters()
    countries = filters_config.get('countries', [])

    if country in countries:
        countries.remove(country)
        filters_config['countries'] = countries
        save_filters(filters_config)
        await update.message.reply_text(f"Removed country filter: {country}")
    else:
        await update.message.reply_text(f"Country not in filters: {country}")


async def add_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /addkeyword command."""
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /addkeyword <keyword>")
        return

    keyword = ' '.join(context.args)
    filters_config = get_filters()
    keywords = filters_config.get('keywords', [])

    if keyword not in keywords:
        keywords.append(keyword)
        filters_config['keywords'] = keywords
        save_filters(filters_config)
        await update.message.reply_text(f"Added keyword filter: {keyword}")
    else:
        await update.message.reply_text(f"Keyword already in filters: {keyword}")


async def remove_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /removekeyword command."""
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text("Usage: /removekeyword <keyword>")
        return

    keyword = ' '.join(context.args)
    filters_config = get_filters()
    keywords = filters_config.get('keywords', [])

    if keyword in keywords:
        keywords.remove(keyword)
        filters_config['keywords'] = keywords
        save_filters(filters_config)
        await update.message.reply_text(f"Removed keyword filter: {keyword}")
    else:
        await update.message.reply_text(f"Keyword not in filters: {keyword}")


async def toggle_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /togglefilters command."""
    if not is_owner(update.effective_user.id):
        return

    filters_config = get_filters()
    filters_config['enabled'] = not filters_config.get('enabled', True)
    save_filters(filters_config)

    status = 'enabled' if filters_config['enabled'] else 'disabled'
    await update.message.reply_text(f"Filters {status}!")


async def saved(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /saved command - browse saved scholarships."""
    if not is_owner(update.effective_user.id):
        return

    saved_list = get_saved_scholarships()

    if not saved_list:
        await update.message.reply_text("No saved scholarships yet.\nUse the ⭐ Save button to bookmark.")
        return

    context.user_data['browse_list'] = saved_list
    context.user_data['browse_index'] = 0
    context.user_data['browse_mode'] = 'saved'
    await show_browse_item(update.message, context, 0, is_saved=True)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /stats command - show statistics."""
    if not is_owner(update.effective_user.id):
        return

    combined_file = DATA_DIR / 'all_scholarships.json'

    if not combined_file.exists():
        await update.message.reply_text("No data available yet.")
        return

    try:
        with open(combined_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        generated_at = data.get('generated_at', 'Unknown')
        total = data.get('total_scholarships', 0)
        sources = data.get('sources', {})

        message = (
            f"<b>Scholarship Statistics</b>\n\n"
            f"<b>Last Updated:</b> {generated_at}\n"
            f"<b>Total Scholarships:</b> {total}\n\n"
            f"<b>By Source:</b>\n"
        )

        for source, count in sources.items():
            message += f"  {source}: {count}\n"

        sent_count = len(get_sent_ids())
        saved_count = len(get_saved_scholarships())

        message += f"\n<b>Sent notifications:</b> {sent_count}\n"
        message += f"<b>Saved scholarships:</b> {saved_count}"

        await update.message.reply_text(message, parse_mode=ParseMode.HTML)

    except Exception as e:
        await update.message.reply_text(f"Error loading stats: {e}")


async def digest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /digest command - show digest summary with link."""
    if not is_owner(update.effective_user.id):
        return

    scholarships = load_scholarships()
    filters_config = get_filters()

    # Get filtered scholarships
    filtered = [s for s in scholarships if matches_filters(s, filters_config)]

    # Count by source
    sources = {}
    for s in filtered[:100]:
        src = s.get('source_label') or 'Other'
        sources[src] = sources.get(src, 0) + 1

    source_list = '\n'.join(f"  • {k}: {v}" for k, v in sources.items())

    message = (
        f"<b>📊 Scholarship Digest</b>\n\n"
        f"<b>Total matching filters:</b> {len(filtered)}\n\n"
        f"<b>By category:</b>\n{source_list}\n\n"
        f"🔗 <a href=\"{GITHUB_PAGES_URL}/\">Browse All</a>\n"
        f"📰 <a href=\"{GITHUB_PAGES_URL}/feed.xml\">RSS Feed</a>"
    )

    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks."""
    query = update.callback_query

    if not is_owner(query.from_user.id):
        await query.answer()
        return

    data = query.data

    # Browse navigation
    if data.startswith('browse:'):
        action = data[7:]
        is_saved = context.user_data.get('browse_mode') == 'saved'
        if action == 'prev':
            index = context.user_data.get('browse_index', 0) - 1
            await show_browse_item(query.message, context, index, is_saved=is_saved, edit=True)
        elif action == 'next':
            index = context.user_data.get('browse_index', 0) + 1
            await show_browse_item(query.message, context, index, is_saved=is_saved, edit=True)
        await query.answer()
        return

    # List view navigation
    if data.startswith('list:'):
        action = data[5:]
        page = context.user_data.get('list_page', 0)
        data_list = context.user_data.get('list_data', [])
        page_size = 5
        total_pages = (len(data_list) + page_size - 1) // page_size if data_list else 1

        if action == 'prev':
            page = max(0, page - 1)
        elif action == 'next':
            page = min(total_pages - 1, page + 1)
        elif action == 'first':
            page = 0
        elif action == 'last':
            page = total_pages - 1
        elif action.startswith('jump:'):
            jump = int(action[5:])
            page = max(0, min(total_pages - 1, page + jump))

        await show_list_page(query.message, context, page, edit=True)
        await query.answer()
        return

    # List view save (lsave:page:index)
    if data.startswith('lsave:'):
        parts = data[6:].split(':')
        if len(parts) == 2:
            page = int(parts[0])
            idx = int(parts[1])
            data_list = context.user_data.get('list_data', [])
            page_size = 5
            item_idx = page * page_size + idx
            if 0 <= item_idx < len(data_list):
                s = data_list[item_idx]
                if save_scholarship_bookmark(s):
                    await query.answer(f"⭐ Saved #{idx+1}!", show_alert=True)
                else:
                    await query.answer("Already saved", show_alert=True)
            else:
                await query.answer("Item not found", show_alert=True)
        else:
            await query.answer()
        return

    # Save scholarship
    if data.startswith('save:'):
        url_prefix = data[5:]
        # Find from current browse list or all scholarships
        browse_list = context.user_data.get('browse_list', [])
        scholarships = browse_list if browse_list else load_scholarships()
        for s in scholarships:
            if s.get('url', '').startswith(url_prefix):
                if save_scholarship_bookmark(s):
                    await query.answer("⭐ Saved!", show_alert=True)
                else:
                    await query.answer("Already saved", show_alert=True)
                return
        await query.answer()
        return

    # Remove from saved
    if data.startswith('unsave:'):
        url_prefix = data[7:]
        saved_list = get_saved_scholarships()
        for s in saved_list:
            if s.get('url', '').startswith(url_prefix):
                if remove_bookmark(s.get('url')):
                    await query.answer("🗑️ Removed!", show_alert=True)
                    # Refresh saved list and show next item
                    new_saved = get_saved_scholarships()
                    if new_saved:
                        context.user_data['browse_list'] = new_saved
                        index = min(context.user_data.get('browse_index', 0), len(new_saved) - 1)
                        await show_browse_item(query.message, context, index, is_saved=True, edit=True)
                    else:
                        await query.message.edit_text("No saved scholarships.")
                return
        await query.answer()
        return

    await query.answer()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    logger.error(f"Error: {context.error}")


class ScholarshipBot:
    """Main bot class."""

    def __init__(self, token: str = None):
        self.token = token or BOT_TOKEN
        self.app = None

    async def set_commands(self):
        """Set bot commands menu."""
        commands = [
            BotCommand("list", "Fast view (5 at once)"),
            BotCommand("latest", "Browse one by one"),
            BotCommand("today", "Browse new scholarships"),
            BotCommand("search", "Search scholarships"),
            BotCommand("saved", "View saved items"),
            BotCommand("filters", "Manage filters"),
            BotCommand("stats", "Statistics"),
            BotCommand("help", "Show help"),
        ]
        await self.app.bot.set_my_commands(commands)
        logger.info("Bot commands menu set")

    def setup(self):
        """Setup the bot application."""
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not set")

        self.app = Application.builder().token(self.token).build()

        # Add handlers
        self.app.add_handler(CommandHandler("start", start))
        self.app.add_handler(CommandHandler("help", help_command))
        self.app.add_handler(CommandHandler("list", list_view))
        self.app.add_handler(CommandHandler("latest", latest))
        self.app.add_handler(CommandHandler("today", today))
        self.app.add_handler(CommandHandler("search", search))
        self.app.add_handler(CommandHandler("browse", browse))
        self.app.add_handler(CommandHandler("filters", show_filters))
        self.app.add_handler(CommandHandler("addcountry", add_country))
        self.app.add_handler(CommandHandler("removecountry", remove_country))
        self.app.add_handler(CommandHandler("addkeyword", add_keyword))
        self.app.add_handler(CommandHandler("removekeyword", remove_keyword))
        self.app.add_handler(CommandHandler("togglefilters", toggle_filters))
        self.app.add_handler(CommandHandler("saved", saved))
        self.app.add_handler(CommandHandler("stats", stats))
        self.app.add_handler(CommandHandler("digest", digest))
        self.app.add_handler(CallbackQueryHandler(button_callback))
        self.app.add_error_handler(error_handler)

        return self.app

    def run(self):
        """Run the bot (blocking)."""
        if not self.app:
            self.setup()

        logger.info("Starting Telegram bot...")

        # Set commands menu on startup
        async def post_init(application):
            await self.set_commands()

        self.app.post_init = post_init
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        return

    if not OWNER_ID:
        logger.warning("TELEGRAM_OWNER_ID not set - bot will deny all access!")

    bot = ScholarshipBot()
    bot.run()


if __name__ == '__main__':
    main()
