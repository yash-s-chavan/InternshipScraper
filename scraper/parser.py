"""
parser.py
---------
Parses markdown tables from GitHub internship README files into normalized
listing dicts. Handles multiple repo formats (SpeedyApply HTML-heavy tables
vs plain-text Vansh/Ouckah style). Strips HTML tags, extracts hrefs from
image-link apply buttons, skips closed/locked postings, and generates stable
MD5 IDs per listing.
"""

import hashlib
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Column alias map — maps raw header variants → our canonical field names
# ---------------------------------------------------------------------------
COLUMN_ALIASES = {
    # company
    "company": "company",
    # role / position
    "role": "role",
    "position": "role",
    "title": "role",
    "job title": "role",
    # location
    "location": "location",
    "locations": "location",
    # application link
    "application/link": "link",
    "application": "link",
    "link": "link",
    "apply": "link",
    "posting": "link",
    # salary / compensation
    "salary": "salary",
    "compensation": "salary",
    "pay": "salary",
    # date
    "date posted": "date_posted",
    "date": "date_posted",
    "posted": "date_posted",
    "age": "date_posted",
}

# Markers that indicate a closed posting — skip these rows entirely
CLOSED_MARKERS = {"🔒", "closed", "filled", "expired"}


def _strip_html(text: str) -> str:
    """Remove all HTML tags from a string."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _extract_href(cell: str) -> Optional[str]:
    """
    Pull the first href URL out of an anchor tag inside a table cell.
    Handles both:
      <a href="URL">...</a>
      [text](URL)
    """
    # HTML anchor
    match = re.search(r'href=["\']([^"\']+)["\']', cell)
    if match:
        return match.group(1).strip()
    # Bare markdown link [text](url)
    match = re.search(r'\[.*?\]\((https?://[^)]+)\)', cell)
    if match:
        return match.group(1).strip()
    return None


def _extract_company(cell: str) -> str:
    """
    Extract plain-text company name from a cell that may contain:
      - <a href="..."><strong>Name</strong></a>
      - Plain text
      - ↳ (continuation row — returns empty string so caller can inherit)
    """
    text = _strip_html(cell).strip()
    # Continuation row marker — role belongs to previous company
    if text in ("↳", "⤷", "└"):
        return ""
    return text


def _is_closed(row_cells: list[str]) -> bool:
    """Return True if any cell contains a closed/locked marker."""
    joined = " ".join(row_cells).lower()
    return any(marker in joined for marker in CLOSED_MARKERS)


def _make_id(company: str, role: str, link: Optional[str]) -> str:
    """Generate a stable MD5 ID from company + role + link."""
    raw = f"{company.lower().strip()}|{role.lower().strip()}|{(link or '').strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def _parse_table(table_text: str, source: str) -> list[dict]:
    """
    Parse a single markdown table block into a list of listing dicts.
    `table_text` is the raw markdown for one table including its header row.
    """
    lines = [l for l in table_text.strip().splitlines() if l.strip()]
    if len(lines) < 2:
        return []

    # --- Parse header ---
    header_line = lines[0]
    raw_headers = [h.strip().lower() for h in header_line.strip("|").split("|")]
    canonical_headers = [COLUMN_ALIASES.get(h, h) for h in raw_headers]

    # Skip separator line (line 1: |---|---|...)
    data_lines = lines[2:]

    listings = []
    last_company = ""

    for line in data_lines:
        if not line.strip().startswith("|"):
            continue

        raw_cells = [c.strip() for c in line.strip("|").split("|")]

        # Pad or truncate to match header count
        while len(raw_cells) < len(canonical_headers):
            raw_cells.append("")
        raw_cells = raw_cells[: len(canonical_headers)]

        if _is_closed(raw_cells):
            continue

        row = dict(zip(canonical_headers, raw_cells))

        # Extract company
        company_raw = row.get("company", "")
        company = _extract_company(company_raw)
        if company == "":
            # Continuation row — inherit last seen company
            company = last_company
        else:
            last_company = company

        # Extract role
        role = _strip_html(row.get("role", "")).strip()
        if not role:
            continue  # No role = not a real listing row

        # Extract location
        location = _strip_html(row.get("location", "")).strip()

        # Extract apply link — check the "link" column first, fallback to any cell
        link_cell = row.get("link", "")
        link = _extract_href(link_cell)
        if not link:
            # Fallback: scan all cells for an href
            for cell in raw_cells:
                link = _extract_href(cell)
                if link:
                    break

        # Extract salary
        salary = _strip_html(row.get("salary", "")).strip() or None

        # Extract date
        date_posted = _strip_html(row.get("date_posted", "")).strip() or None

        listing = {
            "id": _make_id(company, role, link),
            "company": company,
            "role": role,
            "location": location,
            "link": link,
            "salary": salary,
            "date_posted": date_posted,
            "source": source,
        }
        listings.append(listing)

    return listings


def parse_readme(readme_content: str, source: str = "") -> list[dict]:
    """
    Main entry point. Given the full README markdown string, find all markdown
    tables, parse each one, and return a combined deduplicated list of listings.

    Skips tables that don't look like job listing tables (no recognized columns).
    """
    all_listings: list[dict] = []
    seen_ids: set[str] = set()

    # Split README into table blocks — a block starts at a header row (| col | col |)
    # and continues until a blank line or non-table line
    table_pattern = re.compile(
        r'(\|[^\n]+\|\n\|[-| :]+\|\n(?:\|[^\n]+\|\n?)*)',
        re.MULTILINE
    )

    tables = table_pattern.findall(readme_content)

    if not tables:
        logger.warning(f"No markdown tables found in README from {source}")
        return []

    for table_text in tables:
        # Quick check: does this table have at least one job-relevant column?
        first_line = table_text.splitlines()[0].lower()
        has_job_column = any(alias in first_line for alias in ["company", "role", "position", "application"])
        if not has_job_column:
            continue

        listings = _parse_table(table_text, source)

        for listing in listings:
            lid = listing["id"]
            if lid not in seen_ids:
                seen_ids.add(lid)
                all_listings.append(listing)

    return all_listings


if __name__ == "__main__":
    # Quick local test — run from project root: python -m scraper.parser
    import json
    import base64
    import requests
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    with open("config.json") as f:
        cfg = json.load(f)

    token = cfg["github_token"]
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}

    repo = cfg["repos"][0]
    url = f"https://api.github.com/repos/{repo['owner']}/{repo['repo']}/readme"
    resp = requests.get(url, headers=headers)
    content = base64.b64decode(resp.json()["content"].replace("\n", "")).decode()

    results = parse_readme(content, source=repo["label"])
    print(f"Parsed {len(results)} listings")
    for r in results[:5]:
        print(r)
