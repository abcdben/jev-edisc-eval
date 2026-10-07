"""Contamination probes for Big Thorium, Relativity's synthetic "aiR for Review Demo" collection — a second floor beside Veridian.

Big Thorium is fictional, but unlike Veridian it was not written for this study: Relativity has shipped the workspace to its
customers and sales engineers for some time, so it *could* have reached a model through product documentation, training material or
screenshots. The probes therefore ask the same four questions as for the real corpora — do the models continue its e-mails verbatim,
do they know its people, do they recognise its matter when de-identified, do they know it as a benchmark/demo — and the expected
answer on a true floor is "no" on all four. The items live in data/contam/bigthorium_probes.jsonl and the responses in the ordinary
results/contam/<model>.jsonl files (the main scorer ignores items it does not know); the scoring here writes
results/contam/bigthorium_summary.json, which the report, the paper and the ablation REPORT read if present.

Verbatim windows are filtered by the boilerplate rules only (no LLM screen), so the comparison column is the real corpora's
`rules_only` figures from the main summary, not their headline (rules + screen) figures.
"""
from __future__ import annotations

import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

from ..ablation.bigthorium import ALL_DOCS, HDR_PAIR_RE, NOT_PEOPLE
from ..ablation.names import ROLE_WORDS
from .build import ENTITY_CORPORA, CORPORA, RECALL_SYSTEM, RECOG_SYSTEM, BENCH_SYSTEM, OUT_DIR, make_verbatim_item
from .matter import MATTER_ID_SYSTEM, MATTER_RECALL_SYSTEM, _kw_hit, declines
from .run import RESULTS_DIR, load_results
from .score import boot_ci, parse_yes_no, score_entity_recall, score_verbatim

CORPUS = "bigthorium"
PROBES = OUT_DIR / "bigthorium_probes.jsonl"
SUMMARY = RESULTS_DIR / "bigthorium_summary.json"
MODELS = ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]
ERA = "2017-2024"
ORG_DESC = "BigThorium, a sustainable-energy company that won a municipal energy contract from the City of Atlantis"
ORG_KEYWORDS = ["bigthorium", "big thorium", "thorium", "atlantis", "eldorado"]

SKETCH = (
    "A privately held sustainable-energy company answered a mid-sized city's request for proposals for a municipal energy-efficiency "
    "and carbon-reduction project and won the contract. An internal investigation, run by the company's general counsel with outside "
    "counsel, then examined whether its sales and business-development staff had given luxury watches and other gifts to city officials, "
    "including the city treasurer, whether a consulting intermediary had been used to channel payments, and whether the bid evaluation "
    "had been steered. The matter stayed at the fact-finding stage; no charges were filed and no court case is reported."
)
TEMPLATE_KEYS = [("Siemens", ["siemens"]), ("Odebrecht / Petrobras", ["odebrecht", "petrobras", "lava jato"]), ("Walmart Mexico", ["walmart", "wal-mart"]),
                 ("Cognizant", ["cognizant"]), ("Rolls-Royce", ["rolls-royce", "rolls royce"]), ("Alstom", ["alstom"]), ("Ericsson", ["ericsson"]),
                 ("Goldman / 1MDB", ["1mdb", "goldman"]), ("SNC-Lavalin", ["snc-lavalin", "snc lavalin"]), ("Halliburton / KBR", ["halliburton", "kbr"]),
                 ("Redflex / Chicago", ["redflex", "chicago"]), ("Johnson Controls / Milwaukee", ["johnson controls", "milwaukee"]),
                 ("Ameresco / Holyoke", ["ameresco", "holyoke"]), ("Siemens-era FCPA generic", ["fcpa"]),
                 ("a Relativity / aiR demo", ["relativity", "air for review", "thorium", "atlantis"])]
# facts of the matter a model could only know from the collection (none are stated in the question)
RECALL_RUBRIC = [("BigThorium", ["thorium"], "parties"), ("City of Atlantis", ["atlantis"], "parties"), ("John Maxwell (sales)", ["maxwell"], "people"),
                 ("Sarah Thompson (business development)", ["thompson"], "people"), ("Robert Williams (CFO)", ["williams"], "people"),
                 ("Emily Roberts (government relations)", ["roberts"], "people"), ("Laura Smith (procurement)", ["laura smith"], "people"),
                 ("Evelyn Archer (general counsel)", ["archer"], "people"), ("Daniel Carter / Law Firm X", ["carter", "law firm x"], "people"),
                 ("Howard Bass (city treasurer)", ["bass", "treasurer"], "people"), ("Rolex / luxury watch gift", ["rolex", "watch"], "allegations"),
                 ("GNS Partners (intermediary)", ["gns"], "allegations"), ("Eldorado", ["eldorado"], "parties")]


def _docs() -> list[dict]:
    return [json.loads(l) for l in ALL_DOCS.read_text().split("\n") if l.strip()]


