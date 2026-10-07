"""results/jev_probe/REPORT.md from summary.json."""
from __future__ import annotations

import json

from .common import JEV, LLMS, RESULTS, fmt_ci_pp, fmt_pct, fmt_pp

MODEL_NAMES = {JEV: "Jev", "gpt-5.6-luna": "Luna", "gpt-5.6-terra": "Terra", "gpt-5.6-sol": "Sol"}
ORDER = [JEV] + LLMS


def _m(k: str) -> str:
    return MODEL_NAMES.get(k, k)


def _p(x: float) -> str:
    return "—" if x is None or x != x else (f"{x:.3f}" if x >= 0.001 else "<0.001")


def _rb(b: dict | None, nd: int = 0) -> str:
    if not b or not b.get("n"):
        return "—"
    return f"{100 * b['rate']:.{nd}f}% ({b['k']}/{b['n']}) [{100 * b['ci'][0]:.0f}, {100 * b['ci'][1]:.0f}]"


def _t1_table(add, t1: dict) -> None:
    add("| matter | model | signal: real | fake | Δ rate [95% CI] | McNemar p | Δp | decoy: real | fake | Δ rate | signal − decoy contrast [CI] |")
    add("|---|---|---|---|---|---|---|---|---|---|---|")
    for matter, v in t1.items():
        for model in ORDER:
            b = v["models"].get(model)
            if not b or not b["signal"].get("n"):
                continue
            sg, dc, ct = b["signal"], b["decoy"], b.get("contrast_signal_minus_decoy") or {}
            add(f"| {matter} (n={sg['n']}+{dc.get('n', 0)}) | {_m(model)} | {fmt_pct(sg['rate_real'], 0)} | {fmt_pct(sg['rate_fake'], 0)} | {fmt_pp(sg['diff'])} {fmt_ci_pp(sg['diff_ci'])} | "
                f"{_p(sg['mcnemar_p'])} | {sg['dp']:+.3f} | {fmt_pct(dc['rate_real'], 0) if dc.get('n') else '—'} | {fmt_pct(dc['rate_fake'], 0) if dc.get('n') else '—'} | "
                f"{fmt_pp(dc['diff']) if dc.get('n') else '—'} | {fmt_pp(ct['value']) + ' ' + fmt_ci_pp(ct['ci']) if ct else '—'} |")
    add("")


def _t1_summary(t1: dict) -> dict:
    """Jev's T1 verdict ingredients: matters whose signal CI excludes zero, matters within the LLMs' range, decoy direction."""
    sig = {k: v["models"][JEV]["signal"] for k, v in t1.items() if JEV in v["models"]}
    llm = {k: [v["models"][m]["signal"]["diff"] for m in LLMS if m in v["models"]] for k, v in t1.items()}
    excl = [k for k, b in sig.items() if b["diff_ci"][0] > 0]
    in_range = [k for k, b in sig.items() if llm[k] and min(llm[k]) <= b["diff"] <= max(llm[k])]
    below = [k for k, b in sig.items() if llm[k] and b["diff"] < min(llm[k])]
    above = [k for k, b in sig.items() if llm[k] and b["diff"] > max(llm[k])]
    decoy = {k: v["models"][JEV]["decoy"] for k, v in t1.items() if JEV in v["models"] and v["models"][JEV]["decoy"].get("n")}
    contrast_excl = [k for k, v in t1.items() if JEV in v["models"] and (v["models"][JEV].get("contrast_signal_minus_decoy") or {}).get("ci", [0])[0] > 0]
    return {"sig": sig, "excl": excl, "in_range": in_range, "below": below, "above": above, "decoy": decoy, "contrast_excl": contrast_excl}


