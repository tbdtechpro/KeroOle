#!/usr/bin/env python3
"""
KeroOle TUI — interactive terminal interface for downloading O'Reilly books.

Requires:
  pip install git+https://github.com/tbdtechpro/bubblepy
  pip install git+https://github.com/tbdtechpro/pygloss
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, List, Optional, Tuple

from platform_utils import find_calibre_binary

import bubblepy as tea
import pygloss
from pygloss import (
    Color,
    Style,
    join_horizontal,
    join_vertical,
    normal_border,
    rounded_border,
    Center,
    Left,
    Top,
)

from keroole import COOKIES_FILE, PATH, KeroOle, KeroOleError, API_V2_TEMPLATE
from retrieve_cookies import parse_cookie_string, get_oreilly_cookies_from_browser, login_with_credentials

# ── Colours ──────────────────────────────────────────────────────────────────

C_ACCENT   = Color("#7C3AED")   # violet
C_GREEN    = Color("#22C55E")
C_RED      = Color("#EF4444")
C_YELLOW   = Color("#EAB308")
C_MUTED    = Color("#6B7280")
C_WHITE    = Color("#F9FAFB")
C_BG_DARK  = Color("#1F2937")
C_SELECTED = Color("#DDD6FE")   # light violet

# ── Shared styles ─────────────────────────────────────────────────────────────

title_style = (
    Style()
    .bold(True)
    .foreground(C_WHITE)
    .background(C_ACCENT)
    .padding(0, 2)
)

panel_style = (
    Style()
    .border(rounded_border())
    .border_foreground(C_ACCENT)
    .padding(1, 2)
)

hint_style   = Style().foreground(C_MUTED).italic(True)
error_style  = Style().foreground(C_RED).bold(True)
success_style = Style().foreground(C_GREEN).bold(True)
label_style  = Style().foreground(C_MUTED)
value_style  = Style().foreground(C_WHITE)
accent_style = Style().foreground(C_ACCENT).bold(True)
cursor_style = Style().foreground(C_SELECTED).bold(True)

# ── ASCII art variants ────────────────────────────────────────────────────────
# Each variant is a list of lines.  Variant 0 is the default (mixed-case KeroOle).
# Additional variants are unlocked via the cheat code system (see Settings).

ASCII_ART_VARIANTS = [
    # 0 — default: mixed-case block art (mono9 style); K and O show uppercase
    #     ascender marks while ero and le sit at lowercase height. ~48 cols wide.
    [
        " \u2584    \u2584                       \u2584\u2584\u2584\u2584  \u2580\u2580\u2588",
        " \u2588  \u2584\u2580   \u2584\u2584\u2584    \u2584 \u2584\u2584   \u2584\u2584\u2584   \u2584\u2580  \u2580\u2584   \u2588     \u2584\u2584\u2584",
        " \u2588\u2584\u2588    \u2588\u2580  \u2588   \u2588\u2580  \u2580 \u2588\u2580 \u2580\u2588  \u2588    \u2588   \u2588    \u2588\u2580  \u2588",
        " \u2588  \u2588\u2584  \u2588\u2580\u2580\u2580\u2580   \u2588     \u2588   \u2588  \u2588    \u2588   \u2588    \u2588\u2580\u2580\u2580\u2580",
        " \u2588   \u2580\u2584 \u2580\u2588\u2584\u2584\u2580   \u2588     \u2580\u2588\u2584\u2588\u2580   \u2588\u2584\u2584\u2588    \u2580\u2584\u2584  \u2580\u2588\u2584\u2584\u2580",
    ],
    # 1 — full block letters, all-caps style (unlockable via cheat code)
    [
        "  \u2588\u2588\u2557  \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2557     \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
        "  \u2588\u2588\u2551 \u2588\u2588\u2554\u255d\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d\u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2554\u2550\u2550\u2550\u2588\u2588\u2557 \u2588\u2588\u2551     \u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d",
        "  \u2588\u2588\u2588\u2588\u2588\u2554\u255d \u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2551   \u2588\u2588\u2551 \u2588\u2588\u2551     \u2588\u2588\u2588\u2588\u2588\u2557  ",
        "  \u2588\u2588\u2554\u2550\u2588\u2588\u2557 \u2588\u2588\u2554\u2550\u2550\u255d  \u2588\u2588\u2554\u2550\u2550\u2588\u2588\u2557\u2588\u2588\u2551   \u2588\u2588\u2551 \u2588\u2588\u2551     \u2588\u2588\u2554\u2550\u2550\u255d  ",
        "  \u2588\u2588\u2551  \u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551  \u2588\u2588\u2551\u255a\u2588\u2588\u2588\u2588\u2588\u2588\u2554\u255d \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557",
        "  \u255a\u2550\u255d  \u255a\u2550\u255d\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u255d  \u255a\u2550\u255d \u255a\u2550\u2550\u2550\u2550\u2550\u255d  \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d",
    ],
    # 2 — minimal dots (unlockable)
    [
        "  \u00b7 K e r o O l e \u00b7",
        "  \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500",
    ],
]

# Active variant index — 0 on startup (mixed-case KeroOle art)
_ascii_art_variant: int = 0


# ── Screens ───────────────────────────────────────────────────────────────────

class Screen(Enum):
    MAIN       = auto()
    LOGIN         = auto()
    COOKIE        = auto()
    ADD_BOOK      = auto()
    QUEUE         = auto()
    DOWNLOAD      = auto()
    CALIBRE       = auto()
    SETTINGS      = auto()
    CALIBRE_SYNC  = auto()
    FAILED_SUMMARY = auto()
    LIBRARY_BROWSE = auto()
    SEARCH         = auto()


# ── Custom messages ───────────────────────────────────────────────────────────

@dataclass
class ProgressMsg(tea.Msg):
    book_id: str
    stage: str
    percent: float   # 0.0–1.0, or -1.0 for stage-only update


@dataclass
class BookDoneMsg(tea.Msg):
    book_id: str
    title: str
    epub_path: str


@dataclass
class BookErrorMsg(tea.Msg):
    book_id: str
    error: str


@dataclass
class BookSkippedMsg(tea.Msg):
    book_id: str


@dataclass
class AllDownloadsDoneMsg(tea.Msg):
    failures: List[dict] = field(default_factory=list)
    log_path: str = ""
    debug_log_path: str = ""


@dataclass
class CalibreMsg(tea.Msg):
    book_id: str
    stage: str    # "converting" | "done" | "error"
    message: str = ""


@dataclass
class AllCalibreDoneMsg(tea.Msg):
    pass


@dataclass
class CalibreSyncDoneMsg(tea.Msg):
    entries: list          # list of SyncEntry
    already_synced: int    # count of definitive matches (hidden from review)
    skipped: int           # count of books with no EPUB
    error: str = ""

@dataclass
class CalibreAddProgressMsg(tea.Msg):
    book_id: str
    stage: str             # "adding" | "done" | "error:..."

@dataclass
class CalibreAddDoneMsg(tea.Msg):
    pass


@dataclass
class LibraryScanDoneMsg(tea.Msg):
    added: int
    error: str = ""


@dataclass
class SearchResult:
    book_id: str
    title: str
    authors_str: str
    publishers_str: str
    issued: str
    page_count: int
    topics_str: str
    description: str
    cover_url: str
    format: str


@dataclass
class SearchDoneMsg(tea.Msg):
    results: list          # list of SearchResult
    total: int
    page: int
    error: str = ""


@dataclass
class LoginResultMsg(tea.Msg):
    cookies: dict
    error: str = ""


@dataclass
class BrowserCookieMsg(tea.Msg):
    cookies: dict
    error: str = ""


@dataclass
class ClipboardMsg(tea.Msg):
    text: str


# ── Download state per book ───────────────────────────────────────────────────

@dataclass
class BookState:
    book_id: str
    title: str = ""
    stage: str = "Queued"
    percent: float = 0.0
    epub_path: str = ""
    calibre_path: str = ""
    error: str = ""
    done: bool = False
    failed: bool = False
    skipped: bool = False   # True when bypassed due to cascade failure
    calibre_done: bool = False
    calibre_failed: bool = False


# ── Progress bar helper ───────────────────────────────────────────────────────

def render_bar(percent: float, width: int = 28) -> str:
    filled = int(percent * width)
    bar = "█" * filled + "░" * (width - filled)
    pct = int(percent * 100)
    filled_style  = Style().foreground(C_ACCENT)
    empty_style   = Style().foreground(C_MUTED)
    filled_str = filled_style.render("█" * filled)
    empty_str  = empty_style.render("░" * (width - filled))
    pct_str    = Style().foreground(C_WHITE if percent < 1.0 else C_GREEN).render(f" {pct:3d}%")
    return filled_str + empty_str + pct_str


# ── Download worker ───────────────────────────────────────────────────────────

class DownloadWorker:
    """Runs book downloads sequentially in a background thread."""

    def __init__(self, book_ids: List[str], program: tea.Program, kindle: bool = False,
                 export_markdown: bool = False, export_obsidian: bool = False,
                 export_db: bool = False, export_rag: bool = False,
                 skip_if_downloaded: bool = False):
        self.book_ids = book_ids
        self.program = program
        self.kindle = kindle
        self.export_markdown = export_markdown
        self.export_obsidian = export_obsidian
        self.export_db = export_db
        self.export_rag = export_rag
        self.skip_if_downloaded = skip_if_downloaded
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        consecutive_failures = 0
        # Each entry: {book_id, title, reason, was_skipped}
        failures: List[dict] = []

        for book_id in self.book_ids:
            # Cascade guard: two consecutive failures → skip remaining books
            if consecutive_failures >= 2:
                self.program.send(BookSkippedMsg(book_id))
                failures.append({
                    "book_id": book_id,
                    "title": self._fetch_book_title(book_id),
                    "reason": "Skipped — multiple preceding downloads failed consecutively.",
                    "was_skipped": True,
                })
                continue

            self.program.send(ProgressMsg(book_id, "Starting…", 0.0))
            try:
                args = argparse.Namespace(
                    bookid=book_id,
                    cred=None,
                    login=False,
                    no_cookies=False,
                    kindle=self.kindle,
                    log=False,
                    export_markdown=self.export_markdown,
                    export_obsidian=self.export_obsidian,
                    export_db=self.export_db,
                    export_rag=self.export_rag,
                    skip_if_downloaded=self.skip_if_downloaded,
                    scan_library=False,
                )

                def cb(stage: str, percent: float, _id=book_id):
                    self.program.send(ProgressMsg(_id, stage, percent))

                sb = KeroOle(args, progress_callback=cb, raise_on_exit=True, quiet=True)
                self.program.send(BookDoneMsg(book_id, sb.book_title, sb.epub_path))
                consecutive_failures = 0

            except KeroOleError as exc:
                consecutive_failures += 1
                title = self._fetch_book_title(book_id)
                failures.append({
                    "book_id": book_id,
                    "title": title,
                    "reason": str(exc),
                    "was_skipped": False,
                })
                self.program.send(BookErrorMsg(book_id, str(exc)))

            except Exception as exc:
                consecutive_failures += 1
                title = self._fetch_book_title(book_id)
                failures.append({
                    "book_id": book_id,
                    "title": title,
                    "reason": f"Unexpected error: {exc}",
                    "was_skipped": False,
                })
                self.program.send(BookErrorMsg(book_id, f"Unexpected error: {exc}"))

        log_path = ""
        debug_log_path = ""
        if failures:
            log_path, debug_log_path = self._write_failure_logs(failures)

        self.program.send(AllDownloadsDoneMsg(
            failures=failures,
            log_path=log_path,
            debug_log_path=debug_log_path,
        ))

    @staticmethod
    def _fetch_book_title(book_id: str) -> str:
        """Minimal API call to retrieve a book title for failure reporting.
        Returns empty string if the lookup fails for any reason."""
        import requests as _req
        try:
            with open(COOKIES_FILE) as f:
                cookies = json.load(f)
            session = _req.Session()
            session.cookies.update(cookies)
            # Try v1 API first
            r = session.get(KeroOle.API_TEMPLATE.format(book_id), timeout=10)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and "title" in data:
                    return data["title"]
            # Fall back to v2 API
            r = session.get(API_V2_TEMPLATE.format(book_id), timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("title", "")
        except Exception:
            pass
        return ""

    @staticmethod
    def _write_failure_logs(failures: List[dict]) -> tuple:
        """Write user-facing and debug failure logs to the Books/ directory.
        Returns (user_log_path, debug_log_path)."""
        books_dir = os.path.join(PATH, "Books")
        os.makedirs(books_dir, exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path   = os.path.join(books_dir, f"failed_downloads_{ts}.txt")
        debug_path = os.path.join(books_dir, f"failed_downloads_debug_{ts}.log")

        failed  = [b for b in failures if not b["was_skipped"]]
        skipped = [b for b in failures if b["was_skipped"]]

        with open(log_path, "w", encoding="utf-8") as f:
            f.write("KeroOle Download Failure Report\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            if failed:
                f.write(f"Books that started downloading but failed ({len(failed)}):\n")
                for b in failed:
                    t = f' — "{b["title"]}"' if b["title"] else ""
                    f.write(f"  • Book {b['book_id']}{t}\n")
                f.write("\n")
            if skipped:
                f.write(f"Books skipped due to preceding download failures ({len(skipped)}):\n")
                for b in skipped:
                    t = f' — "{b["title"]}"' if b["title"] else ""
                    f.write(f"  • Book {b['book_id']}{t}\n")
                f.write("\n")
            f.write(
                "To retry, add these book IDs to the queue in KeroOle.\n"
                f"Debug log (for troubleshooting): {debug_path}\n"
            )

        with open(debug_path, "w", encoding="utf-8") as f:
            f.write("KeroOle Debug Failure Log\n")
            f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")
            for b in failures:
                kind  = "SKIPPED" if b["was_skipped"] else "FAILED"
                title = b["title"] or "(title unavailable)"
                f.write(f"[{kind}] Book {b['book_id']} — {title}\n")
                f.write(f"  Reason: {b['reason']}\n\n")

        return log_path, debug_path


# ── Export-library worker ─────────────────────────────────────────────────────

class ExportLibraryWorker:
    """Runs markdown/db/rag exports against existing Books/ downloads in a background thread."""

    def __init__(self, books_dir: str, book_ids: List[str], program: tea.Program,
                 export_markdown: bool = False, export_obsidian: bool = False,
                 export_db: bool = False, export_rag: bool = False):
        self.books_dir       = books_dir
        self.book_ids        = book_ids   # pre-scanned list in display order
        self.program         = program
        self.export_markdown = export_markdown
        self.export_obsidian = export_obsidian
        self.export_db       = export_db
        self.export_rag      = export_rag
        if export_rag:
            self.export_db = True
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        import re as _re
        from config import load_export_config, book_folder_name
        from library import BookRegistry, parse_epub_contents
        books_dir = self.books_dir

        exp_cfg = load_export_config()
        db_path = exp_cfg.resolved_db_path() or os.path.join(books_dir, "library.db")
        reg     = BookRegistry(db_path)

        _dir_re = _re.compile(r'^.+\((\w+)\)$')

        for entry in sorted(os.scandir(books_dir), key=lambda e: e.name):
            if not entry.is_dir():
                continue
            m = _dir_re.match(entry.name)
            if not m:
                continue
            book_id  = m.group(1)
            book_dir = entry.path

            self.program.send(ProgressMsg(book_id, "Parsing EPUB…", 0.05))
            try:
                book_info, chapters, toc_data = parse_epub_contents(book_dir)
            except FileNotFoundError:
                self.program.send(BookErrorMsg(book_id, "content.opf not found"))
                continue
            except Exception as exc:
                self.program.send(BookErrorMsg(book_id, str(exc)))
                continue

            title  = book_info.get("title") or book_id
            folder = book_folder_name(book_info, book_id, exp_cfg.folder_name_style)

            try:
                markdown_map = None
                if self.export_markdown:
                    self.program.send(ProgressMsg(book_id, "Exporting Markdown…", 0.3))
                    from exporters import MarkdownExporter
                    md_output_dir = exp_cfg.resolved_markdown_dir()
                    exporter = MarkdownExporter(
                        book_id=book_id,
                        book_path=book_dir,
                        book_info=book_info,
                        chapters=chapters,
                        output_dir=md_output_dir,
                        folder_name=folder,
                    )
                    markdown_map = exporter.export()

                if self.export_obsidian:
                    self.program.send(ProgressMsg(book_id, "Exporting Obsidian…", 0.4))
                    from exporters import ObsidianExporter
                    obs_output_dir = exp_cfg.resolved_markdown_obsidian_dir()
                    obs_exporter = ObsidianExporter(
                        book_id=book_id,
                        book_path=book_dir,
                        book_info=book_info,
                        chapters=chapters,
                        output_dir=obs_output_dir,
                        folder_name=folder,
                    )
                    obs_exporter.export()

                if self.export_db:
                    self.program.send(ProgressMsg(book_id, "Storing in DB…", 0.7))
                    reg.store_chapters(
                        book_id=book_id,
                        chapters=chapters,
                        book_path=book_dir,
                        markdown_map=markdown_map,
                    )
                    if toc_data:
                        reg.store_toc(book_id, toc_data)

                if self.export_rag:
                    self.program.send(ProgressMsg(book_id, "Exporting RAG JSONL…", 0.9))
                    from exporters import RagExporter
                    rag_base = exp_cfg.resolved_rag_dir() or os.path.join(book_dir, "rag")
                    os.makedirs(rag_base, exist_ok=True)
                    output_path = os.path.join(rag_base, folder + "_rag.jsonl")
                    exporter = RagExporter(
                        book_id=book_id,
                        book_info=book_info,
                        chapters=chapters,
                        book_path=book_dir,
                        markdown_map=markdown_map,
                    )
                    exporter.export(output_path)

                self.program.send(BookDoneMsg(book_id, title, ""))
            except Exception as exc:
                self.program.send(BookErrorMsg(book_id, str(exc)))

        reg.close()
        self.program.send(AllDownloadsDoneMsg())


# ── Calibre sync worker ───────────────────────────────────────────────────────

class CalibreSyncWorker:
    """Scans Books/ and calibredb to find unsynced books."""

    def __init__(self, books_dir: str, program: tea.Program):
        self.books_dir = books_dir
        self.program   = program
        self._thread   = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        import re as _re
        from calibre_sync import run_calibredb_list, parse_calibredb_output, match_books
        from library import parse_epub_contents

        # 1. Query calibredb
        raw, err = run_calibredb_list()
        if err:
            self.program.send(CalibreSyncDoneMsg(entries=[], already_synced=0, skipped=0, error=err))
            return
        calibre_books = parse_calibredb_output(raw)

        # 2. Scan Books/
        _dir_re = _re.compile(r'^.+\((\w+)\)$')
        local_books = []
        try:
            dir_entries = sorted(os.scandir(self.books_dir), key=lambda e: e.name)
        except OSError as exc:
            self.program.send(CalibreSyncDoneMsg(entries=[], already_synced=0, skipped=0,
                                                  error=f"Cannot read Books directory: {exc}"))
            return
        for entry in dir_entries:
            if not entry.is_dir():
                continue
            m = _dir_re.match(entry.name)
            if not m:
                continue
            book_id  = m.group(1)
            book_dir = entry.path

            # Find EPUB
            epub_path = ""
            try:
                for f in os.listdir(book_dir):
                    if f.endswith(".epub"):
                        epub_path = os.path.join(book_dir, f)
                        break
            except OSError:
                pass

            try:
                book_info, _, _ = parse_epub_contents(book_dir)
            except Exception:
                book_info = {}

            local_books.append({
                "book_id":   book_id,
                "title":     book_info.get("title") or book_id,
                "authors":   book_info.get("authors") or [],
                "isbn":      book_info.get("isbn") or "",
                "epub_path": epub_path,
            })

        # 3. Match
        entries    = match_books(local_books, calibre_books)
        definitive = [e for e in entries if e.match == "definitive"]
        visible    = [e for e in entries if e.match != "definitive"]
        skipped    = sum(1 for lb in local_books if not lb["epub_path"])

        self.program.send(CalibreSyncDoneMsg(
            entries=visible,
            already_synced=len(definitive),
            skipped=skipped,
        ))


# ── O'Reilly Search worker ────────────────────────────────────────────────────

class SearchWorker:
    """Searches O'Reilly Learning API in a background thread."""

    SEARCH_URL = "https://learning.oreilly.com/api/v1/search/"

    def __init__(self, query: str, format_filter: str, topic: str, publisher: str,
                 sort: str, page: int, program: tea.Program):
        self.query         = query
        self.format_filter = format_filter  # "book", "video", or "" for all
        self.topic         = topic
        self.publisher     = publisher
        self.sort          = sort           # "relevance" or "created_time"
        self.page          = page
        self.program       = program
        self._thread       = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        import json as _json
        try:
            session = self._make_session()
            params = {"query": self.query, "limit": 10, "page": self.page}
            if self.format_filter:
                params["formats"] = self.format_filter
            if self.topic:
                params["topics"] = self.topic
            if self.publisher:
                params["publishers"] = self.publisher
            if self.sort == "created_time":
                params["sort"] = "created_time"

            resp = session.get(self.SEARCH_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            results = []
            for item in data.get("results", []):
                authors = [a.get("name", "") for a in item.get("authors", [])]
                pubs    = [p.get("name", "") for p in item.get("publishers", [])]
                topics  = [t.get("name", "") for t in item.get("topics", [])][:4]
                results.append(SearchResult(
                    book_id=str(item.get("archive_id", "")),
                    title=item.get("title", ""),
                    authors_str=", ".join(authors),
                    publishers_str=", ".join(pubs),
                    issued=(item.get("issued") or "")[:4],   # year only
                    page_count=item.get("virtual_pages", 0) or 0,
                    topics_str=", ".join(topics),
                    description=item.get("description", ""),
                    cover_url=item.get("cover", ""),
                    format=item.get("format", "book"),
                ))
            total = data.get("total", len(results))
            self.program.send(SearchDoneMsg(results=results, total=total, page=self.page))
        except Exception as exc:
            self.program.send(SearchDoneMsg(results=[], total=0, page=self.page,
                                            error=str(exc)))

    @staticmethod
    def _make_session():
        """Build a requests Session loaded with saved cookies."""
        import requests as _req
        session = _req.Session()
        session.headers.update({"Accept": "application/json"})
        if os.path.isfile(COOKIES_FILE):
            try:
                import json as _json
                with open(COOKIES_FILE) as f:
                    cookies = _json.load(f)
                session.cookies.update(cookies)
            except Exception:
                pass
        return session


# ── Calibre add worker ────────────────────────────────────────────────────────

class CalibreAddWorker:
    """Runs `calibredb add` for each selected SyncEntry."""

    def __init__(self, entries: list, program: tea.Program):
        self.entries = entries
        self.program = program
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        for entry in self.entries:
            self.program.send(CalibreAddProgressMsg(entry.book_id, "adding"))
            try:
                result = subprocess.run(
                    [find_calibre_binary("calibredb"), "add", entry.epub_path],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0:
                    self.program.send(CalibreAddProgressMsg(entry.book_id, "done"))
                else:
                    err = (result.stderr or result.stdout or "unknown error").strip()[:80]
                    self.program.send(CalibreAddProgressMsg(entry.book_id, f"error:{err}"))
            except subprocess.TimeoutExpired:
                self.program.send(CalibreAddProgressMsg(entry.book_id, "error:timed out"))
            except Exception as exc:
                self.program.send(CalibreAddProgressMsg(entry.book_id, f"error:{exc}"))

        self.program.send(CalibreAddDoneMsg())


# ── Calibre worker ────────────────────────────────────────────────────────────

class CalibreWorker:
    """Runs calibre ebook-convert on each downloaded EPUB in a background thread."""

    def __init__(self, books: List[BookState], program: tea.Program,
                 delete_original: bool = False):
        self.books = books
        self.program = program
        self.delete_original = delete_original
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        self._thread.start()

    def _run(self):
        for book in self.books:
            if not book.epub_path or not os.path.isfile(book.epub_path):
                self.program.send(CalibreMsg(book.book_id, "error", "EPUB not found"))
                continue

            self.program.send(CalibreMsg(book.book_id, "converting"))
            out_path = book.epub_path.replace(".epub", "_calibre.epub")
            try:
                result = subprocess.run(
                    [
                        find_calibre_binary("ebook-convert"),
                        book.epub_path,
                        out_path,
                        "--no-default-epub-cover",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
                if result.returncode == 0:
                    if self.delete_original and os.path.isfile(out_path):
                        try:
                            os.remove(book.epub_path)
                        except OSError:
                            pass
                    self.program.send(CalibreMsg(book.book_id, "done", out_path))
                else:
                    err = (result.stderr or result.stdout or "unknown error").strip()
                    self.program.send(CalibreMsg(book.book_id, "error", err[:200]))
            except FileNotFoundError:
                self.program.send(CalibreMsg(book.book_id, "error", "`ebook-convert` not found — is Calibre installed?"))
            except subprocess.TimeoutExpired:
                self.program.send(CalibreMsg(book.book_id, "error", "Calibre conversion timed out"))
            except Exception as exc:
                self.program.send(CalibreMsg(book.book_id, "error", str(exc)))

        self.program.send(AllCalibreDoneMsg())


# ── App model ─────────────────────────────────────────────────────────────────

class AppModel(tea.Model):

    MENU_ITEMS = [
        ("Extract Cookies from Browser", "BROWSER"),
        ("Set Session Cookie (paste)",   Screen.COOKIE),
        ("Login with Email/Password",    Screen.LOGIN),
        ("Search O'Reilly",              Screen.SEARCH),
        ("Add Book to Queue",            Screen.ADD_BOOK),
        ("View / Run Queue",             Screen.QUEUE),
        ("Browse Library",               Screen.LIBRARY_BROWSE),
        ("Sync with Calibre Library",    Screen.CALIBRE_SYNC),
        ("Export Paths / Settings",      Screen.SETTINGS),
        ("Quit",                         None),
    ]

    def __init__(self):
        self.screen: Screen = Screen.MAIN
        self.width:  int = 80
        self.height: int = 24

        # main menu
        self.menu_cursor: int = 0

        # login screen
        self.login_email: str = ""
        self.login_password: str = ""
        self.login_field: int = 0          # 0 = email, 1 = password
        self.login_status: str = ""
        self.login_running: bool = False

        # cookie screen
        self.cookie_input: str = ""
        self.cookie_saved: bool = os.path.isfile(COOKIES_FILE)
        self.cookie_status: str = ""
        self.cookie_retrieving: bool = False

        # add-book screen
        self.book_id_input: str = ""
        self.add_book_status: str = ""
        self.multi_book_mode: bool = False
        self.multi_book_input: str = ""

        # queue
        self.queue: List[str] = []

        # export toggles
        self.export_markdown: bool = False
        self.export_obsidian: bool = False
        self.export_db: bool = False
        self.export_rag: bool = False
        self.skip_if_downloaded: bool = False

        # download / calibre state
        self.books: dict[str, BookState] = {}   # book_id -> BookState
        self.dl_order: List[str] = []           # insertion order
        self.calibre_running: bool = False
        self.all_calibre_done: bool = False
        self.status_msg: str = ""
        self.dl_label: str = "Downloading"      # header for the download screen
        self.export_library_mode: bool = False  # True when running export-library
        self.dl_scroll: int = 0                 # scroll offset for download screen

        # failure summary state (populated when downloads finish with errors)
        self.failed_books: List[dict] = []
        self.failure_log_path: str = ""
        self.failure_debug_log_path: str = ""

        # library browse screen (Phase 1C)
        self.lib_books: list = []           # from get_all_books()
        self.lib_cursor: int = 0
        self.lib_scroll: int = 0
        self.lib_selected: set = set()
        self.lib_filter: str = ""           # title filter text
        self.lib_filter_mode: bool = False  # True when in /filter mode
        self.lib_status: str = ""

        # search screen (Phase 1A)
        self.search_query: str = ""
        self.search_topic: str = ""
        self.search_publisher: str = ""
        self.search_format: str = "book"    # "book", "video", ""
        self.search_sort: str = "relevance" # "relevance" or "created_time"
        self.search_results: list = []
        self.search_cursor: int = 0
        self.search_scroll: int = 0
        self.search_selected: set = set()   # book_ids to add to queue
        self.search_page: int = 1
        self.search_total: int = 0
        self.search_status: str = ""
        self.search_running: bool = False
        # search form phase: "form" (entering query) or "results" (viewing results)
        self.search_phase: str = "form"
        # which form field is focused: 0=query, 1=topic, 2=publisher
        self.search_field: int = 0

        # settings screen
        from config import load_export_config
        _cfg = load_export_config()
        self.settings_fields: List[str] = [
            _cfg.markdown_dir,
            _cfg.rag_dir,
            _cfg.db_path,
            _cfg.folder_name_style,        # "title" or "id"
            _cfg.markdown_gfm_dir,         # GFM output dir
            _cfg.markdown_obsidian_dir,    # Obsidian vault dir
        ]
        self.settings_delete_original: bool = _cfg.delete_original_epub
        self.settings_cursor: int = 0   # which field is focused
        self.settings_status: str = ""
        self.settings_action_status: str = ""   # "ok:..." or "error:..."
        self.settings_scanning: bool = False
        # Cheat code sub-section
        self.cheat_input: str = ""
        self.cheat_status: str = ""   # "ok:..." or "error:..."
        self.cheat_input_focused: bool = False

        # calibre sync screen
        self.sync_scanning: bool       = False
        self.sync_entries: list        = []   # list of SyncEntry (non-definitive only)
        self.sync_already_synced: int  = 0
        self.sync_skipped: int         = 0
        self.sync_selected: set        = set()
        self.sync_cursor: int          = 0
        self.sync_scroll: int          = 0
        self.sync_adding: bool         = False
        self.sync_add_status: dict     = {}   # book_id → "adding"|"done"|"error:msg"
        self.sync_all_done: bool       = False
        self.sync_error: str           = ""

        # program reference set after Program() creation
        self._program: Optional[tea.Program] = None

        # Apply any previously unlocked cheats
        self._apply_cheats()

    # ── tea.Model interface ────────────────────────────────────────────────

    def init(self) -> Optional[tea.Cmd]:
        return tea.window_size()

    def update(self, msg: tea.Msg) -> Tuple["AppModel", Optional[tea.Cmd]]:
        if isinstance(msg, tea.WindowSizeMsg):
            self.width  = msg.width
            self.height = msg.height
            return self, None

        if isinstance(msg, tea.KeyMsg):
            return self._handle_key(msg.key)

        if isinstance(msg, tea.PasteMsg):
            if self.screen == Screen.LOGIN:
                if self.login_field == 0:
                    self.login_email = msg.text.strip()
                else:
                    self.login_password = msg.text.strip()
            elif self.screen == Screen.COOKIE:
                self.cookie_input = msg.text.strip()
            elif self.screen == Screen.ADD_BOOK:
                if self.multi_book_mode:
                    self.multi_book_input += msg.text
                else:
                    self.book_id_input = msg.text.strip()
            return self, None

        if isinstance(msg, ProgressMsg):
            self._on_progress(msg)
            return self, None

        if isinstance(msg, BookDoneMsg):
            self._on_book_done(msg)
            return self, None

        if isinstance(msg, BookErrorMsg):
            self._on_book_error(msg)
            return self, None

        if isinstance(msg, BookSkippedMsg):
            self._on_book_skipped(msg)
            return self, None

        if isinstance(msg, AllDownloadsDoneMsg):
            self.failed_books = msg.failures
            self.failure_log_path = msg.log_path
            self.failure_debug_log_path = msg.debug_log_path
            if not self.export_library_mode:
                self._start_calibre()
            else:
                self.all_calibre_done = True  # signal "all done" so footer updates
            return self, None

        if isinstance(msg, CalibreMsg):
            self._on_calibre(msg)
            return self, None

        if isinstance(msg, AllCalibreDoneMsg):
            self.all_calibre_done = True
            if self.failed_books:
                self.screen = Screen.FAILED_SUMMARY
            return self, None

        if isinstance(msg, CalibreSyncDoneMsg):
            self.sync_scanning = False
            if msg.error:
                self.sync_error = msg.error
            else:
                self.sync_entries        = msg.entries
                self.sync_already_synced = msg.already_synced
                self.sync_skipped        = msg.skipped
                self.sync_selected = {
                    e.book_id for e in msg.entries if e.match == "none"
                }
            return self, None

        if isinstance(msg, CalibreAddProgressMsg):
            self.sync_add_status[msg.book_id] = msg.stage
            return self, None

        if isinstance(msg, CalibreAddDoneMsg):
            self.sync_adding   = False
            self.sync_all_done = True
            return self, None

        if isinstance(msg, LibraryScanDoneMsg):
            self.settings_scanning = False
            if msg.error:
                self.settings_action_status = f"error:{msg.error}"
            else:
                self.settings_action_status = f"ok:{msg.added} book(s) added to registry"
            return self, None

        if isinstance(msg, LoginResultMsg):
            self.login_running = False
            if msg.cookies:
                with open(COOKIES_FILE, "w") as f:
                    json.dump(msg.cookies, f)
                self.cookie_saved = True
                self.login_status = "ok:Logged in and cookies saved."
            else:
                self.login_status = f"error:{msg.error or 'Login failed — check your credentials.'}"
            return self, None

        if isinstance(msg, BrowserCookieMsg):
            self.cookie_retrieving = False
            if msg.cookies:
                with open(COOKIES_FILE, "w") as f:
                    json.dump(msg.cookies, f)
                self.cookie_saved = True
                self.cookie_status = f"ok:Saved {len(msg.cookies)} cookies from browser."
            else:
                self.cookie_status = (
                    f"error:{msg.error or 'Browser extraction failed — try the CLI tool instead.'}"
                )
            return self, None

        if isinstance(msg, ClipboardMsg):
            if self.screen == Screen.COOKIE:
                if msg.text:
                    self.cookie_input = msg.text
                    self.cookie_status = f"ok:{len(msg.text)} chars read from clipboard — press Enter to save."
                else:
                    self.cookie_status = "error:Could not read clipboard."
            elif self.screen == Screen.ADD_BOOK:
                if msg.text:
                    if self.multi_book_mode:
                        self.multi_book_input += msg.text
                        self.add_book_status = ""
                    else:
                        self.book_id_input = msg.text.strip()
                        self.add_book_status = ""
                else:
                    self.add_book_status = "error:Could not read clipboard."
            return self, None

        if isinstance(msg, SearchDoneMsg):
            self.search_running = False
            if msg.error:
                self.search_status = "error:" + msg.error
            else:
                self.search_results = msg.results
                self.search_total   = msg.total
                self.search_page    = msg.page
                self.search_cursor  = 0
                self.search_scroll  = 0
                self.search_status  = ""
                if msg.results:
                    self.search_phase = "results"
                else:
                    self.search_status = "No results found."
            return self, None

        return self, None

    # ── Key handling ───────────────────────────────────────────────────────

    def _handle_key(self, key: str) -> Tuple["AppModel", Optional[tea.Cmd]]:
        if key == "ctrl+c":
            return self, tea.quit_cmd

        dispatch = {
            Screen.MAIN:     self._key_main,
            Screen.LOGIN:    self._key_login,
            Screen.COOKIE:   self._key_cookie,
            Screen.ADD_BOOK: self._key_add_book,
            Screen.QUEUE:    self._key_queue,
            Screen.DOWNLOAD: self._key_download,
            Screen.CALIBRE:        self._key_calibre,
            Screen.SETTINGS:       self._key_settings,
            Screen.CALIBRE_SYNC:   self._key_calibre_sync,
            Screen.FAILED_SUMMARY: self._key_failed_summary,
            Screen.LIBRARY_BROWSE: self._key_library_browse,
            Screen.SEARCH:         self._key_search,
        }
        handler = dispatch.get(self.screen)
        if handler:
            return handler(key)
        return self, None

    def _visible_menu_items(self) -> list:
        from config import load_unlocked_cheats as _luc
        _cheats = _luc()
        show_email = "show_email_login" in _cheats
        return [
            (label, dest) for label, dest in self.MENU_ITEMS
            if not (label == "Login with Email/Password" and not show_email)
        ]

    def _key_main(self, key: str):
        items = self._visible_menu_items()
        n = len(items)
        if key in ("up", "k"):
            self.menu_cursor = (self.menu_cursor - 1) % n
        elif key in ("down", "j"):
            self.menu_cursor = (self.menu_cursor + 1) % n
        elif key in ("enter", " "):
            _, target = items[self.menu_cursor]
            if target is None:
                return self, tea.quit_cmd
            if target == "BROWSER":
                self.screen = Screen.COOKIE
                self.cookie_status = ""
                self._retrieve_from_browser()
            else:
                if target == Screen.CALIBRE_SYNC:
                    self._start_calibre_sync()
                    return self, None
                if target == Screen.LIBRARY_BROWSE:
                    self._load_library_books()
                    self.lib_cursor = 0
                    self.lib_scroll = 0
                    self.lib_filter = ""
                    self.lib_filter_mode = False
                    self.lib_status = ""
                if target == Screen.SEARCH:
                    self.search_phase = "form"
                    self.search_field = 0
                    self.search_results = []
                    self.search_status = ""
                    self.search_running = False
                self.screen = target
                self.cookie_status = ""
                self.add_book_status = ""
        elif key == "q":
            return self, tea.quit_cmd
        return self, None

    def _key_login(self, key: str):
        if self.login_running:
            return self, None
        if key == "escape":
            self.screen = Screen.MAIN
            self.login_status = ""
        elif key in ("tab", "down", "enter") and self.login_field == 0:
            self.login_field = 1
        elif key in ("shift+tab", "up") and self.login_field == 1:
            self.login_field = 0
        elif key == "enter" and self.login_field == 1:
            self._do_login()
        elif key in ("backspace", "delete"):
            if self.login_field == 0:
                self.login_email = self.login_email[:-1]
            else:
                self.login_password = self.login_password[:-1]
            self.login_status = ""
        elif key == "ctrl+u":
            if self.login_field == 0:
                self.login_email = ""
            else:
                self.login_password = ""
            self.login_status = ""
        elif len(key) == 1 and key.isprintable():
            if self.login_field == 0:
                self.login_email += key
            else:
                self.login_password += key
            self.login_status = ""
        return self, None

    def _key_cookie(self, key: str):
        if key == "escape":
            self.screen = Screen.MAIN
        elif key == "enter":
            self._save_cookie()
        elif key in ("backspace", "delete"):
            self.cookie_input = self.cookie_input[:-1]
            self.cookie_status = ""
        elif key == "ctrl+u":
            self.cookie_input = ""
            self.cookie_status = ""
        elif key == "ctrl+v":
            self._read_clipboard()
        elif key in ("b", "B") and not self.cookie_retrieving:
            self._retrieve_from_browser()
        elif len(key) == 1:
            self.cookie_input += key
            self.cookie_status = ""
        return self, None

    def _key_add_book(self, key: str):
        if self.multi_book_mode:
            if key == "escape":
                # Esc from multi mode: return to single mode (stay on ADD_BOOK)
                self.multi_book_mode = False
                self.multi_book_input = ""
                self.add_book_status = ""
            elif key == "enter":
                self._add_multi_books_to_queue()
            elif key in ("m", "M"):
                self.multi_book_mode = False
                self.multi_book_input = ""
                self.add_book_status = ""
            elif key == "backspace":
                self.multi_book_input = self.multi_book_input[:-1]
                self.add_book_status = ""
            elif key == "ctrl+u":
                self.multi_book_input = ""
                self.add_book_status = ""
            elif key == "ctrl+v":
                self._read_clipboard_book()
            elif len(key) == 1 and key.isprintable():
                self.multi_book_input += key
                self.add_book_status = ""
        else:
            if key == "escape":
                self.screen = Screen.MAIN
                self.book_id_input = ""
            elif key == "enter":
                self._add_book_to_queue()
            elif key in ("m", "M"):
                self.multi_book_mode = True
                self.multi_book_input = ""
                self.add_book_status = ""
            elif key == "backspace":
                self.book_id_input = self.book_id_input[:-1]
                self.add_book_status = ""
            elif key == "ctrl+u":
                self.book_id_input = ""
                self.add_book_status = ""
            elif key == "ctrl+v":
                self._read_clipboard_book()
            elif len(key) == 1 and key.isprintable():
                self.book_id_input += key
                self.add_book_status = ""
        return self, None

    def _key_queue(self, key: str):
        if key == "escape":
            self.screen = Screen.MAIN
        elif key in ("a", "A"):
            self.screen = Screen.ADD_BOOK
        elif key in ("r", "R"):
            self._start_downloads()
        elif key in ("s", "S"):
            self.screen = Screen.COOKIE
            self.cookie_status = ""
        elif key in ("c", "C"):
            # clear queue
            self.queue.clear()
        elif key in ("m", "M"):
            self.export_markdown = not self.export_markdown
        elif key in ("o", "O"):
            self.export_obsidian = not self.export_obsidian
        elif key in ("d", "D"):
            self.export_db = not self.export_db
        elif key in ("x", "X"):
            self.export_rag = not self.export_rag
        elif key in ("k", "K"):
            self.skip_if_downloaded = not self.skip_if_downloaded
        elif key in ("e", "E"):
            self._start_export_library()
        return self, None

    def _key_download(self, key: str):
        if self.all_calibre_done and key in ("q", "escape"):
            self.screen = Screen.MAIN
            return self, None
        total = len(self.dl_order)
        if key in ("up", "k"):
            self.dl_scroll = max(0, self.dl_scroll - 1)
        elif key in ("down", "j"):
            self.dl_scroll = min(max(0, total - 1), self.dl_scroll + 1)
        return self, None

    def _key_calibre(self, key: str):
        if self.all_calibre_done and key in ("q", "enter", "escape"):
            self.screen = Screen.MAIN
            return self, None
        return self, None

    def _key_settings(self, key: str):
        # Field indices: 0=md_dir, 1=rag_dir, 2=db_path, 3=folder_style(toggle),
        #                4=gfm_dir, 5=obsidian_dir, 6=delete_original(toggle)
        #                | 7=Scan btn, 8=Clear btn
        _TEXT_FIELDS = {0, 1, 2, 4, 5}
        n = 9  # 6 text/toggle fields + 1 bool toggle + 2 action buttons
        if key == "escape":
            self.screen = Screen.MAIN
            self.settings_status = ""
        elif key in ("tab", "down"):
            self.settings_cursor = (self.settings_cursor + 1) % n
            self.settings_status = ""
        elif key in ("shift+tab", "up"):
            self.settings_cursor = (self.settings_cursor - 1) % n
            self.settings_status = ""
        elif self.settings_cursor == 3:
            # Toggle field — space/enter/left/right cycle between "title" and "id"
            if key in ("enter", " ", "left", "right", "h", "l"):
                cur = self.settings_fields[3]
                self.settings_fields[3] = "id" if cur == "title" else "title"
                self.settings_status = ""
        elif self.settings_cursor == 6:
            # Toggle bool — delete_original_epub
            if key in ("enter", " "):
                self.settings_delete_original = not self.settings_delete_original
                self._save_settings()
        elif key == "enter" and self.settings_cursor in _TEXT_FIELDS:
            self._save_settings()
        elif self.settings_cursor in _TEXT_FIELDS and key in ("backspace", "delete"):
            val = self.settings_fields[self.settings_cursor]
            self.settings_fields[self.settings_cursor] = val[:-1]
            self.settings_status = ""
        elif self.settings_cursor in _TEXT_FIELDS and key == "ctrl+u":
            self.settings_fields[self.settings_cursor] = ""
            self.settings_status = ""
        elif self.settings_cursor in _TEXT_FIELDS and len(key) == 1 and key.isprintable():
            self.settings_fields[self.settings_cursor] += key
            self.settings_status = ""
        elif self.settings_cursor == 7 and key == "enter":
            self._run_scan_library()
        elif self.settings_cursor == 8 and key == "enter":
            self._run_clear_chapter_db()
        # Cheat code input — active when cheat_input_focused
        if self.cheat_input_focused:
            if key == "escape":
                self.cheat_input_focused = False
                self.cheat_input = ""
                self.cheat_status = ""
            elif key in ("backspace", "delete"):
                self.cheat_input = self.cheat_input[:-1]
            elif key == "ctrl+u":
                self.cheat_input = ""
            elif key == "enter":
                if self.cheat_input:
                    self._enter_cheat_code(self.cheat_input)
                    self.cheat_input = ""
                self.cheat_input_focused = False
            elif len(key) == 1 and key.isprintable():
                self.cheat_input += key
        elif key == "c" and self.settings_cursor not in _TEXT_FIELDS and not self.cheat_input_focused:
            # 'c' on a non-text field activates cheat input
            self.cheat_input_focused = True
            self.cheat_status = ""
        return self, None

    def _save_settings(self):
        from config import ExportConfig, save_export_config
        cfg = ExportConfig(
            markdown_dir=self.settings_fields[0].strip(),
            rag_dir=self.settings_fields[1].strip(),
            db_path=self.settings_fields[2].strip(),
            folder_name_style=self.settings_fields[3],
            markdown_gfm_dir=self.settings_fields[4].strip(),
            markdown_obsidian_dir=self.settings_fields[5].strip(),
            delete_original_epub=self.settings_delete_original,
        )
        try:
            save_export_config(cfg)
            self.settings_status = "ok:Settings saved to ~/.keroole.toml"
        except Exception as exc:
            self.settings_status = f"error:Save failed — {exc}"

    def _apply_cheats(self) -> None:
        """Apply all currently unlocked cheats (called on startup and after each unlock)."""
        global _ascii_art_variant
        from config import load_unlocked_cheats
        unlocked = load_unlocked_cheats()
        # ASCII art — highest numbered unlocked variant wins
        for variant_idx in range(len(ASCII_ART_VARIANTS) - 1, 0, -1):
            if f"ascii_variant_{variant_idx}" in unlocked:
                _ascii_art_variant = variant_idx
                break
        # Other effects are applied via settings_fields / menu filtering
        # (show_email_login is read by _get_visible_menu_items at render time)

    def _enter_cheat_code(self, code: str) -> None:
        """Try to unlock a cheat code and apply effects immediately."""
        from config import unlock_cheat, cheat_description
        try:
            already, effect = unlock_cheat(code)
            desc = cheat_description(effect)
            if already:
                self.cheat_status = f"ok:Already unlocked: {desc}"
            else:
                self.cheat_status = f"ok:Unlocked — {desc}"
            self._apply_cheats()
        except ValueError:
            self.cheat_status = "error:Unknown code"

    def _run_scan_library(self):
        if self.settings_scanning:
            return
        self.settings_scanning = True
        self.settings_action_status = "ok:Scanning…"

        def _worker():
            import os as _os
            from config import load_export_config
            from library import BookRegistry
            books_dir = _os.path.join(PATH, "Books")
            exp_cfg = load_export_config()
            db_path = exp_cfg.resolved_db_path() or _os.path.join(books_dir, "library.db")
            try:
                reg = BookRegistry(db_path)
                try:
                    added = reg.scan_existing_books(books_dir)
                finally:
                    reg.close()
                self._program.send(LibraryScanDoneMsg(added=added))
            except Exception as exc:
                self._program.send(LibraryScanDoneMsg(added=0, error=str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _run_clear_chapter_db(self):
        import os as _os
        from config import load_export_config
        from library import BookRegistry
        books_dir = _os.path.join(PATH, "Books")
        exp_cfg = load_export_config()
        db_path = exp_cfg.resolved_db_path() or _os.path.join(books_dir, "library.db")
        try:
            reg = BookRegistry(db_path)
            try:
                reg.clear_chapter_db()
            finally:
                reg.close()
            self.settings_action_status = "ok:Chapter data cleared"
        except Exception as exc:
            self.settings_action_status = f"error:{exc}"

    # ── Business logic ─────────────────────────────────────────────────────

    def _do_login(self):
        email = self.login_email.strip()
        password = self.login_password
        if not email:
            self.login_status = "error:Please enter your email."
            self.login_field = 0
            return
        if not password:
            self.login_status = "error:Please enter your password."
            return
        self.login_running = True
        self.login_status = ""

        def _worker():
            cookies = login_with_credentials(email, password)
            self._program.send(LoginResultMsg(
                cookies=cookies,
                error="" if cookies else "Login failed — check your credentials.",
            ))

        threading.Thread(target=_worker, daemon=True).start()

    def _save_cookie(self):
        raw = self.cookie_input.strip()
        if not raw:
            self.cookie_status = "error:No cookie value entered."
            return
        try:
            cookies = parse_cookie_string(raw)
        except json.JSONDecodeError:
            self.cookie_status = "error:Invalid JSON format."
            return
        except Exception as exc:
            self.cookie_status = f"error:Parse error: {exc}"
            return
        if not cookies:
            self.cookie_status = (
                "error:Could not parse cookies — paste the full Cookie header value."
            )
            return
        with open(COOKIES_FILE, "w") as f:
            json.dump(cookies, f)
        self.cookie_saved = True
        self.cookie_input = ""
        self.cookie_status = "ok:Saved."

    def _retrieve_from_browser(self):
        self.cookie_retrieving = True
        self.cookie_status = ""

        def _worker():
            cookies = get_oreilly_cookies_from_browser()
            self._program.send(BrowserCookieMsg(
                cookies=cookies,
                error="" if cookies else "No O'Reilly cookies found in browser.",
            ))

        threading.Thread(target=_worker, daemon=True).start()

    def _read_clipboard(self):
        """Read clipboard content via pyperclip and deliver as ClipboardMsg."""
        self.cookie_status = "ok:Reading clipboard…"
        self._read_clipboard_impl()

    def _read_clipboard_book(self):
        """Read clipboard content and deliver as ClipboardMsg for the add-book screen."""
        self._read_clipboard_impl()

    def _read_clipboard_impl(self):
        """Shared clipboard worker — sends ClipboardMsg("") on any failure."""
        def _worker():
            try:
                import pyperclip
                text = pyperclip.paste()
                self._program.send(ClipboardMsg(text.strip() if text else ""))
            except Exception:
                self._program.send(ClipboardMsg(""))
        threading.Thread(target=_worker, daemon=True).start()

    def _cookie_age_mins(self) -> int:
        """Minutes since cookies.json was last written, or -1 if file is missing."""
        if not os.path.isfile(COOKIES_FILE):
            return -1
        return int((time.time() - os.path.getmtime(COOKIES_FILE)) / 60)

    def _cookie_age_str(self) -> str:
        mins = self._cookie_age_mins()
        if mins < 0:
            return ""
        if mins < 1:
            return "< 1 min ago"
        if mins == 1:
            return "1 min ago"
        return f"{mins} min ago"

    def _add_book_to_queue(self):
        book_id = self.book_id_input.strip()
        if not book_id:
            self.add_book_status = "error:Please enter a book ID."
            return
        if not book_id.isdigit():
            self.add_book_status = "error:Book ID must be numeric."
            return
        if book_id in self.queue:
            self.add_book_status = "error:Book already in queue."
            return
        self.queue.append(book_id)
        self.book_id_input = ""
        self.add_book_status = f"ok:Added {book_id} to queue."

    def _add_multi_books_to_queue(self):
        text = self.multi_book_input.strip()
        if not text:
            self.add_book_status = "error:Please paste or type book IDs first."
            return
        # Any non-digit characters are treated as delimiters; extract numeric runs
        ids = re.findall(r'\d+', text)
        if not ids:
            self.add_book_status = "error:No numeric IDs found in the pasted text."
            return
        added, dupes = 0, 0
        for bid in ids:
            if bid not in self.queue:
                self.queue.append(bid)
                added += 1
            else:
                dupes += 1
        self.multi_book_input = ""
        if added == 0:
            self.add_book_status = "error:All IDs already in queue."
        elif dupes:
            self.add_book_status = f"ok:Added {added} book(s) — {dupes} duplicate(s) skipped."
        else:
            self.add_book_status = f"ok:Added {added} book(s) to queue."

    def _start_downloads(self):
        if not self.queue:
            return
        if not os.path.isfile(COOKIES_FILE):
            self.status_msg = "No cookies.json found — press 's' to set your cookie first."
            return

        # Initialise state entries
        self.dl_order = list(self.queue)
        for book_id in self.dl_order:
            self.books[book_id] = BookState(book_id=book_id)
        self.queue.clear()

        self.dl_label = "Downloading"
        self.export_library_mode = False
        self.dl_scroll = 0
        self.screen = Screen.DOWNLOAD
        worker = DownloadWorker(
            self.dl_order, self._program,
            export_markdown=self.export_markdown,
            export_obsidian=self.export_obsidian,
            export_db=self.export_db,
            export_rag=self.export_rag,
            skip_if_downloaded=self.skip_if_downloaded,
        )
        worker.start()

    def _load_library_books(self):
        """Reload lib_books from the registry DB."""
        from config import load_export_config
        exp_cfg = load_export_config()
        books_dir = os.path.join(PATH, "Books")
        db_path = exp_cfg.resolved_db_path() or os.path.join(books_dir, "library.db")
        try:
            from library import BookRegistry
            reg = BookRegistry(db_path)
            self.lib_books = reg.get_all_books()
            reg.close()
        except Exception:
            self.lib_books = []

    def _start_export_library(self, selected_ids=None):
        """Start library export. If selected_ids is given, export only those books."""
        if not (self.export_markdown or self.export_obsidian or self.export_db or self.export_rag):
            self.status_msg = "Select at least one export format (m/o/d/x) before running."
            return

        import re as _re
        books_dir = os.path.join(PATH, "Books")
        if not os.path.isdir(books_dir):
            self.status_msg = "Books/ directory not found."
            return

        # Quick scan — just directory names, no file I/O
        _dir_re = _re.compile(r'^.+\((\w+)\)$')
        book_ids = []
        for entry in sorted(os.scandir(books_dir), key=lambda e: e.name):
            if entry.is_dir() and _dir_re.match(entry.name):
                m = _dir_re.match(entry.name)
                book_ids.append(m.group(1))

        # Filter to selected_ids when provided (Library Browse per-book export)
        if selected_ids:
            book_ids = [bid for bid in book_ids if bid in selected_ids]

        if not book_ids:
            self.status_msg = "No downloaded books found in Books/."
            return

        self.dl_order = book_ids
        self.books = {bid: BookState(book_id=bid) for bid in book_ids}
        self.all_calibre_done = False
        self.calibre_running = False
        self.dl_label = "Exporting Library"
        self.export_library_mode = True
        self.dl_scroll = 0
        self.status_msg = ""
        self.screen = Screen.DOWNLOAD

        worker = ExportLibraryWorker(
            books_dir=books_dir,
            book_ids=book_ids,
            program=self._program,
            export_markdown=self.export_markdown,
            export_obsidian=self.export_obsidian,
            export_db=self.export_db,
            export_rag=self.export_rag,
        )
        worker.start()

    def _start_calibre(self):
        successful = [self.books[bid] for bid in self.dl_order if not self.books[bid].failed]
        if not successful:
            self.all_calibre_done = True
            if self.failed_books:
                self.screen = Screen.FAILED_SUMMARY
            return
        self.calibre_running = True
        self.screen = Screen.CALIBRE
        from config import load_export_config as _lec
        exp_cfg = _lec()
        CalibreWorker(successful, self._program,
                      delete_original=exp_cfg.delete_original_epub).start()

    # ── Progress callbacks (called from worker threads via program.send) ───

    def _on_progress(self, msg: ProgressMsg):
        if msg.book_id not in self.books:
            self.books[msg.book_id] = BookState(book_id=msg.book_id)
        b = self.books[msg.book_id]
        b.stage = msg.stage
        if msg.percent >= 0:
            b.percent = msg.percent

    def _on_book_done(self, msg: BookDoneMsg):
        if msg.book_id not in self.books:
            self.books[msg.book_id] = BookState(book_id=msg.book_id)
        b = self.books[msg.book_id]
        b.title     = msg.title
        b.epub_path = msg.epub_path
        b.done      = True
        b.percent   = 1.0
        b.stage     = "Download complete"

    def _on_book_error(self, msg: BookErrorMsg):
        if msg.book_id not in self.books:
            self.books[msg.book_id] = BookState(book_id=msg.book_id)
        b = self.books[msg.book_id]
        b.error  = msg.error
        b.failed = True
        b.stage  = "Failed"

    def _on_book_skipped(self, msg: BookSkippedMsg):
        if msg.book_id not in self.books:
            self.books[msg.book_id] = BookState(book_id=msg.book_id)
        b = self.books[msg.book_id]
        b.skipped = True
        b.failed  = True   # treated as failed so Calibre skips it too
        b.stage   = "Skipped"

    def _on_calibre(self, msg: CalibreMsg):
        if msg.book_id not in self.books:
            return
        b = self.books[msg.book_id]
        if msg.stage == "converting":
            b.stage = "Converting with Calibre…"
        elif msg.stage == "done":
            b.calibre_path = msg.message
            b.calibre_done = True
            b.stage = "Calibre done"
        elif msg.stage == "error":
            b.calibre_failed = True
            b.error = msg.message
            b.stage = "Calibre failed"

    # ── View ───────────────────────────────────────────────────────────────

    def view(self) -> str:
        views = {
            Screen.MAIN:     self._view_main,
            Screen.LOGIN:    self._view_login,
            Screen.COOKIE:   self._view_cookie,
            Screen.ADD_BOOK: self._view_add_book,
            Screen.QUEUE:    self._view_queue,
            Screen.DOWNLOAD: self._view_download,
            Screen.CALIBRE:        self._view_calibre,
            Screen.SETTINGS:       self._view_settings,
            Screen.CALIBRE_SYNC:   self._view_calibre_sync,
            Screen.FAILED_SUMMARY: self._view_failed_summary,
            Screen.LIBRARY_BROWSE: self._view_library_browse,
            Screen.SEARCH:         self._view_search,
        }
        render = views.get(self.screen, self._view_main)
        return render() + "\n"

    def _header(self, subtitle: str = "") -> str:
        title = title_style.render("  KeroOle  ")
        if subtitle:
            sub = Style().foreground(C_MUTED).render(f"  {subtitle}")
            return join_horizontal(Top, title, sub)
        return title

    def _footer(self, hints: str) -> str:
        return hint_style.render(hints)

    def _library_book_count(self) -> int:
        """Count book directories in Books/ — fast directory scan, no file reads."""
        import re as _re
        books_dir = os.path.join(PATH, "Books")
        if not os.path.isdir(books_dir):
            return 0
        _dir_re = _re.compile(r'^.+\((\w+)\)$')
        return sum(
            1 for e in os.scandir(books_dir)
            if e.is_dir() and _dir_re.match(e.name)
        )

    # Main menu ───────────────────────────────────────────────────────────────

    def _view_main(self) -> str:
        art = ASCII_ART_VARIANTS[_ascii_art_variant % len(ASCII_ART_VARIANTS)]
        art_style = Style().foreground(C_ACCENT).bold(True)
        lines = [art_style.render(line) for line in art]
        lines.append("")

        # Cookie status badge — always read from disk so external saves are reflected
        cookie_exists = os.path.isfile(COOKIES_FILE)
        if cookie_exists:
            age_mins = self._cookie_age_mins()
            age_str  = self._cookie_age_str()
            if age_mins > 15:
                badge = Style().foreground(C_YELLOW).bold(True).render(
                    f"● Cookie: saved ({age_str}) ⚠ may be expired"
                )
            else:
                badge = success_style.render(f"● Cookie: saved ({age_str})")
        else:
            badge = error_style.render("○ Cookie: not set")
        lines.append("  " + badge)
        lines.append("")

        # Menu items — filter hidden items unless unlocked via cheat
        visible_items = self._visible_menu_items()
        lib_count = self._library_book_count()
        q = len(self.queue)
        for i, (label, _) in enumerate(visible_items):
            is_queue = label == "View / Run Queue"
            if is_queue:
                label = "View / Run Queue / Export"
            if i == self.menu_cursor:
                lines.append(cursor_style.render(f"  ▶ {label}"))
            else:
                lines.append(f"    {label}")
            if is_queue:
                lib_str = f"{lib_count} in library" if lib_count else "library empty"
                lines.append(hint_style.render(f"      {q} queued · {lib_str}"))

        lines.append("")
        lines.append(self._footer("↑/↓  move    Enter  select    q  quit"))

        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 60)).render(content)

    # Login screen ────────────────────────────────────────────────────────────

    def _view_login(self) -> str:
        lines = [self._header("Login with Email/Password"), ""]

        # Current cookie status
        if os.path.isfile(COOKIES_FILE):
            age_str = self._cookie_age_str()
            lines.append(success_style.render(f"● Already logged in ({age_str}) — log in again to refresh"))
        else:
            lines.append(hint_style.render("○ No session saved — enter credentials below"))
        lines.append("")

        box_w = min(self.width - 12, 48)

        def _field(label: str, value: str, focused: bool, masked: bool = False) -> str:
            display = ("*" * len(value)) if masked else value
            cursor  = "█" if focused else ""
            border_color = C_ACCENT if focused else C_MUTED
            box = (
                Style()
                .border(normal_border())
                .border_foreground(border_color)
                .padding(0, 1)
                .width(box_w)
                .render(display + cursor)
            )
            lbl = (accent_style if focused else label_style).render(label)
            return lbl + "\n" + box

        lines.append(_field("Email", self.login_email, self.login_field == 0))
        lines.append("")
        lines.append(_field("Password", self.login_password, self.login_field == 1, masked=True))
        lines.append("")

        if self.login_running:
            lines.append(Style().foreground(C_YELLOW).render("  ⟳  Logging in…"))
        elif self.login_status:
            kind, _, msg = self.login_status.partition(":")
            if kind == "ok":
                lines.append(success_style.render("✓ " + msg))
            else:
                lines.append(error_style.render("✗ " + msg))
        lines.append("")

        lines.append(self._footer("Tab/↓  next field    Enter  submit    Ctrl+U  clear    Esc  back"))
        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 60)).render(content)

    # Cookie screen ───────────────────────────────────────────────────────────

    def _view_cookie(self) -> str:
        lines = [self._header("Set Session Cookie"), ""]

        # Current file status — reflects CLI saves too
        cookie_exists = os.path.isfile(COOKIES_FILE)
        if cookie_exists:
            age_str = self._cookie_age_str()
            age_mins = self._cookie_age_mins()
            if age_mins > 15:
                lines.append(Style().foreground(C_YELLOW).bold(True).render(
                    f"● cookies.json saved ({age_str}) ⚠ may be expired — update below"
                ))
            else:
                lines.append(success_style.render(
                    f"● cookies.json saved ({age_str}) ✓ — ready, or update below"
                ))
        else:
            lines.append(error_style.render("○ cookies.json not found — set a cookie below"))
        lines.append("")

        # Option 1: browser auto-retrieve
        lines.append(accent_style.render("Option 1 — Auto-retrieve from browser  [press b]"))
        if self.cookie_retrieving:
            lines.append(Style().foreground(C_YELLOW).render("  ⟳  Retrieving cookies from browser…"))
        else:
            lines.append(label_style.render("  Reads Chrome/Firefox cookies directly from disk."))
            lines.append(hint_style.render("  May fail over SSH or if Chrome is still running — use Option 2 then."))
        lines.append("")

        # Option 2: paste from DevTools
        lines.append(accent_style.render("Option 2 — Paste from DevTools  [Ctrl+V or Enter to save]"))
        lines.append(label_style.render("  1. DevTools (F12) → Network → any learning.oreilly.com request"))
        lines.append(label_style.render("  2. Headers → Request Headers → right-click Cookie → Copy value"))
        lines.append(label_style.render("  3. Press Ctrl+V to read from clipboard, then Enter to save"))
        import sys as _sys
        if _sys.platform == "win32":
            _clip_cmd = "Get-Clipboard | python3 retrieve_cookies.py --stdin"
        elif _sys.platform == "darwin":
            _clip_cmd = "pbpaste | python3 retrieve_cookies.py --stdin"
        else:
            _clip_cmd = "xclip -o | python3 retrieve_cookies.py --stdin"
        lines.append(hint_style.render("  Tip: if Ctrl+V fails, use the CLI (most reliable for long cookies):"))
        lines.append(hint_style.render(f"       {_clip_cmd}"))
        lines.append("")

        # Input display — show last 60 chars + character count
        char_count = len(self.cookie_input)
        truncated = self.cookie_input[-60:] if char_count > 60 else self.cookie_input
        count_str = hint_style.render(f"  ({char_count} chars captured)")
        input_box = (
            Style()
            .border(normal_border())
            .border_foreground(C_ACCENT)
            .padding(0, 1)
            .width(min(self.width - 12, 64))
            .render(truncated + "█" if self.cookie_input else "█")
        )
        lines.append(input_box)
        if char_count > 0:
            lines.append(count_str)
        lines.append("")

        # Status
        if self.cookie_status:
            kind, _, msg = self.cookie_status.partition(":")
            if kind == "ok":
                lines.append(success_style.render("✓ " + msg))
            else:
                lines.append(error_style.render("✗ " + msg))
            lines.append("")

        lines.append(self._footer("Enter  save    Ctrl+V  paste    b  browser    Backspace  clear    Esc  back"))
        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 72)).render(content)

    # Add-book screen ─────────────────────────────────────────────────────────

    def _view_add_book(self) -> str:
        if self.multi_book_mode:
            return self._view_add_book_multi()

        lines = [self._header("Add Book to Queue"), ""]

        lines.append(label_style.render("Enter the numeric Book ID from the O'Reilly URL:"))
        lines.append(label_style.render("  learning.oreilly.com/library/view/title/XXXXXXXXXXX/"))
        lines.append("")

        cursor = "█"
        input_box = (
            Style()
            .border(normal_border())
            .border_foreground(C_ACCENT)
            .padding(0, 1)
            .width(32)
            .render(self.book_id_input + cursor)
        )
        lines.append(input_box)
        lines.append("")

        if self.add_book_status:
            kind, _, msg = self.add_book_status.partition(":")
            if kind == "ok":
                lines.append(success_style.render("✓ " + msg))
            else:
                lines.append(error_style.render("✗ " + msg))
            lines.append("")

        lines.append(self._footer("Enter  add    Ctrl+V  paste    m  multi-add    Esc  back"))
        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 60)).render(content)

    def _view_add_book_multi(self) -> str:
        lines = [self._header("Add Multiple Books"), ""]

        lines.append(label_style.render("Paste a list of book IDs — any separator works"))
        lines.append(hint_style.render("  (commas, spaces, newlines, pipes, full URLs, etc.)"))
        lines.append("")

        cursor = "█"
        # Show the last ~8 lines of input to keep the box manageable
        display_text = self.multi_book_input + cursor
        text_lines = display_text.splitlines() or [""]
        visible = "\n".join(text_lines[-8:])
        input_box = (
            Style()
            .border(normal_border())
            .border_foreground(C_ACCENT)
            .padding(0, 1)
            .width(56)
            .render(visible)
        )
        lines.append(input_box)
        lines.append("")

        if self.add_book_status:
            kind, _, msg = self.add_book_status.partition(":")
            if kind == "ok":
                lines.append(success_style.render("✓ " + msg))
            else:
                lines.append(error_style.render("✗ " + msg))
            lines.append("")

        lines.append(self._footer("Enter  add all    Ctrl+V  paste    m/Esc  back to single"))
        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 68)).render(content)

    # Queue screen ────────────────────────────────────────────────────────────

    def _view_queue(self) -> str:
        lines = [self._header("Queue / Export"), ""]

        if not self.queue:
            lines.append(hint_style.render("  Download queue is empty — press 'a' to add books, or 'e' to export existing downloads."))
        else:
            for i, book_id in enumerate(self.queue, 1):
                lines.append(f"  {i}. {book_id}")

        lines.append("")

        cookie_exists = os.path.isfile(COOKIES_FILE)
        if not cookie_exists:
            lines.append(error_style.render("  ⚠  Cookie not set — press 's' to set one before running."))
        else:
            age_mins = self._cookie_age_mins()
            age_str  = self._cookie_age_str()
            if age_mins > 15:
                lines.append(Style().foreground(C_YELLOW).bold(True).render(
                    f"  ⚠  Cookie saved {age_str} — may be expired.  Press 's' to refresh."
                ))
            else:
                lines.append(success_style.render(f"  ● Cookie ready  ({age_str})"))
        lines.append("")

        if self.status_msg:
            lines.append(error_style.render("  " + self.status_msg))
            lines.append("")

        # Export toggles
        def _toggle(label: str, value: bool) -> str:
            marker = success_style.render("✓") if value else hint_style.render("○")
            return f"  {marker} {label}"

        lines.append(_toggle("[m] GFM Markdown",       self.export_markdown))
        lines.append(_toggle("[o] Obsidian Markdown",  self.export_obsidian))
        lines.append(_toggle("[d] Chapter Content DB", self.export_db))
        lines.append(_toggle("[x] RAG JSONL",          self.export_rag))
        lines.append(_toggle("[k] Skip if downloaded", self.skip_if_downloaded))
        lines.append("")

        lines.append(self._footer(
            "a  add    r  run    e  export library    s  set cookie    c  clear    m/o/d/x/k  toggles    Esc  back"
        ))
        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 60)).render(content)

    # Download screen ─────────────────────────────────────────────────────────

    def _view_download(self) -> str:
        total = len(self.dl_order)
        # Each book renders as 3 lines (id, status, blank). Reserve 4 for
        # header + footer + scroll indicator.
        rows_available = max(3, self.height - 4)
        per_book = 3
        visible_count = min(12, max(1, rows_available // per_book))

        # Auto-scroll: keep the first in-progress book visible
        active_idx = None
        for i, bid in enumerate(self.dl_order):
            b = self.books.get(bid)
            if b and not b.done and not b.failed:
                active_idx = i
                break
        if active_idx is not None:
            # Clamp scroll so active book is in window
            if active_idx < self.dl_scroll:
                self.dl_scroll = active_idx
            elif active_idx >= self.dl_scroll + visible_count:
                self.dl_scroll = active_idx - visible_count + 1

        self.dl_scroll = max(0, min(self.dl_scroll, max(0, total - visible_count)))
        visible_ids = self.dl_order[self.dl_scroll: self.dl_scroll + visible_count]

        lines = [self._header(self.dl_label), ""]

        for book_id in visible_ids:
            b = self.books.get(book_id)
            if b is None:
                continue

            if b.title:
                id_line = f"{book_id}  {value_style.render(b.title[:38])}"
            else:
                id_line = book_id

            if b.skipped:
                status = Style().foreground(C_YELLOW).render("⊘ Skipped (cascade failure)")
                lines.append(f"  {id_line}")
                lines.append(f"  {status}")
            elif b.failed:
                status = error_style.render("✗ " + (b.error[:50] if b.error else "Failed"))
                lines.append(f"  {id_line}")
                lines.append(f"  {status}")
            elif b.done:
                status = success_style.render("✓ Complete")
                lines.append(f"  {id_line}")
                lines.append(f"  {status}")
            else:
                lines.append(f"  {id_line}")
                lines.append(f"  {render_bar(b.percent)}  {hint_style.render(b.stage[:38])}")
            lines.append("")

        # Scroll indicator when list is longer than the viewport
        if total > visible_count:
            end = min(self.dl_scroll + visible_count, total)
            scroll_hint = hint_style.render(
                f"  Showing {self.dl_scroll + 1}–{end} of {total}   ↑/↓ to scroll"
            )
            lines.append(scroll_hint)
            lines.append("")

        if self.all_calibre_done:
            lines.append(self._footer("↑/↓  scroll    Esc  back to menu    q  quit"))
        else:
            lines.append(self._footer("↑/↓  scroll    Ctrl+C  cancel"))
        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 72)).render(content)

    # Calibre screen ──────────────────────────────────────────────────────────

    def _view_calibre(self) -> str:
        lines = [self._header("Calibre Conversion"), ""]

        for book_id in self.dl_order:
            b = self.books.get(book_id)
            if b is None or b.failed:
                continue

            label = b.title[:40] if b.title else book_id

            if b.calibre_failed:
                status = error_style.render(f"✗ {b.error[:50]}")
            elif b.calibre_done:
                status = success_style.render(f"✓ {b.calibre_path}")
            else:
                status = Style().foreground(C_YELLOW).render("⟳ Converting…")

            lines.append(f"  {label}")
            lines.append(f"  {status}")
            lines.append("")

        if self.all_calibre_done:
            lines.append(success_style.render("  All done!"))
            lines.append("")
            lines.append(self._footer("Enter/Esc/q  back to menu    Ctrl+C  quit"))
        else:
            lines.append(self._footer("Ctrl+C  cancel"))

        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 72)).render(content)

    # Settings screen ─────────────────────────────────────────────────────────

    def _view_settings(self) -> str:
        lines = [self._header("Export Paths / Settings"), ""]

        box_w = min(self.width - 12, 56)

        # (label, placeholder when empty, sub-hint shown below field, field index)
        # Field indices: 0=legacy_md_dir, 1=rag_dir, 2=db_path,
        #                4=gfm_dir, 5=obsidian_dir  (3 is the toggle below)
        field_defs = [
            ("GFM Markdown output dir",
             "blank = Books/{title}/markdown/",
             "e.g. ~/Documents/Books/MD  — each book gets its own subfolder inside",
             4),
            ("Obsidian vault dir",
             "blank = Books/{title}/markdown/",
             "e.g. ~/Documents/ObsidianVault  — set to your Obsidian vault root",
             5),
            ("RAG JSONL output dir",
             "blank = next to each book in Books/",
             "e.g. ~/Documents/Books/RAG  — all JSONL files land flat inside",
             1),
            ("Library DB path",
             "blank = Books/library.db",
             "e.g. ~/Documents/Books/library.db  — full path to the SQLite file",
             2),
        ]

        lines.append(hint_style.render(
            "  Leave blank to keep the default path inside each book's folder."
        ))
        lines.append(hint_style.render(
            "  Paths support ~ (e.g. ~/Documents/Books).  Tab/↓ to move.  Enter to save."
        ))
        lines.append("")

        for label, placeholder, sub_hint, idx in field_defs:
            focused = self.settings_cursor == idx
            val = self.settings_fields[idx]
            cursor  = "█" if focused else ""
            border_color = C_ACCENT if focused else C_MUTED
            box = (
                Style()
                .border(normal_border())
                .border_foreground(border_color)
                .padding(0, 1)
                .width(box_w)
                .render((val + cursor) if val else (hint_style.render(placeholder) + cursor))
            )
            lbl = (accent_style if focused else label_style).render(label)
            lines.append(lbl)
            lines.append(box)
            lines.append(hint_style.render(f"  ↳ {sub_hint}"))
            lines.append("")

        # Toggle: folder name style
        focused = self.settings_cursor == 3
        style_val = self.settings_fields[3] or "title"
        title_sel = accent_style.render("[ Title ]") if style_val == "title" else hint_style.render("[ Title ]")
        id_sel    = accent_style.render("[ ID ]")    if style_val == "id"    else hint_style.render("[ ID ]")
        lbl = (accent_style if focused else label_style).render("Folder name style")
        toggle_row = f"  {title_sel}  {id_sel}"
        if focused:
            toggle_row += "  " + hint_style.render("← → or Space to switch")
        lines.append(lbl)
        lines.append(toggle_row)
        lines.append(hint_style.render("  ↳ How export subfolders are named — by book title or numeric book ID"))
        lines.append("")

        # Toggle: delete original EPUB after Calibre conversion
        focused = self.settings_cursor == 6
        del_on  = self.settings_delete_original
        on_lbl  = accent_style.render("[ On  ]") if del_on  else hint_style.render("[ On  ]")
        off_lbl = accent_style.render("[ Off ]") if not del_on else hint_style.render("[ Off ]")
        lbl = (accent_style if focused else label_style).render("Delete original EPUB after Calibre conversion")
        del_toggle = f"  {on_lbl}  {off_lbl}"
        if focused:
            del_toggle += "  " + hint_style.render("Space to toggle  (saves immediately)")
        lines.append(lbl)
        lines.append(del_toggle)
        lines.append(hint_style.render("  ↳ When On, the pre-conversion EPUB is removed after a successful Calibre convert"))
        lines.append("")

        # Action buttons
        scan_focused  = self.settings_cursor == 7
        clear_focused = self.settings_cursor == 8

        def _action_btn(label: str, focused: bool, scanning: bool = False) -> str:
            lbl = (accent_style if focused else label_style).render(label)
            hint = hint_style.render("  [Enter to run]") if focused else ""
            spinner = Style().foreground(C_YELLOW).render(" ⟳") if scanning else ""
            return lbl + spinner + hint

        lines.append(_action_btn("Scan Library",      scan_focused,  self.settings_scanning))
        lines.append(hint_style.render("  ↳ Populate the download registry from existing Books/ folders"))
        lines.append("")
        lines.append(_action_btn("Clear Chapter DB", clear_focused))
        lines.append(hint_style.render("  ↳ Remove stored chapter XHTML/TOC data (registry is preserved)"))
        lines.append("")

        if self.settings_action_status:
            kind, _, msg = self.settings_action_status.partition(":")
            if kind == "ok":
                lines.append(success_style.render("✓ " + msg))
            else:
                lines.append(error_style.render("✗ " + msg))
            lines.append("")

        if self.settings_status:
            kind, _, msg = self.settings_status.partition(":")
            if kind == "ok":
                lines.append(success_style.render("✓ " + msg))
            else:
                lines.append(error_style.render("✗ " + msg))
            lines.append("")

        # Cheat code sub-section
        lines.append(hint_style.render("  ─── Cheat Codes ───"))
        from config import load_unlocked_cheats, cheat_description
        unlocked = load_unlocked_cheats()
        if unlocked:
            for eff in sorted(unlocked):
                lines.append(hint_style.render(f"  ✓ {cheat_description(eff)}"))
        else:
            lines.append(hint_style.render("  (none unlocked)"))
        if self.cheat_input_focused:
            cursor = "█"
            masked = "*" * len(self.cheat_input) + cursor
            cheat_box = (
                Style()
                .border(normal_border())
                .border_foreground(C_ACCENT)
                .padding(0, 1)
                .width(30)
                .render(masked)
            )
            lines.append(accent_style.render("Enter code:") + " " + cheat_box)
            lines.append(hint_style.render("  Enter to submit  Esc to cancel  (input is masked)"))
        else:
            lines.append(hint_style.render("  Press [c] to enter a cheat code"))
        if self.cheat_status:
            kind, _, msg = self.cheat_status.partition(":")
            if kind == "ok":
                lines.append(success_style.render("✓ " + msg))
            else:
                lines.append(error_style.render("✗ " + msg))
        lines.append("")

        lines.append(self._footer("Tab/↓  next    Enter  save/run    Ctrl+U  clear    Space  toggle    Esc  back"))
        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 68)).render(content)

    # ── Calibre sync screen ────────────────────────────────────────────────

    def _start_calibre_sync(self):
        self.sync_scanning    = True
        self.sync_entries     = []
        self.sync_selected    = set()
        self.sync_cursor      = 0
        self.sync_scroll      = 0
        self.sync_adding      = False
        self.sync_add_status  = {}
        self.sync_all_done    = False
        self.sync_error       = ""
        self.screen           = Screen.CALIBRE_SYNC
        worker = CalibreSyncWorker(
            books_dir=os.path.join(PATH, "Books"),
            program=self._program,
        )
        worker.start()

    def _key_failed_summary(self, key: str):
        if key in ("escape", "q", "enter"):
            self.screen = Screen.MAIN
        return self, None

    # ── Library Browse screen (Phase 1C) ────────────────────────────────────

    def _key_library_browse(self, key: str):
        if self.lib_filter_mode:
            if key == "escape":
                self.lib_filter_mode = False
                self.lib_filter = ""
            elif key in ("backspace", "delete"):
                self.lib_filter = self.lib_filter[:-1]
            elif key == "ctrl+u":
                self.lib_filter = ""
            elif len(key) == 1 and key.isprintable():
                self.lib_filter += key
            return self, None

        visible = self._lib_filtered_books()
        total = len(visible)

        if key in ("escape", "q"):
            self.screen = Screen.MAIN
        elif key == "/":
            self.lib_filter_mode = True
        elif key in ("up", "k"):
            self.lib_cursor = max(0, self.lib_cursor - 1)
            if self.lib_cursor < self.lib_scroll:
                self.lib_scroll = self.lib_cursor
        elif key in ("down", "j"):
            self.lib_cursor = min(max(0, total - 1), self.lib_cursor + 1)
            rows = max(3, self.height - 10)
            if self.lib_cursor >= self.lib_scroll + rows:
                self.lib_scroll = self.lib_cursor - rows + 1
        elif key == " ":
            if 0 <= self.lib_cursor < total:
                bid = visible[self.lib_cursor]["book_id"]
                if bid in self.lib_selected:
                    self.lib_selected.discard(bid)
                else:
                    self.lib_selected.add(bid)
        elif key == "a":
            all_ids = {b["book_id"] for b in visible}
            if self.lib_selected >= all_ids:
                self.lib_selected = set()
            else:
                self.lib_selected = all_ids.copy()
        elif key == "e":
            # Export selected books
            if not self.lib_selected:
                self.lib_status = "error:No books selected — use Space to select, or A for all."
            else:
                self._start_export_library(selected_ids=self.lib_selected)
        elif key == "A":
            # Export ALL books (ignores selection)
            self._start_export_library()
        elif key == "r":
            # Refresh book list from DB
            self._load_library_books()
            self.lib_status = "ok:Library refreshed."
        return self, None

    def _lib_filtered_books(self) -> list:
        """Return lib_books filtered by current lib_filter (title substring)."""
        if not self.lib_filter:
            return self.lib_books
        q = self.lib_filter.lower()
        return [b for b in self.lib_books if q in (b.get("title") or "").lower()]

    def _view_library_browse(self) -> str:
        books = self._lib_filtered_books()
        total = len(books)

        lines = [self._header("Browse Library"), ""]

        # Status / filter bar
        if self.lib_filter_mode:
            lines.append(accent_style.render(f"  Filter: {self.lib_filter}█"))
        elif self.lib_filter:
            lines.append(hint_style.render(f"  Filter: {self.lib_filter}  (/ to edit, Esc to clear)"))
        else:
            lines.append(hint_style.render(f"  {len(self.lib_books)} books in library  •  / to filter"))

        if self.lib_status:
            if self.lib_status.startswith("error:"):
                lines.append(error_style.render("  " + self.lib_status[6:]))
            else:
                lines.append(success_style.render("  " + self.lib_status.lstrip("ok:")))
        lines.append("")

        if not books:
            lines.append(hint_style.render("  No books found." if self.lib_filter else
                                            "  Library is empty — download a book first."))
            lines.append("")
            lines.append(self._footer("r  refresh    /  filter    Esc  back"))
            return panel_style.width(min(self.width - 4, 80)).render("\n".join(lines))

        rows = max(3, self.height - 10)
        self.lib_scroll = max(0, min(self.lib_scroll, max(0, total - rows)))
        visible = books[self.lib_scroll: self.lib_scroll + rows]

        for i, book in enumerate(visible):
            abs_idx = self.lib_scroll + i
            focused = abs_idx == self.lib_cursor
            bid     = book["book_id"]
            checked = bid in self.lib_selected

            # Status badges
            xhtml_ok = (book.get("stored_chapters") or 0) > 0
            md_ok    = (book.get("md_chapters") or 0) > 0
            badge_xhtml = success_style.render("[DB]") if xhtml_ok else hint_style.render("[DB]")
            badge_md    = success_style.render("[MD]") if md_ok    else hint_style.render("[MD]")
            badges = f"{badge_xhtml}{badge_md}"

            title   = (book.get("title") or bid)[:40]
            box     = accent_style.render("[✓]") if checked else "[ ]"
            prefix  = "▶ " if focused else "  "
            row     = f"{prefix}{box}  {title}  {badges}"
            if focused:
                lines.append(cursor_style.render(row))
            else:
                lines.append(row)

        if total > rows:
            end = min(self.lib_scroll + rows, total)
            lines.append("")
            lines.append(hint_style.render(
                f"  Showing {self.lib_scroll + 1}–{end} of {total}  ↑/↓ scroll"
            ))

        lines.append("")
        sel_count = len(self.lib_selected)
        lines.append(self._footer(
            f"↑/↓ move  Space toggle  a all  e export selected ({sel_count})  A export all  / filter  r refresh  Esc back"
        ))
        return panel_style.width(min(self.width - 4, 80)).render("\n".join(lines))

    # ── Search screen (Phase 1A) ─────────────────────────────────────────────

    def _key_search(self, key: str):
        if self.search_phase == "form":
            return self._key_search_form(key)
        else:
            return self._key_search_results(key)

    def _key_search_form(self, key: str):
        _EDITABLE = {0, 1, 2}

        if key == "escape":
            self.screen = Screen.MAIN
        elif key in ("tab", "down"):
            self.search_field = (self.search_field + 1) % 5
        elif key in ("shift+tab", "up"):
            self.search_field = (self.search_field - 1) % 5
        elif self.search_field == 3:
            # format toggle
            if key in (" ", "enter", "left", "right"):
                options = ("book", "video", "")
                idx = options.index(self.search_format) if self.search_format in options else 0
                self.search_format = options[(idx + 1) % len(options)]
        elif self.search_field == 4:
            # sort toggle
            if key in (" ", "enter", "left", "right"):
                self.search_sort = "created_time" if self.search_sort == "relevance" else "relevance"
        elif key == "enter" and self.search_field in _EDITABLE:
            if self.search_query.strip():
                self._run_search(page=1)
        elif self.search_field in _EDITABLE and key in ("backspace", "delete"):
            if self.search_field == 0:
                self.search_query = self.search_query[:-1]
            elif self.search_field == 1:
                self.search_topic = self.search_topic[:-1]
            elif self.search_field == 2:
                self.search_publisher = self.search_publisher[:-1]
        elif self.search_field in _EDITABLE and key == "ctrl+u":
            if self.search_field == 0:
                self.search_query = ""
            elif self.search_field == 1:
                self.search_topic = ""
            elif self.search_field == 2:
                self.search_publisher = ""
        elif self.search_field in _EDITABLE and len(key) == 1 and key.isprintable():
            if self.search_field == 0:
                self.search_query += key
            elif self.search_field == 1:
                self.search_topic += key
            elif self.search_field == 2:
                self.search_publisher += key
        return self, None

    def _key_search_results(self, key: str):
        total = len(self.search_results)
        rows  = max(3, self.height - 12)

        if key in ("escape", "q"):
            self.search_phase = "form"
            self.search_status = ""
        elif key in ("up", "k"):
            self.search_cursor = max(0, self.search_cursor - 1)
            if self.search_cursor < self.search_scroll:
                self.search_scroll = self.search_cursor
        elif key in ("down", "j"):
            self.search_cursor = min(max(0, total - 1), self.search_cursor + 1)
            if self.search_cursor >= self.search_scroll + rows:
                self.search_scroll = self.search_cursor - rows + 1
        elif key == " ":
            if 0 <= self.search_cursor < total:
                bid = self.search_results[self.search_cursor].book_id
                if bid in self.search_selected:
                    self.search_selected.discard(bid)
                else:
                    self.search_selected.add(bid)
        elif key in ("]",):
            if not self.search_running:
                max_page = max(1, (self.search_total + 9) // 10)
                if self.search_page < max_page:
                    self._run_search(page=self.search_page + 1)
        elif key in ("[",):
            if not self.search_running and self.search_page > 1:
                self._run_search(page=self.search_page - 1)
        elif key in ("enter", "r", "R"):
            # Add selected results to queue and go to QUEUE screen
            added = 0
            for bid in self.search_selected:
                if bid and bid not in self.queue:
                    self.queue.append(bid)
                    self.books[bid] = BookState(book_id=bid)
                    self.dl_order.append(bid)
                    added += 1
            if added:
                self.search_selected = set()
                self.status_msg = f"Added {added} book(s) to queue."
                self.screen = Screen.QUEUE
        return self, None

    def _run_search(self, page: int):
        if self.search_running:
            return
        self.search_running = True
        self.search_status = "Searching…"
        worker = SearchWorker(
            query=self.search_query.strip(),
            format_filter=self.search_format,
            topic=self.search_topic.strip(),
            publisher=self.search_publisher.strip(),
            sort=self.search_sort,
            page=page,
            program=self._program,
        )
        worker.start()

    def _view_search(self) -> str:
        if self.search_phase == "results":
            return self._view_search_results()
        return self._view_search_form()

    def _view_search_form(self) -> str:
        lines = [self._header("Search O'Reilly"), ""]
        box_w = min(self.width - 14, 50)

        def _field(label: str, value: str, idx: int, placeholder: str = "") -> list:
            focused = self.search_field == idx
            cursor  = "█" if focused else ""
            border  = C_ACCENT if focused else C_MUTED
            display = (value + cursor) if value else (hint_style.render(placeholder) + cursor)
            box = (
                Style().border(normal_border()).border_foreground(border)
                .padding(0, 1).width(box_w)
                .render(display)
            )
            lbl = (accent_style if focused else label_style).render(label)
            return [lbl, box]

        lines += _field("Search query", self.search_query, 0, "e.g. kubernetes, machine learning…")
        lines.append("")
        lines += _field("Topic filter", self.search_topic, 1, "e.g. python, cloud, security  (optional)")
        lines.append("")
        lines += _field("Publisher filter", self.search_publisher, 2, "e.g. oreilly, packt  (optional)")
        lines.append("")

        # Format toggle
        fmt_focused = self.search_field == 3
        fmt_labels = {"book": "Books", "video": "Videos", "": "All"}
        fmt_row = "  " + "  ".join(
            accent_style.render(f"[{v}]") if self.search_format == k else hint_style.render(f"[{v}]")
            for k, v in fmt_labels.items()
        )
        lbl = (accent_style if fmt_focused else label_style).render("Format")
        lines.append(lbl)
        lines.append(fmt_row)
        lines.append("")

        # Sort toggle
        sort_focused = self.search_field == 4
        relevance_s  = accent_style.render("[Relevance]") if self.search_sort == "relevance" else hint_style.render("[Relevance]")
        newest_s     = accent_style.render("[Newest]")    if self.search_sort == "created_time" else hint_style.render("[Newest]")
        lbl = (accent_style if sort_focused else label_style).render("Sort")
        lines.append(lbl)
        lines.append(f"  {relevance_s}  {newest_s}")
        lines.append("")

        if self.search_status:
            if self.search_status.startswith("error:"):
                lines.append(error_style.render("  " + self.search_status[6:]))
            else:
                lines.append(hint_style.render("  " + self.search_status))
            lines.append("")

        lines.append(self._footer("Tab/↓ move  Enter search  ←→ toggle options  Esc back"))
        return panel_style.width(min(self.width - 4, 72)).render("\n".join(lines))

    def _view_search_results(self) -> str:
        results = self.search_results
        total   = self.search_total
        page    = self.search_page
        max_page = max(1, (total + 9) // 10)

        lines = [self._header("Search O'Reilly — Results"), ""]

        # Summary bar
        sel_count = len(self.search_selected)
        summary = f"  {total} results  •  page {page}/{max_page}  •  {sel_count} selected"
        if self.search_running:
            summary += "  " + hint_style.render("⟳ loading…")
        lines.append(accent_style.render(summary))
        lines.append("")

        if not results and not self.search_running:
            lines.append(hint_style.render("  No results."))
            lines.append("")
            lines.append(self._footer("Esc  back to form"))
            return panel_style.width(min(self.width - 4, 80)).render("\n".join(lines))

        rows = max(3, self.height - 12)
        self.search_scroll = max(0, min(self.search_scroll, max(0, len(results) - rows)))
        visible = results[self.search_scroll: self.search_scroll + rows]

        for i, result in enumerate(visible):
            abs_idx = self.search_scroll + i
            focused  = abs_idx == self.search_cursor
            checked  = result.book_id in self.search_selected

            fmt_icon = hint_style.render("[V]") if result.format == "video" else ""
            box      = accent_style.render("[✓]") if checked else "[ ]"
            prefix   = "▶ " if focused else "  "
            title    = result.title[:38]
            year     = result.issued[:4] if result.issued else ""
            pages    = f"{result.page_count}p" if result.page_count else ""
            meta     = "  " + hint_style.render(
                " · ".join(filter(None, [result.authors_str[:24], result.publishers_str[:16],
                                          year, pages]))
            )
            row = f"{prefix}{box} {fmt_icon} {title}"
            if focused:
                lines.append(cursor_style.render(row))
                lines.append(meta)
            else:
                lines.append(row)
                lines.append(meta)

        if len(results) < total:
            lines.append("")
            lines.append(hint_style.render(f"  [ to prev page  ] to next page"))

        lines.append("")
        lines.append(self._footer(
            "↑/↓ move  Space select  Enter/r add to queue  [ prev  ] next  Esc back"
        ))
        return panel_style.width(min(self.width - 4, 80)).render("\n".join(lines))

    def _key_calibre_sync(self, key: str):
        # Scanning — only Esc
        if self.sync_scanning:
            if key == "escape":
                self.screen = Screen.MAIN
            return self, None

        # Done — Esc/q to go back
        if self.sync_all_done:
            if key in ("escape", "q"):
                self.screen = Screen.MAIN
            return self, None

        # Adding in progress — no keys
        if self.sync_adding:
            return self, None

        # Error state
        if self.sync_error:
            if key == "escape":
                self.screen = Screen.MAIN
            return self, None

        # Review phase
        entries = self.sync_entries
        total   = len(entries)

        if key == "escape":
            self.screen = Screen.MAIN
            return self, None

        if key in ("up", "k"):
            self.sync_cursor = max(0, self.sync_cursor - 1)
            rows_available = max(3, self.height - 8)
            visible_count  = max(1, rows_available // 2)
            if self.sync_cursor < self.sync_scroll:
                self.sync_scroll = self.sync_cursor
        elif key in ("down", "j"):
            self.sync_cursor = min(max(0, total - 1), self.sync_cursor + 1)
            rows_available = max(3, self.height - 8)
            visible_count  = max(1, rows_available // 2)
            if self.sync_cursor >= self.sync_scroll + visible_count:
                self.sync_scroll = self.sync_cursor - visible_count + 1
        elif key == " ":
            if 0 <= self.sync_cursor < total:
                entry = entries[self.sync_cursor]
                if entry.match == "none":
                    if entry.book_id in self.sync_selected:
                        self.sync_selected.discard(entry.book_id)
                    else:
                        self.sync_selected.add(entry.book_id)
        elif key == "a":
            none_ids = {e.book_id for e in entries if e.match == "none"}
            if self.sync_selected >= none_ids:
                self.sync_selected = set()
            else:
                self.sync_selected = none_ids.copy()
        elif key == "r":
            to_add = [e for e in entries if e.book_id in self.sync_selected]
            if to_add:
                self._start_calibre_add(to_add)

        return self, None

    # Failed Summary screen ───────────────────────────────────────────────────

    def _view_failed_summary(self) -> str:
        lines = [self._header("Download Failures"), ""]

        failed  = [b for b in self.failed_books if not b.get("was_skipped")]
        skipped = [b for b in self.failed_books if b.get("was_skipped")]

        if failed:
            lines.append(error_style.render(f"  {len(failed)} book(s) failed to download:"))
            for b in failed:
                t = f'  "{b["title"]}"' if b["title"] else ""
                lines.append(f"    • {b['book_id']}{t}")
            lines.append("")

        if skipped:
            lines.append(Style().foreground(C_YELLOW).render(
                f"  {len(skipped)} book(s) skipped (consecutive failure cascade):"
            ))
            for b in skipped:
                t = f'  "{b["title"]}"' if b["title"] else ""
                lines.append(f"    • {b['book_id']}{t}")
            lines.append("")

        if self.failure_log_path:
            lines.append(hint_style.render("  Failure report saved to:"))
            lines.append(value_style.render(f"    {self.failure_log_path}"))
            lines.append("")
        if self.failure_debug_log_path:
            lines.append(hint_style.render("  Debug log (for troubleshooting):"))
            lines.append(value_style.render(f"    {self.failure_debug_log_path}"))
            lines.append("")

        lines.append(hint_style.render(
            "  Add failed book IDs to the queue to retry downloading them."
        ))
        lines.append("")
        lines.append(self._footer("Esc / Enter / q  back to menu"))
        content = "\n".join(lines)
        return panel_style.width(min(self.width - 4, 76)).render(content)

    def _view_calibre_sync(self) -> str:
        lines = [self._header("Sync with Calibre Library"), ""]

        # ── Scanning phase ─────────────────────────────────────────────────────
        if self.sync_scanning:
            lines.append("")
            lines.append(hint_style.render("  Scanning library and calibredb…"))
            lines.append("")
            lines.append(self._footer("Esc  cancel"))
            return panel_style.width(min(self.width - 4, 72)).render("\n".join(lines))

        # ── Error state ────────────────────────────────────────────────────────
        if self.sync_error:
            lines.append(error_style.render(f"  ✗ {self.sync_error}"))
            lines.append("")
            lines.append(self._footer("Esc  back"))
            return panel_style.width(min(self.width - 4, 72)).render("\n".join(lines))

        # ── Adding / done phase ────────────────────────────────────────────────
        if self.sync_adding or self.sync_all_done:
            return self._view_calibre_sync_adding()

        # ── Review phase ───────────────────────────────────────────────────────
        entries   = self.sync_entries
        unsynced  = [e for e in entries if e.match == "none"]
        ambiguous = [e for e in entries if e.match == "ambiguous"]
        selected  = len([e for e in unsynced if e.book_id in self.sync_selected])

        summary = (
            f"  {len(unsynced)} not in library  "
            f"({self.sync_already_synced} synced"
            + (f" · {len(ambiguous)} ambiguous" if ambiguous else "")
            + (f" · {self.sync_skipped} skipped" if self.sync_skipped else "")
            + ")"
        )
        lines.append(accent_style.render(summary))
        lines.append(hint_style.render(f"  {selected} selected for import"))
        lines.append("")

        if not entries:
            lines.append(success_style.render("  ✓ All local books are already in your Calibre library!"))
            lines.append("")
            lines.append(self._footer("Esc  back"))
            return panel_style.width(min(self.width - 4, 72)).render("\n".join(lines))

        rows_available = max(3, self.height - 8)
        visible_count  = max(1, rows_available // 2)
        total          = len(entries)
        self.sync_scroll = max(0, min(self.sync_scroll, max(0, total - visible_count)))
        visible = entries[self.sync_scroll: self.sync_scroll + visible_count]

        for i, entry in enumerate(visible):
            abs_idx  = self.sync_scroll + i
            focused  = abs_idx == self.sync_cursor
            checked  = entry.book_id in self.sync_selected
            is_ambig = entry.match == "ambiguous"

            if is_ambig:
                box  = hint_style.render("[~]")
                body = hint_style.render(f"  {entry.title[:42]}  ~ possible match")
            else:
                box  = accent_style.render("[✓]") if checked else "[ ]"
                body = f"  {entry.title[:42]}"
                if entry.author:
                    body += hint_style.render(f" — {entry.author[:28]}")

            prefix = "▶ " if focused else "  "
            row = f"{prefix}{box}{body}"
            if focused:
                lines.append(cursor_style.render(row))
            else:
                lines.append(row)
            lines.append("")

        if total > visible_count:
            end = min(self.sync_scroll + visible_count, total)
            lines.append(hint_style.render(
                f"  Showing {self.sync_scroll + 1}–{end} of {total}   ↑/↓ to scroll"
            ))
            lines.append("")

        lines.append(self._footer("↑/↓  move    Space  toggle    a  all    r  add selected    Esc  back"))
        return panel_style.width(min(self.width - 4, 72)).render("\n".join(lines))

    def _view_calibre_sync_adding(self) -> str:
        lines = [self._header("Adding to Calibre Library"), ""]

        for book_id, status in self.sync_add_status.items():
            entry = next((e for e in self.sync_entries if e.book_id == book_id), None)
            label = entry.title[:40] if entry else book_id
            if status == "adding":
                st = Style().foreground(C_YELLOW).render("⟳ Adding…")
            elif status == "done":
                st = success_style.render("✓ Added")
            elif status.startswith("error:"):
                st = error_style.render("✗ " + status[6:50])
            else:
                st = hint_style.render(status)
            lines.append(f"  {label}")
            lines.append(f"  {st}")
            lines.append("")

        if self.sync_all_done:
            lines.append(success_style.render("  All done!"))
            lines.append("")
            lines.append(self._footer("Esc  back to menu    q  quit"))
        else:
            lines.append(self._footer("Running…"))

        return panel_style.width(min(self.width - 4, 72)).render("\n".join(lines))

    def _start_calibre_add(self, entries: list):
        self.sync_adding     = True
        self.sync_all_done   = False
        self.sync_add_status = {e.book_id: "queued" for e in entries}
        worker = CalibreAddWorker(entries=entries, program=self._program)
        worker.start()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    try:
        import colorama
        colorama.just_fix_windows_console()
    except AttributeError:
        try:
            colorama.init(strip=False)
        except Exception:
            pass
    except ImportError:
        pass

    model = AppModel()
    program = tea.Program(model, alt_screen=True)
    model._program = program  # back-reference so workers can send messages
    try:
        final = program.run()
    except (tea.ErrInterrupted, KeyboardInterrupt):
        pass


if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
