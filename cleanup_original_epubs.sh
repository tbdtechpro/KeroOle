#!/usr/bin/env bash
# cleanup_original_epubs.sh — Delete original EPUBs where a _calibre.epub already exists.
#
# Usage:
#   ./cleanup_original_epubs.sh [--dry-run] [BOOKS_DIR]
#
# Arguments:
#   --dry-run   Print what would be deleted without actually deleting anything.
#   BOOKS_DIR   Path to the Books directory. Defaults to ./Books if not provided.
#
# A file is deleted only when BOTH conditions are true:
#   1. The file does NOT end in _calibre.epub  (it's the original)
#   2. A sibling _calibre.epub file exists     (conversion succeeded)
#
# Example:
#   ./cleanup_original_epubs.sh --dry-run
#   ./cleanup_original_epubs.sh
#   ./cleanup_original_epubs.sh ~/Documents/Books

set -euo pipefail

DRY_RUN=false
BOOKS_DIR=""

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        *)         BOOKS_DIR="$arg" ;;
    esac
done

BOOKS_DIR="${BOOKS_DIR:-./Books}"

if [[ ! -d "$BOOKS_DIR" ]]; then
    echo "Error: Books directory not found: $BOOKS_DIR" >&2
    exit 1
fi

deleted=0
skipped=0

while IFS= read -r -d '' epub; do
    stem="${epub%.epub}"
    calibre="${stem}_calibre.epub"

    if [[ -f "$calibre" ]]; then
        if $DRY_RUN; then
            echo "[dry-run] Would delete: $epub"
        else
            rm "$epub"
            echo "Deleted: $epub"
        fi
        ((deleted++)) || true
    else
        ((skipped++)) || true
    fi
done < <(find "$BOOKS_DIR" -name "*.epub" ! -name "*_calibre.epub" -print0)

echo ""
if $DRY_RUN; then
    echo "Dry run complete. Would delete: $deleted  |  No _calibre.epub found (kept): $skipped"
else
    echo "Done. Deleted: $deleted  |  No _calibre.epub found (kept): $skipped"
fi