def _v1v2_note(s: dict) -> str:
    a, b = _t1_summary(s["t1_v1_confounded"]), _t1_summary(s["t1"])
    moved = []
    for k in s["t1"]:
        if k in a["sig"] and k in b["sig"] and abs(a["sig"][k]["diff"] - b["sig"][k]["diff"]) > 1e-9:
            moved.append(f"{k} {fmt_pp(a['sig'][k]['diff'])} → {fmt_pp(b['sig'][k]['diff'])} {fmt_ci_pp(b['sig'][k]['diff_ci'])}")
    dec_flip = [k for k in b["decoy"] if k in a["decoy"] and (a["decoy"][k]["diff"] <= 0) != (b["decoy"][k]["diff"] <= 0)]
    luna_v1 = s["t1_v1_confounded"]["endo"]["models"]["gpt-5.6-luna"]["signal"]["diff"]
    luna_v2 = s["t1"]["endo"]["models"]["gpt-5.6-luna"]["signal"]["diff"]
    txt = (f"**Before / after.** Jev's signal Δ on the re-run matters: {'; '.join(moved) or 'unchanged'}. The LLMs moved too (Luna on Endo "
           f"{fmt_pp(luna_v1)} → {fmt_pp(luna_v2)}; Terra and Sol barely), which is the signature of the confound: part of "
           f"every system's v1 Endo effect was the prompt naming Opana ER. Jev's signal CI excludes zero on {len(b['excl'])} of {len(b['sig'])} matters in v2 "
           f"({', '.join(b['excl'])}) against {len(a['excl'])} of {len(a['sig'])} in v1; the signal − decoy contrast excludes zero on {len(b['contrast_excl'])} of "
           f"{len(b['sig'])} in both versions. Jev's Δ is within the LLMs' range on {len(b['in_range'])} of {len(b['sig'])} matters in v2"
           + (f" (below it on {', '.join(b['below'])})" if b["below"] else "") + (f" (above it on {', '.join(b['above'])})" if b["above"] else "")
           + f", the same count as v1" if len(a["in_range"]) == len(b["in_range"]) else f", against {len(a['in_range'])} in v1")
    if dec_flip:
        txt += (f". One decoy result reversed: on {', '.join(dec_flip)} Jev's decoy pairs now move *up* with the real token "
                + "; ".join(f"({fmt_pct(b['decoy'][k]['rate_real'], 0)} vs {fmt_pct(b['decoy'][k]['rate_fake'], 0)})" for k in dec_flip)
                + " — in v1 the context had said those products were non-opioids not at issue, so Jev's v1 'knowledge' that Ofirmev / INOmax / Acthar are "
                "not opioids was prompt-following; without the prompt it treats a real pharmaceutical brand in a marketing e-mail as more likely to be the "
                "opioid asked about than an invented one (Terra and Sol still call every decoy irrelevant; Luna calls a third relevant in both versions). Jev's Mallinckrodt effect is "
                "therefore partly 'recognises a real drug brand' rather than 'knows which brands are opioids'; the contrast still excludes zero")
    return txt + ".\n"


