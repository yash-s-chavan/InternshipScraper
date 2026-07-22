"""
app.py
------
Flask application entry point.
Runs the full scrape → score → filter pipeline on startup, then serves the
dashboard and JSON API. Run each morning with: python app.py
"""

import json
import logging
import os
import webbrowser
from threading import Timer

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from db.database import (
    get_all_seen,
    get_listing,
    get_stats,
    init_db,
    is_seen,
    mark_approved,
    mark_seen,
    mark_skipped,
)
from engine.matcher import score_listings
from engine.skill_extractor import get_skills
from scraper.github_scraper import scrape_all
from sheets.google_sheets import check_duplicate, get_all_rows, push_listing

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CONFIG_FILE = "config.json"


def load_config() -> dict:
    with open(CONFIG_FILE) as f:
        return json.load(f)


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# ---------------------------------------------------------------------------
# Pipeline — runs once on startup, results cached in module-level state
# ---------------------------------------------------------------------------
_new_listings: list = []   # scored listings not yet seen by user this session
_user_skills:  list = []   # skills extracted from resume


def run_pipeline(config: dict) -> None:
    """
    Full scrape → skill extract → score → filter pipeline.
    Populates _new_listings with listings the user hasn't seen before.
    """
    global _new_listings, _user_skills

    logger.info("=== Pipeline starting ===")

    # 1. Scrape all active repos
    raw = scrape_all(config)
    logger.info(f"Scraped {len(raw)} total listings")

    # 2. Filter out already-seen listings
    unseen = [l for l in raw if not is_seen(l["id"])]
    logger.info(f"{len(unseen)} new (unseen) listings")

    # 3. Extract skills from resume
    _user_skills = get_skills(config.get("resume_path", "resume.pdf"))
    logger.info(f"User skills ({len(_user_skills)}): {_user_skills}")

    # 4. Score and filter
    threshold = config.get("skill_match_threshold", 30)
    scored = score_listings(unseen, _user_skills, threshold=threshold)
    logger.info(f"{len(scored)} listings above threshold ({threshold})")

    # 5. Mark all unseen listings as seen in DB (whether above threshold or not)
    #    so they never reappear — but only persist the scored ones for display
    for listing in unseen:
        mark_seen(listing)

    _new_listings = scored
    logger.info(f"=== Pipeline complete — {len(_new_listings)} listings ready for review ===")


# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
CORS(app, origins=['http://localhost:5173', 'http://localhost:5001'])  # Vite dev server


@app.route("/")
def index():
    """Render the main dashboard."""
    config = load_config()
    stats = get_stats()
    return render_template(
        "index.html",
        new_count=len(_new_listings),
        stats=stats,
        skills=_user_skills,
        repos=config.get("repos", []),
    )


@app.route("/api/listings")
def api_listings():
    """Return new (unactioned) listings as JSON for the dashboard."""
    return jsonify(_new_listings)


@app.route("/api/stats")
def api_stats():
    """Return aggregate counts: total, approved, skipped, pending."""
    return jsonify(get_stats())


@app.route("/api/approve", methods=["POST"])
def api_approve():
    """
    Mark a listing as approved and push it to Google Sheets.
    Body: { "id": "<listing_id>" }
    """
    data = request.get_json(force=True)
    listing_id = data.get("id")
    if not listing_id:
        return jsonify({"error": "Missing listing id"}), 400

    # Update DB
    if not mark_approved(listing_id):
        return jsonify({"error": "Listing not found in database"}), 404

    # Remove from in-memory new listings
    global _new_listings
    listing = next((l for l in _new_listings if l["id"] == listing_id), None)
    _new_listings = [l for l in _new_listings if l["id"] != listing_id]

    # Push to Google Sheets
    sheets_pushed = False
    if listing:
        config = load_config()
        sheet_id = config.get("google_sheets_id", "")
        creds_file = config.get("credentials_file", "credentials.json")

        if sheet_id and os.path.exists(creds_file):
            if not check_duplicate(listing, sheet_id, creds_file):
                sheets_pushed = push_listing(listing, sheet_id, creds_file)
            else:
                logger.info(f"Skipping duplicate in Sheets: {listing.get('company')}")
                sheets_pushed = True  # Already there — treat as success
        else:
            logger.warning("Google Sheets not configured — skipping push.")

    return jsonify({"ok": True, "sheets_pushed": sheets_pushed})


@app.route("/api/skip", methods=["POST"])
def api_skip():
    """
    Mark a listing as skipped (will never appear again).
    Body: { "id": "<listing_id>" }
    """
    data = request.get_json(force=True)
    listing_id = data.get("id")
    if not listing_id:
        return jsonify({"error": "Missing listing id"}), 400

    if not mark_skipped(listing_id):
        return jsonify({"error": "Listing not found in database"}), 404

    global _new_listings
    _new_listings = [l for l in _new_listings if l["id"] != listing_id]

    return jsonify({"ok": True})


@app.route("/api/add-repo", methods=["POST"])
def api_add_repo():
    """
    Add a new GitHub repo to config.json and re-run the pipeline.
    Body: { "url": "https://github.com/owner/repo" }
    """
    data = request.get_json(force=True)
    url = (data.get("url") or "").strip().rstrip("/")

    if not url or "github.com" not in url:
        return jsonify({"error": "Invalid GitHub URL"}), 400

    parts = url.split("github.com/")[-1].split("/")
    if len(parts) < 2:
        return jsonify({"error": "Could not parse owner/repo from URL"}), 400

    owner, repo = parts[0], parts[1]

    config = load_config()
    existing = [r for r in config.get("repos", []) if r["owner"] == owner and r["repo"] == repo]
    if existing:
        return jsonify({"error": "Repo already tracked"}), 409

    new_repo = {
        "owner": owner,
        "repo": repo,
        "label": f"{owner}/{repo}",
        "active": True,
    }
    config.setdefault("repos", []).append(new_repo)
    save_config(config)

    logger.info(f"Added new repo: {owner}/{repo} — re-running pipeline")
    run_pipeline(config)

    return jsonify({"ok": True, "new_count": len(_new_listings)})


@app.route("/api/pipeline")
def api_pipeline():
    """Return all approved listings from the database (for the pipeline/tracker view)."""
    config = load_config()
    approved = get_all_seen(status_filter="approved")

    # Optionally enrich with live Sheet data for status tracking
    sheet_rows = []
    sheet_id = config.get("google_sheets_id", "")
    creds_file = config.get("credentials_file", "credentials.json")
    if sheet_id and os.path.exists(creds_file):
        sheet_rows = get_all_rows(sheet_id, creds_file)

    return jsonify({"approved": approved, "sheet_rows": sheet_rows})


@app.route("/api/listings/skipped")
def api_listings_skipped():
    """Return all skipped listings from the database."""
    skipped = get_all_seen(status_filter="skipped")
    return jsonify(skipped)



# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    config = load_config()

    # Init DB
    init_db()

    # Run pipeline
    run_pipeline(config)

    # Open browser after a short delay to let Flask start
    Timer(1.2, lambda: webbrowser.open("http://localhost:5001")).start()

    logger.info("Starting Flask on http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