def _email_rows(docs: list[dict]) -> list[dict]:
    """Documents with a real person as sender (not a newsletter/no-reply mailbox) and a body region long enough for a window."""
    out = []
    for d in docs:
        m = HDR_PAIR_RE.search(d["meta"].get("from") or "")
        if not m:
            continue
        parts = m.group(1).split()
        if len(parts) < 2 or parts[-1] in NOT_PEOPLE or parts[-1] in ROLE_WORDS or parts[-1].lower() not in m.group(2).lower():
            continue
        out.append(d)
    return out


def _name_tiers(docs: list[dict], rng: random.Random, per_tier: int = 10) -> list[tuple[str, str, int]]:
    freq: Counter = Counter()
    for d in docs:
        seen = set()
        for f in ("from", "to", "cc"):
            for m in HDR_PAIR_RE.finditer(d["meta"].get(f) or ""):
                parts = m.group(1).replace("...", "").split()
                if len(parts) >= 2 and parts[-1] not in NOT_PEOPLE and parts[-1] not in ROLE_WORDS and parts[-1].lower() in m.group(2).lower():
                    seen.add(" ".join(parts))
        freq.update(seen)
    ranked = sorted(freq, key=lambda n: (-freq[n], n))
    top = ranked[:per_tier]
    mid_pool = ranked[per_tier:per_tier + 30]
    mid = rng.sample(mid_pool, min(per_tier, len(mid_pool)))
    tail_pool = sorted(n for n, c in freq.items() if c <= 3 and n not in top and n not in mid)
    tail = rng.sample(tail_pool, min(per_tier, len(tail_pool)))
    return [(n, "top", freq[n]) for n in top] + [(n, "mid", freq[n]) for n in mid] + [(n, "tail", freq[n]) for n in tail]


def build_items(n_verbatim: int = 60, seed: int = 7, log=print) -> list[dict]:
    from .boilerplate import CorpusIndex, boilerplate_reasons  # noqa: PLC0415
    docs = _docs()
    rng = random.Random(seed)
    pool = _email_rows(docs)
    rng.shuffle(pool)
    index = CorpusIndex(CORPUS, docs=docs)
    items: list[dict] = []
    rejected: Counter = Counter()
    for d in pool:
        if len(items) >= n_verbatim:
            break
        w = make_verbatim_item(d, CORPUS)
        if not w:
            rejected["too_short"] += 1
            continue
        df = index.lookup([w["gold"]["target"], w["gold"]["prefix"][-400:]])
        rs = boilerplate_reasons(w["gold"]["prefix"], w["gold"]["target"], "email", df)
        if rs:
            rejected[rs[0]] += 1
            continue
        items.append(w)
    log(f"verbatim: {len(items)} windows from {len(pool)} e-mails; rejected {dict(rejected)}")
    tiers = _name_tiers(docs, rng)
    for name, tier, f in tiers:
        meta = {"name": name, "tier": tier, "doc_freq": f}
        items.append({"item_id": f"entity_recall:{CORPUS}:{name}", "probe": "entity_recall", "corpus": CORPUS, "system": RECALL_SYSTEM,
                      "user": (f"Who is {name}, a person active around {ERA}? Answer in one or two sentences naming the organisation(s) they were "
                               "affiliated with and their role. If you do not know who this specific person is, answer exactly: UNKNOWN."),
                      "gold": {"org_keywords": ORG_KEYWORDS, "true_corpus": CORPUS}, "meta": meta})
        for org in ENTITY_CORPORA + [CORPUS]:
            desc = ORG_DESC if org == CORPUS else CORPORA[org]["org_desc"]
            items.append({"item_id": f"entity_recog:{CORPUS}:{name}:{org}", "probe": "entity_recog", "corpus": CORPUS, "system": RECOG_SYSTEM,
                          "user": f"Was {name}, a person active around {ERA}, affiliated with {desc}? Answer with exactly one word: yes, no, or unknown.",
                          "gold": {"asked_org": org, "is_true_org": org == CORPUS}, "meta": {**meta, "asked_org": org}})
    items.append({"item_id": f"matter_id:{CORPUS}", "probe": "matter_id", "corpus": CORPUS, "system": MATTER_ID_SYSTEM,
                  "user": f"{SKETCH}\n\nWhich real company, person or case is this modelled on? Name it first, then give your reasons in a few sentences.",
                  "gold": {"answer_keys": [], "control": True, "template_keys": TEMPLATE_KEYS}, "meta": {"sketch": CORPUS, "kind": "de-identified sketch (fictional matter)"}})
    items.append({"item_id": f"matter_recall:{CORPUS}", "probe": "matter_recall", "corpus": CORPUS, "system": MATTER_RECALL_SYSTEM,
                  "user": "Describe the BigThorium / City of Atlantis bribery investigation: the parties, the key allegations or issues, the key people, the main events with dates, and the outcome.",
                  "gold": {"rubric": [{"label": a, "keys": b, "cat": c} for a, b, c in RECALL_RUBRIC], "control": True}, "meta": {"matter": CORPUS}})
    items.append({"item_id": f"bench_knowledge:{CORPUS}", "probe": "bench_knowledge", "corpus": CORPUS, "system": BENCH_SYSTEM,
                  "user": ("Relativity's aiR for Review product is demonstrated on a sample workspace built around a fictional company and a fictional legal matter. "
                           "Name the company, the counter-party it dealt with, and the nature of the matter, as specifically as you can."),
                  "gold": {"keys": [("BigThorium", ["thorium"]), ("City of Atlantis", ["atlantis"]), ("bribery / RFP", ["brib", "rfp", "procurement", "corrupt"])], "control": False},
                  "meta": {"benchmark": "relativity_air_demo"}})
    PROBES.parent.mkdir(parents=True, exist_ok=True)
    PROBES.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items))
    c = Counter(i["probe"] for i in items)
    log(f"wrote {len(items)} items → {PROBES}: {dict(c)}")
    return items


