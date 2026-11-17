"""Playwright checks for the desktop polish (Phase 7): shortcuts, drop safety, dialog focus.
Run against MockApi in a normal browser.  Usage:  python app/web/dev/test_desktop.py
Needs `pip install playwright` and `playwright install chromium` (kept outside the app).
Release-only blocks (F5, right click, zoom) are checked with ?host=py&mock=1 style flags in the second part.
"""
import functools
import http.server
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

WEB = pathlib.Path(__file__).resolve().parents[1]
results = []


def check(name, ok, extra=""):
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (" " + str(extra) if extra and not ok else ""))


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(WEB))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def st(page, expr):
    return page.evaluate(f"(() => {{ const s = window.__bc.store.getState(); return {expr}; }})()")


def active(page):
    return page.evaluate("document.activeElement.getAttribute('aria-label') || document.activeElement.textContent.trim()")


FILE_DROP = """(sel) => {
  // A plain object stands in for the DataTransfer so the test can see what the page writes to dropEffect.
  const el = document.querySelector(sel);
  const make = (type) => {
    const e = new Event(type, {bubbles: true, cancelable: true});
    Object.defineProperty(e, 'dataTransfer', {value: {types: ['Files'], files: [], dropEffect: 'copy'}});
    return e;
  };
  const over = make('dragover'), drop = make('drop');
  el.dispatchEvent(over); el.dispatchEvent(drop);
  return {overPrevented: over.defaultPrevented, dropPrevented: drop.defaultPrevented, effect: over.dataTransfer.dropEffect};
}"""


