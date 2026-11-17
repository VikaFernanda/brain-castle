import pytest

from brain_castle.services import ServiceError, cutoff_date


def mk_task(svc, **kw):
    return svc.create_task({"title": "t", **kw})


def mk_book(svc, name="B"):
    return svc.create_book({"name": name, "color": "#FFE9A0"})


def mk_note(svc, book, **kw):
    return svc.create_note({"title": "n", "bookId": book["id"], **kw})


# ---------- ids and first run ----------

def test_first_run_is_empty(svc):
    data = svc.load_all()
    assert data == {"tasks": [], "notes": [], "books": [], "tags": [], "settings": {"theme": "pink"}}


def test_ids_have_prefixes_and_never_repeat(svc):
    t1 = mk_task(svc)
    svc.delete_task(t1["id"])
    t2 = mk_task(svc)
    assert t1["id"].startswith("t") and t2["id"].startswith("t")
    assert t1["id"] != t2["id"]  # AUTOINCREMENT: a deleted id is not reused
    assert mk_book(svc)["id"].startswith("b")
    assert svc.create_tag({"name": "x", "color": "#FFC9D9"})["id"].startswith("g")


def test_task_defaults_and_validation(svc):
    t = mk_task(svc)
    assert (t["notes"], t["date"], t["time"], t["tags"], t["images"]) == ("", "", "", [], {})
    assert (t["done"], t["archived"], t["auto"], t["keep"]) == (False, False, False, False)
    assert isinstance(t["created"], int)
    for bad in ({"title": "  "}, {"title": "a", "date": "2026-13-01"}, {"title": "a", "date": "17/11/2026"},
                {"title": "a", "time": "25:00"}, {"title": "a", "tags": ["g99"]}, {"title": "a", "done": "yes"}):
        with pytest.raises(ServiceError):
            svc.create_task(bad)
    with pytest.raises(ServiceError):
        svc.update_task("t999", {"title": "x"})
    with pytest.raises(ServiceError):
        svc.update_task("n1", {"title": "x"})  # wrong prefix


def test_update_changes_only_given_fields(svc):
    t = mk_task(svc, notes="keep me", date="2026-11-01", time="09:30")
    u = svc.update_task(t["id"], {"title": "new"})
    assert (u["title"], u["notes"], u["date"], u["time"]) == ("new", "keep me", "2026-11-01", "09:30")


# ---------- delete and cascade ----------

def test_delete_book_deletes_its_notes(svc):
    b1, b2 = mk_book(svc, "one"), mk_book(svc, "two")
    n1, n2 = mk_note(svc, b1), mk_note(svc, b2)
    assert svc.delete_book(b1["id"]) == {"id": b1["id"]}
    ids = [n["id"] for n in svc.load_all()["notes"]]
    assert ids == [n2["id"]] and n1["id"] not in ids


def test_archive_book_does_not_touch_notes(svc):
    b = mk_book(svc)
    n = mk_note(svc, b)
    assert svc.archive_book(b["id"])["archived"] is True
    assert svc.load_all()["notes"][0]["archived"] is False and svc.load_all()["notes"][0]["id"] == n["id"]


def test_restore_note_restores_its_book(svc):
    b = mk_book(svc)
    n = mk_note(svc, b)
    svc.archive_note(n["id"])
    svc.archive_book(b["id"])
    out = svc.restore_note(n["id"])
    assert out["archived"] is False
    assert svc.load_all()["books"][0]["archived"] is False


def test_restore_task_sets_keep_and_clears_auto(svc, clock):
    t = mk_task(svc, date="2026-01-01")
    assert svc.run_maintenance() == {"autoArchived": [t["id"]]}
    r = svc.restore_task(t["id"])
    assert (r["archived"], r["auto"], r["keep"]) == (False, False, True)
    assert svc.run_maintenance() == {"autoArchived": []}  # keep: never auto-archived again


def test_archive_then_delete_is_permanent(svc):
    t = mk_task(svc)
    svc.archive_task(t["id"])
    svc.delete_task(t["id"])
    assert svc.load_all()["tasks"] == []
    with pytest.raises(ServiceError):
        svc.delete_task(t["id"])


