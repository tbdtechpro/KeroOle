# Windows Smoke Test Findings — KeroOle / bubblepy / pygloss

**Date:** 2026-03-27
**Machine:** Windows 11 IoT Enterprise LTSC 2024 (10.0.26100)
**Python:** 3.14.3 (`C:\Users\MatthewPhelps\AppData\Local\Programs\Python\Python314\python.exe`)
**Git:** 2.53.0.windows.2

---

## Result: FAIL

| Check | Pass/Fail | Notes |
|---|---|---|
| Rounded border appears | FAIL | Crashed before rendering |
| Border is purple/violet | FAIL | Crashed before rendering |
| `q` exits cleanly | FAIL | Crashed before running |

---

## Error

```
Traceback (most recent call last):
  File "smoke_test.py", line 1, in <module>
    import bubblepy as tea
  File "bubblepy\__init__.py", line 54, in <module>
    from .tea import ErrInterrupted, ErrProgramKilled, ErrProgramPanic, Program
  File "bubblepy\tea.py", line 7, in <module>
    import termios
ModuleNotFoundError: No module named 'termios'
```

---

## Root Cause

`bubblepy/tea.py` unconditionally imports `termios` and `tty` at the module level (lines 7–8):

```python
import termios
import tty
```

Both modules are Unix-only and do not exist on Windows. There is a partial
`sys.platform != "win32"` guard at line 659, but the top-level imports fail
before any runtime check is reached.

---

## What Worked

- Git: available and working
- Python 3.14.3: installed and working (not on PATH at session start — needed full path to invoke)
- `bubblepy` and `pygloss`: cloned and installed via `pip install -e .` without errors
- `pygloss`: no import errors observed

---

## What Needs Fixing

`bubblepy/tea.py` needs platform-conditional imports. The `termios`/`tty`
references should be guarded, e.g.:

```python
import sys
if sys.platform != "win32":
    import termios
    import tty
else:
    # Windows alternative (msvcrt) or stub
    pass
```

All call sites in `tea.py` that use `termios.tcgetattr` / `termios.tcsetattr` /
`tty` will also need Windows equivalents (likely `msvcrt`-based).

---

## Next Step

This failure is the go/no-go gate for the cross-platform work described in:
`docs/superpowers/specs/2026-03-27-cross-platform-runtime-compat-design.md`

**Recommendation:** Implement the Windows terminal compatibility layer in
`bubblepy/tea.py` before proceeding with any other cross-platform changes.
