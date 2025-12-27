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

    # Generate report content
    report_content = generate_report_content(today, new_scholarships, current_scholarships)

    # Save dated report (archive)
    dated_report_file = output_path / f"daily_report_{today}.md"
    with open(dated_report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    # Save as latest.md (always current)
    latest_report_file = output_path / "latest.md"
    with open(latest_report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    logger.info(f"✓ Dated report saved to {dated_report_file}")
    logger.info(f"✓ Latest report saved to {latest_report_file}")

    # Save current as previous for next run
    with open(previous_file, 'w', encoding='utf-8') as f:
        json.dump(current_data, f, ensure_ascii=False, indent=2)

    logger.info(f"✓ Saved current data as previous for next run")

    return len(new_scholarships), dated_report_file


def generate_report_content(today, new_scholarships, current_scholarships):
    """Generate markdown report content."""
    lines = []

    # Header
    lines.append(f"# 📚 PhD 奖学金日报 - {today}\n")
    lines.append(f"**新增奖学金**: {len(new_scholarships)} 条\n")
    lines.append(f"**总数**: {len(current_scholarships)} 条\n")
    lines.append("---\n")

    if not new_scholarships:
        lines.append("🎉 今日无新增奖学金\n")
    else:
        # Group by topic/source (first category)
        by_topic = {}
        for scholarship in new_scholarships:
            topic = scholarship.get('source_label', 'General')
            if topic not in by_topic:
                by_topic[topic] = []
            by_topic[topic].append(scholarship)

        # Write by topic with collapsible sections
        for topic, scholarships in sorted(by_topic.items()):
            lines.append(f"## 📚 {topic}\n")
            lines.append(f"**数量**: {len(scholarships)} 条\n")

            # Collapsible details
            lines.append("<details>\n")
            lines.append("<summary>点击展开查看所有条目</summary>\n\n")

            for idx, scholarship in enumerate(scholarships, 1):
                title = scholarship.get('title', '无标题')
                title_zh = scholarship.get('title_zh', '')
                url = scholarship.get('url', '#')
                country = scholarship.get('country', '')
                university = scholarship.get('university', '')

                # Show number and title
                if title_zh and title_zh != title:
                    lines.append(f"{idx}. **[{title}]({url})**\n")
                    lines.append(f"   - 中文：{title_zh}\n")
                else:
                    lines.append(f"{idx}. **[{title}]({url})**\n")

                # Show university and country on same line if both exist
                if university and country:
                    lines.append(f"   - {university}, {country}\n")
                elif university:
                    lines.append(f"   - {university}\n")
                elif country:
                    lines.append(f"   - {country}\n")

                lines.append("\n")

            lines.append("</details>\n\n")
            lines.append("---\n\n")

    return '\n'.join(lines)


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
