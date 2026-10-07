"""Pseudonymisation ablation, round 2 — CUAD (rename + paraphrase) and the Jeb Bush e-mail (matter vs control topics).

Arms and conditions (design/07_ablation_round2.md):

  cuad       1,200 CUAD excerpts (every excerpt carrying a positive label + negatives spread over all 102 contracts)
             named       original excerpts                                          results/ablation/round2/cuad/multi/<model>__named__all.jsonl
             renamed     parties, aliases, products, dates, amounts, jurisdictions renamed per contract (cuad_names.ContractRenamer)
             paraphrased body rewritten by GPT-5.6 Luna, legal content preserved (paraphrase.py), header kept
  veridian   500 of the round-1 Veridian documents, paraphrased with the same pipeline (e-mail variant): the perturbation-cost control
             for the paraphrase arm. Its named rows are the round-1 results (results/ablation/veridian/multi/<model>__named__all.jsonl).
  jeb        the 600 locally available Jeb Bush e-mails, all 11 requests per call
             named       original e-mails + the study context
             renamed     the Governor, his family, staff and the Florida public figures renamed (jeb_names.JebRenamer); Florida kept

Data files (data/ablation/): cuad.jsonl, cuad__renamed.jsonl, cuad__paraphrased.jsonl, cuad_mapping.json, veridian__paraphrased.jsonl,
jeb.jsonl, jeb__renamed.jsonl, jeb_mapping.json, jeb__renamed.yaml, cuad_memo.jsonl (+ cuad_memo.json), cuad_paraphrase_check.jsonl,
veridian_paraphrase_check.jsonl, round2_spend.json (every paid step, estimated vs realised).
"""
from __future__ import annotations

import asyncio
import json
import random
import re
import statistics
import time
from collections import Counter, defaultdict
from pathlib import Path

from ..config import MODELS
from ..providers import parse_model_key
from ..providers.openai_ import CACHE_READ_MULT, FLEX_MULT
from ..runner import job_path, load_predictions, run_job
from ..tasks import Document, TaskSet
from .build import DATA, ROOT, renamed_taskset
from .cuad_names import ContractRenamer
from .jeb_names import build_jeb_renamer, jeb_dose_renamer, load_jeb_renamer
from .run import ALL_MODELS, JEV, LLM_MODELS, key_available
from .run import RESULTS as R1_RESULTS

RESULTS = ROOT / "results" / "ablation" / "round2"
SEED = 23
CUAD_N = 1200
VERIDIAN_N = 500
SPEND = DATA / "round2_spend.json"

ARMS2 = {
    "cuad": {"src": ROOT / "data" / "cuad" / "cuad.jsonl", "task": "tasks/cuad.yaml", "conditions": ("named", "renamed", "paraphrased"), "genre": "contract"},
    "veridian": {"src": DATA / "veridian.jsonl", "task": "tasks/veridian.yaml", "conditions": ("paraphrased",), "genre": "email"},
    "jeb": {"src": ROOT / "data" / "trec" / "local_subset.jsonl", "task": "tasks/trec.yaml", "conditions": ("named", "renamed"), "genre": "email"},
}
JEB_MATTER = ["recount_2000", "rilya_wilson", "medicaid_reform", "gw_bush", "a1_terri_schiavo"]
JEB_CONTROL = ["movie_gallery", "condominiums", "bottled_water", "marketing", "faith_based", "nra_rifle", "nra_aliens"]
JEB_YEARS_RE = re.compile(r"\s*\(1999-2007\)")
JEB_N = 1000
JEB_POS_PER_TOPIC = 60
JEB_ZIP = ROOT / "data" / "TREC 2016 - Jeb Bush.zip"
JEB_TXT = ROOT / "data" / "trec" / "raw" / "jeb_bush_txt"
JEB_EVAL = ROOT / "data" / "trec" / "eval.jsonl"

# Terri Schiavo: the 2015 athome1 topic (complete NIST judgments, title-only topic definition). Request text written for round 2 in the
# style of tasks/trec.yaml; the matter-specific topic the knowledge probes showed the models recite most readily (Terri's Law, 2003-05).
SCHIAVO_QUESTION = dict(
    id="a1_terri_schiavo", title="Terri Schiavo",
    rfp_text="All documents concerning Terri Schiavo, the dispute over her care, and the actions of the Governor, the Legislature or the courts in her case.",
    positive_desc=("The email concerns Terri Schiavo, the Florida woman in a persistent vegetative state whose husband and parents (Robert and Mary Schindler) "
                   "fought in court over removing her feeding tube: the litigation, the Legislature's \"Terri's Law\" (2003) and the Governor's "
                   "intervention under it, the 2005 legislative and federal efforts, the Governor's statements or decisions in the case, DCF's "
                   "involvement, and constituents writing to the Governor for or against keeping her alive or about the case. Right-to-die, "
                   "end-of-life and guardianship discussion that is prompted by or refers to her case is responsive."),
    negative_desc=("The email does not concern Terri Schiavo or the dispute over her care. Other end-of-life, disability, health-care or "
                   "guardianship matters with no reference to her case are not responsive."),
)


def _rows(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text().split("\n") if l.strip()]


def _write(path: Path, rows: list[dict]):
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _docs(rows: list[dict]) -> list[Document]:
    return [Document(id=r["id"], text=r["text"], labels=r.get("labels") or {}, gray=frozenset(r.get("gray") or []), meta=r.get("meta") or {}) for r in rows]


