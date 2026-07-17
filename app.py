"""
app.py
------
Flask application entry point.
Starts the web server, runs the scrape pipeline, and serves the dashboard.
Run each morning with: python app.py
"""

# TODO: Load config.json
# TODO: init_db() on startup
# TODO: Run scrape pipeline:
#         1. github_scraper.scrape_all() → raw listings
#         2. Filter out already-seen listings via db.is_seen()
#         3. skill_extractor.get_skills() → user skills
#         4. matcher.score_listings() → scored + sorted listings
#         5. db.mark_seen() for all new listings
# TODO: Serve dashboard at http://localhost:5000

# Routes:
#   GET  /             → render index.html with new listings + stats
#   GET  /api/listings → return new listings as JSON
#   GET  /api/stats    → return pipeline stats (total, approved, skipped)
#   POST /api/approve  → mark listing approved + push to Google Sheets
#   POST /api/skip     → mark listing skipped
#   POST /api/add-repo → add a new GitHub repo to config + re-scrape
#   GET  /api/pipeline → return all approved listings (pipeline view)
