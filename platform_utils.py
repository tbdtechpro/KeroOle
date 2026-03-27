"""Platform utilities for KeroOle — Calibre binary discovery."""

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

    Returns the full path if found, or bare ``name`` as fallback
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
    return name
