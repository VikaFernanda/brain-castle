"""Front-end load test in a browser with MockApi: 1,000 tasks, 200 notes, 50 books, 100 images.
Times each action until the next painted frame (two requestAnimationFrame calls).

Usage: python app/web/dev/load_test.py
"""
import functools, http.server, pathlib, threading
from playwright.sync_api import sync_playwright

WEB = pathlib.Path(__file__).resolve().parents[1]

SEED = """
(() => {
  const api = window.__bc.api; const iso = (d) => d.toISOString().slice(0, 10);
  const day = (n) => { const d = new Date(); d.setDate(d.getDate() + n); return iso(d); };
  const tags = ['g1','g2','g3','g4','g5'];
  api.db.tasks = []; api.db.notes = []; api.db.books = [];
  for (let i = 0; i < 1000; i++) api.db.tasks.push({ id: 't' + (1000 + i), title: 'Task number ' + i, notes: 'some **notes** for ' + i, date: day((i % 120) - 60), time: i % 3 ? '' : '09:30', tags: [tags[i % 5]], images: i < 100 ? { ['i' + i]: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==' } : {}, done: i % 4 === 0, archived: i >= 800, created: i });
  for (let i = 0; i < 50; i++) api.db.books.push({ id: 'b' + (1000 + i), name: 'Book ' + i, color: '#FFE9A0', date: '', archived: false, created: i });
  for (let i = 0; i < 200; i++) api.db.notes.push({ id: 'n' + (1000 + i), title: 'Note ' + i, body: 'text of note ' + i + ' '.repeat(1) + 'lorem ipsum '.repeat(20), bookId: 'b' + (1000 + i % 50), date: day((i % 90) - 45), tags: [tags[i % 5]], images: {}, archived: false, created: i });
})()
"""
FRAME = "new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"


def serve():
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a, **k): pass
    s = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=str(WEB)))
    threading.Thread(target=s.serve_forever, daemon=True).start()
    return s


def main():
    srv = serve()
    with sync_playwright() as p:
        br = p.chromium.launch()
        page = br.new_page(viewport={"width": 1440, "height": 900})
        errs = []
        page.on("pageerror", lambda e: errs.append(str(e)))
        page.goto(f"http://127.0.0.1:{srv.server_port}/index.html")
        page.wait_for_function("window.__bc && window.__bc.store.getState().loaded")
        page.evaluate(SEED)

        def t(label, js):
            ms = page.evaluate(f"(async () => {{ const t0 = performance.now(); await (async () => {{ {js} }})(); await {FRAME}; return performance.now() - t0; }})()")
            print(f"{label:<46}{ms:8.1f} ms")
            return ms

        A = "window.__bc.actions"; S = "window.__bc.store"
        t("load_all + first render (1000/200/50)", "await window.__bc.reload()")
        t("Tasks list, week", f"{A}.go('diary'); await {FRAME}; {A}.go('tasks')")
        t("Tasks list, scope month", f"{S}.setState({{ tscope: 'month' }})")
        t("Tasks list, scope month, sort latest", f"{S}.setState({{ tsort: 'created' }})")
        t("Calendar board, month", f"{S}.setState({{ tview: 'board' }})")
        t("Calendar board, week", f"{S}.setState({{ tscope: 'week' }})")
        page.evaluate(f"{S}.setState({{ tview: 'list', tscope: 'month', tsort: 'manual' }})")
        t("Done filter", f"{S}.setState({{ tstat: 'done' }})")
        page.evaluate(f"{S}.setState({{ tstat: 'all' }})")
        t("Diary list (50 books, 200 notes)", f"{A}.go('diary')")
        t("Diary list, expand every book", f"{S}.setState({{ expanded: Object.fromEntries({S}.getState().books.map(b => [b.id, true])) }})")
        t("Diary board", f"{S}.setState({{ dview: 'board' }})")
        t("Archive", f"{A}.go('archive')")
        page.evaluate(f"{A}.go('tasks')")
        # typing in the search box: time per key
        page.click("input[aria-label^='Search']")
        times = []
        for ch in "Task number 5":
            t0 = page.evaluate("performance.now()")
            page.keyboard.type(ch)
            page.evaluate(FRAME)
            times.append(page.evaluate("performance.now()") - t0)
        print(f"{'search: type 13 chars (per key avg / max)':<46}{sum(times) / len(times):8.1f} / {max(times):.1f} ms")
        page.evaluate(f"{A}.clearSearch()")
        # drag in the week board
        page.evaluate(f"{S}.setState({{ tview: 'board', tscope: 'week', tmonth: window.__bc.store.getState().tmonth }})")
        cards = page.locator(".card[draggable=true]")
        heads = page.locator("section[aria-label] h2")
        print("cards on week board:", cards.count())
        if cards.count() and heads.count() > 1:
            t0 = page.evaluate("performance.now()")
            cards.first.drag_to(heads.nth(heads.count() - 1))
            page.evaluate(FRAME)
            print(f"{'drag a card to another day (incl. playwright)':<46}{page.evaluate('performance.now()') - t0:8.1f} ms")
        print("page errors:", errs or "none")
        br.close()
    srv.shutdown()


main()
