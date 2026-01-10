"""Telegram Bot module for scholarship notifications."""
from .bot import ScholarshipBot
from .notifier import send_new_scholarships, send_daily_digest

__all__ = ['ScholarshipBot', 'send_new_scholarships', 'send_daily_digest']
