"""
database.py
-----------
SQLite database layer. Tracks every listing ever shown to the user so
duplicates never appear across morning sessions.

Schema (listings table):
    id            TEXT PRIMARY KEY  — stable MD5 from scraper
    company       TEXT
    role          TEXT
    location      TEXT
    link          TEXT
    salary        TEXT
    date_posted   TEXT
    source        TEXT              — which repo this came from
    match_score   INTEGER
    match_tier    TEXT
    skills_matched TEXT             — JSON array
    status        TEXT              — 'seen' | 'approved' | 'skipped'
    seen_at       TEXT              — ISO timestamp when first shown
    actioned_at   TEXT              — ISO timestamp of approve/skip action
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

DB_PATH = "internships.db"


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row   # rows accessible as dicts
    conn.execute("PRAGMA journal_mode=WAL")  # safe concurrent reads
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Safe to call on every startup."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                id            TEXT PRIMARY KEY,
                company       TEXT NOT NULL,
                role          TEXT NOT NULL,
                location      TEXT,
                link          TEXT,
                salary        TEXT,
                date_posted   TEXT,
                source        TEXT,
                match_score   INTEGER DEFAULT 0,
                match_tier    TEXT,
                skills_matched TEXT DEFAULT '[]',
                status        TEXT NOT NULL DEFAULT 'seen',
                seen_at       TEXT NOT NULL,
                actioned_at   TEXT
            )
        """)
        conn.commit()
    logger.info(f"Database ready: {DB_PATH}")


def is_seen(listing_id: str) -> bool:
    """Return True if this listing has been seen before (any status)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM listings WHERE id = ?", (listing_id,)
        ).fetchone()
    return row is not None


def mark_seen(listing: Dict[str, Any]) -> None:
    """
    Insert a listing with status='seen'. If it already exists, do nothing
    (idempotent — safe to call even if seen check was skipped upstream).
    """
    now = _utcnow()
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO listings
                (id, company, role, location, link, salary, date_posted,
                 source, match_score, match_tier, skills_matched, status, seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'seen', ?)
        """, (
            listing["id"],
            listing.get("company", ""),
            listing.get("role", ""),
            listing.get("location", ""),
            listing.get("link", ""),
            listing.get("salary"),
            listing.get("date_posted"),
            listing.get("source", ""),
            listing.get("match_score", 0),
            listing.get("match_tier", ""),
            json.dumps(listing.get("skills_matched", [])),
            now,
        ))
        conn.commit()


def mark_approved(listing_id: str) -> bool:
    """
    Update a listing's status to 'approved'.
    Returns True if a row was updated, False if listing_id wasn't found.
    """
    now = _utcnow()
    with _connect() as conn:
        cursor = conn.execute("""
            UPDATE listings
            SET status = 'approved', actioned_at = ?
            WHERE id = ?
        """, (now, listing_id))
        conn.commit()
    updated = cursor.rowcount > 0
    if not updated:
        logger.warning(f"mark_approved: no listing found with id={listing_id}")
    return updated


def mark_skipped(listing_id: str) -> bool:
    """
    Update a listing's status to 'skipped'.
    Returns True if a row was updated.
    """
    now = _utcnow()
    with _connect() as conn:
        cursor = conn.execute("""
            UPDATE listings
            SET status = 'skipped', actioned_at = ?
            WHERE id = ?
        """, (now, listing_id))
        conn.commit()
    updated = cursor.rowcount > 0
    if not updated:
        logger.warning(f"mark_skipped: no listing found with id={listing_id}")
    return updated


def get_all_seen(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch all listings from the database, optionally filtered by status
    ('seen', 'approved', 'skipped'). Returns list of dicts.
    """
    with _connect() as conn:
        if status_filter:
            rows = conn.execute(
                "SELECT * FROM listings WHERE status = ? ORDER BY match_score DESC",
                (status_filter,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM listings ORDER BY match_score DESC"
            ).fetchall()

    return [_row_to_dict(r) for r in rows]


def get_listing(listing_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single listing by ID. Returns None if not found."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM listings WHERE id = ?", (listing_id,)
        ).fetchone()
    return _row_to_dict(row) if row else None


def get_stats() -> Dict[str, int]:
    """
    Return aggregate counts for the dashboard header.
    {total, approved, skipped, pending}
    """
    with _connect() as conn:
        total    = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        approved = conn.execute("SELECT COUNT(*) FROM listings WHERE status='approved'").fetchone()[0]
        skipped  = conn.execute("SELECT COUNT(*) FROM listings WHERE status='skipped'").fetchone()[0]
        pending  = conn.execute("SELECT COUNT(*) FROM listings WHERE status='seen'").fetchone()[0]

    return {
        "total": total,
        "approved": approved,
        "skipped": skipped,
        "pending": pending,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    d = dict(row)
    # Deserialize JSON-encoded skills list back to a Python list
    try:
        d["skills_matched"] = json.loads(d.get("skills_matched") or "[]")
    except (json.JSONDecodeError, TypeError):
        d["skills_matched"] = []
    return d
