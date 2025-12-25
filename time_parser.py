"""Time parsing utilities for scholarship scraper."""
import re
from datetime import datetime, timedelta, timezone
from loguru import logger


def parse_relative_time(time_text: str) -> datetime:
    """
    Parse relative time strings like 'about 22 hours ago' into absolute datetime.

    Args:
        time_text: Relative time string (e.g., "about 22 hours ago", "3 days ago")

    Returns:
        Absolute datetime in UTC
    """
    now = datetime.now(timezone.utc)
    time_text_lower = time_text.lower().strip()

    # Remove "about" and "ago"
    time_text_lower = time_text_lower.replace('about', '').replace('ago', '').strip()

    try:
        # Extract number and unit
        # Patterns: "22 hours", "3 days", "1 week", "30 minutes"
        match = re.search(r'(\d+)\s*(minute|hour|day|week|month|year)s?', time_text_lower)

        if not match:
            logger.warning(f"Could not parse time: {time_text}")
            return now

        number = int(match.group(1))
        unit = match.group(2)

        # Calculate timedelta
        if unit == 'minute':
            delta = timedelta(minutes=number)
        elif unit == 'hour':
            delta = timedelta(hours=number)
        elif unit == 'day':
            delta = timedelta(days=number)
        elif unit == 'week':
            delta = timedelta(weeks=number)
        elif unit == 'month':
            delta = timedelta(days=number * 30)  # Approximate
        elif unit == 'year':
            delta = timedelta(days=number * 365)  # Approximate
        else:
            logger.warning(f"Unknown time unit: {unit}")
            return now

        result = now - delta
        logger.debug(f"Parsed '{time_text}' -> {result.isoformat()}")
        return result

    except Exception as e:
        logger.error(f"Error parsing time '{time_text}': {e}")
        return now


def format_datetime(dt: datetime) -> str:
    """Format datetime as ISO 8601 string."""
    return dt.isoformat()
