#!/bin/bash
# Stage the contamination technical write-up and its figure gallery as a static page of the results site.
#
#   results/contam/technical_writeup.html  ->  site/public/contamination/index.html    (served at /contamination/)
#   results/contam/gallery.html            ->  site/public/contamination/gallery.html
#
# Only the images the two pages reference are copied, under site/public/contamination/, and the pages' src/href attributes are
# rewritten to those paths (results/contam/article/... stays article/..., ../ablation/... becomes ablation/..., ../verify/...
# becomes verify/..., ../../Article/charts/... becomes charts/...). A Home link (../) and a link between the two pages are added
# to each header. The staging directory is regenerated from scratch every run and is git-ignored (it is derived from results/,
# whose figures are not tracked); scripts/deploy_site.sh runs this before building.
#
# Usage: scripts/publish_writeup.sh        (from anywhere; exits non-zero if any referenced file is missing)
set -euo pipefail
cd "$(dirname "$0")/.."
python3 - <<'EOF'
import re, shutil, sys
from pathlib import Path

root = Path.cwd()
src_dir = root / "results" / "contam"
out = root / "site" / "public" / "contamination"
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)

# Where a page-relative path (relative to results/contam/) lands under site/public/contamination/.
PREFIXES = [
    ("../../Article/charts/", "charts/"),
    ("../ablation/", "ablation/"),
    ("../verify/", "verify/"),
    ("article/", "article/"),
]

def relocate(p: str):
    for old, new in PREFIXES:
        if p.startswith(old):
            return new + p[len(old):]
    return None

copied, missing = set(), []

def rewrite(html: str) -> str:
    def sub(m):
        attr, p = m.group(1), m.group(2)
        if p.startswith(("#", "http://", "https://", "mailto:")) or p.endswith(".html"):
            return m.group(0)
        new = relocate(p)
        if new is None:
            return m.group(0)
        s = (src_dir / p).resolve()
        if not s.is_file():
            missing.append(p)
            return m.group(0)
        d = out / new
        if new not in copied:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(s, d)
            copied.add(new)
        return f'{attr}="{new}"'
    return re.sub(r'\b(src|href)="([^"]+)"', sub, html)

HOME = '<a class="home" href="../" title="The landing page: every page of the site">Home</a>'

# --- write-up -------------------------------------------------------------------------------------------------------------
w = (src_dir / "technical_writeup.html").read_text(encoding="utf-8")
w = rewrite(w)
if '<meta name="description"' not in w:
    w = w.replace(
        "<title>",
        '<meta name="description" content="Technical write-up of the contamination study: six collections at graded public exposure, '
        'four systems, three tests (case knowledge, document memorisation, knowledge effect under rename-and-subtract), four '
        'generalisation checks, a renamer audit and the decisions taken along the way.">\n<title>', 1)
w = w.replace(
    "nav a:hover{color:var(--acc)}",
    "nav a:hover{color:var(--acc)}\n"
    "nav a.home,nav a.gal{border:1px solid var(--rule);border-radius:6px;padding:2px 9px;color:var(--ink)}\n"
    "nav a.gal{margin-left:auto}", 1)
w = w.replace('<nav><div class="in">\n', f'<nav><div class="in">\n{HOME}', 1)
w = w.replace(
    '<a href="#s10">10 Open items &amp; repro</a>\n',
    '<a href="#s10">10 Open items &amp; repro</a><a class="gal" href="gallery.html" title="Every figure of the study, by what it measures">Figure gallery</a>\n', 1)
assert 'class="home"' in w and 'class="gal"' in w, "write-up nav markers not found"
(out / "index.html").write_text(w, encoding="utf-8")

# --- gallery --------------------------------------------------------------------------------------------------------------
g = (src_dir / "gallery.html").read_text(encoding="utf-8")
g = rewrite(g)
if '<meta name="description"' not in g:
    g = g.replace("<title>", '<meta name="description" content="Every figure of the contamination study, organised by what it measures.">'
                  "<title>", 1)
g = g.replace("header a:hover{background:#eef0ee}",
              "header a:hover{background:#eef0ee}\nheader a.home,header a.wu{border:1px solid #d6d6d2}\nheader a.wu{margin-left:auto}", 1)
g = re.sub(r"(<header><h1>.*?</h1>)",
           lambda m: m.group(1) + '<a class="home" href="../" title="The landing page: every page of the site">Home</a>', g, count=1)
g = g.replace("</header>", '<a class="wu" href="./" title="The technical write-up">Technical write-up</a></header>', 1)
assert 'class="home"' in g and 'class="wu"' in g, "gallery header markers not found"
(out / "gallery.html").write_text(g, encoding="utf-8")

# --- verify ---------------------------------------------------------------------------------------------------------------
if missing:
    print("missing source files:", *sorted(set(missing)), sep="\n  ", file=sys.stderr)
    sys.exit(1)
bad = []
for page in ("index.html", "gallery.html"):
    html = (out / page).read_text(encoding="utf-8")
    for attr, p in re.findall(r'\b(src|href)="([^"]+)"', html):
        if p.startswith(("#", "http://", "https://", "mailto:", "../")):
            continue
        if not (out / p).is_file() and not (out / p / "index.html").is_file():
            bad.append((page, p))
if bad:
    print("unresolved references:", *[f"{pg}: {p}" for pg, p in bad], sep="\n  ", file=sys.stderr)
    sys.exit(1)
size = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
print(f"staged {len(copied)} images + 2 pages in {out.relative_to(root)} ({size/1e6:.1f} MB); every src/href resolves")
EOF
