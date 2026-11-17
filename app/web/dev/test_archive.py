"""Playwright checks for Phase 4: archive, search, breadcrumbs, auto-archive. Runs against MockApi in a browser.

Usage:  python app/web/dev/test_archive.py [screenshot_dir]
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


def api(page, call):
    return page.evaluate(f"(async () => {{ const a = window.__bc.api; return await {call}; }})()")


def open_page(browser, url, clock=None):
    page = browser.new_page(viewport={"width": 1440, "height": 2600})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    if clock:
        page.clock.install(time=clock)
    page.goto(url)
    page.wait_for_function("window.__bc && window.__bc.store.getState().loaded")
    page.evaluate("document.fonts.ready")
    page.add_script_tag(path=str(WEB / "dev" / "overflow-check.js"))
    return page, errors


def overflow(page, label):
    problems = page.evaluate("window.__overflowCheck()")
    check(f"overflow check: {label}", not problems, problems)


def shot(page, name):
    page.set_viewport_size({"width": 1440, "height": 900})
    page.screenshot(path=str(OUT / name))
    page.set_viewport_size({"width": 1440, "height": 2600})


def btn(page, name, exact=True):
    return page.get_by_role("button", name=name, exact=exact)


def sections(page):
    return page.locator("main section[aria-label] h2").all_inner_texts()


def rules_checks(page):
    """cutoffDate and autoArchiveIds at the 3-month edge, month ends included."""
    cut = lambda d: page.evaluate(f"import('./js/rules.js').then(m => m.cutoffDate('{d}'))")
    table = {
        "2026-11-17": "2026-08-17",
        "2026-05-31": "2026-02-28",   # Feb has no 31st: clamp to the last day
        "2024-05-31": "2024-02-29",   # leap year
        "2026-03-31": "2025-12-31",   # crosses the year
        "2026-01-31": "2025-10-31",
        "2026-08-31": "2026-05-31",
        "2026-11-30": "2026-08-30",
        "2026-12-31": "2026-09-30",   # Sep has 30 days
        "2026-02-28": "2025-11-28",
        "2027-03-01": "2026-12-01",
    }
    for today, want in table.items():
        got = cut(today)
        check(f"cutoff of {today} = {want}", got == want, got)
    ids = page.evaluate("""import('./js/rules.js').then(m => {
      const t = (id, date, extra) => ({ id, date, archived: false, ...extra });
      const tasks = [t('a', '2026-08-16'), t('b', '2026-08-17'), t('c', '2026-08-18'), t('d', ''), t('e', '2026-01-01', { keep: true }),
                     t('f', '2026-01-01', { archived: true }), t('g', '2025-12-31')];
      return m.autoArchiveIds(tasks, '2026-11-17');
    })""")
    check("auto-archive: older than cutoff only; cutoff day, newer, no date, keep, archived stay", ids == ["a", "g"], ids)
    ids = page.evaluate("""import('./js/rules.js').then(m => {
      const t = (id, date) => ({ id, date, archived: false });
      return m.autoArchiveIds([t('a', '2026-02-27'), t('b', '2026-02-28'), t('c', '2026-03-01')], '2026-05-31');
    })""")
    check("month end: today May 31, only dates before Feb 28 are archived", ids == ["a"], ids)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srv = serve()
    url = f"http://127.0.0.1:{srv.server_port}/index.html"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page, errors = open_page(browser, url)

        rules_checks(page)

        # ---- auto-archive through the api, with real dates around the edge ----
        page.evaluate("""(async () => {
          const { cutoffDate } = await import('./js/rules.js'); const { todayISO, addDays } = await import('./js/lib/dates.js');
          const cut = cutoffDate(todayISO()); const a = window.__bc.api;
          window.__edge = {
            before: (await a.create_task({ title: 'Edge before', date: addDays(cut, -1) })).id,
            on: (await a.create_task({ title: 'Edge on', date: cut })).id,
            after: (await a.create_task({ title: 'Edge after', date: addDays(cut, 1) })).id,
            none: (await a.create_task({ title: 'Edge none', date: '' })).id
          };
        })()""")
        r = api(page, "a.run_maintenance()")
        edge = page.evaluate("window.__edge")
        check("api auto-archive: day before the cutoff in, cutoff day out", edge["before"] in r["autoArchived"] and edge["on"] not in r["autoArchived"], r)
        d = api(page, "a.load_all()")
        by = {t["id"]: t for t in d["tasks"]}
        check("edge: day before cutoff archived + auto", by[edge["before"]]["archived"] and by[edge["before"]]["auto"])
        check("edge: cutoff day / newer / no date stay", not any(by[edge[k]]["archived"] for k in ("on", "after", "none")))
        check("sample task t12 (125 days old) auto-archived at start", state(page, "s.tasks.find(t => t.id === 't12')").get("auto") is True)
        check("sample task t14 (20 days old) not archived", state(page, "s.tasks.find(t => t.id === 't14').archived") is False)
        page.close()

        # ---- fresh page for the UI flow ----
        early = browser.new_page(viewport={"width": 1440, "height": 900})
        early.goto(url)
        early.wait_for_selector("[role=status]")
        check("start toast says how many were archived", early.locator("[role=status]").inner_text() == "1 task older than 3 months was archived")
        early.close()
        page, errors = open_page(browser, url)

        # ---- archive page ----
        page.click(".side >> text=Archive")
        check("archive title", page.locator("h1").inner_text() == "Archive")
        check("archive sections", sections(page) == ["Tasks 2", "Notes 1"], sections(page))
        check("subtitle count", page.get_by_text("3 items waiting").count() == 1)
        check("sidebar chip shows 3", page.locator(".side .nav", has_text="Archive").locator(".chip").inner_text() == "3")
        check("auto row text", page.get_by_text("Archived automatically (older than 3 months)").count() == 1)
        check("manual archived task has no auto text", page.locator(".card", has_text="Return library books").get_by_text("Archived automatically").count() == 0)
        check("row buttons", btn(page, "Restore").count() == 3 and btn(page, "Delete forever").count() == 3)
        check("selection squares", page.get_by_role("button", name="Select item").count() == 3)
        check("restore selected disabled when nothing selected", btn(page, "Restore selected").is_disabled() and btn(page, "Delete selected").is_disabled())
        shot(page, "archive.png")
        overflow(page, "archive")

        # select all / clear selection / restore selected
        btn(page, "Select all").click()
        check("select all selects every row", state(page, "Object.keys(s.sel).length") == 3)
        check("label becomes Clear selection", btn(page, "Clear selection").count() == 1)
        btn(page, "Clear selection").click()
        check("clear selection", state(page, "Object.keys(s.sel).length") == 0)

        # restore one row: task gets keep=true, auto=false
        page.locator(".card", has_text="Renew bus pass").get_by_role("button", name="Restore").click()
        t12 = state(page, "s.tasks.find(t => t.id === 't12')")
        check("restore task: archived false, keep true, auto false", t12["archived"] is False and t12["keep"] is True and not t12["auto"], t12)
        check("restore toast", page.get_by_text("Restored").count() >= 1)
        check("archive count 2", page.locator(".side .nav", has_text="Archive").locator(".chip").inner_text() == "2")
        # a restored task is never auto-archived again
        api(page, "a.run_maintenance()")
        check("restored task survives maintenance", api(page, "a.load_all().then(d => d.tasks.find(t => t.id === 't12').archived)") is False)

        # restore a note restores its book (archive the book first)
        api(page, "a.archive_book('b1')")
        page.evaluate("window.__bc.api.load_all().then(d => window.__bc.store.setState({ books: d.books }))")
        check("archived book + archived note appear", sections(page) == ["Tasks 1", "Notes 1", "Books 1"], sections(page))
        page.locator(".card", has_text="Draft: October recap").get_by_role("button", name="Restore").click()
        check("restoring a note restores its book", state(page, "s.books.find(b => b.id === 'b1').archived") is False)
        check("note restored", state(page, "s.notes.find(n => n.id === 'n7').archived") is False)
        check("book chip count in sidebar still 4", page.locator(".side .nav", has_text="Diary").locator(".chip").inner_text() == "4")

        # archive a book: its notes disappear from the diary (they keep their own flags)
        page.click(".side >> text=Diary")
        page.get_by_role("button", name="Archive book").first.click()
        n_flags = state(page, "s.notes.filter(n => n.bookId === 'b2').map(n => n.archived)")
        check("archiving a book leaves note flags alone", n_flags == [False, False], n_flags)
        check("notes of an archived book are hidden in the diary", page.get_by_text("The floating library").count() == 0)

        # delete forever with confirm
        page.click(".side >> text=Archive")
        check("archived book listed with its note count", page.get_by_text("2 notes inside").count() == 1)
        page.locator(".card", has_text="Dream Journal").get_by_role("button", name="Delete forever").click()
        check("delete asks first", page.get_by_role("alertdialog").count() == 1 and page.get_by_text("This will be deleted forever. It cannot be undone.").count() == 1)
        btn(page, "Keep it").click()
        check("keep it: nothing deleted", state(page, "s.books.some(b => b.id === 'b2')"))
        page.locator(".card", has_text="Dream Journal").get_by_role("button", name="Delete forever").click()
        btn(page, "Yes, delete").click()
        check("deleting a book deletes its notes", state(page, "!s.books.some(b => b.id === 'b2') && !s.notes.some(n => n.bookId === 'b2')"))
        check("delete toast", page.get_by_text("Deleted").count() >= 1)

        # delete a tag removes it from all items
        api(page, "a.delete_tag('g5')")
        d = api(page, "a.load_all()")
        check("delete tag removes it everywhere (api)", not any("g5" in x["tags"] for x in d["tasks"] + d["notes"]) and not any(g["id"] == "g5" for g in d["tags"]))

        # restore selected / delete selected / restore all / delete all
        for tid in ("t1", "t2", "t3", "t4"):
            api(page, f"a.archive_task('{tid}')")
        api(page, "a.archive_note('n1')")
        page.evaluate("window.__bc.api.load_all().then(d => window.__bc.store.setState({ tasks: d.tasks, notes: d.notes, books: d.books }))")
        check("archive lists new items", sections(page) == ["Tasks 5", "Notes 1"], sections(page))
        page.get_by_role("button", name="Select item").nth(0).click()
        page.get_by_role("button", name="Select item").nth(1).click()
        check("restore/delete selected enabled", btn(page, "Restore selected").is_enabled() and btn(page, "Delete selected").is_enabled())
        btn(page, "Restore selected").click()
        check("restore selected restores 2", sections(page) == ["Tasks 3", "Notes 1"], sections(page))
        page.get_by_role("button", name="Select item").nth(0).click()
        btn(page, "Delete selected").click()
        check("delete selected confirm text", page.get_by_text("Delete 1 selected item forever? This cannot be undone.").count() == 1)
        btn(page, "Yes, delete").click()
        check("delete selected removes 1", sections(page) == ["Tasks 2", "Notes 1"], sections(page))
        btn(page, "Restore all").click()
        check("restore all: archive empty", state(page, "[...s.tasks, ...s.notes, ...s.books].filter(x => x.archived).length") == 0)
        check("empty state with castle", page.get_by_text("The archive is empty").count() == 1 and page.locator("main svg[width='56']").count() == 1)
        check("empty: bulk buttons disabled", btn(page, "Restore all").is_disabled() and btn(page, "Delete all").is_disabled() and btn(page, "Select all").is_disabled())
        shot(page, "archive-empty.png")
        overflow(page, "archive empty")
        for tid in ("t1", "t2"):
            api(page, f"a.archive_task('{tid}')")
        api(page, "a.archive_book('b3')")
        page.evaluate("window.__bc.api.load_all().then(d => window.__bc.store.setState({ tasks: d.tasks, notes: d.notes, books: d.books }))")
        btn(page, "Delete all").click()
        check("delete all confirm text", page.get_by_text("Empty the archive? All 3 items will be deleted forever.").count() == 1)
        btn(page, "Keep it").click()
        check("delete all: cancel keeps items", state(page, "[...s.tasks, ...s.notes, ...s.books].filter(x => x.archived).length") == 3)
        btn(page, "Delete all").click()
        btn(page, "Yes, delete").click()
        check("delete all removes every archived item", state(page, "[...s.tasks, ...s.notes, ...s.books].filter(x => x.archived).length") == 0 and not state(page, "s.books.some(b => b.id === 'b3')"))
        check("delete all removes the book's notes", not state(page, "s.notes.some(n => n.bookId === 'b3')"))
        check("sidebar chip shows 0", page.locator(".side .nav", has_text="Archive").locator(".chip").inner_text() == "0")
        check("store matches api after bulk ops", api(page, "a.load_all().then(d => d.tasks.length + ':' + d.notes.length + ':' + d.books.length)") == state(page, "s.tasks.length + ':' + s.notes.length + ':' + s.books.length"))
        page.close()

        # ---- search ----
        page, errors = open_page(browser, url)
        box = page.get_by_label("Search all tasks, notes and tags")

        def search(text):
            box.fill(text)
            page.wait_for_timeout(50)

        search("plan")
        check("search title", page.locator("h1").inner_text() == "Search results")
        heads = sections(page)
        check("search finds tasks by title", any(h.startswith("Tasks") for h in heads) and page.get_by_text("Plan next week").count() == 1, heads)
        check("search: crumbs", page.locator("nav[aria-label=Breadcrumb] button").all_inner_texts() == ["Search", '"plan"'])
        shot(page, "search.png")
        overflow(page, "search")
        search("pancakes")
        check("search finds note by text", sections(page) == ["Notes 1"] and page.get_by_text("A slow Sunday").count() == 1, sections(page))
        search("dream")
        check("search finds tag + book name + notes", sections(page) == ["Notes 2", "Books 1"], sections(page))
        search("Idea Garden")
        check("search by book name finds the book and its note via book name", sections(page) == ["Notes 1", "Books 1"], sections(page))
        search("self-care")
        check("search by tag name: tasks and notes", sections(page) == ["Tasks 4", "Notes 1"], sections(page))
        search("recap")
        check("archived items are excluded", page.get_by_text("Nothing found. Try another word or tag.").count() == 1 and sections(page) == [])
        search("bus pass")
        check("archived (auto) task excluded", page.get_by_text("Nothing found").count() == 1)
        search("zzz")
        check("empty result text and count", page.get_by_text("0 matches across tasks, notes and books").count() == 1)
        # tag filter combines with search
        page.evaluate("window.__bc.store.setState({ tagF: 'g3' })")
        search("e")
        titles = page.locator("main section[aria-label] button.card > span:first-child > span:first-child").all_inner_texts()
        check("tag filter combines with the text", sorted(titles) == ["Grocery run", "Tidy the desk", "Tiny desk garden", "Water the plants"], titles)
        check("tag filter hides books", not any(h.startswith("Books") for h in sections(page)))
        page.evaluate("window.__bc.store.setState({ tagF: null })")

        # clicking a result
        search("Grocery")
        page.get_by_role("button", name="Grocery run").click()
        page.wait_for_timeout(300)
        check("click task result opens the task modal", page.get_by_role("dialog").count() == 1 and state(page, "s.modal.kind === 'task' && s.modal.id === 't3'"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        check("Esc closes the modal first, search stays", page.get_by_role("dialog").count() == 0 and state(page, "s.q") == "Grocery")
        search("slow")
        page.get_by_role("button", name="A slow Sunday").click()
        page.wait_for_timeout(300)
        check("click note result opens the note modal", state(page, "s.modal.kind === 'note' && s.modal.id === 'n1'"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(150)
        search("Book Club")
        page.locator("main section[aria-label=Books] button.card").click()
        check("click book result opens it in Diary board", state(page, "s.area === 'diary' && s.dview === 'board' && s.openBook === 'b4' && s.q === ''"))
        check("book crumbs: Diary > Board > Book Club", page.locator("nav[aria-label=Breadcrumb] button").all_inner_texts() == ["Diary", "Board", "Book Club"], page.locator("nav[aria-label=Breadcrumb] button").all_inner_texts())

        # clear button and Esc
        search("plan")
        page.get_by_role("button", name="Clear search").click()
        check("clear button clears search", state(page, "s.q") == "" and page.locator("h1").inner_text() != "Search results")
        search("plan")
        box.press("Escape")
        check("Esc clears search", state(page, "s.q") == "")
        page.keyboard.press("Escape")

        # ---- breadcrumbs ----
        def crumbs():
            return page.locator("nav[aria-label=Breadcrumb] button").all_inner_texts()

        page.click(".side >> text=Tasks")
        check("tasks crumbs", crumbs() == ["Tasks", "Week list"], crumbs())
        page.get_by_role("button", name="Calendar board").click()
        check("tasks crumbs: Calendar board", crumbs() == ["Tasks", "Calendar board"], crumbs())
        page.get_by_role("button", name="Select", exact=True).click()
        page.get_by_role("button", name="Select task").first.click()
        page.locator("nav[aria-label=Breadcrumb] button", has_text="Calendar board").click()
        check("Tasks > current crumb clears selection and select mode", state(page, "Object.keys(s.sel).length === 0 && !s.selMode"))
        page.locator("nav[aria-label=Breadcrumb] button", has_text="Tasks").click()
        check("Tasks crumb goes to the Tasks area", state(page, "s.area") == "tasks")
        page.click(".side >> text=Diary")
        page.get_by_role("group", name="Diary view").get_by_role("button", name="List", exact=True).click()
        check("diary crumbs", crumbs() == ["Diary", "List"], crumbs())
        page.get_by_role("group", name="Diary view").get_by_role("button", name="Board", exact=True).click()
        page.get_by_role("button", name="Open book Idea Garden").click()
        check("book open crumbs", crumbs() == ["Diary", "Board", "Idea Garden"], crumbs())
        page.locator("nav[aria-label=Breadcrumb] button", has_text="Board").click()
        check("Board crumb closes the book", state(page, "s.openBook") is None and crumbs() == ["Diary", "Board"], crumbs())
        page.get_by_role("button", name="Open book Idea Garden").click()
        page.locator("nav[aria-label=Breadcrumb] button", has_text="Diary").click()
        check("Diary crumb: area root, book closed", state(page, "s.area === 'diary' && s.openBook === null"))
        page.get_by_role("button", name="Open book Idea Garden").click()
        page.locator("nav[aria-label=Breadcrumb] button", has_text="Idea Garden").click()
        check("book crumb (current) stays on the book", state(page, "s.openBook") == "b3")
        page.click(".side >> text=Archive")
        check("archive crumbs", crumbs() == ["Archive"], crumbs())
        page.locator("nav[aria-label=Breadcrumb] button", has_text="Archive").click()
        check("Archive crumb stays in Archive", state(page, "s.area") == "archive")
        search("plan")
        page.locator("nav[aria-label=Breadcrumb] button", has_text='"plan"').click()
        check("search term crumb stays in search", state(page, "s.q") == "plan")
        page.locator("nav[aria-label=Breadcrumb] button", has_text="Search").click()
        check("Search crumb clears the search", state(page, "s.q") == "")
        page.close()

        # ---- midnight: the timer runs auto-archive while the app is open ----
        page, errors = open_page(browser, url, clock="2026-11-17T23:59:30")
        created = api(page, "a.create_task({ title: 'Edge midnight', date: '2026-08-17' })")
        page.evaluate("window.__bc.api.load_all().then(d => window.__bc.store.setState({ tasks: d.tasks }))")
        tid = created["id"]
        check("before midnight (cutoff 2026-08-17) the task dated on the cutoff stays", state(page, f"s.tasks.find(t => t.id === '{tid}').archived") is False)
        page.clock.run_for(32 * 1000)
        page.wait_for_timeout(200)
        check("after midnight (cutoff 2026-08-18) the same task is archived", state(page, f"s.tasks.find(t => t.id === '{tid}').archived") is True)
        check("midnight: marked auto", state(page, f"s.tasks.find(t => t.id === '{tid}').auto") is True)
        check("midnight toast", page.get_by_text("1 task older than 3 months was archived").count() >= 1)
        page.close()

        # ---- after saving a task: maintenance runs ----
        page, errors = open_page(browser, url)
        page.click(".side >> text=Tasks")
        page.get_by_role("button", name="New task").click()
        page.get_by_placeholder("What needs doing?").fill("Old thing")
        page.locator("input[type=date]").fill("2026-01-05")
        page.get_by_role("button", name="Create", exact=True).click()
        page.wait_for_timeout(200)
        old = state(page, "s.tasks.find(t => t.title === 'Old thing')")
        check("saving an old task auto-archives it", old and old["archived"] and old["auto"], old)
        check("toast after saving", page.get_by_text("task older than 3 months was archived").count() >= 1)
        page.close()

        # ---- fresh load: all screens clean ----
        page, errors = open_page(browser, url)
        for area in ("Tasks", "Diary", "Archive"):
            page.click(f".side >> text={area}")
            overflow(page, area)
        check("no console or page errors", not errors, errors)
        browser.close()
    srv.shutdown()
    print(f"{sum(results)}/{len(results)} checks passed")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
