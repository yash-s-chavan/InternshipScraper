"""
database.py
-----------
SQLite database layer. Tracks every listing ever shown to the user.
Ensures no duplicate listings appear across morning sessions.
"""

# TODO: init_db()       — create tables on first run
# TODO: is_seen(id)     — check if listing was already shown
# TODO: mark_seen()     — insert listing with status='seen'
# TODO: mark_approved() — update status to 'approved' + timestamp
# TODO: mark_skipped()  — update status to 'skipped'
# TODO: get_all_seen()  — fetch all rows (optional status filter)
# TODO: get_stats()     — return total/approved/skipped counts for dashboard header
