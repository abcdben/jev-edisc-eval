"""Paths, JSONL helpers, the OpenAI spend ledger and the small statistics used by every test."""
from __future__ import annotations

import json
import math
import random
from pathlib import Path
from typing import Callable, Iterable, Sequence

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "jev_probe"
RESULTS = ROOT / "results" / "jev_probe"
LEDGER = RESULTS / "llm_spend.jsonl"  # every OpenAI call made by this package that is not a run_job prediction

JEV = "jev@base"
LUNA, TERRA, SOL = "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"
LLMS = [LUNA, TERRA, SOL]
SEED = 23


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:  # split on \n only: str.splitlines also splits on U+2028 inside JSON strings
        return [json.loads(l) for l in f if l.strip()]


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    return n


def append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------------------------------ spend ledger

def ledger_add(step: str, model: str, cost_usd: float, n_calls: int = 1, note: str = "") -> None:
    append_jsonl(LEDGER, {"step": step, "model": model, "cost_usd": round(cost_usd, 6), "n_calls": n_calls, "note": note})


def ledger_total(steps: Sequence[str] | None = None) -> float:
    return sum(r["cost_usd"] for r in read_jsonl(LEDGER) if steps is None or r["step"] in steps)


def prediction_spend(tests: Sequence[str] | None = None, models: Sequence[str] | None = None,
                     exclude: Sequence[tuple[str, str]] = ()) -> float:
    """Paid cost of every run_job prediction row under results/jev_probe/<test>/ for the given models (OpenAI by default).

    `exclude` lists (test, tag) prediction files to leave out — used for files carried over unchanged from an archived run
    so their cost is not counted twice."""
    total = 0.0
    for d in RESULTS.iterdir() if RESULTS.exists() else []:
        if not d.is_dir() or (tests is not None and d.name not in tests):
            continue
        for f in d.glob("*/*.jsonl"):
            stem_model, tag = f.stem.split("__")[0], f.stem.split("__")[-1]
            if (d.name, tag) in exclude:
                continue
            if models is not None and stem_model not in models:
                continue
            if models is None and not stem_model.startswith("gpt-"):
                continue
            for r in read_jsonl(f):
                total += float(r.get("cost_usd") or 0.0)
    return total


# T1 v2 kept the Enron and Jeb Bush prediction files from v1 unchanged (their prompts did not change); their cost lives in t1_v1_confounded/.
T1_CARRIED_OVER = (("t1", "enron"), ("t1", "jebbush"))


# ------------------------------------------------------------------------------------------------ statistics

def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, c - h), min(1.0, c + h))


def bootstrap_ci(values: Sequence[float], stat: Callable[[Sequence[float]], float] = lambda v: sum(v) / len(v),
                 n_boot: int = 2000, seed: int = SEED, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI of `stat` over a resample of `values` (one entry per independent unit)."""
    vals = list(values)
    if not vals:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    n = len(vals)
    bs = []
    for _ in range(n_boot):
        s = [vals[rng.randrange(n)] for _ in range(n)]
        bs.append(stat(s))
    bs.sort()
    lo = bs[int(alpha / 2 * n_boot)]
    hi = bs[min(n_boot - 1, int((1 - alpha / 2) * n_boot))]
    return (lo, hi)


def paired_diff(a: Sequence[float], b: Sequence[float], n_boot: int = 2000, seed: int = SEED) -> dict:
    """Mean of (a_i - b_i) with a paired bootstrap CI over units."""
    d = [x - y for x, y in zip(a, b)]
    if not d:
        return {"n": 0, "mean": float("nan"), "ci": [float("nan"), float("nan")]}
    lo, hi = bootstrap_ci(d, n_boot=n_boot, seed=seed)
    return {"n": len(d), "mean": sum(d) / len(d), "ci": [lo, hi]}


def mcnemar(b: int, c: int) -> float:
    """Exact two-sided McNemar p from the discordant counts (b: A yes / B no, c: A no / B yes)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def mann_whitney_p(x: Sequence[float], y: Sequence[float]) -> float:
    """Two-sided Mann-Whitney U with the normal approximation (ties averaged)."""
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return float("nan")
    allv = sorted([(v, 0) for v in x] + [(v, 1) for v in y])
    ranks = [0.0] * len(allv)
    i = 0
    while i < len(allv):
        j = i
        while j + 1 < len(allv) and allv[j + 1][0] == allv[i][0]:
            j += 1
        r = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[k] = r
        i = j + 1
    rx = sum(r for r, (_, g) in zip(ranks, allv) if g == 0)
    u = rx - nx * (nx + 1) / 2
    mu = nx * ny / 2
    # tie correction
    from collections import Counter

    t = Counter(v for v, _ in allv)
    n = nx + ny
    tc = sum(c ** 3 - c for c in t.values())
    sigma = math.sqrt(nx * ny / 12 * ((n + 1) - tc / (n * (n - 1)))) if n > 1 else 0.0
    if sigma == 0:
        return 1.0
    z = (u - mu) / sigma
    return math.erfc(abs(z) / math.sqrt(2))


def fmt_pct(x: float, nd: int = 1) -> str:
    return "—" if x != x else f"{100 * x:.{nd}f}%"


def fmt_pp(x: float, nd: int = 1) -> str:
    return "—" if x != x else f"{100 * x:+.{nd}f} pp"


def fmt_ci_pp(ci: Sequence[float], nd: int = 1) -> str:
    if not ci or ci[0] != ci[0]:
        return "—"
    return f"[{100 * ci[0]:+.{nd}f}, {100 * ci[1]:+.{nd}f}]"
