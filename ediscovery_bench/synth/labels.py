"""Gold-label assembly for the Veridian corpus.

Three sources, in order of authority:
  1. planner intent   (manifest `responsive_to`, constrained to the arc's allowed RFPs; found to
                       mislabel RFP numbers in several arcs, so treated as a prior only)
  2. spec relabel     (two models read each spec's gist against all 10 RFPs; `--tag speclabel`)
  3. text audit       (three models read the rendered document; `--tag audit`)

Spec-level gold = relabeler consensus; split -> gray with gold by mean probability.
Text-level audit can flip a label only on unanimous disagreement, and always gray-flags it.
Every document keeps the full provenance in meta so the rules can be re-run differently later.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

from ..runner import job_path, load_predictions
from .plan import QIDS

POS = "responsive"


def _votes(results: Path, corpus: str, arm: str, keys: list[str], tag: str) -> dict[str, dict[str, list[tuple[str, str, float]]]]:
    votes: dict[str, dict[str, list[tuple[str, str, float]]]] = {}
    for k in keys:
        f = job_path(results, corpus, arm, k, tag)
        for p in load_predictions(f):
            if not p.error:
                votes.setdefault(p.doc_id, {}).setdefault(p.question, []).append((k, p.label, p.p_positive))
    return votes


def spec_gold(manifest: Path, results: Path, keys: list[str], out: Path, corpus: str = "veridian_gists", tag: str = "speclabel") -> str:
    votes = _votes(results, corpus, "multi", keys, tag)
    rows = [json.loads(l) for l in manifest.read_text().splitlines() if l.strip()]
    stats = Counter()
    with out.open("w") as f:
        for r in rows:
            planner = set(r["labels"])
            labels: dict[str, str] = {}
            gray = set(r.get("gray_q") or [])
            prov: dict[str, dict] = {}
            for q in QIDS:
                vs = votes.get(r["id"], {}).get(q, [])
                prov[q] = {k: round(p, 3) for k, _, p in vs}
                if len(vs) < 2:
                    # missing relabel: fall back to planner
                    if q in planner:
                        labels[q] = POS
                    stats["missing_relabel"] += 1
                    continue
                yes = sum(1 for _, lab, _ in vs if lab == POS)
                mean_p = sum(p for _, _, p in vs) / len(vs)
                if yes == len(vs):
                    labels[q] = POS
                    if q not in planner:
                        stats["added_vs_planner"] += 1
                elif yes == 0:
                    if q in planner:
                        gray.add(q); stats["dropped_vs_planner_gray"] += 1
                else:
                    gray.add(q); stats["split_gray"] += 1
                    if mean_p >= 0.5:
                        labels[q] = POS
            r["labels"] = labels
            r["gray_q"] = sorted(gray)
            r["planner_labels"] = sorted(planner)
            r["spec_relabel"] = prov
            f.write(json.dumps(r) + "\n")
    c = Counter(q for r in rows for q in r["labels"]); g = Counter(q for r in rows for q in r["gray_q"])
    lines = [f"spec gold: {len(rows)} specs; {dict(stats)}"]
    for q in QIDS:
        lines.append(f"  {q:<24} pos={c[q]:<4} gray={g[q]}")
    return "\n".join(lines)


MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
MD_HEAD = re.compile(r"^#{1,6}\s+", re.M)
MD_RULE = re.compile(r"^\s*(\*\*\*|---|___)\s*$", re.M)


def clean_text(t: str) -> str:
    t = MD_BOLD.sub(r"\1", t)
    t = MD_HEAD.sub("", t)
    t = MD_RULE.sub("", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def assemble(spec_gold_path: Path, rendered: Path, out: Path) -> str:
    """Join spec-level gold onto rendered text; normalize markdown artifacts."""
    specs = {json.loads(l)["id"]: json.loads(l) for l in spec_gold_path.read_text().splitlines() if l.strip()}
    rows = [json.loads(l) for l in rendered.read_text().splitlines() if l.strip()]
    with out.open("w") as f:
        for r in rows:
            s = specs[r["id"]]
            r["text"] = clean_text(r["text"])
            r["labels"] = s["labels"]
            r["gray"] = s["gray_q"]
            r["meta"]["planner_labels"] = s["planner_labels"]
            r["meta"]["spec_relabel"] = s["spec_relabel"]
            f.write(json.dumps(r) + "\n")
    return f"assembled {len(rows)} docs -> {out}"


def text_audit(labeled: Path, results: Path, keys: list[str], out: Path, corpus: str = "veridian_audit", tag: str = "audit") -> str:
    """Apply the 3-model text audit. Flip only on unanimous disagreement; gray on any disagreement
    involving >=2 auditors."""
    votes = _votes(results, corpus, "multi", keys, tag)
    rows = [json.loads(l) for l in labeled.read_text().splitlines() if l.strip()]
    stats = Counter()
    with out.open("w") as f:
        for r in rows:
            labels = dict(r["labels"]); gray = set(r["gray"]); audit: dict[str, dict] = {}
            for q in QIDS:
                vs = votes.get(r["id"], {}).get(q, [])
                if not vs:
                    continue
                audit[q] = {k: round(p, 3) for k, _, p in vs}
                yes = sum(1 for _, lab, _ in vs if lab == POS); n = len(vs)
                G = q in labels
                if G and yes == 0 and n >= 2:
                    labels.pop(q); gray.add(q); stats["flip_to_no"] += 1
                elif G and yes < n:
                    if q not in gray: stats["gray_added"] += 1
                    gray.add(q)
                elif not G and yes == n and n >= 2:
                    labels[q] = POS; gray.add(q); stats["flip_to_yes"] += 1
                elif not G and yes >= 2:
                    if q not in gray: stats["gray_added"] += 1
                    gray.add(q)
            r["labels"] = labels; r["gray"] = sorted(gray); r["meta"]["text_audit"] = audit
            f.write(json.dumps(r) + "\n")
    c = Counter(q for r in rows for q in r["labels"]); g = Counter(q for r in rows for q in r["gray"])
    lines = [f"text audit: {len(rows)} docs; {dict(stats)}"]
    for q in QIDS:
        lines.append(f"  {q:<24} pos={c[q]:<4} gray={g[q]}")
    lines.append(f"  docs with >=1 label: {sum(1 for r in rows if r['labels'])}; multi-RFP: {sum(1 for r in rows if len(r['labels'])>1)}; any gray: {sum(1 for r in rows if r['gray'])}")
    return "\n".join(lines)
