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
- Run the app (from the `app` folder): `.venv\Scripts\python -m brain_castle` (`--debug` for dev tools, `--data-dir PATH`, `--seed` = throw-away sample data in `<data>-seed`). Data is `data\` next to the project (next to the exe when built); delete it for a clean first run.
- Tests: `app\.venv\Scripts\python -m pytest app\tests`
- Build (not run in Phase 7): PyInstaller `--onedir --windowed --name BrainCastle --icon app\assets\brain-castle.ico --add-data "app\web;web" --add-data "app\assets;assets"`, entry `app\brain_castle\__main__.py`.
- Front-end checks (browser, MockApi): `python app\web\dev\test_desktop.py` (also test_tasks, test_diary, test_archive, test_rich, test_markdown). Needs playwright installed outside the app.
- Icon: `python app\tools\make_icon.py` redraws `app\assets\brain-castle.ico` from the castle logo.

## Desktop notes (Phase 7)
- Release build blocks F5, right click, devtools and zoom; `--debug` turns that back on (`?host=py&debug=1`).
- One instance per data folder (lock file `data\.lock`). Backups: File menu, zip of DB + images; import makes a safety copy in `data\backups`.
- Crashes go to `data\logs\crash.log`.
