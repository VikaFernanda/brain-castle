"""SQLite connection and schema versioning (PRAGMA user_version)."""
import sqlite3
from pathlib import Path

# Default rollback journal on purpose (no WAL): the .db file alone is a full copy.


def _v1(con: sqlite3.Connection) -> None:
    # No executescript(): it would COMMIT first and break the transaction that migrate() opened.
    statements = [
        """CREATE TABLE tags (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            color      TEXT NOT NULL DEFAULT '',
            position   INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""",
        """CREATE TABLE tasks (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            title      TEXT NOT NULL,
            notes      TEXT NOT NULL DEFAULT '',
            date       TEXT NOT NULL DEFAULT '',
            time       TEXT NOT NULL DEFAULT '',
            done       INTEGER NOT NULL DEFAULT 0,
            archived   INTEGER NOT NULL DEFAULT 0,
            auto       INTEGER NOT NULL DEFAULT 0,
            keep       INTEGER NOT NULL DEFAULT 0,
            position   INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""",
        """CREATE TABLE task_tags (
            task_id  INTEGER NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (task_id, tag_id)
        )""",
        """CREATE TABLE books (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            color      TEXT NOT NULL DEFAULT '',
            date       TEXT NOT NULL DEFAULT '',
            archived   INTEGER NOT NULL DEFAULT 0,
            position   INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""",
        """CREATE TABLE notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id    INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
            title      TEXT NOT NULL,
            body       TEXT NOT NULL DEFAULT '',
            date       TEXT NOT NULL DEFAULT '',
            archived   INTEGER NOT NULL DEFAULT 0,
            position   INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        )""",
        """CREATE TABLE note_tags (
            note_id  INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
            tag_id   INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            position INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (note_id, tag_id)
        )""",
        """CREATE TABLE images (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            filename   TEXT NOT NULL UNIQUE,
            alt        TEXT NOT NULL DEFAULT '',
            task_id    INTEGER REFERENCES tasks(id) ON DELETE CASCADE,
            note_id    INTEGER REFERENCES notes(id) ON DELETE CASCADE,
            position   INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL,
            CHECK ((task_id IS NULL) <> (note_id IS NULL))
        )""",
        """CREATE TABLE settings (
            key   TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )""",
        "CREATE INDEX idx_tasks_position ON tasks(position)",
        "CREATE INDEX idx_notes_book ON notes(book_id)",
        "CREATE INDEX idx_images_task ON images(task_id)",
        "CREATE INDEX idx_images_note ON images(note_id)",
    ]
    for sql in statements:
        con.execute(sql)


# MIGRATIONS[i] upgrades a database from version i to i + 1. Append new functions; never edit old ones.
MIGRATIONS = [_v1]
SCHEMA_VERSION = len(MIGRATIONS)


def migrate(con: sqlite3.Connection, migrations=None) -> int:
    """Run the missing migrations, each in one transaction. Returns the new version."""
    migrations = MIGRATIONS if migrations is None else migrations
    version = con.execute("PRAGMA user_version").fetchone()[0]
    if version > len(migrations):
        raise RuntimeError(f"The database is newer (v{version}) than this app (v{len(migrations)}).")
    for step in range(version, len(migrations)):
        con.execute("BEGIN")
        try:
            migrations[step](con)
            con.execute(f"PRAGMA user_version = {step + 1}")  # PRAGMA values cannot be bound
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    return len(migrations)


def connect(path: str | Path, migrations=None) -> sqlite3.Connection:
    # isolation_level=None: we run BEGIN/COMMIT ourselves. check_same_thread=False: pywebview calls
    # the api from worker threads; services.py serialises them with a lock.
    con = sqlite3.connect(str(path), isolation_level=None, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON")
    migrate(con, migrations)
    return con