def test_note_needs_an_existing_book(svc):
    with pytest.raises(ServiceError):
        svc.create_note({"title": "n", "bookId": "b1"})
    with pytest.raises(ServiceError):
        svc.create_note({"title": "n"})


# ---------- tags ----------

def test_delete_tag_removes_it_from_tasks_and_notes(svc):
    g1 = svc.create_tag({"name": "a", "color": "#FFC9D9"})
    g2 = svc.create_tag({"name": "b", "color": "#C3D4FF"})
    t = mk_task(svc, tags=[g1["id"], g2["id"]])
    n = mk_note(svc, mk_book(svc), tags=[g1["id"]])
    assert svc.delete_tag(g1["id"]) == {"id": g1["id"]}
    data = svc.load_all()
    assert data["tasks"][0]["tags"] == [g2["id"]] and data["notes"][0]["tags"] == []
    assert [g["id"] for g in data["tags"]] == [g2["id"]]
    assert t["id"] and n["id"]


def test_tag_order_on_an_item_is_kept(svc):
    gs = [svc.create_tag({"name": c, "color": "#FFC9D9"})["id"] for c in "abc"]
    t = mk_task(svc, tags=[gs[2], gs[0], gs[1]])
    assert t["tags"] == [gs[2], gs[0], gs[1]]
    assert svc.update_task(t["id"], {"tags": [gs[1]]})["tags"] == [gs[1]]


def test_update_tag(svc):
    g = svc.create_tag({"name": "a", "color": "#FFC9D9"})
    assert svc.update_tag(g["id"], {"name": "z"}) == {"id": g["id"], "name": "z", "color": "#FFC9D9"}
    with pytest.raises(ServiceError):
        svc.update_tag(g["id"], {"color": "pink"})


# ---------- auto-archive ----------

@pytest.mark.parametrize("today,cutoff", [
    ("2026-11-17", "2026-08-17"),
    ("2026-05-31", "2026-02-28"),   # month end: clamp to the last day
    ("2024-05-31", "2024-02-29"),   # leap year
    ("2026-12-31", "2026-09-30"),
    ("2026-03-31", "2025-12-31"),   # across the new year
    ("2026-01-15", "2025-10-15"),
])
def test_cutoff_date(today, cutoff):
    assert cutoff_date(today) == cutoff


def test_auto_archive_at_the_three_month_edge(svc, clock):
    clock.value = "2026-11-17"  # cutoff 2026-08-17
    old = mk_task(svc, date="2026-08-16")
    edge = mk_task(svc, date="2026-08-17")
    new = mk_task(svc, date="2026-08-18")
    nodate = mk_task(svc)
    out = svc.run_maintenance()
    assert out == {"autoArchived": [old["id"]]}
    by = {t["id"]: t for t in svc.load_all()["tasks"]}
    assert by[old["id"]]["archived"] and by[old["id"]]["auto"]
    assert not by[edge["id"]]["archived"] and not by[new["id"]]["archived"] and not by[nodate["id"]]["archived"]


def test_auto_archive_on_month_ends(svc, clock):
    clock.value = "2026-05-31"  # cutoff 2026-02-28
    a = mk_task(svc, date="2026-02-27")
    b = mk_task(svc, date="2026-02-28")
    assert svc.run_maintenance() == {"autoArchived": [a["id"]]}
    assert not {t["id"]: t for t in svc.load_all()["tasks"]}[b["id"]]["archived"]


def test_auto_archive_skips_archived_and_runs_once(svc):
    t = mk_task(svc, date="2026-01-01")
    svc.archive_task(t["id"])
    assert svc.run_maintenance() == {"autoArchived": []}
    assert svc.load_all()["tasks"][0]["auto"] is False  # archived by hand, not "auto"


def test_keep_flag_blocks_auto_archive(svc):
    t = mk_task(svc, date="2026-01-01")
    svc.update_task(t["id"], {"keep": True})
    assert svc.run_maintenance() == {"autoArchived": []}


