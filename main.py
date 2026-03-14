#!/usr/bin/env python
"""Entry point: run all scrapers → generate RSS feed."""
import asyncio
import sys

from loguru import logger

import feed
from scrapers.scholardb import ScholardbSource

SOURCES = [
    ScholardbSource(),
]


async def run():
    all_items = []

    for source in SOURCES:
        logger.info(f"[{source.name}] Fetching...")
        try:
            items = await source.fetch()
            logger.info(f"[{source.name}] {len(items)} items")
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[{source.name}] Failed: {e}")

    if not all_items:
        logger.warning("No items fetched — feed not updated")
        sys.exit(1)

    output = feed.generate(all_items)
    logger.info(f"Feed written → {output}  ({len(all_items)} items total)")


if __name__ == "__main__":
    asyncio.run(run())
