import json
import logging

import pytest

from brain_castle import api as api_module
from brain_castle.api import Api, METHODS
from conftest import data_url


def ok(res):
    assert res["ok"] is True, res
    return res["data"]


def err(res):
    assert res["ok"] is False and set(res) == {"ok", "error"}
    assert isinstance(res["error"], str) and res["error"]
    return res["error"]


def test_every_method_exists_and_returns_plain_json(api):
    for name in METHODS:
        assert callable(getattr(api, name)), name
    res = api.load_all()
    json.dumps(res)  # plain JSON only
    assert ok(res)["tasks"] == []
    t = ok(api.create_task({"title": "a"}))
    json.dumps(ok(api.load_all()))
    assert ok(api.update_task(t["id"], {"done": True}))["done"] is True


def test_methods_match_the_js_interface():
    import pathlib
    import re
    js = (pathlib.Path(__file__).resolve().parents[1] / "web" / "js" / "api.js").read_text(encoding="utf-8")
    block = js[js.index("API_METHODS = ["):js.index("];")]
    assert set(re.findall(r"'(\w+)'", block)) == set(METHODS)


def test_nothing_private_is_public(api):
    public = [n for n in dir(api) if not n.startswith("_")]
    assert set(public) == set(METHODS)  # pywebview exposes every public name


def test_user_errors_are_short_messages(api):
    assert "name" in err(api.create_task({"title": ""})).lower()
    assert "not found" in err(api.update_task("t42", {}))
    assert "not found" in err(api.delete_book("b42"))
    assert err(api.create_task({"title": "x", "date": "tomorrow"}))
    assert err(api.set_settings({"theme": "red"}))
    assert err(api.reorder([], None))
    assert err(api.move(["b1"], {"date": ""}))


def test_bad_input_types_never_raise(api):
    for call in (lambda: api.create_task(None), lambda: api.create_task("text"), lambda: api.create_task({"title": 5}),
                 lambda: api.update_task(None, {}), lambda: api.update_task(["t1"], {}), lambda: api.update_task("t1", 7),
                 lambda: api.delete_task(1), lambda: api.reorder("t1", None), lambda: api.reorder([1], None),
                 lambda: api.move("t1", {}), lambda: api.move(["t1"], None), lambda: api.set_settings(None),
                 lambda: api.create_tag({"name": "a", "color": 5}), lambda: api.create_task({"title": "a", "tags": "g1"}),
                 lambda: api.create_task({"title": "a", "images": 5, "notes": "![a](img:i1)"})):
        res = call()
        assert res["ok"] in (True, False)
        json.dumps(res)


def test_a_bad_image_is_a_clean_error(api):
    res = api.create_task({"title": "t", "notes": "![a](img:i1)", "images": {"i1": data_url(b"MZ exe", "image/png")}})
    assert "PNG" in err(res)
    assert ok(api.load_all())["tasks"] == []


def test_unexpected_errors_are_logged_and_hidden(api, svc, tmp_path, caplog):
    svc.con.close()  # every later query raises sqlite3.ProgrammingError
    api_module.log.propagate = True
    with caplog.at_level(logging.ERROR, logger="brain_castle"):
        res = api.load_all()
    assert err(res) == api_module.GENERIC_ERROR and "sqlite" not in res["error"].lower()
    assert "ProgrammingError" in caplog.text and "Traceback" in caplog.text


def test_errors_go_to_the_log_file(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    for h in list(api_module.log.handlers):
        api_module.log.removeHandler(h)
    api_module.setup_logging(logs)
    api_module.setup_logging(logs)  # twice: still one handler
    assert len(api_module.log.handlers) == 1
    from brain_castle import db
    from brain_castle.services import Services

    svc = Services(db.connect(tmp_path / "l.db"), tmp_path)
    a = Api(svc)
    svc.con.close()
    err(a.load_all())
    for h in api_module.log.handlers:
        h.flush()
    assert "ProgrammingError" in (logs / "brain-castle.log").read_text(encoding="utf-8")
    for h in list(api_module.log.handlers):
        h.close()
        api_module.log.removeHandler(h)


def test_full_round_trip_through_the_api(api):
    g = ok(api.create_tag({"name": "home", "color": "#BFEBDD"}))
    b = ok(api.create_book({"name": "Diary", "color": "#FFE9A0"}))
    n = ok(api.create_note({"title": "n", "bookId": b["id"], "tags": [g["id"]], "body": "x"}))
    t = ok(api.create_task({"title": "t", "date": "2026-11-17", "tags": [g["id"]]}))
    ok(api.archive_note(n["id"]))
    ok(api.archive_book(b["id"]))
    assert ok(api.restore_note(n["id"]))["archived"] is False
    assert ok(api.load_all())["books"][0]["archived"] is False
    assert ok(api.delete_tag(g["id"])) == {"id": g["id"]}
    data = ok(api.load_all())
    assert data["tasks"][0]["tags"] == [] and data["notes"][0]["tags"] == [] and t["id"]
    assert ok(api.delete_book(b["id"])) == {"id": b["id"]} and ok(api.load_all())["notes"] == []
