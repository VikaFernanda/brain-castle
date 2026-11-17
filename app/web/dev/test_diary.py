"""Playwright checks for the Diary area (Phase 3), run against MockApi in a normal browser.

Usage:  python app/web/dev/test_diary.py [screenshot_dir]
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

    handler = functools.partial(Quiet, directory=str(WEB))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def state(page, expr):
    return page.evaluate(f"(() => {{ const s = window.__bc.store.getState(); return {expr}; }})()")


def note(page, nid):
    return state(page, f"s.notes.find(n => n.id === '{nid}')")


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


def book(page, name):
    return page.locator(f"section.card[aria-label='{name}']")


def book_head(page, name):
    return book(page, name).locator("div[draggable=true]").first


def lnote(page, title):
    """A note row in the list view."""
    return page.locator("section.card div[draggable=true]", has=page.locator(".link", has_text=title)).last


def ncard(page, title):
    """A note card in the open-book view."""
    return page.locator("article.card", has=page.locator(".link", has_text=title))


def books_shown(page):
    return page.locator("section.card[aria-label]").evaluate_all("els => els.map(e => e.getAttribute('aria-label'))")


def notes_in(page, name):
    return page.locator(f"section.card[aria-label='{name}'] div[draggable=true] div > button.link").all_inner_texts()


def expand(page, name):
    if not notes_in(page, name) and book(page, name).get_by_text("No notes in this book yet").count() == 0:
        book(page, name).get_by_role("button", name="Show or hide notes").click()


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
        page.add_script_tag(path=str(WEB / "dev" / "overflow-check.js"))
        page.click(".side >> text=Diary")

        # ---- header and controls ----
        check("title Diary", page.locator("h1").inner_text() == "Diary")
        check("subtitle", page.get_by_text("4 books and 6 notes").count() == 1)
        for label in ["List", "Board", "Select", "New book", "New note", "All time", "Month", "Week", "Today", "Manage tags", "Previous", "Next"]:
            check(f"control present: {label}", page.get_by_role("button", name=label, exact=True).count() >= 1)
        sorts = ["Latest created", "Date soon", "Manual"]
        check("book sort options", page.locator("select[aria-label='Sort books'] option").all_inner_texts() == sorts)
        check("note sort options", page.locator("select[aria-label='Sort notes inside books'] option").all_inner_texts() == sorts)

        # ---- list: grouped by month, then week; undated under No date ----
        heads = page.locator("h2").all_inner_texts()
        check("month headings", heads == ["November 2026", "October 2026", "No date"], heads)
        check("week headings", page.get_by_text("Week of Oct 26 to Nov 1").count() == 1 and page.get_by_text("Week of Oct 19 to Oct 25").count() == 1)
        check("book order in list", books_shown(page) == ["Dream Journal", "Book Club", "Daily Diary", "Idea Garden"], books_shown(page))
        check("Daily Diary open by default", page.get_by_text("A slow Sunday").count() == 1 and page.get_by_text("The floating library").count() == 0)
        shot(page, "diary-list.png")
        overflow(page, "diary list")

        # ---- open and close a book ----
        toggle = book(page, "Dream Journal").get_by_role("button", name="Show or hide notes")
        toggle.click()
        check("book opens", page.get_by_text("The floating library").count() == 1)
        check("note count label", book(page, "Dream Journal").get_by_text("2 notes").count() == 1)
        toggle.click()
        check("book closes", page.get_by_text("The floating library").count() == 0)

        # ---- drag a note onto a book (list) ----
        expand(page, "Book Club")
        drag(page, lnote(page, "A slow Sunday"), book_head(page, "Book Club"))
        check("list: drop on book moves note", note(page, "n1")["bookId"] == "b4")
        # drag a note onto a note = join its book, sit before it
        drag(page, lnote(page, "Small wins"), lnote(page, "Chapter 3 thoughts"))
        order = state(page, "s.notes.map(n => n.id)")
        check("list: drop on note joins its book and sits before it", note(page, "n2")["bookId"] == "b4" and order.index("n2") == order.index("n6") - 1, order)
        check("list: Book Club order", notes_in(page, "Book Club") == ["A slow Sunday", "Small wins", "Chapter 3 thoughts"], notes_in(page, "Book Club"))

        # ---- drag a book to reorder (manual) ----
        drag(page, book_head(page, "Idea Garden"), book_head(page, "Daily Diary"))
        ids = state(page, "s.books.map(b => b.id)")
        check("list: dragging a book reorders it", ids.index("b3") == ids.index("b1") - 1, ids)
        check("list: shown order follows", books_shown(page)[2:] == ["Idea Garden", "Daily Diary"], books_shown(page))

        # ---- sort books ----
        page.select_option("select[aria-label='Sort books']", "new")
        check("books latest created: newest first inside a group", books_shown(page)[2:] == ["Idea Garden", "Daily Diary"] or books_shown(page)[2:] == ["Daily Diary", "Idea Garden"])
        undated = state(page, "[...s.books].filter(b => !b.date).sort((a, b) => b.created - a.created).map(b => b.name)")
        check("books latest created", books_shown(page)[2:] == undated, [books_shown(page), undated])
        page.select_option("select[aria-label='Sort books']", "soon")
        check("books date soon: past dates, most recent first", books_shown(page)[:2] == ["Dream Journal", "Book Club"], books_shown(page))
        page.select_option("select[aria-label='Sort books']", "manual")
        check("books manual keeps dragged order", books_shown(page)[2:] == ["Idea Garden", "Daily Diary"], books_shown(page))

        # ---- sort notes (Book Club now has n1 2026-11-15, n2 2026-11-12, n6 2026-10-28) ----
        page.select_option("select[aria-label='Sort notes inside books']", "new")
        check("notes latest created", notes_in(page, "Book Club") == ["Chapter 3 thoughts", "Small wins", "A slow Sunday"], notes_in(page, "Book Club"))
        page.select_option("select[aria-label='Sort notes inside books']", "soon")
        check("notes date soon: past dates, most recent first", notes_in(page, "Book Club") == ["A slow Sunday", "Small wins", "Chapter 3 thoughts"], notes_in(page, "Book Club"))
        page.select_option("select[aria-label='Sort notes inside books']", "manual")
        check("notes manual", notes_in(page, "Book Club") == ["A slow Sunday", "Small wins", "Chapter 3 thoughts"], notes_in(page, "Book Club"))
        # undated notes come last under "soon"
        drag(page, lnote(page, "Small wins"), book_head(page, "Dream Journal"))
        expand(page, "Dream Journal")
        page.select_option("select[aria-label='Sort notes inside books']", "soon")
        check("notes date soon: undated last", notes_in(page, "Dream Journal") == ["Small wins", "The floating library", "Purple ocean"] or notes_in(page, "Dream Journal")[-1] == "Purple ocean", notes_in(page, "Dream Journal"))
        page.select_option("select[aria-label='Sort notes inside books']", "manual")

        # ---- period filters ----
        month_now = state(page, "s.bmonth")
        page.get_by_role("button", name="Month", exact=True).click()
        in_month = state(page, "s.books.filter(b => !b.date || b.date.slice(0, 7) === s.bmonth).map(b => b.name).sort()")
        check("month filter: undated stay, dated books of other months go", sorted(books_shown(page)) == in_month and len(in_month) == 3, [books_shown(page), in_month])
        page.get_by_role("button", name="Previous", exact=True).click()
        check("previous month", state(page, "s.bmonth") != month_now)
        check("October shows Book Club", "Book Club" in books_shown(page) and "Dream Journal" not in books_shown(page), books_shown(page))
        page.get_by_role("button", name="Today", exact=True).click()
        check("Today returns to this month", state(page, "s.bmonth") == month_now)
        page.get_by_role("button", name="Week", exact=True).click()
        check("week filter: no dated book this week", books_shown(page) == ["Idea Garden", "Daily Diary"], books_shown(page))
        page.get_by_role("button", name="Previous", exact=True).click()
        check("week arrows move the week", state(page, "s.bweek") < state(page, "window.__bc.store.getState().tweek"))
        page.get_by_role("button", name="Today", exact=True).click()
        page.get_by_role("button", name="All time", exact=True).click()
        check("all time shows every book", len(books_shown(page)) == 4)

        # ---- board: covers ----
        page.get_by_role("button", name="Board", exact=True).click()
        covers = page.locator("button[aria-label^='Open book']")
        check("board: 4 covers", covers.count() == 4)
        check("board: cover peeks note titles", page.locator(".card[draggable=true]", has=page.get_by_role("button", name="Open book Dream Journal")).get_by_text("Purple ocean").count() == 1)
        shot(page, "diary-board.png")
        overflow(page, "diary board")

        # ---- drag on covers: note-free book reorder ----
        cv = lambda n: page.locator(".card[draggable=true]", has=page.get_by_role("button", name=f"Open book {n}"))
        drag(page, cv("Daily Diary"), cv("Idea Garden"))
        ids = state(page, "s.books.map(b => b.id)")
        check("board: dragging a cover reorders books", ids.index("b1") == ids.index("b3") - 1, ids)

        # ---- open a book, close it ----
        page.get_by_role("button", name="Open book Dream Journal").click()
        check("open book: title", page.locator("h1").inner_text() == "Dream Journal")
        check("open book: All books button", page.get_by_role("button", name="All books").count() == 1)
        check("open book: other books row", page.get_by_text("Drag a note onto a book to move it:").count() == 1)
        check("open book: note cards", page.locator("article.card").count() == 3, page.locator("article.card").count())
        check("open book: breadcrumb", page.locator("nav[aria-label=Breadcrumb] button").all_inner_texts() == ["Diary", "Board", "Dream Journal"])
        shot(page, "diary-open-book.png")
        overflow(page, "open book")
        chip = page.locator("div[style*='dashed']", has_text="Idea Garden")
        drag(page, ncard(page, "Purple ocean"), chip)
        check("board: drop on book chip moves note", note(page, "n4")["bookId"] == "b3")
        drag(page, ncard(page, "The floating library"), ncard(page, "Small wins"))
        order = state(page, "s.notes.map(n => n.id)")
        check("board: drop on note card sits before it", order.index("n3") == order.index("n2") - 1, order)
        page.get_by_role("button", name="All books").click()
        check("close book", page.locator("h1").inner_text() == "Diary" and page.locator("button[aria-label^='Open book']").count() == 4)

        # ---- select mode and bulk (list) ----
        page.get_by_role("button", name="List", exact=True).click()
        page.get_by_role("button", name="Select", exact=True).click()
        page.get_by_role("button", name="Select book").first.click()
        check("book selected: no move select", page.locator("select[aria-label='Move selected notes to a book']").count() == 0 and page.get_by_text("1 selected").count() == 1)
        page.get_by_role("button", name="Clear", exact=True).click()
        for b in ["Dream Journal", "Book Club", "Idea Garden"]:
            expand(page, b)
        sel_ids = state(page, "s.notes.filter(n => n.bookId === 'b3' && !n.archived).map(n => n.id)")
        sqs = page.locator("section[aria-label='Idea Garden'] button[aria-label='Select note']")
        for i in range(sqs.count()):
            sqs.nth(i).click()
        check("notes selected", len(sel_ids) >= 2 and state(page, "Object.keys(s.sel).length") == len(sel_ids), sel_ids)
        shot(page, "diary-bulk.png")
        overflow(page, "bulk bar")
        page.locator("select[aria-label='Move selected notes to a book']").select_option("b1")
        check("bulk move to book", all(note(page, i)["bookId"] == "b1" for i in sel_ids))
        check("bulk move clears selection", state(page, "Object.keys(s.sel).length") == 0)

        # dragging a selected note moves all selected notes
        expand(page, "Daily Diary")
        sqs = page.locator("section[aria-label='Daily Diary'] button[aria-label='Select note']")
        sqs.nth(0).click()
        sqs.nth(1).click()
        both = state(page, "Object.keys(s.sel)")
        drag(page, lnote(page, note(page, both[0])["title"]), book_head(page, "Book Club"))
        check("drag of a selected note moves every selected note", all(note(page, i)["bookId"] == "b4" for i in both), both)
        page.get_by_role("button", name="Clear", exact=True).click()

        # select all, bulk archive and delete
        page.get_by_role("button", name="Select book").first.click()
        page.get_by_role("button", name="Select all").click()
        check("select all picks every visible book and note", state(page, "Object.keys(s.sel).length") >= 4)
        page.get_by_role("button", name="Clear selection").click()
        check("clear selection", state(page, "Object.keys(s.sel).length") == 0)
        page.get_by_role("button", name="Select note").first.click()
        page.get_by_role("button", name="Archive", exact=True).last.click()
        check("bulk archive", page.get_by_text("1 archived").count() == 1 and state(page, "s.notes.filter(n => n.archived).length") == 2)
        page.get_by_role("button", name="Select book").first.click()
        page.get_by_role("button", name="Delete", exact=True).last.click()
        check("bulk delete asks first", page.get_by_role("alertdialog").count() == 1)
        nb = state(page, "s.books.length")
        page.get_by_role("button", name="Yes, delete").click()
        check("bulk delete removes the book and its notes", state(page, "s.books.length") == nb - 1 and state(page, "s.notes.every(n => s.books.some(b => b.id === n.bookId))"))
        page.get_by_role("button", name="Done selecting").click()

        # ---- tag filter hides books with no match ----
        page.locator("[aria-label='Filter by tag'] .tagbtn", has_text="dreams").click()
        shown = books_shown(page)
        expect = state(page, "s.books.filter(b => !b.archived && s.notes.some(n => n.bookId === b.id && !n.archived && n.tags.includes('g5'))).map(b => b.name).sort()")
        check("tag filter hides books without a match", sorted(shown) == expect and len(shown) < 3, [shown, expect])
        page.locator("[aria-label='Filter by tag'] .tagbtn", has_text="All").click()
        check("tag filter cleared", len(books_shown(page)) == state(page, "s.books.filter(b => !b.archived).length"))

        # ---- book modal ----
        page.get_by_role("button", name="New book", exact=True).click()
        check("book modal opens", page.get_by_role("dialog", name="New book").count() == 1)
        page.get_by_role("button", name="Create", exact=True).click()
        check("book modal error text", page.get_by_role("alert").inner_text() == "Please add a name first.")
        page.get_by_placeholder("For example, Travel Diary").fill("Recipes")
        page.locator("input[type=date]").fill("2026-11-18")
        page.get_by_role("button", name="Blue", exact=True).click()
        shot(page, "diary-book-modal.png")
        overflow(page, "book modal")
        page.get_by_role("button", name="Create", exact=True).click()
        nbk = state(page, "s.books[s.books.length - 1]")
        check("create book", nbk["name"] == "Recipes" and nbk["date"] == "2026-11-18" and nbk["color"] == "#C3D4FF", nbk)
        check("new book is grouped by week", page.get_by_text("Week of Nov 16 to Nov 22").count() == 1)
        book(page, "Recipes").get_by_role("button", name="Edit book").click()
        page.get_by_placeholder("For example, Travel Diary").fill("Recipe Box")
        page.get_by_role("button", name="Save changes").click()
        check("edit book saves", state(page, f"s.books.find(b => b.id === '{nbk['id']}').name") == "Recipe Box")

        # ---- note modal ----
        book(page, "Recipe Box").get_by_role("button", name="Add note to this book").click()
        check("note modal opens with its book", page.get_by_role("dialog", name="New note").count() == 1 and state(page, "s.modal.bookId") == nbk["id"])
        page.get_by_role("button", name="Create", exact=True).click()
        check("note modal error text", page.get_by_role("alert").inner_text() == "Please add a name first.")
        page.get_by_placeholder("Give this note a title").fill("Pasta night")
        page.get_by_label("Your note").fill("Boil water. Add salt.")
        page.get_by_placeholder("New tag name").fill("food")
        page.get_by_role("button", name="Add tag").click()
        shot(page, "diary-note-modal.png")
        overflow(page, "note modal")
        page.get_by_role("button", name="Create", exact=True).click()
        nn = state(page, "s.notes[s.notes.length - 1]")
        check("create note", nn["title"] == "Pasta night" and nn["bookId"] == nbk["id"] and nn["body"] == "Boil water. Add salt." and len(nn["tags"]) == 1, nn)
        check("new note shows in its book", page.get_by_text("Pasta night").count() == 1)
        lnote(page, "Pasta night").get_by_role("button", name="Edit note").click()
        check("edit note modal has Archive and Delete", page.get_by_role("dialog", name="Edit note").count() == 1 and page.get_by_role("button", name="Delete", exact=True).count() >= 1)
        page.get_by_placeholder("Give this note a title").fill("Pasta feast")
        page.locator("[role=dialog] select").select_option("b1")
        page.get_by_role("button", name="Save changes").click()
        check("edit note saves", note(page, nn["id"])["title"] == "Pasta feast" and note(page, nn["id"])["bookId"] == "b1")
        expand(page, "Daily Diary")
        lnote(page, "Pasta feast").get_by_role("button", name="Archive note").click()
        check("note archive", note(page, nn["id"])["archived"] is True)
        book(page, "Recipe Box").get_by_role("button", name="Delete book").click()
        check("book delete asks first", page.get_by_role("alertdialog").count() == 1)
        page.get_by_role("button", name="Yes, delete").click()
        check("book removed", state(page, f"!s.books.some(b => b.id === '{nbk['id']}')"))

        # ---- themes and a narrow window ----
        for theme in ["blue", "teal"]:
            page.evaluate(f"window.__bc.actions.pickTheme('{theme}')")
            shot(page, f"diary-list-{theme}.png")
            overflow(page, f"diary list {theme}")
        page.set_viewport_size({"width": 800, "height": 900})
        overflow(page, "diary list 800px")

        check("no console errors", not errors, errors)
        browser.close()
    srv.shutdown()
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
