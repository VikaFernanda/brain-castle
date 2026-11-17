r"""Backend load test: 1,000 tasks, 200 notes, 50 books, 100 images (about 150 KB each) in a temp folder.

Usage (from the repo root):  app\.venv\Scripts\python app\tools\load_test.py
Prints timings in ms. Nothing is written outside a temp folder.
"""
import base64
import os
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain_castle import db  # noqa: E402
from brain_castle.services import Services  # noqa: E402

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


def timed(label, fn):
    t = time.perf_counter()
    r = fn()
    print(f"{label:<42}{(time.perf_counter() - t) * 1000:9.1f} ms")
    return r


def main():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "images").mkdir()
        con = db.connect(d / "t.db")
        svc = Services(con, d / "images")
        tags = [svc.create_tag({"name": f"tag{i}", "color": "#FFB8CC"})["id"] for i in range(10)]
        books = timed("create 50 books", lambda: [svc.create_book({"name": f"Book {i}", "color": "#FFB8CC"})["id"] for i in range(50)])

        def tasks():
            return [svc.create_task({"title": f"Task {i}", "notes": "some **notes** " * 10, "date": f"2026-{1 + i % 12:02d}-{1 + i % 28:02d}",
                                     "tags": [tags[i % 10]]})["id"] for i in range(1000)]
        tids = timed("create 1000 tasks", tasks)

        def notes():
            return [svc.create_note({"title": f"Note {i}", "bookId": books[i % 50], "body": "text " * 50, "tags": [tags[i % 10]]})["id"] for i in range(200)]
        nids = timed("create 200 notes", notes)
        big = PNG + os.urandom(150_000)
        url = "data:image/png;base64," + base64.b64encode(big).decode()

        def imgs():
            for i in range(100):
                svc.update_task(tids[i], {"notes": f"pic ![p](img:i{900 + i})", "images": {f"i{900 + i}": url}})
        timed("attach 100 images (150 KB each)", imgs)
        timed("load_all (1000 t, 200 n, 50 b, 100 img)", svc.load_all)
        timed("load_all again", svc.load_all)
        timed("update one task", lambda: svc.update_task(tids[500], {"title": "changed"}))
        timed("reorder: move 1 task to the top", lambda: svc.reorder([tids[900]], tids[0]))
        timed("reorder: move 20 tasks", lambda: svc.reorder(tids[300:320], tids[0]))
        timed("move 50 tasks to another day", lambda: svc.move(tids[100:150], {"date": "2026-12-01"}))
        timed("run_maintenance (auto-archive)", svc.run_maintenance)
        timed("delete one book (with 4 notes)", lambda: svc.delete_book(books[0]))
        size = sum(p.stat().st_size for p in d.rglob("*") if p.is_file()) / 1e6
        print(f"data size: {size:.1f} MB")
        con.close()


main()
