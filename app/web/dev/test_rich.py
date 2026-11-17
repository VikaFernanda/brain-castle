"""Playwright checks for the rich text editor (Phase 5), run against MockApi in a normal browser.

Usage:  python app/web/dev/test_rich.py [screenshot_dir]
Needs `pip install playwright` and `playwright install chromium` (kept outside the app).
Exit code 1 if any check fails.
"""
import functools
import http.server
import pathlib
import sys
import threading

from playwright.sync_api import sync_playwright

WEB = pathlib.Path(__file__).resolve().parents[1]
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else WEB.parent.parent / "shots"
results = []


def check(name, ok, extra=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (" " + str(extra) if extra and not ok else ""))


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(WEB)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def state(page, expr):
    return page.evaluate(f"(() => {{ const s = window.__bc.store.getState(); return {expr}; }})()")


# Make a real image file in the page (a coloured canvas), so the test needs no files on disk.
MAKE_FILE = """([w, h, type, name]) => new Promise((res) => {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const g = c.getContext('2d'); g.fillStyle = '#ff77aa'; g.fillRect(0, 0, w, h);
  c.toBlob((b) => { window.__file = new File([b], name, { type }); res(true); }, type);
})"""
FIRE_DROP = """(sel) => { const dt = new DataTransfer(); dt.items.add(window.__file);
  const el = document.querySelector(sel);
  ['dragenter', 'dragover', 'drop'].forEach((t) => el.dispatchEvent(new DragEvent(t, { dataTransfer: dt, bubbles: true, cancelable: true })));
  return true; }"""
