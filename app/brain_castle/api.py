"""The one class given to pywebview as js_api.

Every public method returns plain JSON: {"ok": true, "data": ...} or {"ok": false, "error": "..."}.
Nothing is ever raised to JS. Unexpected errors are logged to data/logs and shown as a short message.
pywebview exposes every public attribute, so everything that is not an api method starts with "_".
"""
import functools
import logging
import logging.handlers
from pathlib import Path

from .images import ImageError
from .services import ServiceError, Services

METHODS = (
    "load_all",
    "create_task", "update_task", "delete_task", "archive_task", "restore_task",
    "create_note", "update_note", "delete_note", "archive_note", "restore_note",
    "create_book", "update_book", "delete_book", "archive_book", "restore_book",
    "create_tag", "update_tag", "delete_tag",
    "reorder", "move", "run_maintenance", "get_settings", "set_settings",
)
GENERIC_ERROR = "Something went wrong. Your data is safe."

log = logging.getLogger("brain_castle")


def setup_logging(logs_dir: Path) -> None:
    if any(getattr(h, "_bc", False) for h in log.handlers):
        return
    handler = logging.handlers.RotatingFileHandler(Path(logs_dir) / "brain-castle.log", maxBytes=512_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    handler._bc = True
    log.addHandler(handler)
    log.setLevel(logging.INFO)


def _safe(name):
    def decorate(fn):
        @functools.wraps(fn)
        def call(self, *args):
            try:
                return {"ok": True, "data": fn(self._svc, *args)}
            except (ServiceError, ImageError) as e:
                log.info("%s: %s", name, e)
                return {"ok": False, "error": str(e)}
            except BaseException as e:  # never raise to JS
                log.exception("%s failed", name)
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                return {"ok": False, "error": GENERIC_ERROR}
        return call
    return decorate


class Api:
    def __init__(self, services: Services):
        self._svc = services

    load_all = _safe("load_all")(Services.load_all)
    create_task = _safe("create_task")(Services.create_task)
    update_task = _safe("update_task")(Services.update_task)
    delete_task = _safe("delete_task")(Services.delete_task)
    archive_task = _safe("archive_task")(Services.archive_task)
    restore_task = _safe("restore_task")(Services.restore_task)
    create_note = _safe("create_note")(Services.create_note)
    update_note = _safe("update_note")(Services.update_note)
    delete_note = _safe("delete_note")(Services.delete_note)
    archive_note = _safe("archive_note")(Services.archive_note)
    restore_note = _safe("restore_note")(Services.restore_note)
    create_book = _safe("create_book")(Services.create_book)
    update_book = _safe("update_book")(Services.update_book)
    delete_book = _safe("delete_book")(Services.delete_book)
    archive_book = _safe("archive_book")(Services.archive_book)
    restore_book = _safe("restore_book")(Services.restore_book)
    create_tag = _safe("create_tag")(Services.create_tag)
    update_tag = _safe("update_tag")(Services.update_tag)
    delete_tag = _safe("delete_tag")(Services.delete_tag)
    reorder = _safe("reorder")(Services.reorder)
    move = _safe("move")(Services.move)
    run_maintenance = _safe("run_maintenance")(Services.run_maintenance)
    get_settings = _safe("get_settings")(Services.get_settings)
    set_settings = _safe("set_settings")(Services.set_settings)
