# TUI UX and Metadata Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix five independent issues: return-to-menu after queue, download screen overflow, Content DB label clarity, settings-screen library management actions, and missing author/publisher metadata in v2 EPUB downloads.

**Architecture:** Pure-edit approach — no new screens, no new files except one test file. Changes are ordered from lowest-risk (label/key tweaks) to highest-risk (new metadata extraction logic). Each task is independently committable.

**Tech Stack:** Python 3.12, bubblepy/pygloss TUI framework, lxml, SQLite via `sqlite3`, pytest

**Spec:** `docs/superpowers/specs/2026-03-27-tui-ux-and-metadata-fixes-design.md`

---

## File Map

| File | What changes |
|------|-------------|
| `safaribooks/tui.py` | Tasks 1–4: key handler, footer, visible-count cap, queue label, settings state + actions |
| `safaribooks/library.py` | Task 3: `clear_chapter_db()` helper |
| `safaribooks/kerole.py` | Task 5: `_extract_metadata_from_xhtml()` + injection call |
| `safaribooks/tests/test_xhtml_extraction.py` | Task 5: new test file |

---

## Task 1: Fix Calibre Screen — Return to Main Menu Instead of Quitting

**Files:**
- Modify: `safaribooks/tui.py` — `_key_calibre` (line ~870), `_view_calibre` (line ~1547)

**Context:** `_key_calibre` currently returns `tea.quit_cmd` on `q`, `enter`, `escape` when `all_calibre_done`. Change to navigate to `Screen.MAIN` instead. `ctrl+c` still quits (handled globally at line 719 before any screen handler fires).

- [ ] **Step 1: Edit `_key_calibre`**

  Find this block (lines ~870–873):
  ```python
  def _key_calibre(self, key: str):
      if self.all_calibre_done and key in ("q", "enter", "escape"):
          return self, tea.quit_cmd
      return self, None
  ```
  Replace with:
  ```python
  def _key_calibre(self, key: str):
      if self.all_calibre_done and key in ("q", "enter", "escape"):
          self.screen = Screen.MAIN
          return self, None
      return self, None
  ```

- [ ] **Step 2: Update `_view_calibre` footer**

  Find (line ~1550):
  ```python
  lines.append(self._footer("Enter/q  quit"))
  ```
  Replace with:
  ```python
  lines.append(self._footer("Enter/Esc/q  back to menu    Ctrl+C  quit"))
  ```

- [ ] **Step 3: Verify manually**

  Run `cd safaribooks && python3 tui.py`, queue a book, let it complete through the Calibre conversion screen, confirm pressing Enter/q/Esc returns to the main menu rather than exiting the app.

- [ ] **Step 4: Commit**

  ```bash
  cd /home/matt/github/KeroOle
  git add safaribooks/tui.py
  git commit -m "fix: return to main menu after Calibre conversion completes"
  ```

---

## Task 2: Cap Download Screen at 12 Visible Items

**Files:**
- Modify: `safaribooks/tui.py` — `_view_download` (line ~1464)

**Context:** `visible_count = max(1, rows_available // per_book)` can produce 16+ on tall terminals, overflowing the panel. Cap at 12 (12 × 3 lines + 4 header/footer = 40 lines total, fits a standard 40-row terminal).

- [ ] **Step 1: Edit the visible-count line**

  Find (line ~1464):
  ```python
  visible_count = max(1, rows_available // per_book)
  ```
  Replace with:
  ```python
  visible_count = min(12, max(1, rows_available // per_book))
  ```

- [ ] **Step 2: Verify manually**

  Queue 20+ books, run the queue, confirm the display shows at most 12 items at once and auto-scrolls correctly as books complete.

- [ ] **Step 3: Commit**

  ```bash
  git add safaribooks/tui.py
  git commit -m "fix: cap download screen at 12 visible items to prevent panel overflow"
  ```

---

## Task 3: Library Management — `clear_chapter_db()` in `library.py` + Settings Actions

This task has three parts: (A) add the helper to `library.py`, (B) wire up the new TUI state and message, (C) add the settings-screen UI.

### Part A: Add `clear_chapter_db()` to `BookRegistry`

**Files:**
- Modify: `safaribooks/library.py` — after `store_toc()` (line ~274)

