"""ALL data rules in ONE module (a port of app/web/js/rules.js plus the MockApi behaviour).

Rules (docs/data-contract.md):
  - Archiving a book hides its notes (the notes' own flags are not changed).
  - Restoring a note also restores its book. Restoring a task sets archived=0, auto=0, keep=1.
  - Deleting a book deletes its notes. Deleting a tag removes it from every task and note.
  - Auto-archive: tasks dated more than 3 calendar months ago. No date = never. keep = never.
  - Deleting an item deletes its image rows; saving text drops images whose token left the text.
Every write runs in one transaction. Dates are plain "YYYY-MM-DD" / "HH:MM" strings, no time zones.
"""
import calendar
import re
import sqlite3
import threading
import time
from datetime import date as _date
from pathlib import Path
from typing import Callable

from . import images as imgs

AUTO_ARCHIVE_MONTHS = 3
THEMES = ("pink", "blue", "teal")
SETTINGS_DEFAULTS = {"theme": "pink"}
PREFIX = {"t": "task", "n": "note", "b": "book", "g": "tag", "i": "image"}

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_TOKEN_RE = re.compile(r"!\[([^\]]*)\]\(img:([\w-]+)\)")
_TEXT_MAX = 200_000
_TITLE_MAX = 300


class ServiceError(Exception):
    """A short, readable message for the user (shown in a toast)."""


# ---------- pure helpers ----------

def today_iso() -> str:
    return _date.today().isoformat()


def cutoff_date(today: str, months: int = AUTO_ARCHIVE_MONTHS) -> str:
    """Today minus N calendar months. A shorter target month clamps the day (May 31 -> Feb 28)."""
    y, m, d = (int(p) for p in today.split("-"))
    total = y * 12 + (m - 1) - months
    y, m = divmod(total, 12)
    m += 1
    return f"{y:04d}-{m:02d}-{min(d, calendar.monthrange(y, m)[1]):02d}"


def auto_archive_ids(tasks, today: str) -> list[int]:
    """A task dated exactly on the cutoff day is NOT older, so it stays."""
    cut = cutoff_date(today)
    return [t["id"] for t in tasks if not t["archived"] and not t["keep"] and t["date"] and t["date"] < cut]


def _now_ms() -> int:
    return int(time.time() * 1000)


def fmt_id(prefix: str, n: int) -> str:
    return f"{prefix}{n}"


def parse_id(value, prefix: str) -> int:
    kind = PREFIX[prefix]
    if isinstance(value, str) and value[:1] == prefix and value[1:].isdigit():
        return int(value[1:])
    raise ServiceError(f"{kind} not found: {value}")


def _text(value, label: str, *, required=False, limit=_TITLE_MAX) -> str:
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ServiceError(f"{label} must be text.")
    value = value.replace("\x00", "")
    if required:
        value = value.strip()
        if not value:
            raise ServiceError("Please add a name first.")
    if len(value) > limit:
        raise ServiceError(f"{label} is too long.")
    return value


def _date_field(value) -> str:
    value = "" if value is None else value
    if value == "":
        return ""
    if not isinstance(value, str) or not _DATE_RE.match(value):
        raise ServiceError("The date must look like YYYY-MM-DD.")
    try:
        _date.fromisoformat(value)
    except ValueError:
        raise ServiceError("This date does not exist.") from None
    return value


def _time_field(value) -> str:
    value = "" if value is None else value
    if value == "":
        return ""
    if not isinstance(value, str) or not _TIME_RE.match(value):
        raise ServiceError("The time must look like HH:MM.")
    return value


def _color_field(value) -> str:
    value = "" if value is None else value
    if value != "" and (not isinstance(value, str) or not _COLOR_RE.match(value)):
        raise ServiceError("The color must be a hex color like #FFC9D9.")
    return value


def _bool(value, label: str) -> int:
    if not isinstance(value, bool):
        raise ServiceError(f"{label} must be true or false.")
    return int(value)


