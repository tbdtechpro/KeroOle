# PyInstaller Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cross-platform PyInstaller build system that produces a onedir executable at the repo root from a single `KeroOle.spec`, with dedicated build scripts for Windows, Linux, and macOS.

**Architecture:** A shared `KeroOle.spec` (with `sys.platform` conditionals) drives all builds. Three platform-specific scripts handle Python detection/install, a `.build-venv/` for PyInstaller, the build itself, and post-build output relocation to the repo root. `kerole.py` gets a two-line frozen PATH fix so `Books/` and `cookies.json` resolve relative to the exe, not `_internal/`.

**Tech Stack:** PyInstaller ≥ 6, Python 3.10+, PowerShell 5+ (Windows), Bash (Linux/macOS), winget (Windows Python install), apt (Linux), Homebrew (macOS)

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `kerole.py` | Modify line 25 | Frozen PATH fix — use `sys.executable` dir when frozen |
| `KeroOle.spec` | Create | Cross-platform PyInstaller spec |
| `build-windows.ps1` | Create | Windows build script |
| `build-linux.sh` | Create | Linux build script |
| `build-macos.sh` | Create | macOS build script |
| `.gitignore` | Modify | Ignore build outputs |
| `tests/test_frozen_path.py` | Create | Test for frozen PATH fix |

---

## Task 1: Frozen PATH fix in `kerole.py`

**Files:**
- Modify: `kerole.py:25`
- Create: `tests/test_frozen_path.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_frozen_path.py`:

```python
"""Tests for kerole.py frozen-exe PATH resolution."""
import importlib
import os
import sys
import pytest


def test_frozen_path_uses_executable_directory(monkeypatch, tmp_path):
    """When sys.frozen is True, PATH must be the directory containing the exe."""
    fake_exe = str(tmp_path / "KeroOle.exe")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", fake_exe)

    import kerole
    importlib.reload(kerole)

    assert kerole.PATH == str(tmp_path)
    assert kerole.COOKIES_FILE == str(tmp_path / "cookies.json")


def test_unfrozen_path_uses_source_directory():
    """When not frozen, PATH must be the directory containing kerole.py."""
    import kerole
    importlib.reload(kerole)

    expected = os.path.dirname(os.path.realpath(kerole.__file__))
    assert kerole.PATH == expected
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /path/to/KeroOle
source .venv/bin/activate
pytest tests/test_frozen_path.py -v
```

Expected: `test_frozen_path_uses_executable_directory` FAILS — `kerole.PATH` resolves to `_internal/` equivalent, not `tmp_path`.

- [ ] **Step 3: Apply the frozen PATH fix**

In `kerole.py`, replace line 25:

```python
# Before
PATH = os.path.dirname(os.path.realpath(__file__))
```

With:

```python
# After  (sys is already imported at line 4)
if getattr(sys, "frozen", False):
    PATH = os.path.dirname(sys.executable)
else:
    PATH = os.path.dirname(os.path.realpath(__file__))
```

`COOKIES_FILE` on line 26 is unchanged — it already uses `PATH`.

- [ ] **Step 4: Run tests to verify both pass**

```bash
pytest tests/test_frozen_path.py -v
```

Expected output:
```
tests/test_frozen_path.py::test_frozen_path_uses_executable_directory PASSED
tests/test_frozen_path.py::test_unfrozen_path_uses_source_directory PASSED
```

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
pytest tests/ -q
```

Expected: all 51 existing tests + 2 new = 53 passed.

- [ ] **Step 6: Commit**

```bash
git add kerole.py tests/test_frozen_path.py
git commit -m "fix: resolve PATH from sys.executable when running as frozen exe"
```

---

## Task 2: `.gitignore` additions

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Add build output entries**

Append to `.gitignore`:

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

- [ ] **Step 2: Verify spec file is NOT ignored**

```bash
git check-ignore -v KeroOle.spec
```

Expected: no output (not ignored).

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore PyInstaller build output and build venv"
```

---

## Task 3: `KeroOle.spec`

**Files:**
- Create: `KeroOle.spec`

- [ ] **Step 1: Create the spec file**

Create `KeroOle.spec` in the repo root:

