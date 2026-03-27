# Design: TUI UX and Metadata Fixes

**Date:** 2026-03-27
**Scope:** Five targeted improvements to KeroOle's TUI and EPUB metadata pipeline.

---

## 1. Post-Queue Return to Main Menu

### Problem
After a queue finishes processing (download + Calibre conversion), the Calibre screen (`Screen.CALIBRE`) only offers quit via `tea.quit_cmd`. The user cannot return to the main menu without restarting the app.

### Solution
Modify `_key_calibre` in `AppModel` to navigate to `Screen.MAIN` on `"escape"`, `"q"`, or `"enter"` (all three currently trigger quit; all three will now return to menu instead). Quit remains available via `ctrl+c`, which is caught globally before any per-screen handler fires. Update `_view_calibre` footer from `"Enter/q  quit"` to `"Enter/Esc/q  back to menu"`.

The download screen (`Screen.DOWNLOAD`) already correctly returns to `Screen.MAIN` — only the Calibre screen needs the fix.

Re-run safety: `_start_downloads()` already resets all relevant state (`dl_order`, `books`, `all_calibre_done`, `calibre_running`, `dl_scroll`) before starting a new run, so returning to main menu and starting another queue is safe.

### Files changed
- `safaribooks/tui.py`: `_key_calibre`, `_view_calibre`

---

## 2. Cap Download Screen Visible Item Count

### Problem
`_view_download` computes `visible_count = max(1, rows_available // per_book)` where `per_book = 3`. On a typical modern terminal (50+ rows), this renders 16+ book rows, which overflow past the top of the terminal panel before scrolling engages.

### Solution
Cap `visible_count` at 12: `visible_count = min(12, max(1, rows_available // per_book))`. Derivation: 12 books × 3 lines/book = 36 content lines + 4 header/footer lines = 40 total — fits a standard 40-row terminal. Existing auto-scroll behaviour (keeping the active book visible) is unchanged.

### Files changed
- `safaribooks/tui.py`: `_view_download`

---

## 3. Rename "Content DB" Label; Add Library Management to Settings

### Problem
- The queue screen label `[d] Content DB` is ambiguous — users conflate it with the download registry.
- There is no TUI path to run `scan_existing_books()` or clear chapter data.

### Clarification of two distinct DB concepts

| Concept | Table | Auto/Manual | Purpose |
|---------|-------|-------------|---------|
| **Registry** | `registry` | **Always automatic** | Records every downloaded book; powers skip-if-downloaded |
| **Chapter Content DB** | `chapters` + `toc` | **Optional toggle** | Stores full XHTML and TOC for RAG/search use cases |

### Solution

**Queue screen** — rename label only:
- `[d] Content DB` → `[d] Chapter Content DB`

**Settings screen** — add two new action items after the existing four editable fields:

| Position | Type | Label | Trigger |
|----------|------|-------|---------|
| 0–2 | Editable text | Markdown dir / RAG dir / DB path | `backspace`, printable chars |
| 3 | Toggle | Folder name style | `space`, `left`, `right` |
| 4 | Action button | Scan Library | `enter` when focused |
| 5 | Action button | Clear Chapter DB | `enter` when focused |

**Implementation note for settings navigation**: `settings_fields` is currently a `List[str]` holding values for the four editable items. The action items at indices 4 and 5 are **not** added to `settings_fields` — they are rendered separately (after the editable fields loop) and navigated via `settings_cursor` extended to range 0–5. The `_key_settings` handler dispatches by cursor position: indices 0–2 do text editing, index 3 does toggle, indices 4–5 trigger actions. No change to the `settings_fields` list structure.

**Scan Library**: Runs `BookRegistry.scan_existing_books(books_dir)` in a background thread (disk I/O + SHA256 on each EPUB — can be slow for large libraries). Reports count inline: `"✓ N books added to registry"`.

**Clear Chapter DB**: Runs `clear_chapter_db()` inline (simple `DELETE` — fast). Reports inline: `"✓ Chapter data cleared"`. The `registry` table is **not** touched; only `chapters` and `toc` are truncated. SQLite foreign key enforcement is off by default in this codebase, so the truncation is safe.

Both actions add new state fields to `AppModel.__init__`: `settings_action_status: str`, `settings_scanning: bool`.

**Error handling**: If the scan thread raises an exception, `settings_action_status` is set to `"error:<message>"` (same `"ok:"` / `"error:"` prefix convention used throughout the TUI). The thread always updates `settings_scanning = False` in a `finally` block.

**Mid-scan navigation**: Navigation away from the Settings screen while scanning is allowed (no lock). The background thread writes `settings_scanning` and `settings_action_status` directly on `AppModel` — this is safe because all state writes happen via `program.send()` (a `LibraryScanDoneMsg` message), which queues the update through the normal event loop rather than writing state directly. The existing TUI pattern (e.g. `AllDownloadsDoneMsg`) follows the same approach. When the scan completes, the message is processed; if the user is on a different screen the status fields simply update silently in the background and are visible when they return to Settings.

