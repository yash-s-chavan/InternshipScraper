"""
matcher.py
----------
Scores each internship listing against the user's extracted skill set.
Produces a 0-100 match score, a tier label, and the list of matched skills.
Filters out listings below the configured threshold and sorts by score descending.
"""

import logging
import re
from typing import List, Dict, Any

from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------
TIERS = [
    (75, "🔥 Strong"),
    (50, "✅ Good"),
    (30, "🟡 Partial"),
    (0,  "⚪ Speculative"),
]

# ---------------------------------------------------------------------------
# Common tech keywords to pull from role titles / location strings.
# These are scored at lower weight than direct skill matches.
# ---------------------------------------------------------------------------
TITLE_KEYWORDS = [
    "frontend", "backend", "full stack", "fullstack", "mobile",
    "ios", "android", "web", "data", "ml", "ai", "cloud", "devops",
    "platform", "infrastructure", "embedded", "security", "qa", "sre",
    "software engineer", "software developer", "intern",
]

# Scoring weights
WEIGHT_SKILL_MATCH  = 3.0   # points per matched skill from user's skill set
WEIGHT_TITLE_KW     = 1.0   # points per title keyword that overlaps with user skills
WEIGHT_ROLE_ALIGN   = 2.5   # bonus per SWE-core keyword hit in the role title
SCORE_CAP           = 100

# Fuzzy threshold for matching skill tokens in a listing's text
FUZZY_THRESHOLD = 78

# Role alignment — keywords that confirm a role is SWE-core.
# Each hit in the role title adds WEIGHT_ROLE_ALIGN bonus points (max 2 hits counted).
SWE_CORE_KEYWORDS = [
    "software", "engineer", "developer", "swe", "sde",
    "frontend", "backend", "full stack", "fullstack",
    "data engineer", "data scientist", "machine learning", "ml engineer",
    "platform", "devops", "site reliability", "sre",
    "cloud", "infrastructure", "embedded", "systems",
    "mobile", "ios", "android", "security", "firmware",
    "quantitative", "research scientist", "computer vision",
    "robotics", "simulation", "analytics engineer",
]


def _tokenize(text: str) -> str:
    """Lowercase and normalize text for matching."""
    return re.sub(r"[^a-z0-9+#.\s]", " ", text.lower())


def _skills_in_text(text: str, user_skills: List[str]) -> List[str]:
    """
    Return which of the user's skills appear (exactly or fuzzily) in `text`.
    """
    normalized = _tokenize(text)
    found = []

    for skill in user_skills:
        # Exact substring check first (fast path)
        if skill in normalized:
            found.append(skill)
            continue

        # Fuzzy match — only run if skill is long enough to be meaningful
        if len(skill) >= 4:
            result = process.extractOne(
                skill,
                normalized.split(),
                scorer=fuzz.partial_ratio,
                score_cutoff=FUZZY_THRESHOLD,
            )
            if result:
                found.append(skill)

    return found


def _title_keywords_present(role: str, user_skills: List[str]) -> List[str]:
    """
    Find TITLE_KEYWORDS in the role string that are also conceptually
    relevant to the user (e.g. "backend" when user has "java").
    Returns matched title keywords for context display.
    """
    normalized = _tokenize(role)
    return [kw for kw in TITLE_KEYWORDS if kw in normalized]


def _get_tier(score: float) -> str:
    for threshold, label in TIERS:
        if score >= threshold:
            return label
    return "⚪ Speculative"


def _role_alignment(role: str) -> float:
    """
    P2: Return a bonus score for how SWE-aligned the role title is.
    Checks for SWE_CORE_KEYWORDS, capped at 2 hits to avoid over-rewarding.
    """
    r = role.lower()
    hits = sum(1 for kw in SWE_CORE_KEYWORDS if kw in r)
    return min(hits, 2) * WEIGHT_ROLE_ALIGN


def score_listing(listing: Dict[str, Any], user_skills: List[str]) -> Dict[str, Any]:
    """
    Score a single listing dict against `user_skills`.
    Adds the following keys to the listing:
        match_score     - int 0-100
        match_tier      - str tier label
        skills_matched  - list of user skills found in the listing
        title_keywords  - list of title keywords matched
        role_aligned    - bool, True if role is SWE-core
    Returns the enriched listing dict.
    """
    corpus = " ".join(filter(None, [
        listing.get("role", ""),
        listing.get("company", ""),
    ]))

    skills_matched = _skills_in_text(corpus, user_skills)
    title_kws      = _title_keywords_present(listing.get("role", ""), user_skills)
    role_bonus     = _role_alignment(listing.get("role", ""))

    # Raw score: skill hits + title keywords + role alignment bonus
    raw = (
        len(skills_matched) * WEIGHT_SKILL_MATCH
        + len(title_kws)    * WEIGHT_TITLE_KW
        + role_bonus
    )

    # Normalizer: "perfect" listing = 5 skill hits + 3 title kws + 2 role alignment hits
    normalizer = (5 * WEIGHT_SKILL_MATCH) + (3 * WEIGHT_TITLE_KW) + (2 * WEIGHT_ROLE_ALIGN)
    score = min(int((raw / normalizer) * 100), SCORE_CAP)

    listing = listing.copy()
    listing["match_score"]    = score
    listing["match_tier"]     = _get_tier(score)
    listing["skills_matched"] = skills_matched
    listing["title_keywords"] = title_kws
    listing["role_aligned"]   = role_bonus > 0

    return listing


def score_listings(
    listings: List[Dict[str, Any]],
    user_skills: List[str],
    threshold: int = 30,
) -> List[Dict[str, Any]]:
    """
    Main entry point. Scores all listings, filters below threshold,
    and returns sorted by match_score descending.

    Args:
        listings:    Raw listing dicts from the scraper.
        user_skills: Normalized skill list from skill_extractor.get_skills().
        threshold:   Minimum match_score to include (from config.json).

    Returns:
        Filtered and sorted list of enriched listing dicts.
    """
    if not user_skills:
        logger.warning("No user skills provided — returning all listings unscored.")
        for listing in listings:
            listing["match_score"] = 0
            listing["match_tier"] = "⚪ Speculative"
            listing["skills_matched"] = []
            listing["title_keywords"] = []
        return listings

    scored = [score_listing(l, user_skills) for l in listings]
    filtered = [l for l in scored if l["match_score"] >= threshold]
    sorted_listings = sorted(filtered, key=lambda l: l["match_score"], reverse=True)

    logger.info(
        f"Scoring complete: {len(listings)} total → "
        f"{len(filtered)} above threshold ({threshold}) → "
        f"top score: {sorted_listings[0]['match_score'] if sorted_listings else 'N/A'}"
    )

    return sorted_listings


if __name__ == "__main__":
    # Quick end-to-end test: scrape + extract skills + score
    import json
    import logging as _logging
    _logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    with open("config.json") as f:
        cfg = json.load(f)

    from engine.skill_extractor import get_skills
    from scraper.github_scraper import scrape_all

    print("Fetching listings...")
    listings = scrape_all(cfg)

    print("Extracting skills from resume...")
    skills = get_skills(cfg.get("resume_path", "resume.pdf"))
    print(f"Skills: {skills}")

    print("Scoring listings...")
    results = score_listings(listings, skills, threshold=cfg.get("skill_match_threshold", 30))

    print(f"\nTop 10 matches ({len(results)} total above threshold):")
    for r in results[:10]:
        print(
            f"  [{r['match_score']:>3}] {r['match_tier']}  "
            f"{r['company']} — {r['role'][:60]}"
            f"\n        Skills: {r['skills_matched']}"
        )
