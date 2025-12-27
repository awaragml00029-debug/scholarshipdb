#!/usr/bin/env python
"""Generate daily markdown report with only new scholarships."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger


def generate_daily_report(
    current_file='data/all_scholarships.json',
    previous_file='data/previous_scholarships.json',
    output_dir='reports'
):
    """
    Generate daily markdown report with only new scholarships.

    Args:
        current_file: Current scholarships JSON
        previous_file: Previous day's scholarships JSON
        output_dir: Directory to save reports
    """
    logger.info("Generating daily report...")

    # Load current scholarships
    with open(current_file, 'r', encoding='utf-8') as f:
        current_data = json.load(f)

    current_scholarships = current_data.get('scholarships', [])
    current_urls = {s.get('url') for s in current_scholarships}

    logger.info(f"Current: {len(current_scholarships)} scholarships")

    # Load previous scholarships (if exists)
    previous_urls = set()
    if Path(previous_file).exists():
        with open(previous_file, 'r', encoding='utf-8') as f:
            previous_data = json.load(f)
        previous_scholarships = previous_data.get('scholarships', [])
        previous_urls = {s.get('url') for s in previous_scholarships}
        logger.info(f"Previous: {len(previous_scholarships)} scholarships")
    else:
        logger.info("No previous file found, all scholarships will be marked as new")

    # Find new scholarships
    new_scholarships = [
        s for s in current_scholarships
        if s.get('url') not in previous_urls
    ]

    logger.info(f"New scholarships: {len(new_scholarships)}")

    # Generate markdown report
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    report_file = output_path / f"daily_report_{today}.md"

    with open(report_file, 'w', encoding='utf-8') as f:
        # Header
        f.write(f"# 📚 PhD 奖学金日报 - {today}\n\n")
        f.write(f"**新增奖学金**: {len(new_scholarships)} 条\n\n")
        f.write(f"**总数**: {len(current_scholarships)} 条\n\n")
        f.write("---\n\n")

        if not new_scholarships:
            f.write("🎉 今日无新增奖学金\n")
        else:
            # Group by country
            by_country = {}
            for scholarship in new_scholarships:
                country = scholarship.get('country', '未知')
                if country not in by_country:
                    by_country[country] = []
                by_country[country].append(scholarship)

            # Write by country
            for country, scholarships in sorted(by_country.items()):
                f.write(f"## 🌍 {country}\n\n")
                f.write(f"**数量**: {len(scholarships)} 条\n\n")

                for scholarship in scholarships:
                    title = scholarship.get('title', '无标题')
                    title_zh = scholarship.get('title_zh', '')
                    university = scholarship.get('university', '未知大学')
                    url = scholarship.get('url', '#')
                    posted = scholarship.get('posted_time_text', '未知时间')
                    source = scholarship.get('source_label', '未知来源')

                    f.write(f"### {title}\n\n")

                    if title_zh and title_zh != title:
                        f.write(f"**中文**: {title_zh}\n\n")

                    f.write(f"- **学校**: {university}\n")
                    f.write(f"- **发布时间**: {posted}\n")
                    f.write(f"- **来源**: {source}\n")
                    f.write(f"- **链接**: [{url}]({url})\n\n")

                    description = scholarship.get('description', '')
                    if description:
                        # Truncate description
                        desc_short = description[:200] + '...' if len(description) > 200 else description
                        f.write(f"> {desc_short}\n\n")

                    f.write("---\n\n")

    logger.info(f"✓ Report saved to {report_file}")

    # Save current as previous for next run
    with open(previous_file, 'w', encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ Saved current data as previous for next run")

    return len(new_scholarships), report_file


if __name__ == '__main__':
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    new_count, report_path = generate_daily_report()

    print(f"\n✓ Daily report generated!")
    print(f"  New scholarships: {new_count}")
    print(f"  Report: {report_path}")
