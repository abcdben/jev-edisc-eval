"""Build the CUAD paragraph corpus.

CUAD (Hendrycks et al. 2021, CC BY 4.0) is 510 EDGAR contracts with expert-highlighted spans for
41 clause categories. We use the official *test* split (102 contracts) and turn it into an
eDiscovery-style corpus: the unit of review is a contract paragraph, and the question is
"is this paragraph responsive to clause category X". Gold comes from the human spans:

    positive  the paragraph carries >= HALF of a gold span for X, or a gold span for X covers
              >= HALF of the paragraph
    gray      the paragraph overlaps a gold span for X but below those thresholds
              (a clause that runs across a paragraph break, or a stray fragment)
    negative  no overlap

The 41 categories are mapped to the question ids in tasks/cuad.yaml; only the categories listed
there are labeled. Paragraphs are shown with a short header (contract title, position) the way a
reviewer would see an excerpt.

    bench cuad-build --out data/cuad/cuad.jsonl          # downloads data.zip from GitHub if needed
"""

from __future__ import annotations

import io
import json
import re
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

DATA_URL = "https://github.com/TheAtticusProject/cuad/raw/main/data.zip"
HALF = 0.5
MIN_CHARS = 200  # merge shorter fragments forward
MAX_CHARS = 3000  # split longer paragraphs at sentence boundaries
MIN_CHARS_KEEP = 120  # drop trailing fragments shorter than this with no gold


def fetch(cache: Path) -> dict:
    cache.mkdir(parents=True, exist_ok=True)
    p = cache / "test.json"
    if not p.exists():
        raw = urllib.request.urlopen(DATA_URL, timeout=120).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for name in ("test.json", "CUADv1.json"):
                (cache / name).write_bytes(z.read(name))
    return json.loads(p.read_text())


def clean_title(t: str) -> str:
    """CUAD titles are EDGAR filenames, in two styles:
    "LIMEENERGYCO_09_09_1999-EX-10-DISTRIBUTOR AGREEMENT"
    "BerkshireHillsBancorpInc 20120809 10-Q EX-10.16 7708169 EX-10.16 Endorsement Agreement"
    -> "Distributor Agreement (LimeEnergyCo, 1999)"."""
    s = re.sub(r"[_]+", " ", t).strip()
    toks = s.split(" ")
    co = re.split(r"[ _-]", t)[0]
    m = re.search(r"\b((?:19|20)\d{2})(?:\d{4})?\b", " ".join(toks[1:5]))
    yr = m.group(1) if m else None
    # the agreement kind is whatever follows the last "EX-10.xx" style token
    parts = re.split(r"\bEX-?\d+(?:\.\d+)?(?:\([a-z]\))?\b[-_ ]*", s, flags=re.I)
    if len(parts) > 1:
        kind = parts[-1].strip(" -_")
    else:  # free-form title: "PACIRA PHARMACEUTICALS, INC. - A_R STRATEGIC LICENSING ... AGREEMENT"
        kind = s.split(" - ", 1)[1] if " - " in s else s
        kind = re.sub(r"\s*\(\d+\)\s*$", "", kind)
    kind = re.sub(r"\s+", " ", kind).strip().title() or "Agreement"
    co = re.sub(r"(Inc|Corp|Co|Ltd|Llc)$", r" \1", co).strip()
    return f"{kind} ({co}, {yr})" if yr else f"{kind} ({co})"


def segment(ctx: str) -> list[tuple[int, int]]:
    """Return [(start, end)] paragraph char ranges covering the contract."""
    spans: list[tuple[int, int]] = []
    pos = 0
    for m in re.finditer(r"\n[ \t]*\n(?:[ \t]*\n)*", ctx):
        if m.start() > pos:
            spans.append((pos, m.start()))
        pos = m.end()
    if pos < len(ctx):
        spans.append((pos, len(ctx)))
    # strip whitespace at the edges
    spans = [(_ltrim(ctx, a, b), _rtrim(ctx, a, b)) for a, b in spans]
    spans = [(a, b) for a, b in spans if b > a]
    # merge short fragments forward (headings, page numbers, defined-term labels)
    merged: list[tuple[int, int]] = []
    for a, b in spans:
        if merged and (merged[-1][1] - merged[-1][0]) < MIN_CHARS:
            merged[-1] = (merged[-1][0], b)
        else:
            merged.append((a, b))
    # split very long paragraphs at sentence boundaries
    out: list[tuple[int, int]] = []
    for a, b in merged:
        while b - a > MAX_CHARS:
            cut = _sentence_cut(ctx, a, b)
            out.append((a, cut))
            a = _ltrim(ctx, cut, b)
        out.append((a, b))
    return out


