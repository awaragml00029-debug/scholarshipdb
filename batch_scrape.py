#!/usr/bin/env python
"""Batch scraper that processes multiple URLs from configuration file."""
import asyncio
import json
import random
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import yaml
from loguru import logger

from scraper_v2 import ScholarshipScraperV2
from time_parser import parse_relative_time


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


def get_proxy(proxy_pool: List[str], index: int, rotation: str = "sequential") -> Optional[str]:
    """
    Select a proxy from the pool based on rotation strategy.

    Args:
        proxy_pool: List of proxy URLs
        index: Current source index (for sequential rotation)
        rotation: Rotation strategy ("sequential" or "random")

    Returns:
        Proxy URL or None if pool is empty
    """
    if not proxy_pool:
        return None

    if rotation == "random":
        return random.choice(proxy_pool)
    else:  # sequential
        return proxy_pool[index % len(proxy_pool)]


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

    # Proxy configuration
    use_proxy = config_settings.get('use_proxy', False)
    proxy_pool = config_settings.get('proxy_pool', [])
    proxy_rotation = config_settings.get('proxy_rotation', 'sequential')

    # Create output directory
    output_dir.mkdir(exist_ok=True)

    # Filter enabled sources
    enabled_sources = [s for s in sources if s.get('enabled', True)]

    logger.info(f"Found {len(enabled_sources)} enabled sources out of {len(sources)} total")

    # Log proxy configuration
    if use_proxy and proxy_pool:
        logger.info(f"Proxy enabled: {len(proxy_pool)} proxies in pool, rotation: {proxy_rotation}")
    else:
        logger.info("Proxy disabled: using direct connection")

    all_results = {}
    total_scholarships = 0

    # Process each source with its own browser instance to avoid IP/Cloudflare issues
    for idx, source in enumerate(enabled_sources, 1):
        name = source['name']
        label = source['label']
        url = source['url']
        max_pages = source.get('max_pages', 10)

        logger.info(f"\n{'='*70}")
        logger.info(f"[{idx}/{len(enabled_sources)}] Processing: {label} ({name})")
        logger.info(f"URL: {url}")
        logger.info(f"Max pages: {max_pages}")

        # Select proxy if enabled
        proxy = None
        if use_proxy and proxy_pool:
            proxy = get_proxy(proxy_pool, idx - 1, proxy_rotation)
            logger.info(f"Using proxy: {proxy.split('@')[-1] if '@' in proxy else proxy}")

        logger.info(f"{'='*70}\n")

        try:
            # Create new browser instance for each source to avoid browser closure issues
            async with ScholarshipScraperV2(proxy=proxy) as scraper:
                scholarships = await scraper.scrape_url(url, max_pages=max_pages)

                # Add source metadata to each scholarship
                for sch in scholarships:
                    sch['source_name'] = name
                    sch['source_label'] = label
                    sch['source_url'] = url

                # Deduplicate within this source (by URL)
                seen_urls = set()
                unique_scholarships = []
                duplicates_in_source = 0

                for sch in scholarships:
                    url_key = sch.get('url', '')
                    if url_key and url_key not in seen_urls:
                        seen_urls.add(url_key)
                        unique_scholarships.append(sch)
                    else:
                        duplicates_in_source += 1

                all_results[name] = unique_scholarships
                total_scholarships += len(unique_scholarships)

                # Save individual source file (deduplicated)
                source_file = output_dir / f"{name}.json"
                with open(source_file, 'w', encoding='utf-8') as f:
                    json.dump(unique_scholarships, f, ensure_ascii=False, indent=2)

                logger.info(f"✓ Scraped {len(scholarships)} scholarships")
                if duplicates_in_source > 0:
                    logger.info(f"  ⚠ Removed {duplicates_in_source} duplicates within source")
                    logger.info(f"  ✓ Unique: {len(unique_scholarships)} scholarships")
                logger.info(f"✓ Saved to {source_file}")

        except Exception as e:
            logger.error(f"✗ Error scraping {name}: {e}")
            logger.exception(e)  # Print full traceback for debugging
            all_results[name] = []

        # Longer delay between sources to avoid IP blocking
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


