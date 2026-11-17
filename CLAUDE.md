# Brain Castle

Portable Windows desktop app in Python.

## Rules
- The design file (`E:\Library\claude-code-projects\brain-castle\project`, read-only) is the source of truth. The UI must look IDENTICAL: same CSS tokens, class names, spacing, copy text, icons, fonts. Never restyle or "improve" the design. Its `support.js` is missing: read it as source code.
- Stack: Python 3.12, pywebview 6.x (WebView2), SQLite via the standard library, front-end = Preact + htm saved locally in `app\web\js\vendor`. No CDN, no Node, no build step. Fonts (Fredoka, Nunito) are saved locally. The app must work fully offline.
- Item IDs start with `t` (task), `n` (note), `b` (book), `g` (tag), like the design.
- JS owns view logic (filter, sort, group). Python owns data, rules and files.
- Icons must never leave their button or area: fixed size, `flex:none`, no overflow.
- The front-end must also run in a normal browser using a MockApi, so it can be tested with Playwright screenshots against the files in `reference\`.
- Work in small steps, commit at the end of each phase, never start the next phase.

## Commands
- Setup: `py -3.12 -m venv app\.venv` then `app\.venv\Scripts\python -m pip install -r app\requirements.txt -r app\requirements-dev.txt`
- Run the app: (fill in as it appears)
- Tests: `app\.venv\Scripts\python -m pytest app\tests`
- Build: (fill in as it appears) PyInstaller `--onedir --windowed`