def load_items() -> list[dict]:
    return [json.loads(l) for l in PROBES.read_text().split("\n") if l.strip()]


async def run(models: list[str] = MODELS, concurrency: int = 8, log=print) -> list[dict]:
    from .run import run_models  # noqa: PLC0415
    return await run_models(models, load_items(), concurrency=concurrency, log=log)


def score(models: list[str] = MODELS, log=print) -> dict:
    items = {i["item_id"]: i for i in load_items()}
    main = json.loads((RESULTS_DIR / "summary.json").read_text()) if (RESULTS_DIR / "summary.json").exists() else {}
    out: dict = {"corpus": CORPUS, "models": [], "verbatim": {}, "entity_recall": {}, "entity_recog": {}, "matter_id": {}, "matter_recall": {},
                 "bench_knowledge": {}, "cost_usd": {}, "reference": {}, "n_items": len(items)}
    for m in models:
        res = {k: v for k, v in load_results(m).items() if k in items}
        if not res:
            log(f"[{m}] no Big Thorium results")
            continue
        out["models"].append(m)
        out["cost_usd"][m] = round(sum(r.get("cost_usd", 0) for r in res.values()), 4)
        V, ER, EG = [], [], defaultdict(list)
        for iid, r in res.items():
            it = items[iid]
            resp = r.get("response", "") or ""
            if it["probe"] == "verbatim":
                V.append(score_verbatim(it, resp))
            elif it["probe"] == "entity_recall":
                ER.append({**score_entity_recall(it, resp), "tier": it["meta"]["tier"], "name": it["meta"]["name"], "first_line": resp.strip().split("\n", 1)[0][:140]})
            elif it["probe"] == "entity_recog":
                EG[it["meta"]["asked_org"]].append(parse_yes_no(resp))
            elif it["probe"] == "matter_id":
                low = resp.lower()
                out["matter_id"][m] = {"unknown": declines(resp), "templates": [lab for lab, keys in TEMPLATE_KEYS if _kw_hit(low, keys)],
                                       "names_bigthorium": _kw_hit(low, ["thorium", "atlantis"]), "first_line": resp.strip().split("\n", 1)[0][:200], "response": resp}
            elif it["probe"] == "matter_recall":
                low = resp.lower()
                hits = [{"label": x["label"], "cat": x["cat"], "hit": _kw_hit(low, x["keys"])} for x in it["gold"]["rubric"] if x["label"] not in ("BigThorium", "City of Atlantis")]
                out["matter_recall"][m] = {"declines": declines(resp), "n_rubric": len(hits), "n_hit": sum(h["hit"] for h in hits),
                                           "hits": [h["label"] for h in hits if h["hit"]], "words": len(resp.split()), "first_line": resp.strip().split("\n", 1)[0][:200], "response": resp}
            elif it["probe"] == "bench_knowledge":
                low = resp.lower()
                rec = [lab for lab, keys in it["gold"]["keys"] if any(k in low for k in keys)]
                out["bench_knowledge"][m] = {"recovered": rec, "score": round(len(rec) / len(it["gold"]["keys"]), 3), "declines": declines(resp), "response": resp}
        if V:
            lcs = [v["lcs_f"] for v in V]
            runs = [v["max_run"] for v in V]
            out["verbatim"][m] = {"n": len(V), "n_refused": sum(v["refusal"] for v in V), "lcs_f_mean": round(sum(lcs) / len(lcs), 4), "lcs_f_ci": list(boot_ci(lcs)),
                                  "max_run_mean": round(sum(runs) / len(runs), 2), "max_run_ci": list(boot_ci([float(x) for x in runs])),
                                  "frac_run_ge8": round(sum(r >= 8 for r in runs) / len(runs), 3), "frac_run_ge15": round(sum(r >= 15 for r in runs) / len(runs), 3)}
        if ER:
            by = defaultdict(list)
            for e in ER:
                by[e["tier"]].append(e)
            out["entity_recall"][m] = {"n": len(ER), "hit_rate": round(sum(e["hit"] for e in ER) / len(ER), 3), "unknown_rate": round(sum(e["unknown"] for e in ER) / len(ER), 3),
                                       "hedge_hit_rate": round(sum(e["hedge_hit"] for e in ER) / len(ER), 3), "other_rate": round(sum(e["other"] for e in ER) / len(ER), 3),
                                       "by_tier": {t: {"n": len(v), "hit_rate": round(sum(e["hit"] for e in v) / len(v), 3), "unknown_rate": round(sum(e["unknown"] for e in v) / len(v), 3)} for t, v in by.items()},
                                       "non_unknown_examples": [e["first_line"] for e in ER if not e["unknown"]][:10]}
        if EG:
            out["entity_recog"][m] = {org: {"n": len(v), "yes_rate": round(sum(x == "yes" for x in v) / len(v), 3), "unknown_rate": round(sum(x == "unknown" for x in v) / len(v), 3)} for org, v in EG.items()}
        # reference figures from the main summary: the rules-only verbatim pool and entity recall of Veridian and the real e-mail corpora
        if main:
            ref = {}
            for c in ("veridian", "enron", "jebbush", "mnk", "endo"):
                v = main.get("verbatim", {}).get(m, {}).get(c, {})
                ro = v.get("rules_only", {})
                ref[c] = {"verbatim_rules_only_lcs_f": ro.get("lcs_f_mean"), "verbatim_rules_only_max_run": ro.get("max_run_mean"),
                          "verbatim_lcs_f": v.get("lcs_f_mean"), "entity_recall_hit_rate": main.get("entity_recall", {}).get(m, {}).get(c, {}).get("hit_rate"),
                          "entity_recog_true_org_yes_rate": main.get("entity_recog", {}).get(m, {}).get(c, {}).get("true_org_yes_rate")}
            out["reference"][m] = ref
        log(f"[{m}] verbatim lcs_f {out['verbatim'].get(m, {}).get('lcs_f_mean')} (Veridian rules-only {out['reference'].get(m, {}).get('veridian', {}).get('verbatim_rules_only_lcs_f')}); "
            f"entity recall hit {out['entity_recall'].get(m, {}).get('hit_rate')}; matter_id {out['matter_id'].get(m, {}).get('templates')} unknown={out['matter_id'].get(m, {}).get('unknown')}; "
            f"matter_recall declines={out['matter_recall'].get(m, {}).get('declines')} hits={out['matter_recall'].get(m, {}).get('hits')}; bench {out['bench_knowledge'].get(m, {}).get('recovered')}")
    out["cost_total_usd"] = round(sum(out["cost_usd"].values()), 4)
    SUMMARY.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    log(f"wrote {SUMMARY} (${out['cost_total_usd']})")
    return out


