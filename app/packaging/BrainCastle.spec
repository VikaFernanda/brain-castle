# PyInstaller spec for the portable build. Run through build.ps1 (it makes build\version_info.txt first).
# Paths are relative to this spec file.
from pathlib import Path

APP = Path(SPECPATH).resolve().parent          # .../app
VERSION_FILE = APP.parent / "build" / "version_info.txt"

a = Analysis(
    [str(APP / "packaging" / "launcher.py")],
    pathex=[str(APP)],
    datas=[(str(APP / "web"), "web"), (str(APP / "assets"), "assets")],
    excludes=["tkinter", "pytest"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="BrainCastle",
    console=False,                      # --windowed
    icon=str(APP / "assets" / "brain-castle.ico"),
    version=str(VERSION_FILE),
    upx=False,                          # UPX makes antivirus warnings more likely
)
coll = COLLECT(exe, a.binaries, a.datas, name="BrainCastle", upx=False)
