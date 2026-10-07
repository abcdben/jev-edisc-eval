"""Render selected figures from the existing report pages (story.html, contamination_report.html, verbatim_review.html) to PNG with
headless Chrome + PIL, for the article and the gallery. Writes only under results/contam/article/. Recovered from the original
/tmp script on 2026-10-06 so the figures can be regenerated whenever the pages change (e.g. when a collection is added).

    .venv/bin/python scripts/article/shoot_story_figs.py
"""
import os, re, subprocess
from PIL import Image, ImageChops

import pathlib
REPO = str(pathlib.Path(__file__).resolve().parents[2])
OUT = os.path.join(REPO, "results/contam/article")
TMP = "/tmp/jev_figs"
import sys
ONLY = set(sys.argv[1:])  # optional: names of figures to (re)render
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)

story = open(os.path.join(REPO, "results/contam/story.html")).read()
report = open(os.path.join(REPO, "results/contam/contamination_report.html")).read()
review = open(os.path.join(REPO, "results/contam/verbatim_review.html")).read()

def style_of(html):
    return "\n".join(re.findall(r"<style.*?</style>", html, flags=re.S))

def pfig_at(html, pos):
    assert html.startswith('<div class="pfig">', pos), html[pos:pos+40]
    depth = 0
    for m in re.finditer(r"<div\b|</div>", html[pos:]):
        depth += 1 if m.group(0).startswith("<div") else -1
        if depth == 0:
            return html[pos:pos + m.end()]
    raise RuntimeError("unbalanced")

def figure_containing(html, key):
    i = html.find(key); assert i > 0, key
    s = html.rfind("<figure", 0, i); e = html.find("</figure>", i) + len("</figure>")
    return html[s:e]

def legend_before(html, pos):
    s = html.rfind('<div class="legend', 0, pos)
    return html[s:pos] if 0 < pos - s < 1500 else ""

def wrap(style, fragment, width=1200, extra_css="", body_class="paper story"):
    return f"""<!doctype html><html><head><meta charset="utf-8">{style}
<style>html,body{{background:#fff !important;margin:0}} main{{max-width:none;padding:28px 36px 36px;width:{width}px}}
.pfig,.ptbl{{margin:0}} svg.fig,.pfig svg{{width:100% !important;height:auto !important}} .pcap{{font-size:15px;max-width:none}} .legend{{font-size:14px}} {extra_css}</style></head>
<body class="{body_class}"><main>{fragment}</main></body></html>"""

def shoot(name, html, height=2400, width=1200):
    p = os.path.join(TMP, name + ".html"); open(p, "w").write(html)
    png = os.path.join(TMP, name + ".raw.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    f"--screenshot={png}", f"--window-size={width},{height}",
                    "--force-device-scale-factor=1", "file://" + p], check=True, capture_output=True)
    return png

def want(name):
    return not ONLY or name in ONLY

def finish(raw, name, pad=28):
    im = Image.open(raw).convert("RGB")
    bbox = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    im = im.crop(bbox); w, h = im.size
    W = max(1200, w + 2 * pad); H = h + 2 * pad
    canvas = Image.new("RGB", (W, H), (255, 255, 255)); canvas.paste(im, ((W - w) // 2, (H - h) // 2))
    out = os.path.join(OUT, name + ".png"); canvas.save(out, optimize=True)
    print(f"{name}: {canvas.size}, {os.path.getsize(out)//1024} KB")

# 1 hero
if want("documents_vs_case"):
    pos = story.find('<div class="pfig">')
    finish(shoot("documents_vs_case", wrap(style_of(story), pfig_at(story, pos))), "documents_vs_case")

# 2 grid
if want("two_kinds_grid"):
    pos = story.find('<div class="pfig"><div class="pcap">Two kinds of knowing')
    finish(shoot("two_kinds_grid", wrap(style_of(story), pfig_at(story, pos), extra_css="table.grid{font-size:14px} table.grid td{width:92px;height:44px;font-size:15px} table.grid th{font-size:12.5px} table.grid th.rl{font-size:14px}")), "two_kinds_grid")

# 3 knowledge effect (classifier relabeled, data unchanged)
if want("knowledge_effect"):
    pos = story.find('<div class="pfig"><div class="pcap">The knowledge effect')
    frag = legend_before(story, pos) + pfig_at(story, pos)
    frag = re.sub(r"Jev\s*<small>\(classifier\)</small>", "review classifier <small>(commercial)</small>", frag)
    frag = re.sub(r">Jev<", ">classifier<", frag).replace("Jev (classifier)", "review classifier").replace("<title>Jev:", "<title>classifier:")
    assert "Jev" not in frag, re.findall(r".{40}Jev.{40}", frag)
    finish(shoot("knowledge_effect", wrap(style_of(story), frag)), "knowledge_effect")

# 4 ladder footprint scatter
if want("ladder_footprint"):
    key = "Does public footprint predict how much of the record the model has?"
    frag = legend_before(report, report.find("The ladder: public footprint")) + figure_containing(report, key)
    finish(shoot("ladder_footprint", wrap(style_of(report), frag, body_class="")), "ladder_footprint")

# 4b the ladder itself (rows = matters incl. the two floors), from the report
if want("ladder"):
    key = "The ladder: public footprint, recall of the record, and identification from a de-identified sketch"
    frag = legend_before(report, report.find(key)) + figure_containing(report, key)
    finish(shoot("ladder", wrap(style_of(report), frag, body_class=""), height=3000), "ladder")

# 5 awareness scatter
if want("awareness_scatter"):
    pos = story.find('<div class="pfig"><div class="pcap">Where each collection sits')
    finish(shoot("awareness_scatter", wrap(style_of(story), legend_before(story, pos) + pfig_at(story, pos))), "awareness_scatter")

# 6 verbatim review card (Sol, mnk ltjw0253, excluded)
inj = """
<style>header{display:none !important} body{background:#fff !important} main{max-width:1128px;margin:0 auto;padding:20px 0} .more{display:none !important}
.card{font-size:15px} .doc,.gen{font-size:15px;line-height:1.6} .hd{font-size:14px}</style>
<script>
document.querySelectorAll('.corp').forEach(c => c.checked = (c.value === 'mnk'));
document.querySelector('#pool').value = 'excluded';
document.querySelector('#model').value = 'gpt-5.6-sol';
document.querySelector('#q').value = 'ltjw0253';
render(true);
</script>"""
if want("verbatim_federal_register_card"):
    finish(shoot("verbatim_federal_register_card", review.replace("</body></html>", inj + "</body></html>"), height=3000), "verbatim_federal_register_card", pad=20)
