"""Phase 9 visual QA. Every screen x 3 themes x (1440x900, 1024x700): screenshot + overflow check.
Also checks computed values of parts that the app builds from components (design inline styles).

Usage: python app/web/dev/qa.py [output_dir]      Exit 1 on any problem.
"""
import functools, http.server, pathlib, sys, threading
from playwright.sync_api import sync_playwright

WEB = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else WEB.parent.parent / "shots"
THEMES = ["pink", "blue", "teal"]
SIZES = [(1440, 900), (1024, 700)]
bad = []


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k): pass
    h = functools.partial(Quiet, directory=str(WEB))
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), h)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def btn(page, name, **kw):
    return page.get_by_role("button", name=name, exact=True, **kw)


def screens(page):
    """(name, setup) pairs. Each setup returns the page to a known state afterwards via reload."""
    def tasks_list(p): p.click(".side >> text=Tasks")
    def tasks_week(p): p.click(".side >> text=Tasks"); p.get_by_role("button", name="Calendar board").click()
    def tasks_month(p): tasks_week(p); btn(p, "Month").click()
    def month_list(p): p.click(".side >> text=Tasks"); btn(p, "Month").click()
    def tasks_done(p): p.click(".side >> text=Tasks"); btn(p, "Done").click()
    def tasks_select(p): p.click(".side >> text=Tasks"); btn(p, "Select").click(); p.get_by_role("button", name="Select task").nth(0).click(); p.get_by_role("button", name="Select task").nth(1).click()
    def task_modal(p): p.click(".side >> text=Tasks"); btn(p, "New task").click()
    def tags_modal(p): p.click(".side >> text=Tasks"); p.get_by_role("button", name="Manage tags").first.click()
    def task_delete(p): p.click(".side >> text=Tasks"); btn(p, "Select").click(); p.get_by_role("button", name="Select task").nth(0).click(); btn(p, "Delete").last.click()
    def diary_list(p): p.click(".side >> text=Diary")
    def diary_board(p): p.click(".side >> text=Diary"); p.get_by_role("button", name="Board").first.click()
    def book_open(p): diary_board(p); p.get_by_role("button", name="Open book").first.click() if p.get_by_role("button", name="Open book").count() else None
    def note_modal(p): p.click(".side >> text=Diary"); btn(p, "New note").click()
    def book_modal(p): p.click(".side >> text=Diary"); btn(p, "New book").click()
    def archive(p): p.click(".side >> text=Archive")
    def search(p): p.click(".side >> text=Tasks"); p.get_by_role("searchbox").first.fill("a") if p.get_by_role("searchbox").count() else p.locator("input[type=search], input[aria-label*=earch]").first.fill("a")
    def themes_menu(p): p.click("text=Themes")
    return [("tasks-list", tasks_list), ("tasks-board-week", tasks_week), ("tasks-board-month", tasks_month),
            ("tasks-month-list", month_list), ("tasks-done", tasks_done), ("tasks-select", tasks_select),
            ("task-modal", task_modal), ("tags-modal", tags_modal), ("task-delete-confirm", task_delete),
            ("diary-list", diary_list), ("diary-board", diary_board), ("book-open", book_open),
            ("note-modal", note_modal), ("book-modal", book_modal), ("archive", archive),
            ("search", search), ("themes-menu", themes_menu)]


COMPUTED = [  # (what, js returning value, expected)
    ("breadcrumb separator icon 14px", "(() => { const e = document.querySelector('header .i[style*=\"14px\"], .top .i[style*=\"14px\"]'); return e ? [getComputedStyle(e).width, getComputedStyle(e).height] : 'none'; })()", ["14px", "14px"]),
    ("Show tasks track: yellow, radius 999, padding 4", "(() => { const e = document.querySelector('[role=group][aria-label=\"Show tasks\"]'); const c = getComputedStyle(e); return [c.paddingTop, c.borderTopLeftRadius, c.backgroundColor]; })()", None),
    ("board card icon buttons 32px, icon 16px", "(() => { const b = document.querySelector('button[aria-label=\"Edit task\"]'); const i = b.querySelector('svg'); return [getComputedStyle(b).width, getComputedStyle(b).height, getComputedStyle(i).width, getComputedStyle(i).height]; })()", ["32px", "32px", "16px", "16px"]),
    ("Add-task-on-day button 32px, surface bg", "(() => { const b = document.querySelector('button[aria-label=\"Add task on this day\"]'); return b ? [getComputedStyle(b).width, getComputedStyle(b).height, getComputedStyle(b).backgroundColor] : 'none'; })()", None),
]


