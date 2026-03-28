# 05-library-browse.tape — Demonstrate Library Browse screen
# Records: open Browse Library → scroll books → filter → select → export

Output tapes/output/05-library-browse.gif

Require python3

Set Shell "bash"
Set FontSize 14
Set Width 900
Set Height 540
Set Theme "Catppuccin Mocha"
Set Framerate 24
Set PlaybackSpeed 0.8

# Assumes cookies.json and a populated library.db
Type "source .venv/bin/activate 2>/dev/null; python main.py"
Enter
Sleep 2s

# Navigate to "Browse Library" — down 6 times from top
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

# Library list is shown with badges — scroll down
Down
Sleep 300ms
Down
Sleep 300ms
Down
Sleep 300ms
Down
Sleep 300ms
Down
Sleep 300ms

# Toggle filter mode and search
Type "/"
Sleep 400ms
Type "kubernetes"
Sleep 1s

# Clear filter
Ctrl+U
Sleep 500ms

# Select a book with Space
Space
Sleep 300ms
Down
Sleep 300ms
Space
Sleep 300ms

# Back out without exporting
Escape
Sleep 500ms

Ctrl+C
Sleep 500ms
