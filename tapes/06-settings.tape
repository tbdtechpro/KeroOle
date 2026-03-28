# 06-settings.tape — Demonstrate the Settings / Export Paths screen
# Records: open Settings → configure Obsidian vault path → toggle delete_original → save

Output tapes/output/06-settings.gif

Require python3

Set Shell "bash"
Set FontSize 14
Set Width 900
Set Height 540
Set Theme "Catppuccin Mocha"
Set Framerate 24
Set PlaybackSpeed 0.8

Type "source .venv/bin/activate 2>/dev/null; python main.py"
Enter
Sleep 2s

# Navigate to "Export Paths / Settings" — second from last item
# Go down to it (item 8)
Down
Sleep 200ms
Down
Sleep 200ms
Down
Sleep 200ms
Down
Sleep 200ms
Down
Sleep 200ms
Down
Sleep 200ms
Down
Sleep 200ms
Down
Sleep 200ms
Enter
Sleep 1s

# Settings screen — we're on field 0 (GFM Markdown dir)
# Tab to Obsidian vault dir (field index 5 — tab 5 times)
Tab
Sleep 300ms
Tab
Sleep 300ms
Tab
Sleep 300ms
Tab
Sleep 300ms
Tab
Sleep 300ms

# Type an Obsidian vault path
Type "~/Documents/ObsidianVault"
Sleep 500ms
Enter
Sleep 800ms

# Tab to the delete_original toggle (index 6)
Tab
Sleep 400ms

# Toggle it on
Space
Sleep 600ms

# Tab to Scan Library button and press it
Tab
Sleep 300ms
Enter
Sleep 3s

# Done — back out
Escape
Sleep 500ms
Ctrl+C
Sleep 500ms
