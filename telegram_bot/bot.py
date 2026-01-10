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


def format_scholarship(scholarship: dict, include_buttons: bool = True) -> tuple:
    """Format a scholarship for Telegram message."""
    title = scholarship.get('title') or 'Unknown'
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

    # Format message
    message = (
        f"<b>{title}</b>\n\n"
        f"<b>Location:</b> {location}\n"
    )

    if source:
        message += f"<b>Category:</b> {source}\n"

    if country and country not in location:
        message += f"<b>Country:</b> {country}\n"

    if posted:
        message += f"<b>Posted:</b> {posted}\n"

    # Add hashtags at the end
    if tags_str:
        message += f"\n{tags_str}\n"

    message += f"\n<a href=\"{url}\">View Details</a>"

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
        f"/latest - Get latest 10 scholarships\n"
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
    """Handle /latest command - show link to latest scholarships."""
    if not is_owner(update.effective_user.id):
        return

    scholarships = load_scholarships()
    total = len(scholarships)

    # Count by source
    sources = {}
    for s in scholarships[:50]:  # Count top 50
        src = s.get('source_label') or 'Other'
        sources[src] = sources.get(src, 0) + 1

    source_list = '\n'.join(f"  • {k}: {v}" for k, v in sources.items())

    message = (
        f"<b>📚 Latest Scholarships</b>\n\n"
        f"<b>Total:</b> {total} scholarships\n\n"
        f"<b>Top sources:</b>\n{source_list}\n\n"
        f"🔗 <a href=\"{GITHUB_PAGES_URL}/\">View All Scholarships</a>"
    )

    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False
    )


async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /today command - show link to today's new scholarships."""
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
        message = (
            f"<b>📅 Today's Scholarships</b>\n\n"
            f"No new scholarships since last check.\n\n"
            f"🔗 <a href=\"{GITHUB_PAGES_URL}/daily.html\">View Daily Report</a>"
        )
    else:
        # Count by source
        sources = {}
        for s in new_scholarships:
            src = s.get('source_label') or 'Other'
            sources[src] = sources.get(src, 0) + 1

        source_list = '\n'.join(f"  • {k}: {v}" for k, v in sources.items())

        message = (
            f"<b>📅 Today's New Scholarships</b>\n\n"
            f"<b>Found:</b> {len(new_scholarships)} new scholarships\n\n"
            f"<b>By category:</b>\n{source_list}\n\n"
            f"🔗 <a href=\"{GITHUB_PAGES_URL}/daily.html\">View Daily Report</a>"
        )

    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /search command."""
    if not is_owner(update.effective_user.id):
        return

    if not context.args:
        await update.message.reply_text(
            "Usage: /search <keyword>\n"
            "Example: /search cancer research"
        )
        return

    query = ' '.join(context.args).lower()
    scholarships = load_scholarships()

    # Search in title
    results = [
        s for s in scholarships
        if query in (s.get('title') or '').lower()
    ]

    if not results:
        await update.message.reply_text(
            f"<b>🔍 Search: '{query}'</b>\n\n"
            f"No scholarships found.\n\n"
            f"🔗 <a href=\"{GITHUB_PAGES_URL}/\">Browse All</a>",
            parse_mode=ParseMode.HTML
        )
        return

    # Count by country
    countries = {}
    for s in results[:20]:
        c = s.get('country') or 'Unknown'
        countries[c] = countries.get(c, 0) + 1

    country_list = '\n'.join(f"  • {k}: {v}" for k, v in list(countries.items())[:5])

    message = (
        f"<b>🔍 Search: '{query}'</b>\n\n"
        f"<b>Found:</b> {len(results)} scholarships\n\n"
        f"<b>Top countries:</b>\n{country_list}\n\n"
        f"🔗 <a href=\"{GITHUB_PAGES_URL}/\">Browse All</a>"
    )

    await update.message.reply_text(
        message,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=False
    )


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
    """Handle /saved command - show saved scholarships."""
    if not is_owner(update.effective_user.id):
        return

    saved_list = get_saved_scholarships()

    if not saved_list:
        await update.message.reply_text("No saved scholarships yet.\nUse the Save button to bookmark scholarships.")
        return

    await update.message.reply_text(
        f"<b>Saved Scholarships ({len(saved_list)})</b>",
        parse_mode=ParseMode.HTML
    )

    for scholarship in saved_list[:10]:
        message, _ = format_scholarship(scholarship, include_buttons=False)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Apply", url=scholarship.get('url', '#')),
                InlineKeyboardButton("Remove", callback_data=f"unsave:{scholarship.get('url', '')[:60]}"),
            ]
        ])
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        await asyncio.sleep(0.3)


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
    await query.answer()

    if not is_owner(query.from_user.id):
        return

    data = query.data

    if data.startswith('save:'):
        url_prefix = data[5:]
        # Find the scholarship by URL prefix
        scholarships = load_scholarships()
        for s in scholarships:
            if s.get('url', '').startswith(url_prefix):
                if save_scholarship_bookmark(s):
                    await query.edit_message_reply_markup(
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("Saved!", callback_data="noop")]
                        ])
                    )
                else:
                    await query.edit_message_reply_markup(
                        reply_markup=InlineKeyboardMarkup([
                            [InlineKeyboardButton("Already saved", callback_data="noop")]
                        ])
                    )
                break

    elif data.startswith('unsave:'):
        url_prefix = data[7:]
        saved_list = get_saved_scholarships()
        for s in saved_list:
            if s.get('url', '').startswith(url_prefix):
                if remove_bookmark(s.get('url')):
                    await query.edit_message_text("Removed from saved.")
                break


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
            BotCommand("start", "Welcome & help"),
            BotCommand("latest", "Latest 10 scholarships"),
            BotCommand("today", "New scholarships today"),
            BotCommand("search", "Search by keyword"),
            BotCommand("filters", "View/edit filters"),
            BotCommand("saved", "Saved scholarships"),
            BotCommand("stats", "Statistics"),
            BotCommand("digest", "Manual digest"),
            BotCommand("addcountry", "Add country filter"),
            BotCommand("addkeyword", "Add keyword filter"),
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
        self.app.add_handler(CommandHandler("latest", latest))
        self.app.add_handler(CommandHandler("today", today))
        self.app.add_handler(CommandHandler("search", search))
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
