"""Generate RSS 2.0 feed from scraped FeedItems."""
from datetime import datetime, timezone
from pathlib import Path
from typing import List
from xml.dom import minidom
from xml.etree.ElementTree import Element, SubElement, tostring

import config
from scrapers import FeedItem


def generate(items: List[FeedItem], output: str = None) -> str:
    output = output or config.RSS_OUTPUT
    Path(output).parent.mkdir(parents=True, exist_ok=True)

    rss = Element("rss", version="2.0", attrib={
        "xmlns:atom": "http://www.w3.org/2005/Atom",
        "xmlns:dc": "http://purl.org/dc/elements/1.1/",
    })
    channel = SubElement(rss, "channel")

    SubElement(channel, "title").text = config.RSS_TITLE
    SubElement(channel, "link").text = config.RSS_LINK
    SubElement(channel, "description").text = f"{len(items)} scholarships"
    SubElement(channel, "lastBuildDate").text = _rfc822(datetime.now(timezone.utc))

    atom_link = SubElement(channel, "atom:link")
    atom_link.set("href", f"{config.RSS_LINK}/feed.xml")
    atom_link.set("rel", "self")
    atom_link.set("type", "application/rss+xml")

    # newest first, capped at max
    min_dt = datetime.min.replace(tzinfo=timezone.utc)
    sorted_items = sorted(items, key=lambda x: x.published or min_dt, reverse=True)
    sorted_items = sorted_items[: config.RSS_MAX_ITEMS]

    for item in sorted_items:
        entry = SubElement(channel, "item")
        SubElement(entry, "title").text = item.title
        SubElement(entry, "link").text = item.url
        SubElement(entry, "guid", isPermaLink="true").text = item.url
        SubElement(entry, "description").text = _build_description(item)
        if item.published:
            SubElement(entry, "pubDate").text = _rfc822(item.published)
        if item.source:
            SubElement(entry, "dc:creator").text = item.source

    xml_str = minidom.parseString(tostring(rss, encoding="unicode")).toprettyxml(indent="  ")
    # Fix declaration encoding label
    lines = xml_str.split("\n")
    lines[0] = '<?xml version="1.0" encoding="UTF-8"?>'
    xml_str = "\n".join(lines)

    with open(output, "w", encoding="utf-8") as f:
        f.write(xml_str)

    return output


def _build_description(item: FeedItem) -> str:
    parts = []
    e = item.extra
    if e.get("university"):
        parts.append(f"<strong>University:</strong> {e['university']}")
    if e.get("country"):
        parts.append(f"<strong>Country:</strong> {e['country']}")
    if e.get("deadline"):
        parts.append(f"<strong>Deadline:</strong> {e['deadline']}")
    if item.description:
        parts.append(f"<p>{item.description}</p>")
    if item.source:
        parts.append(f"<em>Source: {item.source}</em>")
    return "<br/>".join(parts)


def _rfc822(dt: datetime) -> str:
    return dt.strftime("%a, %d %b %Y %H:%M:%S %z")
