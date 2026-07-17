"""
skill_extractor.py
------------------
Reads resume.pdf and extracts a clean list of skills.
Used to build the user's skill profile that the matcher scores against.
"""

# TODO: Use pdfplumber to extract raw text from resume PDF
# TODO: Match against a curated master skill list (languages, frameworks, tools, clouds)
# TODO: Use rapidfuzz for fuzzy matching to catch "Typescript" vs "TypeScript" etc.
# TODO: Cache extracted skills to skills_cache.json so PDF isn't re-parsed every run
# TODO: Return list of normalized skill strings e.g. ["python", "react", "sql", "aws"]
