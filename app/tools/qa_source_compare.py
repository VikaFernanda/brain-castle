"""Source-level comparison of the app against the design file (Main.dc.html).

The design cannot be rendered (its support.js is missing), so we compare the source:
  1. every CSS rule in the design <style> block is in the app (normalized, whitespace-free)
  2. every inline style="..." string in the design markup is in the app JS/CSS
  3. every visible copy text in the design markup is in the app JS
Usage: python app/tools/qa_source_compare.py [path-to-Main.dc.html]
Prints the differences. Exit 1 if any.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT = pathlib.Path(r"E:\Library\claude-code-projects\brain-castle\project\Main.dc.html")
design = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
src = design.read_text(encoding="utf-8")

app_files = [p for p in (ROOT / "app" / "web").rglob("*")
             if p.suffix in (".js", ".css", ".html") and "vendor" not in p.parts and "dev" not in p.parts and "tests" not in p.parts]
app = "\n".join(p.read_text(encoding="utf-8") for p in app_files)


def norm(s):
    return re.sub(r"\s+", "", s).replace("'", '"').replace(";}", "}").rstrip(";")


napp = norm(app)
diffs = []

style = re.search(r"<style>(.*?)</style>", src, re.S).group(1)
style = re.sub(r"/\*.*?\*/", "", style, flags=re.S)
rules = re.findall(r"[^{}]+\{[^{}]*\}", style)
for r in rules:
    if norm(r) not in napp:
        diffs.append(("css-rule", " ".join(r.split())[:140]))

body = src[src.index("</style>"):src.index('<script type="text/x-dc"')]
for m in set(re.findall(r'style="([^"{]+)"', body)):
    if norm(m) not in napp:
        diffs.append(("inline-style", m.strip()[:140]))

for t in sorted(set(re.findall(r">([^<>{}\n]*[A-Za-z][^<>{}\n]*)<", body))):
    t = t.strip()
    if len(t) > 1 and t not in app:
        diffs.append(("text", t))

for kind, d in diffs:
    print(f"{kind}: {d}")
print(f"{len(diffs)} differences ({len(rules)} css rules checked)")
sys.exit(1 if diffs else 0)
