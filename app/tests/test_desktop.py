import json
import sys
import threading
import zipfile

import pytest

from brain_castle import backup, db, desktop
from brain_castle.instance import InstanceLock
from brain_castle.services import Services
from conftest import PNG, data_url, files


# ---------- fixtures ----------

def make_services(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "images").mkdir(exist_ok=True)
    return Services(db.connect(root / "brain-castle.db"), root / "images", image_url=lambda n: "/images/" + n)


def fill(svc):
    book = svc.create_book({"name": "Ideas", "color": "#FFB8CC", "date": ""})
    tag = svc.create_tag({"name": "home", "color": "#FFE58F"})
    svc.create_task({"title": "Pay rent", "notes": "see ![pic](img:i900)", "images": {"i900": data_url()}, "tags": [tag["id"]], "date": "2026-11-17"})
    svc.create_note({"title": "Plan", "body": "text", "bookId": book["id"], "tags": [tag["id"]]})
    svc.set_settings({"theme": "teal"})


def snapshot(svc, folder):
    """Everything that must survive a backup, with the image ids replaced by their file bytes."""
    data = svc.load_all()
    return json.dumps(data, sort_keys=True), {n: (folder / n).read_bytes() for n in files(folder)}


# ---------- backup and restore ----------

def test_backup_then_restore_on_clean_folder_gives_identical_data(tmp_path):
    a = make_services(tmp_path / "a")
    fill(a)
    zip_path = backup.export_backup(a, tmp_path / "out" / "b.zip")

    b = make_services(tmp_path / "clean")  # a fresh data folder
    backup.import_backup(b, zip_path, tmp_path / "clean" / "backups")

    assert snapshot(b, tmp_path / "clean" / "images") == snapshot(a, tmp_path / "a" / "images")
    assert b.get_settings() == {"theme": "teal"}
    assert len(files(tmp_path / "clean" / "images")) == 1


def test_export_zip_content(tmp_path):
    a = make_services(tmp_path / "a")
    fill(a)
    path = backup.export_backup(a, tmp_path / "b.zip")
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    assert "manifest.json" in names and "brain-castle.db" in names
    assert len([n for n in names if n.startswith("images/")]) == 1
    assert not (tmp_path / "b.zip.part").exists()


def test_import_replaces_existing_data_and_makes_safety_copy(tmp_path):
    src = make_services(tmp_path / "src")
    fill(src)
    zip_path = backup.export_backup(src, tmp_path / "b.zip")

    dst = make_services(tmp_path / "dst")
    dst.create_task({"title": "only here", "notes": ""})
    old = snapshot(dst, tmp_path / "dst" / "images")
    safety = backup.import_backup(dst, zip_path, tmp_path / "dst" / "backups")

    assert [t["title"] for t in dst.load_all()["tasks"]] == ["Pay rent"]
    # the safety copy restores the old data
    again = make_services(tmp_path / "again")
    backup.import_backup(again, safety, tmp_path / "again" / "backups")
    assert snapshot(again, tmp_path / "again" / "images") == old


def test_import_rejects_bad_files_and_changes_nothing(tmp_path):
    svc = make_services(tmp_path / "d")
    svc.create_task({"title": "keep me", "notes": ""})
    before = snapshot(svc, tmp_path / "d" / "images")

    not_zip = tmp_path / "x.zip"
    not_zip.write_bytes(b"hello")
    no_db = tmp_path / "nodb.zip"
    with zipfile.ZipFile(no_db, "w") as z:
        z.writestr("hello.txt", "x")
    evil = tmp_path / "evil.zip"
    good = backup.export_backup(svc, tmp_path / "good.zip")
    with zipfile.ZipFile(good) as zin, zipfile.ZipFile(evil, "w") as zout:
        for n in zin.namelist():
            zout.writestr(n, zin.read(n))
        zout.writestr("images/../../evil.png", PNG)
    bad_db = tmp_path / "baddb.zip"
    with zipfile.ZipFile(bad_db, "w") as z:
        z.writestr("manifest.json", json.dumps({"format": backup.FORMAT, "schema_version": 1}))
        z.writestr("brain-castle.db", b"this is not sqlite" * 100)
    newer = tmp_path / "newer.zip"
    with zipfile.ZipFile(good) as zin, zipfile.ZipFile(newer, "w") as zout:
        for n in zin.namelist():
            zout.writestr(n, json.dumps({"format": backup.FORMAT, "schema_version": 99}) if n == "manifest.json" else zin.read(n))

    for bad in (not_zip, no_db, evil, bad_db, newer, tmp_path / "missing.zip"):
        with pytest.raises(backup.BackupError):
            backup.import_backup(svc, bad, tmp_path / "d" / "backups")
    assert snapshot(svc, tmp_path / "d" / "images") == before
    assert not (tmp_path / "d" / "backups").exists()  # no safety copy for a rejected file
    assert not (tmp_path / "evil.png").exists()


