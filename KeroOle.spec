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
