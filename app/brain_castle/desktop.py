"""Desktop helpers: window size/position, startup error messages, crash log.

Nothing here draws UI inside the page. Messages use plain native message boxes.
"""
import logging
import sys
import tempfile
import threading
import traceback
import webbrowser
from pathlib import Path

WEBVIEW2_URL = "https://developer.microsoft.com/microsoft-edge/webview2/"
_WEBVIEW2_GUID = "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
DEFAULT_SIZE = (1280, 840)
MIN_SIZE = (900, 600)

log = logging.getLogger("brain_castle")


# ---------- window geometry ----------

def fit_window(saved: dict | None, screens: list[tuple[int, int, int, int]]):
    """Return (x, y, width, height). x and y are None when the window should start centered.

    `saved` = last close {x, y, width, height}. `screens` = list of (x, y, width, height).
    A saved position is used only if the title bar is still on a screen (a monitor may be gone).
    """
    if not saved:
        return (None, None, *DEFAULT_SIZE)
    w = max(MIN_SIZE[0], saved["width"])
    h = max(MIN_SIZE[1], saved["height"])
    x, y = saved["x"], saved["y"]
    for sx, sy, sw, sh in screens:
        # the top-left 100x40 area of the window must be inside this screen
        if sx <= x + 100 <= sx + sw and sy <= y + 40 <= sy + sh and x < sx + sw and y >= sy - 10:
            return (x, y, w, h)
    return (None, None, w, h)


# ---------- WebView2 ----------

def webview2_installed() -> bool:
    """Documented check: the Evergreen runtime writes its version ('pv') under EdgeUpdate\\Clients."""
    if sys.platform != "win32":
        return True
    import winreg
    places = (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients" + "\\" + _WEBVIEW2_GUID),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate\Clients" + "\\" + _WEBVIEW2_GUID),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\EdgeUpdate\Clients" + "\\" + _WEBVIEW2_GUID),
    )
    for root, sub in places:
        try:
            with winreg.OpenKey(root, sub) as key:
                version = winreg.QueryValueEx(key, "pv")[0]
            if version and version != "0.0.0.0":
                return True
        except OSError:
            continue
    return False


# ---------- messages ----------

def message_box(title: str, text: str, ask_open_url: str | None = None) -> None:
    """Show a native message. With ask_open_url the box has Yes/No and Yes opens the page."""
    if sys.platform == "win32":
        import ctypes
        MB_YESNO, MB_OK, ICON_ERROR, IDYES = 0x4, 0x0, 0x10, 6
        flags = ICON_ERROR | (MB_YESNO if ask_open_url else MB_OK)
        answer = ctypes.windll.user32.MessageBoxW(None, text, title, flags)
        if ask_open_url and answer == IDYES:
            webbrowser.open(ask_open_url)
    else:
        print(f"{title}: {text}", file=sys.stderr)


def webview2_missing_message() -> str:
    return ("Brain Castle needs the Microsoft Edge WebView2 Runtime, and it is not installed on this PC.\n\n"
            f"Download it here:\n{WEBVIEW2_URL}\n\nOpen the download page now?")


def data_folder_message(error: OSError) -> str:
    return ("Brain Castle could not create or write to its data folder.\n\n"
            f"{error}\n\nMove the app to a folder you can write to, or check the folder permissions.")


def database_damaged_message(path, reason: str) -> str:
    return ("Brain Castle cannot read its database. Your file was NOT changed or deleted.\n\n"
            f"File: {path}\nProblem: {reason}\n\n"
            "What to do:\n"
            "1. Close the app and copy the file to a safe place.\n"
            "2. Restore a backup: rename the damaged file (for example to brain-castle.damaged.db), "
            "start the app, and use File > Import backup...\n"
            "3. Or open the copy with a SQLite tool to rescue your data.\n\n"
            "The app will not start until the file is moved or fixed.")


# ---------- crash log ----------

def install_crash_logging(logs_dir: Path | None) -> Path:
    """Send uncaught errors (main thread and other threads) to <data>\\logs\\crash.log.
    Before the data folder exists the file goes to the temp folder instead. Returns the file path."""
    folder = Path(logs_dir) if logs_dir else Path(tempfile.gettempdir())
    target = folder / ("crash.log" if logs_dir else "brain-castle-crash.log")

    def write(kind: str, exc_type, exc, tb) -> None:
        try:
            with open(target, "a", encoding="utf-8") as f:
                f.write(f"--- {kind} ---\n{''.join(traceback.format_exception(exc_type, exc, tb))}\n")
        except OSError:
            pass

    def main_hook(exc_type, exc, tb):
        write("crash", exc_type, exc, tb)
        sys.__excepthook__(exc_type, exc, tb)

    def thread_hook(args):
        write(f"crash in thread {args.thread.name if args.thread else '?'}", args.exc_type, args.exc_value, args.exc_traceback)

    sys.excepthook = main_hook
    threading.excepthook = thread_hook
    return target
