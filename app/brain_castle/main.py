"""Start the app: python -m brain_castle [--debug] [--seed] [--data-dir PATH]

--seed      dev only: run on a throw-away sample database in <data>-seed (the real data is never touched).
--data-dir  use another data folder (tests, manual checks).
--debug     turn on the WebView2 developer tools, right-click menu, reload and zoom keys.
"""
import argparse
import shutil
import sys
from pathlib import Path

from . import api as api_module
from . import db, desktop, paths
from .images import LocalServer
from .instance import InstanceLock, focus_existing_window
from .menu import BackupMenu
from .seed import seed
from .services import Services


def build(data: paths.DataPaths, with_seed: bool = False):
    """Open the database and make the services, the image route and the api object."""
    api_module.setup_logging(data.logs)
    server = LocalServer(data.images, paths.web_dir()).start()
    svc = Services(db.connect(data.db), data.images, image_url=server.url_for)
    if with_seed:
        seed(svc)
    return api_module.Api(svc), server


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="brain_castle")
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--seed", action="store_true", help="dev only: sample data in a separate folder")
    ap.add_argument("--data-dir", type=Path)
    args = ap.parse_args(argv)

    desktop.install_crash_logging(None)  # until the data folder is known
    primary = args.data_dir or paths.default_data_dir()
    if args.seed:
        primary = primary.with_name(primary.name + "-seed")
        shutil.rmtree(primary, ignore_errors=True)  # a fresh sample every run
    try:
        data = paths.resolve_paths(primary)
    except OSError as e:
        desktop.message_box("Brain Castle", desktop.data_folder_message(e))
        return 1
    desktop.install_crash_logging(data.logs)

    lock = InstanceLock(data.root)
    if not lock.acquire():  # same data already open: bring that window forward, open nothing
        focus_existing_window()
        return 0
    try:
        if not desktop.webview2_installed():
            desktop.message_box("Brain Castle", desktop.webview2_missing_message(), ask_open_url=desktop.WEBVIEW2_URL)
            return 1
        return run(args, data)
    finally:
        lock.release()


def run(args, data: paths.DataPaths) -> int:
    api, server = build(data, with_seed=args.seed)
    svc = api._svc

    import webview  # late: tests do not need it

    try:
        screens = [(s.x, s.y, s.width, s.height) for s in webview.screens]
    except Exception:
        screens = []
    x, y, w, h = desktop.fit_window(svc.get_window_state(), screens)

    # "host=py" tells the JS to use the Python api (a normal browser has no such flag and gets MockApi).
    # "debug=1" keeps the browser keys (reload, zoom...) alive for development.
    url = server.base + "/index.html?host=py" + ("&debug=1" if args.debug else "")
    window = webview.create_window("Brain Castle", url, js_api=api, width=w, height=h, x=x, y=y,
                                   min_size=desktop.MIN_SIZE)

    def remember_window():  # runs when the window starts closing; returning None lets it close
        try:
            if window.x > -10000 and window.y > -10000:  # a minimized window reports -32000
                svc.set_window_state({"x": window.x, "y": window.y, "width": window.width, "height": window.height})
        except Exception:
            api_module.log.exception("could not save the window position")
    window.events.closing += remember_window

    backups = BackupMenu(svc, data.root / "backups")
    backups.window = window
    try:
        webview.start(debug=args.debug, storage_path=str(data.webview), private_mode=False,
                      menu=backups.menu(), icon=str(paths.assets_dir() / "brain-castle.ico"))
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
