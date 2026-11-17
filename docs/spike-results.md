# Phase 0 spike results

Tested on this PC (Windows 11, Python 3.12.2, pywebview 6.2.1, PyInstaller 6.22.3, WebView2).
Items a, e, f, h were checked in the dev run and in the PyInstaller build. Items b, c, c2, d were checked
in the **PyInstaller `--onedir --windowed` build** with real mouse/keyboard input (Win32 `mouse_event`,
`SendKeys`, and a WinForms OLE file drag from a helper window). Screenshot: `docs/spike-screenshot.png`.

| Item | Result | Notes |
|---|---|---|
| a) JS -> Python, Python -> JS | PASS | `add(2,3)=5`; `window.evaluate_js` got a reply from JS. |
| b) HTML5 drag and drop between two zones | PASS | Element moved from zone A to zone B. |
| c) File dropped on textarea | PASS | `dataTransfer.files` had the file; `arrayBuffer()` read 182 bytes. |
| c2) File dropped outside textarea | PASS | Window did not navigate (needs a window-level `dragover`/`drop` `preventDefault`). |
| d) Ctrl+V image into textarea | PASS | `clipboardData.items` gave `image/png`, bytes read. |
| e) Save image in Python, show in JS | PASS | See below. |
| f) `storage_path` | PASS | WebView2 profile files were created in `<exe folder>\data\webview`. |
| g) PyInstaller onedir windowed build | PASS | The built exe passed a-f and h. |
| h) Native menu File > Export... | PASS (partly) | `webview.start(menu=...)` shows the menu. I did not click the item; I can't confirm the click callback. |

## e) base64 vs local route
Test image was 10x10 PNG; times from one run (save, then show):
- base64 over the bridge: ~6-10 ms
- local route (`http.server` on 127.0.0.1, random port, serving the images folder): ~3-4 ms

**Recommendation: local route for display, base64 only for upload.** Both are fast on small images, so
this is based on one tiny sample. The route needs no re-encoding (33% bigger), lets the browser cache and
lazy-load, and works in `<img src>` and CSS. base64 is simpler (no server) and fine for the upload
direction (JS -> Python), where there is no other option. If the route is used, bind to 127.0.0.1 only.

## Notes
- Closing a dev run with a hard kill leaves `msedgewebview2.exe` processes that lock the `data` folder.
- `--add-data` source paths are relative to the spec folder; use an absolute path.
- Python 3.12 venv: `app\.venv`. Versions are pinned in `requirements*.txt`.
- No item failed, so no alternative is needed.