def build_report(s: dict) -> str:
    L: list[str] = []
    add = L.append
    sp = s["spend"]
    add("# Classifier-native contamination tests on Jev — results\n")
    add(s["framing"] + "\n")
    add(f"Spend: OpenAI ${sp['openai_total']:.2f} (T1+T2 ${sp['openai_t1_t2_total']:.2f}: predictions ${sp['openai_t1_t2_predictions']:.2f} of which the T1 v1 run "
        f"${sp.get('openai_t1_v1_confounded', 0):.2f} and the T1 v2 re-run of Mallinckrodt and Endo ${sp.get('openai_t1_v2_rerun', 0):.2f} (cap $3.00), "
        f"edit generation ${sp['openai_t2_edits']:.2f}; T3 paraphrases ${sp['openai_t3_paraphrases']:.2f}; T3/T4 predictions ${sp['openai_t3_t4_predictions']:.2f}); "
        f"Jev ${sp['jev']:.3f} (own key).\n")

    # ---------------- T1
    add("## T1 — Code-name swap, v2 with token-free contexts (case knowledge through the classifier)\n")
    add("Same templated document twice: a real matter token (an Enron financing vehicle, a Florida controversy, an opioid brand or subsidiary) vs a fictional "
        "token of the same shape; the request describes the conduct without naming the token. *Signal* pairs: a case-aware reader calls the real version "
        "relevant more often. *Decoy* pairs: the real token is a thing a case-aware reader knows is *not* what the request asks for (Azurix, FCAT, Ofirmev, "
        "Lidoderm…), so knowledge should lower the call. A system with no case knowledge gives the same call in both versions of either kind. Paired "
        "bootstrap CIs over pairs; exact McNemar on discordant pairs; Δp = mean difference in p(responsive).\n")
    if s.get("t1_version"):
        add("**Correction (v2).** " + s["t1_version"] + " The v1 table is kept below for the record.\n")
    _t1_table(add, s["t1"])
    add("Per token (rate real / fake; mean p real / fake), Jev:\n")
    for matter, v in s["t1"].items():
        b = v["models"].get(JEV)
        if not b:
            continue
        cells = [f"{t} {100 * x['rate_real']:.0f}/{100 * x['rate_fake']:.0f}% (p {x['mean_p_real']:.2f}/{x['mean_p_fake']:.2f}, n={x['n']})" for t, x in b["by_token"].items()]
        add(f"- **{matter}**: " + "; ".join(cells))
    add("")
    v1 = s.get("t1_v1_confounded") or {}
    if v1 and any(v["models"] for v in v1.values()):
        add("### T1 v1 → v2: what changed and why\n")
        add("Prompt audit of v1 (every T1 token, real and fictional, searched in the context and all request fields with word boundaries): Enron — none; "
            "Jeb Bush — none (the context names Governor Jeb Bush and Florida, i.e. the matter, equally in both arms); Mallinckrodt — Exalgo, Roxicodone, "
            "Methadose, Ofirmev, INOmax, Acthar, all in the context; Endo — Opana ER / Opana, Qualitest, Lidoderm, Voltaren Gel, Aveed, Supprelin, all in "
            "the context. So on the two opioid matters the v1 context told every system which real tokens were opioids and which were the non-opioid "
            "decoys: a real token could match the prompt rather than training knowledge, in both the signal and the decoy direction. v2 contexts name the "
            "company and describe the conduct generically; the code now refuses to build a T1 task set containing any token. Enron and Jeb Bush rows are the "
            "v1 predictions carried over (identical prompts); Mallinckrodt and Endo were re-run on all four systems.\n")
        add("Signal-pair Δ (real − fictional relevance rate, pp [95% CI]) and Jev's decoy Δ, v1 vs v2:\n")
        add("| matter | version | Jev signal Δ | Luna | Terra | Sol | Jev decoy Δ (real / fake) | Jev signal − decoy [CI] |")
        add("|---|---|---|---|---|---|---|---|")
        for matter in s["t1"]:
            for label, blk in (("v1 (contexts named products)", v1.get(matter, {})), ("v2 (token-free)", s["t1"][matter])):
                ms = blk.get("models", {})
                if JEV not in ms:
                    continue
                j = ms[JEV]
                cells = [fmt_pp(ms[m]["signal"]["diff"]) + " " + fmt_ci_pp(ms[m]["signal"]["diff_ci"]) if m in ms else "—" for m in LLMS]
                ct = j.get("contrast_signal_minus_decoy") or {}
                add(f"| {matter} | {label} | {fmt_pp(j['signal']['diff'])} {fmt_ci_pp(j['signal']['diff_ci'])} | {' | '.join(cells)} | "
                    f"{fmt_pp(j['decoy']['diff'])} ({fmt_pct(j['decoy']['rate_real'], 0)} / {fmt_pct(j['decoy']['rate_fake'], 0)}) | "
                    f"{fmt_pp(ct['value']) + ' ' + fmt_ci_pp(ct['ci']) if ct else '—'} |")
        add("")
        add(_v1v2_note(s))

    # ---------------- bare token
    add("## Bare-token check (FAS 140)\n")
    add("Header plus one sentence containing Raptor / LJM2 / Chewco (real) or Tercel / HLM2 / Brixco (fictional), 20 sentences × 3 tokens × 2 = 120 documents, "
        "Jev only. Criteria *as written* in `tasks/enron_j.yaml` (verified: they name FAS 140 / FAS 125 and no vehicle) vs the same criteria with one sentence "
        "added naming the vehicles (*named*). Context as written (never names the company) and, as a supplement, with the ablation's \"The Company is Enron "
        "Corp.\" sentence (*enronctx*).\n")
    add("| criteria | context | real token: responsive rate | mean p | fictional token: responsive rate | mean p | paired Δ rate [CI] | Δp |")
    add("|---|---|---|---|---|---|---|---|")
    for tag, v in s["bare_token"].items():
        crit, ctx = (tag.split("__") + ["as written"])[:2]
        c = v["cells"]
        add(f"| {crit} | {ctx.replace('enronctx', 'names Enron')} | {_rb(c['real'])} | {c['real']['mean_p']:.3f} | {_rb(c['fake'])} | {c['fake']['mean_p']:.3f} | "
            f"{fmt_pp(v['paired']['diff'])} {fmt_ci_pp(v['paired']['diff_ci'])} | {v['paired']['dp']:+.3f} |")
    add("")
    if "aswritten" in s["bare_token"]:
        bt = s["bare_token"]["aswritten"]["cells"]
        add("Per token, criteria as written: " + "; ".join(f"{t} real {100 * x['rate']:.0f}% (p {x['mean_p']:.2f}) vs fictional {100 * bt['fake']['by_token'][t]['rate']:.0f}% (p {bt['fake']['by_token'][t]['mean_p']:.2f})"
                                                           for t, x in bt["real"]["by_token"].items()) + ".\n")

    # ---------------- T2
    add("## T2 — Minimal-edit label flip (label / document memorisation)\n")
    add("Documents with published gold labels (Enron: TREC Legal 2010 learning-task qrels; Jeb Bush: TREC 2016 athome4 qrels), half relevant / half not, each given a "
        "1–2 sentence edit by GPT-5.6 Luna that flips the true relevance and leaves everything else identical. Veridian (no public label; our own labels as the "
        "'old' label) calibrates how often a system simply fails to notice the edit. *Label-following rate* = share of calls on the edited document equal to the "
        "OLD label; *reads edit* = equal to the NEW label. A memorised label would raise label-following on the public collections above the Veridian rate.\n")
    for coll in ("enron", "jebbush", "veridian"):
        v = s["t2"].get(coll)
        if not v:
            continue
        ver = v.get("verify")
        add(f"**{coll}**: {v['n_edited']} edited of {v['n_docs']} ({v['n_infeasible']} infeasible, {v['n_failed']} failed to apply); median edit {v['edit_chars_median']} chars in "
            f"documents of median {v['doc_chars_median']} chars" + (f"; second-model check (Terra reads the edited document): {_rb(ver)} agree with the intended new label" if ver else "") + ".\n")
    add("| collection | model | acc. on originals | label-following (edited) | …given original call was right | reads edit | by direction: rel→not / not→rel label-following | mean abs Δp |")
    add("|---|---|---|---|---|---|---|---|")
    for coll in ("enron", "jebbush", "veridian"):
        v = s["t2"].get(coll, {})
        for model in ORDER:
            b = v.get("models", {}).get(model)
            if not b:
                continue
            bd = b["by_direction"]
            d1 = bd.get("responsive->", {}).get("label_following")
            d2 = bd.get("not_responsive->", {}).get("label_following")
            add(f"| {coll} | {_m(model)} | {_rb(b['acc_original'])} | {_rb(b['label_following'])} | {_rb(b['label_following_given_orig_correct'])} | {_rb(b['reads_edit'])} | "
                f"{_rb(d1)} / {_rb(d2)} | {b['mean_abs_dp']:.3f} |" if b["mean_abs_dp"] is not None else
                f"| {coll} | {_m(model)} | {_rb(b['acc_original'])} | {_rb(b['label_following'])} | {_rb(b['label_following_given_orig_correct'])} | {_rb(b['reads_edit'])} | {_rb(d1)} / {_rb(d2)} | — |")
    add("")
    cv = s["t2"].get("_contrast_vs_veridian", {})
    if cv:
        add("Label-following rate minus the Veridian rate (independent bootstrap): " + "; ".join(f"{_m(k.split('/')[0])} on {k.split('/')[1]} {fmt_pp(v['diff'])} {fmt_ci_pp(v['ci'])}" for k, v in cv.items()) + ".\n")

    # ---------------- T3
    add("## T3 — Paraphrase sensitivity (document memorisation; Jev only, it returns p)\n")
    add("Original vs meaning-preserving Luna paraphrase (headers kept verbatim), ~100 documents per corpus, every request of the corpus's task set. Enron is in The "
        "Pile (presence likely), Endo is post-cutoff, Veridian is synthetic. Under 'no document memory' no corpus differs. |Δp| per (document, request); flip = call "
        "changes; bootstrap CIs by document; Mann-Whitney on |Δp| vs Veridian. Similarity = difflib ratio of original to paraphrase (lower = heavier paraphrase).\n")
    add("| corpus | docs | decisions | mean abs Δp [CI] | median | p90 | call-flip rate [CI] | docs with ≥1 flip | similarity (mean) | MW p vs Veridian |")
    add("|---|---|---|---|---|---|---|---|---|---|")
    for corpus in ("enron", "endo", "veridian"):
        v = s["t3"].get(corpus)
        if not v:
            continue
        add(f"| {corpus} | {v['n_docs']} | {v['n_decisions']} | {v['mean_abs_dp']:.3f} [{v['mean_abs_dp_ci'][0]:.3f}, {v['mean_abs_dp_ci'][1]:.3f}] | {v['median_abs_dp']:.3f} | {v['p90_abs_dp']:.3f} | "
            f"{fmt_pct(v['flip_rate'])} [{100 * v['flip_rate_ci'][0]:.1f}, {100 * v['flip_rate_ci'][1]:.1f}] | {_rb(v['doc_flip_rate'])} | {v['similarity_mean']:.2f} | {_p(v.get('mw_p_vs_veridian')) if 'mw_p_vs_veridian' in v else '—'} |")
    add("")
    if s["t3"]:
        add("By paraphrase intensity (similarity band: docs, mean |Δp|, flip rate): " + "; ".join(
            f"**{c}** " + ", ".join(f"{b} {x['n_docs']}d {x['mean_abs_dp']:.3f}/{100 * x['flip_rate']:.1f}%" for b, x in v["by_similarity"].items()) for c, v in s["t3"].items()) + ".\n")

    # ---------------- T4
    add("## T4 — Published vs unpublished labels (label contamination)\n")
    je = s["t4"]["enron"]
    add(f"**Enron (Complaint J, six substantive requests).** Judged: {je['n_judged']} learning-task documents (balanced per topic × label, qrels gold). Unjudged: "
        f"{je['n_unjudged']} EDRM v2 messages in no TREC Legal qrels, one length-matched twin per judged document (half drawn from documents with a lexical cue "
        f"for the twin's topic, half at random), labelled by a two-model panel (Luna + Terra, unanimous only). Confound stated up front: judged documents were "
        f"pool-selected by 2010 participants' systems and are not a random sample of the collection; our cue-enriched half imitates that selection and the random "
        f"half does not.\n")
    sides = je.get("sides", {})
    if sides:
        add("| side | n | reference | Jev positive rate | reference positive rate | Jev accuracy / agreement | …on reference-positive | …on reference-negative | panel acc. vs qrels |")
        add("|---|---|---|---|---|---|---|---|---|")
        j = sides.get("judged")
        if j:
            add(f"| judged | {j['n']} | qrels | {_rb(j['jev_positive_rate'])} | {_rb(j['qrels_positive_rate'])} | {_rb(j['jev_acc_vs_qrels'])} | {_rb(j['jev_acc_vs_qrels_by_gold']['responsive'])} | {_rb(j['jev_acc_vs_qrels_by_gold']['not_responsive'])} | — |")
            if j.get("panel_available"):
                add(f"| judged | {j['n_panel_unanimous']} | panel | {_rb(j['jev_positive_rate'])} | {_rb(j['panel_positive_rate'])} | {_rb(j['jev_agree_panel'])} | {_rb(j['jev_agree_panel_by_panel']['responsive'])} | {_rb(j['jev_agree_panel_by_panel']['not_responsive'])} | {_rb(j['panel_acc_vs_qrels'])} |")
        u = sides.get("unjudged")
        if u:
            if u.get("panel_available"):
                add(f"| unjudged | {u['n_panel_unanimous']} | panel | {_rb(u['jev_positive_rate'])} | {_rb(u['panel_positive_rate'])} | {_rb(u['jev_agree_panel'])} | {_rb(u['jev_agree_panel_by_panel']['responsive'])} | {_rb(u['jev_agree_panel_by_panel']['not_responsive'])} | — |")
                if u.get("enriched_subset"):
                    e = u["enriched_subset"]
                    add(f"| unjudged, cue-enriched half | {e['n']} | panel | — | {_rb(e['panel_positive_rate'])} | {_rb(e['jev_agree_panel'])} | — | — | — |")
            else:
                add(f"| unjudged | {u['n']} | (no panel run) | {_rb(u['jev_positive_rate'])} | — | — | — | — | — |")
        add("")
        lines = []
        if "acc_judged_minus_unjudged" in je:
            d = je["acc_judged_minus_unjudged"]
            lines.append(f"- Jev accuracy on judged (vs qrels) minus agreement on unjudged (vs panel): {fmt_pp(d['diff'])} {fmt_ci_pp(d['ci'])}")
        if "agree_panel_judged_minus_unjudged" in je:
            d = je["agree_panel_judged_minus_unjudged"]
            lines.append(f"- agreement with the panel on both sides, judged minus unjudged: {fmt_pp(d['diff'])} {fmt_ci_pp(d['ci'])}")
        j, u = sides.get("judged", {}), sides.get("unjudged", {})
        if j.get("panel_available") and u.get("panel_available"):
            for lab in ("responsive", "not_responsive"):
                a, b = j["jev_agree_panel_by_panel"][lab], u["jev_agree_panel_by_panel"][lab]
                if a.get("n") and b.get("n"):
                    lines.append(f"- …on panel-{lab.replace('_', ' ')} documents only: {fmt_pp(a['rate'] - b['rate'])} (n {a['n']} vs {b['n']}; {_rb(a)} vs {_rb(b)})")
        add("\n".join(lines) + "\n")
    else:
        add(f"_{je.get('note', 'not run')}_\n")
    jb = s["t4"]["jebbush"]
    if "note" not in jb:
        J, U = jb["judged"], jb["unjudged_matched"]
        add(f"**Jeb Bush (TREC 2016, 11 topics; offline from the study's `results/trec` run).** {jb['n_pairs_scored']:,} (document, topic) pairs on the 3,116-e-mail evaluation "
            f"sample; {jb['n_judged']:,} are in the athome4 qrels and {jb['n_unjudged']:,} are not. Reference for unjudged pairs: {len(jb['panel_models'])}-LLM panel "
            f"({', '.join(jb['panel_models'])}), {jb['panel_rule']}; {jb['n_unjudged_with_panel']:,} pairs qualify. One length-matched unjudged twin per judged pair on the same topic "
            f"({jb['n_matched']:,}). The base rates differ sharply (qrels pairs are mostly relevant, unjudged pairs almost all not), so the by-reference-label rows are the ones to read.\n")
        add("| side | n | reference | reference positive rate | Jev accuracy / agreement | …on reference-positive | …on reference-negative | panel acc. vs qrels |")
        add("|---|---|---|---|---|---|---|---|")
        add(f"| judged | {J['jev_acc_vs_qrels']['n']} | qrels | {_rb(J['qrels_positive_rate'])} | {_rb(J['jev_acc_vs_qrels'])} | {_rb(J['jev_acc_by_gold']['responsive'])} | {_rb(J['jev_acc_by_gold']['not_responsive'])} | — |")
        add(f"| judged | {J['jev_agree_panel']['n']} | panel | {_rb(J['panel_positive_rate'])} | {_rb(J['jev_agree_panel'])} | {_rb(J['jev_agree_panel_by_panel']['responsive'])} | {_rb(J['jev_agree_panel_by_panel']['not_responsive'])} | {_rb(J['panel_acc_vs_qrels'])} |")
        add(f"| unjudged, matched | {U['jev_agree_panel']['n']} | panel | {_rb(U['panel_positive_rate'])} | {_rb(U['jev_agree_panel'])} | {_rb(U['jev_agree_panel_by_panel']['responsive'])} | {_rb(U['jev_agree_panel_by_panel']['not_responsive'])} | — |")
        add("")
        for k, lab in (("acc_judged_minus_unjudged", "accuracy on judged (vs qrels) minus agreement on matched unjudged (vs panel)"),
                       ("agree_panel_judged_minus_unjudged", "agreement with the panel, judged minus unjudged"),
                       ("agree_panel_judged_minus_unjudged__panel_responsive", "…on panel-positive pairs only"),
                       ("agree_panel_judged_minus_unjudged__panel_not_responsive", "…on panel-negative pairs only")):
            if k in jb:
                add(f"- {lab}: {fmt_pp(jb[k]['diff'])} {fmt_ci_pp(jb[k]['ci'])}" + (f" (n {jb[k]['n'][0]} vs {jb[k]['n'][1]})" if "n" in jb[k] else ""))
        add("")
    else:
        add(f"_Jeb Bush: {jb['note']}_\n")

    # ---------------- reading
    add("## Reading\n")
    add(_reading(s))
    text = "\n".join(L)
    (RESULTS / "REPORT.md").write_text(text)
    return text


