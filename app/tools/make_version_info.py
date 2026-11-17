"""Write the Windows version resource for PyInstaller from brain_castle.__version__.

python app\tools\make_version_info.py <output file>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from brain_castle import __version__  # noqa: E402

TEMPLATE = """VSVersionInfo(
  ffi=FixedFileInfo(filevers=({t}), prodvers=({t}), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Brain Castle'),
      StringStruct('FileDescription', 'Brain Castle'),
      StringStruct('FileVersion', '{v}'),
      StringStruct('InternalName', 'BrainCastle'),
      StringStruct('LegalCopyright', 'GPL-3.0'),
      StringStruct('OriginalFilename', 'BrainCastle.exe'),
      StringStruct('ProductName', 'Brain Castle'),
      StringStruct('ProductVersion', '{v}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main() -> None:
    parts = [int(p) for p in __version__.split(".")][:4]
    parts += [0] * (4 - len(parts))
    out = Path(sys.argv[1])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(TEMPLATE.format(t=", ".join(map(str, parts)), v=__version__), encoding="utf-8")


if __name__ == "__main__":
    main()
