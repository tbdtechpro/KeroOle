# Windows App Test Findings — KeroOle Cross-Platform Verification

**Date:** 2026-03-27
**Python:** 3.14.3 (`C:\Users\MatthewPhelps\AppData\Local\Programs\Python\Python314\python.exe`)
**Windows build:** 11 IoT Enterprise LTSC 2024 (10.0.26100)
**KeroOle commit:** db05d32

---

## Summary

| Area | Result |
|---|---|
| App launches without errors | PASS |
| Main menu renders correctly | PASS |
| Colours appear | PASS |
| No garbled characters | PASS |
| Clipboard — cookie screen hint text | PASS (verified via source) |
| Clipboard — Ctrl+V wired up (cookie screen) | PASS (verified via source) |
| Clipboard — Ctrl+V wired up (add-book screen) | PASS (verified via source) |
| Clipboard — pyperclip paste called | PASS (verified via source) |
| Calibre binary discovery (Windows paths) | PASS (verified via source) |
| `colorama.just_fix_windows_console()` called | PASS |
| `multiprocessing.freeze_support()` called | PASS |

> **Note:** Clipboard Ctrl+V and screen navigation could not be exercised end-to-end
> through automated stdin piping — bubblepy reads keys directly from the terminal, not
> from piped stdin. Items marked "verified via source" are confirmed by code inspection
> rather than live interaction. Manual verification in Windows Terminal is recommended
> for the clipboard paste flow.

---

## TUI Rendering — PASS

App launched cleanly with no errors. Main menu output (raw ANSI):

```
╭────────────────────────────────────────────────────────────╮
│                                                            │
│    KeroOle                                                 │
│                                                            │
│    ○ Cookie: not set                                       │
│                                                            │
│    ▶ Extract Cookies from Browser                          │
│      Set Session Cookie (paste)                            │
│      Login with Email/Password                             │
│      Add Book to Queue                                     │
│      View / Run Queue / Export                             │
│        0 queued · library empty                            │
│      Sync with Calibre Library                             │
│      Export Paths / Settings                               │
│      Quit                                                  │
│                                                            │
│    ↑/↓  move    Enter  select    q  quit                   │
│                                                            │
╰────────────────────────────────────────────────────────────╯
```

- Purple/violet border (`#7C3AED` → ANSI 99) ✓
- Red/orange cookie status indicator (`○ Cookie: not set`) ✓
- Italic dimmed status line and footer ✓
- No garbled or missing box-drawing characters ✓

---

## Clipboard — Cookie Screen — PASS (source verified)

`main.py:1385-1390` — platform detection for the CLI hint is correct:

```python
if _sys.platform == "win32":
    _clip_cmd = "Get-Clipboard | python3 retrieve_cookies.py --stdin"
elif _sys.platform == "darwin":
    _clip_cmd = "pbpaste | python3 retrieve_cookies.py --stdin"
else:
    _clip_cmd = "xclip -o | python3 retrieve_cookies.py --stdin"
```

On this machine (`win32`) the hint will read:
`Get-Clipboard | python3 retrieve_cookies.py --stdin` ✓

Ctrl+V is wired at `main.py:824-825` → `_read_clipboard()` → `pyperclip.paste()` ✓

---

## Clipboard — Add Book Screen — PASS (source verified)

Ctrl+V wired at `main.py:845-846` → `_read_clipboard_book()` → shared
`_read_clipboard_impl()` → `pyperclip.paste()` ✓

---

## Calibre Binary Discovery — PASS (source verified)

`platform_utils.py` checks in order:
1. `shutil.which(name)` — PATH lookup
2. `C:\Program Files\Calibre2\<name>.exe`
3. `C:\Program Files (x86)\Calibre2\<name>.exe`

Calibre is not installed on this machine so live conversion could not be tested.

---

## Windows Console / ANSI — PASS

`main.py:1914-1918` calls `colorama.just_fix_windows_console()` on startup,
with fallback to `colorama.init(strip=False)`. ANSI colour sequences rendered
correctly in the observed output. ✓

---

## PyInstaller Compatibility — PASS (source verified)

`main.py:1934-1935` calls `multiprocessing.freeze_support()` at entry point. ✓

---

## Recommended Manual Follow-up

The following items need hands-on Windows Terminal testing to fully close out:

1. **Ctrl+V paste on cookie screen** — copy a real cookie string, press Ctrl+V,
   confirm text appears in the input field and status reads `ok: N chars read from clipboard`.
2. **Ctrl+V paste on add-book screen** — copy a URL or book ID, press Ctrl+V,
   confirm it pastes into the field.
3. **Calibre conversion** — requires Calibre installation; download a book and
   confirm ANSI colours appear in the log output.