- [ ] **Step 1: Add the method**

  After the `store_toc` method (around line 274), insert:
  ```python
  def clear_chapter_db(self):
      """Truncate chapters and toc tables. Registry rows are preserved."""
      self._conn.executescript("""
          DELETE FROM chapters;
          DELETE FROM toc;
      """)
      self._conn.commit()
  ```

- [ ] **Step 2: Verify the method works at the REPL**

  ```bash
  cd safaribooks
  python3 -c "
  from library import BookRegistry
  import os, tempfile
  db = os.path.join(tempfile.mkdtemp(), 'test.db')
  reg = BookRegistry(db)
  reg.clear_chapter_db()   # should not raise
  print('clear_chapter_db OK')
  reg.close()
  "
  ```
  Expected: prints `clear_chapter_db OK` with no errors.

### Part B: Add TUI Message + State for Scan Library

**Files:**
- Modify: `safaribooks/tui.py` — new dataclass, `AppModel.__init__`, `AppModel.update`

- [ ] **Step 3: Add `LibraryScanDoneMsg` dataclass**

  After the existing `@dataclass` message classes (around line 140, after `CalibreAddDoneMsg`), insert:
  ```python
  @dataclass
  class LibraryScanDoneMsg(tea.Msg):
      added: int
      error: str = ""
  ```

- [ ] **Step 4: Add new state fields to `AppModel.__init__`**

  Find the settings state block in `__init__` (around line 583, after `self.settings_status`):
  ```python
  self.settings_status: str = ""
  ```
  Add below it:
  ```python
  self.settings_action_status: str = ""   # "ok:..." or "error:..."
  self.settings_scanning: bool = False
  ```

- [ ] **Step 5: Handle `LibraryScanDoneMsg` in `AppModel.update`**

  Find the `update` method's message dispatcher (around line 626, after the `AllDownloadsDoneMsg` block). Add:
  ```python
  if isinstance(msg, LibraryScanDoneMsg):
      self.settings_scanning = False
      if msg.error:
          self.settings_action_status = f"error:{msg.error}"
      else:
          self.settings_action_status = f"ok:{msg.added} book(s) added to registry"
      return self, None
  ```

### Part C: Settings Screen UI — Keys, Rendering, and Scan Worker

**Files:**
- Modify: `safaribooks/tui.py` — `_key_settings`, `_view_settings`, add `_run_scan_library` method

- [ ] **Step 6: Extend `_key_settings` to handle cursor positions 4 and 5**

  Find `_key_settings` (line ~875). The current handler ends with:
  ```python
  elif len(key) == 1 and key.isprintable():
      self.settings_fields[self.settings_cursor] += key
      self.settings_status = ""
  return self, None
  ```

  The current `n = len(self.settings_fields)` is 4, which already limits cursor navigation to 0–3. Change `n` to 6 and add action dispatching:

  Replace:
  ```python
  def _key_settings(self, key: str):
      n = len(self.settings_fields)
  ```
  With:
  ```python
  def _key_settings(self, key: str):
      n = 6  # 4 editable fields + 2 action buttons
  ```

  Then, just before `return self, None` at the end of `_key_settings`, add:
  ```python
  elif self.settings_cursor == 4 and key == "enter":
      self._run_scan_library()
  elif self.settings_cursor == 5 and key == "enter":
      self._run_clear_chapter_db()
  ```

  Also guard the text-editing and toggle branches so they only fire for cursor positions 0–3:
  - Wrap the `elif self.settings_cursor == 3:` toggle block — no change needed (already position-gated).
  - Wrap `elif key in ("backspace", "delete"):` and `elif key == "ctrl+u":` and the final `elif len(key) == 1` to only apply when `self.settings_cursor < 4`:

  ```python
  elif self.settings_cursor < 4 and key in ("backspace", "delete"):
      val = self.settings_fields[self.settings_cursor]
      self.settings_fields[self.settings_cursor] = val[:-1]
      self.settings_status = ""
  elif self.settings_cursor < 4 and key == "ctrl+u":
      self.settings_fields[self.settings_cursor] = ""
      self.settings_status = ""
  elif self.settings_cursor < 4 and len(key) == 1 and key.isprintable():
      self.settings_fields[self.settings_cursor] += key
      self.settings_status = ""
  ```

