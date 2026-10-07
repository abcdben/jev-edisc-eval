"""Check D — knowledge injection on Veridian: prepend a detailed (fictional) case brief and re-run the ablation's Veridian arm.

Veridian is the one matter no system can know anything about beyond the task context. If matter knowledge helps relevance
review, F1 should rise when the only possible source of case knowledge is supplied. The brief (`data/ablation/veridian_brief.md`,
written from the corpus bible in the style of `data/ablation/mnk_brief.md`: parties, products, the people, deals and code names,
timeline, outcome) is appended to the task context exactly as the Mallinckrodt brief arm did (`context + "\\n\\n" + brief`), and the
same runner, arm (multi, all ten requests per call), effort, flex tier and temperature settings are used. The comparison is paired
by document with the ablation's existing Veridian *named* predictions, so the without-brief side costs nothing new.

Token volume: the full Veridian arm cost $13.89 paid for the three OpenAI models without the brief; with ~900 brief tokens on every
call it would exceed the whole $15 cap on its own, so a stratified half (≈500 documents, same positive-set mix) is run and that is
stated in the report. Jev runs on the same subset.
"""
from __future__ import annotations

import json
import random
from collections import Counter, defaultdict

import numpy as np

from ..config import MODELS
from ..runner import job_path, load_predictions, run_job
from ..tasks import Document, TaskSet
from .common import (DATA, JEV, POS, RESULTS, ROOT, SEED, SYSTEMS, boot_delta_by_cluster, mcnemar, prediction_spend, prf, read_jsonl, write_jsonl)

ABL_VERIDIAN = ROOT / "results" / "ablation" / "veridian" / "multi"
SRC = ROOT / "data" / "ablation" / "veridian.jsonl"
SUBSET = DATA / "d_veridian_subset.jsonl"
BRIEF_PATH = ROOT / "data" / "ablation" / "veridian_brief.md"
N_SUBSET = 500
TAG = "brief__all"

