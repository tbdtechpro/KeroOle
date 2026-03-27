# Windows Smoke Test — KeroOle Cross-Platform Gate

**Purpose:** Verify that `bubblepy` and `pygloss` work in Windows Terminal before implementing cross-platform changes.
**Run this in:** Windows Terminal (not cmd.exe, not classic PowerShell ISE)

---

## 1. Prerequisites

- Python 3.10+ installed and on PATH
  Verify: `python --version`
- Git installed
  Verify: `git --version`
- Windows Terminal (ships with Windows 11; install from Microsoft Store on Windows 10)

---

## 2. Install Dependencies

Open Windows Terminal and run:

```powershell
# Clone and install bubblepy
git clone https://github.com/tbdtechpro/bubblepy.git
cd bubblepy
pip install -e .
cd ..

# Clone and install pygloss
git clone https://github.com/tbdtechpro/pygloss.git
cd pygloss
pip install -e .
cd ..
```

---

## 3. Run the Smoke Test

Create a file called `smoke_test.py` anywhere convenient and paste this into it:

```python
import bubblepy as tea
from pygloss import Color, Style, rounded_border

class Smoke(tea.Model):
    def init(self): return []
    def update(self, msg):
        if isinstance(msg, tea.KeyMsg) and str(msg) in ("q", "ctrl+c"):
            return self, tea.Quit()
        return self, None
    def view(self):
        return (Style().border(rounded_border())
                .border_foreground(Color("#7C3AED"))
                .padding(1, 2)
                .render("bubblepy OK\n\nPress q to quit"))

if __name__ == "__main__":
    tea.Program(Smoke(), alt_screen=True).run()
```

Then run it:

```powershell
python smoke_test.py
```

---

## 4. Pass / Fail Criteria

| What to check | Pass | Fail |
|---|---|---|
| A rounded border appears | Yes | Garbled or missing characters |
| The border is purple/violet | Yes | No colour / wrong colour |
| `q` exits cleanly | Yes | Hangs or crashes |

**If all three pass:** Report back — implementation can proceed.
**If any fail:** Note the exact error or visual problem and report back before proceeding.

---

## 5. Context

This smoke test is the go/no-go gate for the cross-platform runtime compatibility work described in:
`docs/superpowers/specs/2026-03-27-cross-platform-runtime-compat-design.md`

The changes being gated are:
- Cross-platform clipboard via `pyperclip`
- Calibre binary discovery on macOS and Windows
- ANSI colour support in Windows Terminal
- `multiprocessing.freeze_support()` for PyInstaller compatibility
