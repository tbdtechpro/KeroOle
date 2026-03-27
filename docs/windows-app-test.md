# Windows App Test — KeroOle Cross-Platform Verification

**Date:** 2026-03-27
**Purpose:** Verify the cross-platform runtime changes work end-to-end on Windows Terminal.

---

## 1. Setup

Open **Windows Terminal** (not cmd.exe, not classic PowerShell ISE).

### Pull latest KeroOle
```powershell
cd KeroOle
git pull
```

### Install dependencies
```powershell
pip install lxml requests browser_cookie3 pyperclip colorama
```

> `bubblepy` and `pygloss` should already be installed from the smoke test.
> If not: clone from `https://github.com/tbdtechpro/bubblepy` and
> `https://github.com/tbdtechpro/pygloss` and run `pip install -e .` in each.

---

## 2. Launch

```powershell
python main.py
```

---

## 3. Checklist

### TUI rendering
- [ ] App launches without errors
- [ ] Main menu renders with correct borders and layout
- [ ] Colours appear (purple/violet accents, yellow/red status indicators)
- [ ] No garbled characters or box-drawing artifacts

### Clipboard (cookie screen)
- [ ] Navigate to the cookie entry screen
- [ ] Copy any text to the clipboard
- [ ] Press Ctrl+V — confirm the text is pasted into the input field
- [ ] Confirm the CLI hint at the bottom reads:
      `Get-Clipboard | python3 retrieve_cookies.py --stdin`

### Clipboard (add book screen)
- [ ] Navigate to the add-book screen
- [ ] Copy a URL or book ID to the clipboard
- [ ] Press Ctrl+V — confirm the text pastes correctly

### Calibre (optional — only if Calibre is installed)
- [ ] Download a book
- [ ] Trigger Calibre conversion
- [ ] Confirm conversion completes and returns to the main menu
- [ ] Confirm ANSI colours appear in the download/conversion log output

---

## 4. Reporting

Add a `windows-app-test-findings.md` file in `/docs` with:
- Pass/fail for each checklist item
- Any error messages or tracebacks in full
- Python version and Windows build (already known: Python 3.14.3, Windows 11 26100)
