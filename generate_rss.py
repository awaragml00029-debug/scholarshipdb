#!/usr/bin/env python
"""Generate RSS feed from scholarship data."""
import json
from datetime import datetime
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom


def generate_rss_feed(input_file='data/all_scholarships.json', output_file='docs/feed.xml', max_items=50):
    """
    Generate RSS 2.0 feed from scholarship data.

    Args:
        input_file: Path to all_scholarships.json
        output_file: Path to output RSS XML file
        max_items: Maximum number of items in feed
    """
    # Load data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    scholarships = data.get('scholarships', [])
    total = data.get('total_scholarships', 0)
    generated_at = data.get('generated_at', datetime.utcnow().isoformat())

    # Sort by posted_time (newest first)
    scholarships.sort(key=lambda x: x.get('posted_time') or '', reverse=True)

    # Limit items
    scholarships = scholarships[:max_items]

    # Create RSS structure
    rss = Element('rss', version='2.0', attrib={
        'xmlns:atom': 'http://www.w3.org/2005/Atom',
        'xmlns:dc': 'http://purl.org/dc/elements/1.1/'
    })

    channel = SubElement(rss, 'channel')

    # Channel metadata
    SubElement(channel, 'title').text = 'PhD Scholarships Database'
    SubElement(channel, 'link').text = 'https://awaragml00029-debug.github.io/scholarshipdb/'
    SubElement(channel, 'description').text = f'Latest PhD scholarship opportunities from around the world. Total: {total} scholarships.'
    SubElement(channel, 'language').text = 'en'
    SubElement(channel, 'lastBuildDate').text = format_rfc822(generated_at)
    SubElement(channel, 'generator').text = 'PhD Scholarship Scraper'

    # Self-referencing atom link
    atom_link = SubElement(channel, '{http://www.w3.org/2005/Atom}link', attrib={
        'href': 'https://awaragml00029-debug.github.io/scholarshipdb/feed.xml',
        'rel': 'self',
        'type': 'application/rss+xml'
    })

    # Add items
    for scholarship in scholarships:
        item = SubElement(channel, 'item')

        # Title
        title = scholarship.get('title', 'Untitled Scholarship')
        university = scholarship.get('university', '')
        if university:
            title = f"{title} - {university}"
        SubElement(item, 'title').text = title

        # Link
        SubElement(item, 'link').text = scholarship.get('url', '')

        # GUID
        SubElement(item, 'guid', isPermaLink='true').text = scholarship.get('url', '')

        # Description
        description = build_description(scholarship)
        SubElement(item, 'description').text = description

        # Publication date
        posted_time = scholarship.get('posted_time')
        if posted_time:
            SubElement(item, 'pubDate').text = format_rfc822(posted_time)

        # Category with domain attribute for better organization
        source_label = scholarship.get('source_label', 'General')
        SubElement(item, 'category', domain='topic').text = source_label

        # Location category
        country = scholarship.get('country')
        if country:
            SubElement(item, 'category', domain='location').text = country

    # Pretty print XML
    xml_str = minidom.parseString(tostring(rss, encoding='utf-8')).toprettyxml(indent='  ', encoding='utf-8')

    # Write to file
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'wb') as f:
        f.write(xml_str)

    print(f"✓ Generated RSS feed: {output_file}")
    print(f"  Items: {len(scholarships)}")
    print(f"  Total scholarships: {total}")


def build_description(scholarship):
    """Build HTML description for RSS item."""
    parts = []

    # University
    university = scholarship.get('university')
    if university:
        parts.append(f"<strong>University:</strong> {university}")

    # Location
    location = scholarship.get('location')
    country = scholarship.get('country')
    if location or country:
        loc_str = ', '.join(filter(None, [location, country]))
        parts.append(f"<strong>Location:</strong> {loc_str}")

    # Posted time
    posted_time_text = scholarship.get('posted_time_text')
    if posted_time_text:
        parts.append(f"<strong>Posted:</strong> {posted_time_text}")

    # Description
    desc = scholarship.get('description')
    if desc:
        parts.append(f"<p>{desc}</p>")

    # Source
    source_label = scholarship.get('source_label')
    if source_label:
        parts.append(f"<em>Source: {source_label}</em>")

    return '<br/>'.join(parts)


def format_rfc822(iso_datetime):
    """Convert ISO datetime to RFC 822 format for RSS."""
    try:
        dt = datetime.fromisoformat(iso_datetime.replace('Z', '+00:00'))
        return dt.strftime('%a, %d %b %Y %H:%M:%S %z')
    except:
        return datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')


if __name__ == '__main__':
    generate_rss_feed()
    print("\n✓ RSS feed generated successfully!")
    print("📡 Subscribe at: https://awaragml00029-debug.github.io/scholarshipdb/feed.xml")
