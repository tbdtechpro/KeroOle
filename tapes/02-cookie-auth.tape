# 02-cookie-auth.tape — Demonstrate manual cookie paste auth flow
# Records: open app → Set Session Cookie → paste cookie string → confirm

Output tapes/output/02-cookie-auth.gif

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

# Navigate to "Set Session Cookie (paste)" — it's item 2 (index 1)
Down
Sleep 300ms
Enter
Sleep 800ms

# Now on cookie input screen — type a placeholder cookie string
# (replace with a real truncated cookie for an actual recording)
Type "orm-jwt=eyJhbGciOiJSUzI1NiJ9.DEMO_TOKEN_REPLACE_FOR_REAL_RECORDING"
Sleep 500ms

# Submit
Enter
Sleep 1.5s

# Back at main menu with cookie saved
Sleep 1s
Ctrl+C
Sleep 500ms
