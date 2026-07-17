"""
matcher.py
----------
Scores each internship listing against the user's extracted skill set.
Produces a 0-100 match score and assigns a match tier label.
"""

# TODO: For each listing, extract skill keywords from role title + notes + description
# TODO: Compare against user skill list using rapidfuzz partial matching
# TODO: Weight: required skills (high) > preferred skills (medium) > title keywords (low)
# TODO: Assign tier:
#         🔥 Strong  (75-100%)
#         ✅ Good    (50-74%)
#         🟡 Partial (30-49%)
#         ⚪ Speculative (<30%)
# TODO: Attach skills_matched list and match_score to each listing dict
# TODO: Filter out listings below config threshold (default 30%)
# TODO: Sort results by match_score descending
