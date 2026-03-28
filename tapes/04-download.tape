# 04-download.tape — Demonstrate adding a book to queue and downloading
# Records: Add Book → enter ID → go to queue → toggle exports → run

Output tapes/output/04-download.gif

Require python3

Set Shell "bash"
Set FontSize 14
Set Width 900
Set Height 540
Set Theme "Catppuccin Mocha"
Set Framerate 24
Set PlaybackSpeed 0.8

# Assumes cookies.json already populated
Type "source .venv/bin/activate 2>/dev/null; python main.py"
Enter
Sleep 2s

# Navigate to "Add Book to Queue" (item 5 — down 4 times)
Down
Sleep 200ms
Down
Sleep 200ms
Down
Sleep 200ms
Down
Sleep 200ms
Enter
Sleep 800ms

# Enter a book ID — use a short book for demo
# 9780596007836 is "Ajax: The Definitive Guide" — relatively short
Type "9780596007836"
Enter
Sleep 800ms

# Go to queue screen (Escape takes us back to menu, then navigate to View / Run Queue)
Escape
Sleep 400ms
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
Sleep 800ms

# Queue screen — toggle GFM Markdown on
Type "g"
Sleep 400ms

# Toggle DB on
Type "d"
Sleep 400ms

# Run the download
Type "r"
Sleep 8s

# Download progress is shown per-chapter
# Wait for completion
Sleep 15s

Ctrl+C
Sleep 500ms