def record_spend(step: str, estimate: float | None, realised: float, detail: dict | None = None):
    rec = json.loads(SPEND.read_text()) if SPEND.exists() else {"steps": []}
    rec["steps"] = [s for s in rec["steps"] if s["step"] != step]
    rec["steps"].append({"step": step, "estimate_usd": estimate, "realised_usd": round(realised, 4), "at": time.strftime("%Y-%m-%d %H:%M"), **(detail or {})})
    rec["total_realised_usd"] = round(sum(s["realised_usd"] for s in rec["steps"]), 4)
    rec["total_estimate_usd"] = round(sum(s["estimate_usd"] or 0 for s in rec["steps"]), 4)
    SPEND.write_text(json.dumps(rec, indent=1))
    return rec


# ------------------------------------------------------------------------------------------------ sampling

def sample_cuad(rng: random.Random) -> list[dict]:
    rows = _rows(ARMS2["cuad"]["src"])
    pos = [r for r in rows if any(v == "responsive" for v in r["labels"].values())]
    neg_by: dict[int, list[dict]] = defaultdict(list)
    for r in rows:
        if r not in pos:
            neg_by[r["meta"]["contract_idx"]].append(r)
    for v in neg_by.values():
        rng.shuffle(v)
    out = list(pos)
    need = CUAD_N - len(pos)
    order = sorted(neg_by)
    rng.shuffle(order)
    while need > 0 and any(neg_by.values()):
        for ci in order:
            if need <= 0:
                break
            if neg_by[ci]:
                out.append(neg_by[ci].pop())
                need -= 1
    return sorted(out, key=lambda r: r["id"])


def extract_jeb_texts(log=print) -> int:
    """Pull the study's 3,116 eval e-mails out of the user's zip of the collection into data/trec/raw/jeb_bush_txt/ (gitignored) and
    write data/trec/eval.jsonl exactly as `bench trec-build` would (same normalisation as trec.build.read_email). Nothing else is
    extracted: the collection is under NIST's usage agreement and the other 287k files are not needed."""
    import zipfile  # noqa: PLC0415

    ids = _rows(ROOT / "data" / "trec" / "eval_ids.jsonl")
    JEB_TXT.mkdir(parents=True, exist_ok=True)
    want = {r["meta"]["docno"]: r for r in ids}
    missing = [d for d in want if not (JEB_TXT / f"{int(d)}.txt").exists()]
    if missing:
        if not JEB_ZIP.exists():
            raise FileNotFoundError(f"{JEB_ZIP} not found and {len(missing)} eval e-mails are not extracted")
        with zipfile.ZipFile(JEB_ZIP) as z:
            names = {n.rsplit("/", 1)[-1]: n for n in z.namelist() if n.startswith("Jeb Bush TXT/") and n.endswith(".txt")}
            for d in missing:
                n = names.get(f"{int(d)}.txt")
                if n is None:
                    log(f"  !! docno {d} not in zip")
                    continue
                (JEB_TXT / f"{int(d)}.txt").write_bytes(z.read(n))
        log(f"extracted {len(missing)} e-mails from {JEB_ZIP.name} to {JEB_TXT.relative_to(ROOT)}")
    out = []
    for r in ids:
        p = JEB_TXT / f"{int(r['meta']['docno'])}.txt"
        if not p.exists():
            continue
        b = p.read_bytes()
        try:
            t = b.decode("utf-8")
        except UnicodeDecodeError:
            t = b.decode("latin-1")
        t = re.sub(r"\n{3,}", "\n\n", t.replace("\r\n", "\n").replace("\r", "\n")).strip()
        out.append({"id": r["id"], "text": t, "labels": r["labels"], "gray": r.get("gray") or [], "meta": r["meta"]})
    _write(JEB_EVAL, out)
    log(f"wrote {JEB_EVAL.relative_to(ROOT)}: {len(out)} e-mails with text")
    return len(out)


