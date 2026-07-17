"""
google_sheets.py
----------------
Handles all Google Sheets API interactions.
Pushes approved internship listings to the user's Google Sheet.
"""

# TODO: Load credentials from credentials.json (service account)
# TODO: Authenticate with google-auth and build sheets service
# TODO: On first run, create sheet headers:
#       [Company, Role, Location, Match Score, Skills Matched,
#        Apply Link, Date Added, Status, Source Repo]
# TODO: push_listing(listing) — append a new row for an approved listing
# TODO: check_duplicate(listing_id) — avoid double-pushing the same listing
# TODO: get_all_rows() — fetch current sheet state for the dashboard pipeline view
