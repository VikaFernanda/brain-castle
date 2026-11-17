"""Serve app/web, open every screen in every theme at 1440x900, run the overflow check, take screenshots.

Usage (needs `pip install playwright` and `playwright install chromium`, kept outside the app):
    python app/web/dev/shoot.py [output_dir]
Exit code 1 if the overflow check finds anything or the sidebar moves when the main area scrolls.
"""
import functools
import http.server
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

WEB = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else WEB.parent.parent / "shots"
THEMES = ["pink", "blue", "teal"]
AREAS = [("tasks", "Tasks"), ("diary", "Diary"), ("archive", "Archive")]


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(WEB))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srv = serve()
    url = f"http://127.0.0.1:{srv.server_port}/index.html"
    failed = False
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for theme in THEMES:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            errors = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.goto(url)
            page.wait_for_function("window.__bc && window.__bc.store.getState().loaded")
            page.evaluate("t => window.__bc.actions.pickTheme(t)", theme)  # the theme lives in settings now
            page.evaluate("document.fonts.ready")
            page.add_script_tag(path=str(WEB / "dev" / "overflow-check.js"))
            for area, label in AREAS:
                page.click(f".side >> text={label}")
                page.screenshot(path=str(OUT / f"{theme}-{area}.png"))
                problems = page.evaluate("window.__overflowCheck()")
                print(f"{theme}/{area}: overflow problems = {len(problems)}", problems or "")
                failed |= bool(problems)
            # theme menu open
            page.click("text=Themes")
            page.screenshot(path=str(OUT / f"{theme}-menu.png"))
            problems = page.evaluate("window.__overflowCheck()")
            print(f"{theme}/menu: overflow problems = {len(problems)}", problems or "")
            failed |= bool(problems)
            page.click("text=Themes")
            # sidebar must stay fixed while only the main area scrolls
            page.evaluate("document.querySelector('.mainpane').insertAdjacentHTML('beforeend','<div id=\"filler\" style=\"height:3000px\"></div>')")
            before = page.evaluate("document.querySelector('.side').getBoundingClientRect().top")
            page.evaluate("document.querySelector('.mainpane').scrollTop = 1200")
            after = page.evaluate("document.querySelector('.side').getBoundingClientRect().top")
            main_scrolled = page.evaluate("document.querySelector('.mainpane').scrollTop")
            win_scrolled = page.evaluate("window.scrollY")
            ok = before == after and main_scrolled > 0 and win_scrolled == 0
            print(f"{theme}: sidebar fixed while main scrolls = {ok} (main scrollTop {main_scrolled}, window {win_scrolled})")
            failed |= not ok
            if errors:
                print(f"{theme}: console/page errors:", errors)
                failed = True
            page.close()
        browser.close()
    srv.shutdown()
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