# ------------------------------------------------------------------------------------------------ merge into the main summary

def merge_into_summary(summary: dict, log=print) -> bool:
    """Add Big Thorium as corpus key `bigthorium` to the main summary's per-model tables (verbatim, entity_recall, entity_recog,
    matter_id, matter_recall, bench_knowledge) so the composite, the story page, the ladder and every per-collection figure treat it
    like any other collection. Re-scores the Big Thorium items from the result files with the same per-item functions the main
    scorer uses; no model calls. Returns True when at least one model had Big Thorium results.

    Comparability notes: the verbatim windows passed the boilerplate rules only (no LLM screen), so `vs_control` compares them with
    Veridian's rules-only windows; label recall (L) and day-one search terms (M2) were not probed for Big Thorium and stay absent
    (rendered as 'not measurable'). The demo-set knowledge question stands in for the benchmark-knowledge channel (B) under the
    key `relativity_air_demo`."""
    import numpy as np  # noqa: PLC0415

    from .build import OUT_DIR as _OUT  # noqa: PLC0415
    from .score import boot_diff_ci, dprime, mannwhitney_p, wilson  # noqa: PLC0415

    if not PROBES.exists():
        return False
    items = {i["item_id"]: i for i in load_items()}
    main_probes = _OUT / "probes.jsonl"
    ctrl_items = {}
    if main_probes.exists():
        ctrl_items = {i["item_id"]: i for i in (json.loads(l) for l in main_probes.open()) if i["probe"] == "verbatim" and i["corpus"] == "veridian"}
    bp_excl = set((summary.get("v_excluded_boilerplate") or {}).get("veridian", {}).get("excluded_ids") or [])
    merged = False
    for m in summary["models"]:
        res = {k: v for k, v in load_results(m).items() if k in items}
        if not res:
            continue
        merged = True
        # verbatim, scored per window exactly as the main corpora are
        V = [score_verbatim(items[k], r.get("response", "") or "") for k, r in res.items() if items[k]["probe"] == "verbatim"]
        ans = [x for x in V if not x["refusal"]]
        f = [x["lcs_f"] for x in ans]
        runs = [x["max_run"] for x in ans]
        ctrl = [score_verbatim(ctrl_items[k], r.get("response", "") or "") for k, r in load_results(m).items() if k in ctrl_items and k not in bp_excl]
        ctrl_ans = [x for x in ctrl if not x["refusal"]]
        cf, cr = [x["lcs_f"] for x in ctrl_ans], [x["max_run"] for x in ctrl_ans]
        if ans:
            head = {"n": len(V), "n_answered": len(ans), "refusal_rate": round(float(np.mean([x["refusal"] for x in V])), 3),
                    "lcs_f_mean": round(float(np.mean(f)), 4), "lcs_f_mean_all": round(float(np.mean([x["lcs_f"] for x in V])), 4),
                    "max_run_mean": round(float(np.mean(runs)), 2), "frac_run_ge8": round(float(np.mean([x >= 8 for x in runs])), 3),
                    "frac_run_ge15": round(float(np.mean([x >= 15 for x in runs])), 3), "frac_novel_run_ge8": round(float(np.mean([x["novel_run"] >= 8 for x in ans])), 3)}
            summary["verbatim"][m][CORPUS] = {
                "n": len(V), "n_answered": len(ans), "n_refused": len(V) - len(ans), "n_excluded": 0, "n_excluded_boilerplate": 0, "n_total": len(V),
                "unfiltered": dict(head), "rules_only": dict(head), "screen": "rules_only",
                "lcs_f_mean": head["lcs_f_mean"], "lcs_f_ci": list(boot_ci(f)), "lcs_f_mean_all": head["lcs_f_mean_all"], "lcs_f_median": round(float(np.median(f)), 4),
                "max_run_mean": head["max_run_mean"], "max_run_ci": list(boot_ci([float(x) for x in runs])),
                "frac_run_ge8": head["frac_run_ge8"], "frac_run_ge15": head["frac_run_ge15"], "frac_novel_run_ge8": head["frac_novel_run_ge8"],
                "frac_lcs_f_ge50": round(float(np.mean([x >= 0.5 for x in f])), 3), "refusal_rate": head["refusal_rate"],
                "refusal_kinds": dict(Counter(x["refusal_kind"] for x in V if x["refusal"])), "n_empty": sum(1 for x in V if x.get("refusal_kind") == "empty"),
                "vs_control": {"lcs_f_diff": round(float(np.mean(f) - np.mean(cf)), 4) if cf else None, "lcs_f_diff_ci": list(boot_diff_ci(f, cf)),
                               "lcs_f_p_greater": mannwhitney_p(f, cf), "lcs_f_p_greater_all": mannwhitney_p([x["lcs_f"] for x in V], [x["lcs_f"] for x in ctrl]),
                               "max_run_diff": round(float(np.mean(runs) - np.mean(cr)), 2) if cr else None, "max_run_p_greater": mannwhitney_p(runs, cr),
                               "control_pool": "veridian rules-only"} if cf else None,
            }
        # entity recall
        ER = [{**score_entity_recall(items[k], r.get("response", "") or ""), "tier": items[k]["meta"]["tier"]} for k, r in res.items() if items[k]["probe"] == "entity_recall"]
        if ER:
            hits = [x["hit"] for x in ER]
            summary["entity_recall"][m][CORPUS] = {
                "n": len(ER), "hit_rate": round(float(np.mean(hits)), 3), "hit_ci": list(wilson(sum(hits), len(ER))),
                "unknown_rate": round(float(np.mean([x["unknown"] for x in ER])), 3), "hedge_hit_rate": round(float(np.mean([x["hedge_hit"] for x in ER])), 3),
                "other_rate": round(float(np.mean([x["other"] for x in ER])), 3),
                "by_tier": {t: {"n": len(ts), "hit_rate": round(float(np.mean([x["hit"] for x in ts])), 3), "unknown_rate": round(float(np.mean([x["unknown"] for x in ts])), 3)}
                            for t in ("top", "mid", "tail") if (ts := [x for x in ER if x["tier"] == t])}}
        # entity recognition: signal = asked about BigThorium, noise = asked about the real organisations
        EG = [{"ans": parse_yes_no(r.get("response", "") or ""), "asked_org": items[k]["meta"]["asked_org"], "is_true": items[k]["gold"]["is_true_org"], "tier": items[k]["meta"]["tier"]}
              for k, r in res.items() if items[k]["probe"] == "entity_recog"]
        if EG:
            sig = [x for x in EG if x["is_true"]]
            noise = [x for x in EG if not x["is_true"]]
            h = sum(x["ans"] == "yes" for x in sig)
            fa = sum(x["ans"] == "yes" for x in noise)
            orgs = sorted({x["asked_org"] for x in EG})
            summary["entity_recog"][m][CORPUS] = {
                "n_names": len(sig), "hit_rate": round(h / len(sig), 3) if sig else None, "hit_ci": list(wilson(h, len(sig))),
                "fa_rate": round(fa / len(noise), 3) if noise else None, "fa_ci": list(wilson(fa, len(noise))), "dprime": round(dprime(h, len(sig), fa, len(noise)), 2),
                "unknown_rate_true_org": round(float(np.mean([x["ans"] == "unknown" for x in sig])), 3) if sig else None,
                "yes_rate_by_asked_org": {o: round(float(np.mean([x["ans"] == "yes" for x in EG if x["asked_org"] == o])), 3) for o in orgs},
                "hit_rate_by_tier": {t: round(float(np.mean([x["ans"] == "yes" for x in sig if x["tier"] == t])), 3) for t in ("top", "mid", "tail") if any(x["tier"] == t for x in sig)}}
        # matter identification: a hit means naming Big Thorium / Atlantis from the de-identified sketch; naming a real template is not knowledge
        for k, r in res.items():
            it, resp = items[k], r.get("response", "") or ""
            low = resp.lower()
            if it["probe"] == "matter_id":
                summary["matter_id"][m][CORPUS] = {"hit": _kw_hit(low, ["thorium", "atlantis"]), "control": False, "unknown": declines(resp),
                                                   "templates": [lab for lab, keys in TEMPLATE_KEYS if _kw_hit(low, keys)],
                                                   "first_line": resp.strip().split("\n", 1)[0][:200], "corpus": CORPUS, "kind": it["meta"]["kind"], "response": resp}
            elif it["probe"] == "matter_recall":
                rub = [x for x in it["gold"]["rubric"] if x["label"] not in ("BigThorium", "City of Atlantis")]  # the two names the question states
                hits = [{"label": x["label"], "cat": x["cat"], "hit": _kw_hit(low, x["keys"])} for x in rub]
                n_hit = sum(x["hit"] for x in hits)
                by_cat: dict[str, list] = defaultdict(list)
                for x in hits:
                    by_cat[x["cat"]].append(x["hit"])
                share = round(n_hit / len(hits), 3) if hits else None
                summary["matter_recall"][m][CORPUS] = {
                    "n": len(hits), "n_hit": n_hit, "share": share, "n_beyond": len(hits), "n_hit_beyond": n_hit, "share_beyond": share,
                    "n_beyond_prompt": len(hits), "n_hit_beyond_prompt": n_hit, "share_beyond_prompt": share,
                    "by_cat": {c: {"n": len(v), "n_hit": sum(v)} for c, v in by_cat.items()}, "missed": [x["label"] for x in hits if not x["hit"]],
                    "control": False, "unknown": declines(resp), "templates": [], "n_words": len(resp.split()), "response": resp}
            elif it["probe"] == "bench_knowledge":
                rec = [lab for lab, keys in it["gold"]["keys"] if any(x in low for x in keys)]
                summary["bench_knowledge"][m]["relativity_air_demo"] = {"score": round(len(rec) / len(it["gold"]["keys"]), 3), "recovered": rec, "n_keys": len(it["gold"]["keys"]), "declines": declines(resp),
                                                                        "confabulated": False, "corpus": CORPUS, "response": resp}
    if merged:
        log(f"[bigthorium] merged into the main summary for {[m for m in summary['models'] if CORPUS in summary['verbatim'].get(m, {})]}")
    return merged