def sample_jeb(rng: random.Random) -> list[dict]:
    """~1,000 e-mails from the study's eval sample: up to JEB_POS_PER_TOPIC gold positives per topic (matter and control), the rest
    hard-negative and random-stratum e-mails. The same documents serve both conditions. Falls back to the 600-e-mail local subset
    (all of it) when eval.jsonl cannot be built."""
    if not JEB_EVAL.exists() and (JEB_ZIP.exists() or JEB_TXT.exists()):
        extract_jeb_texts()
    rows = _rows(JEB_EVAL) if JEB_EVAL.exists() else _rows(ARMS2["jeb"]["src"])
    keep = JEB_MATTER + JEB_CONTROL
    rows = [r for r in rows if len(r["text"]) <= 12000]
    chosen: dict[str, dict] = {}
    if JEB_EVAL.exists():
        pos_by: dict[str, list[dict]] = defaultdict(list)
        for r in rows:
            for q in keep:
                if r["labels"].get(q) == "responsive":
                    pos_by[q].append(r)
        for q in sorted(keep, key=lambda q: len(pos_by[q])):  # scarce topics first so their positives are not used up by others
            cands = [r for r in pos_by[q] if r["id"] not in chosen]
            have = sum(1 for r in chosen.values() if r["labels"].get(q) == "responsive")
            rng.shuffle(cands)
            for r in cands[: max(0, JEB_POS_PER_TOPIC - have)]:
                chosen[r["id"]] = r
        neg = [r for r in rows if r["id"] not in chosen and not any(r["labels"].get(q) == "responsive" for q in keep)]
        hard = [r for r in neg if r["meta"]["stratum"] == "hard_neg"]
        rand = [r for r in neg if r["meta"]["stratum"] == "random"]
        rng.shuffle(hard)
        rng.shuffle(rand)
        need = JEB_N - len(chosen)
        for r in hard[: need // 2] + rand[: need - need // 2]:
            chosen[r["id"]] = r
        rows = list(chosen.values())
    out = []
    for r in rows:
        rr = dict(r)
        rr["labels"] = {q: l for q, l in r["labels"].items() if q in keep}
        rr["gray"] = [q for q in (r.get("gray") or []) if q in keep]
        out.append(rr)
    return sorted(out, key=lambda r: r["id"])


def sample_veridian(rng: random.Random) -> list[dict]:
    rows = _rows(ARMS2["veridian"]["src"])
    rng.shuffle(rows)
    return sorted(rows[:VERIDIAN_N], key=lambda r: r["id"])


# ------------------------------------------------------------------------------------------------ build (no API calls)

def build(log=print) -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)
    info: dict = {}

    # ---- CUAD: sample + per-contract rename
    cuad = sample_cuad(rng)
    all_rows = _rows(ARMS2["cuad"]["src"])
    by_contract: dict[int, list[dict]] = defaultdict(list)
    for r in all_rows:
        by_contract[r["meta"]["contract_idx"]].append(r)
    renamers = {ci: ContractRenamer(ci, [r["text"] for r in sorted(rs, key=lambda r: r["meta"]["para_idx"])]) for ci, rs in by_contract.items()}
    renamed, mapping, unchanged = [], {}, 0
    for r in cuad:
        rn = renamers[r["meta"]["contract_idx"]]
        t = rn.apply(r["text"])
        if t == r["text"]:
            unchanged += 1
        renamed.append({**r, "text": t, "meta": {**r["meta"], "n_sub": rn.n_sub}})
    for ci, rn in sorted(renamers.items()):
        mapping[str(ci)] = {"contract": by_contract[ci][0]["meta"]["contract"], **rn.info()}
    _write(DATA / "cuad.jsonl", cuad)
    _write(DATA / "cuad__renamed.jsonl", renamed)
    (DATA / "cuad_mapping.json").write_text(json.dumps(mapping, indent=1, ensure_ascii=False))
    n_pos = sum(1 for r in cuad if any(v == "responsive" for v in r["labels"].values()))
    n_lab = sum(sum(1 for v in r["labels"].values() if v == "responsive") for r in cuad)
    info["cuad"] = {"n": len(cuad), "positive_excerpts": n_pos, "positive_labels": n_lab, "contracts": len({r["meta"]["contract_idx"] for r in cuad}),
                    "gray_excerpts": sum(1 for r in cuad if r.get("gray")), "mean_chars": round(statistics.mean(len(r["text"]) for r in cuad)),
                    "renamed_unchanged": unchanged, "phrases_total": sum(len(m["phrases"]) for m in mapping.values()),
                    "contracts_with_people": sum(1 for m in mapping.values() if m["people"])}
    log(f"cuad: {len(cuad)} excerpts ({n_pos} with a positive, {n_lab} positive labels, {info['cuad']['contracts']} contracts); "
        f"renamed: {info['cuad']['phrases_total']} phrases, {unchanged} excerpts unchanged")

    # ---- Veridian paraphrase-control subset (paraphrased file is written by `paraphrase`)
    ver = sample_veridian(rng)
    _write(DATA / "veridian__para_subset.jsonl", ver)
    info["veridian"] = {"n": len(ver), "mean_chars": round(statistics.mean(len(r["text"]) for r in ver))}

    # ---- Jeb Bush
    jeb = sample_jeb(rng)
    texts = [r["text"] for r in jeb]
    rn, jinfo = build_jeb_renamer(texts, log=log)
    dose_rn = jeb_dose_renamer()
    jeb_named, jeb_renamed = [], []
    for r in jeb:
        d = dose_rn.count_hits(r["text"])
        jeb_named.append({**r, "meta": {**r["meta"], "dose": d}})
        jeb_renamed.append({**r, "text": rn.apply(r["text"]), "meta": {**r["meta"], "dose": d}})
    residual = sum(1 for r in jeb_renamed if re.search(r"\bjeb\b|\bbush\b", r["text"], re.I))
    _write(DATA / "jeb.jsonl", jeb_named)
    _write(DATA / "jeb__renamed.jsonl", jeb_renamed)
    (DATA / "jeb_mapping.json").write_text(json.dumps(jinfo, indent=1, ensure_ascii=False))
    rts = jeb_tasksets(rn)["renamed"]
    (DATA / "jeb__renamed.yaml").write_text(_taskset_yaml(rts))
    pos = Counter(q for r in jeb for q, l in r["labels"].items() if l == "responsive")
    info["jeb"] = {"n": len(jeb), "source": "eval.jsonl" if JEB_EVAL.exists() else "local_subset.jsonl",
                   "strata": dict(Counter(r["meta"].get("stratum", "?").split(":")[0] for r in jeb)),
                   "positives_matter": {q: pos[q] for q in JEB_MATTER}, "positives_control": {q: pos[q] for q in JEB_CONTROL},
                   "mean_chars": round(statistics.mean(len(t) for t in texts)), "residual_jeb_bush_docs": residual,
                   "dose_bands": dict(Counter("0" if d == 0 else "1-2" if d <= 2 else "3+" for d in (r["meta"]["dose"] for r in jeb_named))),
                   "phrases": len(jinfo["phrases"]), "people": len(jinfo["people"])}
    log(f"jeb: {len(jeb)} e-mails from {info['jeb']['source']}; matter positives {sum(pos[q] for q in JEB_MATTER)}, control positives "
        f"{sum(pos[q] for q in JEB_CONTROL)}; renamed: {len(jinfo['people'])} people, residual Jeb/Bush in {residual} docs")
    (DATA / "round2_build.json").write_text(json.dumps(info, indent=1))
    return info


