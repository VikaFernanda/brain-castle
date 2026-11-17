"""Image files: check the real type, size limit, save, delete, and the local route that shows them.

Phase 0 spike choice (docs/spike-results.md): upload as base64 (a data URL), display through a local
route on 127.0.0.1 with a random port (LocalServer, which also serves the web folder).
"""
import base64
import binascii
import http.server
import re
import threading
import urllib.parse
import uuid
from pathlib import Path

MAX_BYTES = 8 * 1024 * 1024
_DATA_URL = re.compile(r"^data:([\w.+/-]*)(;[^,]*)?,(.*)$", re.S)
_SAFE_NAME = re.compile(r"^[0-9a-f]{32}\.(png|jpg|gif|webp)$")


class ImageError(ValueError):
    """A short message that is fine to show to the user."""


def sniff(data: bytes) -> str | None:
    """Real file type from the first bytes (never from the name or the declared mime)."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def is_data_url(value) -> bool:
    return isinstance(value, str) and value[:5].lower() == "data:"


def decode_data_url(value: str, max_bytes: int = MAX_BYTES) -> bytes:
    m = _DATA_URL.match(value)
    if not m or ";base64" not in (m.group(2) or "").lower():
        raise ImageError("This image could not be read.")
    payload = m.group(3)
    if len(payload) > max_bytes * 4 // 3 + 8:  # cheap check before decoding
        raise ImageError("This image is too big.")
    try:
        data = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise ImageError("This image could not be read.") from None
    if len(data) > max_bytes:
        raise ImageError("This image is too big.")
    return data


def save_image(images_dir: Path, data: bytes, max_bytes: int = MAX_BYTES) -> str:
    """Write the bytes as a new file and return its file name. Raises ImageError for bad input."""
    if not data:
        raise ImageError("This image is empty.")
    if len(data) > max_bytes:
        raise ImageError("This image is too big.")
    kind = sniff(data)
    if not kind:
        raise ImageError("Only PNG, JPEG, GIF and WebP images are allowed.")
    name = f"{uuid.uuid4().hex}.{kind}"
    (Path(images_dir) / name).write_bytes(data)
    return name


def delete_image_file(images_dir: Path, filename: str) -> None:
    if _SAFE_NAME.match(filename or ""):
        try:
            (Path(images_dir) / filename).unlink()
        except FileNotFoundError:
            pass


_TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8",
          ".woff2": "font/woff2", ".txt": "text/plain; charset=utf-8", ".json": "application/json", ".svg": "image/svg+xml"}


class LocalServer:
    """One server on http://127.0.0.1:<random port>, GET only:
      /images/<file>  the images folder (names are checked, nothing else is reachable)
      /...            the web folder (index.html and its files), only when web_dir is given.
    The page must come from http, not file://: Chromium blocks ES modules loaded from file://.
    """

    def __init__(self, images_dir: Path, web_dir: Path | None = None):
        folder = Path(images_dir)
        web = Path(web_dir).resolve() if web_dir else None

        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):  # silence
                pass

            def _send(self, data: bytes, ctype: str, cache: str):
                self.send_response(200)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", cache)
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                path = urllib.parse.unquote(self.path.split("?", 1)[0].split("#", 1)[0])
                if path.startswith("/images/"):
                    name = path[len("/images/"):]
                    file = folder / name
                    if not _SAFE_NAME.match(name) or not file.is_file():
                        return self.send_error(404)
                    ext = name.rsplit(".", 1)[1]
                    return self._send(file.read_bytes(), {"jpg": "image/jpeg"}.get(ext, f"image/{ext}"), "max-age=31536000, immutable")  # names never repeat
                if web is None:
                    return self.send_error(404)
                file = (web / ("index.html" if path == "/" else path.lstrip("/"))).resolve()
                if not file.is_relative_to(web) or not file.is_file():
                    return self.send_error(404)
                self._send(file.read_bytes(), _TYPES.get(file.suffix.lower(), "application/octet-stream"), "no-cache")

        self._srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._srv.serve_forever, daemon=True)

    def start(self) -> "LocalServer":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._srv.shutdown()
        self._srv.server_close()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self._srv.server_port}"

    def url_for(self, filename: str) -> str:
        return f"{self.base}/images/{filename}"
