# KeroOle VHS Demo Tapes

These [VHS](https://github.com/charmbracelet/vhs) tape files produce the demo GIFs used in the README.

## Prerequisites

Install VHS (requires Go):

```bash
# Linux (Homebrew or direct)
brew install vhs
# or
go install github.com/charmbracelet/vhs@latest

# Also requires ttyd and ffmpeg
sudo apt-get install ttyd ffmpeg
```

## Tapes

| File | Output | What it shows |
|---|---|---|
| `01-main-menu.tape` | `01-main-menu.gif` | App launch and main menu navigation |
| `02-cookie-auth.tape` | `02-cookie-auth.gif` | Pasting a session cookie via the TUI |
| `03-search.tape` | `03-search.gif` | Searching O'Reilly and adding to queue |
| `04-download.tape` | `04-download.gif` | Running a queue download with export options |
| `05-library-browse.tape` | `05-library-browse.gif` | Library Browse screen with status badges |
| `06-settings.tape` | `06-settings.gif` | Export path configuration |

## Recording

```bash
cd KeroOle/
vhs tapes/01-main-menu.tape
```

All GIFs are written to `tapes/output/`.

## Notes

- Tapes use a pre-populated `cookies.json` for demos that require auth. Replace with your own.
- Download demos use a short, fast-to-download book (e.g. `9780596007836` — a short O'Reilly report).
- Terminal dimensions are set to 100×30 for all tapes to ensure consistent rendering.
- Font: any monospace works; demos were recorded with JetBrains Mono Nerd Font.
