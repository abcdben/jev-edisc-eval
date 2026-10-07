"""Run the tests through the ordinary benchmark runner (resumable), with a hard cap on OpenAI spend.

Result files: results/jev_probe/<test>/multi/<model>__<tag>.jsonl
  t1/   <model>__<matter>.jsonl                     all T1 docs (both conditions), the matter's nameless requests
  bt/   jev__base__<criteria>[__enronctx].jsonl     bare-token docs; criteria = aswritten | named
  t2/   <model>__<coll>__<orig|edited>__<qid>.jsonl one job per target request and condition
  t3/   jev__base__<corpus>__<orig|para>.jsonl      Jev only (the test needs a score)
  t4/   <model>__enron__<judged|unjudged>.jsonl     six substantive Complaint J requests per document

Jev runs everywhere. LLM jobs are run in a fixed priority order and skipped once the projected spend would exceed the cap;
the projection uses the list price x the flex discount, and actual paid cost is read back from the prediction rows.
"""
from __future__ import annotations

import os
from collections import defaultdict

from ..config import ENV_KEYS, MODELS
from ..providers import parse_model_key
from ..runner import job_path, load_predictions, run_job
from ..tasks import Document, Question, TaskSet
from .common import T1_CARRIED_OVER, DATA, JEV, LLMS, LUNA, RESULTS, ROOT, SOL, TERRA, ledger_total, prediction_spend, read_jsonl
from .items import FAS140_NAMES_NOTE, MATTERS

ENRON_TOPICS = ["prepay_transactions", "fas140", "financial_forecasts", "document_destruction", "energy_schedules", "financial_analysts"]
T2_TASKS = {"enron": "tasks/enron_j.yaml", "jebbush": "tasks/trec.yaml", "veridian": "tasks/veridian.yaml"}
T3_TASKS = {"enron": "tasks/enron_j.yaml", "endo": "tasks/endo.yaml", "veridian": "tasks/veridian.yaml"}
ENRON_NAMED_NOTE = (" The Company is Enron Corp.; the e-mails are from the Enron corpus (the complaint refers to the Company by the "
                    "pseudonym \"Volteron\").")  # same sentence the ablation's named condition used
FLEX = 0.5
CAP_T12_DEFAULT = 5.0   # OpenAI spend cap for T1 + T2 (predictions + edit generation + verification)
CAP_OTHER_DEFAULT = 3.0  # OpenAI spend cap for T3 paraphrases + T4 panel


def key_available(model_key: str) -> bool:
    spec, _ = parse_model_key(model_key)
    env = ENV_KEYS.get(spec.provider, "")
    return (not env) or bool(os.environ.get(env))


def _docs(rows: list[dict]) -> list[Document]:
    return [Document(id=r["id"], text=r["text"], labels=r.get("labels") or {}, gray=frozenset(r.get("gray") or []), meta=r.get("meta") or {}) for r in rows]


def _estimate(ts: TaskSet, docs: list[Document], model: str) -> float:
    spec = MODELS[model.split("@")[0]]
    prefix = len(ts.context) + sum(len(q.rfp_text) + len(q.positive_desc) + len(q.negative_desc) + 120 for q in ts.questions.values()) + 400
    in_tok = sum((prefix + len(d.text)) / 4 for d in docs)
    out_tok = len(docs) * (25 + 30 * len(ts.qids))
    paid = spec.cost_usd(int(in_tok), int(out_tok))
    return paid * (FLEX if spec.provider == "openai" else 1.0)


# T1 v1 (task-yaml contexts that named the products; see items.py) is archived under t1_v1_confounded/ and still counts toward the cap.
T12_TESTS = ["t1", "t1_v1_confounded", "t2"]


class Budget:
    def __init__(self, cap_t12: float, cap_other: float, log=print):
        self.cap_t12, self.cap_other, self.log = cap_t12, cap_other, log

    def spent_t12(self) -> float:
        return prediction_spend(T12_TESTS, exclude=T1_CARRIED_OVER) + ledger_total(["t2_edit"])

    def spent_other(self) -> float:
        return prediction_spend(["t3", "t4"]) + ledger_total(["t3_para"])

    def allow(self, test: str, est: float) -> bool:
        if test in ("t1", "t2"):
            spent, cap = self.spent_t12(), self.cap_t12
        else:
            spent, cap = self.spent_other(), self.cap_other
        ok = spent + est <= cap
        if not ok:
            self.log(f"  [budget] {test}: spent ${spent:.2f} + est ${est:.2f} > cap ${cap:.2f} — skipped")
        return ok


