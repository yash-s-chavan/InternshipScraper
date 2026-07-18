"""
github_scraper.py
-----------------
Fetches README content from each tracked GitHub repo via the GitHub API.
Decodes base64 content, handles rate limiting with retries, and delegates
markdown parsing to parser.py. Returns a combined list of raw listing dicts
across all active repos.
"""

import base64
import json
import logging
import time

import requests
from typing import Optional

from scraper.parser import parse_readme

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
MAX_RETRIES = 3
RETRY_BACKOFF = 5  # seconds between retries on rate limit


def _get_headers(token: str) -> dict:
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _fetch_readme(owner: str, repo: str, headers: dict) -> Optional[str]:
    """
    Fetch and decode the README content for a given GitHub repo.
    Returns the decoded markdown string, or None on failure.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/readme"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                encoded = data.get("content", "")
                # GitHub encodes content with newlines in the base64 string
                decoded = base64.b64decode(encoded.replace("\n", "")).decode("utf-8")
                return decoded

            elif response.status_code == 403:
                # Rate limit hit — check reset time
                reset_time = int(response.headers.get("X-RateLimit-Reset", time.time() + 60))
                wait = max(reset_time - int(time.time()), RETRY_BACKOFF)
                logger.warning(
                    f"Rate limited on {owner}/{repo}. Waiting {wait}s (attempt {attempt}/{MAX_RETRIES})"
                )
                time.sleep(wait)

            elif response.status_code == 404:
                logger.warning(f"README not found for {owner}/{repo} (404). Skipping.")
                return None

            else:
                logger.warning(
                    f"Unexpected status {response.status_code} for {owner}/{repo} "
                    f"(attempt {attempt}/{MAX_RETRIES})"
                )
                time.sleep(RETRY_BACKOFF)

        except requests.RequestException as e:
            logger.error(f"Network error fetching {owner}/{repo}: {e} (attempt {attempt}/{MAX_RETRIES})")
            time.sleep(RETRY_BACKOFF)

    logger.error(f"Failed to fetch README for {owner}/{repo} after {MAX_RETRIES} attempts.")
    return None


def scrape_all(config: dict) -> list[dict]:
    """
    Main entry point. Iterates over all active repos in config, fetches their
    READMEs, parses listings, and returns the combined deduplicated list.

    Each listing dict contains:
        id          - stable MD5 hash (company+role+link)
        company     - company name (plain text)
        role        - job title
        location    - location string
        link        - direct application URL
        salary      - salary string if available, else None
        date_posted - date string if available, else None
        source      - label from config (e.g. "SpeedyApply 2027")
    """
    token = config.get("github_token", "")
    repos = config.get("repos", [])
    headers = _get_headers(token)

    all_listings: list[dict] = []
    seen_ids: set[str] = set()

    for repo_cfg in repos:
        if not repo_cfg.get("active", True):
            logger.info(f"Skipping inactive repo: {repo_cfg.get('label')}")
            continue

        owner = repo_cfg["owner"]
        repo = repo_cfg["repo"]
        label = repo_cfg.get("label", f"{owner}/{repo}")

        logger.info(f"Fetching README: {owner}/{repo} ({label})")
        readme_content = _fetch_readme(owner, repo, headers)

        if readme_content is None:
            continue

        listings = parse_readme(readme_content, source=label)
        logger.info(f"  → Parsed {len(listings)} listings from {label}")

        # Cross-repo deduplication by listing ID
        for listing in listings:
            lid = listing.get("id")
            if lid and lid not in seen_ids:
                seen_ids.add(lid)
                all_listings.append(listing)
            elif not lid:
                all_listings.append(listing)

    logger.info(f"Total unique listings scraped: {len(all_listings)}")
    return all_listings


if __name__ == "__main__":
    # Quick local test — run from project root: python -m scraper.github_scraper
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    with open("config.json") as f:
        cfg = json.load(f)
    results = scrape_all(cfg)
    print(f"\nTotal listings: {len(results)}")
    for r in results[:5]:
        print(r)