def _taskset_yaml(ts: TaskSet) -> str:
    import yaml  # noqa: PLC0415

    d = {"name": ts.name, "kind": "binary", "positive_label": ts.positive_label, "negative_label": ts.negative_label, "context": ts.context,
         "gate_question": ts.gate_question, "questions": {}}
    for qid, q in ts.questions.items():
        d["questions"][qid] = {"title": q.title, "rfp_text": q.rfp_text, "positive_desc": q.positive_desc, "negative_desc": q.negative_desc,
                               **({"literal": q.literal} if q.literal else {})}
    return "# Generated by `bench ablation2-build`: the TREC task set with the Governor and the public figures renamed (jeb_names.py).\n" + yaml.safe_dump(d, sort_keys=False, allow_unicode=True, width=120)


# ------------------------------------------------------------------------------------------------ task sets per arm × condition

def jeb_base_taskset() -> TaskSet:
    """The study's TREC task set restricted to the round-2 topics, plus the Terri Schiavo request (athome1 gold)."""
    from ..tasks import Question  # noqa: PLC0415

    base = TaskSet.load(ROOT / ARMS2["jeb"]["task"])
    qs = {q: base.questions[q] for q in JEB_MATTER + JEB_CONTROL if q in base.questions}
    for q in JEB_MATTER + JEB_CONTROL:
        if q not in qs and q == SCHIAVO_QUESTION["id"]:
            qs[q] = Question(**SCHIAVO_QUESTION)
    return TaskSet(name=base.name, context=base.context, questions=qs, positive_label=base.positive_label, negative_label=base.negative_label,
                   gate_question=base.gate_question, source=base.source)


def jeb_tasksets(rn=None) -> dict[str, TaskSet]:
    ts = jeb_base_taskset()
    if rn is None:
        rn = load_jeb_renamer(json.loads((DATA / "jeb_mapping.json").read_text()))
    rts = renamed_taskset(ts, rn)
    rts = TaskSet(name=rts.name, context=JEB_YEARS_RE.sub("", rts.context), questions=rts.questions, positive_label=rts.positive_label,
                  negative_label=rts.negative_label, gate_question=rts.gate_question, source=rts.source)
    return {"named": ts, "renamed": rts}


def arm_taskset(arm: str, condition: str) -> TaskSet:
    if arm == "jeb":
        return jeb_tasksets()[condition]
    return TaskSet.load(ROOT / ARMS2[arm]["task"])  # CUAD / Veridian contexts contain nothing to rename; one task set, one prompt cache


def arm_docs(arm: str, condition: str) -> list[Document]:
    if condition == "named":
        return _docs(_rows(DATA / f"{arm}.jsonl"))
    return _docs(_rows(DATA / f"{arm}__{condition}.jsonl"))


# ------------------------------------------------------------------------------------------------ paid steps

async def paraphrase(arms=("cuad", "veridian"), limit: int | None = None, log=print) -> dict:
    """Write <arm>__paraphrased.jsonl with Luna; deterministic checks per row; resumable."""
    from .paraphrase import paraphrase_rows

    out = {}
    for arm in arms:
        src = DATA / ("veridian__para_subset.jsonl" if arm == "veridian" else f"{arm}.jsonl")
        rows = _rows(src)
        if limit:
            rows = rows[:limit]
        est = estimate_paraphrase(rows)
        prows, stats = await paraphrase_rows(rows, ARMS2[arm]["genre"], DATA / f"{arm}__paraphrased.cache.jsonl", log=log)
        if not limit:
            _write(DATA / f"{arm}__paraphrased.jsonl", prows)
        record_spend(f"paraphrase:{arm}" + (f":pilot{limit}" if limit else ""), est, stats["paid_usd_total"], {"n": len(rows), "ok": stats["ok"], "retried": stats["retried"]})
        out[arm] = stats
    return out


async def fidelity(n_cuad: int = 100, n_ver: int = 50, log=print) -> dict:
    from .paraphrase import fidelity_judge, split_header

    rng = random.Random(5)
    out = {}
    for arm, n in (("cuad", n_cuad), ("veridian", n_ver)):
        orig = {r["id"]: r["text"] for r in _rows(DATA / ("veridian__para_subset.jsonl" if arm == "veridian" else f"{arm}.jsonl"))}
        para_path = DATA / f"{arm}__paraphrased.jsonl"
        if not para_path.exists():
            para = {r["id"]: r["text"] for r in _rows(DATA / f"{arm}__paraphrased.cache.jsonl")}
        else:
            para = {r["id"]: r["text"] for r in _rows(para_path)}
        ids = sorted(set(orig) & set(para))
        rng.shuffle(ids)
        pairs = [(i, split_header(orig[i])[1], split_header(para[i])[1]) for i in ids[:n]]
        est = len(pairs) * 0.0016
        summ = await fidelity_judge(pairs, ARMS2[arm]["genre"], DATA / f"{arm}_paraphrase_check.jsonl", log=log)
        record_spend(f"fidelity:{arm}", est, summ["paid_usd_total"], {"n": summ["n"], "equivalent": summ["equivalent"]})
        out[arm] = summ
    return out


