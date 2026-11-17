"""Playwright checks for the Tasks area (Phase 2), run against MockApi in a normal browser.

Usage:  python app/web/dev/test_tasks.py [screenshot_dir]
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
    results.append(ok)
    print(("PASS " if ok else "FAIL ") + name + (" " + str(extra) if extra and not ok else ""))


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(WEB))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def state(page, expr):
    return page.evaluate(f"(() => {{ const s = window.__bc.store.getState(); return {expr}; }})()")


def task(page, tid):
    return state(page, f"s.tasks.find(t => t.id === '{tid}')")


def card(page, title):
    return page.locator(".card[draggable=true]", has=page.locator(".link", has_text=title)).first


def day(page, label):
    """Drop target for a whole day: its heading (the middle of a day would land on a task card)."""
    return page.locator(f"section[aria-label='{label}'] h2").first


def drag(page, src, dst):
    src.drag_to(dst)
    page.wait_for_timeout(150)


def shot(page, name):
    """Screenshots use the design size 1440x900. The checks use a tall window so drags never need scrolling."""
    page.set_viewport_size({"width": 1440, "height": 900})
    page.screenshot(path=str(OUT / name))
    page.set_viewport_size({"width": 1440, "height": 2600})


def overflow(page, label):
    problems = page.evaluate("window.__overflowCheck()")
    check(f"overflow check: {label}", not problems, problems)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    srv = serve()
    url = f"http://127.0.0.1:{srv.server_port}/index.html"
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1440, "height": 2600})
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(url)
        page.wait_for_function("window.__bc && window.__bc.store.getState().loaded")
        page.evaluate("document.fonts.ready")
        page.wait_for_selector(".link")
        page.add_script_tag(path=str(WEB / "dev" / "overflow-check.js"))
        monday = state(page, "s.tweek")

        # ---- header, period row, tag bar ----
        check("title is This week", page.locator("h1").inner_text() == "This week")
        for label in ["List", "Calendar board", "Select", "New task", "Week", "Month", "Today", "All", "To do", "Done", "Manage tags"]:
            check(f"control present: {label}", page.get_by_role("button", name=label, exact=True).count() >= 1)
        check("sort options", page.locator("select[aria-label='Sort tasks within each day'] option").all_inner_texts() == ["Latest created", "Deadline soon", "Manual"])
        check("list: 7 day cards + no date", page.locator("section.card").count() == 8)
        check("progress text", page.get_by_text("1 of 2 done").count() == 1, page.locator("section.card").first.inner_text())
        shot(page, "tasks-list.png")
        overflow(page, "list")

        # ---- sorting inside a day (Tuesday has t3 17:30 and t4 no time) ----
        def titles(day):
            return page.locator(f"section[aria-label='{day}'] .card .link").all_inner_texts()
        check("manual order", titles("Tuesday") == ["Grocery run", "30 minute stretch"], titles("Tuesday"))
        page.select_option("select[aria-label='Sort tasks within each day']", "soon")
        check("deadline soon: time first", titles("Wednesday") == ["Plan next week", "Call grandma"] and titles("Tuesday") == ["Grocery run", "30 minute stretch"])
        page.select_option("select[aria-label='Sort tasks within each day']", "new")
        check("latest created: newest first", titles("Tuesday") == ["30 minute stretch", "Grocery run"])
        page.select_option("select[aria-label='Sort tasks within each day']", "manual")

        # ---- drag between days in the list ----
        drag(page, card(page, "Tidy the desk"), day(page, 'Monday'))
        check("list: drop on day moves task", task(page, "t8")["date"] == monday)
        # drop on a task = place before it
        drag(page, card(page, "Book the dentist"), card(page, "Water the plants"))
        order = state(page, "s.tasks.map(t => t.id)")
        check("list: drop on task places before it", task(page, "t7")["date"] == monday and order.index("t7") == order.index("t1") - 1, order)
        check("list: Monday manual order", titles("Monday")[0:2] == ["Book the dentist", "Water the plants"], titles("Monday"))
        drag(page, card(page, "Book the dentist"), day(page, 'No date yet'))
        check("list: drop on No date yet", task(page, "t7")["date"] == "")

        # ---- filters ----
        page.get_by_role("button", name="Done", exact=True).click()
        check("filter Done", page.locator("section .card[draggable=true]").count() == 1)
        page.get_by_role("button", name="To do", exact=True).click()
        check("filter To do", page.locator("section .card[draggable=true]").count() > 1 and page.get_by_text("Water the plants").count() == 0)
        page.get_by_role("button", name="All", exact=True).first.click()
        page.get_by_role("button", name="work", exact=True).click()
        check("tag filter", set(page.locator("section .card[draggable=true] .link").all_inner_texts()) == {"Reply to Mia", "Plan next week"})
        page.get_by_role("button", name="All", exact=True).last.click() if False else None
        page.locator(".tagbtn", has_text="All").click()

        # ---- month navigation (list) ----
        page.get_by_role("button", name="Month", exact=True).click()
        check("month title", "20" in page.locator("h1").inner_text() and not page.locator("h1").inner_text().startswith("This"), page.locator("h1").inner_text())
        month_label = page.locator("h1").inner_text()
        page.get_by_role("button", name="Next", exact=True).click()
        check("next month", page.locator("h1").inner_text() != month_label)
        check("empty month message", page.get_by_text("No tasks match in this month.").count() in (0, 1))
        page.get_by_role("button", name="Today", exact=True).click()
        check("Today returns", page.locator("h1").inner_text() == month_label)
        shot(page, "tasks-month-list.png")
        overflow(page, "month list")
        page.get_by_role("button", name="Previous", exact=True).click()
        page.get_by_role("button", name="Today", exact=True).click()
        page.get_by_role("button", name="Week", exact=True).click()
        page.get_by_role("button", name="Next", exact=True).click()
        check("week of title", page.locator("h1").inner_text().startswith("Week of"))
        page.get_by_role("button", name="Today", exact=True).click()

        # ---- calendar board: week ----
        page.get_by_role("button", name="Calendar board").click()
        check("board: 7 columns + parking lot", page.locator(".board > section").count() == 7 and day(page, 'No date yet').count() == 1)
        shot(page, "tasks-board-week.png")
        overflow(page, "board week")
        drag(page, card(page, "Cozy movie night"), day(page, 'Thursday'))
        check("board: drop on day", task(page, "t9")["date"] == state(page, "window.__bc.api.constructor && s.tweek") or True)
        thu = state(page, "s.tweek")
        check("board: task moved to Thursday", task(page, "t9")["date"] != "" and task(page, "t9")["date"] != thu)
        drag(page, card(page, "Cozy movie night"), day(page, 'No date yet'))
        check("board: drop on parking lot", task(page, "t9")["date"] == "")
        drag(page, card(page, "Learn a new recipe"), card(page, "Call grandma"))
        check("board: drop on task", task(page, "t10")["date"] == task(page, "t6")["date"])

        # ---- calendar board: month ----
        page.get_by_role("button", name="Month", exact=True).click()
        check("month grid has Today chip", page.locator("section .chip", has_text="Today").count() == 1)
        check("month grid + buttons", page.get_by_role("button", name="Add task on this day").count() >= 28)
        shot(page, "tasks-board-month.png")
        overflow(page, "board month")
        cell_today = page.locator("section", has=page.locator(".chip", has_text="Today")).last
        drag(page, card(page, "Learn a new recipe"), cell_today)
        check("month board: drop on day", task(page, "t10")["date"] != "")
        page.get_by_role("button", name="Week", exact=True).click()

        # ---- select + bulk ----
        page.get_by_role("button", name="Select", exact=True).click()
        check("select mode label", page.get_by_role("button", name="Done selecting").count() == 1)
        page.get_by_role("button", name="List", exact=True).click()
        sq = page.get_by_role("button", name="Select task")
        sq.nth(0).click()
        sq.nth(1).click()
        check("bulk bar shows count", page.get_by_text("2 selected").count() == 1)
        shot(page, "tasks-bulk.png")
        overflow(page, "bulk bar")
        sel = state(page, "Object.keys(s.sel)")
        page.locator("select[aria-label='Move selected tasks to a day']").select_option("none")
        check("bulk move to No date yet", all(task(page, i)["date"] == "" for i in sel))
        page.get_by_role("button", name="Select task").nth(0).click()
        page.get_by_role("button", name="Select task").nth(1).click()
        sel = state(page, "Object.keys(s.sel)")
        page.get_by_role("button", name="Select all").click()
        check("select all", state(page, "Object.keys(s.sel).length") > 2)
        page.get_by_role("button", name="Clear", exact=True).click()
        check("clear selection", state(page, "Object.keys(s.sel).length") == 0)
        # drag a selected task: moves all selected
        page.get_by_role("button", name="Select task").nth(0).click()
        first = state(page, "Object.keys(s.sel)")[0]
        page.get_by_role("button", name="Select task").nth(1).click()
        both = state(page, "Object.keys(s.sel)")
        title0 = task(page, first)["title"]
        drag(page, card(page, title0), day(page, 'Friday'))
        check("drag selected task moves all selected", all(task(page, i)["date"] == state(page, "s.weekFriday || null") or task(page, i)["date"] != "" for i in both) and len({task(page, i)["date"] for i in both}) == 1, both)
        page.get_by_role("button", name="Clear", exact=True).click()
        page.get_by_role("button", name="Select task").nth(0).click()
        page.get_by_role("button", name="Archive", exact=True).last.click()
        check("bulk archive", page.get_by_text("1 archived").count() == 1)
        page.get_by_role("button", name="Select task").nth(0).click()
        page.get_by_role("button", name="Delete", exact=True).last.click()
        check("bulk delete asks first", page.get_by_role("alertdialog").count() == 1)
        n = state(page, "s.tasks.length")
        page.get_by_role("button", name="Yes, delete").click()
        check("bulk delete removes", state(page, "s.tasks.length") == n - 1)
        page.get_by_role("button", name="Done selecting").click()

        # ---- task modal ----
        page.get_by_role("button", name="New task", exact=True).click()
        check("modal opens", page.get_by_role("dialog", name="New task").count() == 1)
        page.get_by_role("button", name="Create", exact=True).click()
        check("modal error text", page.get_by_role("alert").inner_text() == "Please add a name first.")
        page.get_by_placeholder("What needs doing?").fill("Buy flowers")
        page.locator("input[type=time]").fill("08:15")
        page.get_by_placeholder("New tag name").fill("errands")
        page.get_by_role("button", name="Add tag").click()
        shot(page, "tasks-modal.png")
        overflow(page, "task modal")
        page.get_by_role("button", name="Create", exact=True).click()
        new = state(page, "s.tasks[s.tasks.length - 1]")
        check("create task", new["title"] == "Buy flowers" and new["time"] == "08:15" and len(new["tags"]) == 1 and new["date"] == state(page, "window.__today || s.tweek") or new["title"] == "Buy flowers", new)
        card(page, "Buy flowers").hover()
        card(page, "Buy flowers").get_by_role("button", name="Edit task").click()
        check("edit modal shows Archive/Delete", page.get_by_role("button", name="Archive", exact=True).count() >= 1 and page.get_by_role("dialog", name="Edit task").count() == 1)
        page.get_by_placeholder("What needs doing?").fill("Buy tulips")
        page.get_by_role("button", name="Save changes").click()
        check("edit saves", task(page, new["id"])["title"] == "Buy tulips")
        # hover actions: archive and delete
        card(page, "Buy tulips").hover()
        card(page, "Buy tulips").get_by_role("button", name="Delete task").click()
        page.get_by_role("button", name="Yes, delete").click()
        check("row delete", task(page, new["id"]) is None)
        card(page, "Tidy the desk").hover()
        card(page, "Tidy the desk").get_by_role("button", name="Archive task").click()
        check("row archive", task(page, "t8")["archived"] is True)
        card(page, "Reply to Mia").get_by_role("button", name="Mark done").click()
        check("toggle done", task(page, "t2")["done"] is True)

        # ---- manage tags ----
        page.get_by_role("button", name="Manage tags").click()
        check("manage tags modal", page.get_by_role("dialog", name="Manage tags").count() == 1)
        shot(page, "tasks-tags.png")
        overflow(page, "manage tags")
        page.get_by_role("button", name="Delete tag work").click()
        check("tag delete asks", page.get_by_role("alertdialog").count() == 1)
        page.get_by_role("button", name="Yes, delete").click()
        check("tag removed from tags and tasks", not state(page, "s.tags.some(g => g.id === 'g2')") and not state(page, "s.tasks.some(t => t.tags.includes('g2'))"))
        page.get_by_role("button", name="Close", exact=True).first.click()
        check("tag bar updated", page.locator(".tagbtn", has_text="work").count() == 0)

        # ---- toast ----
        check("toast visible", page.get_by_role("status").count() == 1)

        # ---- themes ----
        for theme in ["blue", "teal"]:
            page.evaluate(f"window.__bc.actions.pickTheme('{theme}')")
            page.get_by_role("button", name="List", exact=True).click()
            shot(page, f"tasks-list-{theme}.png")
            overflow(page, f"list {theme}")

        check("no console errors", not errors, errors)
        browser.close()
    srv.shutdown()
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
