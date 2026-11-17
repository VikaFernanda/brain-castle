"""Native window menu: File > Export backup... / Import backup...

The callbacks run on a pywebview worker thread. Messages go through the page's existing toast
(window.__bc.actions.toast), so no new screen is added.
"""
import json
import logging
from pathlib import Path

from . import backup
from .services import Services

log = logging.getLogger("brain_castle")


def _first(result) -> str | None:
    """create_file_dialog gives a str, a tuple or None, depending on the dialog."""
    if not result:
        return None
    return result if isinstance(result, str) else result[0]


class BackupMenu:
    def __init__(self, svc: Services, safety_dir: Path):
        self.svc = svc
        self.safety_dir = Path(safety_dir)
        self.window = None  # set once the window exists

    # ---- helpers (small, so tests can replace the window with a fake) ----
    def _toast(self, text: str) -> None:
        try:
            self.window.evaluate_js("window.__bc && window.__bc.actions.toast(" + json.dumps(text) + ")")
        except Exception:
            log.exception("toast failed")

    def _reload_page(self) -> None:
        self.window.evaluate_js("window.__bc && window.__bc.reload()")

    def _dialog(self, kind, **kw):
        import webview
        return _first(self.window.create_file_dialog(getattr(webview.FileDialog, kind), **kw))

    # ---- menu actions ----
    def export(self) -> None:
        try:
            path = self._dialog("SAVE", directory=str(Path.home() / "Documents"), save_filename=backup.default_name(),
                                file_types=("Backup (*.zip)",))
            if not path:
                return
            if not path.lower().endswith(".zip"):
                path += ".zip"
            backup.export_backup(self.svc, Path(path))
            self._toast("Backup saved")
        except Exception:
            log.exception("export backup failed")
            self._toast("Could not save the backup")

    def import_(self) -> None:
        try:
            path = self._dialog("OPEN", directory=str(Path.home() / "Documents"), file_types=("Backup (*.zip)",))
            if not path:
                return
            try:
                backup.check_backup(Path(path))
            except backup.BackupError as e:
                self._toast(str(e))
                return
            ok = self.window.create_confirmation_dialog(
                "Import backup",
                "Replace all your current tasks, notes and images with this backup?\n\n"
                "A safety copy of your current data is saved first.")
            if not ok:
                return
            safety = backup.import_backup(self.svc, Path(path), self.safety_dir)
            self._reload_page()
            self._toast("Backup imported. Your old data is saved in " + safety.name)
        except backup.BackupError as e:
            self._toast(str(e))
        except Exception:
            log.exception("import backup failed")
            self._toast("Could not import the backup. Your data is safe.")

    def menu(self):
        from webview.menu import Menu, MenuAction
        return [Menu("File", [MenuAction("Export backup...", self.export), MenuAction("Import backup...", self.import_)])]