async def memo(per_contract: int = 2, limit_contracts: int | None = None, models=None, log=print) -> dict:
    """Finish-the-document probe on 2 windows per contract × {original, renamed, paraphrased} × 3 OpenAI models."""
    from .paraphrase import MEMO_MODELS, contract_windows, memo_probe, memo_summary

    models = models or MEMO_MODELS
    all_rows = _rows(ARMS2["cuad"]["src"])
    by_all: dict[int, list[dict]] = defaultdict(list)
    for r in all_rows:
        by_all[r["meta"]["contract_idx"]].append(r)
    # windows are taken from the sampled excerpts (which have paraphrases); contracts with no long enough sampled excerpt fall back to any excerpt
    by: dict[int, list[dict]] = defaultdict(list)
    for r in _rows(DATA / "cuad.jsonl"):
        by[r["meta"]["contract_idx"]].append(r)
    if limit_contracts:
        by = {ci: by[ci] for ci in sorted(by)[:limit_contracts]}
        by_all = {ci: by_all[ci] for ci in by}
    renamers = {ci: ContractRenamer(ci, [r["text"] for r in sorted(rs, key=lambda r: r["meta"]["para_idx"])]) for ci, rs in by_all.items()}
    renamed = {r["id"]: renamers[ci].apply(r["text"]) for ci, rs in by_all.items() for r in rs}
    para_path = DATA / "cuad__paraphrased.cache.jsonl"
    para = {r["id"]: r["text"] for r in _rows(para_path)} if para_path.exists() else {}
    variants = {"renamed": renamed, "paraphrased": para}
    items = contract_windows(by, variants, per_contract=per_contract)
    covered = {it["contract_idx"] for it in items}
    missing = {ci: rs for ci, rs in by_all.items() if ci not in covered}
    if missing:
        items += contract_windows(missing, variants, per_contract=per_contract)
        log(f"memo probe: {len(missing)} contracts had no sampled excerpt long enough; windows taken from unsampled excerpts (no paraphrase variant)")
    n_calls = sum(1 + len(it["variants"]) for it in items) * len(models)
    est = sum(_memo_call_cost(m) for m in models) * sum(1 + len(it["variants"]) for it in items)
    log(f"memo probe: {len(items)} windows over {len({it['contract_idx'] for it in items})} contracts, {n_calls} calls, est ${est:.2f}")
    recs = await memo_probe(items, DATA / "cuad_memo.jsonl", models=models, log=log)
    summ = memo_summary(recs)
    (DATA / "cuad_memo.json").write_text(json.dumps(summ, indent=1))
    realised = sum(r["cost_usd"] for r in recs)
    record_spend("memo_probe", est, realised, {"windows": len(items), "responses": len(recs)})
    return summ


def _memo_call_cost(model: str, in_tok: int = 420, out_tok: int = 100) -> float:
    s = MODELS[model]
    return (in_tok * s.input_per_mtok + out_tok * s.output_per_mtok) / 1e6 * FLEX_MULT


def dedupe(path: Path, log=print) -> float:
    """Keep the first row per (document, question). Two writers on one result file (a run restarted while the first was still going)
    leave duplicate rows; the duplicates' cost was paid and is recorded in the ledger as waste. Returns the wasted cost."""
    if not path.exists():
        return 0.0
    rows = [json.loads(l) for l in path.read_text().split("\n") if l.strip()]
    seen, keep, waste = set(), [], 0.0
    for r in rows:
        k = (r["doc_id"], r["question"])
        if k in seen and not r.get("error"):
            waste += r.get("cost_usd") or 0.0
            continue
        if not r.get("error"):
            seen.add(k)
        keep.append(r)
    if len(keep) < len(rows):
        with path.open("w") as f:
            for r in keep:
                f.write(json.dumps(r) + "\n")
        rec = json.loads(SPEND.read_text()) if SPEND.exists() else {"steps": []}
        prev = next((s for s in rec["steps"] if s["step"] == "duplicate_rows_waste"), None)
        record_spend("duplicate_rows_waste", 0.0, (prev["realised_usd"] if prev else 0.0) + waste,
                     {"files": sorted(set((prev or {}).get("files", []) + [str(path.resolve().relative_to(ROOT.resolve()))]))})
        log(f"  deduped {path.name}: {len(rows) - len(keep)} duplicate rows removed (${waste:.3f} wasted)")
    return waste


