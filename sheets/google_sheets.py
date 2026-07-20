"""
google_sheets.py
----------------
Handles all Google Sheets API interactions via a service account.
Pushes approved listings as rows and reads back the current sheet state.

Sheet columns (in order):
    Company | Role | Location | Match Score | Skills Matched |
    Apply Link | Salary | Date Posted | Date Added | Source
"""

import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

HEADERS = [
    "Company", "Role", "Location", "Match Score", "Skills Matched",
    "Apply Link", "Salary", "Date Posted", "Date Added", "Source",
]

# Cache the built service so we don't re-auth on every call
_service_cache = None


def _get_service(credentials_file: str):
    """Build and cache the Sheets API service client."""
    global _service_cache
    if _service_cache is not None:
        return _service_cache

    if not os.path.exists(credentials_file):
        raise FileNotFoundError(
            f"Google credentials file not found: {credentials_file}\n"
            "Follow the setup instructions in README.md to create a service account."
        )

    creds = service_account.Credentials.from_service_account_file(
        credentials_file, scopes=SCOPES
    )
    _service_cache = build("sheets", "v4", credentials=creds, cache_discovery=False)
    return _service_cache


def _ensure_headers(service, sheet_id: str) -> None:
    """
    If the sheet is empty (row 1 is blank), write the header row.
    Safe to call on every startup.
    """
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range="A1:J1",
        ).execute()
        existing = result.get("values", [])
        if not existing or existing[0] != HEADERS:
            service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range="A1",
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            ).execute()
            logger.info("Sheet headers written.")
    except HttpError as e:
        logger.error(f"Failed to ensure headers: {e}")
        raise


def _listing_to_row(listing: Dict[str, Any]) -> List[str]:
    """Convert a listing dict to a flat list matching HEADERS order."""
    skills = listing.get("skills_matched", [])
    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
    date_added = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    return [
        listing.get("company", ""),
        listing.get("role", ""),
        listing.get("location", ""),
        str(listing.get("match_score", "")),
        skills_str,
        listing.get("link", ""),
        listing.get("salary", ""),
        listing.get("date_posted", ""),
        date_added,
        listing.get("source", ""),
    ]


def push_listing(listing: Dict[str, Any], sheet_id: str, credentials_file: str) -> bool:
    """
    Append an approved listing as a new row in the Google Sheet.
    Returns True on success, False on error.
    """
    try:
        service = _get_service(credentials_file)
        _ensure_headers(service, sheet_id)

        row = _listing_to_row(listing)
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range="A1",
            valueInputOption="RAW",
            insertDataOption="INSERT_ROWS",
            body={"values": [row]},
        ).execute()

        logger.info(f"Pushed to Sheets: {listing.get('company')} — {listing.get('role')}")
        return True

    except FileNotFoundError as e:
        logger.error(str(e))
        return False
    except HttpError as e:
        logger.error(f"Sheets API error pushing listing {listing.get('id')}: {e}")
        return False


def get_all_rows(sheet_id: str, credentials_file: str) -> List[Dict[str, Any]]:
    """
    Read all rows from the sheet and return as list of dicts keyed by HEADERS.
    Skips the header row. Returns empty list if sheet is empty or creds missing.
    """
    try:
        service = _get_service(credentials_file)
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range="A1:J",
        ).execute()
        rows = result.get("values", [])

        if len(rows) <= 1:
            return []  # Only headers or empty

        # rows[0] is the header row — skip it
        return [
            dict(zip(HEADERS, row + [""] * (len(HEADERS) - len(row))))
            for row in rows[1:]
        ]

    except FileNotFoundError as e:
        logger.warning(str(e))
        return []
    except HttpError as e:
        logger.error(f"Sheets API error reading rows: {e}")
        return []


def check_duplicate(listing: Dict[str, Any], sheet_id: str, credentials_file: str) -> bool:
    """
    Return True if a listing with the same company+role already exists in the sheet.
    Used as a safety guard before pushing.
    """
    rows = get_all_rows(sheet_id, credentials_file)
    company = listing.get("company", "").lower().strip()
    role = listing.get("role", "").lower().strip()

    for row in rows:
        if (
            row.get("Company", "").lower().strip() == company
            and row.get("Role", "").lower().strip() == role
        ):
            return True
    return False
