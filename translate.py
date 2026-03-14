"""Translate FeedItem titles with caching to avoid re-translating daily."""
import json
import time
from copy import copy
from pathlib import Path
from typing import List

from loguru import logger

import config
from scrapers import FeedItem


def translate_items(items: List[FeedItem]) -> List[FeedItem]:
    """Return new FeedItems with titles translated to TRANSLATE_TARGET language.

    Translations are cached in TRANSLATE_CACHE so only new titles are sent
    to the translation API on each run.
    """
    target = config.TRANSLATE_TARGET
    if not target:
        return items

    try:
        from deep_translator import GoogleTranslator
    except ImportError:
        logger.warning("deep-translator not installed — skipping translation")
        return items

    cache = _load_cache()
    translator = GoogleTranslator(source="en", target=target)

    result = []
    new_translations = 0

    for item in items:
        translated = copy(item)
        title = item.title

        if title in cache:
            translated.title = cache[title]
        else:
            try:
                zh_title = translator.translate(title)
                cache[title] = zh_title
                translated.title = zh_title
                new_translations += 1
                time.sleep(0.1)  # avoid rate limiting
            except Exception as e:
                logger.warning(f"Translation failed for '{title[:40]}': {e}")
                translated.title = title  # fallback to original

        result.append(translated)

    if new_translations:
        _save_cache(cache)
        logger.info(f"Translated {new_translations} new titles (cache: {len(cache)} total)")
    else:
        logger.info("All titles from cache — no API calls needed")

    return result


def _load_cache() -> dict:
    path = Path(config.TRANSLATE_CACHE)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_cache(cache: dict):
    path = Path(config.TRANSLATE_CACHE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