VERIDIAN_BRIEF = """Case brief: In re Veridian Orthopedics ApexHip Products Liability Litigation, MDL 3102 (background a well-informed reviewer would know)

Parties and forum. Veridian Orthopedics, Inc. (Warsaw, Indiana; NYSE: VRDO; founded 1994, about 1,800 employees; manufacturing in
Warsaw and Cork, Ireland; regional sales offices in Atlanta, Dallas, Denver and Newark) is the defendant in MDL No. 3102 (N.D. Ind.),
formed in December 2023 after the first state-court suits of March 2023, and in related state actions. Outside counsel is Whitfield
& Barr LLP (Elena Ruiz); the product-liability carrier is Aegis Specialty Insurance. CEO Rob Castellano, CFO Owen Park, General
Counsel Rachel Steinberg, Chief Medical Officer Dr. Leon Adeyemi.

Product. ApexHip is a metal-on-metal total hip system: cobalt-chromium femoral head and stem with a cobalt-chromium acetabular cup
carrying the "KinetiCoat" porous-titanium coating, acquired with Kinetic Bearing Technologies (KBT) in March 2016 for $41 million
(due diligence flagged limited long-term adhesion data). Cleared by FDA 510(k) K162447 on 9 March 2017 (predicate ClassicHip; FDA
lead reviewer Dr. P. Anand), launched in the US in April 2017 and in the EU that September, and marketed to "active adults" aged
45-65 on longevity, low wear and large-head stability (the Kessler Reid agency's "Active Life" campaign, brochure line "designed to
last a lifetime of movement"). Peak year 2020: about 14,200 systems and $96 million, roughly 22% of company revenue. Lot numbers:
cups V-2xxx, stems S-7xxx, heads H-3xxx. Other Veridian products - KneeFlex knees (launched 2019), the legacy metal-on-polyethylene
ClassicHip being phased out, and ShoulderPro - are not at issue.

The people. Tom Halvorsen (senior design engineer, ApexHip) led the 2015-2017 design; design review DR-3 in November 2016 approved an
ISO 14242 wear-test protocol at the standard 45-degree cup inclination only, with testing by Meridian Testing Labs. In February 2019
Halvorsen re-ran wear testing at 55 degrees, found four to six times the wear (edge loading), and wrote to Priya Raman (Director,
Quality and Complaint Handling) and Carlos Mendes (Product Manager, ApexHip); the resulting design change, ECO-2019-118, was proposed
and deferred. Halvorsen resigned in 2022. Dana Okonkwo is VP Regulatory Affairs (Devon Mitchell her senior regulatory specialist);
Greg Novak is Director of Post-Market Surveillance and ran the registry analyses; Marcus Lee is VP Sales, Jenna Whitfield the
Southeast regional sales manager (reps Sarah Kim, Atlanta, and Mike Ruiz, Nashville); Anika Shah runs marketing communications;
Hannah Berg is the FP&A manager; Bill Kowalski manages the Cork plant; Lisa Tran is the HR business partner. Paid surgeons: Dr. Marcus
Feld (Atlanta Joint Institute; design consultant since May 2017, 1.5% royalty on ApexHip, speaker, $180,000-$240,000 a year, whose
own practice later produced a revision cluster) and Dr. Anita Rao (Nashville; speaker honoraria of about $60,000 a year, advisory
board, increasingly sceptical from 2021). Dr. James Whitaker (Denver) was never paid and complained loudly about revisions in 2022.
Sam Ibarra (Ibarra Surgical, Texas) is the distributor; Northgate Health System (GPO VantageOne) a hospital customer.

Allegations and timeline. (1) Design and warning: that ApexHip sheds cobalt and chromium wear debris causing adverse reaction to
metal debris (pseudotumours, tissue necrosis) and early revision, that the 2019 wear re-analysis was known and not acted on, and that
the company failed to warn. The first metal-ion complaint cluster - three of Dr. Feld's Atlanta patients - was logged in TrackWise in
August 2018 (TW-2018-0233); FDA sent an Additional Information request on MDR trending in May 2019; the June 2021 FDA inspection of
Warsaw (Investigator R. Delgado) produced a Form 483 with three observations, one on complaint-trending timeliness, answered in
July 2021; an anonymous ethics-hotline report in November 2021 alleged suppression of complaint trends. (2) The registry signal and
the decision to keep selling: the March 2021 UK National Joint Registry annual report put ApexHip's five-year revision rate at 7.1%
against a 3.2% class average, American Joint Replacement Registry data in late 2021 pointed the same way, and at the 14 September 2021
"Registry Signal Review" meeting the company decided to continue selling with a labelling update and an October 2021 "Dear Doctor"
letter rather than withdraw. (3) Promotion and surgeons: that the "Active Life" claims about longevity, wear and suitability for
younger, more active patients were unsubstantiated, that sales representatives were scripted on how to answer surgeons' metal-ion
and revision-rate questions ("Answering the metal ion question"), and that consulting and speaker payments to surgeons promoted the
device. (4) The recall, a distinct manufacturing issue plaintiffs try to blur with the wear problem: cup lots V-2200 through V-2299,
made in Cork between November 2021 and February 2022, showed KinetiCoat coating flaking at incoming inspection in two hospitals;
a voluntary Class II recall began on 14 June 2022 (FDA recall Z-1418-2022; 1,140 units distributed, 412 implanted), root cause a
plasma-spray parameter drift after a chamber maintenance event.

Outcome. Whitfield & Barr was engaged in January 2022 and a litigation hold issued on 1 February 2022; an $18 million reserve for
ApexHip claims was booked in the third quarter of 2022 and Aegis Specialty was notified (notice of circumstance, reservation of
rights). ApexHip sales continued until the voluntary market withdrawal announced on 2 February 2024. The relevant period runs from
1 January 2015 to 30 June 2024.
"""


def write_brief() -> str:
    BRIEF_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRIEF_PATH.write_text(VERIDIAN_BRIEF)
    return str(BRIEF_PATH)


def brief_text() -> str:
    return BRIEF_PATH.read_text() if BRIEF_PATH.exists() else VERIDIAN_BRIEF


def brief_taskset() -> TaskSet:
    ts = TaskSet.load(ROOT / "tasks" / "veridian.yaml")
    return TaskSet(name=ts.name + "__brief", context=ts.context + "\n\n" + brief_text().strip(), questions=ts.questions,
                   positive_label=ts.positive_label, negative_label=ts.negative_label, gate_question=ts.gate_question, source=ts.source)


# ------------------------------------------------------------------------------------------------ subset

