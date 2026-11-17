"""Backup and restore: one zip with the database and the image files.

Zip layout:  manifest.json | brain-castle.db | images/<file>
Export copies the database with the SQLite backup API, so the copy is consistent even while the app runs.
Import checks the zip first, saves a safety copy of the current data, then replaces the data in place.
The live connection is kept (restored through the backup API), so the app does not have to restart.
"""
import json
import shutil
import sqlite3
import tempfile
import time
import zipfile
from pathlib import Path

from . import db
from .images import _SAFE_NAME
from .services import Services

DB_NAME = "brain-castle.db"
MANIFEST = "manifest.json"
FORMAT = "brain-castle-backup"
EXPECTED_TABLES = {"tags", "tasks", "task_tags", "books", "notes", "note_tags", "images", "settings"}


class BackupError(Exception):
    """A short message that is fine to show to the user."""


def default_name(today: str | None = None) -> str:
    return f"brain-castle-backup-{today or time.strftime('%Y-%m-%d')}.zip"


def export_backup(svc: Services, dest: Path) -> Path:
    """Write the backup zip to `dest` (through a temp file, so a failure never leaves a half zip)."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_zip = dest.with_name(dest.name + ".part")
    with tempfile.TemporaryDirectory() as work:
        copy = Path(work) / DB_NAME
        with svc._lock:  # no write may happen between the db copy and the image list
            target = sqlite3.connect(str(copy))
            try:
                svc.con.backup(target)
            finally:
                target.close()
            names = sorted(p.name for p in svc.images_dir.iterdir() if p.is_file() and _SAFE_NAME.match(p.name))
            try:
                with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED) as z:
                    manifest = {"format": FORMAT, "schema_version": db.SCHEMA_VERSION,
                                "created": time.strftime("%Y-%m-%dT%H:%M:%S"), "images": len(names)}
                    z.writestr(MANIFEST, json.dumps(manifest))
                    z.write(copy, DB_NAME)
                    for name in names:
                        z.write(svc.images_dir / name, "images/" + name)
            except BaseException:
                tmp_zip.unlink(missing_ok=True)
                raise
    tmp_zip.replace(dest)
    return dest


def _check_zip(z: zipfile.ZipFile) -> list[str]:
    """Return the image names in the zip. Raise BackupError if this is not a usable backup."""
    names = z.namelist()
    if MANIFEST not in names or DB_NAME not in names:
        raise BackupError("This file is not a Brain Castle backup.")
    try:
        manifest = json.loads(z.read(MANIFEST))
        version = int(manifest.get("schema_version", 0))
    except (ValueError, AttributeError, TypeError):
        raise BackupError("This file is not a Brain Castle backup.") from None
    if manifest.get("format") != FORMAT:
        raise BackupError("This file is not a Brain Castle backup.")
    if version > db.SCHEMA_VERSION:
        raise BackupError("This backup was made by a newer version of Brain Castle.")
    images = []
    for n in names:
        if n in (MANIFEST, DB_NAME) or n == "images/":
            continue
        short = n[len("images/"):] if n.startswith("images/") else ""
        if not _SAFE_NAME.match(short):  # also rejects "..", absolute paths and sub folders
            raise BackupError("This backup has a file that does not belong in it.")
        images.append(short)
    return images


def _check_db(path: Path) -> None:
    try:
        con = sqlite3.connect(str(path))
        try:
            if con.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise BackupError("The data in this backup is damaged.")
            tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            version = con.execute("PRAGMA user_version").fetchone()[0]
        finally:
            con.close()
    except sqlite3.DatabaseError:
        raise BackupError("The data in this backup is damaged.") from None
    if not EXPECTED_TABLES <= tables:
        raise BackupError("This file is not a Brain Castle backup.")
    if version > db.SCHEMA_VERSION:
        raise BackupError("This backup was made by a newer version of Brain Castle.")


def check_backup(src: Path) -> None:
    """Full check of a backup file without touching any data. Raises BackupError."""
    try:
        with zipfile.ZipFile(src) as z, tempfile.TemporaryDirectory() as work:
            _check_zip(z)
            with z.open(DB_NAME) as f, open(Path(work) / DB_NAME, "wb") as out:
                shutil.copyfileobj(f, out)
            _check_db(Path(work) / DB_NAME)
    except zipfile.BadZipFile:
        raise BackupError("This file is not a Brain Castle backup.") from None
    except OSError as e:
        raise BackupError(f"Could not read this file: {e}") from None


def import_backup(svc: Services, src: Path, safety_dir: Path) -> Path:
    """Replace the current data with the backup. Returns the path of the safety copy.

    Everything is checked and unpacked before anything is changed. If the restore itself fails
    half way, the safety copy has the old data.
    """
    src = Path(src)
    check_backup(src)
    with tempfile.TemporaryDirectory(dir=svc.images_dir.parent) as work_dir:
        work = Path(work_dir)
        with zipfile.ZipFile(src) as z:
            names = _check_zip(z)
            z.extract(DB_NAME, work)
            new_images = work / "images"
            new_images.mkdir()
            for n in names:
                with z.open("images/" + n) as f, open(new_images / n, "wb") as out:
                    shutil.copyfileobj(f, out)
        with svc._lock:
            safety = Path(safety_dir) / ("before-import-" + time.strftime("%Y%m%d-%H%M%S") + ".zip")
            export_backup(svc, safety)
            source = sqlite3.connect(str(work / DB_NAME))
            try:
                source.backup(svc.con)
            finally:
                source.close()
            svc.con.execute("PRAGMA foreign_keys=ON")
            db.migrate(svc.con)  # an older backup is upgraded to the current schema
            for p in svc.images_dir.iterdir():
                if p.is_file():
                    p.unlink()
            for p in new_images.iterdir():
                shutil.move(str(p), str(svc.images_dir / p.name))
    return safety
