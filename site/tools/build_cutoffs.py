#!/usr/bin/env python3
"""Write site/public/cutoffs.json: every model's per-decision p(responsive) on the two site corpora, so the Cutoffs page
(site/src/CutoffsPage.tsx) can re-threshold each issue in the browser.

Run from anywhere:  python3 site/tools/build_cutoffs.py            (stdlib only; --check-only skips the write)

Source: results/<corpus>/multi/<model>.jsonl (the site's default arm), gold and gray re-bound from the corpus files
(data/trec/eval.jsonl, data/mallinckrodt/mnk.jsonl) exactly as ediscovery_bench/export.py does. Nothing under results/ or
ediscovery_bench/ is modified.

Layout (all arrays are doc-major: cell i = doc_index * n_issues + issue_index)
  corpora.<c>.docs        ordered document ids
  corpora.<c>.issues      [{id, title, short, n_pos, n_gray}] in task order (findings.json order)
  corpora.<c>.gold        base64, packed bits (bit i = cell i is gold-responsive)
  corpora.<c>.gray        base64, packed bits (bit i = the corpus marks the cell's gold as debatable)
  corpora.<c>.models.<k>  {enc, p, label, n_docs, n_cells, n_err, n_disagree}
      enc    "u8"  → one byte per cell, p = v / 200 (the 0.005 grid), 255 = missing (no row, or an errored decision)
             "u16" → two bytes per cell little-endian, p = v / 10000, 65535 = missing; used when any p is off the 0.005 grid
      p      base64 of the quantized probabilities
      label  base64 packed bits: the label the benchmark scored (the model's stated label; 1 = responsive). Missing cells are 0.
             This is what results/findings.json was computed from; p ≥ 0.5 differs from it on `n_disagree` cells (LLMs that
             returned "not responsive" with p_positive 0.99, or "responsive" with 0.4).

Self-check (always run): the label bits at 0.5 must reproduce findings.json's tp/fp/fn/tn for every model × corpus at
decision and document level, all and nogray, plus per-issue recall/precision; the quantized p must sit on the same side of 0.5
as the original. A threshold on p at 0.5 is also compared, and any difference is reported with the disagreement count that
explains it (it is a property of the model's output, not of this file).
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "site" / "public" / "cutoffs.json"
POS = "responsive"
U8_SENTINEL, U16_SENTINEL = 255, 65535

# The non-hidden roster of site/src/data.ts (PRIMARY, in display order) → file stem per corpus.
ROSTER = ["jev@base", "jev@choice", "jev@score", "jev@decompose", "jev@ensemble", "jev@gate", "laya-ft",
          "claude-haiku-4.5", "claude-sonnet-5", "gpt-5.6-luna", "gpt-5.6-terra", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemma3-12b"]
CORPORA = {
    "trec": dict(data="data/trec/eval.jsonl", display="TREC 2016 (Jeb Bush email)", label="TREC 2016"),
    "mnk": dict(data="data/mallinckrodt/mnk.jsonl", display="Mallinckrodt (opioid emails)", label="Mallinckrodt"),
}
# Documents excluded from scoring by meta.stratum, mirroring ediscovery_bench/scope.py: TREC topic 404 (eminent_domain) was
# dropped from the study on 2026-09-23 and the 100 eval emails drawn as its positives are not scored (3,016 of 3,116).
# The question itself is absent from findings.json's issue list, so its prediction rows are skipped below.
DROPPED_STRATA = {"trec": {"pos:eminent_domain"}}
# Short issue labels for the page's table (the findings title minus its "(broad)"/"(narrow)" suffix is the fallback).
SHORT = {
    "gw_bush": "George W. Bush", "movie_gallery": "Movie Gallery", "rilya_wilson": "Rilya Wilson", "faith_based": "Faith-based initiatives",
    "marketing": "Marketing", "recount_2000": "2000 recount", "condominiums": "Condominiums", "bottled_water": "Bottled water",
    "medicaid_reform": "Medicaid reform", "eminent_domain": "Eminent domain", "nra_rifle": "NRA (rifle association)", "nra_aliens": "NRA (non-resident aliens)",
    "som_broad": "Suspicious order monitoring", "som_narrow": "Release of flagged orders", "mktg_broad": "Opioid marketing", "mktg_narrow": "Exalgo abuse risk",
    "data_broad": "Distribution data", "data_narrow": "Florida oxycodone / pill mills", "dea_broad": "DEA and regulators", "dea_narrow": "DEA production quota",
}


def model_file(corpus: str, key: str) -> Path:
    mk = f"laya-ft-{corpus}@recipe" if key == "laya-ft" else key
    return ROOT / "results" / corpus / "multi" / f"{mk.replace('@', '__')}.jsonl"


def pack_bits(bits: list[int]) -> str:
    out = bytearray((len(bits) + 7) // 8)
    for i, b in enumerate(bits):
        if b:
            out[i >> 3] |= 1 << (i & 7)
    return base64.b64encode(bytes(out)).decode("ascii")


def quantize(p: float, scale: int) -> int:
    return int(round(p * scale))


def prf(tp: int, fp: int, fn: int, tn: int) -> dict:
    r = tp / (tp + fn) if tp + fn else None
    pr = tp / (tp + fp) if tp + fp else None
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "recall": r, "precision": pr}


def score(pred: list[int], gold: list[int], present: list[int], gray: list[int], doc_gray: list[bool], n_issues: int, exclude_gray: bool) -> dict:
    """Mirror of export.py _score: decision level, per issue, and the any-issue document level (over present cells)."""
    n_docs = len(doc_gray)
    ok = [i for i in range(len(pred)) if present[i] and not (exclude_gray and gray[i])]
    dec = [0, 0, 0, 0]
    per_q: dict[int, list[int]] = {}
    for i in ok:
        k = (0 if pred[i] and gold[i] else 1 if pred[i] else 2 if gold[i] else 3)
        dec[k] += 1
        per_q.setdefault(i % n_issues, [0, 0, 0, 0])[k] += 1
    doc = [0, 0, 0, 0]
    for d in range(n_docs):
        if exclude_gray and doc_gray[d]:
            continue
        cells = [d * n_issues + q for q in range(n_issues)]
        cells = [i for i in cells if present[i] and not (exclude_gray and gray[i])]
        if not cells:
            continue
        pa = any(pred[i] for i in cells); ga = any(gold[i] for i in cells)
        doc[0 if pa and ga else 1 if pa else 2 if ga else 3] += 1
    return {"decision": prf(*dec), "doc": prf(*doc), "per_issue": {q: prf(*v) for q, v in per_q.items()}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-only", action="store_true", help="run the self-check without writing cutoffs.json")
    args = ap.parse_args()

    findings = json.loads((ROOT / "results" / "findings.json").read_text())
    payload = {
        "version": 1,
        "arm": "multi",
        "quant": {"u8": "p = v / 200, 255 = missing", "u16": "p = v / 10000 (little-endian), 65535 = missing"},
        "note": "Per-decision p(responsive) for the site roster; gold and gray re-bound from the corpus files. label = the benchmark's scored label.",
        "corpora": {},
    }
    failures: list[str] = []
    notes: list[str] = []

    for corpus, cm in CORPORA.items():
        meta = findings["corpora"][corpus]
        qids = list(meta["issues"].keys())
        nq = len(qids)
        qi = {q: i for i, q in enumerate(qids)}
        docs: list[str] = []
        gold: list[int] = []
        gray: list[int] = []
        doc_gray: list[bool] = []
        for line in (ROOT / cm["data"]).open():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if (row.get("meta") or {}).get("stratum") in DROPPED_STRATA.get(corpus, ()):
                continue
            labels = {str(k): str(v) for k, v in (row.get("labels") or {}).items()}
            g = set(row.get("gray") or [])
            docs.append(str(row["id"]))
            for q in qids:
                gold.append(1 if labels.get(q, "not_responsive") == POS else 0)  # Document.gold: absent => negative
                gray.append(1 if q in g else 0)
            doc_gray.append(bool(g))  # export.py skips the doc under nogray when docs_by_id[d].gray is non-empty (any qid, task or not)
        di = {d: i for i, d in enumerate(docs)}
        nd = len(docs)
        if nd != meta["n_docs"]:
            failures.append(f"{corpus}: {nd} docs in corpus file, findings says {meta['n_docs']}")
        issues = []
        for q in qids:
            title = meta["issues"][q]
            issues.append({"id": q, "title": title, "short": SHORT.get(q, title.replace(" (broad)", "").replace(" (narrow)", "")),
                           "n_pos": meta["n_pos_by_issue"][q], "n_gray": meta["n_gray_by_issue"][q]})
        cj = {"display": cm["display"], "label": cm["label"], "n_docs": nd, "n_pos_docs_any": meta["n_pos_docs_any"],
              "docs": docs, "issues": issues, "gold": pack_bits(gold), "gray": pack_bits(gray), "models": {}}

        for key in ROSTER:
            f = model_file(corpus, key)
            if not f.exists():
                notes.append(f"{corpus} {key}: no multi-arm file, omitted")
                continue
            ncell = nd * nq
            p_raw: list[float | None] = [None] * ncell
            label: list[int] = [0] * ncell
            n_err = 0; n_rows = 0; dup = 0
            for line in f.open():
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line); n_rows += 1
                d = di.get(str(r["doc_id"])); q = qi.get(r["question"])
                if d is None or q is None:
                    continue  # export.py _rebind drops rows whose document is out of scope or whose question left the task set
                if r.get("error") is not None:
                    n_err += 1
                    continue
                i = d * nq + q
                if p_raw[i] is not None:
                    dup += 1
                p_raw[i] = float(r["p_positive"])
                label[i] = 1 if r["label"] == POS else 0
            if dup:
                failures.append(f"{corpus} {key}: {dup} duplicate (doc, issue) rows; export.py would count both, this file keeps the last")
            present = [1 if p is not None else 0 for p in p_raw]
            on_grid = all(p is None or abs(round(p * 200) - p * 200) < 1e-9 for p in p_raw)
            enc, scale, sent = ("u8", 200, U8_SENTINEL) if on_grid else ("u16", 10000, U16_SENTINEL)
            qv = [sent if p is None else min(scale, quantize(p, scale)) for p in p_raw]
            # quantization must not move any decision across 0.5
            side_bad = sum(1 for p, v in zip(p_raw, qv) if p is not None and (v / scale >= 0.5) != (p >= 0.5))
            if side_bad:
                failures.append(f"{corpus} {key}: quantization ({enc}) moved {side_bad} cells across 0.5")
            n_disagree = sum(1 for p, l in zip(p_raw, label) if p is not None and (p >= 0.5) != bool(l))
            if enc == "u8":
                buf = bytes(qv)
            else:
                buf = b"".join(int(v).to_bytes(2, "little") for v in qv)
            docs_present = {i // nq for i in range(ncell) if present[i]}
            cj["models"][key] = {"enc": enc, "p": base64.b64encode(buf).decode("ascii"), "label": pack_bits(label),
                                 "n_docs": len(docs_present), "n_cells": sum(present), "n_err": n_err, "n_disagree": n_disagree}

            # ---- self-check against findings.json ----
            rec = next((r for r in findings["records"] if r["corpus"] == corpus and r["tag"] == "" and r["arm"] == "multi" and r["model"] == key), None)
            if rec is None:
                failures.append(f"{corpus} {key}: no findings record to check against")
                continue
            pred_label = [label[i] if present[i] else 0 for i in range(ncell)]
            pred_p = [1 if present[i] and qv[i] / scale >= 0.5 else 0 for i in range(ncell)]
            for gname, exclude in (("all", False), ("nogray", True)):
                s = score(pred_label, gold, present, gray, doc_gray, nq, exclude)
                for lvl in ("decision", "doc"):
                    want = rec[gname][lvl]; got = s[lvl]
                    for k in ("tp", "fp", "fn", "tn"):
                        if want[k] != got[k]:
                            failures.append(f"{corpus} {key} {gname}.{lvl}.{k}: findings {want[k]} vs rebuilt {got[k]}")
                    for k in ("recall", "precision"):
                        w = want[k][0] if want[k] else None; g = got[k]
                        if (w is None) != (g is None) or (w is not None and abs(w - g) > 1e-3):
                            failures.append(f"{corpus} {key} {gname}.{lvl}.{k}: findings {w} vs rebuilt {g}")
                if gname == "all":
                    for q, want in rec["all"].get("per_issue", {}).items():
                        got = s["per_issue"].get(qi[q])
                        if got is None:
                            failures.append(f"{corpus} {key} per_issue {q}: missing"); continue
                        for k in ("recall", "precision"):
                            w = want[k][0] if want[k] else None; g = got[k]
                            if (w is None) != (g is None) or (w is not None and abs(w - g) > 1e-3):
                                failures.append(f"{corpus} {key} per_issue {q} {k}: findings {w} vs rebuilt {g}")
                        if want["n_pos"] != got["tp"] + got["fn"]:
                            failures.append(f"{corpus} {key} per_issue {q} n_pos: {want['n_pos']} vs {got['tp'] + got['fn']}")
                # a threshold on p at 0.5 (what the page computes) against the published label-based figures
                sp = score(pred_p, gold, present, gray, doc_gray, nq, exclude)
                for lvl in ("decision", "doc"):
                    want = rec[gname][lvl]; got = sp[lvl]
                    diff = [k for k in ("tp", "fp", "fn", "tn") if want[k] != got[k]]
                    if diff and n_disagree == 0:
                        failures.append(f"{corpus} {key} {gname}.{lvl}: p>=0.5 differs from findings ({diff}) with no label/p disagreement")
                    elif diff and gname == "all" and lvl == "doc":
                        notes.append(f"{corpus} {key}: p>=0.5 vs published labels at doc level: recall {want['recall'][0]:.4f}->{got['recall']:.4f}, "
                                     f"precision {want['precision'][0]:.4f}->{got['precision']:.4f} ({n_disagree} decisions where the stated label contradicts p)")
            if rec["subset"]:
                notes.append(f"{corpus} {key}: subset {rec['subset']} → {len(docs_present)} docs with cells, metrics over those")
        payload["corpora"][corpus] = cj

    print("self-check:", "OK" if not failures else f"{len(failures)} FAILURES")
    for f in failures:
        print("  FAIL", f)
    for n in notes:
        print("  note", n)
    if failures:
        return 1
    if not args.check_only:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(payload, separators=(",", ":"))
        OUT.write_text(text)
        print(f"wrote {OUT.relative_to(ROOT)}: {len(text):,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
