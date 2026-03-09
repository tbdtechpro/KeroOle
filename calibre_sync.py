"""
calibre_sync.py — Logic for comparing local SafariBooks downloads against a Calibre library.

Public API:
  parse_calibredb_output(raw)  → list of calibre book dicts
  normalize_for_match(text)    → normalized string for comparison
  match_books(local, calibre)  → list of SyncEntry
  run_calibredb_list()         → (raw_output, error_str)
"""

import json
import re
import subprocess
from dataclasses import dataclass
from typing import List


@dataclass
class SyncEntry:
    book_id: str
    title: str
    author: str
    epub_path: str
    match: str   # "none" | "ambiguous" | "definitive"


def normalize_for_match(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_calibredb_output(raw: str) -> list:
    """Parse calibredb --for-machine output, which may be multiple JSON arrays."""
    if not raw.strip():
        return []
    results = []
    for match in re.finditer(r"\[.*?\]", raw, re.DOTALL):
        try:
            chunk = json.loads(match.group())
            if isinstance(chunk, list):
                results.extend(chunk)
        except json.JSONDecodeError:
            continue
    return results


def run_calibredb_list() -> tuple:
    """Run `calibredb list` and return (raw_output, error). Returns ("", error_message) on failure."""
    try:
        result = subprocess.run(
            ["calibredb", "list", "--fields", "title,authors,identifiers", "--for-machine"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return "", result.stderr.strip() or "calibredb list failed"
        return result.stdout, ""
    except FileNotFoundError:
        return "", "calibredb not found — is Calibre installed?"
    except subprocess.TimeoutExpired:
        return "", "calibredb timed out after 60 seconds"


def _book_isbn(book_info: dict) -> str:
    return (book_info.get("isbn") or "").strip()


def _calibre_isbn(calibre_book: dict) -> str:
    return (calibre_book.get("identifiers") or {}).get("isbn", "").strip()


def _first_author(book_info: dict) -> str:
    authors = book_info.get("authors") or []
    if not authors:
        return ""
    return authors[0].get("name", "") if isinstance(authors[0], dict) else str(authors[0])


def match_books(local_books: list, calibre_books: list) -> List[SyncEntry]:
    """
    Compare local books against calibre library.

    local_books: list of dicts with keys: book_id, title, authors, isbn, epub_path
    calibre_books: list of dicts from parse_calibredb_output

    Returns SyncEntry list; books with empty epub_path are skipped.

    Match tiers:
      "definitive" — ISBN match
      "ambiguous"  — title+author normalized match, no ISBN confirmation
      "none"       — no match found
    """
    # Build calibre lookup sets
    calibre_isbns = set()
    calibre_title_author = set()
    for cb in calibre_books:
        isbn = _calibre_isbn(cb)
        if isbn:
            calibre_isbns.add(isbn)
        title = normalize_for_match(cb.get("title") or "")
        author = normalize_for_match(cb.get("authors") or "")
        if title:
            calibre_title_author.add((title, author))

    entries = []
    for lb in local_books:
        epub_path = (lb.get("epub_path") or "").strip()
        if not epub_path:
            continue

        isbn = _book_isbn(lb)
        title = normalize_for_match(lb.get("title") or "")
        author = normalize_for_match(_first_author(lb))

        if isbn and isbn in calibre_isbns:
            match = "definitive"
        elif title and (title, author) in calibre_title_author:
            match = "ambiguous"
        else:
            match = "none"

        entries.append(SyncEntry(
            book_id=lb["book_id"],
            title=lb.get("title") or lb["book_id"],
            author=_first_author(lb),
            epub_path=epub_path,
            match=match,
        ))

    return entries
