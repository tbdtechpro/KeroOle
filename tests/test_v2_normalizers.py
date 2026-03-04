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
