# Windows Test Plan — 2026-03-28

**Purpose:** Close out remaining Windows verification items and smoke-test the PyInstaller exe.

Two sessions: **Part A** runs from source (existing venv). **Part B** builds and tests the standalone exe.

---

## Setup

Open **Windows Terminal** (not cmd.exe, not PowerShell ISE).

Pull latest code first:

```powershell
cd KeroOle
git pull
```

---

## Part A — Interactive Application Test (from source)

Tests that are still open from `windows-app-test-findings.md`:
clipboard paste (live), full download flow, Calibre conversion.

### A1 — Baseline render (re-confirm with latest code)

```powershell
python main.py
```

- [ ] App launches without errors
- [ ] Main menu renders with purple/violet border, no garbled characters
- [ ] `q` exits cleanly

---

### A2 — Login

From the main menu:

- [ ] Navigate to **Login with Email/Password**
- [ ] Enter credentials
- [ ] Cookie status changes from `○ Cookie: not set` to a filled indicator
- [ ] No errors or tracebacks

---

### A3 — Clipboard paste — cookie screen

> Copy any text (e.g. a test string) to the Windows clipboard first.

- [ ] Navigate to **Set Session Cookie (paste)**
- [ ] Press **Ctrl+V**
- [ ] Confirm the pasted text appears in the input field
- [ ] Confirm the status line reads something like `ok: N chars read from clipboard`
- [ ] Press Escape or back out without saving

---

### A4 — Clipboard paste — add book screen

> Copy a book ID or URL to the clipboard (e.g. `9781491958698`).

- [ ] Navigate to **Add Book to Queue**
- [ ] Press **Ctrl+V**
- [ ] Confirm the book ID / URL pastes into the input field correctly

---

### A5 — Full download

Queue and download a small book (fewer chapters = faster):

- [ ] Add a book ID to the queue (e.g. `9781491958698`)
- [ ] Navigate to **View / Run Queue / Export**
- [ ] Press `r` to run
- [ ] Download completes without errors
- [ ] EPUB appears in `Books\<title>\<bookid>.epub`
- [ ] `cookies.json` is present in the repo root (not inside `_internal\`)
- [ ] Return to main menu automatically after completion

---

### A6 — Calibre conversion (skip if Calibre not installed)

If Calibre is installed:

- [ ] After a successful download, trigger Calibre conversion from the TUI
- [ ] Conversion completes and returns to the main menu
- [ ] `<bookid>_calibre.epub` appears in the book directory
- [ ] Colour output appears in the conversion log (ANSI colours rendering correctly)

---

### A7 — Record findings

Save results to `docs/windows-interactive-test-findings-2026-03-28.md` (or ask Claude Code to record them for you). Note any failures with the full error message / traceback.

---

---

## Part B — PyInstaller Exe Test

Build the standalone exe and verify it runs correctly.

### B1 — Run the build script

From the repo root in PowerShell:

```powershell
.\build-windows.ps1
```

Expected output:
- Python version check passes
- `.build-venv\` is created (or reused if it already exists)
- `pyinstaller`, `lxml`, `requests`, `browser_cookie3`, `pyperclip`, `colorama`, `bubblepy`, `pygloss` install without errors
- PyInstaller build completes
- `KeroOle.exe` is moved to the repo root
- `_internal\` is moved to the repo root
- `dist\` and `build\` are cleaned up

- [ ] Build script completes without errors
- [ ] `KeroOle.exe` exists at repo root
- [ ] `_internal\` exists at repo root
- [ ] `dist\` and `build\` are absent (cleaned up)

---

### B2 — Exe launches

```powershell
.\KeroOle.exe
```

- [ ] App launches without errors
- [ ] Main menu renders correctly (same as A1)
- [ ] `q` exits cleanly

---

### B3 — File paths are correct (not inside `_internal\`)

After launching the exe and then quitting (or after a download):

- [ ] `Books\` directory is created at the repo root, **not** inside `_internal\`
- [ ] `cookies.json` (if it exists) is at the repo root, **not** inside `_internal\`
- [ ] Log files (if any) appear at the repo root, **not** inside `_internal\`

---

### B4 — Login from exe

- [ ] Navigate to **Login with Email/Password**
- [ ] Enter credentials
- [ ] Login succeeds
- [ ] `cookies.json` written to repo root

---

### B5 — Full download from exe

- [ ] Add a book to the queue
- [ ] Run the download
- [ ] EPUB appears in `Books\<title>\` at the repo root
- [ ] Download completes and returns to main menu

---

### B6 — Idempotent build (re-run = no-op)

Run the build script a second time:

```powershell
.\build-windows.ps1
```

- [ ] Script completes without errors
- [ ] Skips steps that are already done (no re-install of packages unless flagged)
- [ ] Existing `KeroOle.exe` is replaced cleanly

---

### B7 — Record findings

Save results to `docs/windows-exe-test-findings-2026-03-28.md`. Note any failures with full error output.

---

---

## Summary Checklist

| ID | Area | Status |
|---|---|---|
| A1 | Baseline render (latest code) | |
| A2 | Login | |
| A3 | Clipboard paste — cookie screen | |
| A4 | Clipboard paste — add book screen | |
| A5 | Full download | |
| A6 | Calibre conversion | |
| B1 | Build script completes | |
| B2 | Exe launches | |
| B3 | File paths at repo root (not `_internal\`) | |
| B4 | Login from exe | |
| B5 | Full download from exe | |
| B6 | Idempotent build | |

---

## Known Limitations Going In

- Clipboard (Ctrl+V) is source-verified only — this will be the first live test
- Calibre has not been installed on the test machine; B-tests will skip A6 if still absent
- macOS is untested; Windows findings here do not imply macOS works
