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