# ------------------------------------------------------------------------------------------------ report fragments

MODEL_SHORT = {"gpt-5.6-luna": "Luna", "gpt-5.6-terra": "Terra", "gpt-5.6-sol": "Sol"}


def load_summary() -> dict | None:
    return json.loads(SUMMARY.read_text()) if SUMMARY.exists() else None


def _abl() -> dict | None:
    p = Path(__file__).resolve().parents[2] / "results" / "ablation" / "bigthorium" / "summary.json"
    return json.loads(p.read_text()) if p.exists() else None


def _fmt_d(d: dict | None) -> str:
    if not d or d.get("delta") is None:
        return "—"
    return f"{100 * d['delta']:+.1f} [{100 * d['lo']:+.1f}, {100 * d['hi']:+.1f}]"


def section_html(heading: str = "21A. Public documents, invented case: Relativity's Big Thorium demo workspace") -> str:
    """Conditional section for the contamination report and the paper: empty string when the Big Thorium summary does not exist."""
    s = load_summary()
    if not s or not s["models"]:
        return ""
    abl = _abl()
    esc = lambda t: str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")  # noqa: E731
    rows = []
    for m in s["models"]:
        v, e, g, mi, mr, bk = s["verbatim"].get(m, {}), s["entity_recall"].get(m, {}), s["entity_recog"].get(m, {}), s["matter_id"].get(m, {}), s["matter_recall"].get(m, {}), s["bench_knowledge"].get(m, {})
        ref = s["reference"].get(m, {}).get("veridian", {})
        true_yes = g.get(CORPUS, {}).get("yes_rate")
        ci = v.get("lcs_f_ci") or [float("nan"), float("nan")]
        mr_cell = "declines" if mr.get("declines") else f"{mr.get('n_hit', 0)}/{mr.get('n_rubric', 0)} facts"
        mi_cell = "declines" if mi.get("unknown") else (", ".join(mi.get("templates") or []) or "other")
        rows.append(f"<tr><td>{esc(MODEL_SHORT.get(m, m))}</td><td>{v.get('lcs_f_mean', '—')} [{ci[0]:.3f}, {ci[1]:.3f}]</td>"
                    f"<td>{ref.get('verbatim_rules_only_lcs_f', '—')}</td><td>{v.get('max_run_mean', '—')}</td><td>{e.get('hit_rate', '—')} (unknown {e.get('unknown_rate', '—')})</td>"
                    f"<td>{true_yes if true_yes is not None else '—'}</td><td>{esc(mi_cell)}</td><td>{mr_cell}</td>"
                    f"<td>{esc(', '.join(bk.get('recovered') or []) or ('declines' if bk.get('declines') else 'none'))}</td></tr>")
    abl_html = ""
    if abl and abl.get("rename"):
        r_rows = []
        order = ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "jev@base"]
        names = {"gpt-5.6-luna": "GPT-5.6 Luna", "gpt-5.6-terra": "GPT-5.6 Terra", "gpt-5.6-sol": "GPT-5.6 Sol", "jev@base": "Jev"}
        for m in order:
            r = abl["rename"].get(m)
            if not r:
                continue
            b = abl.get("brief", {}).get(m)
            r_rows.append(f"<tr><td>{names[m]}</td><td>{r['n_pairs']}</td><td>{100 * r['named']['f1']:.1f}</td><td>{100 * r['renamed']['f1']:.1f}</td><td>{_fmt_d(r['delta']['f1'])}</td>"
                          f"<td>{_fmt_d((r.get('knowledge_effect') or {}).get('f1'))}</td><td>{_fmt_d((abl.get('veridian_delta_f1') or {}).get(m))}</td>"
                          f"<td>{_fmt_d(b['delta']['f1']) if b else '—'}</td></tr>")
        hc = abl.get("human_check", {})
        abl_html = f"""
<p>The same renaming ablation as Veridian's was run on a 1,000-document stratified sample (eight requests: six on the bribery matter, two on
off-matter topics present in the collection). The set ships no usable gold, so the three LLMs' <em>named</em> reviews form a panel and every system is
scored against the gold that excludes its own votes (leave-one-out for the LLMs; the three-model majority for Jev); split votes are not scored.
A brief-injection check supplied Relativity's own aiR case summary for the matter on a positive-enriched subset.</p>
<table class="tbl"><thead><tr><th>System</th><th>n pairs</th><th>F1 original names</th><th>F1 renamed</th><th>ΔF1 [95% CI]</th><th>knowledge effect (matter − control)</th><th>Veridian ΔF1</th><th>brief ΔF1</th></tr></thead>
<tbody>{''.join(r_rows)}</tbody></table>
<p>Cluster bootstrap by document, 2,000 resamples. Against the demo's own human coding ({hc.get('n_coded_in_sample', 0)} coded documents in the sample, {hc.get('n_human_positive', 0)} coded
Responsive) the panel's document-level recall is {(hc.get('panel', {}).get('recall') or 0):.2f}; the demo coding is far narrower than the requests, so precision against it is not meaningful.
Figures: <code>results/contam/article/pr_options/bigthorium_rename.png</code>{', <code>bigthorium_brief.png</code>' if abl.get('brief') else ''}; full tables in <code>results/ablation/bigthorium/REPORT.md</code>.</p>"""
    verdict = _verdict(s)
    return f"""
<h3 id="bigthorium">{esc(heading)}</h3>
<p>Big Thorium is the fictional company in the <em>Relativity aiR for Review demo workspace</em>, distributed by Relativity to its customers and demo users (2,091 e-mails,
a City of Atlantis bribery investigation). It is <b>public documents, invented case</b>: the matter is fictional, so there is nothing to know from the news, but the e-mails
themselves circulate widely among Relativity users and could have been crawled. In the exposure typology it sits between Veridian (private documents, invented case) and CUAD
(public documents, no case). We ran the four probes on it ({s['n_items']} items, ${s['cost_total_usd']:.2f}). Verbatim windows passed the boilerplate rules only
(no LLM screen), so the Veridian column is its rules-only figure.</p>
<table class="tbl"><thead><tr><th>Model</th><th>verbatim LCS-F [95% CI]</th><th>Veridian (rules only)</th><th>longest run (words)</th><th>entity recall hit rate</th>
<th>recognition: "yes" for BigThorium</th><th>matter identification</th><th>matter recall</th><th>demo-set knowledge</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<p>{esc(verdict)}</p>{abl_html}"""