async def _run(ts: TaskSet, docs: list[Document], model: str, test: str, tag: str, budget: Budget | None, concurrency, log) -> dict:
    path = job_path(RESULTS, test, "multi", model, tag)
    before = {(p.doc_id, p.question) for p in load_predictions(path) if not p.error}
    pending = [d for d in docs if any((d.id, q) not in before for q in ts.qids)]
    if not pending:
        return {"new": 0, "paid": 0.0}
    if not key_available(model):
        log(f"  [pending] {model}: key not set — {test}/{tag} skipped")
        return {"new": 0, "paid": 0.0, "pending": True}
    spec = MODELS[model.split("@")[0]]
    if spec.provider == "openai" and budget is not None and not budget.allow(test, _estimate(ts, pending, model)):
        return {"new": 0, "paid": 0.0, "skipped_budget": True}
    preds = await run_job(ts, docs, model, "multi", RESULTS, test, concurrency=concurrency, tag=tag, log=log)
    new = [p for p in preds if (p.doc_id, p.question) not in before and not p.error]
    return {"new": len(new), "paid": sum(p.cost_usd for p in new), "errors": sum(1 for p in preds if p.error)}


# ------------------------------------------------------------------------------------------------ the tests

async def run_t1(models: list[str], budget: Budget, concurrency, log) -> dict:
    out = {}
    for key, m in MATTERS.items():
        ts = m.taskset(ROOT)
        docs = _docs(read_jsonl(DATA / f"t1_{key}.jsonl"))
        for model in models:
            out[f"{model}/{key}"] = await _run(ts, docs, model, "t1", key, budget, concurrency, log)
    return out


def bare_tasksets() -> dict[str, TaskSet]:
    base = TaskSet.load(ROOT / "tasks/enron_j.yaml").subset(["fas140"])
    q = base.questions["fas140"]
    assert not any(t.lower() in (q.rfp_text + q.positive_desc + q.negative_desc).lower() for t in ("raptor", "talon", "ljm", "chewco", "whitewing", "jedi")), \
        "the as-written FAS 140 criteria were expected to name no vehicle"
    named_q = Question(id=q.id, title=q.title, rfp_text=q.rfp_text, positive_desc=q.positive_desc + FAS140_NAMES_NOTE, negative_desc=q.negative_desc)
    out = {
        "aswritten": base,
        "named": TaskSet(name="enron_j", context=base.context, questions={"fas140": named_q}),
        "aswritten__enronctx": TaskSet(name="enron_j", context=base.context + ENRON_NAMED_NOTE, questions=base.questions),
        "named__enronctx": TaskSet(name="enron_j", context=base.context + ENRON_NAMED_NOTE, questions={"fas140": named_q}),
    }
    return out


async def run_bare(concurrency, log) -> dict:
    docs = _docs(read_jsonl(DATA / "bt_docs.jsonl"))
    out = {}
    for tag, ts in bare_tasksets().items():
        out[tag] = await _run(ts, docs, JEV, "bt", tag, None, concurrency, log)
    return out


async def run_t2(models: list[str], budget: Budget, concurrency, log, verify_n: int = 10) -> dict:
    out = {}
    for coll, yaml_ in T2_TASKS.items():
        ts_full = TaskSet.load(ROOT / yaml_)
        orig = read_jsonl(DATA / f"t2_{coll}.jsonl")
        edited = [r for r in read_jsonl(DATA / f"t2_{coll}__edited.jsonl") if r["meta"].get("applied")]
        if not edited:
            log(f"T2 {coll}: no applied edits yet (run build); skipped")
            continue
        keep = {r["id"] for r in edited}
        orig = [r for r in orig if r["id"] in keep]
        for cond, rows in (("orig", orig), ("edited", edited)):
            by: dict[str, list[dict]] = defaultdict(list)
            for r in rows:
                by[r["meta"]["target_qid"]].append(r)
            for q, rs in sorted(by.items()):
                ts = ts_full.subset([q])
                for model in models:
                    if model == f"{TERRA}#verify":
                        continue
                    out[f"{model}/{coll}/{cond}/{q}"] = await _run(ts, _docs(rs), model, "t2", f"{coll}__{cond}__{q}", budget, concurrency, log)
    return out


async def run_t2_verify(concurrency, log, n_per_coll: int = 10, model: str = TERRA) -> dict:
    """Second-model check that the edits flipped the true label: `model` reads the first n edited docs per collection."""
    out = {}
    budget = Budget(CAP_T12_DEFAULT, CAP_OTHER_DEFAULT, log)
    for coll, yaml_ in T2_TASKS.items():
        ts_full = TaskSet.load(ROOT / yaml_)
        edited = [r for r in read_jsonl(DATA / f"t2_{coll}__edited.jsonl") if r["meta"].get("applied")][:n_per_coll]
        by: dict[str, list[dict]] = defaultdict(list)
        for r in edited:
            by[r["meta"]["target_qid"]].append(r)
        for q, rs in sorted(by.items()):
            out[f"{coll}/{q}"] = await _run(ts_full.subset([q]), _docs(rs), model, "t2", f"{coll}__verify__{q}", budget, concurrency, log)
    return out