async def run(models: list[str], arms: list[str], conditions: list[str] | None = None, limit: int | None = None, concurrency: int | None = None, log=print) -> dict:
    """Classification runs through the ordinary runner → results/ablation/round2/<arm>/multi/<model>__<condition>__all.jsonl.
    Stops before a run whose realised cost is tracking > 25 % over the estimate (checked after each arm × condition × model)."""
    spent: Counter = Counter()
    listed: Counter = Counter()
    pending = [m for m in models if not key_available(m)]
    for m in pending:
        log(f"[pending] {m}: key not set — skipped")
    live = [m for m in models if key_available(m)]
    est_table = estimate_runs()
    n_rows = 0
    t0 = time.time()
    overruns = []
    for arm in arms:
        for cond in (conditions or ARMS2[arm]["conditions"]):
            ts = arm_taskset(arm, cond)
            docs = arm_docs(arm, cond)
            if limit:
                docs = docs[:limit]
            for m in live:
                tag = f"{cond}__all" + (f"__pilot{limit}" if limit else "")
                dedupe(job_path(RESULTS, arm, "multi", m, tag), log=log)
                before = {(p.doc_id, p.question) for p in load_predictions(job_path(RESULTS, arm, "multi", m, tag)) if not p.error}
                preds = await run_job(ts, docs, m, "multi", RESULTS, arm, concurrency=concurrency, tag=tag, log=log)
                new = [p for p in preds if (p.doc_id, p.question) not in before and not p.error]
                paid = sum(p.cost_usd for p in new)
                spent[m] += paid
                listed[m] += sum(p.list_cost_usd for p in new)
                n_rows += len(new)
                ok = [p for p in preds if not p.error]
                realised = sum(p.cost_usd for p in ok)
                est = est_table.get(arm, {}).get(cond, {}).get(m, {}).get("paid")
                if not limit and est:
                    record_spend(f"run:{arm}:{cond}:{m}", est, realised, {"rows": len(ok), "docs": len({p.doc_id for p in ok})})
                    ratio = realised / est if est else 0
                    log(f"  {arm}/{cond}/{m}: {len(ok)} rows, paid ${realised:.3f} vs est ${est:.3f} ({ratio:.0%})")
                    if ratio > 1.25 and len(ok) >= 0.5 * len(docs) * len(ts.qids):
                        overruns.append((arm, cond, m, realised, est))
                        log(f"  !! {arm}/{cond}/{m} realised cost {ratio:.0%} of estimate — stopping per budget rule")
                        return {"spent": dict(spent), "list": dict(listed), "pending": pending, "rows": n_rows, "overrun": overruns}
    log(f"ablation2 run: {n_rows} new rows in {time.time() - t0:.0f}s; paid ${sum(spent.values()):.2f} (list ${sum(listed.values()):.2f})")
    return {"spent": dict(spent), "list": dict(listed), "pending": pending, "rows": n_rows, "overrun": overruns}


# ------------------------------------------------------------------------------------------------ cost estimates (exact token accounting)

# observed per-call token means from the study runs (multi arm, 12 / 12 / 10 questions), used to derive the prompt-only token counts
_OBS = {
    # corpus: (mean doc chars in that run, input tokens per call, cached tokens, output tokens) for the OpenAI models; Jev input separately
    "cuad": {"doc_chars": 800, "in": 3746, "cached": 1344, "out": 216, "jev_in": 2591, "jev_out": 216},
    "jeb": {"doc_chars": None, "in": 4812, "cached": 1350, "out": 227, "jev_in": 3708, "jev_out": 228},
    "veridian": {"doc_chars": None, "in": None, "cached": None, "out": None, "jev_in": None, "jev_out": None},
}


def _trec_eval_mean_chars() -> float:
    rows = _rows(ROOT / "data" / "trec" / "eval_ids.jsonl")
    return statistics.mean(min(12000, r["meta"]["n_chars"]) for r in rows)


def _veridian_obs() -> dict:
    """Per-call token means from the round-1 Veridian named run (Luna) and Jev."""
    f = R1_RESULTS / "veridian" / "multi" / "gpt-5.6-luna__named__all.jsonl"
    j = R1_RESULTS / "veridian" / "multi" / "jev__base__named__all.jsonl"
    ps = [p for p in load_predictions(f) if not p.error]
    js = [p for p in load_predictions(j) if not p.error] if j.exists() else []
    docs = {p.doc_id for p in ps}
    rows = {r["id"]: len(r["text"]) for r in _rows(DATA / "veridian.jsonl")}
    n = max(1, len(docs))
    return {"doc_chars": statistics.mean(rows[d] for d in docs if d in rows), "in": sum(p.input_tokens for p in ps) / n, "cached": sum(p.cached_tokens for p in ps) / n,
            "out": sum(p.output_tokens for p in ps) / n, "jev_in": (sum(p.input_tokens for p in js) / max(1, len({p.doc_id for p in js}))) if js else 0,
            "jev_out": (sum(p.output_tokens for p in js) / max(1, len({p.doc_id for p in js}))) if js else 0}


def call_cost(model: str, in_tok: float, cached: float, out_tok: float) -> tuple[float, float]:
    """(paid, list) for one call. OpenAI: flex × (uncached + 0.1 × cached) input + output. Jev: input only, no discounts."""
    spec, _ = parse_model_key(model)
    listed = spec.cost_usd(int(in_tok), int(out_tok))
    if spec.provider == "openai":
        paid = ((in_tok - cached) * spec.input_per_mtok + cached * spec.input_per_mtok * CACHE_READ_MULT + out_tok * spec.output_per_mtok) / 1e6 * FLEX_MULT
    else:
        paid = listed
    return paid, listed


