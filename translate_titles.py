#!/usr/bin/env python
"""Add Chinese translations to scholarship titles."""
import json
import sys
from pathlib import Path
from loguru import logger

try:
    from googletrans import Translator
except ImportError:
    logger.error("Please install googletrans: pip install googletrans==4.0.0-rc1")
    sys.exit(1)


def translate_scholarships(input_file='data/all_scholarships.json', output_file=None):
    """
    Add Chinese translations to scholarship titles.

    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file (defaults to same as input)
    """
    if output_file is None:
        output_file = input_file

    logger.info(f"Loading scholarships from {input_file}")

    # Load data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    scholarships = data.get('scholarships', [])
    total = len(scholarships)

    logger.info(f"Found {total} scholarships")
    logger.info("Starting translation...")

    # Initialize translator
    translator = Translator()

    # Translate titles
    translated = 0
    skipped = 0

    for idx, scholarship in enumerate(scholarships, 1):
        title = scholarship.get('title', '')

        # Skip if already has Chinese translation
        if scholarship.get('title_zh'):
            skipped += 1
            continue

        if title:
            try:
                # Translate to Chinese
                translation = translator.translate(title, src='en', dest='zh-cn')
                scholarship['title_zh'] = translation.text
                translated += 1

                if idx % 10 == 0:
                    logger.info(f"Progress: {idx}/{total} ({(idx/total*100):.1f}%)")

            except Exception as e:
                logger.warning(f"Failed to translate: {title[:50]}... - {e}")
                scholarship['title_zh'] = title  # Fallback to original

    logger.info(f"✓ Translated {translated} titles")
    logger.info(f"  Skipped {skipped} (already translated)")

    # Save updated data
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ Saved to {output_file}")

    return translated


if __name__ == '__main__':
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    input_file = sys.argv[1] if len(sys.argv) > 1 else 'data/all_scholarships.json'

    translated = translate_scholarships(input_file)

    print(f"\n✓ Translation completed! {translated} titles translated to Chinese.")