def _fields(fields) -> dict:
    if fields is None:
        return {}
    if not isinstance(fields, dict):
        raise ServiceError("The fields must be an object.")
    return fields


class Services:
    """All reads and writes. One lock serialises the calls that pywebview makes from worker threads."""

    def __init__(self, con: sqlite3.Connection, images_dir: Path, image_url: Callable[[str], str] | None = None,
                 today: Callable[[], str] = today_iso):
        self.con = con
        self.images_dir = Path(images_dir)
        self.image_url = image_url or (lambda name: "images/" + name)
        self.today = today
        self._lock = threading.RLock()

    # ---------- transaction plumbing ----------

    def _tx(self, fn):
        """Run fn() in one transaction. Image files of rows that were deleted are removed after COMMIT;
        files saved by a transaction that rolls back are removed again."""
        with self._lock:
            self._doomed: list[str] = []
            self._fresh: list[str] = []
            self.con.execute("BEGIN")
            try:
                result = fn()
                self.con.execute("COMMIT")
            except BaseException:
                self.con.execute("ROLLBACK")
                for name in self._fresh:
                    imgs.delete_image_file(self.images_dir, name)
                raise
            for name in self._doomed:
                imgs.delete_image_file(self.images_dir, name)
            return result

    def _read(self, fn):
        with self._lock:
            return fn()

    # ---------- row -> contract dict ----------

    def _tag_ids(self, table: str, key: str, owner: int) -> list[str]:
        rows = self.con.execute(f"SELECT tag_id FROM {table} WHERE {key}=? ORDER BY position", (owner,)).fetchall()
        return [fmt_id("g", r[0]) for r in rows]

    def _image_map(self, col: str, owner: int) -> dict:
        rows = self.con.execute(f"SELECT id, filename FROM images WHERE {col}=? ORDER BY position, id", (owner,)).fetchall()
        return {fmt_id("i", r["id"]): self.image_url(r["filename"]) for r in rows}

    def _task(self, row) -> dict:
        return {"id": fmt_id("t", row["id"]), "title": row["title"], "notes": row["notes"], "date": row["date"],
                "time": row["time"], "tags": self._tag_ids("task_tags", "task_id", row["id"]),
                "images": self._image_map("task_id", row["id"]), "done": bool(row["done"]),
                "archived": bool(row["archived"]), "auto": bool(row["auto"]), "keep": bool(row["keep"]),
                "created": row["created_at"]}

    def _note(self, row) -> dict:
        return {"id": fmt_id("n", row["id"]), "bookId": fmt_id("b", row["book_id"]), "title": row["title"],
                "body": row["body"], "date": row["date"], "tags": self._tag_ids("note_tags", "note_id", row["id"]),
                "images": self._image_map("note_id", row["id"]), "archived": bool(row["archived"]),
                "created": row["created_at"]}

    @staticmethod
    def _book(row) -> dict:
        return {"id": fmt_id("b", row["id"]), "name": row["name"], "color": row["color"], "date": row["date"],
                "archived": bool(row["archived"]), "created": row["created_at"]}

    @staticmethod
    def _tag(row) -> dict:
        return {"id": fmt_id("g", row["id"]), "name": row["name"], "color": row["color"]}

    def _get(self, table: str, n: int, kind: str):
        row = self.con.execute(f"SELECT * FROM {table} WHERE id=?", (n,)).fetchone()
        if row is None:
            raise ServiceError(f"{kind} not found")
        return row

    def _item(self, kind: str, n: int) -> dict:
        table = {"task": "tasks", "note": "notes", "book": "books", "tag": "tags"}[kind]
        row = self._get(table, n, kind)
        return {"task": self._task, "note": self._note, "book": self._book, "tag": self._tag}[kind](row)

    @staticmethod
    def _next_position(con, table: str) -> int:
        return con.execute(f"SELECT COALESCE(MAX(position), -1) + 1 FROM {table}").fetchone()[0]

    # ---------- load ----------

    def load_all(self) -> dict:
        def run():
            q = self.con.execute
            return {
                "tasks": [self._task(r) for r in q("SELECT * FROM tasks ORDER BY position, id")],
                "notes": [self._note(r) for r in q("SELECT * FROM notes ORDER BY position, id")],
                "books": [self._book(r) for r in q("SELECT * FROM books ORDER BY position, id")],
                "tags": [self._tag(r) for r in q("SELECT * FROM tags ORDER BY position, id")],
                "settings": self._settings(),
            }
        return self._read(run)

    # ---------- tags on items ----------

    def _set_tags(self, table: str, key: str, owner: int, tag_ids) -> None:
        if not isinstance(tag_ids, list):
            raise ServiceError("Tags must be a list.")
        wanted: list[int] = []
        for raw in tag_ids:
            n = parse_id(raw, "g")
            if n not in wanted:
                wanted.append(n)
        for n in wanted:
            if self.con.execute("SELECT 1 FROM tags WHERE id=?", (n,)).fetchone() is None:
                raise ServiceError(f"tag not found: g{n}")
        self.con.execute(f"DELETE FROM {table} WHERE {key}=?", (owner,))
        for pos, n in enumerate(wanted):
            self.con.execute(f"INSERT INTO {table}({key}, tag_id, position) VALUES (?,?,?)", (owner, n, pos))

    # ---------- images of one text ----------

    def _sync_images(self, col: str, owner: int, text: str, sent) -> str:
        """Make the images of one task/note match its text. Returns the text (image ids may be renamed).

        `sent` is the {id: src} map from JS. A src that is a data URL is a NEW image: its file is checked
        and saved, and Python picks the id (the token in the text is rewritten). An id this item already
        owns, without a data URL, is kept. Images whose token left the text are deleted.
        """
        sent = sent if isinstance(sent, dict) else {}
        owned = {fmt_id("i", r["id"]): r for r in self.con.execute(f"SELECT * FROM images WHERE {col}=?", (owner,))}
        now = _now_ms()
        rename: dict[str, str] = {}
        used: set[str] = set()
        for m in _TOKEN_RE.finditer(text):
            alt, old = m.group(1), m.group(2)
            if old in rename or old in used:
                continue
            src = sent.get(old)
            if imgs.is_data_url(src):
                name = imgs.save_image(self.images_dir, imgs.decode_data_url(src))
                self._fresh.append(name)
                pos = self.con.execute(f"SELECT COALESCE(MAX(position), -1) + 1 FROM images WHERE {col}=?", (owner,)).fetchone()[0]
                cur = self.con.execute(f"INSERT INTO images(filename, alt, {col}, position, created_at, updated_at) VALUES (?,?,?,?,?,?)",
                                       (name, alt, owner, pos, now, now))
                rename[old] = fmt_id("i", cur.lastrowid)
                used.add(rename[old])
            elif old in owned:
                used.add(old)
            # else: unknown id without data. The token stays and the UI shows "missing image".
        for key, row in owned.items():
            if key not in used:
                self._doomed.append(row["filename"])
                self.con.execute("DELETE FROM images WHERE id=?", (row["id"],))
        if rename:
            text = _TOKEN_RE.sub(lambda m: f"![{m.group(1)}](img:{rename.get(m.group(2), m.group(2))})", text)
        return text

    def _delete_owner_images(self, col: str, owner_ids: list[int]) -> None:
        for n in owner_ids:
            for r in self.con.execute(f"SELECT filename FROM images WHERE {col}=?", (n,)):
                self._doomed.append(r["filename"])

    # ---------- tasks ----------

    def create_task(self, fields) -> dict:
        f = _fields(fields)

        def run():
            now = _now_ms()
            title = _text(f.get("title"), "The title", required=True)
            notes = _text(f.get("notes"), "The notes", limit=_TEXT_MAX)
            cur = self.con.execute(
                "INSERT INTO tasks(title, notes, date, time, done, archived, position, created_at, updated_at) VALUES (?,?,?,?,?,0,?,?,?)",
                (title, notes, _date_field(f.get("date")), _time_field(f.get("time")), _bool(f.get("done", False), "done"),
                 self._next_position(self.con, "tasks"), now, now))
            n = cur.lastrowid
            self._set_tags("task_tags", "task_id", n, f.get("tags", []))
            notes = self._sync_images("task_id", n, notes, f.get("images"))
            self.con.execute("UPDATE tasks SET notes=? WHERE id=?", (notes, n))
            return self._item("task", n)
        return self._tx(run)

    def update_task(self, id, fields) -> dict:
        n, f = parse_id(id, "t"), _fields(fields)

        def run():
            row = self._get("tasks", n, "task")
            sets: dict = {}
            if "title" in f:
                sets["title"] = _text(f["title"], "The title", required=True)
            if "date" in f:
                sets["date"] = _date_field(f["date"])
            if "time" in f:
                sets["time"] = _time_field(f["time"])
            for key in ("done", "archived", "auto", "keep"):
                if key in f:
                    sets[key] = _bool(f[key], key)
            text = _text(f["notes"], "The notes", limit=_TEXT_MAX) if "notes" in f else row["notes"]
            if "notes" in f or "images" in f:
                sets["notes"] = self._sync_images("task_id", n, text, f.get("images"))
            if "tags" in f:
                self._set_tags("task_tags", "task_id", n, f["tags"])
            self._apply("tasks", n, sets)
            return self._item("task", n)
        return self._tx(run)

    def _apply(self, table: str, n: int, sets: dict) -> None:
        sets = {**sets, "updated_at": _now_ms()}
        cols = ", ".join(f"{k}=?" for k in sets)
        self.con.execute(f"UPDATE {table} SET {cols} WHERE id=?", (*sets.values(), n))

    def delete_task(self, id) -> dict:
        n = parse_id(id, "t")

        def run():
            self._get("tasks", n, "task")
            self._delete_owner_images("task_id", [n])
            self.con.execute("DELETE FROM tasks WHERE id=?", (n,))
            return {"id": id}
        return self._tx(run)

    def archive_task(self, id) -> dict:
        return self.update_task(id, {"archived": True})

    def restore_task(self, id) -> dict:
        return self.update_task(id, {"archived": False, "auto": False, "keep": True})

    # ---------- books ----------

    def create_book(self, fields) -> dict:
        f = _fields(fields)

        def run():
            now = _now_ms()
            cur = self.con.execute(
                "INSERT INTO books(name, color, date, archived, position, created_at, updated_at) VALUES (?,?,?,0,?,?,?)",
                (_text(f.get("name"), "The name", required=True), _color_field(f.get("color")), _date_field(f.get("date")),
                 self._next_position(self.con, "books"), now, now))
            return self._item("book", cur.lastrowid)
        return self._tx(run)

    def update_book(self, id, fields) -> dict:
        n, f = parse_id(id, "b"), _fields(fields)

        def run():
            self._get("books", n, "book")
            sets: dict = {}
            if "name" in f:
                sets["name"] = _text(f["name"], "The name", required=True)
            if "color" in f:
                sets["color"] = _color_field(f["color"])
            if "date" in f:
                sets["date"] = _date_field(f["date"])
            if "archived" in f:
                sets["archived"] = _bool(f["archived"], "archived")
            self._apply("books", n, sets)
            return self._item("book", n)
        return self._tx(run)

    def delete_book(self, id) -> dict:
        n = parse_id(id, "b")

        def run():
            self._get("books", n, "book")
            note_ids = [r[0] for r in self.con.execute("SELECT id FROM notes WHERE book_id=?", (n,))]
            self._delete_owner_images("note_id", note_ids)
            self.con.execute("DELETE FROM books WHERE id=?", (n,))  # notes go with it (ON DELETE CASCADE)
            return {"id": id}
        return self._tx(run)

    def archive_book(self, id) -> dict:
        return self.update_book(id, {"archived": True})

    def restore_book(self, id) -> dict:
        return self.update_book(id, {"archived": False})

    # ---------- notes ----------

    def _book_exists(self, raw) -> int:
        n = parse_id(raw, "b") if raw else None
        if n is None or self.con.execute("SELECT 1 FROM books WHERE id=?", (n,)).fetchone() is None:
            raise ServiceError("Make a book first, then add notes to it.")
        return n

    def create_note(self, fields) -> dict:
        f = _fields(fields)

        def run():
            now = _now_ms()
            book = self._book_exists(f.get("bookId"))
            title = _text(f.get("title"), "The title", required=True)
            body = _text(f.get("body"), "The text", limit=_TEXT_MAX)
            cur = self.con.execute(
                "INSERT INTO notes(book_id, title, body, date, archived, position, created_at, updated_at) VALUES (?,?,?,?,0,?,?,?)",
                (book, title, body, _date_field(f.get("date")), self._next_position(self.con, "notes"), now, now))
            n = cur.lastrowid
            self._set_tags("note_tags", "note_id", n, f.get("tags", []))
            body = self._sync_images("note_id", n, body, f.get("images"))
            self.con.execute("UPDATE notes SET body=? WHERE id=?", (body, n))
            return self._item("note", n)
        return self._tx(run)

    def update_note(self, id, fields) -> dict:
        n, f = parse_id(id, "n"), _fields(fields)

        def run():
            row = self._get("notes", n, "note")
            sets: dict = {}
            if "title" in f:
                sets["title"] = _text(f["title"], "The title", required=True)
            if "date" in f:
                sets["date"] = _date_field(f["date"])
            if "bookId" in f:
                sets["book_id"] = self._book_exists(f["bookId"])
            if "archived" in f:
                sets["archived"] = _bool(f["archived"], "archived")
            body = _text(f["body"], "The text", limit=_TEXT_MAX) if "body" in f else row["body"]
            if "body" in f or "images" in f:
                sets["body"] = self._sync_images("note_id", n, body, f.get("images"))
            if "tags" in f:
                self._set_tags("note_tags", "note_id", n, f["tags"])
            self._apply("notes", n, sets)
            return self._item("note", n)
        return self._tx(run)

    def delete_note(self, id) -> dict:
        n = parse_id(id, "n")

        def run():
            self._get("notes", n, "note")
            self._delete_owner_images("note_id", [n])
            self.con.execute("DELETE FROM notes WHERE id=?", (n,))
            return {"id": id}
        return self._tx(run)

    def archive_note(self, id) -> dict:
        return self.update_note(id, {"archived": True})

    def restore_note(self, id) -> dict:
        n = parse_id(id, "n")

        def run():
            row = self._get("notes", n, "note")  # a note needs its book: bring the book back too
            self._apply("books", row["book_id"], {"archived": 0})
            self._apply("notes", n, {"archived": 0})
            return self._item("note", n)
        return self._tx(run)

    # ---------- tags ----------

    def create_tag(self, fields) -> dict:
        f = _fields(fields)

        def run():
            now = _now_ms()
            cur = self.con.execute(
                "INSERT INTO tags(name, color, position, created_at, updated_at) VALUES (?,?,?,?,?)",
                (_text(f.get("name"), "The name", required=True), _color_field(f.get("color")),
                 self._next_position(self.con, "tags"), now, now))
            return self._item("tag", cur.lastrowid)
        return self._tx(run)

    def update_tag(self, id, fields) -> dict:
        n, f = parse_id(id, "g"), _fields(fields)

        def run():
            self._get("tags", n, "tag")
            sets: dict = {}
            if "name" in f:
                sets["name"] = _text(f["name"], "The name", required=True)
            if "color" in f:
                sets["color"] = _color_field(f["color"])
            self._apply("tags", n, sets)
            return self._item("tag", n)
        return self._tx(run)

    def delete_tag(self, id) -> dict:
        n = parse_id(id, "g")

        def run():
            self._get("tags", n, "tag")
            self.con.execute("DELETE FROM tags WHERE id=?", (n,))  # task_tags / note_tags rows cascade
            return {"id": id}
        return self._tx(run)

    # ---------- order and moving ----------

    def reorder(self, ids, before_id=None) -> dict:
        if not isinstance(ids, list) or not ids:
            raise ServiceError("Nothing to reorder.")
        prefix = ids[0][:1] if isinstance(ids[0], str) else ""
        table = {"t": "tasks", "n": "notes", "b": "books", "g": "tags"}.get(prefix)
        if table is None:
            raise ServiceError(f"unknown id: {ids[0]}")
        moved = [parse_id(i, prefix) for i in ids]
        before = parse_id(before_id, prefix) if before_id else None

        def run():
            order = [r[0] for r in self.con.execute(f"SELECT id FROM {table} ORDER BY position, id")]
            for n in moved:
                if n not in order:
                    raise ServiceError(f"{PREFIX[prefix]} not found: {prefix}{n}")
            moved_set = set(moved)
            rest = [n for n in order if n not in moved_set]
            moved_unique = list(dict.fromkeys(moved))
            at = rest.index(before) if before in rest else len(rest)
            rest[at:at] = moved_unique
            for pos, n in enumerate(rest):
                self.con.execute(f"UPDATE {table} SET position=? WHERE id=?", (pos, n))
            return {"ids": [fmt_id(prefix, n) for n in rest]}
        return self._tx(run)

    def move(self, ids, target) -> dict:
        if not isinstance(ids, list) or not isinstance(target, dict):
            raise ServiceError("Nothing to move.")
        parsed = []
        for raw in ids:
            first = raw[:1] if isinstance(raw, str) else ""
            if first not in ("t", "n"):
                raise ServiceError(f"cannot move {raw}")
            parsed.append((first, parse_id(raw, first)))

        def run():
            now = _now_ms()
            date = _date_field(target.get("date")) if any(k == "t" for k, _ in parsed) else ""
            book = self._book_exists(target.get("bookId")) if any(k == "n" for k, _ in parsed) else None
            for kind, n in parsed:
                if kind == "t":
                    self._get("tasks", n, "task")
                    self.con.execute("UPDATE tasks SET date=?, updated_at=? WHERE id=?", (date, now, n))
                else:
                    self._get("notes", n, "note")
                    self.con.execute("UPDATE notes SET book_id=?, updated_at=? WHERE id=?", (book, now, n))
            return {"ids": ids}
        return self._tx(run)

    # ---------- maintenance ----------

    def run_maintenance(self) -> dict:
        def run():
            rows = self.con.execute("SELECT id, date, archived, keep FROM tasks WHERE date != ''").fetchall()
            ids = auto_archive_ids([dict(r) for r in rows], self.today())
            now = _now_ms()
            for n in ids:
                self.con.execute("UPDATE tasks SET archived=1, auto=1, updated_at=? WHERE id=?", (now, n))
            return {"autoArchived": [fmt_id("t", n) for n in ids]}
        return self._tx(run)

    # ---------- settings ----------

    def _settings(self) -> dict:
        saved = {r["key"]: r["value"] for r in self.con.execute("SELECT key, value FROM settings")}
        out = {**SETTINGS_DEFAULTS, **{k: v for k, v in saved.items() if k in SETTINGS_DEFAULTS}}
        if out["theme"] not in THEMES:
            out["theme"] = SETTINGS_DEFAULTS["theme"]
        return out

    def get_settings(self) -> dict:
        return self._read(self._settings)

    def set_settings(self, patch) -> dict:
        patch = _fields(patch)

        def run():
            for key, value in patch.items():
                if key not in SETTINGS_DEFAULTS:
                    raise ServiceError(f"unknown setting: {key}")
                if key == "theme" and value not in THEMES:
                    raise ServiceError("Unknown theme.")
                self.con.execute("INSERT INTO settings(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                                 (key, value))
            return self._settings()
        return self._tx(run)
