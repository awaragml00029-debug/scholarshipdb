#!/usr/bin/env python
"""Entry point: run all scrapers → generate RSS feed."""
import asyncio
import sys

from loguru import logger

import config
import feed
import translate
from scrapers.scholardb import ScholardbSource

SOURCES = [
    ScholardbSource(sources=[
        {"label": "Cancer Research", "url": "https://scholarshipdb.net/scholarships/Program-PhD?q=cancer", "max_pages": 5},
        {"label": "Biology",         "url": "https://scholarshipdb.net/scholarships?q=Biology",             "max_pages": 5},
        {"label": "Netherlands",     "url": "https://scholarshipdb.net/scholarships-in-Netherlands",        "max_pages": 5},
        {"label": "Sweden",          "url": "https://scholarshipdb.net/scholarships-in-Sweden",             "max_pages": 5},
        {"label": "Belgium",         "url": "https://scholarshipdb.net/scholarships-in-Belgium",            "max_pages": 5},
        {"label": "Luxembourg",      "url": "https://scholarshipdb.net/scholarships-in-Luxembourg",         "max_pages": 5},
        {"label": "Norway",          "url": "https://scholarshipdb.net/scholarships-in-Norway",             "max_pages": 5},
        {"label": "Austria",         "url": "https://scholarshipdb.net/scholarships-in-Austria",            "max_pages": 5},
        {"label": "Denmark",         "url": "https://scholarshipdb.net/scholarships-in-Denmark",            "max_pages": 5},
        {"label": "Switzerland",     "url": "https://scholarshipdb.net/scholarships-in-Switzerland",        "max_pages": 5},
    ]),
]


async def run():
    all_items = []

    for source in SOURCES:
        logger.info(f"[{source.name}] Fetching...")
        try:
            items = await source.fetch()
            logger.info(f"[{source.name}] {len(items)} items total")
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[{source.name}] Failed: {e}")

    if not all_items:
        logger.warning("No items fetched — feed not updated")
        sys.exit(1)

    # English feed
    feed.generate(all_items)
    logger.info(f"Feed written → {config.RSS_OUTPUT}  ({len(all_items)} items)")

    # Translated feed (default zh-CN, skip if TRANSLATE_TARGET is empty)
    if config.TRANSLATE_TARGET:
        lang = config.TRANSLATE_TARGET
        out = config.RSS_OUTPUT.replace(".xml", f"_{lang.replace('-', '_')}.xml")
        logger.info(f"Translating titles to {lang}...")
        translated_items = translate.translate_items(all_items)
        feed.generate(translated_items, output=out,
                      title=f"{config.RSS_TITLE} ({lang})")
        logger.info(f"Translated feed written → {out}")


if __name__ == "__main__":
    asyncio.run(run())