```python
# KeroOle.spec — PyInstaller build spec (Windows, Linux, macOS)
import sys

# ── Platform-specific hidden imports ─────────────────────────────────────────
_hidden = [
    "lxml._elementpath",
    "lxml.etree",
    "lxml.html",
    "browser_cookie3",
    "pyperclip",
    "wcwidth",             # pygloss dependency
]

if sys.platform == "win32":
    _hidden += ["keyring.backends.Windows"]
elif sys.platform == "darwin":
    _hidden += ["keyring.backends.macOS"]
else:
    _hidden += ["keyring.backends.SecretService", "keyring.backends.fail"]

# ── Analysis ──────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[],
    hiddenimports=_hidden,
    hookspath=[],
    excludes=["pytest", "tkinter", "_tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="KeroOle",
    console=True,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="KeroOle",
)
```

- [ ] **Step 2: Verify spec is valid Python syntax**

```bash
python3 -c "compile(open('KeroOle.spec').read(), 'KeroOle.spec', 'exec'); print('syntax OK')"
```

Expected: `syntax OK`

- [ ] **Step 3: Commit**

```bash
git add KeroOle.spec
git commit -m "feat: add cross-platform PyInstaller spec"
```

---

## Task 4: `build-windows.ps1`

**Files:**
- Create: `build-windows.ps1`

- [ ] **Step 1: Create the script**

Create `build-windows.ps1` in the repo root:

```powershell
#Requires -Version 5.0
<#
.SYNOPSIS
    Builds the KeroOle Windows executable using PyInstaller.
    Run from the repo root in PowerShell:  .\build-windows.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Write-Step { param($msg) Write-Host "[*] $msg" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "[+] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }

# ── 1. Detect Python ≥ 3.10 ──────────────────────────────────────────────────
Write-Step "Checking for Python..."
$pythonCmd = $null
$minVersion = [version]"3.10"

foreach ($cmd in @("python", "python3")) {
    try {
        $ver = & $cmd --version 2>&1
        if ($ver -match "Python (\d+\.\d+)") {
            if ([version]$Matches[1] -ge $minVersion) {
                $pythonCmd = $cmd
                Write-Ok "Found: $ver"
                break
            }
        }
    } catch { }
}

if (-not $pythonCmd) {
    Write-Warn "Python $minVersion+ not found."
    $install = Read-Host "Install Python 3.13 via winget? [Y/N]"
    if ($install -notin @("Y","y")) {
        Write-Host "Aborting. Install Python manually: https://python.org" -ForegroundColor Red
        exit 1
    }
    Write-Step "Installing Python via winget..."
    winget install Python.Python.3.13 --silent --accept-package-agreements --accept-source-agreements
    # Refresh PATH in this session
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path","User")
    $pythonCmd = "python"
    Write-Ok "Python installed."
}

# ── 2. Create / reuse .build-venv ─────────────────────────────────────────────
$venvDir    = Join-Path $ScriptDir ".build-venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Step "Creating build venv at .build-venv..."
    & $pythonCmd -m venv $venvDir
    Write-Ok "Venv created."
} else {
    Write-Step "Reusing existing .build-venv."
}

# ── 3. Install dependencies ────────────────────────────────────────────────────
Write-Step "Installing dependencies into build venv..."
& $venvPython -m pip install --quiet --upgrade pip
& $venvPython -m pip install --quiet `
    pyinstaller `
    "lxml>=4.9.0" `
    "requests>=2.28.0" `
    browser_cookie3 `
    "pyperclip>=1.8.0" `
    "colorama>=0.4.6" `
    "git+https://github.com/tbdtechpro/bubblepy" `
    "git+https://github.com/tbdtechpro/pygloss"
Write-Ok "Dependencies installed."

# ── 4. Run PyInstaller ────────────────────────────────────────────────────────
Write-Step "Building with PyInstaller..."
Set-Location $ScriptDir
& $venvPython -m PyInstaller KeroOle.spec --distpath dist --noconfirm
Write-Ok "Build complete."

# ── 5. Move output to repo root ───────────────────────────────────────────────
Write-Step "Moving output to repo root..."

$exeSrc = Join-Path $ScriptDir "dist\KeroOle\KeroOle.exe"
$exeDst = Join-Path $ScriptDir "KeroOle.exe"
$intSrc = Join-Path $ScriptDir "dist\KeroOle\_internal"
$intDst = Join-Path $ScriptDir "_internal"

if (Test-Path $exeDst) { Remove-Item $exeDst -Force }
if (Test-Path $intDst) { Remove-Item $intDst -Recurse -Force }

Move-Item $exeSrc $exeDst
Move-Item $intSrc $intDst
Write-Ok "Moved KeroOle.exe and _internal\ to repo root."

# ── 6. Clean up ───────────────────────────────────────────────────────────────
Write-Step "Cleaning up..."
Remove-Item (Join-Path $ScriptDir "dist")  -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $ScriptDir "build") -Recurse -Force -ErrorAction SilentlyContinue
Write-Ok "Cleaned up dist\ and build\."

# ── 7. Optional PATH addition ─────────────────────────────────────────────────
$addPath = Read-Host "Add KeroOle to your user PATH? [Y/N]"
if ($addPath -in @("Y","y")) {
    $currentPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
    if ($currentPath -notlike "*$ScriptDir*") {
        [System.Environment]::SetEnvironmentVariable("Path", "$currentPath;$ScriptDir", "User")

        # Broadcast WM_SETTINGCHANGE so open terminals pick up the new PATH
        $sig = '[DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern IntPtr SendMessageTimeout(IntPtr hWnd, uint Msg, UIntPtr wParam, string lParam, uint fuFlags, uint uTimeout, out UIntPtr lpdwResult);'
        $type = Add-Type -MemberDefinition $sig -Name WinMsg -Namespace Win32 -PassThru
        $result = [UIntPtr]::Zero
        $type::SendMessageTimeout([IntPtr]0xffff, 0x1a, [UIntPtr]::Zero, "Environment", 2, 5000, [ref]$result) | Out-Null

        Write-Ok "Added to PATH. Restart your terminal to use 'KeroOle' from anywhere."
    } else {
        Write-Ok "Already in PATH — no change needed."
    }
}

Write-Host ""
Write-Ok "Done!  Run .\KeroOle.exe to launch KeroOle."
```