# ---------- single instance ----------

def test_second_instance_is_refused_until_the_first_lets_go(tmp_path):
    first, second = InstanceLock(tmp_path), InstanceLock(tmp_path)
    assert first.acquire() is True
    assert second.acquire() is False
    (tmp_path / "other").mkdir()
    other = InstanceLock(tmp_path / "other")
    assert other.acquire() is True  # another data folder is free
    other.release()
    first.release()
    assert second.acquire() is True
    second.release()


def test_second_launch_leaves_the_data_alone(tmp_path):
    """A second process (main) on the same folder returns at once and touches nothing."""
    from brain_castle import main as app_main

    svc = make_services(tmp_path / "data")
    svc.create_task({"title": "one", "notes": ""})
    lock = InstanceLock(tmp_path / "data")
    assert lock.acquire()
    try:
        assert app_main.main(["--data-dir", str(tmp_path / "data")]) == 0  # would open a window if it did not stop
    finally:
        lock.release()
    assert [t["title"] for t in svc.load_all()["tasks"]] == ["one"]


# ---------- window size and position ----------

SCREENS = [(0, 0, 1920, 1080), (1920, 0, 1280, 1024)]


def test_fit_window():
    assert desktop.fit_window(None, SCREENS) == (None, None, 1280, 840)  # first start: centered
    ok = {"x": 100, "y": 80, "width": 1000, "height": 700}
    assert desktop.fit_window(ok, SCREENS) == (100, 80, 1000, 700)
    assert desktop.fit_window({**ok, "x": 2000}, SCREENS) == (2000, 80, 1000, 700)  # second monitor
    assert desktop.fit_window({**ok, "x": 5000}, SCREENS) == (None, None, 1000, 700)  # monitor is gone
    assert desktop.fit_window({**ok, "width": 300, "height": 200}, SCREENS) == (100, 80, 900, 600)  # min size
    assert desktop.fit_window({**ok, "x": -32000, "y": -32000}, SCREENS)[:2] == (None, None)  # was minimized


def test_window_state_is_saved_in_settings_but_hidden_from_js(svc):
    assert svc.get_window_state() is None
    svc.set_window_state({"x": 10, "y": 20, "width": 1000, "height": 700})
    assert svc.get_window_state() == {"x": 10, "y": 20, "width": 1000, "height": 700}
    assert svc.get_settings() == {"theme": "pink"} and svc.load_all()["settings"] == {"theme": "pink"}
    svc.con.execute("UPDATE settings SET value='garbage' WHERE key='window'")
    assert svc.get_window_state() is None


# ---------- errors ----------

def test_crash_log_gets_main_and_thread_errors(tmp_path):
    old = sys.excepthook, threading.excepthook
    try:
        target = desktop.install_crash_logging(tmp_path)
        assert target == tmp_path / "crash.log"

        def boom():
            raise ValueError("thread boom")
        t = threading.Thread(target=boom)
        t.start()
        t.join()
        try:
            raise RuntimeError("main boom")
        except RuntimeError:
            sys.excepthook(*sys.exc_info())
    finally:
        sys.excepthook, threading.excepthook = old
    text = target.read_text(encoding="utf-8")
    assert "thread boom" in text and "main boom" in text


def test_messages_name_the_place_and_the_download_link(tmp_path):
    from brain_castle import paths
    blocker = tmp_path / "file"
    blocker.write_text("x")
    with pytest.raises(OSError) as e:
        paths.resolve_paths(blocker / "data", blocker / "fallback")
    assert str(blocker / "data") in desktop.data_folder_message(e.value)
    assert desktop.WEBVIEW2_URL in desktop.webview2_missing_message()