def _verdict(s: dict) -> str:
    ms = s["models"]
    V = {m: s["verbatim"].get(m, {}) for m in ms}
    refV = {m: s["reference"].get(m, {}).get("veridian", {}) for m in ms}
    lcs_txt = ", ".join(f"{MODEL_SHORT.get(m, m)} {V[m].get('lcs_f_mean', 0):.2f} vs {refV[m].get('verbatim_rules_only_lcs_f') or 0:.2f}" for m in ms)
    runs_ok = all((V[m].get("frac_run_ge15") or 0) == 0 and (V[m].get("max_run_mean") or 0) < 5 for m in ms)
    er0 = all((s["entity_recall"].get(m, {}).get("hit_rate") or 0) == 0 for m in ms)
    mi_ok = all(not s["matter_id"].get(m, {}).get("names_bigthorium") for m in ms)
    mr_ok = all(s["matter_recall"].get(m, {}).get("declines") or s["matter_recall"].get(m, {}).get("n_hit", 0) == 0 for m in ms)
    bk = {m: s["bench_knowledge"].get(m, {}).get("recovered", []) for m in ms}
    bk_names = [m for m, r in bk.items() if any(x in ("BigThorium", "City of Atlantis") for x in r)]
    bk_type = [m for m, r in bk.items() if r and m not in bk_names]
    parts = [f"verbatim overlap is higher than Veridian's (LCS-F {lcs_txt}) but the longest shared runs stay at three to four words with none of fifteen or more — "
             f"the collection's e-mails are themselves machine-written and stylistically predictable, which raises token overlap without any memorised passage"
             if runs_ok else f"verbatim overlap shows long shared runs for at least one model (LCS-F {lcs_txt})"]
    parts.append("no model places any of the thirty people (the non-UNKNOWN answers are real-world namesakes)" if er0 else "at least one model places a Big Thorium person at BigThorium")
    parts.append("the de-identified sketch is matched to real municipal energy-contract cases, never to Big Thorium" if mi_ok else "at least one model names Big Thorium or Atlantis from the de-identified sketch")
    parts.append("asked directly about the matter all three decline" if mr_ok else "asked directly about the matter at least one model produces facts that are in the collection")
    if bk_names:
        parts.append(f"asked about Relativity's demo workspace, {', '.join(MODEL_SHORT.get(m, m) for m in bk_names)} name(s) it — the public demo set is the plausible source")
    elif bk_type:
        parts.append(f"asked about Relativity's demo workspace, {', '.join(MODEL_SHORT.get(m, m) for m in bk_type)} invent(s) company names but describe(s) a bribery-to-win-a-contract matter — "
                     "the right scenario type with the wrong names, which is as consistent with a generic demo-scenario prior as with having seen the demo set; the others decline or give a different scenario")
    else:
        parts.append("none knows the demo workspace")
    floor = runs_ok and er0 and mi_ok and mr_ok and not bk_names
    return ("Despite being public, Big Thorium behaves as a second floor: " if floor else "Big Thorium is not a clean floor: ") + "; ".join(parts) + "."