def estimate_runs(models: list[str] = ALL_MODELS) -> dict:
    """arm → condition → model → {calls, paid, list}: prompt tokens from the observed study runs, document tokens from the actual
    texts of the built arm files (chars / 4), output tokens as observed, scaled by the number of questions."""
    out: dict = {}
    obs = dict(_OBS)
    if (DATA / "veridian.jsonl").exists() and (R1_RESULTS / "veridian" / "multi" / "gpt-5.6-luna__named__all.jsonl").exists():
        obs["veridian"] = _veridian_obs()
    if obs["jeb"]["doc_chars"] is None:
        obs["jeb"] = {**obs["jeb"], "doc_chars": _trec_eval_mean_chars()}
    for arm, spec in ARMS2.items():
        o = obs[arm]
        if not o.get("in"):
            continue
        ts = TaskSet.load(ROOT / spec["task"])
        nq_obs = len(ts.qids) + (1 if arm == "jeb" else 0)  # the observed TREC runs carried 12 questions (eminent_domain included)
        nq = len(JEB_MATTER + JEB_CONTROL) if arm == "jeb" else nq_obs
        q_scale = nq / nq_obs
        out[arm] = {}
        for cond in spec["conditions"]:
            path = DATA / (f"{arm}.jsonl" if cond == "named" else f"{arm}__{cond}.jsonl")
            if not path.exists():
                path = DATA / ("veridian__para_subset.jsonl" if arm == "veridian" else f"{arm}.jsonl")
            if not path.exists():
                continue
            lens = [min(12000, len(r["text"])) for r in _rows(path)]
            n = len(lens)
            d_tok = statistics.mean(lens) / 4
            d_obs = o["doc_chars"] / 4
            prompt_in = (o["in"] - d_obs) * q_scale
            jev_prompt = (o["jev_in"] - d_obs) * q_scale
            out[arm][cond] = {}
            for m in models:
                if m == JEV:
                    paid, listed = call_cost(m, jev_prompt + d_tok, 0, o["jev_out"] * q_scale)
                else:
                    paid, listed = call_cost(m, prompt_in + d_tok, o["cached"] * q_scale, o["out"] * q_scale)
                out[arm][cond][m] = {"calls": n, "paid": round(paid * n, 3), "list": round(listed * n, 3), "paid_per_call": round(paid, 5)}
    return out


def estimate_paraphrase(rows: list[dict], model: str = "gpt-5.6-luna", retry_rate: float = 0.15) -> float:
    s = MODELS[model]
    tot = 0.0
    for r in rows:
        body = len(r["text"]) / 4
        tot += ((body + 330) * s.input_per_mtok + body * 1.05 * s.output_per_mtok) / 1e6 * FLEX_MULT
    return round(tot * (1 + retry_rate), 3)


def cost_table(models: list[str] = ALL_MODELS, log=print) -> dict:
    """Full estimate for every paid step: classification runs per arm × condition × system, paraphrase generation, fidelity judge,
    memorisation probe, leak checks. Also a 'cheap' variant."""
    runs = estimate_runs(models)
    rows_c = _rows(DATA / "cuad.jsonl") if (DATA / "cuad.jsonl").exists() else []
    rows_v = _rows(DATA / "veridian__para_subset.jsonl") if (DATA / "veridian__para_subset.jsonl").exists() else []
    gen = {"paraphrase:cuad": estimate_paraphrase(rows_c), "paraphrase:veridian": estimate_paraphrase(rows_v),
           "fidelity_judge(100+50, Terra)": round(150 * 0.0016, 3),
           "memo_probe(102×2×3 variants×3 models)": round(sum(_memo_call_cost(m) for m in LLM_MODELS) * 102 * 2 * 3, 3),
           "leak_check(jeb 150 + cuad 102, 3 LLMs)": round(sum(call_cost(m, 900, 0, 150)[0] for m in LLM_MODELS) * 252, 3)}
    full_runs = sum(v["paid"] for arm in runs.values() for cond in arm.values() for v in cond.values())
    full = full_runs + sum(gen.values())
    # cheap: drop Terra everywhere (Luna and Sol span the price/quality range; Sol carries the strongest CUAD memorisation signal);
    # everything else as in the full version
    cheap_runs = 0.0
    cheap_detail = {}
    for arm, conds in runs.items():
        for cond, ms in conds.items():
            for m, v in ms.items():
                if m == "gpt-5.6-terra":
                    continue
                cheap_detail[f"{arm}:{cond}:{m}"] = v["paid"]
                cheap_runs += v["paid"]
    cheap_gen = dict(gen)
    cheap = cheap_runs + sum(cheap_gen.values())
    out = {"runs": runs, "generation": gen, "full_total_paid": round(full, 2), "full_runs_paid": round(full_runs, 2),
           "cheap": {"runs": cheap_detail, "generation": cheap_gen, "total_paid": round(cheap, 2)},
           "openai_only_full": round(full - sum(v["paid"] for arm in runs.values() for cond in arm.values() for m, v in cond.items() if m == JEV), 2)}
    log(f"cost table: full ${full:.2f} paid (runs ${full_runs:.2f}; OpenAI key ${out['openai_only_full']:.2f}); cheap ${cheap:.2f}")
    return out


# ------------------------------------------------------------------------------------------------ leak checks

JEB_LEAK_SYSTEM = ("You are a records analyst. You will be shown an e-mail from a public-records collection in which the people's names "
                   "have been changed. Say whose office or e-mail collection the message most likely comes from — which real public "
                   "official — and why. If you cannot tell, say so.")