def build_subset(n: int = N_SUBSET, log=print) -> dict:
    """Stratified half of the ablation's 1,000 Veridian documents: stratum = the document's positive-label set; a seeded shuffle within
    each stratum and the first ceil(share) of each, so every request keeps its positive share. Same ids in both conditions."""
    rows = read_jsonl(SRC)
    by: dict[tuple, list] = defaultdict(list)
    for r in rows:
        by[tuple(sorted(r["labels"]))].append(r)
    rng = random.Random(SEED)
    frac = n / len(rows)
    out = []
    for key in sorted(by, key=lambda k: (len(k), k)):
        grp = sorted(by[key], key=lambda r: r["id"])
        rng.shuffle(grp)
        take = int(round(len(grp) * frac))
        out += grp[:take]
    out.sort(key=lambda r: r["id"])
    write_jsonl(SUBSET, out)
    pos = Counter(q for r in out for q in r["labels"])
    pos_all = Counter(q for r in rows for q in r["labels"])
    log(f"D subset: {len(out)} of {len(rows)} docs; positives per request kept " + ", ".join(f"{q}={pos[q]}/{pos_all[q]}" for q in sorted(pos_all)))
    return {"n": len(out), "n_source": len(rows), "positives": {q: [pos[q], pos_all[q]] for q in sorted(pos_all)}}


def subset_docs() -> list[Document]:
    return [Document(id=r["id"], text=r["text"], labels=r.get("labels") or {}, gray=frozenset(r.get("gray") or []), meta=r.get("meta") or {}) for r in read_jsonl(SUBSET)]


def estimate(models: list[str]) -> dict:
    """Projected paid cost per model from the ablation's named rows on the subset documents, scaled for the brief's extra tokens."""
    ids = {d.id for d in subset_docs()}
    brief_tok = len(brief_text()) / 4
    out = {}
    for m in models:
        rows = [p for p in load_predictions(ABL_VERIDIAN / f"{m.replace('@', '__')}__named__all.jsonl") if not p.error and p.doc_id in ids]
        if not rows:
            out[m] = {"paid": None}
            continue
        calls = len({p.doc_id for p in rows})
        in_tok = sum(p.input_tokens for p in rows); paid = sum(p.cost_usd for p in rows)
        scale = 1 + brief_tok * calls / max(1, in_tok)
        spec = MODELS[m.split("@")[0]]
        extra = spec.cost_usd(int(brief_tok * calls), 0) * (0.5 if spec.provider == "openai" else 1.0)
        out[m] = {"calls": calls, "named_paid_subset": round(paid, 3), "projected_paid": round(paid + extra, 3), "scale": round(scale, 3)}
    out["_brief_tokens"] = int(brief_tok)
    return out


async def run(models: list[str], remaining_cap: float, concurrency: int | None = None, log=print) -> dict:
    """Run the with-brief condition on the subset for each model (resumable). OpenAI models are skipped when the projection would
    exceed the remaining cap; Jev always runs."""
    if not SUBSET.exists():
        build_subset(log=log)
    write_brief()
    ts = brief_taskset()
    docs = subset_docs()
    est = estimate(models)
    out = {"estimate": est}
    spent_before = prediction_spend("d")
    for m in models:
        spec = MODELS[m.split("@")[0]]
        path = job_path(RESULTS, "d", "multi", m, TAG)
        before = {(p.doc_id, p.question) for p in load_predictions(path) if not p.error}
        pending = [d for d in docs if any((d.id, q) not in before for q in ts.qids)]
        if not pending:
            out[m] = {"new": 0, "paid": 0.0}
            continue
        if spec.provider == "openai":
            proj = (est.get(m, {}).get("projected_paid") or 0.0) * len(pending) / len(docs)
            spent_now = prediction_spend("d") - spent_before
            if spent_now + proj > remaining_cap:
                log(f"  [budget] D {m}: projected ${proj:.2f} + spent ${spent_now:.2f} > remaining cap ${remaining_cap:.2f} — skipped")
                out[m] = {"new": 0, "paid": 0.0, "skipped_budget": True, "projected": proj}
                continue
        preds = await run_job(ts, docs, m, "multi", RESULTS, "d", concurrency=concurrency, tag=TAG, log=log)
        new = [p for p in preds if (p.doc_id, p.question) not in before and not p.error]
        out[m] = {"new": len(new), "paid": round(sum(p.cost_usd for p in new), 4), "list": round(sum(p.list_cost_usd for p in new), 4), "errors": sum(1 for p in preds if p.error)}
        log(f"D {m}: {len(new)} new rows, ${out[m]['paid']:.3f} paid")
    return out


# ------------------------------------------------------------------------------------------------ scoring

