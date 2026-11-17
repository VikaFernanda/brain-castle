# Data contract

The UI (JavaScript) talks to data only through one `api` object (`app/web/js/api.js`).
Phase 1 implements `MockApi` (in memory, sample data from the design). Later, Python (pywebview `js_api`)
implements the same methods with SQLite. Same names, same arguments, same results.

Rules
- Every method is async and returns plain JSON. No classes, no dates as objects.
- Method names are snake_case so they are identical in JS and Python.
- JS owns view logic (filter, sort, group, week/month math). Python owns data, rules and files.
- Errors: a method rejects with an `Error` whose message is short and readable. The UI shows it in a toast.
- Dates are `"YYYY-MM-DD"` strings, times are `"HH:MM"` (24 h). Empty string `""` means "not set".
- Colors are hex strings from the palette (see Tag colors).

## ID prefixes

| Prefix | Entity | Example |
|---|---|---|
| `t` | task | `t12` |
| `n` | note | `n3` |
| `b` | book | `b1` |
| `g` | tag | `g5` |
| `i` | image | `i104` |

The first letter tells what an id is. Python creates ids as prefix + a number that never repeats.
List order in `load_all` is the manual order (see `reorder`).

## Entities

### task
| Field | Type | Notes |
|---|---|---|
| `id` | string | `t…` |
| `title` | string | required, not empty |
| `notes` | string | GitHub markdown. Images appear as `![alt](img:IMAGE_ID)` |
| `date` | string | `YYYY-MM-DD` or `""` (no date yet) |
| `time` | string | `HH:MM` or `""` |
| `tags` | string[] | tag ids |
| `images` | object | `{ imageId: src }` for ids used in `notes` (see image) |
| `done` | boolean | |
| `archived` | boolean | |
| `auto` | boolean | true when `run_maintenance` archived it |
| `keep` | boolean | true after the user restored it, so it is never auto-archived again |
| `created` | number | creation time, ms since epoch |

### note
| Field | Type | Notes |
|---|---|---|
| `id` | string | `n…` |
| `bookId` | string | `b…`, required |
| `title` | string | required |
| `body` | string | GitHub markdown, same image tokens as task notes |
| `date` | string | `YYYY-MM-DD` or `""` |
| `tags` | string[] | tag ids |
| `images` | object | `{ imageId: src }` |
| `archived` | boolean | |
| `created` | number | |

### book
| Field | Type | Notes |
|---|---|---|
| `id` | string | `b…` |
| `name` | string | required |
| `color` | string | palette color |
| `date` | string | `YYYY-MM-DD` or `""` |
| `archived` | boolean | |
| `created` | number | |

### tag
| Field | Type | Notes |
|---|---|---|
| `id` | string | `g…` |
| `name` | string | required |
| `color` | string | palette color |

Tag colors (palette from the design): `#FFC9D9` Pink, `#FFE9A0` Yellow, `#C3D4FF` Blue, `#E0CCFF` Purple, `#BFEBDD` Mint, `#FFD3B8` Peach.

### image
Images belong to the text of one task or note. The text holds the token `![alt](img:ID)`.
Python stores the file in the data `images` folder; the UI receives `src` (a data URL in the mock,
a file URL or data URL from Python). Fields: `id` (`i…`), `alt` (string), `src` (string).
Rules: when text is saved, images whose token is no longer in the text are dropped (the design's `pruneImgs`).
In Phase 1 images are only carried as the `images` map on tasks and notes; separate image methods are not part of this contract yet.

### settings
| Field | Type | Notes |
|---|---|---|
| `theme` | string | `"pink"` (default), `"blue"` or `"teal"` |

The theme lives in the `settings` table (Python) or in memory (MockApi). Nothing uses `localStorage`.

## Methods

### Load
- `load_all()` → `{ tasks: task[], notes: note[], books: book[], tags: tag[], settings }`.
  Includes archived items (they have `archived: true`). One call at start.

### Create, update, delete, archive, restore
For each of `task`, `note`, `book`:

| Method | Arguments | Returns |
|---|---|---|
| `create_task(fields)` / `create_note(fields)` / `create_book(fields)` | fields without `id`, `archived`, `created` | the new item |
| `update_task(id, fields)` / `update_note(id, fields)` / `update_book(id, fields)` | only the fields that change | the updated item |
| `delete_task(id)` / `delete_note(id)` / `delete_book(id)` | id | `{ id }` |
| `archive_task(id)` / `archive_note(id)` / `archive_book(id)` | id | the updated item |
| `restore_task(id)` / `restore_note(id)` / `restore_book(id)` | id | the updated item |

Rules
- `delete_book` also deletes the notes of that book. Archiving a book does not touch its notes' own flags (the UI shows them under the book).
- `restore_note` also restores its book (a note needs its book). Restore sets `archived: false`, `auto: false`, `keep: true`.
- Deleting is permanent. Archiving is reversible.
- Tasks are never moved between types.

### Tags
- `create_tag({ name, color })` → tag
- `update_tag(id, { name?, color? })` → tag
- `delete_tag(id)` → `{ id }`. Also removes the tag id from every task and note.

### Order and moving
- `reorder(ids, beforeId = null)` → `{ ids }` (new full order of that kind).
  `ids` all have the same prefix. They are placed right before `beforeId`; `null` puts them at the end.
  Used by drag and drop on tasks, notes and books.
- `move(ids, target)` → `{ ids }`.
  Tasks: `target = { date: "YYYY-MM-DD" | "" }` (the day, or `""` for "No date yet").
  Notes: `target = { bookId }`.

### Maintenance
- `run_maintenance()` → `{ autoArchived: string[] }`.
  Archives every non-archived task with a `date` more than 3 months before today, unless `keep` is true.
  Sets `archived: true, auto: true`. The UI calls it at start and after saving a task, and shows a toast when the list is not empty.

### Settings
- `get_settings()` → settings
- `set_settings(patch)` → settings (full, after the change). Example: `set_settings({ theme: "blue" })`.

## Python backend (Phase 6)

- Python methods answer `{ok: true, data}` or `{ok: false, error}`; `PyApi` (in `api.js`) turns that into a value or a rejected `Error`.
- Images: JS sends new pictures in the `images` map as data URLs. Python checks the real file type and size, saves the file,
  picks the image id and rewrites the token in the text. The returned item has the final text and `images` (`id -> http://127.0.0.1:PORT/images/FILE`).
- The page is served from the same local server (`http://127.0.0.1:PORT/index.html?host=py`), because Chromium blocks ES modules on `file://`.
- Data folder: `data\` (images, logs, webview, `brain-castle.db`). Fallback `%APPDATA%\BrainCastle`.