- [ ] **Step 2: Commit**

```bash
git add build-windows.ps1
git commit -m "feat: add Windows PyInstaller build script"
```

---

## Task 5: `build-linux.sh`

**Files:**
- Create: `build-linux.sh`

- [ ] **Step 1: Create the script**

Create `build-linux.sh` in the repo root:

```bash
#!/usr/bin/env bash
# build-linux.sh — Builds the KeroOle Linux executable using PyInstaller.
# Run from the repo root:  bash build-linux.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIN_MINOR=10

info() { echo "[*] $*"; }
ok()   { echo "[+] $*"; }
warn() { echo "[!] $*"; }
die()  { echo "[✗] $*" >&2; exit 1; }

# ── 1. Detect Python ≥ 3.10 ───────────────────────────────────────────────────
info "Checking for Python..."
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        major=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo 0)
        minor=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
        if [[ "$major" -ge 3 && "$minor" -ge "$MIN_MINOR" ]]; then
            PYTHON_CMD="$cmd"
            ok "Found: $("$cmd" --version)"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    warn "Python 3.$MIN_MINOR+ not found."
    read -rp "Install Python via apt? [Y/N] " install
    if [[ "$install" != "Y" && "$install" != "y" ]]; then
        die "Aborting. Install Python manually: https://python.org"
    fi
    if command -v apt-get &>/dev/null; then
        sudo apt-get install -y python3 python3-venv python3-pip
        PYTHON_CMD="python3"
        ok "Python installed."
    else
        die "Non-Debian distro detected. Install Python 3.$MIN_MINOR+ manually, then re-run."
    fi
fi

# ── 2. Create / reuse .build-venv ─────────────────────────────────────────────
VENV_DIR="$SCRIPT_DIR/.build-venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    info "Creating build venv at .build-venv..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    ok "Venv created."
else
    info "Reusing existing .build-venv."
fi

# ── 3. Install dependencies ────────────────────────────────────────────────────
info "Installing dependencies into build venv..."
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
"$VENV_PYTHON" -m pip install --quiet \
    pyinstaller \
    "lxml>=4.9.0" \
    "requests>=2.28.0" \
    browser_cookie3 \
    "pyperclip>=1.8.0" \
    "colorama>=0.4.6" \
    "git+https://github.com/tbdtechpro/bubblepy" \
    "git+https://github.com/tbdtechpro/pygloss"
ok "Dependencies installed."

# ── 4. Run PyInstaller ────────────────────────────────────────────────────────
info "Building with PyInstaller..."
cd "$SCRIPT_DIR"
"$VENV_PYTHON" -m PyInstaller KeroOle.spec --distpath dist --noconfirm
ok "Build complete."

# ── 5. Move output to repo root ───────────────────────────────────────────────
info "Moving output to repo root..."
rm -f "$SCRIPT_DIR/KeroOle"
rm -rf "$SCRIPT_DIR/_internal"
mv "$SCRIPT_DIR/dist/KeroOle/KeroOle" "$SCRIPT_DIR/KeroOle"
mv "$SCRIPT_DIR/dist/KeroOle/_internal" "$SCRIPT_DIR/_internal"
chmod +x "$SCRIPT_DIR/KeroOle"
ok "Moved KeroOle and _internal/ to repo root."

# ── 6. Clean up ───────────────────────────────────────────────────────────────
info "Cleaning up..."
rm -rf "$SCRIPT_DIR/dist" "$SCRIPT_DIR/build"
ok "Cleaned up dist/ and build/."

# ── 7. Optional PATH addition ─────────────────────────────────────────────────
read -rp "Add KeroOle to your PATH? [Y/N] " add_path
if [[ "$add_path" == "Y" || "$add_path" == "y" ]]; then
    EXPORT_LINE="export PATH=\"$SCRIPT_DIR:\$PATH\"  # KeroOle"
    added=0
    for rc in "$HOME/.bashrc" "$HOME/.profile"; do
        if [[ -f "$rc" ]] && ! grep -qF "$SCRIPT_DIR" "$rc" 2>/dev/null; then
            printf '\n%s\n' "$EXPORT_LINE" >> "$rc"
            ok "Added to $rc"
            added=1
        fi
    done
    [[ $added -eq 0 ]] && ok "Already in PATH — no change needed."
    ok "Restart your terminal or run: export PATH=\"$SCRIPT_DIR:\$PATH\""
fi

echo ""
ok "Done!  Run ./KeroOle to launch KeroOle."
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x build-linux.sh
git add build-linux.sh
git commit -m "feat: add Linux PyInstaller build script"
```