### Files changed
- `safaribooks/tui.py`: `_view_queue` (label rename), `_view_settings`, `_key_settings`, `AppModel.__init__` (new state fields), background thread for Scan Library
- `safaribooks/library.py`: expose `clear_chapter_db()` helper method

---

## 4. Library Count Accuracy and Rescan

### Problem
The main menu "library" count (`_library_book_count`) does a directory scan of `PATH/Books/` and should already reflect all copied book folders. The registry (`library.db`) may have fewer entries if books were copied rather than downloaded through the app.

### Solution
The directory-scan count will correctly show all 300 folders once they are in `PATH/Books/` with the correct naming pattern `{Title} ({book_id})`. The "Scan Library" action added in §3 above will populate the registry for skip-if-downloaded to work correctly on those books.

No additional changes are needed beyond §3.

**Note on `_BOOK_DIR_RE` pattern**: The regex `r'^.+\((\w+)\)$'` uses `\w+` which matches only alphanumeric characters and underscores. O'Reilly/ORM book IDs are ISBNs (all digits) or all-alphanumeric identifiers — this regex handles all current IDs correctly. Book directories manually copied with non-standard naming will be silently skipped by the directory scan, which is pre-existing behaviour.

---

## 5. EPUB Metadata: Author and Publisher from Downloaded XHTML

### Root Cause
The v2 O'Reilly API endpoint (`/api/v2/epubs/urn:orm:book:{id}/`) does not return `authors` or `publishers` fields — they are absent entirely from the API response. `_normalize_v2_book_info` correctly receives an empty response and returns empty lists; there is no other v2 endpoint that supplies this data.

The author and publisher names ARE present in the downloaded XHTML files (title page and copyright page), so they can be extracted post-download.

### Solution

Add `_extract_metadata_from_xhtml(self) -> tuple[list, list]` to `KeroOle`.

**Parsing library**: Use `lxml` (`from lxml import html as lhtml`) — already a project dependency. `xml.etree.ElementTree` cannot handle HTML class lookups as required.

**Extraction logic** (scans the first 10 files in spine order):

| Field | Pattern 1 (O'Reilly) | Pattern 2 (third-party e.g. Wiley) |
|-------|----------------------|--------------------------------------|
| Author | Element with `class` containing `"author"`, text stripped of leading `"by "` and collapsed whitespace | Element with `class` containing `"authorName"` or `"bookAuthor"` |
| Publisher | Element with `class` containing `"publishername"` | Regex `Published by ([^,\n]{3,80})` in any element with `class` containing `"copyright"` or `epub:type="copyright-page"` |

**Filename normalisation at injection point**: At the time of the call, `self.book_chapters[i]["filename"]` values may have `.html` extensions (the `.xhtml` renaming is performed inside `save_page_html()` which already ran). The XHTML files on disk are named with `.xhtml`. The extraction method must substitute `.html` → `.xhtml` when constructing `OEBPS/` paths, and skip files that are not found.

**Injection point** — between `collect_images()` and `create_epub()`:
```python
if self.api_v2 and not self.book_info.get("authors"):
    authors, publishers = self._extract_metadata_from_xhtml()
    if authors:
        self.book_info["authors"] = authors
    if publishers:
        self.book_info["publishers"] = publishers
```

This is v2-only and only runs when the API returned empty authors — v1 metadata is unchanged.

**content.opf and toc.ncx** already read from `self.book_info["authors"]` and `self.book_info["publishers"]` — no changes needed to `create_content_opf()` or `create_toc()`.

**Registry** — `record_download()` is called in `_post_download_exports()` after `create_epub()`, so the registry will automatically receive the corrected metadata.

### Files changed
- `safaribooks/kerole.py`: `_extract_metadata_from_xhtml` (new method), injection call between `collect_images()` and `create_epub()`

### Test updates
- `safaribooks/tests/test_xhtml_extraction.py` (new file — separate from `test_v2_normalizers.py` to keep concerns distinct): `test_extract_authors_oreilly_pattern`, `test_extract_publisher_oreilly_pattern`, `test_extract_authors_wiley_pattern`, `test_extract_publisher_wiley_copyright_text`, `test_extract_returns_empty_when_no_match`

---

## Non-Goals

- No changes to the download path location or Books/ directory configurability.
- No external API calls (e.g. Open Library, Google Books) for metadata.
- No backfill of existing epub files on disk — only new downloads are fixed. Users who want corrected metadata on existing books can re-download.
- The `[d] Chapter Content DB` toggle in the queue screen remains optional; no change to its behaviour.

---

## Summary of File Changes

| File | Changes |
|------|---------|
| `safaribooks/tui.py` | `_key_calibre` (return to menu), `_view_calibre` (footer), `_view_download` (cap 12), `_view_queue` (label), `_view_settings` (scan/clear actions), `_key_settings` (scan/clear keys), `AppModel.__init__` (new state) |
| `safaribooks/kerole.py` | `_extract_metadata_from_xhtml` (new), injection call |
| `safaribooks/library.py` | `clear_chapter_db()` (new helper) |
| `safaribooks/tests/test_xhtml_extraction.py` | New file: XHTML metadata extraction tests |