FIRE_PASTE = """(sel) => { const dt = new DataTransfer(); dt.items.add(window.__file);
  const el = document.querySelector(sel);
  el.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true, cancelable: true }));
  return true; }"""


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srv = serve()
    url = f"http://127.0.0.1:{srv.server_port}/index.html"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("dialog", lambda d: (errors.append("dialog: " + d.message), d.dismiss()))
        page.goto(url)
        page.wait_for_function("window.__bc && window.__bc.store.getState().loaded")
        page.evaluate("document.fonts.ready")
        page.add_script_tag(path=str(WEB / "dev" / "overflow-check.js"))
        ta = "textarea[aria-label='Details (optional)']"

        # ---- the modal has the design's controls ----
        page.get_by_role("button", name="New task", exact=True).click()
        dlg = page.get_by_role("dialog", name="New task")
        check("Write and Preview and arrange buttons", dlg.get_by_role("button", name="Write").count() == 1 and dlg.get_by_role("button", name="Preview and arrange").count() == 1)
        check("Add image button", dlg.locator("label.filebtn", has_text="Add image").count() == 1)
        check("Write mode is on at first", page.locator(ta).count() == 1)
        page.get_by_role("button", name="Preview and arrange").click()
        check("empty preview message", page.get_by_text("Nothing to show yet").count() == 1)
        page.get_by_role("button", name="Write").click()

        # ---- type markdown, see it in the preview ----
        page.fill("input[placeholder='What needs doing?']", "Rich task")
        page.fill(ta, "# Title\n\nFirst **bold** paragraph\n\n- one\n- two\n\nhttps://example.com/x")
        page.get_by_role("button", name="Preview and arrange").click()
        check("preview shows 4 blocks", page.locator(".block").count() == 4)
        check("preview heading", page.locator(".block").first.inner_text().strip() == "Title")
        check("preview autolink", page.locator(".block a[href='https://example.com/x']").count() == 1)
        page.screenshot(path=str(OUT / "rich-preview.png"))
        page.evaluate("window.__overflowCheck()")
        problems = page.evaluate("window.__overflowCheck()")
        check("overflow check: preview", not problems, problems)

        # ---- arrange: move up, move down, remove ----
        blocks = lambda: page.locator(".block")
        blocks().nth(1).get_by_role("button", name="Move up").click()
        check("move up swaps blocks", state(page, "s.modal.text.split('\\n\\n')[0]") == "First **bold** paragraph")
        blocks().nth(0).get_by_role("button", name="Move down").click()
        check("move down swaps back", state(page, "s.modal.text.split('\\n\\n')[0]") == "# Title")
        check("first block has Move up disabled", blocks().first.get_by_role("button", name="Move up").is_disabled())
        check("last block has Move down disabled", blocks().last.get_by_role("button", name="Move down").is_disabled())
        blocks().last.get_by_role("button", name="Remove this block").click()
        check("remove drops the block", blocks().count() == 3 and "example.com" not in state(page, "s.modal.text"))

        # ---- add images: file picker, drop on textarea, paste, drop on a block ----
        page.evaluate(MAKE_FILE, [2400, 1200, "image/png", "wide.png"])
        page.get_by_role("button", name="Write").click()
        page.fill(ta, "alpha\n\nomega")
        page.locator(ta).click()
        page.evaluate(f"document.querySelector(\"{ta}\").setSelectionRange(5, 5)")
        page.locator(ta).dispatch_event("select")
        page.set_input_files("input[type=file]", files=[{"name": "pick.png", "mimeType": "image/png", "buffer": bytes(page.evaluate("() => { const c = document.createElement('canvas'); c.width = 10; c.height = 10; return Array.from(atob(c.toDataURL('image/png').split(',')[1]), (x) => x.charCodeAt(0)); }"))}])
        page.wait_for_function("window.__bc.store.getState().modal.text.includes('img:')")
        text = state(page, "s.modal.text")
        check("picker inserts a token at the caret", text.startswith("alpha\n\n![pick](img:i") and text.endswith("\n\nomega"), text)

        page.evaluate(f"document.querySelector(\"{ta}\").setSelectionRange(0, 0)")
        page.locator(ta).dispatch_event("select")
        page.evaluate(FIRE_DROP, ta)
        page.wait_for_function("window.__bc.store.getState().modal.text.includes('wide')")
        text = state(page, "s.modal.text")
        check("drop on textarea inserts at the caret (start)", text.startswith("![wide](img:i"), text)
        wide = state(page, "Object.values(s.modal.images).find((v) => v.length > 0 && v.startsWith('data:image/png')) && 1")
        dims = page.evaluate("() => new Promise((res) => { const s = window.__bc.store.getState().modal; const id = /wide\\]\\(img:([\\w-]+)/.exec(s.text)[1]; const i = new Image(); i.onload = () => res([i.width, i.height]); i.src = s.images[id]; })")
        check("big image is shrunk to 1200px", dims == [1200, 600], dims)

        page.evaluate(MAKE_FILE, [30, 30, "image/png", "pasted.png"])
        page.locator(ta).focus()
        page.evaluate(f"document.querySelector(\"{ta}\").setSelectionRange(document.querySelector(\"{ta}\").value.length, document.querySelector(\"{ta}\").value.length)")
        page.evaluate(FIRE_PASTE, ta)
        page.wait_for_function("window.__bc.store.getState().modal.text.includes('pasted')")
        check("paste adds an image at the caret (end)", state(page, "s.modal.text").rstrip().endswith(")") and "omega" in state(page, "s.modal.text"))

        page.evaluate(MAKE_FILE, [20, 20, "image/gif", "anim.gif"])
        page.get_by_role("button", name="Preview and arrange").click()
        n_before = page.locator(".block").count()
        page.evaluate(FIRE_DROP, ".block >> nth=0") if False else None
        page.evaluate("""() => { const dt = new DataTransfer(); dt.items.add(window.__file);
          const el = document.querySelectorAll('.block')[0];
          ['dragover', 'drop'].forEach((t) => el.dispatchEvent(new DragEvent(t, { dataTransfer: dt, bubbles: true, cancelable: true }))); }""")
        page.wait_for_function("window.__bc.store.getState().modal.text.includes('anim')")
        parts = state(page, "s.modal.text.split('\\n\\n')")
        check("drop on a block inserts right after it", "anim" in parts[1] and "wide" in parts[0], parts)
        check("preview shows the pictures", page.locator(".block img").count() == 4 and n_before == 5 and page.locator(".block").count() == 6, (n_before, page.locator(".block").count()))
        gif_ok = state(page, "Object.values(s.modal.images).some((v) => v.startsWith('data:image/gif'))")
        check("GIF is kept as it is", gif_ok)
        page.screenshot(path=str(OUT / "rich-images.png"))
        problems = page.evaluate("window.__overflowCheck()")
        check("overflow check: preview with images", not problems, problems)

        # ---- save: unused images are dropped, chip and thumbnail show ----
        page.locator(".block").nth(1).get_by_role("button", name="Remove this block").click()  # remove the gif block
        page.get_by_role("button", name="Create", exact=True).click()
        page.wait_for_function("!window.__bc.store.getState().modal")
        task = state(page, "s.tasks.find((t) => t.title === 'Rich task')")
        check("saved task keeps used images only", len(task["images"]) == 3 and all(("img:" + k) in task["notes"] for k in task["images"]), task["images"].keys())
        check("task shows the image chip", page.get_by_text("3 images").count() >= 1)
        page.screenshot(path=str(OUT / "rich-task-chip.png"))

        # ---- note card thumbnail in board view ----
        page.click(".side >> text=Diary")
        page.get_by_role("button", name="Board").click()
        page.get_by_role("button", name="New note", exact=True).click()
        page.fill("input[placeholder='Give this note a title']", "Picture note")
        page.evaluate(MAKE_FILE, [300, 200, "image/png", "photo.png"])
        page.evaluate("document.querySelector(\"textarea[aria-label='Your note']\")")
        page.evaluate(FIRE_DROP, "textarea[aria-label='Your note']")
        page.wait_for_function("window.__bc.store.getState().modal.text.includes('photo')")
        page.get_by_role("button", name="Create", exact=True).click()
        page.wait_for_function("!window.__bc.store.getState().modal")
        page.get_by_role("button", name="Open book Daily Diary").click()
        check("note card shows the first image as thumbnail", page.locator("article.card", has_text="Picture note").locator("img").count() == 1)
        page.screenshot(path=str(OUT / "rich-note-thumb.png"))
        problems = page.evaluate("window.__overflowCheck()")
        check("overflow check: board with thumbnail", not problems, problems)

        # ---- editing keeps the text, hostile text stays text ----
        page.locator(".link", has_text="Picture note").first.click()
        page.get_by_role("button", name="Write").click()
        page.fill("textarea[aria-label='Your note']", "<script>window.__xss=1</script> [x](javascript:alert(1))")
        page.get_by_role("button", name="Preview and arrange").click()
        check("hostile note stays text in the preview", page.locator(".block script").count() == 0 and page.locator(".block a").count() == 0 and page.evaluate("window.__xss") is None)
        browser.close()
    srv.shutdown()
    check("no page errors", not errors, errors)
    print(f"{sum(results)} of {len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