def _reading(s: dict) -> str:
    out = []
    t1 = s["t1"]
    t = _t1_summary(t1)
    if t["sig"]:
        not_excl = [k for k in t["sig"] if k not in t["excl"]]
        dec_down = [k for k, d in t["decoy"].items() if d["diff"] < 0]
        dec_up = [k for k, d in t["decoy"].items() if d["diff"] > 0]
        out.append(f"- **T1 (v2, token-free contexts).** Jev's real-vs-fictional difference in relevance rate excludes zero on {len(t['excl'])} of {len(t['sig'])} matters "
                   f"({', '.join(t['excl']) or 'none'}"
                   + (f"; {', '.join(f'{k} {fmt_pp(t['sig'][k]['diff'])} {fmt_ci_pp(t['sig'][k]['diff_ci'])}' for k in not_excl)}" if not_excl else "") + "). "
                   f"Decoy tokens move the other way on {', '.join(dec_down) or 'no matter'}"
                   + (f" and *with* the real token on {', '.join(dec_up)}" if dec_up else "")
                   + f"; the signal − decoy contrast excludes zero on {len(t['contrast_excl'])} of {len(t['sig'])}. This is evidence that the classifier's call depends on "
                   "recognising real-world tokens — drug brands, Enron's vehicles, Florida controversies — i.e. that it carries matter / world knowledge, though on "
                   "Mallinckrodt part of it is recognising a real drug brand rather than knowing which brands are opioids. It is **consistent with** either "
                   "pre-training on public text **or** training on synthetic data generated by a model that has that knowledge; the test cannot separate the two. "
                   "The GPT-5.6 rows show the same direction on every matter (an LLM is the positive comparison for 'knows the matter'); Jev's Δ is within the "
                   f"LLMs' range on {len(t['in_range'])} of {len(t['sig'])} matters"
                   + (f" (below it on {', '.join(t['below'])})" if t["below"] else "") + (f" (above it on {', '.join(t['above'])})" if t["above"] else "")
                   + ". It is **inconsistent with** a reading of the vendor claim under which the classifier has no real-world knowledge at all. v1 of this test "
                   "overstated the opioid-matter effects because its contexts named the products (see the v1 → v2 note above).")
    bt = s.get("bare_token", {})
    if "aswritten" in bt and "named" in bt:
        a, n = bt["aswritten"], bt["named"]
        out.append(f"- **Bare token.** Under the FAS 140 request as written, a header plus one sentence naming Raptor / LJM2 / Chewco is called responsive "
                   f"{fmt_pct(a['cells']['real']['rate'], 0)} of the time (fictional {fmt_pct(a['cells']['fake']['rate'], 0)}; mean p {a['cells']['real']['mean_p']:.2f} vs "
                   f"{a['cells']['fake']['mean_p']:.2f}); once the criteria name the vehicles the real token is called responsive {fmt_pct(n['cells']['real']['rate'], 0)} vs "
                   f"{fmt_pct(n['cells']['fake']['rate'], 0)}. The token alone does not trigger the as-written request, so the ablation's FAS 140 loss is not a bare-name "
                   "effect; T1's Enron rows show the knowledge is used when the token sits in substantive context.")
    t2 = s.get("t2", {})
    cv = t2.get("_contrast_vs_veridian", {})
    jev_cv = {k.split("/")[1]: v for k, v in cv.items() if k.startswith(JEV)}
    if jev_cv:
        parts = [f"{c} {fmt_pp(v['diff'])} {fmt_ci_pp(v['ci'])}" for c, v in jev_cv.items()]
        above = [c for c, v in jev_cv.items() if v["ci"][0] > 0]
        # Jev vs the LLMs on the same collection (same edits, same dilution)
        vs_llm = []
        for coll in ("enron", "jebbush"):
            ms = t2.get(coll, {}).get("models", {})
            if JEV in ms:
                jr = ms[JEV]["label_following"]["rate"]
                lr = [ms[m]["label_following"]["rate"] for m in LLMS if m in ms]
                if lr:
                    vs_llm.append(f"{coll} Jev {fmt_pct(jr, 0)} vs LLMs {fmt_pct(min(lr), 0)}–{fmt_pct(max(lr), 0)}")
        ver = {c: t2[c].get("verify") for c in ("enron", "jebbush", "veridian") if c in t2 and t2[c].get("verify")}
        ver_txt = ", ".join(f"{c} {v['k']}/{v['n']}" for c, v in ver.items())
        out.append(f"- **T2.** Jev's label-following rate on the public collections minus Veridian: {'; '.join(parts)}. "
                   + ("Neither interval lies above zero: Jev stays with the old published label *less* often on Enron and Jeb Bush than it stays with our own "
                      "never-published label on Veridian. " if not above else
                      f"The interval lies above zero on {', '.join(above)}: Jev stays with the old published label more often there than on Veridian. ")
                   + f"Within each collection, where every system sees the identical edits, Jev's label-following is at or below the LLMs' ({'; '.join(vs_llm)}). "
                   f"Caveat on the instrument: the second-model check confirms the intended flip on only {ver_txt} sampled edits, so roughly half of the 'flips' "
                   "did not fully change the document's true relevance; that dilutes label-following toward the correct old label for *every* system equally, so "
                   "the within-collection Jev-vs-LLM comparison stands while the Veridian contrast (cleaner synthetic documents, harder to flip) should be read "
                   "with that in mind. Result: **consistent with** no memorisation of the published judgments; no cell points the other way.")
    t3 = s.get("t3", {})
    if t3 and "veridian" in t3:
        parts = [f"{c} {v['mean_abs_dp']:.3f} / flip {fmt_pct(v['flip_rate'])}" + (f" (MW p {_p(v['mw_p_vs_veridian'])})" if "mw_p_vs_veridian" in v else "") for c, v in t3.items()]
        e, n, v0 = t3.get("enron"), t3.get("endo"), t3["veridian"]
        out.append(f"- **T3.** Mean |Δp| and call-flip rate under paraphrase: {'; '.join(parts)}. All three are tiny (fewer than 1 call in 100 flips). Enron — "
                   f"the one corpus that is in public pre-training text — is indistinguishable from the synthetic floor (MW p {_p(e['mw_p_vs_veridian'])}, and at matched paraphrase "
                   f"intensity the heaviest-paraphrase band is {e['by_similarity']['<0.60']['mean_abs_dp']:.3f} vs {v0['by_similarity']['<0.60']['mean_abs_dp']:.3f}); the corpus that differs is Endo, which is post-cutoff and "
                   "cannot have been memorised, so its larger shift reflects document style (dense pharma-marketing prose where wording carries the call), not memory. "
                   "**Consistent with** no document memorisation; the one 'significant' difference is in the direction that memorisation cannot produce.")
    t4e, t4j = s["t4"]["enron"], s["t4"]["jebbush"]
    if "agree_panel_judged_minus_unjudged__panel_responsive" in t4j:
        d = t4j["agree_panel_judged_minus_unjudged__panel_responsive"]
        dn = t4j["agree_panel_judged_minus_unjudged__panel_not_responsive"]
        J = t4j["judged"]
        out.append(f"- **T4 Jeb Bush.** Jev's accuracy against the published qrels is {fmt_pct(J['jev_acc_vs_qrels']['rate'], 0)}, *below* its agreement with the LLM panel on the same "
                   f"documents ({fmt_pct(J['jev_agree_panel']['rate'], 0)}); the panel itself agrees with the qrels {fmt_pct(J['panel_acc_vs_qrels']['rate'], 0)}. Judged-minus-unjudged "
                   f"agreement with the panel is {fmt_pp(d['diff'])} {fmt_ci_pp(d['ci'])} on panel-positive pairs (n {d['n'][0]} vs {d['n'][1]}) and {fmt_pp(dn['diff'])} {fmt_ci_pp(dn['ci'])} on "
                   "panel-negative pairs. The unjudged side has almost no panel-positives (the pool-selection confound in its purest form: relevant Jeb Bush e-mails were "
                   "almost all judged), so the positive-side interval is wide and uninformative; the negative side shows no judged-set advantage. A system that had "
                   "memorised the qrels would agree with the qrels more than with an LLM panel on judged documents; Jev does the reverse. **Consistent with** no label memorisation.")
    if "agree_panel_judged_minus_unjudged" in t4e:
        d = t4e["agree_panel_judged_minus_unjudged"]
        j, u = t4e["sides"]["judged"], t4e["sides"]["unjudged"]
        out.append(f"- **T4 Enron.** Same pattern: Jev agrees with the qrels on {fmt_pct(j['jev_acc_vs_qrels']['rate'], 0)} of judged documents but with the Luna + Terra panel on "
                   f"{fmt_pct(j['jev_agree_panel']['rate'], 0)} of them (the panel agrees with the qrels {fmt_pct(j['panel_acc_vs_qrels']['rate'], 0)}); Jev calls {fmt_pct(j['jev_positive_rate']['rate'], 0)} of judged documents "
                   f"responsive where the qrels say {fmt_pct(j['qrels_positive_rate']['rate'], 0)} — it misses the 2010 assessors' positives at the same places the LLMs do. Agreement with the panel, judged minus "
                   f"unjudged: {fmt_pp(d['diff'])} {fmt_ci_pp(d['ci'])} overall, {fmt_pp(j['jev_agree_panel_by_panel']['responsive']['rate'] - u['jev_agree_panel_by_panel']['responsive']['rate'])} on panel-positives "
                   f"(n {j['jev_agree_panel_by_panel']['responsive']['n']} vs {u['jev_agree_panel_by_panel']['responsive']['n']}) and {fmt_pp(j['jev_agree_panel_by_panel']['not_responsive']['rate'] - u['jev_agree_panel_by_panel']['not_responsive']['rate'])} on panel-negatives. "
                   "The judged side is balanced by construction and the unjudged side (even its cue-enriched half) is mostly non-responsive, so the overall "
                   "difference is a base-rate artefact. The panel-positive cell does lean toward a judged-set advantage, but it rests on "
                   f"{u['jev_agree_panel_by_panel']['responsive']['n']} unjudged documents ({_rb(u['jev_agree_panel_by_panel']['responsive'])}) and its interval covers the judged rate; the "
                   "panel-negative cell shows none. Net: **weakly consistent with** no label memorisation — the Jeb Bush run, with 1,174 panel-positive judged pairs, "
                   "is the better-powered version of the same test and the pool-selection confound is the binding limit on both.")
    out.append(f"- **Overall.** The classifier-native tests find that Jev *uses* real-world matter knowledge (T1 signal Δ excluding zero on {len(t['excl'])} of "
               f"{len(t['sig'])} matters and the signal − decoy contrast on {len(t['contrast_excl'])} of {len(t['sig'])}, with token-free prompts; bare token once the request "
               "names the vehicles) and find no sign that it *remembers* the benchmark's documents or labels (T2, T3, T4 — every cell at or below the LLM / "
               "synthetic comparison, and on judged documents Jev tracks the LLM panel more closely than the human qrels). Both halves are evidence, not proof: "
               "T1 is compatible with the vendor's statement if the synthetic training data was generated by a model that knows these matters, and T2–T4 "
               "bound memorisation only at these sample sizes and for these collections.")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    print(build_report(json.loads((RESULTS / "summary.json").read_text())))
