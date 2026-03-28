"""
config.py — User-level configuration for KeroOle.

Config file: ~/.kerole.toml

Example:
    [exports]
    markdown_dir      = "~/Documents/Books/markdown"
    rag_dir           = "~/Documents/Books/rag"
    db_path           = "~/Documents/Books/library.db"
    folder_name_style = "title"   # "title" or "id"

All paths support ~ expansion.  If a key is absent, the default behaviour
(paths relative to each book's directory inside Books/) is used.
"""

import hashlib
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path.home() / ".kerole.toml"

FOLDER_NAME_STYLES = ("title", "id")


@dataclass
class ExportConfig:
    """Resolved export-path configuration."""
    # If empty string, fall back to the per-book default inside Books/
    markdown_dir: str      = ""
    rag_dir: str           = ""
    db_path: str           = ""
    # "title" → sanitized book title;  "id" → numeric book ID
    folder_name_style: str = "title"
    # Dual markdown flavor export (Phase 1B)
    markdown_gfm: bool          = False
    markdown_gfm_dir: str       = ""   # "" = Books/{title}/markdown/
    markdown_obsidian: bool      = False
    markdown_obsidian_dir: str   = ""   # "" = same default; set to vault path
    # After successful Calibre conversion, delete the original pre-conversion EPUB
    delete_original_epub: bool   = False

    def resolved_markdown_dir(self) -> str:
        """Absolute path for the markdown output base dir, or '' for default."""
        return str(Path(self.markdown_dir).expanduser()) if self.markdown_dir else ""

    def resolved_rag_dir(self) -> str:
        """Absolute path for the RAG JSONL output dir, or '' for default."""
        return str(Path(self.rag_dir).expanduser()) if self.rag_dir else ""

    def resolved_db_path(self) -> str:
        """Absolute path for library.db, or '' for default."""
        return str(Path(self.db_path).expanduser()) if self.db_path else ""

    def resolved_markdown_gfm_dir(self) -> str:
        return str(Path(self.markdown_gfm_dir).expanduser()) if self.markdown_gfm_dir else ""

    def resolved_markdown_obsidian_dir(self) -> str:
        return str(Path(self.markdown_obsidian_dir).expanduser()) if self.markdown_obsidian_dir else ""


@dataclass
class MenuConfig:
    """Visibility toggles for main menu items (Phase 2A)."""
    show_browser_cookie: bool  = True
    show_manual_cookie: bool   = True
    show_email_login: bool     = False   # hidden by default — non-functional
    show_calibre_sync: bool    = True
    show_search: bool          = True
    show_library_browse: bool  = True


# ---------------------------------------------------------------------------
# Folder-name helpers
# ---------------------------------------------------------------------------

def sanitize_folder_name(name: str, max_len: int = 80) -> str:
    """Return a filesystem-safe version of name.

    Replaces characters invalid on Windows/Linux/macOS, collapses whitespace,
    strips leading/trailing dots, and truncates to max_len.
    """
    name = re.sub(r'[/\\:*?"<>|]', '-', name)   # forbidden chars → dash
    name = re.sub(r'\s+', ' ', name).strip()      # collapse whitespace
    name = name.strip('.')                         # no leading/trailing dots
    return name[:max_len] if name else "unknown"


def book_folder_name(book_info: dict, book_id: str, style: str = "title") -> str:
    """Return the folder/filename stem to use for a book's export output.

    style="title" → sanitized book title (falls back to book_id if title missing)
    style="id"    → numeric book_id as-is
    """
    if style == "id":
        return book_id
    title = (book_info.get("title") or "").strip()
    if not title:
        return book_id
    return sanitize_folder_name(title)


# ---------------------------------------------------------------------------
# Load / save
# ---------------------------------------------------------------------------

