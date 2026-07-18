"""
skill_extractor.py
------------------
Reads a resume PDF and extracts a normalized list of skills by fuzzy-matching
raw text tokens against a curated master skill list.

Results are cached to skills_cache.json (keyed by PDF modification time)
so the PDF is not re-parsed on every run unless the file changes.
"""

import hashlib
import json
import logging
import os
import re
from typing import List

import pdfplumber
from rapidfuzz import fuzz, process

logger = logging.getLogger(__name__)

CACHE_FILE = "skills_cache.json"

# ---------------------------------------------------------------------------
# Master skill list — canonical lowercase names the matcher will work against.
# Covers languages, frameworks, tools, clouds, and CS concepts.
# ---------------------------------------------------------------------------
MASTER_SKILLS = [
    # Languages
    "python", "java", "javascript", "typescript", "swift", "kotlin", "sql",
    "c", "c++", "c#", "go", "rust", "ruby", "php", "scala", "r", "matlab",
    "bash", "shell", "html", "css",
    # Frameworks & Libraries
    "react", "react native", "node.js", "express", "next.js", "vue", "angular",
    "spring", "spring boot", "django", "flask", "fastapi", "rails",
    "swiftui", "uikit", "jetpack compose",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "junit", "pytest", "jest",
    # Databases
    "postgresql", "mysql", "sqlite", "mongodb", "redis", "cassandra",
    "dynamodb", "firebase", "supabase",
    # Cloud & DevOps
    "aws", "azure", "gcp", "google cloud",
    "ec2", "s3", "lambda", "rds", "cloudformation",
    "docker", "kubernetes", "terraform", "ansible",
    "ci/cd", "github actions", "jenkins", "circleci",
    # Tools & Platforms
    "git", "github", "gitlab", "jira", "confluence", "postman",
    "xcode", "intellij", "pycharm", "vscode", "android studio",
    "linux", "unix",
    # Concepts
    "rest", "restful", "graphql", "grpc", "websocket",
    "multithreading", "concurrency", "virtual threads",
    "microservices", "distributed systems", "system design",
    "data structures", "algorithms",
    "machine learning", "deep learning", "nlp", "computer vision",
    "generative ai", "llm", "prompt engineering",
    # Certifications — captured implicitly via "aws", "github" entries above
    # (multi-word cert names fuzzy-match too broadly against listing text)
]

# Fuzzy match score threshold — below this we don't count it as a hit
FUZZY_THRESHOLD = 82


def _pdf_fingerprint(path: str) -> str:
    """Return an MD5 of the file's mtime + size — cheap change detection."""
    stat = os.stat(path)
    raw = f"{stat.st_mtime}:{stat.st_size}"
    return hashlib.md5(raw.encode()).hexdigest()


def _load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_cache(fingerprint: str, skills: List[str]) -> None:
    cache = _load_cache()
    cache[fingerprint] = skills
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except IOError as e:
        logger.warning(f"Could not write skills cache: {e}")


def _extract_text(pdf_path: str) -> str:
    """Extract all text from every page of the PDF."""
    texts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                texts.append(text)
    return "\n".join(texts)


def _parse_skills_from_text(raw_text: str) -> List[str]:
    """
    Tokenize raw resume text and fuzzy-match every meaningful token/phrase
    against MASTER_SKILLS. Returns deduplicated list of canonical skill names.
    """
    # Normalize: lowercase, collapse whitespace
    text = raw_text.lower()
    # Replace common separators with spaces for cleaner tokenization
    text = re.sub(r"[,|•·/]", " ", text)

    # Build candidate tokens: single words + bigrams + trigrams
    words = text.split()
    candidates = set()

    for i, w in enumerate(words):
        # Skip very short tokens and pure numbers
        if len(w) < 2 or w.isdigit():
            continue
        candidates.add(w)
        if i + 1 < len(words):
            candidates.add(f"{w} {words[i+1]}")
        if i + 2 < len(words):
            candidates.add(f"{w} {words[i+1]} {words[i+2]}")

    matched_skills = set()

    for skill in MASTER_SKILLS:
        # Exact match first (fast path)
        if skill in candidates:
            matched_skills.add(skill)
            continue

        # Fuzzy match against all candidates
        result = process.extractOne(
            skill,
            candidates,
            scorer=fuzz.ratio,
            score_cutoff=FUZZY_THRESHOLD,
        )
        if result:
            matched_skills.add(skill)

    return sorted(matched_skills)


def get_skills(resume_path: str) -> List[str]:
    """
    Main entry point. Returns a list of normalized skill strings extracted
    from the resume at `resume_path`.

    Uses a file-fingerprint cache so the PDF is only re-parsed when it changes.

    Example return:
        ["aws", "docker", "java", "javascript", "python", "react", "sql", ...]
    """
    if not os.path.exists(resume_path):
        logger.error(f"Resume not found at: {resume_path}")
        return []

    fingerprint = _pdf_fingerprint(resume_path)
    cache = _load_cache()

    if fingerprint in cache:
        skills = cache[fingerprint]
        logger.info(f"Skills loaded from cache ({len(skills)} skills)")
        return skills

    logger.info(f"Parsing resume: {resume_path}")
    raw_text = _extract_text(resume_path)
    skills = _parse_skills_from_text(raw_text)
    logger.info(f"Extracted {len(skills)} skills: {skills}")

    _save_cache(fingerprint, skills)
    return skills


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    import json as _json

    with open("config.json") as f:
        cfg = _json.load(f)

    resume_path = cfg.get("resume_path", "resume.pdf")
    skills = get_skills(resume_path)
    print(f"\nExtracted skills ({len(skills)}):")
    for s in skills:
        print(f"  - {s}")
