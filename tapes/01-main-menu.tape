# 01-main-menu.tape — Show app launch and main menu navigation
# Records: app opens, user scrolls through menu items, quits

Output tapes/output/01-main-menu.gif

Require python3

Set Shell "bash"
Set FontSize 14
Set Width 900
Set Height 540
Set Theme "Catppuccin Mocha"
Set Framerate 24
Set PlaybackSpeed 0.8

# Activate venv if present
Type "source .venv/bin/activate 2>/dev/null; python main.py"
Enter
Sleep 2s

# Main menu is visible — scroll down through items
Sleep 500ms
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
Down
Sleep 300ms
Down
Sleep 300ms
Down
Sleep 300ms

# Back to top
Up
Up
Up
Up
Up
Up
Up
Up
Sleep 500ms

# Quit
Ctrl+C
Sleep 1s