- [ ] **Step 7: Add `_run_scan_library` and `_run_clear_chapter_db` methods**

  Add these methods to `AppModel` (e.g., after `_save_settings`):

  ```python
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
              added = reg.scan_existing_books(books_dir)
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
          reg.clear_chapter_db()
          reg.close()
          self.settings_action_status = "ok:Chapter data cleared"
      except Exception as exc:
          self.settings_action_status = f"error:{exc}"
  ```

- [ ] **Step 8: Update `_view_settings` to render the two action buttons**

  In `_view_queue` find and update the label:
  ```python
  lines.append(_toggle("[d] Content DB",      self.export_db))
  ```
  Change to:
  ```python
  lines.append(_toggle("[d] Chapter Content DB", self.export_db))
  ```

  In `_view_settings`, find the final `if self.settings_status:` block and add the action buttons and their shared status line **before** it:

  ```python
  # Action buttons
  scan_focused  = self.settings_cursor == 4
  clear_focused = self.settings_cursor == 5

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
  ```

  Also update the settings footer to include the action hint:
  ```python
  lines.append(self._footer("Tab/↓  next    Enter  save/run    Ctrl+U  clear    Space  toggle    Esc  back"))
  ```

- [ ] **Step 9: Smoke-test the settings screen**

  Run `python3 tui.py`, navigate to **Export Paths / Settings**, use Tab/↓ to reach **Scan Library** (position 4) and **Clear Chapter DB** (position 5), press Enter on each, confirm inline status messages appear correctly.

- [ ] **Step 10: Commit**

  ```bash
  git add safaribooks/tui.py safaribooks/library.py
  git commit -m "feat: rename Content DB label, add Scan Library and Clear Chapter DB to settings"
  ```

---

## Task 4: EPUB Metadata — Extract Author/Publisher from Downloaded XHTML

This task adds `_extract_metadata_from_xhtml()` to `KeroOle` and injects it into the download pipeline.

### Part A: Tests First

**Files:**
- Create: `safaribooks/tests/test_xhtml_extraction.py`

- [ ] **Step 1: Create the test file**

  ```python
  # safaribooks/tests/test_xhtml_extraction.py
  """Tests for _extract_metadata_from_xhtml in KeroOle."""
  import os
  import sys
  import tempfile
  import pytest

  sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
  from kerole import KeroOle

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
  ```

