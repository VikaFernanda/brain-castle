# Brain Castle

A portable Windows app for tasks, notes and books. It works offline. You do not install it.

## Run it
1. Unzip `BrainCastle-portable-<version>.zip` to any folder (for example `D:\Apps` or a USB stick).
2. Double-click `BrainCastle.exe`.

You do not need Python. You need the **Microsoft Edge WebView2 Runtime** (see below).

Only one window can be open for one data folder. If you start it again, the open window comes to the front.

## Where your data lives
In the `data\` folder next to `BrainCastle.exe`:

| Path | What it is |
| --- | --- |
| `data\brain-castle.db` | your items (SQLite) |
| `data\images\` | pasted and added images |
| `data\backups\` | safety copies made when you import a backup |
| `data\logs\crash.log` | errors, if the app crashes |
| `data\webview\` | browser cache of the window |

If the app folder is not writable (for example a read-only folder), the app uses `%APPDATA%\BrainCastle` instead.
The app writes nothing else on the PC. It does not write to the registry.

If `data\` is missing, the app makes a new empty one.

## Back up
- Easy way: menu **File > Export backup...**. It saves a zip with the database and the images. Use **File > Import backup...** to restore.
- Manual way: close the app and copy the whole `data\` folder.

## Update
1. Close Brain Castle.
2. Unzip the new version to a temporary folder.
3. Copy the new `BrainCastle` folder over the old one. **Keep your `data\` folder** (the zip has no `data\`, so a copy over the old folder keeps it).
4. Start `BrainCastle.exe`. Old data is upgraded automatically.

Tip: make a backup before you update.

## Windows warns about the exe (SmartScreen)
The exe is not code-signed, so Windows SmartScreen may show "Windows protected your PC". The app is not harmed. To run it:
1. Click **More info**.
2. Click **Run anyway**.

If you downloaded the zip, you can also right-click the zip, choose **Properties**, tick **Unblock**, click OK, and then unzip. Some antivirus programs may also flag unsigned programs. You can add the folder as an exception.

## WebView2 requirement
The window uses Microsoft Edge WebView2. It is included in Windows 11 and in current Windows 10 updates. If it is missing, the app shows a message with the download link:
https://developer.microsoft.com/microsoft-edge/webview2/ (choose the Evergreen runtime).

## If the database file is damaged
The app checks the database file when it starts. If it cannot be read, the app shows a message with the file name and does
not start. **It does not change, move or delete the file.** To get going again:
1. Close the app. Copy `data\brain-castle.db` to a safe place.
2. Rename the damaged file (for example to `brain-castle.damaged.db`) and start the app. It opens with an empty database.
3. Use **File > Import backup...** to restore your last backup (the zip from **File > Export backup...**).

Make a backup now and then. It is the only way back if the file is lost.

## Checks before a release
```powershell
app\.venv\Scripts\python -m pytest app\tests            # Python: rules, images, backup, data safety
python app\web\dev\qa.py shots                          # every screen, 3 themes, 1440x900 and 1024x700, overflow check
python app\tools\qa_source_compare.py                   # design CSS / text against the app
app\.venv\Scripts\python app\tools\load_test.py         # 1,000 tasks, 200 notes, 50 books, 100 images
python app\web\dev\load_test.py                         # same in the browser
```
Reports: `docs\qa-report.md`, `docs\requirements-check.md`. Changes: `CHANGELOG.md`.

## Build it yourself
You need Windows and Python 3.12 (`py -3.12`).

```powershell
powershell -ExecutionPolicy Bypass -File build.ps1
```

The script makes `app\.venv`, installs the requirements, runs the tests, runs PyInstaller (`app\packaging\BrainCastle.spec`, onedir, windowed) and writes `dist\BrainCastle-portable-<version>.zip`. The version is `__version__` in `app\brain_castle\__init__.py`.

## License
GPL-3.0, see `LICENSE`.
