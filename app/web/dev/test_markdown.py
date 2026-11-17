"""Run app/web/tests/markdown.html in Chromium and fail if any case fails.

Usage:  python app/web/dev/test_markdown.py
Needs `pip install playwright` and `playwright install chromium` (kept outside the app).
"""
import functools
import http.server
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

WEB = pathlib.Path(__file__).resolve().parents[1]


def main():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(WEB)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        page.goto(f"http://127.0.0.1:{srv.server_port}/tests/markdown.html")
        page.wait_for_function("window.__results", timeout=15000)
        r = page.evaluate("window.__results")
        xss = page.evaluate("window.__xss")
        b.close()
    srv.shutdown()
    print(f"{r['pass']} of {r['total']} markdown cases passed")
    for f in r["failed"]:
        print("FAIL", f)
    for e in errors:
        print("ERROR", e)
    sys.exit(0 if not r["failed"] and not errors and xss == 0 and r["total"] >= 40 else 1)


if __name__ == "__main__":
    main()
