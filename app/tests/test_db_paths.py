import sqlite3

import pytest

from brain_castle import db, paths


def tables(con):
    return {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}


def test_migrates_from_an_empty_db(tmp_path):
    con = db.connect(tmp_path / "a.db")
    assert con.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION
    assert tables(con) == {"tags", "tasks", "task_tags", "books", "notes", "note_tags", "images", "settings"}
    assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    assert con.execute("PRAGMA journal_mode").fetchone()[0] == "delete"  # rollback journal, easy to copy


def test_migrating_twice_changes_nothing(tmp_path):
    con = db.connect(tmp_path / "a.db")
    con.execute("INSERT INTO tags(name, created_at, updated_at) VALUES ('x', 1, 1)")
    assert db.migrate(con) == db.SCHEMA_VERSION
    assert con.execute("SELECT COUNT(*) FROM tags").fetchone()[0] == 1


def test_runs_only_the_missing_migrations(tmp_path):
    calls = []

    def v1(con):
        calls.append(1)
        con.execute("CREATE TABLE a(x)")

    def v2(con):
        calls.append(2)
        con.execute("CREATE TABLE b(x)")

    con = db.connect(tmp_path / "m.db", migrations=[v1])
    assert calls == [1]
    db.migrate(con, [v1, v2])
    assert calls == [1, 2] and con.execute("PRAGMA user_version").fetchone()[0] == 2


def test_a_failing_migration_rolls_back(tmp_path):
    def good(con):
        con.execute("CREATE TABLE a(x)")

    def bad(con):
        con.execute("CREATE TABLE b(x)")
        raise RuntimeError("boom")

    con = db.connect(tmp_path / "f.db", migrations=[good])
    with pytest.raises(RuntimeError):
        db.migrate(con, [good, bad])
    assert con.execute("PRAGMA user_version").fetchone()[0] == 1
    assert "b" not in tables(con)


def test_a_newer_database_is_refused(tmp_path):
    path = tmp_path / "n.db"
    con = sqlite3.connect(path)
    con.execute("PRAGMA user_version = 99")
    con.close()
    with pytest.raises(RuntimeError):
        db.connect(path)


def test_foreign_keys_are_enforced(tmp_path):
    con = db.connect(tmp_path / "fk.db")
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO notes(book_id, title, created_at, updated_at) VALUES (99, 'x', 1, 1)")


# ---------- paths ----------

def test_resolve_paths_creates_subfolders(tmp_path):
    p = paths.resolve_paths(tmp_path / "data")
    assert p.root == tmp_path / "data"
    assert p.images.is_dir() and p.logs.is_dir() and p.webview.is_dir()
    assert p.db == p.root / "brain-castle.db"


def test_falls_back_when_the_data_folder_is_not_writable(tmp_path):
    blocker = tmp_path / "data"
    blocker.write_text("a file, so no folder can be made here")
    fallback = tmp_path / "appdata" / "BrainCastle"
    p = paths.resolve_paths(blocker, fallback)
    assert p.root == fallback and p.images.is_dir()


def test_fallback_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert paths.fallback_data_dir() == tmp_path / "BrainCastle"


def test_error_when_nothing_is_writable(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    a.write_text("x")
    b.write_text("x")
    with pytest.raises(OSError):
        paths.resolve_paths(a, b)


def test_default_dir_is_next_to_the_project_or_exe(monkeypatch, tmp_path):
    assert paths.default_data_dir() == paths.PROJECT_DIR / "data"
    monkeypatch.setattr(paths.sys, "frozen", True, raising=False)
    monkeypatch.setattr(paths.sys, "executable", str(tmp_path / "BrainCastle.exe"))
    assert paths.default_data_dir() == tmp_path / "data"