async def run_t3(concurrency, log) -> dict:
    out = {}
    for corpus, yaml_ in T3_TASKS.items():
        ts = TaskSet.load(ROOT / yaml_)
        if corpus == "enron":
            ts = ts.subset(ENRON_TOPICS)
        para = [r for r in read_jsonl(DATA / f"t3_{corpus}__para.jsonl") if r["meta"].get("applied")]
        if not para:
            log(f"T3 {corpus}: no paraphrases yet (run build); skipped")
            continue
        keep = {r["id"] for r in para}
        orig = [r for r in read_jsonl(DATA / f"t3_{corpus}.jsonl") if r["id"] in keep]
        for cond, rows in (("orig", orig), ("para", para)):
            out[f"{corpus}/{cond}"] = await _run(ts, _docs(rows), JEV, "t3", f"{corpus}__{cond}", None, concurrency, log)
    return out


async def run_t4(models: list[str], budget: Budget, concurrency, log) -> dict:
    ts = TaskSet.load(ROOT / "tasks/enron_j.yaml").subset(ENRON_TOPICS)
    out = {}
    for side in ("judged", "unjudged"):
        rows = read_jsonl(DATA / f"t4_enron_{side}.jsonl")
        if not rows:
            log(f"T4 {side}: no documents (EDRM pool not built?); skipped")
            continue
        for model in models:
            out[f"{model}/{side}"] = await _run(ts, _docs(rows), model, "t4", f"enron__{side}", budget, concurrency, log)
    return out


async def run(tests: list[str], models: list[str] | None = None, cap_t12: float = CAP_T12_DEFAULT, cap_other: float = CAP_OTHER_DEFAULT,
              concurrency: int | None = None, log=print) -> dict:
    budget = Budget(cap_t12, cap_other, log)
    res: dict = {}
    llms = [m for m in (models or [JEV] + LLMS) if m != JEV]
    want_jev = models is None or JEV in models
    # Jev first everywhere (own key, cheap), then LLMs in priority order under the cap
    if "t1" in tests and want_jev:
        res["t1_jev"] = await run_t1([JEV], budget, concurrency, log)
    if "bt" in tests and want_jev:
        res["bt"] = await run_bare(concurrency, log)
    if "t2" in tests and want_jev:
        res["t2_jev"] = await run_t2([JEV], budget, concurrency, log)
    if "t3" in tests and want_jev:
        res["t3"] = await run_t3(concurrency, log)
    if "t4" in tests and want_jev:
        res["t4_jev"] = await run_t4([JEV], budget, concurrency, log)
    order = [m for m in (LUNA, TERRA, SOL) if m in llms]
    if "t1" in tests and LUNA in order:
        res["t1_luna"] = await run_t1([LUNA], budget, concurrency, log)
    if "t2" in tests and LUNA in order:
        res["t2_luna"] = await run_t2([LUNA], budget, concurrency, log)
    if "t2" in tests and TERRA in order:
        res["t2_verify"] = await run_t2_verify(concurrency, log)
    for m in (TERRA, SOL):
        if "t1" in tests and m in order:
            res[f"t1_{m}"] = await run_t1([m], budget, concurrency, log)
    if "t4" in tests:
        for m in (LUNA, TERRA):
            if m in order:
                res[f"t4_{m}"] = await run_t4([m], budget, concurrency, log)
    for m in (TERRA, SOL):
        if "t2" in tests and m in order:
            res[f"t2_{m}"] = await run_t2([m], budget, concurrency, log)
    res["spend"] = {"t1_t2_predictions": round(prediction_spend(T12_TESTS, exclude=T1_CARRIED_OVER), 4), "t1_v2_rerun": round(prediction_spend(["t1"], exclude=T1_CARRIED_OVER), 4),
                    "t1_v1_confounded": round(prediction_spend(["t1_v1_confounded"]), 4), "t2_edits": round(ledger_total(["t2_edit"]), 4),
                    "t3_paraphrases": round(ledger_total(["t3_para"]), 4), "t3_t4_predictions": round(prediction_spend(["t3", "t4"]), 4),
                    "jev_all": round(prediction_spend(None, ["jev"], exclude=T1_CARRIED_OVER), 4)}
    res["spend"]["openai_total"] = round(res["spend"]["t1_t2_predictions"] + res["spend"]["t2_edits"] + res["spend"]["t3_paraphrases"] + res["spend"]["t3_t4_predictions"], 4)
    log(f"spend: {res['spend']}")
    return res
