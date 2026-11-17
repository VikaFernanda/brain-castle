"""Where the app keeps its files.

Data folder = "data" next to the exe (frozen build) or next to the project (run from source).
If that folder is not writable, fall back to %APPDATA%/BrainCastle.
"""
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]  # .../app
PROJECT_DIR = APP_DIR.parent


@dataclass(frozen=True)
class DataPaths:
    root: Path
    images: Path
    logs: Path
    webview: Path
    db: Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def default_data_dir() -> Path:
    base = Path(sys.executable).resolve().parent if is_frozen() else PROJECT_DIR
    return base / "data"


def fallback_data_dir() -> Path:
    appdata = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(appdata) / "BrainCastle"


def web_dir() -> Path:
    """Folder with index.html (inside the bundle when frozen)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "web"
    return APP_DIR / "web"


def assets_dir() -> Path:
    """Folder with the app icon (inside the bundle when frozen)."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent)) / "assets"
    return APP_DIR / "assets"


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder):
            pass
        return True
    except OSError:
        return False


def resolve_paths(primary: Path | None = None, fallback: Path | None = None) -> DataPaths:
    """Pick the data folder and create its subfolders (images, logs, webview)."""
    primary = Path(primary) if primary else default_data_dir()
    if _writable(primary):
        root = primary
    else:
        root = Path(fallback) if fallback else fallback_data_dir()
        if not _writable(root):
            raise OSError(f"No writable data folder: tried {primary} and {root}")
    paths = DataPaths(root=root, images=root / "images", logs=root / "logs", webview=root / "webview", db=root / "brain-castle.db")
    for folder in (paths.images, paths.logs, paths.webview):
        folder.mkdir(parents=True, exist_ok=True)
    return paths
