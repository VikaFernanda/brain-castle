"""Data safety (Phase 9): a process killed during a save, and a damaged database file."""
import hashlib
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from brain_castle import db, desktop
from brain_castle import main as app_main
from brain_castle.services import Services

APP = str(Path(__file__).resolve().parents[1])


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_py(code: str, *args, timeout=60):
    return subprocess.run([sys.executable, "-c", textwrap.dedent(code), *map(str, args)], cwd=APP,
                          env={**os.environ, "PYTHONPATH": APP}, capture_output=True, text=True, timeout=timeout)


def open_services(folder: Path) -> tuple:
    (folder / "images").mkdir(exist_ok=True)
    con = db.connect(folder / "brain-castle.db")
    return con, Services(con, folder / "images")


# ---------- killed during a save ----------

def test_kill_in_the_middle_of_a_transaction(tmp_path):
    con, svc = open_services(tmp_path)
    for i in range(5):
        svc.create_task({"title": f"saved {i}"})
    con.close()
    # The child begins a transaction, writes 50 rows, then dies without COMMIT (os._exit = like a kill).
    r = run_py("""
        import os, sys
        from pathlib import Path
        from brain_castle import db
        con = db.connect(Path(sys.argv[1]) / "brain-castle.db")
        con.execute("BEGIN")
        for i in range(50):
            con.execute("INSERT INTO tasks(title, notes, date, time, done, archived, position, created_at, updated_at) VALUES ('half', '', '', '', 0, 0, ?, 1, 1)", (1000 + i,))
        os._exit(9)
    """, tmp_path)
    assert r.returncode == 9, r.stderr
    con, svc = open_services(tmp_path)
    titles = [t["title"] for t in svc.load_all()["tasks"]]
    assert titles == [f"saved {i}" for i in range(5)]  # the half-written save is gone, nothing else lost
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    svc.create_task({"title": "after the crash"})  # and the app can keep saving
    con.close()


def test_hard_kill_of_a_busy_process_keeps_every_finished_save(tmp_path):
    """Kill the process from outside (like Task Manager > End task) while it saves in a loop."""
    code = """
        import sys
        from pathlib import Path
        from brain_castle import db
        from brain_castle.services import Services
        folder = Path(sys.argv[1]); (folder / "images").mkdir(exist_ok=True)
        svc = Services(db.connect(folder / "brain-castle.db"), folder / "images")
        i = 0
        while True:
            t = svc.create_task({"title": f"task {i}", "notes": "x" * 2000})
            print(i, flush=True)   # printed only AFTER the save finished
            i += 1
    """
    proc = subprocess.Popen([sys.executable, "-c", textwrap.dedent(code), str(tmp_path)], cwd=APP,
                            env={**os.environ, "PYTHONPATH": APP}, stdout=subprocess.PIPE, text=True)
    last = -1
    for line in proc.stdout:
        last = int(line)
        if last >= 40:
            break
    proc.kill()
    proc.wait()
    con, svc = open_services(tmp_path)
    count = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert count >= last + 1  # every save that finished is there (one more may have finished after the last print)
    assert all(t["title"].startswith("task ") for t in svc.load_all()["tasks"])
    con.close()


# ---------- damaged database ----------

def write(path: Path, data: bytes) -> str:
    path.write_bytes(data)
    return sha(path)


def test_garbage_file_is_reported_and_kept(tmp_path):
    f = tmp_path / "brain-castle.db"
    before = write(f, b"this is not a database " * 500)
    with pytest.raises(db.DatabaseDamaged) as e:
        db.connect(f)
    assert e.value.path == f
    assert sha(f) == before
    assert sorted(p.name for p in tmp_path.iterdir()) == ["brain-castle.db"]  # no journal, no copy, no new file


def test_broken_pages_are_reported_and_kept(tmp_path):
    con, svc = open_services(tmp_path)
    for i in range(300):
        svc.create_task({"title": f"task {i}", "notes": "text " * 40})
    con.close()
    f = tmp_path / "brain-castle.db"
    data = bytearray(f.read_bytes())
    for off in range(8192, len(data) - 4096, 4096 * 3):  # wreck pages in the middle, keep the header
        data[off:off + 64] = b"\xff" * 64
    before = write(f, bytes(data))
    with pytest.raises(db.DatabaseDamaged):
        db.connect(f)
    assert sha(f) == before


def test_truncated_file_is_reported_and_kept(tmp_path):
    con, svc = open_services(tmp_path)
    for i in range(300):
        svc.create_task({"title": f"task {i}", "notes": "text " * 40})
    con.close()
    f = tmp_path / "brain-castle.db"
    before = write(f, f.read_bytes()[: 4096 * 3 + 100])
    with pytest.raises(db.DatabaseDamaged):
        db.connect(f)
    assert sha(f) == before


def test_newer_database_is_not_called_damaged(tmp_path):
    con = db.connect(tmp_path / "x.db")
    con.execute("PRAGMA user_version = 99")
    con.close()
    with pytest.raises(RuntimeError):
        db.connect(tmp_path / "x.db")


def test_main_shows_a_clear_message_and_keeps_the_file(tmp_path, monkeypatch):
    data = tmp_path / "data"
    data.mkdir()
    f = data / "brain-castle.db"
    before = write(f, b"garbage" * 1000)
    shown = []
    monkeypatch.setattr(desktop, "message_box", lambda title, text, ask_open_url=None: shown.append(text))
    monkeypatch.setattr(desktop, "webview2_installed", lambda: True)
    assert app_main.main(["--data-dir", str(data)]) == 1
    assert len(shown) == 1
    assert "NOT changed or deleted" in shown[0] and str(f) in shown[0] and "Import backup" in shown[0]
    assert sha(f) == before
