"""Tests for v2 API response normalizers in SafariBooks."""
import pytest
from safaribooks import API_V2_TEMPLATE, API_V2_CHAPTERS_TEMPLATE, SAFARI_BASE_HOST


def test_v2_constants_have_correct_host():
    assert SAFARI_BASE_HOST in API_V2_TEMPLATE
    assert SAFARI_BASE_HOST in API_V2_CHAPTERS_TEMPLATE


def test_v2_template_formats_book_id():
    url = API_V2_TEMPLATE.format("9781098119058")
    assert url == "https://learning.oreilly.com/api/v2/epubs/urn:orm:book:9781098119058/"


def test_v2_chapters_template_formats_book_id():
    url = API_V2_CHAPTERS_TEMPLATE.format("9781098119058")
    assert url == "https://learning.oreilly.com/api/v2/epub-chapters/?epub_identifier=urn:orm:book:9781098119058"


from unittest.mock import MagicMock
from safaribooks import SafariBooks, SAFARI_BASE_HOST

# Minimal v2 book info response (as returned by the API)
V2_BOOK_INFO = {
    "ourn": "urn:orm:book:9781098119058",
    "identifier": "9781098119058",
    "isbn": "9781098119065",
    "title": "Designing Data-Intensive Applications, 2nd Edition",
    "publication_date": "2026-02-25",
    "descriptions": {
        "text/plain": "Data is at the center of many challenges.",
        "text/html": "<span>Data is at the center.</span>",
    },
    "tags": ["databases", "distributed-systems"],
    "roughcut": False,
}


def _make_safari_books():
    """Return a SafariBooks instance without running __init__ (avoids network calls)."""
    sb = SafariBooks.__new__(SafariBooks)
    sb.book_id = "9781098119058"
    sb.api_v2 = False
    return sb


def test_normalize_v2_book_info_title():
    sb = _make_safari_books()
    result = sb._normalize_v2_book_info(V2_BOOK_INFO)
    assert result["title"] == "Designing Data-Intensive Applications, 2nd Edition"


def test_normalize_v2_book_info_isbn():
    sb = _make_safari_books()
    result = sb._normalize_v2_book_info(V2_BOOK_INFO)
    assert result["isbn"] == "9781098119065"


def test_normalize_v2_book_info_identifier():
    sb = _make_safari_books()
    result = sb._normalize_v2_book_info(V2_BOOK_INFO)
    assert result["identifier"] == "9781098119058"


def test_normalize_v2_book_info_issued():
    sb = _make_safari_books()
    result = sb._normalize_v2_book_info(V2_BOOK_INFO)
    assert result["issued"] == "2026-02-25"


def test_normalize_v2_book_info_description():
    sb = _make_safari_books()
    result = sb._normalize_v2_book_info(V2_BOOK_INFO)
    assert result["description"] == "Data is at the center of many challenges."


def test_normalize_v2_book_info_web_url():
    sb = _make_safari_books()
    result = sb._normalize_v2_book_info(V2_BOOK_INFO)
    assert "9781098119058" in result["web_url"]
    assert SAFARI_BASE_HOST in result["web_url"]
    assert result["web_url"].endswith("/files/")


def test_normalize_v2_book_info_empty_authors():
    sb = _make_safari_books()
    result = sb._normalize_v2_book_info(V2_BOOK_INFO)
    assert result["authors"] == []


def test_normalize_v2_book_info_subjects_from_tags():
    sb = _make_safari_books()
    result = sb._normalize_v2_book_info(V2_BOOK_INFO)
    assert result["subjects"] == [{"name": "databases"}, {"name": "distributed-systems"}]


def test_normalize_v2_book_info_no_cover_key():
    """cover must be absent so the caller's `if "cover" in self.book_info` is False."""
    sb = _make_safari_books()
    result = sb._normalize_v2_book_info(V2_BOOK_INFO)
    assert "cover" not in result