def _load_toml() -> dict:
    """Load ~/.kerole.toml, returning empty dict if missing or unreadable."""
    if not CONFIG_PATH.exists():
        return {}
    try:
        with open(CONFIG_PATH, "rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError:
        return {}


def load_export_config() -> ExportConfig:
    """Load [exports] section from ~/.kerole.toml."""
    data = _load_toml()
    e = data.get("exports", {})
    raw_style = e.get("folder_name_style", "title")
    return ExportConfig(
        markdown_dir=e.get("markdown_dir", ""),
        rag_dir=e.get("rag_dir", ""),
        db_path=e.get("db_path", ""),
        folder_name_style=raw_style if raw_style in FOLDER_NAME_STYLES else "title",
        markdown_gfm=bool(e.get("markdown_gfm", False)),
        markdown_gfm_dir=e.get("markdown_gfm_dir", ""),
        markdown_obsidian=bool(e.get("markdown_obsidian", False)),
        markdown_obsidian_dir=e.get("markdown_obsidian_dir", ""),
        delete_original_epub=bool(e.get("delete_original_epub", False)),
    )


def load_menu_config() -> MenuConfig:
    """Load [menu] section from ~/.kerole.toml."""
    data = _load_toml()
    m = data.get("menu", {})
    return MenuConfig(
        show_browser_cookie=bool(m.get("show_browser_cookie", True)),
        show_manual_cookie=bool(m.get("show_manual_cookie", True)),
        show_email_login=bool(m.get("show_email_login", False)),
        show_calibre_sync=bool(m.get("show_calibre_sync", True)),
        show_search=bool(m.get("show_search", True)),
        show_library_browse=bool(m.get("show_library_browse", True)),
    )


def save_export_config(cfg: ExportConfig) -> None:
    """Write [exports] section back to ~/.kerole.toml.

    Preserves any other sections already present in the file.
    """
    existing = _load_toml()
    existing["exports"] = {
        "markdown_dir":           cfg.markdown_dir,
        "rag_dir":                cfg.rag_dir,
        "db_path":                cfg.db_path,
        "folder_name_style":      cfg.folder_name_style
                                  if cfg.folder_name_style in FOLDER_NAME_STYLES
                                  else "title",
        "markdown_gfm":           cfg.markdown_gfm,
        "markdown_gfm_dir":       cfg.markdown_gfm_dir,
        "markdown_obsidian":      cfg.markdown_obsidian,
        "markdown_obsidian_dir":  cfg.markdown_obsidian_dir,
        "delete_original_epub":   cfg.delete_original_epub,
    }
    _write_toml(existing)


def save_menu_config(cfg: MenuConfig) -> None:
    """Write [menu] section back to ~/.kerole.toml."""
    existing = _load_toml()
    existing["menu"] = {
        "show_browser_cookie":  cfg.show_browser_cookie,
        "show_manual_cookie":   cfg.show_manual_cookie,
        "show_email_login":     cfg.show_email_login,
        "show_calibre_sync":    cfg.show_calibre_sync,
        "show_search":          cfg.show_search,
        "show_library_browse":  cfg.show_library_browse,
    }
    _write_toml(existing)


def _write_toml(data: dict) -> None:
    """Serialize a flat dict-of-dicts to TOML and write to CONFIG_PATH."""
    lines = []
    for section, values in data.items():
        lines.append(f"[{section}]")
        for key, val in values.items():
            if isinstance(val, bool):
                lines.append(f"{key} = {'true' if val else 'false'}")
            else:
                escaped = str(val).replace("\\", "\\\\").replace('"', '\\"')
                lines.append(f'{key} = "{escaped}"')
        lines.append("")
    CONFIG_PATH.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Cheat code system
# ---------------------------------------------------------------------------

# Mapping of SHA-256(code) → effect name.
# Codes are intentionally not stored in plain text.
# Effects: "ascii_variant_N" changes the main menu ASCII art;
#          "show_email_login" reveals the hidden menu item;
#          "export_obsidian" auto-enables Obsidian export.
_CHEAT_HASHES: dict[str, str] = {
    "c1f1a893cb408d864faf89fa45eb2ccbe8587d20109e8b6a1e6b6f9ff5354156": "ascii_variant_1",
    "1b91bae778a467b0b9682a9903a896326af3eb0e4421398a844f45ce5645fde4": "ascii_variant_2",
    "c72c74af99ca16fd11be080633d398d89e997c823a45493a0a1963d8ec3f0a9a": "show_email_login",
    "7dc234b30beafd3ea7add0694aa5770f4ad7feb4ed3e1d42cf694efbcc5bda2e": "export_obsidian",
}

# Human-readable descriptions shown in the Settings unlock list
_CHEAT_DESCRIPTIONS: dict[str, str] = {
    "ascii_variant_1": "ASCII art variant: block letters",
    "ascii_variant_2": "ASCII art variant: minimal dots",
    "show_email_login": "Reveal email/password login in main menu",
    "export_obsidian": "Auto-enable Obsidian export on every download",
}


def check_cheat_code(code: str) -> str | None:
    """Return the effect name if *code* is a valid cheat code, else None."""
    h = hashlib.sha256(code.strip().upper().encode()).hexdigest()
    return _CHEAT_HASHES.get(h)


def load_unlocked_cheats() -> set[str]:
    """Return the set of currently unlocked cheat effect names."""
    data = _load_toml()
    raw = data.get("cheats", {}).get("unlocked", "")
    if not raw:
        return set()
    return {e.strip() for e in raw.split(",") if e.strip()}


def save_unlocked_cheats(effects: set[str]) -> None:
    """Persist the unlocked cheat effects to ~/.kerole.toml."""
    existing = _load_toml()
    existing.setdefault("cheats", {})["unlocked"] = ",".join(sorted(effects))
    _write_toml(existing)


def unlock_cheat(code: str) -> tuple[bool, str]:
    """Try to unlock a cheat code.  Returns (already_had, effect_name) or raises ValueError."""
    effect = check_cheat_code(code)
    if effect is None:
        raise ValueError("Unknown cheat code")
    unlocked = load_unlocked_cheats()
    already = effect in unlocked
    unlocked.add(effect)
    save_unlocked_cheats(unlocked)
    return already, effect


def cheat_description(effect: str) -> str:
    return _CHEAT_DESCRIPTIONS.get(effect, effect)
