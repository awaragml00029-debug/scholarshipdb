import os

# Proxy for Cloudflare bypass (set via env or GitHub Actions Secret)
# Format: http://user:pass@host:port  or  socks5://host:port
PROXY_URL = os.environ.get("PROXY_URL")

# Browser
HEADLESS = os.environ.get("HEADLESS", "true").lower() == "true"
TIMEOUT = int(os.environ.get("TIMEOUT", "30000"))
MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
DELAY_MIN = float(os.environ.get("DELAY_MIN", "2"))
DELAY_MAX = float(os.environ.get("DELAY_MAX", "5"))

# Translation
TRANSLATE_TARGET = os.environ.get("TRANSLATE_TARGET", "zh-CN")  # set to "" to disable
TRANSLATE_CACHE = os.environ.get("TRANSLATE_CACHE", "docs/translations_cache.json")

# Telegram notifications
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TELEGRAPH_TOKEN_FILE = os.environ.get("TELEGRAPH_TOKEN_FILE", "docs/telegraph_token.json")
NOTIFIED_URLS_FILE = os.environ.get("NOTIFIED_URLS_FILE", "docs/notified_urls.json")

# RSS output
RSS_MAX_ITEMS = int(os.environ.get("RSS_MAX_ITEMS", "100"))
RSS_OUTPUT = os.environ.get("RSS_OUTPUT", "docs/feed.xml")
RSS_TITLE = os.environ.get("RSS_TITLE", "PhD Scholarships Feed")
RSS_LINK = os.environ.get("RSS_LINK", "https://example.github.io/scholarshipdb")