JEB_LEAK_USER = ("{doc}\n\nWhich real public official's e-mail collection is this from? Name the person first (one name, or \"cannot tell\"), "
                 "then give your reasons in two or three sentences.")
CUAD_LEAK_SYSTEM = ("You are a contracts analyst. You will be shown an excerpt of a commercial contract in which the party names have been "
                    "changed. Say which real companies most likely signed the original contract, and why. If you cannot tell, say so.")
CUAD_LEAK_USER = ("{doc}\n\nWhich real companies were the parties to the original contract? Name them first (or \"cannot tell\"), then give "
                  "your reasons in two or three sentences.")


async def leak(models: list[str] = LLM_MODELS, n_jeb: int = 150, n_cuad: int | None = None, log=print) -> dict:
    """Identification rate on renamed documents. Jeb: 150 renamed e-mails (half from dose 3+), 'identified' = answer names Bush/Jeb.
    CUAD: the first renamed excerpt of every contract (102), 'identified' = answer contains a real party name from the mapping."""
    from .paraphrase import FlexText

    out_path = RESULTS / "leak_check.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["arm"], r["model"], r["doc_id"]) for r in _rows(out_path)} if out_path.exists() else set()
    rng = random.Random(7)
    jeb = _rows(DATA / "jeb__renamed.jsonl")
    rng.shuffle(jeb)
    hi = [r for r in jeb if r["meta"]["dose"] >= 3][: n_jeb // 2]
    sample_j = hi + [r for r in jeb if r not in hi][: n_jeb - len(hi)]
    cuad = _rows(DATA / "cuad__renamed.jsonl")
    first: dict[int, dict] = {}
    for r in sorted(cuad, key=lambda r: (r["meta"]["contract_idx"], r["meta"]["para_idx"])):
        first.setdefault(r["meta"]["contract_idx"], r)
    sample_c = list(first.values())[: n_cuad] if n_cuad else list(first.values())
    mapping = json.loads((DATA / "cuad_mapping.json").read_text())
    sem = asyncio.Semaphore(8)
    cost = Counter()
    lock = asyncio.Lock()

    async def one(arm, m, client, r):
        if (arm, m, r["id"]) in done:
            return
        sysm, usr = (JEB_LEAK_SYSTEM, JEB_LEAK_USER) if arm == "jeb" else (CUAD_LEAK_SYSTEM, CUAD_LEAK_USER)
        async with sem:
            text, paid, listed, *_ = await client.complete(sysm, usr.format(doc=r["text"][:12000]), max_tokens=160, cache_key=f"ablation2-leak-{arm}")
        rec = {"arm": arm, "model": m, "doc_id": r["id"], "dose": r["meta"].get("dose"), "contract_idx": r["meta"].get("contract_idx"), "answer": text, "cost_usd": paid}
        async with lock:
            with out_path.open("a") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            cost[m] += paid

    for m in models:
        if not key_available(m):
            log(f"[pending] {m}: key not set — leak check skipped")
            continue
        client = FlexText(MODELS[m])
        try:
            await asyncio.gather(*(one("jeb", m, client, r) for r in sample_j), *(one("cuad", m, client, r) for r in sample_c))
        finally:
            await client.aclose()
    recs = _rows(out_path)
    summ = score_leak(recs, mapping)
    record_spend("leak_check", 0.9, sum(r["cost_usd"] for r in recs), {"answers": len(recs)})
    log(f"leak check: {len(recs)} answers, ${sum(cost.values()):.2f} this run; " + "; ".join(
        f"{a}/{m}: {v['identified']}/{v['n']}" for a, d in summ.items() for m, v in d.items()))
    return summ


def score_leak(recs: list[dict], mapping: dict) -> dict:
    real_by_contract = {ci: [k.lower() for k in m["phrases"]] for ci, m in mapping.items()}
    out: dict = {"jeb": {}, "cuad": {}}
    for arm in ("jeb", "cuad"):
        by: dict[str, list[dict]] = defaultdict(list)
        for r in recs:
            if r["arm"] == arm:
                by[r["model"]].append(r)
        for m, rs in by.items():
            ident, cannot, examples = 0, 0, []
            by_dose = defaultdict(lambda: [0, 0])
            for r in rs:
                a = r["answer"].lower()
                if arm == "jeb":
                    hit = bool(re.search(r"\bjeb\b|\bbush\b", a))
                else:
                    names = [n for n in real_by_contract.get(str(r["contract_idx"]), []) if len(n) >= 4]
                    hit = any(n in a for n in names)
                if hit:
                    ident += 1
                    if len(examples) < 5:
                        examples.append({"doc_id": r["doc_id"], "answer": r["answer"][:220]})
                if "cannot tell" in a[:80]:
                    cannot += 1
                if arm == "jeb":
                    band = "0" if (r["dose"] or 0) == 0 else "1-2" if r["dose"] <= 2 else "3+"
                    by_dose[band][0] += hit
                    by_dose[band][1] += 1
            out[arm][m] = {"n": len(rs), "identified": ident, "share": round(ident / len(rs), 3), "cannot_tell": cannot, "examples": examples,
                           **({"by_dose": {b: {"identified": v[0], "n": v[1]} for b, v in by_dose.items()}} if arm == "jeb" else {})}
    return out
