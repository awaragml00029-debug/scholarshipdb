# PhD Scholarship RSS Feed

Scrapes [scholarshipdb.net](https://scholarshipdb.net) daily and generates an RSS feed, deployed via GitHub Pages.

## How it works

```
scrapers/scholardb.py  →  feed.py  →  docs/feed.xml  →  GitHub Pages
```

- **Playwright** handles Cloudflare-protected pages
- **GitHub Actions** runs daily at 06:00 UTC and commits updated `feed.xml`
- **Proxy support** for bypassing Cloudflare blocks on Actions IPs

## Subscribe

RSS feed URL (after GitHub Pages is enabled):
```
https://<your-username>.github.io/<repo-name>/feed.xml
```

## Project structure

```
scrapers/
├── __init__.py       # FeedItem + BaseSource interface
└── scholardb.py      # scholarshipdb.net scraper
notify/
└── telegram.py       # Telegram push (planned)
feed.py               # RSS 2.0 generator
main.py               # Entrypoint: run all scrapers → generate feed
config.py             # All config via environment variables
time_parser.py        # Relative time parsing ("3 days ago" → datetime)
docs/
└── feed.xml          # Generated RSS output
```

## Configuration

All settings via environment variables (or GitHub Secrets/Variables):

| Variable | Description | Default |
|---|---|---|
| `PROXY_URL` | Proxy for Cloudflare bypass | _(none, direct)_ |
| `RSS_LINK` | Your GitHub Pages base URL | `https://example.github.io/scholarshipdb` |
| `RSS_TITLE` | Feed title | `PhD Scholarships Feed` |
| `RSS_MAX_ITEMS` | Max items in feed | `100` |

### Proxy formats supported

| Format | Supported |
|---|---|
| `http://host:port` | ✓ |
| `http://user:pass@host:port` | ✓ |
| `socks5://host:port` | ✓ |
| `socks5://user:pass@host:port` | ✓ (Actions auto-tunnels via gost) |
| `socks5h://user:pass@host:port` | ✓ (same as above) |

## GitHub Actions setup

1. Go to **Settings → Secrets → Actions**, add `PROXY_URL` (if needed)
2. Go to **Settings → Variables → Actions**, add `RSS_LINK` with your Pages URL
3. Enable **GitHub Pages** from the `docs/` folder
4. Trigger manually: **Actions → Scrape & Update Feed → Run workflow**

## Add a new source

1. Create `scrapers/mysource.py` extending `BaseSource`
2. Implement `async def fetch(self) -> List[FeedItem]`
3. Add it to `SOURCES` in `main.py`

## Local run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Without proxy
python main.py

# With proxy
PROXY_URL=http://user:pass@host:port python main.py
```
