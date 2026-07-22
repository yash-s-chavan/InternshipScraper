"""
pre_filter.py
-------------
Hard disqualifier layer that runs BEFORE skill matching.
Eliminates listings that are definitively not relevant:

  1. Wrong season  — Fall 2026, Spring 2026, 2026 Start, etc.
  2. Grad-only     — PhD required, Master's only, MS/PhD, etc.
  3. Non-SWE role  — HR, Marketing, Finance, Sales, etc.

Rules are configurable in config.json under the "filters" key:
  {
    "filters": {
      "filter_season":   true,
      "filter_grad_only": true,
      "filter_non_swe":  true
    }
  }
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rule sets
# ---------------------------------------------------------------------------

# Listings that are clearly the wrong season or employment type.
# We keep anything that doesn't match — if no season is mentioned we assume
# it's Summer 2027 (the repos we scrape are labelled as such).
SEASON_REJECT_PATTERNS: List[str] = [
    r"\bfall\s+202[0-6]\b",          # Fall 2020–2026
    r"\bfall\s*\.{2,}",              # Fall... (truncated, year cut off)
    r"\bspring\s+202[0-7]\b",        # Spring 2020–2027
    r"\bspring\s*\.{2,}",            # Spring... (truncated)
    r"\bwinter\s+202[0-7]\b",        # Winter 2020–2027
    r"\bsummer\s+202[0-6]\b",        # Summer 2020–2026 (NOT 2027)
    r"202[0-6]\s*start",             # 2026 Start, 2025 Start
    r"start\s*202[0-6]",             # Start 2026
    r"\bnew[\s\-]?grad(?:uate)?\b",  # New Grad / New Graduate (full-time)
    r"\bco[\s\-]?op\b",              # Co-op (semester-based, not summer)
]

# Listings explicitly requiring a Master's or PhD.
# Exceptions: "BS/MS" means undergrads can also apply — we keep those.
GRAD_KEEP_EXCEPTIONS: List[str] = [
    r"\bbs\s*/\s*ms\b",              # BS/MS
    r"\bbs\s+or\s+ms\b",            # BS or MS
    r"\bbs\s*/\s*ms\s*/\s*phd\b",   # BS/MS/PhD
]

GRAD_REJECT_PATTERNS: List[str] = [
    r"\(ph\.?d",                     # (PhD or (Ph.D
    r"\bph\.?d\.?\s+only\b",        # PhD only
    r"\bph\.?d\s+student",          # PhD student
    r"\bphd\s+intern",              # PhD intern
    r"\bsoftware\s+ph\.?d\b",       # Software PhD
    r"\bms\s*/\s*ph\.?d\b",         # MS/PhD
    r"\bmaster.s?\s*/\s*ph\.?d\b",  # Master's/PhD
    r"\(master",                    # (Master's ...) — any paren containing master
    r"\bmaster.s?\s+only\b",        # Master's only
    r"\bmaster.s?\s+student",       # Master's student
    r"\bgraduate\s+student",        # Graduate student
    r"\bgrad\s+student",            # Grad student
    r"\(ms[,)]",                    # (MS) or (MS, ...) in parens = MS-only
    r"\bms\s+only\b",               # MS only
    r"\bfor\s+graduate\b",          # for graduate students
]

# Roles that are clearly not software engineering.
# The NON-SWE check only fires when the role does NOT contain any SWE keyword —
# so "IT Operations" is fine (has "IT") but "HR Intern" is filtered.
NON_SWE_REJECT_PATTERNS: List[str] = [
    r"\bhr\s+intern",
    r"\bhuman\s+resources",
    r"\btalent\s+acquisition",
    r"\brecruiter\b",
    r"\brecruiting\s+intern",
    r"\bmarketing\s+intern",
    r"\bgrowth\s+intern",
    r"\bcontent\s+(marketing|intern)",
    r"\bbrand\s+intern",
    r"\bsales\s+intern",
    r"\baccount\s+executive",
    r"\bbusiness\s+development\s+intern",
    r"\bfinance\s+intern",
    r"\baccounting\s+intern",
    r"\blegal\s+intern",
    r"\bcompliance\s+intern",
    r"\bsupply\s+chain\s+intern",
    r"\boperations\s+intern",        # "Operations Intern" (not DevOps/Platform)
    r"\bpr\s+intern",
    r"\bcommunications\s+intern",
    r"\bcustomer\s+success\s+intern",
    r"\bsocial\s+media\s+intern",
    r"\bpolicy\s+intern",
    r"\bdesign\s+intern",            # Graphic/Brand Design (not UX/Product)
]

# If ANY of these keywords appear in the role title, it's SWE-adjacent
# and we skip the non-SWE filter.
SWE_ROLE_KEYWORDS: List[str] = [
    "software", "engineer", "developer", "swe", "sde",
    "frontend", "backend", "full stack", "fullstack",
    "data", "machine learning", "ml ", " ml,", "ai ", " ai,",
    "platform", "devops", "dev ops", "site reliability", "sre",
    "cloud", "infrastructure", "mobile", "ios", "android",
    "embedded", "systems", "security", "quantitative", "quant",
    "research scientist", "computer", "firmware", "robotics",
    "simulation", "analytics", "algorithm", "it ", "information tech",
    "product manager", "pm ", "program manager",  # borderline but usually cs grads
    "ux", "ui/ux",                                  # keep product design
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _strip_markdown(text: str) -> str:
    """Remove markdown formatting (bold, italic, links) before pattern matching."""
    text = re.sub(r"\*{1,2}(.*?)\*{1,2}", r"\1", text)  # **bold** / *italic*
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)       # [text](url)
    text = re.sub(r"[\u2019\u2018']", "'", text)            # curly apostrophes
    return text


def _first_match(text: str, patterns: List[str]) -> Optional[str]:
    """Return the first regex pattern that matches text (lowercased), or None."""
    t = _strip_markdown(text).lower()
    for p in patterns:
        if re.search(p, t):
            return p
    return None


def _is_swe_role(role: str) -> bool:
    r = _strip_markdown(role).lower()
    return any(kw in r for kw in SWE_ROLE_KEYWORDS)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def pre_filter(
    listings: List[Dict[str, Any]],
    config: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """
    Apply hard disqualification rules before skill matching.

    Args:
        listings: raw listing dicts from the scraper
        config:   loaded config.json dict

    Returns:
        (kept, counts) where counts tracks how many were dropped per reason
    """
    cfg = config.get("filters", {})
    do_season  = cfg.get("filter_season",    True)
    do_grad    = cfg.get("filter_grad_only", True)
    do_non_swe = cfg.get("filter_non_swe",   True)

    kept: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {
        "season":         0,
        "grad_only":      0,
        "non_swe":        0,
        "total_discarded": 0,
    }

    for listing in listings:
        role    = listing.get("role", "")
        company = listing.get("company", "")
        text    = f"{role} {company}"

        # ── 1. Season filter ────────────────────────────────────────────────
        if do_season:
            if _first_match(text, SEASON_REJECT_PATTERNS):
                counts["season"] += 1
                counts["total_discarded"] += 1
                logger.debug("SEASON discard: %s — %s", company, role[:60])
                continue

        # ── 2. Grad-only filter ─────────────────────────────────────────────
        # NOTE: grad check runs on role only (not company) to avoid false positives.
        # It also runs BEFORE the BS/MS exception so that "(Master's, Summer 2027)"
        # is still caught — the exception only saves "BS/MS" combos.
        if do_grad:
            role_clean = _strip_markdown(role)
            has_exception = bool(_first_match(role_clean, GRAD_KEEP_EXCEPTIONS))
            if not has_exception and _first_match(role_clean, GRAD_REJECT_PATTERNS):
                counts["grad_only"] += 1
                counts["total_discarded"] += 1
                logger.debug("GRAD discard: %s — %s", company, role[:60])
                continue

        # ── 3. Non-SWE filter ───────────────────────────────────────────────
        # Only fires when role has NO SWE keywords (avoids false positives
        # like "IT Operations" or "AI Creator" being caught)
        if do_non_swe:
            if not _is_swe_role(role) and _first_match(role, NON_SWE_REJECT_PATTERNS):
                counts["non_swe"] += 1
                counts["total_discarded"] += 1
                logger.debug("NON-SWE discard: %s — %s", company, role[:60])
                continue

        kept.append(listing)

    logger.info(
        "Pre-filter: %d → %d kept | season=%d grad=%d non-swe=%d",
        len(listings),
        len(kept),
        counts["season"],
        counts["grad_only"],
        counts["non_swe"],
    )
    return kept, counts