def main():
    srv = serve()
    base = f"http://127.0.0.1:{srv.server_port}/index.html"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto(base)
        page.wait_for_selector("header")

        # ---- Ctrl+K ----
        page.keyboard.press("Control+k")
        check("Ctrl+K focuses search", page.evaluate("document.activeElement.getAttribute('aria-label')") == "Search all tasks, notes and tags")

        # ---- Esc clears search ----
        page.keyboard.type("a")
        check("typing searches", st(page, "s.q") == "a")
        page.keyboard.press("Escape")
        check("Esc clears search", st(page, "s.q") == "")

        # ---- Ctrl+N in Tasks / Diary ----
        page.locator("body").click(position={"x": 5, "y": 5})
        page.keyboard.press("Control+n")
        page.wait_for_timeout(80)  # the dialog hooks run after the first paint
        check("Ctrl+N opens a new task", st(page, "s.modal && s.modal.kind") == "task" and st(page, "s.modal.id") is None)
        check("focus moved into the modal", page.evaluate("!!document.activeElement.closest('[role=dialog]')"))
        # ---- focus trap ----
        for _ in range(40):
            page.keyboard.press("Tab")
        check("Tab stays inside the modal", page.evaluate("!!document.activeElement.closest('[role=dialog]')"))
        for _ in range(40):
            page.keyboard.press("Shift+Tab")
        check("Shift+Tab stays inside the modal", page.evaluate("!!document.activeElement.closest('[role=dialog]')"))
        page.keyboard.press("Control+n")
        page.wait_for_timeout(80)  # the dialog hooks run after the first paint
        check("Ctrl+N does nothing while a modal is open", st(page, "s.modal.kind") == "task")
        page.keyboard.press("Escape")
        check("Esc closes the modal", st(page, "s.modal") is None)

        page.get_by_role("button", name="Diary").first.click()
        page.keyboard.press("Control+n")
        page.wait_for_timeout(80)  # the dialog hooks run after the first paint
        check("Ctrl+N opens a new note in Diary", st(page, "s.modal && s.modal.kind") == "note")
        page.keyboard.press("Escape")
        page.evaluate("window.__bc.actions.go('archive')")
        page.keyboard.press("Control+n")
        page.wait_for_timeout(80)  # the dialog hooks run after the first paint
        check("Ctrl+N does nothing in Archive", st(page, "s.modal") is None)

        # ---- focus returns to the opener ----
        page.evaluate("window.__bc.actions.go('tasks')")
        opener = page.locator("button.link").first
        opener.focus()
        label = opener.inner_text()
        opener.press("Enter")
        page.wait_for_timeout(80)
        check("Enter opens an item", st(page, "!!s.modal"))
        page.keyboard.press("Escape")
        check("focus returns to the opener", page.evaluate("document.activeElement.textContent.trim()") == label, page.evaluate("document.activeElement.outerHTML.slice(0,100)"))

        # ---- Esc leaves select mode, then confirm dialog Esc closes only the dialog ----
        page.get_by_role("button", name="Select", exact=True).click()
        check("select mode on", st(page, "s.selMode"))
        page.locator("body").click(position={"x": 5, "y": 5})
        page.keyboard.press("Escape")
        check("Esc leaves select mode", st(page, "!s.selMode && Object.keys(s.sel).length === 0"))
        page.evaluate("window.__bc.actions.ask('Sure?', () => {})")
        page.keyboard.press("Escape")
        check("Esc closes the confirm dialog", st(page, "s.confirm") is None)

        # ---- confirm over a modal: Esc closes only the confirm, focus goes back into the modal ----
        page.keyboard.press("Control+n")
        page.wait_for_timeout(80)  # the dialog hooks run after the first paint
        page.evaluate("window.__bc.actions.ask('Sure?', () => {})")
        page.wait_for_timeout(80)
        check("confirm takes focus", page.evaluate("!!document.activeElement.closest('[role=alertdialog]')"))
        page.keyboard.press("Escape")
        check("Esc closes only the confirm", st(page, "s.confirm") is None and st(page, "s.modal && s.modal.kind") == "task")
        check("focus is back in the modal", page.evaluate("!!document.activeElement.closest('[role=dialog]')"))
        page.keyboard.press("Escape")

        # ---- files dropped outside the editor do nothing ----
        r = page.evaluate(FILE_DROP, "main")
        check("file over the page: drop refused", r["overPrevented"] and r["dropPrevented"] and r["effect"] == "none", r)
        page.keyboard.press("Control+n")
        page.wait_for_timeout(80)  # the dialog hooks run after the first paint
        r = page.evaluate(FILE_DROP, "[role=dialog] textarea")
        check("file over the editor is allowed", r["effect"] == "copy", r)
        page.keyboard.press("Escape")
        check("page did not navigate", page.url == base)

        # ---- text drag must not start; item drag still works with a text selection ----
        title = page.locator("button.link").first
        text_drag_started = page.evaluate("""() => { const e = new DragEvent('dragstart', {bubbles: true, cancelable: true, dataTransfer: new DataTransfer()});
          document.querySelector('main h2').firstChild.parentElement.dispatchEvent(e); return !e.defaultPrevented; }""")
        check("dragging non-item content is blocked", text_drag_started is False)
        page.evaluate("window.getSelection().selectAllChildren(document.querySelector('main'))")
        card = page.locator(".card[draggable=true]").first
        card.dispatch_event("mousedown")
        check("mousedown on an item clears a text selection", page.evaluate("window.getSelection().isCollapsed"))
        item_drag = page.evaluate("""() => { const c = document.querySelector('.card[draggable=true]');
          const e = new DragEvent('dragstart', {bubbles: true, cancelable: true, dataTransfer: new DataTransfer()});
          c.dispatchEvent(e); return !e.defaultPrevented; }""")
        check("dragging an item is allowed", item_drag)
        page.evaluate("document.querySelector('.card[draggable=true]').dispatchEvent(new DragEvent('dragend', {bubbles: true}))")

        # ---- a normal browser keeps its own keys and right click ----
        check("normal browser: contextmenu not blocked", page.evaluate("""() => { const e = new MouseEvent('contextmenu', {bubbles: true, cancelable: true}); document.body.dispatchEvent(e); return !e.defaultPrevented; }"""))

        # ---- release build (desktop host, no debug): browser behaviours are blocked ----
        rel = browser.new_page(viewport={"width": 1440, "height": 900})
        rel.add_init_script("window.pywebview = {api: new Proxy({}, {get: () => async () => ({ok: false, error: 'x'})})}")
        rel.goto(base + "?host=py")
        rel.wait_for_selector("header")
        blocked = rel.evaluate("""() => {
          const k = (init) => { const e = new KeyboardEvent('keydown', {bubbles: true, cancelable: true, ...init}); document.body.dispatchEvent(e); return e.defaultPrevented; };
          const c = new MouseEvent('contextmenu', {bubbles: true, cancelable: true}); document.body.dispatchEvent(c);
          const w = new WheelEvent('wheel', {bubbles: true, cancelable: true, ctrlKey: true}); document.body.dispatchEvent(w);
          return {f5: k({key: 'F5'}), ctrlR: k({key: 'r', ctrlKey: true}), f12: k({key: 'F12'}), zoomIn: k({key: '+', ctrlKey: true}),
                  zoomOut: k({key: '-', ctrlKey: true}), zoom0: k({key: '0', ctrlKey: true}), inspect: k({key: 'I', ctrlKey: true, shiftKey: true}),
                  menu: c.defaultPrevented, wheel: w.defaultPrevented, plainKey: k({key: 'a'})};
        }""")
        check("release: F5, Ctrl+R, F12, zoom, devtools, right click, Ctrl+wheel blocked",
              all(blocked[n] for n in ("f5", "ctrlR", "f12", "zoomIn", "zoomOut", "zoom0", "inspect", "menu", "wheel")) and not blocked["plainKey"], blocked)
        dbg = browser.new_page()
        dbg.add_init_script("window.pywebview = {api: new Proxy({}, {get: () => async () => ({ok: false, error: 'x'})})}")
        dbg.goto(base + "?host=py&debug=1")
        dbg.wait_for_selector("header")
        check("--debug turns the blocks back off", dbg.evaluate("""() => { const e = new KeyboardEvent('keydown', {bubbles: true, cancelable: true, key: 'F5'}); document.body.dispatchEvent(e); return !e.defaultPrevented; }"""))

        check("no console errors", not errors, errors)
        browser.close()
    srv.shutdown()
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
