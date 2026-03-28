# KeroOle

<!-- Logo placeholder — coming soon -->

Download and export ebooks from your [O'Reilly Learning](https://learning.oreilly.com) subscription. Produces EPUB, GFM Markdown, Obsidian Markdown, RAG JSONL, and a searchable SQLite library — all from an interactive terminal UI.

> **Note:** KeroOle is a maintained fork of [lorenzodifuccia/safaribooks](https://github.com/lorenzodifuccia/safaribooks).
> Credit and thanks to Lorenzo Di Fuccia for the original download pipeline and EPUB assembly.

*For personal and educational use only. Please read the O'Reilly [Terms of Service](https://learning.oreilly.com/terms/) before use.*

---

## Platform Support

| Platform | Status | Notes |
|---|---|---|
| **Linux** | Supported | Primary development platform (Ubuntu 24.04) |
| **Windows** | Experimental — partially tested | TUI renders correctly; clipboard and Calibre conversion not yet verified end-to-end |
| **macOS** | Experimental — untested | Build script included; no test results yet |

---

## Contents

- [Requirements & Setup](#requirements--setup)
- [Authentication](#authentication)
- [TUI Overview](#tui-overview)
- [Export Features](#export-features)
- [Configuration](#configuration)
- [Library Management](#library-management)
- [Calibre Integration](#calibre-integration)
- [Standalone Executable](#standalone-executable)
- [Credits & License](#credits--license)

---

## Requirements & Setup

**Python 3.10+** and **[Calibre](https://calibre-ebook.com/)** are required.

### Linux (Ubuntu / Debian)

```bash
git clone https://github.com/tbdtechpro/KeroOle.git
cd KeroOle/
chmod +x setup.sh
./setup.sh
source .venv/bin/activate
python main.py
```

The setup script installs system packages (Python 3, build tools, Calibre), creates a `.venv`, and installs all Python dependencies.

### Windows (experimental)

See [Standalone Executable](#standalone-executable) for the easiest path. To run from source:

```powershell
pip install lxml requests browser_cookie3 pyperclip colorama
# Install bubblepy and pygloss from https://github.com/tbdtechpro/bubblepy
# and https://github.com/tbdtechpro/pygloss via `pip install -e .`
python main.py
```

### macOS (experimental — untested)

```bash
pip3 install lxml requests browser_cookie3 pyperclip colorama
# Install bubblepy and pygloss as above
python3 main.py
```

---

## Authentication

KeroOle requires an active O'Reilly Learning subscription. Two methods work:

### Option 1 — Extract Cookies from Browser (recommended)

Sign in to [learning.oreilly.com](https://learning.oreilly.com) in Chrome, Firefox, or Edge, then select **"Extract Cookies from Browser"** in the KeroOle main menu. Cookies are saved to `cookies.json` automatically and reused until the session expires.

This works for all login methods including SSO and Google login.

### Option 2 — Paste Session Cookie Manually

If browser extraction fails, copy the session cookie from your browser's DevTools:

1. Open DevTools → Network → any request to `learning.oreilly.com`
2. Copy the `Cookie:` header value
3. Select **"Set Session Cookie (paste)"** in KeroOle and paste it

> **Security note:** Anyone with access to `cookies.json` can use your O'Reilly session. Keep the file private.

> **Note:** Email/password login is present in the menu but is currently non-functional due to changes in the O'Reilly authentication flow. Use one of the cookie methods above.

---

## TUI Overview

Launch the terminal UI:

```bash
python main.py
# or, if using the standalone build:
./KeroOle
```

### Main Menu

```
  KeroOle
  ─────────────────────────
  Extract Cookies from Browser
  Set Session Cookie (paste)
  Search O'Reilly
  Add Book to Queue
  View / Run Queue
  Browse Library
  Sync with Calibre Library
  Export Paths / Settings
  Quit
```

### Searching

**Search O'Reilly** opens a two-phase search UI:

- Enter a query, optionally filter by format (`books` / `videos` / `all`), topic, or publisher
- Toggle sort between relevance and newest
- `[` / `]` pages through results
- `Space` to add books to the download queue
- `r` / `Enter` to confirm and go to the queue

### Downloading

**Add Book to Queue** accepts book IDs (the number in the O'Reilly URL) one at a time. Paste multiple IDs line by line.

**View / Run Queue** shows queued books with export toggles:

| Key | Toggle |
|---|---|
| `g` | GFM Markdown export |
| `o` | Obsidian Markdown export |
| `d` | Content DB storage |
| `x` | RAG JSONL export |
| `k` | Skip if already downloaded |
| `r` | Run all downloads |

Progress is shown per-book with chapter count and download percentage. Books that fail during download are listed in a summary at the end.

### Library Browse

**Browse Library** lists all books in your local registry with status badges:

```
  [DB] [MD]  AI Engineering                   2024  Chip Huyen
  [DB]       The Kubernetes Book               2024  Nigel Poulton
             Node.js for Beginners            2024  ...
```

- `Space` — toggle selection
- `a` — select / deselect all
- `e` — export selected books
- `A` — export all books
- `/` — filter by title

---

## Export Features

All outputs are stored under `Books/{book-title}/` next to the downloaded EPUB. Output paths can be overridden globally in Settings.

### EPUB

Every download produces a standards-compliant EPUB at `Books/{title}/{book_id}.epub`. After download, Calibre conversion runs automatically (when Calibre is installed), producing `{book_id}_calibre.epub` with improved reader compatibility.

### GFM Markdown

Each chapter is exported as GitHub Flavored Markdown under `Books/{title}/markdown/`:

```
Books/{title}/markdown/
├── images/
├── ch01.md
├── ch02.md
└── _book.md      ← all chapters combined
```

Images without `alt` text automatically get alt text derived from the filename.

Enable: toggle `g` in the Queue screen, or set `markdown_gfm = true` in `~/.kerole.toml`.

### Obsidian Markdown

A second Markdown export optimized for [Obsidian](https://obsidian.md) vaults:

- **YAML frontmatter** on every chapter file (title, authors, publisher, tags, source URL)
- **`![[filename]]` image embeds** (Obsidian wiki-style)
- **`> [!note]` / `> [!tip]` / `> [!warning]` callouts** from O'Reilly `data-type` elements
- **`[[chapter-stem|Title]]` wiki-links** for cross-chapter references — shows as graph edges in Obsidian
- **`_book.md` MOC (Map of Content)** index note linking all chapters — creates a hub node in the graph

Set `markdown_obsidian_dir` in Settings to your vault root and KeroOle will write directly into it.

Enable: toggle `o` in the Queue screen, or set `markdown_obsidian = true` in `~/.kerole.toml`.

### Content DB (`--export-db`)

Stores raw XHTML and converted Markdown for every chapter, plus a flattened TOC, in `Books/library.db` (SQLite):

```bash
sqlite3 Books/library.db ".tables"
# chapters  chapters_fts  registry  toc

sqlite3 Books/library.db \
  "SELECT title, markdown_text FROM chapters WHERE book_id='9781098166298' LIMIT 1"
```

A **FTS5 full-text search index** (`chapters_fts`) is maintained automatically. Search across all downloaded chapters:

```sql
SELECT book_id, title, snippet(chapters_fts, 2, '[', ']', '…', 64) AS excerpt
FROM chapters_fts
WHERE chapters_fts MATCH 'transformer attention'
ORDER BY rank LIMIT 20;
```

### RAG JSONL Export (`--export-rag`)

Heading-chunked JSONL for retrieval-augmented generation pipelines:

```json
{
  "book_id": "9781098166298",
  "title": "AI Engineering",
  "authors": ["Chip Huyen"],
  "chapter_filename": "ch01.xhtml",
  "chapter_title": "Introduction",
  "section_heading": "From Language Models to LLMs",
  "section_depth": 2,
  "chunk_index": 0,
  "text": "...",
  "approx_tokens": 487,
  "source_url": "https://learning.oreilly.com/library/view/..."
}
```

Output: `Books/{title}/rag/{book_id}_rag.jsonl`. Implies `--export-db`.

---

## Configuration

KeroOle stores user configuration in `~/.kerole.toml`. Edit directly or use the **Export Paths / Settings** screen in the TUI.

```toml
[exports]
# Output directories (blank = default inside each book's Books/ folder)
markdown_gfm_dir      = ""        # e.g. "~/Documents/Books/MD"
markdown_obsidian_dir = ""        # e.g. "~/Documents/ObsidianVault"
rag_dir               = ""        # e.g. "~/Documents/Books/RAG"
db_path               = ""        # e.g. "~/Documents/Books/library.db"

# Folder naming: "title" (default) or "id" (numeric book ID)
folder_name_style = "title"

# Enable export formats automatically on every download
markdown_gfm      = false
markdown_obsidian = false

# After Calibre conversion, delete the pre-conversion EPUB
delete_original_epub = false
```

All paths support `~` expansion.

---

## Library Management

### Scan Existing Books

If you have Books already downloaded (or migrated from a previous install), populate the registry without re-downloading:

In the TUI: **Export Paths / Settings** → **Scan Library**

Or from the command line:
```bash
python kerole.py --scan-library
```

### Full-Text Search (SQLite)

The `chapters_fts` FTS5 virtual table enables full-text search across all downloaded chapter content. Rebuild the index after adding books outside KeroOle:

```sql
INSERT INTO chapters_fts(chapters_fts) VALUES('rebuild');
```

### Cleanup Script

After Calibre conversion, remove original pre-conversion EPUBs where a `_calibre.epub` already exists:

```bash
# Preview what would be deleted
./cleanup_original_epubs.sh --dry-run

# Delete
./cleanup_original_epubs.sh
```

---

## Calibre Integration

[Calibre](https://calibre-ebook.com/) is used for two things:

### 1. EPUB Post-Processing

After each download, KeroOle runs `ebook-convert` to produce a clean, reader-compatible EPUB (`{book_id}_calibre.epub`). The TUI shows conversion progress per-book.

To convert books that were downloaded before this was added:

```bash
python calibre_convert.py Books/*/*.epub
```

### 2. Sync with Calibre Library

**Sync with Calibre Library** in the TUI scans your local `Books/` folder and your Calibre library, then shows unsynced books. Select books with `Space` and press `Enter` to add them to Calibre.

---

## Standalone Executable

Build a self-contained binary (no Python required on the target machine):

### Linux

```bash
chmod +x build-linux.sh
./build-linux.sh
```

### Windows (experimental)

```powershell
.\build-windows.ps1
```

### macOS (experimental — untested)

```bash
chmod +x build-macos.sh
./build-macos.sh
```

The build output:

```
KeroOle/
  KeroOle          ← Linux / macOS
  KeroOle.exe      ← Windows
  _internal/       ← PyInstaller support files
  Books/           ← download output (created at runtime)
```

---

## Credits & License

**Credits:**
- Original project: [lorenzodifuccia/safaribooks](https://github.com/lorenzodifuccia/safaribooks) by Lorenzo Di Fuccia — the foundational download pipeline, EPUB assembly, and chapter extraction logic come from SafariBooks. The original code was released under WTFPL v2; recipients of prior versions retain WTFPL rights for those versions.
- This fork (KeroOle): [tbdtechpro/KeroOle](https://github.com/tbdtechpro/KeroOle)

For issues, please open a ticket on the [tbdtechpro/KeroOle](https://github.com/tbdtechpro/KeroOle/issues) repository.

**License:**

KeroOle is licensed under the [Beer for the Worker License (BWL) v1.0](LICENSE.md).

**In short:** Free for individuals and worker-owned organizations, including commercial use. Corporations may not use this software without explicit written permission from the copyright holders. Prior versions distributed under WTFPL v2 retain that license for those versions.