- [ ] **Step 2: Run tests — expect all to FAIL (method doesn't exist yet)**

  ```bash
  cd safaribooks
  python3 -m pytest tests/test_xhtml_extraction.py -v 2>&1 | head -40
  ```
  Expected: `AttributeError: '_extract_metadata_from_xhtml'` or similar for all tests.

### Part B: Implement `_extract_metadata_from_xhtml`

**Files:**
- Modify: `safaribooks/kerole.py` — add method to `KeroOle` class

- [ ] **Step 3: Add the method**

  Find the end of the `KeroOle` class — a good insertion point is just before `create_content_opf` (around line 1095). Insert:

  ```python
  def _extract_metadata_from_xhtml(self) -> tuple:
      """Scan the first 10 downloaded XHTML files for author/publisher metadata.

      Used as a fallback when the v2 API returns empty authors/publishers.
      Returns (authors, publishers) in book_info list format:
          authors    = [{"name": "..."}, ...]
          publishers = [{"name": "..."}, ...]
      """
      import re as _re
      from lxml import html as lhtml

      oebps = os.path.join(self.BOOK_PATH, "OEBPS")
      authors: list = []
      publishers: list = []

      for ch in self.book_chapters[:10]:
          fname = ch.get("filename", "")
          if not fname:
              continue
          # Disk files use .xhtml; chapter list from v2 API may say .html
          xhtml_fname = fname.replace(".html", ".xhtml")
          fpath = os.path.join(oebps, xhtml_fname)
          if not os.path.isfile(fpath):
              continue

          try:
              with open(fpath, encoding="utf-8", errors="replace") as f:
                  content = f.read()
              tree = lhtml.fromstring(content.encode("utf-8"))
          except Exception:
              continue

          def _classes(el):
              return el.get("class", "").split()

          # ── Author extraction ─────────────────────────────────────────────
          if not authors:
              for el in tree.iter():
                  cls = _classes(el)
                  matched = (
                      "author" in cls
                      or "authorName" in cls
                      or "bookAuthor" in cls
                  )
                  if not matched:
                      continue
                  text = (el.text_content() or "").strip()
                  # Collapse whitespace, strip leading "by "
                  text = _re.sub(r"\s+", " ", text).strip()
                  text = _re.sub(r"^by\s+", "", text, flags=_re.IGNORECASE).strip()
                  if text and len(text) < 120:
                      authors.append({"name": text})
                      break  # first match wins

          # ── Publisher extraction ─────────────────────────────────────────
          if not publishers:
              # Pattern 1: class="publishername"
              for el in tree.iter():
                  if "publishername" in _classes(el):
                      text = (el.text_content() or "").strip().rstrip(",").strip()
                      if text and len(text) < 120:
                          publishers.append({"name": text})
                          break

              # Pattern 2: "Published by ..." in copyright text
              if not publishers:
                  for el in tree.iter():
                      cls = _classes(el)
                      ep  = el.get("epub:type", "")
                      if "copyright" not in cls and "copyright-page" not in ep:
                          continue
                      full_text = el.text_content() or ""
                      m = _re.search(
                          r"[Pp]ublished by\s+([^,\n]{3,80})", full_text
                      )
                      if m:
                          publishers.append({"name": m.group(1).strip()})
                          break

          if authors and publishers:
              break  # done — no need to scan more files

      return authors, publishers
  ```

- [ ] **Step 4: Run tests — expect all to PASS**

  ```bash
  cd safaribooks
  python3 -m pytest tests/test_xhtml_extraction.py -v
  ```
  Expected: all tests pass.

### Part C: Inject into Download Pipeline

**Files:**
- Modify: `safaribooks/kerole.py` — `__init__` method, between `collect_images()` and `create_epub()`

- [ ] **Step 5: Add the injection call**

  Find this sequence (lines ~451–454):
  ```python
  self.collect_images()

  self.display.info("Creating EPUB file...", state=True)
  self.create_epub()
  ```
  Replace with:
  ```python
  self.collect_images()

  # Fill in author/publisher for v2 books where the API returns empty lists
  if self.api_v2 and not self.book_info.get("authors"):
      _authors, _publishers = self._extract_metadata_from_xhtml()
      if _authors:
          self.book_info["authors"] = _authors
      if _publishers:
          self.book_info["publishers"] = _publishers

  self.display.info("Creating EPUB file...", state=True)
  self.create_epub()
  ```

- [ ] **Step 6: Run the full test suite**

  ```bash
  cd safaribooks
  python3 -m pytest tests/ -v
  ```
  Expected: all pre-existing tests still pass, all new tests pass.

- [ ] **Step 7: Verify with a real download**

  In the TUI, queue the Understanding Color book (ID `9781118920787`) which previously had empty author/publisher, and download it. After completion:

  ```bash
  grep -E "dc:creator|dc:publisher" \
    "Books/Understanding Color 5th Edition (9781118920787)/OEBPS/content.opf"
  ```
  Expected output includes:
  ```
  <dc:creator opf:file-as="Linda Holtzschue" opf:role="aut">Linda Holtzschue</dc:creator>
  <dc:publisher>John Wiley &amp; Sons, Inc.</dc:publisher>
  ```

  Also check in Calibre: add the newly-downloaded EPUB and confirm Author and Publisher fields are populated.

- [ ] **Step 8: Commit**

  ```bash
  cd /home/matt/github/KeroOle
  git add safaribooks/kerole.py safaribooks/tests/test_xhtml_extraction.py
  git commit -m "feat: extract author/publisher from XHTML for v2 API books where API returns none"
  ```

---

## Final Verification

- [ ] Run full test suite one more time from clean state:
  ```bash
  cd safaribooks
  python3 -m pytest tests/ -v
  ```
  Expected: all tests pass.

- [ ] Launch the TUI and walk through all five changed flows:
  1. Queue a book → download → Calibre screen → press q → confirm main menu appears
  2. Queue 20 books → confirm download screen shows ≤ 12 at a time with scroll indicator
  3. Queue screen → confirm label reads `[d] Chapter Content DB`
  4. Settings → Tab to position 4 → Enter → confirm scan runs and reports count
  5. Settings → Tab to position 5 → Enter → confirm chapter data cleared message
  6. Check a newly-downloaded v2 book in Calibre for Author/Publisher fields
