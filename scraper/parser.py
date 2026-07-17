"""
parser.py
---------
Parses markdown tables from GitHub README files into structured listing dicts.
Normalizes column names across different repo formats (company, role, location, link, date).
Deduplicates listings and skips closed/locked postings.
"""

# TODO: Implement column alias mapping for varied repo formats
# TODO: Extract text + href from markdown link cells [text](url)
# TODO: Generate stable MD5 ID per listing (company+role+link)
# TODO: Skip rows with 🔒 or "closed" markers
# TODO: Return list of normalized listing dicts
