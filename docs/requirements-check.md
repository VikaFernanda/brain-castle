# Requirements check - PLAN.md "Your requests -> phase"

Proof = an automated check that passes today (run on 2026-11-17), or a note. `T` = `python app\web\dev\test_<name>.py`
(browser, MockApi), `P` = `app\.venv\Scripts\python -m pytest app\tests` (Python), `QA` = `python app\web\dev\qa.py`.

| # | Request | Phase | Done | Proof |
| --- | --- | --- | --- | --- |
| 1 | Pink/yellow, blue/purple, teal/pink themes + Themes button | 1 | [x] | `QA`: 3 themes x 17 screens x 2 sizes, 0 problems. `qa_source_compare.py`: all 3 theme token sets are in the app. `test_tasks` "overflow check: list blue / teal". Theme saved: `P` `test_settings_theme` |
| 2 | Fixed sidebar, Archive tab at the bottom | 1, 4 | [x] | `shoot.py`: "sidebar fixed while main scrolls = True" (3 themes). Archive tab: `test_archive` "sidebar chip shows 3 / 0" |
| 3 | Top bar: name, clickable breadcrumbs, universal search | 1, 4 | [x] | `test_archive`: "search finds tasks by title / note by text / tag + book name", "tasks crumbs", "diary crumbs", "book open crumbs", "Search crumb clears the search", "Esc clears search" |
| 4 | Tasks list by weekday; calendar board; drag between days (both views) | 2 | [x] | `test_tasks`: "list: 7 day cards + no date", "board: 7 columns + parking lot", "list: drop on day moves task", "board: drop on day", "month board: drop on day". Real mouse drag in Chromium. Drag in WebView2: tested in the Phase 0 spike (`docs\spike-results.md`), **not re-tested in the built exe in this phase** |
| 5 | Optional time on tasks | 2 | [x] | `test_tasks`: "deadline soon: time first". `P` `test_task_defaults_and_validation` (time field) |
| 6 | Sort: latest created / deadline soon / manual (tasks, books, notes) | 2, 3 | [x] | `test_tasks`: "manual order", "deadline soon", "latest created"; `test_diary`: "books latest created", "books date soon", "books manual", "notes latest created / date soon / manual". `P` `test_reorder_*` |
| 7 | Month/week filter, Done filter | 2 (tasks), 3 (books) | [x] | `test_tasks`: "month title", "next month", "filter Done", "filter To do". `test_diary`: "month filter", "week filter", "all time shows every book" |
| 8 | Auto-archive tasks older than 3 months | 4 (UI), 6 (Python) | [x] | `test_archive`: 10 month-end cutoff cases, "midnight: marked auto". `P`: `test_cutoff_date`, `test_auto_archive_at_the_three_month_edge`, `..._on_month_ends`, `test_keep_flag_blocks_auto_archive` |
| 9 | Books with nested notes + dropdown; board of books -> open book | 3 | [x] | `test_diary`: "book opens", "note count label", "board: 4 covers", "open book: note cards", "close book" |
| 10 | Move notes between books; optional dates on books and notes | 3 | [x] | `test_diary`: "list: drop on book moves note", "board: drop on book chip moves note", "bulk move to book". `P` `test_move_notes_between_books`. Dates: "books date soon", "notes date soon: undated last" |
| 11 | Create, edit, archive, delete, multi-select + bulk actions | 2, 3, 4 | [x] | `test_tasks`: "create task", "edit saves", "row archive", "row delete", "bulk archive", "bulk delete removes". `test_diary`: "create book/note", "note archive", "bulk delete removes the book and its notes". `test_archive`: "store matches api after bulk ops" |
| 12 | Tags: create, delete, filter | 2, 3 | [x] | `test_tasks`: "tag filter", "tag removed from tags and tasks". `test_diary`: "tag filter hides books without a match". `P` `test_delete_tag_removes_it_from_tasks_and_notes` |
| 13 | Archive: restore, delete forever, select many, restore all, delete all | 4 | [x] | `test_archive`: "restore task: archived false, keep true", "delete asks first", "restore selected restores 2", "delete selected removes 1", "restore all: archive empty", "delete all removes every archived item". `P` `test_archive_then_delete_is_permanent` |
| 14 | Images in text + arrange + GitHub markdown | 5 | [x] | `test_rich`: "drop on textarea inserts at the caret", "paste adds an image", "move up swaps blocks", "preview shows the pictures", "big image is shrunk to 1200px". `test_markdown`: 89 of 89 cases. `P` `test_images.py` (13 tests). Drop/paste in WebView2: Phase 0 spike |
| 15 | Python + portable Windows app | 0, 6, 7, 8 | [x] on this PC / [ ] second PC | `P`: 86 tests pass. `dist\BrainCastle-portable-1.0.0.zip` built; unzipped to a temp folder, `BrainCastle.exe` started, window title "Brain Castle", `data\brain-castle.db` created. **Not tested on a second PC** (see below) |

## Not proven

- **Second PC.** The "final zip runs on a second PC" condition is not done: I only have this PC. Test steps: README "Run it".
  Test on a PC without Python and (if possible) a clean Windows user. The SmartScreen/antivirus behaviour is unknown.
- **Design equality.** See `docs\qa-report.md`, section 1: no design screenshots exist, so a pixel comparison was not possible.
- The corrupt-database dialog: the code path ran in the built exe (log line written, file unchanged, exit), but in this
  automated session I could not see the dialog on screen.
