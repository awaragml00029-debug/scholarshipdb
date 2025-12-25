#!/usr/bin/env python
"""Sync scholarship data to Google Sheets."""
import json
import sys
from pathlib import Path
from datetime import datetime
from loguru import logger

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except ImportError:
    logger.error("Please install required packages: pip install gspread oauth2client")
    sys.exit(1)


def sync_to_google_sheets(
    json_file='data/all_scholarships.json',
    credentials_file='credentials.json',
    sheet_id='1H6kKgCEiJlGHIbdzC-D8487opW9ckXQMhOf6QzpxEsI',
    worksheet_name='Sheet1'
):
    """
    Sync scholarship data to Google Sheets.

    Args:
        json_file: Path to all_scholarships.json
        credentials_file: Path to Google service account credentials
        sheet_id: Google Sheets document ID
        worksheet_name: Name of the worksheet to update
    """
    logger.info(f"Starting Google Sheets sync...")

    # Check credentials file
    if not Path(credentials_file).exists():
        logger.error(f"Credentials file not found: {credentials_file}")
        logger.info("Please upload credentials.json to the project directory")
        return False

    # Load data
    logger.info(f"Loading data from {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    scholarships = data.get('scholarships', [])
    total = data.get('total_scholarships', 0)
    generated_at = data.get('generated_at', '')

    logger.info(f"Found {total} scholarships")

    # Authenticate with Google
    logger.info("Authenticating with Google Sheets API...")
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]

    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(credentials_file, scope)
        client = gspread.authorize(creds)
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False

    # Open the sheet
    logger.info(f"Opening Google Sheet: {sheet_id}")
    try:
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet(worksheet_name)
    except gspread.exceptions.SpreadsheetNotFound:
        logger.error(f"Spreadsheet not found. Make sure the sheet is shared with:")
        logger.error(f"  scholarship-bot@shcolardbjson.iam.gserviceaccount.com")
        return False
    except gspread.exceptions.WorksheetNotFound:
        logger.warning(f"Worksheet '{worksheet_name}' not found, creating it...")
        worksheet = sheet.add_worksheet(title=worksheet_name, rows=1000, cols=20)
    except Exception as e:
        logger.error(f"Failed to open sheet: {e}")
        return False

    # Prepare data for Google Sheets
    logger.info("Preparing data...")

    # Header row
    headers = [
        'Title',
        'University',
        'Location',
        'Country',
        'Posted Date',
        'Posted Text',
        'Source',
        'URL',
        'Description'
    ]

    # Data rows
    rows = [headers]
    for scholarship in scholarships:
        row = [
            scholarship.get('title', ''),
            scholarship.get('university', ''),
            scholarship.get('location', ''),
            scholarship.get('country', ''),
            scholarship.get('posted_time', ''),
            scholarship.get('posted_time_text', ''),
            scholarship.get('source_label', ''),
            scholarship.get('url', ''),
            scholarship.get('description', '')[:500] if scholarship.get('description') else ''  # Limit description length
        ]
        rows.append(row)

    # Clear existing data and write new data
    logger.info(f"Writing {len(rows)} rows to Google Sheets...")
    try:
        worksheet.clear()
        worksheet.update('A1', rows)

        # Format header row
        worksheet.format('A1:I1', {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.4, 'green': 0.6, 'blue': 0.8}
        })

        # Freeze header row
        worksheet.freeze(rows=1)

        # Auto-resize columns
        worksheet.columns_auto_resize(0, len(headers))

        logger.info(f"✓ Successfully synced {total} scholarships to Google Sheets")
        logger.info(f"  Updated at: {generated_at}")
        logger.info(f"  Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")

        return True

    except Exception as e:
        logger.error(f"Failed to write to sheet: {e}")
        return False


if __name__ == '__main__':
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    success = sync_to_google_sheets()

    if success:
        logger.info("\n✓ Google Sheets sync completed successfully!")
    else:
        logger.error("\n✗ Google Sheets sync failed")
        sys.exit(1)
