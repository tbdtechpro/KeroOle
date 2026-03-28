# Design: PyInstaller Packaging (Spec 2 of 2)

**Date:** 2026-03-27
**Scope:** Build a self-contained onedir executable for Windows, Linux, and macOS from a single `KeroOle.spec`. Each platform gets a dedicated build script. No CI pipeline — local builds only.

---

## Background

KeroOle currently requires a manually activated Python venv. This spec adds a build path that produces a standalone executable a user can run after cloning the repo without installing Python or any dependencies. `multiprocessing.freeze_support()` is already in place from the cross-platform runtime compat work.

---

## Output Layout (all platforms)

After a successful build the repo root contains:

```
KeroOle\                     ← repo root (wherever the user cloned)
  KeroOle.exe                ← Windows launcher  (or `KeroOle` on Linux/macOS)
  _internal\                 ← PyInstaller support files (DLLs, bundled Python, etc.)
  main.py                    ← source files remain alongside
  Books\                     ← download directory (runtime data, not bundled)
  cookies.json               ← generated at runtime (not bundled)
  …
```

`_internal/` is PyInstaller's default contents directory (PyInstaller ≥ 6). Users interact only with `KeroOle.exe` / `KeroOle`.

---

## Change 1: `kerole.py` — Frozen PATH Fix

`PATH` and `COOKIES_FILE` are defined at module level:

```python
PATH = os.path.dirname(os.path.realpath(__file__))
COOKIES_FILE = os.path.join(PATH, "cookies.json")
```

In a frozen onedir exe, `__file__` resolves inside `_internal/` — so `Books/` and `cookies.json` would be looked for there instead of alongside the exe.

**Fix** (one conditional, no behavioural change when running from source):

```python
import sys as _sys
if getattr(_sys, 'frozen', False):
    PATH = os.path.dirname(_sys.executable)
else:
    PATH = os.path.dirname(os.path.realpath(__file__))
```

`sys.executable` in a frozen exe always points to the launcher (`KeroOle.exe`), so `dirname` yields the repo root.

---

## Change 2: `KeroOle.spec`

Single spec file, checked into the repo root. Platform conditionals handle the differences.

```python
import sys

# ── Platform-specific hidden imports ───────────────────────────────────────
_hidden = [
    'lxml._elementpath',
    'lxml.etree',
    'lxml.html',
    'browser_cookie3',
    'pyperclip',
    'wcwidth',             # pygloss dependency
]

if sys.platform == 'win32':
    _hidden += ['keyring.backends.Windows']
elif sys.platform == 'darwin':
    _hidden += ['keyring.backends.macOS']
else:
    _hidden += ['keyring.backends.SecretService', 'keyring.backends.fail']

# ── Analysis ────────────────────────────────────────────────────────────────
a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[],           # Books/, cookies.json are runtime data — not bundled
    hiddenimports=_hidden,
    hookspath=[],
    excludes=['pytest', 'tkinter', '_tkinter'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KeroOle',
    console=True,        # TUI requires console window
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='KeroOle',
)
```

`datas=[]` — `Books/`, `cookies.json`, and user config are runtime files that live alongside the exe, not inside the bundle. No data files need to be embedded.

`upx=False` — UPX compression is optional and can cause false-positive antivirus hits on Windows. Disabled by default; can be enabled manually if distribution size is a concern.

---

## Change 3: Build Scripts

All three scripts follow the same logical flow:

```
1. Detect Python ≥ 3.10
     └── not found / too old → ask user confirmation → install
2. Create / reuse .build-venv
3. Install: pyinstaller, lxml, requests, browser_cookie3,
            pyperclip, colorama,
            bubblepy (git+https://github.com/tbdtechpro/bubblepy),
            pygloss  (git+https://github.com/tbdtechpro/pygloss)
4. Run PyInstaller: .build-venv python -m PyInstaller KeroOle.spec --distpath dist
5. Move output to repo root:
     dist/KeroOle/KeroOle[.exe]  →  ./KeroOle[.exe]
     dist/KeroOle/_internal/     →  ./_internal/
6. Clean up dist/ and build/
7. Ask: "Add KeroOle to PATH? [Y/N]"
     └── yes → add repo root to user PATH
```

### `build-windows.ps1`

- Python detection: `Get-Command python` + version check
- Python install: `winget install Python.Python.3 --silent` with user confirmation
- Venv: `.build-venv\Scripts\python.exe`
- PATH: write to `HKCU:\Environment` via registry, broadcast `WM_SETTINGCHANGE`

### `build-linux.sh`

- Python detection: `python3 --version`
- Python install: `sudo apt-get install python3 python3-venv python3-pip` (Debian/Ubuntu) with user confirmation; warns on non-Debian distros to install manually
- Venv: `.build-venv/bin/python`
- PATH: append `export PATH="$PWD:$PATH"` to `~/.bashrc` and `~/.profile`

### `build-macos.sh`

- Python detection: `python3 --version`
- Python install: `brew install python` with user confirmation; warns if Homebrew not present
- Venv: `.build-venv/bin/python`
- PATH: append `export PATH="$PWD:$PATH"` to `~/.zshrc` (macOS default shell)

All three scripts are idempotent — re-running skips steps already completed.

---

## Change 4: `.gitignore` Additions

```gitignore
# PyInstaller build output
KeroOle.exe
KeroOle
_internal/
dist/
build/

# Build venv
.build-venv/
```

`KeroOle.spec` is **not** gitignored — it is source, checked in alongside the scripts.

---

## Files Changed / Created

| File | Change |
|------|--------|
| `kerole.py` | Add frozen PATH check (2 lines) |
| `KeroOle.spec` | **New** — cross-platform PyInstaller spec |
| `build-windows.ps1` | **New** — Windows build script |
| `build-linux.sh` | **New** — Linux build script |
| `build-macos.sh` | **New** — macOS build script |
| `.gitignore` | Add build output entries |

---

## Testing

### Automated
- Existing `pytest tests/` must continue to pass (no regressions from `kerole.py` change)

### Manual (per platform)
| Scenario | Windows | Linux | macOS |
|----------|---------|-------|-------|
| Build script runs clean on fresh clone | verify | verify | verify |
| Build script is idempotent (re-run = no-op) | verify | verify | verify |
| `KeroOle[.exe]` exists at repo root after build | verify | verify | verify |
| TUI launches from exe | verify | verify | verify |
| `Books/` and `cookies.json` created at repo root (not in `_internal/`) | verify | verify | verify |
| Clipboard paste works | verify | n/a (existing) | verify |
| Calibre conversion works (if Calibre installed) | verify | n/a (existing) | verify |

---

## Non-Goals

- CI/CD pipeline (GitHub Actions, etc.)
- Code signing / notarisation
- Auto-update mechanism
- Installer wizard (NSIS, WiX, etc.)
- Single-file (`--onefile`) build
- UPX compression (disabled by default)
