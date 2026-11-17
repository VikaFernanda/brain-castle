# QA report - Phase 9

Date: 2026-11-17. Version 1.0.0.

## 1. What could and could not be checked

**The design cannot be rendered.** `Main.dc.html` needs `support.js`, which is missing, and `reference\` has no screenshots
(only `.gitkeep`). So a pixel-by-pixel side-by-side was **not possible**. I can't confirm pixel equality with the design.

What was done instead, and it can be repeated:

| Check | Tool | Result |
| --- | --- | --- |
| All 52 CSS rules of the design `<style>` block are in the app | `python app\tools\qa_source_compare.py` | 52 of 52 found |
| All inline `style="..."` strings and all visible copy text of the design markup are in the app | same | 8 not found as text (see 3.), 0 text differences |
| Every screen, 3 themes, 1440x900 and 1024x700: screenshot + overflow check | `python app\web\dev\qa.py <folder>` | 102 screens, 0 overflow problems, 0 console errors |
| Computed size of parts that the app builds from components | `qa.py` | 4 of 4 as in the design |
| Themes colors | `qa_source_compare.py` (tokens are CSS rules) | identical |

Screens covered (each x 3 themes x 2 sizes): tasks list, board week, board month, month list, Done filter, select mode with bulk bar,
task modal, manage tags, delete confirm, diary list, diary board, book open, note modal, book modal, archive, search, themes menu.

When someone exports the design screenshots into `reference\`, compare them with the files `qa.py` writes. Until then this
section is the limit of what is proven.

## 2. Differences list

| # | Difference | Status |
| --- | --- | --- |
| - | No visual difference was found by the checks above | none open |

Nothing was changed in the CSS, copy or layout in this phase.

## 3. The 8 inline styles that are not found as text

The source compare reports 8 design inline styles that are not in the app as the same string. They are the same look, written
through a component (`IconButton size=32`, `Segmented tone="soft2"`, bulk bar select width, modal width). Checked in the browser:

| Design | App (computed) | Same? |
| --- | --- | --- |
| Show tasks track: `padding:4px; radius:999px`, yellow | 4px, 999px, `rgb(255,244,199)` = `--accent2-soft` | yes |
| Board card buttons `32x32`, icon `16x16` | 32, 32, 16, 16 | yes |
| "Add task on this day" `32x32`, surface background | 32, 32, `rgb(255,255,255)` | yes |
| Breadcrumb separator icon `14x14` | 14, 14 | yes |
| Bulk "Move selected ..." select `170px` / `190px`, radius 999px | built in `BulkBar` (checked in the overflow check with bulk bars open) | not measured one by one: **I can't confirm** the exact width |
| Modal `max-width:720px` (rich modal) | not measured: **I can't confirm** | open |
| Editor hint `12px/600/line-height 1.4` | written in `RichEditor.js` with the same values (code read) | yes (code only) |

Two rows are not measured. They are listed here as open, so the "no open differences" goal is **not fully proven** for them.

## 4. Load test

1,000 tasks, 200 notes, 50 books, 100 images. Nothing was slow, so nothing was changed. **Before = after.**

Python backend (`app\.venv\Scripts\python app\tools\load_test.py`, 150 KB images, 15.4 MB of data):

| Action | ms |
| --- | --- |
| create 1000 tasks (one by one, each is one saved transaction) | 4055 (about 4 ms each) |
| create 200 notes | 823 |
| attach 100 images | 508 |
| load_all (everything) | 11 |
| update one task | 3.8 |
| reorder 1 / 20 tasks | 7.7 / 7.5 |
| move 50 tasks to a day | 4.6 |
| auto-archive run | 8.5 |
| delete a book with its notes | 5.1 |

Front end in Chromium with MockApi (`python app\web\dev\load_test.py`, time until the next painted frame):

| Action | ms |
| --- | --- |
| load and render | 27 |
| Tasks list, week / month / month sorted | 64 / 42 / 25 |
| Calendar board month / week | 29 / 31 |
| Done filter | 35 |
| Diary list / every book expanded / board | 31 / 46 / 19 |
| Archive | 32 |
| search, per key (avg / max) | 37 / 93 |
| drag a card to another day (includes Playwright) | 132 |

Limit: this ran on the development PC in Chromium, not inside the built exe on a slower PC. The 100 images in the browser
test are 1x1 pixels (the bytes were tested in the Python run).

## 5. Data safety

Found and fixed: a damaged database file was not handled. The app raised a raw SQLite error and only wrote the crash log.

Fixed in `db.py`, `main.py`, `desktop.py`:
- `connect()` runs `PRAGMA quick_check` before any write. A bad file raises `DatabaseDamaged`.
- `main()` shows a clear message (file path, reason, what to do) and exits. The file is never changed, moved or deleted.

New tests (`app\tests\test_safety.py`, all pass):
- process killed with an open transaction (`os._exit`): earlier saves intact, half save gone, integrity ok, app can save again
- process killed from outside while saving in a loop: every save that finished is there, integrity ok
- garbage file, wrecked pages, truncated file: message, file bytes identical (SHA-256), no new files next to it
- newer database version is still refused with its own message (not called "damaged")
- `main()` end to end: message shown, exit code 1, file identical

Limit: the kill tests use Python processes on this PC. Power loss during a write is not tested.
The default SQLite rollback journal is used on purpose (see `db.py`).

## 6. Requirements

See `docs\requirements-check.md`.
