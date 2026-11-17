"""Only one Brain Castle per data folder.

An exclusive OS lock on <data>/.lock. The OS drops the lock when the process ends (even after a crash
or a kill), so there is never a stale lock to clean up. A second launch on the same data does not open
a window: it tries to bring the first window to the front and exits.
"""
import os
import sys
from pathlib import Path

WINDOW_TITLE = "Brain Castle"


class InstanceLock:
    def __init__(self, folder: Path):
        self.path = Path(folder) / ".lock"
        self._fd: int | None = None

    def acquire(self) -> bool:
        """True if this process now owns the data folder, False if another one does."""
        fd = os.open(self.path, os.O_RDWR | os.O_CREAT)
        try:
            if sys.platform == "win32":
                import msvcrt
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            os.close(fd)
            return False
        self._fd = fd
        return True

    def release(self) -> None:
        if self._fd is None:
            return
        try:
            if sys.platform == "win32":
                import msvcrt
                os.lseek(self._fd, 0, os.SEEK_SET)
                msvcrt.locking(self._fd, msvcrt.LK_UNLCK, 1)
            os.close(self._fd)  # closing also drops a flock
        except OSError:
            pass
        self._fd = None


def focus_existing_window() -> bool:
    """Best effort (Windows): restore and raise the window of the running instance."""
    if sys.platform != "win32":
        return False
    import ctypes
    user32 = ctypes.windll.user32
    hwnd = user32.FindWindowW(None, WINDOW_TITLE)
    if not hwnd:
        return False
    SW_RESTORE = 9
    if user32.IsIconic(hwnd):
        user32.ShowWindow(hwnd, SW_RESTORE)
    user32.SetForegroundWindow(hwnd)
    return True