---

## Task 6: `build-macos.sh`

**Files:**
- Create: `build-macos.sh`

- [ ] **Step 1: Create the script**

Create `build-macos.sh` in the repo root:

```bash
#!/usr/bin/env bash
# build-macos.sh — Builds the KeroOle macOS executable using PyInstaller.
# Run from the repo root:  bash build-macos.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIN_MINOR=10

info() { echo "[*] $*"; }
ok()   { echo "[+] $*"; }
warn() { echo "[!] $*"; }
die()  { echo "[✗] $*" >&2; exit 1; }

# ── 1. Detect Python ≥ 3.10 ───────────────────────────────────────────────────
info "Checking for Python..."
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        major=$("$cmd" -c "import sys; print(sys.version_info.major)" 2>/dev/null || echo 0)
        minor=$("$cmd" -c "import sys; print(sys.version_info.minor)" 2>/dev/null || echo 0)
        if [[ "$major" -ge 3 && "$minor" -ge "$MIN_MINOR" ]]; then
            PYTHON_CMD="$cmd"
            ok "Found: $("$cmd" --version)"
            break
        fi
    fi
done

if [[ -z "$PYTHON_CMD" ]]; then
    warn "Python 3.$MIN_MINOR+ not found."
    read -rp "Install Python via Homebrew? [Y/N] " install
    if [[ "$install" != "Y" && "$install" != "y" ]]; then
        die "Aborting. Install Python manually: https://python.org"
    fi
    if command -v brew &>/dev/null; then
        brew install python
        PYTHON_CMD="python3"
        ok "Python installed."
    else
        die "Homebrew not found. Install it from https://brew.sh, then re-run."
    fi
fi

# ── 2. Create / reuse .build-venv ─────────────────────────────────────────────
VENV_DIR="$SCRIPT_DIR/.build-venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    info "Creating build venv at .build-venv..."
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    ok "Venv created."
else
    info "Reusing existing .build-venv."
fi

# ── 3. Install dependencies ────────────────────────────────────────────────────
info "Installing dependencies into build venv..."
"$VENV_PYTHON" -m pip install --quiet --upgrade pip
"$VENV_PYTHON" -m pip install --quiet \
    pyinstaller \
    "lxml>=4.9.0" \
    "requests>=2.28.0" \
    browser_cookie3 \
    "pyperclip>=1.8.0" \
    "colorama>=0.4.6" \
    "git+https://github.com/tbdtechpro/bubblepy" \
    "git+https://github.com/tbdtechpro/pygloss"
ok "Dependencies installed."

# ── 4. Run PyInstaller ────────────────────────────────────────────────────────
info "Building with PyInstaller..."
cd "$SCRIPT_DIR"
"$VENV_PYTHON" -m PyInstaller KeroOle.spec --distpath dist --noconfirm
ok "Build complete."

# ── 5. Move output to repo root ───────────────────────────────────────────────
info "Moving output to repo root..."
rm -f "$SCRIPT_DIR/KeroOle"
rm -rf "$SCRIPT_DIR/_internal"
mv "$SCRIPT_DIR/dist/KeroOle/KeroOle" "$SCRIPT_DIR/KeroOle"
mv "$SCRIPT_DIR/dist/KeroOle/_internal" "$SCRIPT_DIR/_internal"
chmod +x "$SCRIPT_DIR/KeroOle"
ok "Moved KeroOle and _internal/ to repo root."

# ── 6. Clean up ───────────────────────────────────────────────────────────────
info "Cleaning up..."
rm -rf "$SCRIPT_DIR/dist" "$SCRIPT_DIR/build"
ok "Cleaned up dist/ and build/."

# ── 7. Optional PATH addition ─────────────────────────────────────────────────
read -rp "Add KeroOle to your PATH? [Y/N] " add_path
if [[ "$add_path" == "Y" || "$add_path" == "y" ]]; then
    EXPORT_LINE="export PATH=\"$SCRIPT_DIR:\$PATH\"  # KeroOle"
    ZSHRC="$HOME/.zshrc"
    if [[ -f "$ZSHRC" ]] && ! grep -qF "$SCRIPT_DIR" "$ZSHRC" 2>/dev/null; then
        printf '\n%s\n' "$EXPORT_LINE" >> "$ZSHRC"
        ok "Added to ~/.zshrc"
    else
        ok "Already in PATH — no change needed."
    fi
    ok "Restart your terminal or run: export PATH=\"$SCRIPT_DIR:\$PATH\""
fi

echo ""
ok "Done!  Run ./KeroOle to launch KeroOle."
```