def score(log=print) -> dict:
    out: dict = {"n_subset": 0, "brief_chars": len(brief_text()), "brief_path": str(BRIEF_PATH.relative_to(ROOT)), "models": {}}
    if not SUBSET.exists():
        out["status"] = "subset not built"
        return out
    docs = {d.id: d for d in subset_docs()}
    out["n_subset"] = len(docs)
    out["n_source"] = sum(1 for _ in read_jsonl(SRC))
    qids = TaskSet.load(ROOT / "tasks" / "veridian.yaml").qids
    for m in SYSTEMS:
        A = {(p.doc_id, p.question): p for p in load_predictions(ABL_VERIDIAN / f"{m.replace('@', '__')}__named__all.jsonl") if not p.error and p.doc_id in docs}
        B = {(p.doc_id, p.question): p for p in load_predictions(job_path(RESULTS, "d", "multi", m, TAG)) if not p.error}
        keys = sorted(set(A) & set(B))
        if not keys:
            out["models"][m] = {"status": "missing" if not B else "no overlap"}
            continue
        gold = np.array([1 if docs[d].gold(q) == POS else 0 for d, q in keys])
        a = np.array([1 if A[k].label == POS else 0 for k in keys]); b = np.array([1 if B[k].label == POS else 0 for k in keys])
        gray = np.array([q in docs[d].gray for d, q in keys])
        delta, _ = boot_delta_by_cluster(gold, a, b, [d for d, _ in keys])
        res = {"status": "ok", "n_pairs": len(keys), "n_docs": len({d for d, _ in keys}), "without_brief": prf(gold, a), "with_brief": prf(gold, b), "delta": delta,
               "mcnemar": {"lost": int(((a == gold) & (b != gold)).sum()), "gained": int(((a != gold) & (b == gold)).sum())},
               "flips": {"positives_lost": int(((gold == 1) & (a == 1) & (b == 0)).sum()), "positives_gained": int(((gold == 1) & (a == 0) & (b == 1)).sum()),
                         "false_pos_added": int(((gold == 0) & (a == 0) & (b == 1)).sum()), "false_pos_removed": int(((gold == 0) & (a == 1) & (b == 0)).sum())},
               "label_changed_share": float((a != b).mean()), "cost_paid": round(sum(B[k].cost_usd for k in keys), 4), "cost_list": round(sum(B[k].list_cost_usd for k in keys), 4),
               "mean_input_tokens_without": float(np.mean([A[k].input_tokens for k in keys])), "mean_input_tokens_with": float(np.mean([B[k].input_tokens for k in keys]))}
        res["mcnemar"]["p"] = mcnemar(res["mcnemar"]["lost"], res["mcnemar"]["gained"])
        # gray excluded
        gi = np.where(~gray)[0]
        if len(gi) > 10:
            d2, _ = boot_delta_by_cluster(gold[gi], a[gi], b[gi], [keys[i][0] for i in gi], nb=1000)
            res["gray_excluded"] = {"n": int(len(gi)), "without_brief": prf(gold[gi], a[gi]), "with_brief": prf(gold[gi], b[gi]), "delta": d2}
        # per request
        res["per_request"] = {}
        for q in qids:
            qi = np.array([k[1] == q for k in keys])
            idx = np.where(qi)[0]
            if len(idx):
                d3, _ = boot_delta_by_cluster(gold[idx], a[idx], b[idx], [keys[i][0] for i in idx], nb=500)
                res["per_request"][q] = {"n": int(len(idx)), "pos": int(gold[idx].sum()), "without_brief": prf(gold[idx], a[idx]), "with_brief": prf(gold[idx], b[idx]), "delta": d3}
        out["models"][m] = res
        log(f"D {m:14s} n={len(keys)}  F1 {res['without_brief']['f1']:.3f} → {res['with_brief']['f1']:.3f} (Δ {100*delta['f1']['delta']:+.1f} [{100*delta['f1']['lo']:+.1f}, {100*delta['f1']['hi']:+.1f}])  "
            f"R Δ {100*delta['recall']['delta']:+.1f}  P Δ {100*delta['precision']['delta']:+.1f}  McNemar p={res['mcnemar']['p']:.3g}")
    # the Mallinckrodt brief effect from the ablation summary, for side-by-side reading
    abl = ROOT / "results" / "ablation" / "summary.json"
    if abl.exists():
        s = json.loads(abl.read_text())
        out["mnk_brief_effect_from_ablation"] = {m: (v.get("delta") or {}).get("f1") for m, v in s["arms"]["mnk"]["per_model"].items() if v.get("status") == "ok"}
    # the same brief-injection check on Big Thorium (Relativity's public demo workspace, invented case; Relativity's own aiR case summary as the brief)
    bt = ROOT / "results" / "ablation" / "bigthorium" / "summary.json"
    if bt.exists():
        b = json.loads(bt.read_text()).get("brief") or {}
        if b:
            out["bigthorium_brief_effect_from_ablation"] = {m: (v.get("delta") or {}).get("f1") for m, v in b.items() if v.get("delta")}
    return out
