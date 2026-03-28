# 03-search.tape — Demonstrate the O'Reilly search screen
# Records: open Search → type query → view results → add book to queue

Output tapes/output/03-search.gif

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

# Navigate to "Search O'Reilly" — item 4 (down 3 times from top)
Down
Sleep 200ms
Down
Sleep 200ms
Down
Sleep 200ms
Enter
Sleep 800ms

# Search form is shown — type a query
Type "kubernetes"
Sleep 400ms

# Submit search
Enter
Sleep 3s

# Results are shown — navigate down a couple results
Down
Sleep 400ms
Down
Sleep 400ms
Down
Sleep 400ms

# Add top result to queue with Space
Space
Sleep 300ms

# Move to another result and add it too
Down
Sleep 400ms
Space
Sleep 300ms

# Confirm and go to queue
Enter
Sleep 1s

# We're back at queue screen — show the queued items
Sleep 1.5s

Ctrl+C
Sleep 500ms
