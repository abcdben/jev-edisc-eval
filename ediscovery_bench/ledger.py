"""Spend ledger: sums `cost_usd` (what we paid) and `list_cost_usd` across every prediction file,
grouped by vendor and purpose, plus the known off-harness prep costs (planner, writer)."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

VENDOR = {"jev": "TypeSafe", "laya": "Laya (local)", "lexical": "Lexical (local)", "gemma3": "Ollama (local)", "qwen3": "Ollama (local)", "claude": "Anthropic", "gpt": "OpenAI", "gemini": "Google"}
PREP = {  # from the generation logs
    ("Anthropic", "veridian manifest planner (Sonnet 5)"): 12.0,
    ("Anthropic", "veridian writer share (Sonnet 5)"): 4.76,
    ("OpenAI", "veridian writer share (Terra)"): 9.35,
    ("Google", "veridian writer share (Gemini 3.8 Flash)"): 3.59,
}


def purpose(corpus: str, tag: str) -> str:
    if corpus == "veridian_gists":
        return "gold: spec relabel"
    if corpus == "veridian_audit":
        return "gold: text audit"
    if corpus == "mnk" and tag == "panel":
        return "gold: mallinckrodt panel"
    if corpus == "veridian_pilot":
        return "effort pilot"
    if tag == "literal":
        return f"{corpus}: literal-phrasing fairness run"
    return f"{corpus}: benchmark runs"


def ledger(results: Path = Path("results")) -> str:
    paid = defaultdict(float); listed = defaultdict(float); calls = defaultdict(int)
    for f in results.rglob("*.jsonl"):
        corpus = f.parts[-3]; arm = f.parts[-2]
        stem = f.stem
        if stem.startswith(("jev__", "laya__", "laya-typed__")):
            _, rest = stem.split("__", 1)
            mk, _, tag = rest.partition("__")
        else:
            mk, _, tag = stem.partition("__")
        vendor = next((v for k, v in VENDOR.items() if stem.startswith(k)), "?")
        key = (vendor, purpose(corpus, tag))
        for line in f.open():
            r = json.loads(line)
            if r.get("error"):
                continue
            paid[key] += r["cost_usd"]; listed[key] += r["list_cost_usd"]; calls[key] += 1
    for k, v in PREP.items():
        paid[k] += v; listed[k] += v
    rows = sorted(paid)
    out = ["| vendor | purpose | decisions | paid $ | list $ |", "|---|---|---:|---:|---:|"]
    tot_p = tot_l = 0.0
    by_vendor = defaultdict(float)
    for k in rows:
        out.append(f"| {k[0]} | {k[1]} | {calls[k]:,} | {paid[k]:.2f} | {listed[k]:.2f} |")
        tot_p += paid[k]; tot_l += listed[k]; by_vendor[k[0]] += paid[k]
    out.append(f"| **total** | | | **{tot_p:.2f}** | {tot_l:.2f} |")
    out.append("")
    out.append("By vendor (paid): " + ", ".join(f"{v} ${by_vendor[v]:.2f}" for v in sorted(by_vendor)))
    return "\n".join(out)


if __name__ == "__main__":
    print(ledger())
