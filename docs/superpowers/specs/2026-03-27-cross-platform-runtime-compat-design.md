# Design: Cross-Platform Runtime Compatibility (Spec 1 of 2)

**Date:** 2026-03-27
**Scope:** Make KeroOle run natively on Windows Terminal, macOS, and any Linux distro. No packaging yet — that is Spec 2.

---

## Background

KeroOle currently assumes Ubuntu/Debian: clipboard code shells out to `xclip`/`xsel`, Calibre binaries are expected on `PATH` (which Windows installers may not set), ANSI colour constants are disabled on Windows, and the entry-point file is named `tui.py`. This spec fixes each of those in isolation so the app works on all three platforms from a plain `python main.py` invocation.

---

## Gate: Verify bubblepy/pygloss on Windows Terminal

**This must be done before any code changes. It is a go/no-go gate for the entire spec.**

bubblepy and pygloss are ANSI-based TUI libraries. Windows Terminal (Windows 10+) supports ANSI natively, but the Python port's input loop must be verified to handle Windows Terminal's VT sequences correctly.

**Smoke test (local only, not committed):**

```python
# smoke_test.py
import bubblepy as tea
from pygloss import Color, Style, rounded_border

class Smoke(tea.Model):
    def init(self): return []
    def update(self, msg):
        if isinstance(msg, tea.KeyMsg) and str(msg) in ("q", "ctrl+c"):
            return self, tea.Quit()
        return self, None
    def view(self):
        return (Style().border(rounded_border())
                .border_foreground(Color("#7C3AED"))
                .padding(1, 2)
                .render("bubblepy OK\n\nPress q to quit"))

if __name__ == "__main__":
    tea.Program(Smoke(), alt_screen=True).run()
```

Run in **Windows Terminal** (not cmd.exe, not classic PowerShell). Pass criteria: border renders, colours appear, `q` exits cleanly.

**If the smoke test fails:** Stop. Do not proceed with the other changes. Diagnose the bubblepy issue first — it may require a fix to the bubblepy/pygloss libraries themselves before cross-platform support is achievable.

---

## Change 1: Rename `tui.py` → `main.py`

`tui.py` is the app entry point, not a module — renaming it to `main.py` follows Python conventions and enables `pyinstaller --name KeroOle main.py` in Spec 2.

**Confirmed safe:** No other file imports `tui` as a module. The rename is a pure `git mv`.

```bash
git mv safaribooks/tui.py safaribooks/main.py
```

---

## Change 2: Cross-Platform Clipboard

### Problem

`tui.py` clipboard methods shell out to `wl-paste`, `xclip`, `xsel` in sequence. These are Linux X11/Wayland tools only.

### Solution

Replace both clipboard methods with `pyperclip`, which handles:
- **Linux:** xclip or xsel (same backends, managed by pyperclip)
- **macOS:** `pbpaste`/`pbcopy` (built in, no extra tools)
- **Windows:** Win32 `ctypes` clipboard API (no external tools)

The two existing methods `_read_clipboard` and `_read_clipboard_book` are functionally identical — collapse into a shared `_read_clipboard_impl`:

```python
def _read_clipboard(self):
    self.cookie_status = "ok:Reading clipboard…"
    self._read_clipboard_impl()

def _read_clipboard_book(self):
    self._read_clipboard_impl()

def _read_clipboard_impl(self):
    def _worker():
        try:
            import pyperclip
            text = pyperclip.paste()
            self._program.send(ClipboardMsg(text.strip() if text else ""))
        except Exception:
            self._program.send(ClipboardMsg(""))
    threading.Thread(target=_worker, daemon=True).start()
```

The `import pyperclip` inside the worker isolates any `PyperclipException` (raised when no clipboard mechanism is found) within the try/except, resulting in `ClipboardMsg("")` — identical to the current fallthrough behaviour.

### Clipboard Error Strings to Update

Two error strings in `main.py` (formerly `tui.py` lines 721 and 727) currently read:
```
"error:Could not read clipboard. Install xclip, xsel, or wl-paste."
```
Replace with a platform-aware message:
```python
import sys as _sys
if _sys.platform == "win32":
    _clip_hint = "Clipboard unavailable."
elif _sys.platform == "darwin":
    _clip_hint = "Clipboard unavailable."
else:
    _clip_hint = "Could not read clipboard. Install xclip or xsel."
```
Or simply: `"error:Could not read clipboard."` — the tool-specific guidance is no longer relevant once pyperclip manages the backends.