def measured_inline(br, url):
    """Design inline styles built by components: bulk selects 170/190px, rich modal max-width 720px."""
    def fresh(page):
        page.goto(url); page.wait_for_function("window.__bc && window.__bc.store.getState().loaded")
    page = br.new_page(viewport={"width": 1440, "height": 900})
    sel = "(l) => { const e = document.querySelector('select[aria-label=\"' + l + '\"]'); if (!e) return 'none'; const c = getComputedStyle(e); return [c.width, c.borderTopLeftRadius]; }"
    fresh(page); page.click(".side >> text=Tasks"); btn(page, "Select").click(); page.get_by_role("button", name="Select task").nth(0).click()
    checks = [("bulk tasks select 170px/999px", page.evaluate(sel, "Move selected tasks to a day"), ["170px", "999px"])]
    fresh(page); page.click(".side >> text=Diary"); btn(page, "Select").click(); page.get_by_role("button", name="Select note").nth(0).click()
    checks.append(("bulk notes select 190px/999px", page.evaluate(sel, "Move selected notes to a book"), ["190px", "999px"]))
    fresh(page); page.click(".side >> text=Tasks"); btn(page, "New task").click()
    checks.append(("modal max-width 720px", page.evaluate("getComputedStyle(document.querySelector('[role=dialog]')).maxWidth"), "720px"))
    for what, v, exp in checks:
        print(f"{'PASS' if v == exp else 'FAIL'} measured: {what} -> {v}")
        if v != exp: bad.append((what, v))
    page.close()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srv = serve()
    url = f"http://127.0.0.1:{srv.server_port}/index.html"
    with sync_playwright() as p:
        br = p.chromium.launch()
        for w, h in SIZES:
            for theme in THEMES:
                page = br.new_page(viewport={"width": w, "height": h})
                errs = []
                page.on("pageerror", lambda e: errs.append(str(e)))
                page.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
                page.goto(url)
                page.wait_for_function("window.__bc && window.__bc.store.getState().loaded")
                page.evaluate("t => window.__bc.actions.pickTheme(t)", theme)
                page.evaluate("document.fonts.ready")
                page.add_script_tag(path=str(WEB / "dev" / "overflow-check.js"))
                for name, setup in screens(page):
                    try:
                        setup(page)
                    except Exception as e:  # a screen we could not reach is a QA failure, not a pass
                        print(f"FAIL {w}x{h} {theme} {name}: could not open ({str(e).splitlines()[0]})")
                        bad.append((name, "unreachable")); page.keyboard.press("Escape"); continue
                    page.wait_for_timeout(120)
                    page.screenshot(path=str(OUT / f"{theme}-{name}-{w}.png"))
                    probs = page.evaluate("window.__overflowCheck()")
                    print(f"{'FAIL' if probs else 'PASS'} {w}x{h} {theme} {name} overflow={len(probs)}", probs or "")
                    if probs: bad.append((name, probs))
                    page.keyboard.press("Escape")
                    page.evaluate("window.__bc.reload && window.__bc.reload()")
                    page.goto(url); page.wait_for_function("window.__bc && window.__bc.store.getState().loaded")
                    page.evaluate("t => window.__bc.actions.pickTheme(t)", theme)
                    page.add_script_tag(path=str(WEB / "dev" / "overflow-check.js"))
                if errs: print("FAIL console errors:", errs); bad.append(("console", errs))
                if theme == "pink" and w == 1440:
                    page.click(".side >> text=Tasks")
                    page.get_by_role("button", name="Calendar board").click()
                    for what, js, exp in COMPUTED:
                        if "Add-task" in what: btn(page, "Month").click()
                        v = page.evaluate(js)
                        ok = (exp is None and v != "none") or v == exp
                        print(f"{'PASS' if ok else 'FAIL'} computed: {what} -> {v}")
                        if not ok: bad.append((what, v))
                page.close()
        measured_inline(br, url)
        br.close()
    srv.shutdown()
    print("problems:", len(bad))
    sys.exit(1 if bad else 0)


main()