- [ ] **Step 2: Make executable and commit**

```bash
chmod +x build-macos.sh
git add build-macos.sh
git commit -m "feat: add macOS PyInstaller build script"
```

---

## Task 7: Push and smoke-test on Windows

- [ ] **Step 1: Push all commits**

```bash
git push origin master
```

- [ ] **Step 2: On the Windows VM — pull and run the build script**

In Windows Terminal (PowerShell):

```powershell
cd KeroOle
git pull
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build-windows.ps1
```

- [ ] **Step 3: Verify output layout**

```powershell
Test-Path KeroOle.exe       # must be True
Test-Path _internal\        # must be True
Test-Path dist\             # must be False (cleaned up)
Test-Path build\            # must be False (cleaned up)
```

- [ ] **Step 4: Launch the exe**

```powershell
.\KeroOle.exe
```

Expected: TUI launches, borders render, colours appear.

- [ ] **Step 5: Verify Books/ and cookies.json create at repo root**

Navigate to any screen that writes a cookie or starts a download. Confirm files appear at `C:\...\KeroOle\cookies.json` and `C:\...\KeroOle\Books\`, NOT inside `_internal\`.

- [ ] **Step 6: Re-run build script to verify idempotency**

```powershell
.\build-windows.ps1
```

Expected: script completes without error, existing `.build-venv\` is reused (no reinstall).
