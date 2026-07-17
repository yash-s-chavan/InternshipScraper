"""
github_scraper.py
-----------------
Fetches README content from each tracked GitHub repo via the GitHub API.
Calls parser.py to convert markdown tables into structured listing dicts.
Supports adding new repos dynamically via config.json.
"""

# TODO: Implement GitHub API fetching with PAT auth
# TODO: Decode base64 README content
# TODO: Handle rate limiting + retries
# TODO: Call parser.parse_markdown_table() per repo
# TODO: Return combined list of raw listings across all repos