def save_combined_output(all_results: Dict[str, List[Dict]], output_file: str, config: dict = None):
    """Save combined output file with all scholarships."""
    output_path = Path(output_file)
    output_path.parent.mkdir(exist_ok=True)

    # Get filter settings from config
    config_settings = config.get('config', {}) if config else {}
    filter_duplicates = config_settings.get('filter_duplicates', True)
    max_days_old = config_settings.get('max_days_old', 0)
    max_total_results = config_settings.get('max_total_results', 0)

    # Flatten all scholarships into single list
    all_scholarships = []
    for scholarships in all_results.values():
        all_scholarships.extend(scholarships)

    logger.info(f"\n{'='*70}")
    logger.info(f"DEDUPLICATION & FILTERING")
    logger.info(f"{'='*70}")
    logger.info(f"Total scraped: {len(all_scholarships)} scholarships")

    # Step 1: Deduplicate by URL (if enabled)
    filtered_scholarships = all_scholarships
    duplicates = 0

    if filter_duplicates:
        seen_urls = set()
        unique_scholarships = []

        for scholarship in all_scholarships:
            url = scholarship.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_scholarships.append(scholarship)
            else:
                duplicates += 1

        filtered_scholarships = unique_scholarships
        logger.info(f"✓ Removed {duplicates} duplicates (by URL)")
        logger.info(f"  After deduplication: {len(filtered_scholarships)} scholarships")

    # Step 2: Filter by age (if enabled)
    old_scholarships = 0
    if max_days_old > 0:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=max_days_old)
        age_filtered = []

        for scholarship in filtered_scholarships:
            posted_time = scholarship.get('posted_time')
            if posted_time:
                try:
                    # Parse ISO format datetime
                    posted_dt = datetime.fromisoformat(posted_time.replace('Z', '+00:00'))
                    if posted_dt >= cutoff_date:
                        age_filtered.append(scholarship)
                    else:
                        old_scholarships += 1
                except (ValueError, AttributeError):
                    # If parsing fails, keep the scholarship
                    age_filtered.append(scholarship)
            else:
                # If no posted_time, keep it
                age_filtered.append(scholarship)

        filtered_scholarships = age_filtered
        logger.info(f"✓ Removed {old_scholarships} scholarships older than {max_days_old} days")
        logger.info(f"  After age filter: {len(filtered_scholarships)} scholarships")

    # Step 3: Limit total results (if enabled)
    truncated = 0
    if max_total_results > 0 and len(filtered_scholarships) > max_total_results:
        truncated = len(filtered_scholarships) - max_total_results
        filtered_scholarships = filtered_scholarships[:max_total_results]
        logger.info(f"✓ Limited to {max_total_results} scholarships (removed {truncated})")

    logger.info(f"\n{'='*70}")
    logger.info(f"FINAL COUNT: {len(filtered_scholarships)} scholarships")
    logger.info(f"{'='*70}")

    # Sort by posted_time (newest first)
    filtered_scholarships.sort(
        key=lambda x: x.get('posted_time') or '',
        reverse=True
    )

    # Add metadata
    output_data = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_scholarships': len(filtered_scholarships),
        'total_scraped': len(all_scholarships),
        'duplicates_removed': duplicates,
        'old_filtered': old_scholarships,
        'truncated': truncated,
        'filters_applied': {
            'deduplication': filter_duplicates,
            'max_days_old': max_days_old if max_days_old > 0 else None,
            'max_total_results': max_total_results if max_total_results > 0 else None
        },
        'sources': {
            name: len(scholarships)
            for name, scholarships in all_results.items()
        },
        'scholarships': filtered_scholarships
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"\n✓ Combined output saved to {output_path}")
    logger.info(f"  Final count: {len(filtered_scholarships)} scholarships")


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
    save_combined_output(all_results, combined_output, config)

    logger.info(f"\n{'='*70}")
    logger.info("✓ Batch scraping completed successfully!")
    logger.info(f"{'='*70}\n")


if __name__ == "__main__":
    asyncio.run(main())