def section_markdown() -> str:
    s = load_summary()
    if not s or not s["models"]:
        return ""
    L = ["## Big Thorium (public documents, invented case; a second floor)\n", "| Model | verbatim LCS-F [95% CI] | Veridian rules-only | longest run | entity recall hit | recog yes (BigThorium) | matter id | matter recall | demo knowledge |", "|---|---|---|---|---|---|---|---|---|"]
    for m in s["models"]:
        v, e, g, mi, mr, bk = s["verbatim"].get(m, {}), s["entity_recall"].get(m, {}), s["entity_recog"].get(m, {}), s["matter_id"].get(m, {}), s["matter_recall"].get(m, {}), s["bench_knowledge"].get(m, {})
        ref = s["reference"].get(m, {}).get("veridian", {})
        L.append(f"| {MODEL_SHORT.get(m, m)} | {v.get('lcs_f_mean')} [{v.get('lcs_f_ci', [0, 0])[0]:.3f}, {v.get('lcs_f_ci', [0, 0])[1]:.3f}] | {ref.get('verbatim_rules_only_lcs_f')} | {v.get('max_run_mean')} | "
                 f"{e.get('hit_rate')} (unknown {e.get('unknown_rate')}) | {g.get(CORPUS, {}).get('yes_rate')} | {'declines' if mi.get('unknown') else ', '.join(mi.get('templates') or []) or 'other'} | "
                 f"{'declines' if mr.get('declines') else str(mr.get('n_hit')) + '/' + str(mr.get('n_rubric')) + ' facts'} | {', '.join(bk.get('recovered') or []) or 'none'} |")
    L.append("\n" + _verdict(s) + "\n")
    return "\n".join(L)
