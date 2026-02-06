"""Sync scholarship data to Google Sheets."""
import json
import os
from datetime import datetime, timezone
from typing import List, Tuple

import gspread
from gspread.exceptions import WorksheetNotFound
from loguru import logger

from database import get_db, init_db
from models import Scholarship


DEFAULT_COLUMNS: List[Tuple[str, str]] = [
    ("title", "title"),
    ("url", "url"),
    ("university", "university"),
    ("country", "country"),
    ("field_of_study", "field_of_study"),
    ("degree_level", "degree_level"),
    ("deadline", "deadline"),
    ("funding_type", "funding_type"),
    ("application_deadline_text", "application_deadline_text"),
    ("source_id", "source_id"),
    ("scraped_at", "scraped_at"),
    ("updated_at", "updated_at"),
]


def _get_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    return value if value is not None else default


def _service_account_client() -> gspread.Client:
    """Create a gspread client from env-provided credentials."""
    creds_json = _get_env("GOOGLE_SHEETS_CREDENTIALS_JSON").strip()
    creds_file = _get_env("GOOGLE_SHEETS_CREDENTIALS_FILE", "credentials.json").strip()

    if creds_json:
        try:
            data = json.loads(creds_json)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid GOOGLE_SHEETS_CREDENTIALS_JSON") from exc
        return gspread.service_account_from_dict(data)

    if not os.path.exists(creds_file):
        raise FileNotFoundError(
            f"Google Sheets credentials not found. Set GOOGLE_SHEETS_CREDENTIALS_JSON or provide {creds_file}."
        )

    return gspread.service_account(filename=creds_file)


def _format_dt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _build_row(scholarship: Scholarship) -> List[str]:
    row = []
    for _, attr in DEFAULT_COLUMNS:
        value = getattr(scholarship, attr, "")
        if isinstance(value, datetime):
            value = _format_dt(value)
        elif value is None:
            value = ""
        row.append(str(value))
    return row


def _ensure_header(worksheet, columns: List[Tuple[str, str]]) -> int:
    header = worksheet.row_values(1)
    desired = [name for name, _ in columns]

    if not header:
        worksheet.append_row(desired)
        return desired.index("url") + 1

    lowered = [h.strip().lower() for h in header]
    if "url" in lowered:
        return lowered.index("url") + 1

    # Header exists but missing url column; append new header row for safety.
    worksheet.append_row(desired)
    return desired.index("url") + 1


def sync_to_sheets() -> int:
    spreadsheet_id = _get_env("GOOGLE_SHEETS_SPREADSHEET_ID").strip()
    sheet_name = _get_env("GOOGLE_SHEETS_SHEET_NAME", "shcolardb").strip()

    if not spreadsheet_id:
        raise ValueError("Missing GOOGLE_SHEETS_SPREADSHEET_ID")

    client = _service_account_client()
    sheet = client.open_by_key(spreadsheet_id)
    try:
        worksheet = sheet.worksheet(sheet_name)
    except WorksheetNotFound:
        logger.warning(f"Worksheet '{sheet_name}' not found. Creating it.")
        worksheet = sheet.add_worksheet(title=sheet_name, rows=1000, cols=len(DEFAULT_COLUMNS))

    url_col = _ensure_header(worksheet, DEFAULT_COLUMNS)
    existing_urls = set(u.strip() for u in worksheet.col_values(url_col)[1:] if u.strip())

    init_db()
    new_rows: List[List[str]] = []
    seen_urls = set(existing_urls)

    with get_db() as db:
        scholarships = db.query(Scholarship).filter(Scholarship.is_active == True).all()
        for scholarship in scholarships:
            url = (scholarship.url or "").strip()
            if not url or url in seen_urls:
                continue
            new_rows.append(_build_row(scholarship))
            seen_urls.add(url)

    if not new_rows:
        logger.info("No new rows to append to Google Sheets.")
        return 0

    worksheet.append_rows(new_rows, value_input_option="RAW")
    logger.info(f"Appended {len(new_rows)} new rows to Google Sheets.")
    return len(new_rows)


if __name__ == "__main__":
    try:
        count = sync_to_sheets()
        logger.info(f"Sync completed: {count} rows appended.")
    except Exception as exc:
        logger.error(f"Sync failed: {exc}")
        raise
