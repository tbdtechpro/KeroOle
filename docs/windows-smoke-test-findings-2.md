# Windows Smoke Test Findings — Round 2

**Date:** 2026-03-27
**Machine:** Windows 11 IoT Enterprise LTSC 2024 (10.0.26100)
**Python:** 3.14.3 (`C:\Users\MatthewPhelps\AppData\Local\Programs\Python\Python314\python.exe`)
**Git:** 2.53.0.windows.2
**bubblepy:** updated (pulled latest before this run)
**pygloss:** 0.1.0 (no changes since last run)

---

## Result: FAIL

| Check | Pass/Fail | Notes |
|---|---|---|
| Rounded border appears | FAIL | UnicodeEncodeError before render |
| Border is purple/violet | FAIL | UnicodeEncodeError before render |
| `q` exits cleanly | FAIL | Crashed on cleanup |

---

## Progress Since Round 1

The `termios`/`tty` import error from Round 1 is **fixed** in the updated bubblepy.
Two new issues were encountered and resolved/identified:

### Issue 1 — pygloss namespace collision (resolved)
Running `smoke_test.py` from `C:\Users\MatthewPhelps\AppData\Local\Temp\` caused Python
to add that directory to `sys.path`, which picked up the `pygloss\` repo root as a
namespace package instead of the real installed package. This caused:

```
ImportError: cannot import name 'Color' from 'pygloss' (unknown location)
```

**Workaround:** Moved `smoke_test.py` to an isolated folder (`C:\TEMP\smoke\`) away
from the cloned repos. Import then succeeded.

### Issue 2 — UnicodeEncodeError in renderer (active / blocking)
Once running, `bubblepy` crashes when trying to render the rounded border:

```
UnicodeEncodeError: 'charmap' codec can't encode characters in position 10-30:
character maps to <undefined>
  File "bubblepy\renderer.py", line 163, in _flush
    self.output.write(view.replace("\n", "\r\n"))
  File "...\encodings\cp1252.py", line 19, in encode
    return codecs.charmap_encode(input, self.errors, encoding_table)[0]
```

The rounded border uses Unicode box-drawing characters (`╭ ╮ ╰ ╯ ─ │`) that do not
exist in Windows CP1252 (the default terminal codepage). The crash occurs in both
the renderer thread and during cleanup, so the program exits with exit code 1.

---

## Root Cause

`bubblepy/renderer.py` writes to the output stream without setting an encoding,
inheriting the Windows default of CP1252. Box-drawing characters are outside the
CP1252 range and cannot be encoded.

---

## Fix Needed

`bubblepy/renderer.py` needs to ensure UTF-8 output on Windows. Options:

**Option A — Wrap stdout with UTF-8 at renderer init:**
```python
import io, sys
if sys.platform == "win32":
    self.output = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="")
```

**Option B — Enable UTF-8 mode via environment before launch:**
```
set PYTHONUTF8=1
python smoke_test.py
```

**Option C — Set console codepage before writing:**
```python
import os
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
```

Option A is the most robust and self-contained fix.

---

## Resolution

The UTF-8 output issue in `bubblepy/renderer.py` was resolved as part of the
cross-platform runtime compatibility work (commit `c03d0ba`). The renderer now
wraps stdout with a UTF-8 `TextIOWrapper` on Windows. Subsequent app testing
(see `windows-app-test-findings.md`) confirmed TUI rendering passes. Clipboard
(Ctrl+V) and Calibre conversion remain untested in live interactive use.
