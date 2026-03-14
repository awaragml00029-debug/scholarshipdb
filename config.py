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

# RSS output
RSS_MAX_ITEMS = int(os.environ.get("RSS_MAX_ITEMS", "100"))
RSS_OUTPUT = os.environ.get("RSS_OUTPUT", "docs/feed.xml")
RSS_TITLE = os.environ.get("RSS_TITLE", "PhD Scholarships Feed")
RSS_LINK = os.environ.get("RSS_LINK", "https://example.github.io/scholarshipdb")