# ---------- reorder and move ----------

def order(svc, key):
    return [x["id"] for x in svc.load_all()[key]]


def test_new_items_go_to_the_end_and_load_all_is_in_order(svc):
    ids = [mk_task(svc)["id"] for _ in range(3)]
    assert order(svc, "tasks") == ids


def test_reorder_before_and_to_the_end(svc):
    a, b, c, d = (mk_task(svc)["id"] for _ in range(4))
    assert svc.reorder([d], a) == {"ids": [d, a, b, c]}
    assert order(svc, "tasks") == [d, a, b, c]
    assert svc.reorder([d, a]) == {"ids": [b, c, d, a]}  # null = at the end
    assert svc.reorder([c, a], b)["ids"] == [c, a, b, d]  # several at once
    assert order(svc, "tasks") == [c, a, b, d]


def test_reorder_survives_new_items_and_books_are_separate(svc):
    a, b = mk_task(svc)["id"], mk_task(svc)["id"]
    svc.reorder([b], a)
    c = mk_task(svc)["id"]
    assert order(svc, "tasks") == [b, a, c]
    b1, b2 = mk_book(svc, "1")["id"], mk_book(svc, "2")["id"]
    svc.reorder([b2], b1)
    assert order(svc, "books") == [b2, b1] and order(svc, "tasks") == [b, a, c]


def test_reorder_errors(svc):
    a = mk_task(svc)["id"]
    for args in (([], None), (["x1"], None), (["t999"], None), ([a, "n1"], None)):
        with pytest.raises(ServiceError):
            svc.reorder(*args)


def test_move_tasks_to_a_day_and_no_date(svc):
    t = mk_task(svc, date="2026-11-01")
    assert svc.move([t["id"]], {"date": "2026-11-20"}) == {"ids": [t["id"]]}
    assert svc.load_all()["tasks"][0]["date"] == "2026-11-20"
    svc.move([t["id"]], {"date": ""})
    assert svc.load_all()["tasks"][0]["date"] == ""
    with pytest.raises(ServiceError):
        svc.move([t["id"]], {"date": "nope"})


def test_move_notes_between_books(svc):
    b1, b2 = mk_book(svc, "1"), mk_book(svc, "2")
    n = mk_note(svc, b1)
    svc.move([n["id"]], {"bookId": b2["id"]})
    assert svc.load_all()["notes"][0]["bookId"] == b2["id"]
    with pytest.raises(ServiceError):
        svc.move([n["id"]], {"bookId": "b999"})
    with pytest.raises(ServiceError):
        svc.move([b1["id"]], {"date": ""})  # books cannot be moved


# ---------- settings ----------

def test_settings_theme(svc):
    assert svc.get_settings() == {"theme": "pink"}
    assert svc.set_settings({"theme": "blue"}) == {"theme": "blue"}
    assert svc.load_all()["settings"] == {"theme": "blue"}
    for bad in ({"theme": "red"}, {"colour": "x"}):
        with pytest.raises(ServiceError):
            svc.set_settings(bad)
    assert svc.get_settings() == {"theme": "blue"}


# ---------- transactions ----------

def test_a_failed_write_changes_nothing(svc):
    g = svc.create_tag({"name": "a", "color": "#FFC9D9"})
    with pytest.raises(ServiceError):
        svc.create_task({"title": "half", "tags": [g["id"], "g999"]})  # fails after the INSERT
    assert svc.load_all()["tasks"] == []


def test_persists_after_reopen(tmp_path, images_dir):
    from brain_castle import db
    from brain_castle.services import Services
    c1 = db.connect(tmp_path / "keep.db")
    s1 = Services(c1, images_dir)
    s1.create_task({"title": "stay"})
    s1.set_settings({"theme": "teal"})
    c1.close()
    s2 = Services(db.connect(tmp_path / "keep.db"), images_dir)
    data = s2.load_all()
    assert data["tasks"][0]["title"] == "stay" and data["settings"]["theme"] == "teal"
