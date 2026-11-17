"""Start the app: python -m brain_castle [--debug] [--seed] [--data-dir PATH]

--seed      dev only: run on a throw-away sample database in <data>-seed (the real data is never touched).
--data-dir  use another data folder (tests, manual checks).
--debug     turn on the WebView2 developer tools.
"""
import argparse
import shutil
import sys
from pathlib import Path

from . import api as api_module
from . import db, paths
from .images import LocalServer
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

    primary = args.data_dir or paths.default_data_dir()
    if args.seed:
        primary = primary.with_name(primary.name + "-seed")
        shutil.rmtree(primary, ignore_errors=True)  # a fresh sample every run
    data = paths.resolve_paths(primary)
    api, server = build(data, with_seed=args.seed)

    import webview  # late: tests do not need it

    # "host=py" tells the JS to use the Python api (a normal browser has no such flag and gets MockApi).
    webview.create_window("Brain Castle", server.base + "/index.html?host=py", js_api=api, width=1280, height=840, min_size=(900, 600))
    try:
        webview.start(debug=args.debug, storage_path=str(data.webview), private_mode=False)
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