def _ltrim(ctx: str, a: int, b: int) -> int:
    while a < b and ctx[a].isspace():
        a += 1
    return a


def _rtrim(ctx: str, a: int, b: int) -> int:
    while b > a and ctx[b - 1].isspace():
        b -= 1
    return b


def _sentence_cut(ctx: str, a: int, b: int) -> int:
    window = ctx[a : a + MAX_CHARS]
    cands = [m.end() for m in re.finditer(r"[.;:]\s+(?=[A-Z(\"“])", window)]
    cands = [c for c in cands if c > MAX_CHARS * 0.4]
    return a + (cands[-1] if cands else MAX_CHARS)


def label_paragraphs(ctx: str, paras: list[tuple[int, int]], spans: dict[str, list[tuple[int, int]]]):
    """spans: category -> [(start, end)] gold. Returns per-paragraph (labels, gray)."""
    out = []
    for a, b in paras:
        labels: set[str] = set()
        gray: set[str] = set()
        for cat, ss in spans.items():
            for s, e in ss:
                ov = min(b, e) - max(a, s)
                if ov <= 0:
                    continue
                if ov >= HALF * (e - s) or ov >= HALF * (b - a):
                    labels.add(cat)
                else:
                    gray.add(cat)
        gray -= labels
        out.append((labels, gray))
    return out


def build(cache: Path, out: Path, categories: dict[str, str], dev_frac: float = 0.0):
    """categories: CUAD category name -> question id. Writes JSONL and prints a summary."""
    data = fetch(cache)["data"]
    n_docs = 0
    cat_pos: Counter = Counter()
    cat_gray: Counter = Counter()
    with out.open("w") as f:
        for ci, contract in enumerate(data):
            p = contract["paragraphs"][0]
            ctx = p["context"]
            title = clean_title(contract["title"])
            spans: dict[str, list[tuple[int, int]]] = {}
            for qa in p["qas"]:
                cat = qa["id"].split("__")[-1]
                if cat not in categories:
                    continue
                for a in qa["answers"]:
                    spans.setdefault(categories[cat], []).append((a["answer_start"], a["answer_start"] + len(a["text"])))
            paras = segment(ctx)
            lab = label_paragraphs(ctx, paras, spans)
            kept = [(i, r, l) for i, (r, l) in enumerate(zip(paras, lab)) if (r[1] - r[0]) >= MIN_CHARS_KEEP or l[0] or l[1]]
            n = len(kept)
            for k, (i, (a, b), (labels, gray)) in enumerate(kept):
                body = re.sub(r"[ \t]+", " ", ctx[a:b])
                body = re.sub(r"\n(?:[ \t]*\n){2,}", "\n\n", body).strip()
                header = f"Contract: {title}\nExcerpt {k + 1} of {n}\n\n"
                doc = {
                    "id": f"CUAD-{ci:03d}-{k:03d}",
                    "text": header + body,
                    "labels": {q: "responsive" for q in sorted(labels)},
                    "gray": sorted(gray),
                    "meta": {"contract": contract["title"], "contract_idx": ci, "para_idx": k, "char_start": a, "char_end": b, "n_chars": b - a},
                }
                f.write(json.dumps(doc) + "\n")
                n_docs += 1
                for q in labels:
                    cat_pos[q] += 1
                for q in gray:
                    cat_gray[q] += 1
    print(f"{n_docs} paragraphs from {len(data)} contracts -> {out}")
    for q in categories.values():
        print(f"  {q:<28} positives={cat_pos[q]:>4} ({cat_pos[q] / n_docs:5.1%})  gray={cat_gray[q]:>3}")
    return n_docs, cat_pos, cat_gray