### Cookie Screen Hint Text

`main.py` line ~1405 (cookie screen "Option 2" instructions) contains:
```
"       xclip -o | python3 retrieve_cookies.py --stdin"
```
Replace with a platform-appropriate hint:
- Linux: `xclip -o | python3 retrieve_cookies.py --stdin`
- macOS: `pbpaste | python3 retrieve_cookies.py --stdin`
- Windows: `Get-Clipboard | python3 retrieve_cookies.py --stdin`

Use `sys.platform` to select the right string at render time.

**Dependency added:** `pyperclip>=1.8.0`

---

## Change 3: Calibre Binary Discovery

### Problem

`calibre_convert.py` defines `EBOOK_CONVERT = "ebook-convert"` and `CALIBREDB = "calibredb"` as bare strings. `calibre_sync.py` and two workers in `tui.py` also hardcode these names. On Windows, Calibre's GUI installer does not add its directory to `PATH` by default. On macOS, the `.dmg` install puts binaries in `/Applications/calibre.app/Contents/MacOS/`.

### Solution

New `safaribooks/platform_utils.py` with a single public function:

```python
import shutil
import sys
from pathlib import Path

_CALIBRE_MACOS_DIR = Path("/Applications/calibre.app/Contents/MacOS")
_CALIBRE_WIN_DIRS = [
    Path(r"C:\Program Files\Calibre2"),
    Path(r"C:\Program Files (x86)\Calibre2"),
]

def find_calibre_binary(name: str) -> str:
    """Return the path to a Calibre binary by name.

    Search order:
      1. PATH (works for all standard installs, Homebrew on macOS, etc.)
      2. macOS: /Applications/calibre.app/Contents/MacOS/<name>
      3. Windows: C:\\Program Files\\Calibre2\\<name>.exe (and x86 variant)

    Returns the full path if found, or bare `name` as fallback
    (preserving the original FileNotFoundError behaviour at the call site).
    """
    found = shutil.which(name)
    if found:
        return found
    if sys.platform == "darwin":
        candidate = _CALIBRE_MACOS_DIR / name
        if candidate.is_file():
            return str(candidate)
    elif sys.platform == "win32":
        for d in _CALIBRE_WIN_DIRS:
            candidate = d / (name + ".exe")
            if candidate.is_file():
                return str(candidate)
    return name  # fallback — FileNotFoundError propagates at call site as before
```

`platform_utils.py` imports only stdlib (`shutil`, `sys`, `pathlib`) — zero coupling to the rest of the codebase.

### Call Sites (4 total)

**`calibre_convert.py` lines 24–25** — replace module-level string constants:
```python
from platform_utils import find_calibre_binary
EBOOK_CONVERT = find_calibre_binary("ebook-convert")
CALIBREDB     = find_calibre_binary("calibredb")
```
All downstream subprocess calls in this file already use these constants. No other changes needed.

**`calibre_sync.py` line ~75** — add module-level constant matching the pattern above:
```python
from platform_utils import find_calibre_binary
CALIBREDB = find_calibre_binary("calibredb")
```
Use `CALIBREDB` in the subprocess call.

**`main.py` `CalibreWorker._run()` line ~495** — replace `"ebook-convert"` literal:
```python
from platform_utils import find_calibre_binary
# in _run():
[find_calibre_binary("ebook-convert"), ...]
```

**`main.py` `CalibreAddWorker._run()` line ~453** — replace `"calibredb"` literal.

### Platform-Aware Error Message in `check_calibre()`

`calibre_convert.py` line ~178 contains a Linux-only install hint:
```
"Install it with:  sudo apt-get install calibre"
```
Replace with a platform-aware message:
```python
if sys.platform == "win32":
    hint = "Download from https://calibre-ebook.com/download_windows"
elif sys.platform == "darwin":
    hint = "Download from https://calibre-ebook.com/download_osx"
else:
    hint = "Install with: sudo apt-get install calibre  (or your distro's equivalent)"
print(f"Error: Calibre's `ebook-convert` was not found.\n{hint}", file=sys.stderr)
```

---

## Change 4: ANSI Colours on Windows

### Problem

