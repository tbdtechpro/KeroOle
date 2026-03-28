# safaribooks/tests/test_xhtml_extraction.py
"""Tests for _extract_metadata_from_xhtml in KeroOle."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from keroole import KeroOle

# ── Fixtures: real-world XHTML patterns ──────────────────────────────────────

OREILLY_TITLEPAGE = """\
<div id="sbo-rt-content">
<section data-type="titlepage" epub:type="titlepage">
<h1>AI Engineering</h1>
<p class="subtitle">Building Applications with Foundation Models</p>
<p class="author">Chip Huyen</p>
</section>
</div>"""

OREILLY_COPYRIGHT = """\
<div id="sbo-rt-content">
<section data-type="copyright-page" epub:type="copyright-page">
<h1>AI Engineering</h1>
<p class="author">by <span class="firstname">Chip </span><span class="surname">Huyen</span></p>
<p class="publisher">Published by <span class="publishername">O'Reilly Media, Inc.,</span> 1005 Gravenstein Highway North, Sebastopol, CA 95472.</p>
</section>
</div>"""

WILEY_TITLEPAGE = """\
<div id="sbo-rt-content">
<section class="titlePage" epub:type="titlepage">
<h1 class="bookTitle">UNDERSTANDING COLOR</h1>
<div class="authorGroup">
<div class="bookAuthor">
<p class="authorName"><b>Linda Holtzschue</b></p>
</div>
</div>
</section>
</div>"""

WILEY_COPYRIGHT = """\
<div id="sbo-rt-content">
<section class="copyright" epub:type="copyright-page">
<p class="copyright">Copyright 2017 by John Wiley &amp; Sons, Inc.</p>
<p class="copyright">Published by John Wiley &amp; Sons, Inc., Hoboken, New Jersey</p>
</section>
</div>"""

NO_METADATA = """\
<div id="sbo-rt-content">
<section data-type="preface">
<h1>Preface</h1>
<p>Some text without any author or publisher info.</p>
</section>
</div>"""


def _make_sb_with_xhtml(files: dict) -> KeroOle:
    """Build a minimal KeroOle instance backed by temp XHTML files."""
    sb = KeroOle.__new__(KeroOle)
    sb.api_v2 = True
    sb.book_info = {"authors": [], "publishers": []}

    tmpdir = tempfile.mkdtemp()
    oebps  = os.path.join(tmpdir, "OEBPS")
    os.makedirs(oebps)

    chapters = []
    for fname, content in files.items():
        path = os.path.join(oebps, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        chapters.append({"filename": fname})

    sb.BOOK_PATH    = tmpdir
    sb.book_chapters = chapters
    return sb


# ── Author extraction tests ──────────────────────────────────────────────────

def test_extract_authors_oreilly_titlepage():
    sb = _make_sb_with_xhtml({"titlepage01.xhtml": OREILLY_TITLEPAGE})
    authors, _ = sb._extract_metadata_from_xhtml()
    assert authors == [{"name": "Chip Huyen"}]


def test_extract_authors_oreilly_copyright_by_prefix_stripped():
    """The 'by ' prefix on copyright pages must be removed."""
    sb = _make_sb_with_xhtml({"copyright-page01.xhtml": OREILLY_COPYRIGHT})
    authors, _ = sb._extract_metadata_from_xhtml()
    assert authors == [{"name": "Chip Huyen"}]


def test_extract_authors_wiley_authorName_class():
    sb = _make_sb_with_xhtml({"f_01.xhtml": WILEY_TITLEPAGE})
    authors, _ = sb._extract_metadata_from_xhtml()
    assert authors == [{"name": "Linda Holtzschue"}]


def test_extract_authors_no_match_returns_empty():
    sb = _make_sb_with_xhtml({"ch01.xhtml": NO_METADATA})
    authors, _ = sb._extract_metadata_from_xhtml()
    assert authors == []


# ── Publisher extraction tests ───────────────────────────────────────────────

def test_extract_publisher_oreilly_publishername_class():
    sb = _make_sb_with_xhtml({"copyright-page01.xhtml": OREILLY_COPYRIGHT})
    _, publishers = sb._extract_metadata_from_xhtml()
    # "O'Reilly Media, Inc.," — trailing comma stripped
    assert publishers[0]["name"].startswith("O'Reilly Media")


def test_extract_publisher_wiley_published_by_text():
    sb = _make_sb_with_xhtml({"f_02.xhtml": WILEY_COPYRIGHT})
    _, publishers = sb._extract_metadata_from_xhtml()
    assert publishers == [{"name": "John Wiley & Sons, Inc."}]


def test_extract_publisher_no_match_returns_empty():
    sb = _make_sb_with_xhtml({"ch01.xhtml": NO_METADATA})
    _, publishers = sb._extract_metadata_from_xhtml()
    assert publishers == []


# ── html extension normalisation test ────────────────────────────────────────

def test_extract_handles_html_extension_in_chapter_list():
    """book_chapters filenames may end in .html; disk files are .xhtml."""
    sb = KeroOle.__new__(KeroOle)
    sb.api_v2 = True
    sb.book_info = {"authors": [], "publishers": []}

    tmpdir = tempfile.mkdtemp()
    oebps  = os.path.join(tmpdir, "OEBPS")
    os.makedirs(oebps)

    # Write the file with .xhtml extension on disk
    path = os.path.join(oebps, "titlepage01.xhtml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(OREILLY_TITLEPAGE)

    # chapter list uses .html (as the v2 API returns)
    sb.BOOK_PATH     = tmpdir
    sb.book_chapters = [{"filename": "titlepage01.html"}]

    authors, _ = sb._extract_metadata_from_xhtml()
    assert authors == [{"name": "Chip Huyen"}]


# ── Scan-only-first-10-files test ────────────────────────────────────────────

def test_extract_stops_after_finding_both():
    """Should not read all 50 files if author+publisher found in first 2."""
    files = {}
    files["titlepage01.xhtml"] = OREILLY_TITLEPAGE
    files["copyright-page01.xhtml"] = OREILLY_COPYRIGHT
    for i in range(2, 50):
        files[f"ch{i:02d}.xhtml"] = NO_METADATA

    sb = _make_sb_with_xhtml(files)
    authors, publishers = sb._extract_metadata_from_xhtml()
    assert authors    != []
    assert publishers != []
