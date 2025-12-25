#!/usr/bin/env python
"""Batch scraper that processes multiple URLs from configuration file."""
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict
import yaml
from loguru import logger

from scraper_v2 import ScholarshipScraperV2


def setup_logging():
    """Setup logging."""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )


def load_config(config_file: str = "urls.yaml") -> dict:
    """Load configuration from YAML file."""
    config_path = Path(config_file)

    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_file}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    return config


async def scrape_all_sources(config: dict) -> Dict[str, List[Dict]]:
    """
    Scrape all enabled sources from configuration.

    Returns:
        Dictionary mapping source name to list of scholarships
    """
    sources = config.get('sources', [])
    config_settings = config.get('config', {})

    delay_between_sources = config_settings.get('delay_between_sources', 5)
    output_dir = Path(config_settings.get('output_dir', 'data'))

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Filter enabled sources
    enabled_sources = [s for s in sources if s.get('enabled', True)]

    logger.info(f"Found {len(enabled_sources)} enabled sources out of {len(sources)} total")

    all_results = {}
    total_scholarships = 0

    async with ScholarshipScraperV2() as scraper:
        for idx, source in enumerate(enabled_sources, 1):
            name = source['name']
            label = source['label']
            url = source['url']
            max_pages = source.get('max_pages', 10)

            logger.info(f"\n{'='*70}")
            logger.info(f"[{idx}/{len(enabled_sources)}] Processing: {label} ({name})")
            logger.info(f"URL: {url}")
            logger.info(f"Max pages: {max_pages}")
            logger.info(f"{'='*70}\n")

            try:
                scholarships = await scraper.scrape_url(url, max_pages=max_pages)

                # Add source metadata to each scholarship
                for sch in scholarships:
                    sch['source_name'] = name
                    sch['source_label'] = label
                    sch['source_url'] = url

                all_results[name] = scholarships
                total_scholarships += len(scholarships)

                # Save individual source file
                source_file = output_dir / f"{name}.json"
                with open(source_file, 'w', encoding='utf-8') as f:
                    json.dump(scholarships, f, ensure_ascii=False, indent=2)

                logger.info(f"✓ Scraped {len(scholarships)} scholarships")
                logger.info(f"✓ Saved to {source_file}")

            except Exception as e:
                logger.error(f"✗ Error scraping {name}: {e}")
                all_results[name] = []

            # Delay between sources (except after last one)
            if idx < len(enabled_sources):
                logger.info(f"\nWaiting {delay_between_sources} seconds before next source...")
                await asyncio.sleep(delay_between_sources)

    logger.info(f"\n{'='*70}")
    logger.info(f"SUMMARY")
    logger.info(f"{'='*70}")
    logger.info(f"Total sources processed: {len(enabled_sources)}")
    logger.info(f"Total scholarships scraped: {total_scholarships}")

    for name, scholarships in all_results.items():
        logger.info(f"  - {name}: {len(scholarships)} scholarships")

    return all_results


def save_combined_output(all_results: Dict[str, List[Dict]], output_file: str):
    """Save combined output file with all scholarships."""
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True)

    # Flatten all scholarships into single list
    all_scholarships = []
    for scholarships in all_results.values():
        all_scholarships.extend(scholarships)

    # Sort by posted_time (newest first)
    all_scholarships.sort(
        key=lambda x: x.get('posted_time') or '',
        reverse=True
    )

    # Add metadata
    output_data = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_scholarships': len(all_scholarships),
        'sources': {
            name: len(scholarships)
            for name, scholarships in all_results.items()
        },
        'scholarships': all_scholarships
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✓ Combined output saved to {output_path}")
    logger.info(f"  Total: {len(all_scholarships)} scholarships")


async def main():
    """Main function."""
    setup_logging()

    logger.info("PhD Scholarship Batch Scraper")
    logger.info("="*70 + "\n")

    # Load configuration
    config_file = sys.argv[1] if len(sys.argv) > 1 else "urls.yaml"
    logger.info(f"Loading configuration from: {config_file}\n")
    config = load_config(config_file)

    # Scrape all sources
    all_results = await scrape_all_sources(config)

    # Save combined output
    combined_output = config.get('config', {}).get('combined_output', 'data/all_scholarships.json')
    save_combined_output(all_results, combined_output)

    logger.info(f"\n{'='*70}")
    logger.info("✓ Batch scraping completed successfully!")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