`kerole.py` lines 52–55 disable all colour codes on Windows:
```python
SH_DEFAULT = "\033[0m" if "win" not in sys.platform else ""
```
Windows Terminal supports ANSI natively, so this is unnecessarily degraded.

### Solution

Remove the four conditional guards — make all four constants unconditional:
```python
SH_DEFAULT   = "\033[0m"
SH_YELLOW    = "\033[33m"
SH_BG_RED    = "\033[41m"
SH_BG_YELLOW = "\033[43m"
```

Add `colorama.just_fix_windows_console()` to `main.py`'s `main()` function. This calls `SetConsoleMode` to enable `ENABLE_VIRTUAL_TERMINAL_PROCESSING` on Windows Terminal — a no-op on Linux and macOS. Crucially, `just_fix_windows_console()` does **not** wrap `sys.stdout` (unlike `colorama.init()`), so it does not interfere with bubblepy/pygloss's direct terminal writes.

```python
def main():
    try:
        import colorama
        colorama.just_fix_windows_console()
    except (AttributeError, ImportError):
        # AttributeError: colorama < 0.4.6 (just_fix_windows_console not yet added)
        # ImportError: colorama not installed (should not happen — it's in requirements)
        try:
            colorama.init(strip=False)
        except Exception:
            pass  # best effort — colours simply won't work on old Windows
    # ... rest of startup
```

**Dependency added:** `colorama>=0.4.6`

---

## Pre-Existing Windows Workaround: `WinQueue` (No Change Required)

`kerole.py` lines 255–260 define `WinQueue` — a plain list shim for `multiprocessing.Queue` — and lines 446, 449 select it on Windows. This workaround exists because multiprocessing Queue objects cannot be serialized across worker processes on Windows. It was added in a prior refactor. **No changes are needed here** — the workaround is already correct and will continue to function. It is documented here so implementers are not surprised by the platform branch.

---

## Change 5: `multiprocessing.freeze_support`

Required by PyInstaller on Windows when the app uses multiprocessing (even if the multiprocessing paths are currently dormant). One line in `main.py`, no-op everywhere else:

```python
if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
```

---

## New Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `pyperclip` | `>=1.8.0` | Cross-platform clipboard |
| `colorama` | `>=0.4.6` | Windows ANSI VT processing |

Both are pure-Python on Linux/macOS. On Windows, `pyperclip` uses `ctypes` (no external tools); `colorama` uses `ctypes` (no DLL dependencies beyond the Windows runtime).

---

## Files Changed

| File | Change |
|------|--------|
| `tui.py` → `main.py` | Rename; colorama init + freeze_support; clipboard consolidation; calibre call sites; clipboard error strings; cookie screen hint text |
| `kerole.py` | Remove 4 Windows colour guards (lines 52–55) — `WinQueue` workaround untouched |
| `calibre_convert.py` | Replace module-level string constants with `find_calibre_binary`; update `check_calibre()` error message |
| `calibre_sync.py` | Add module-level `CALIBREDB = find_calibre_binary("calibredb")` |
| `platform_utils.py` | **New file** — Calibre binary discovery |
| `requirements.txt` | Add `colorama>=0.4.6`, `pyperclip>=1.8.0` |

---

## Testing

### Automated
- `pytest tests/` must pass on Linux with no regressions
- Unit tests for `find_calibre_binary` using `unittest.mock.patch`:
  - `shutil.which` returns None + macOS fallback path exists → returns macOS path
  - `shutil.which` returns None + Windows fallback path exists → returns `.exe` path
  - `shutil.which` returns path → returns that path immediately
  - Nothing found → returns bare name

### Manual (per platform)
| Scenario | Linux | macOS | Windows Terminal |
|----------|-------|-------|-----------------|
| TUI launches | existing | verify | verify (gate first) |
| Clipboard paste works | existing | verify | verify |
| Calibre converts (PATH install) | existing | verify | verify |
| Calibre converts (default install, not in PATH) | n/a | verify | verify |
| Colours appear in download log | existing | n/a | verify |

---

## Non-Goals

- Windows cmd.exe or classic PowerShell support (Windows Terminal only)
- WSL support
- `setup.sh` updates or new setup scripts (Spec 2)
- PyInstaller configuration (Spec 2)
- Wayland-native clipboard without XWayland (pyperclip falls back to empty string, same as current behaviour)
- Backfilling ANSI colour support in `tui.py` / pygloss rendering paths (pygloss handles this independently)
