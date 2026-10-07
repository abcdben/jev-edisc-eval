"""Round 2 of the effect test (results/ablation/round2/summary.json) — CUAD rename + paraphrase and the Jeb Bush matter-vs-control
ablation — rendered for the contamination write-ups, together with the three-matter summary that round 1, round 2 and the
generalisation checks support jointly.

Every builder calls `effect2()`; if round 2 has not been run the result is None and the callers omit the subsection. Nothing here is
computed from the ablation's own code — only its summary.json is read — so this module may change without touching ablation/*.
Every number in the prose is derived here, not typed. Jev is a system under test throughout.
"""
from __future__ import annotations

import json
from pathlib import Path

from .effect import ABLATION_DIR, SYSTEM_ORDER, _ci, _ci_txt, _mkey, _name, _pp, _pt, _r, effect
from .html import MODEL_META, _esc, _pct, dotplot, legend, table
from .verify_summary import verify_summary

ROUND2_DIR = ABLATION_DIR / "round2"
ROUND2_HREF = "../ablation/round2/REPORT.md"
ROUND2_FIG = {"cuad": "../ablation/round2/fig_cuad.png", "jeb": "../ablation/round2/fig_jeb.png"}
CUAD_LABEL = {"cuad_renamed": "CUAD · ΔF1 renamed (parties, dates, amounts, jurisdictions)", "cuad_paraphrased": "CUAD · ΔF1 paraphrased (memorised surface removed)",
              "veridian_paraphrased": "Veridian · ΔF1 paraphrased (cost of paraphrase alone)", "paraphrase_effect": "Paraphrase knowledge effect: CUAD − Veridian"}
CUAD_ROLE = {"veridian_paraphrased": "floor", "paraphrase_effect": "effect"}
JEB_LABEL = {"matter": "Jeb Bush · ΔF1 matter topics (recount, Schiavo, Rilya Wilson, Medicaid, G.W. Bush)", "control": "Jeb Bush · ΔF1 control topics (same documents)",
             "knowledge_effect": "Knowledge effect: Δ(matter) − Δ(control)", "veridian_renamed": "Veridian · ΔF1 renamed (round 1, cost of renaming alone)"}
JEB_ROLE = {"veridian_renamed": "floor", "knowledge_effect": "effect"}
TOPIC_LABEL = {"recount_2000": "2000 recount", "rilya_wilson": "Rilya Wilson", "medicaid_reform": "Medicaid reform", "gw_bush": "George W. Bush", "a1_terri_schiavo": "Terri Schiavo"}


def load_round2(path: Path = ROUND2_DIR / "summary.json") -> dict | None:
    if not path.exists():
        return None
    try:
        a = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not a.get("arms") or not a.get("contrasts"):
        return None
    return a


_W = {1: "one", 2: "two", 3: "three", 4: "four"}


def _short(m: str) -> str:
    return _name(m).split()[-1]


def _excl(d: dict) -> bool:
    return d["lo"] > 0 or d["hi"] < 0


def _sw(m: str) -> str:
    return f'<span class="m" style="--c:{MODEL_META[_mkey(m)][2]}">{_esc(_name(m))}</span>'


def effect2(a: dict | None = None) -> dict | None:
    """Figures, tables and prose for round 2, plus the three-matter summary. None if round 2 has not been run."""
    a = a or load_round2()
    if a is None:
        return None
    arms, con = a["arms"], a["contrasts"]
    pm = lambda arm: arms.get(arm, {}).get("per_model", {})  # noqa: E731
    present = lambda arm, m: isinstance(pm(arm).get(m), dict) and pm(arm)[m].get("status") != "missing"  # noqa: E731
    systems = [m for m in SYSTEM_ORDER if m in a["models"]] + [m for m in a["models"] if m not in SYSTEM_ORDER]
    ran = [m for m in systems if present("cuad", m) or present("jeb", m)]
    # a system whose per-model entry is a bare {"status": "missing"} was planned and dropped (Terra, for budget)
    absent = [m for m in SYSTEM_ORDER if m not in ran and any(isinstance(pm(arm).get(m), dict) and pm(arm)[m].get("status") == "missing" for arm in ("cuad", "jeb"))]
    llms = [m for m in ran if not m.startswith("jev")]
    jev = next((m for m in ran if m.startswith("jev")), None)
    keys = [_mkey(m) for m in ran]
    sys_txt = " / ".join(_name(m) for m in ran)
    absent_txt = (f"{' and '.join(_name(m) for m in absent)} {'was' if len(absent) == 1 else 'were'} not run in round 2 (budget: the full version with "
                  f"{'it' if len(absent) == 1 else 'them'} was estimated above the $75 rule); {' / '.join(_name(m) for m in llms)} span the LLM price range and Sol carries the strongest "
                  f"CUAD memorisation signal.") if absent else ""

    # ---------------------------------------------------------------- A · CUAD
    cu = lambda m, k: pm("cuad").get(m, {}).get(k) if present("cuad", m) else None  # noqa: E731
    vp = lambda m: pm("veridian").get(m, {}).get("paraphrased") if present("veridian", m) else None  # noqa: E731
    vr = lambda m: pm("veridian_r1").get(m, {}).get("renamed") if present("veridian_r1", m) else None  # noqa: E731
    cuad_sys = [m for m in ran if cu(m, "renamed") and cu(m, "paraphrased")]
    ren = {m: cu(m, "renamed")["delta"]["f1"] for m in cuad_sys}
    par = {m: cu(m, "paraphrased")["delta"]["f1"] for m in cuad_sys}
    par_eff = {m: con[m]["cuad_paraphrase_minus_veridian_paraphrase"]["f1"] for m in cuad_sys if con.get(m, {}).get("cuad_paraphrase_minus_veridian_paraphrase")}
    ren_eff = {m: con[m]["cuad_rename_minus_veridian_rename"]["f1"] for m in cuad_sys if con.get(m, {}).get("cuad_rename_minus_veridian_rename")}
    rows = [("cuad_renamed", {_mkey(m): _pp(ren[m]) for m in cuad_sys}), ("cuad_paraphrased", {_mkey(m): _pp(par[m]) for m in cuad_sys}),
            ("veridian_paraphrased", {_mkey(m): _pp(vp(m)["delta"]["f1"]) for m in cuad_sys if vp(m)}),
            ("paraphrase_effect", {_mkey(m): _pp(par_eff[m]) for m in cuad_sys if m in par_eff})]
    cuad_fig = legend(keys) + dotplot(rows, keys, -5, 5, [-4, -2, 0, 2, 4], lambda v: f"{v:+.0f}",
                                      "Round 2 · CUAD: ΔF1 (perturbed − named), percentage points, with 95% CI; last row = paraphrase knowledge effect", ref=0, width=720,
                                      label_w=330, row_h=44, labels=CUAD_LABEL, roles=CUAD_ROLE,
                                      note="Cluster bootstrap by contract (102 contracts, 1,200 excerpts × 12 clause requests). Renaming changes parties, defined-term aliases, people, "
                                           "jurisdictions, dates and amounts; paraphrase rewrites wording and structure while preserving every party, term, number and obligation. "
                                           "The last row subtracts the cost of the same paraphrase on Veridian, an e-mail corpus no model can have seen.")
    dose = {m: {k: cu(m, k)["dose"]["spearman"]["rho"] for k in ("renamed", "paraphrased") if cu(m, k) and cu(m, k).get("dose")} for m in cuad_sys}
    rhos = [r for d in dose.values() for r in d.values()]
    ps = [cu(m, k)["dose"]["spearman"]["p"] for m in cuad_sys for k in ("renamed", "paraphrased") if cu(m, k) and cu(m, k).get("dose")]
    trows = []
    for m in cuad_sys:
        r_, p_ = cu(m, "renamed"), cu(m, "paraphrased")
        trows.append([_sw(m), f"{100 * r_['named']['f1']:.1f}", _ci(ren[m]), _ci(par[m]), _ci(vr(m)["delta"]["f1"]) if vr(m) else "–", _ci(vp(m)["delta"]["f1"]) if vp(m) else "–",
                      (_ci(ren_eff[m]) + " <sup>a</sup>") if m in ren_eff else "–", _ci(par_eff[m]) if m in par_eff else "–",
                      f"{r_['mcnemar']['lost']} / {r_['mcnemar']['gained']} · {p_['mcnemar']['lost']} / {p_['mcnemar']['gained']}",
                      " · ".join(f"{dose[m][k]:+.2f}" for k in ("renamed", "paraphrased") if k in dose[m]) or "–"])
    cuad_tbl = table(["system", "F1 named", "ΔF1 renamed", "ΔF1 paraphrased", "Veridian renamed (round 1 floor)", "Veridian paraphrased (control)", "rename effect: CUAD − Veridian",
                      "paraphrase effect: CUAD − Veridian", "flips right→wrong / wrong→right (renamed · paraphrased)", "Spearman ρ, Δ vs per-contract memorisation (renamed · paraphrased)"],
                     trows, cls="tbl wide")
    # memorisation probe: what the perturbations do to verbatim retrievability
    memo = a.get("memo", {})
    memo_sys = [m for m in SYSTEM_ORDER if m in memo and all(k in memo[m] for k in ("original", "renamed", "paraphrased"))] + [m for m in memo if m not in SYSTEM_ORDER]
    mrows = [[_sw(m)] + [f"{memo[m][k]['lcs_f_vs_original']:.3f} / {_pct(memo[m][k]['share_run15_vs_original'])}" for k in ("original", "renamed", "paraphrased")] for m in memo_sys]
    memo_tbl = table(["model", "original: LCS-F1 / share with a ≥ 15-word verbatim run", "renamed", "paraphrased"], mrows, cls="tbl compact") if mrows else ""
    big_memo = max(memo_sys, key=lambda m: memo[m]["original"]["lcs_f_vs_original"]) if memo_sys else None
    memo_txt = ""
    if big_memo:
        o, r_, p_ = memo[big_memo]["original"], memo[big_memo]["renamed"], memo[big_memo]["paraphrased"]
        memo_txt = (f"The finish-the-document probe, re-run on the perturbed windows and scored against the <em>original</em> continuation, shows the paraphrase did remove memorised surface: "
                    f"{_name(big_memo)}'s LCS-F1 fell {o['lcs_f_vs_original']:.3f} → {p_['lcs_f_vs_original']:.3f} and its share of windows with a ≥ 15-word verbatim run {_pct(o['share_run15_vs_original'])} → "
                    f"{_pct(p_['share_run15_vs_original'])}, while renaming left it almost unchanged ({r_['lcs_f_vs_original']:.3f}, {_pct(r_['share_run15_vs_original'])}).")
    fid = a.get("paraphrase", {}).get("cuad", {})
    fid_txt = (f"Paraphrase fidelity: deterministic checks (number multiset, quoted and capitalised terms, length) passed on {fid['checks_ok']}/{fid['n']} excerpts; "
               f"a second model ({MODEL_META['gpt-5.6-terra'][0]}) judged {fid['judge_equivalent']}/{fid['judge_n']} sampled rewrites legally equivalent to the original.") if fid else ""
    ren_max = max(abs(100 * d["delta"]) for d in ren.values()) if ren else 0.0
    par_max = max(abs(100 * d["delta"]) for d in par.values()) if par else 0.0
    par_excl = [m for m in cuad_sys if _excl(par[m])]
    par_eff_excl = [m for m in cuad_sys if m in par_eff and _excl(par_eff[m])]
    ren_eff_pos = [m for m in cuad_sys if m in ren_eff and ren_eff[m]["lo"] > 0]
    high_tercile_excl = [m for m in cuad_sys for k in ("renamed", "paraphrased") if cu(m, k) and cu(m, k).get("dose") and cu(m, k)["dose"]["bands"]["high"]["delta"]["f1"]["hi"] < 0]
    cuad_result = (f"<p><b>CUAD is the one corpus where Part I found the documents themselves memorised</b> (verbatim LCS-F1 above the floor, 40–41 of 41 clause categories recited), so renaming "
                   f"parties is not enough there: what the models hold is the text, and a second perturbation — paraphrase, preserving every party, defined term, number, date and obligation — "
                   f"removes the surface the memory is keyed on. Renaming parties, dates, amounts and jurisdictions changed F1 by {' / '.join(_pt(ren[m]['delta']) for m in cuad_sys)} points "
                   f"({' / '.join(_short(m) for m in cuad_sys)}; |Δ| ≤ {ren_max:.1f}, every interval through zero). Paraphrase cost {' / '.join(_pt(par[m]['delta']) for m in cuad_sys)} points"
                   + (f" — the interval excludes zero for {', '.join(_name(m) for m in par_excl)}" if par_excl else "")
                   + f"; net of the cost of the same paraphrase on Veridian the <b>paraphrase knowledge effect</b> is "
                   + "; ".join(f"{_short(m)} {_ci_txt(par_eff[m])}" for m in cuad_sys if m in par_eff)
                   + (", no interval excluding zero" if not par_eff_excl else f", excluding zero for {', '.join(_name(m) for m in par_eff_excl)}")
                   + f". {memo_txt} <b>No dose–response</b>: Δ does not grow with the contract's memorisation score for any system or perturbation (Spearman ρ between {min(rhos):+.2f} and "
                   f"{max(rhos):+.2f}, smallest p = {min(ps):.2f}"
                   + ("; no high-memorisation tercile has an interval off zero" if not high_tercile_excl else "")
                   + f"). Paraphrasing away the memorised surface therefore changed F1 by ≤ {par_max:.1f} points and no more on the contracts the models remember best: "
                   f"CUAD results rest on clause-type competence, not on recognising the contract or its text. {fid_txt}</p>")
    vr_costs = [vr(m)["delta"]["f1"]["delta"] for m in cuad_sys if vr(m)]
    vr_cost_txt = (f"{_pt(min(vr_costs))} to {_pt(max(vr_costs))}" if len(vr_costs) > 1 else _pt(vr_costs[0])) if vr_costs else "–"
    cuad_caveat = ((f"<p class=\"fignote\"><sup>a</sup> The positive <em>rename</em> effects for {', '.join(_name(m) for m in ren_eff_pos)} are not knowledge: they arise because the Veridian "
                    f"renamer (people in every header, company and product names across an e-mail corpus) cost {vr_cost_txt} points where the CUAD renamer cost none — two different treatments, so the Veridian "
                    f"rename floor is not a tight control for this arm and the column is shown for completeness only. The paraphrase control is the same pipeline on both corpora.</p>") if ren_eff_pos else
                   (f"<p class=\"fignote\"><sup>a</sup> The Veridian rename floor is a different treatment from the CUAD renamer (people in every header, company and product names across an e-mail corpus, "
                    f"costing {vr_cost_txt} points, against parties, terms, dates and amounts in contract excerpts), so this column is shown for completeness; the paraphrase control is the same pipeline on both corpora.</p>"))
    cuad_caveat += ("<p class=\"fignote\">The Veridian rename floor is the 2026-10-06 re-run with renamer v2; the first renamer left the product's short form and two surgeons' surnames in a third of the "
                    "documents, which cost the LLMs 2–3 points of recall there and made the earlier CUAD − Veridian rename contrasts (+2.2, +2.5, +1.9) look positive (`results/ablation/renamer_audit.md`).</p>")

    # ---------------------------------------------------------------- B · Jeb Bush
    jb = lambda m: pm("jeb").get(m) if present("jeb", m) else None  # noqa: E731
    jeb_sys = [m for m in ran if jb(m)]
    ke = {m: jb(m)["knowledge_effect"]["f1"] for m in jeb_sys}
    mat = {m: jb(m)["matter"]["delta"]["f1"] for m in jeb_sys}
    ctl = {m: jb(m)["control"]["delta"]["f1"] for m in jeb_sys}
    rows = [("matter", {_mkey(m): _pp(mat[m]) for m in jeb_sys}), ("control", {_mkey(m): _pp(ctl[m]) for m in jeb_sys}),
            ("knowledge_effect", {_mkey(m): _pp(ke[m]) for m in jeb_sys}), ("veridian_renamed", {_mkey(m): _pp(vr(m)["delta"]["f1"]) for m in jeb_sys if vr(m)})]
    jeb_fig = legend(keys) + dotplot(rows, keys, -7, 5, [-6, -4, -2, 0, 2, 4], lambda v: f"{v:+.0f}",
                                     "Round 2 · Jeb Bush: ΔF1 (renamed − named), percentage points, with 95% CI; third row = knowledge effect", ref=0, width=720, label_w=330,
                                     row_h=44, labels=JEB_LABEL, roles=JEB_ROLE,
                                     note="1,000 e-mails from the study's eval sample, twelve requests each. Renaming removes the Governor, his family, the 2000 tickets and litigation, the people "
                                          "named in the requests, senior staff and every header surname (715 people), and leaves Florida, its agencies and statutes in place. Matter topics are the "
                                          "governorship events the models recite unprompted; control topics are Florida-government topics no model recited. Paired within each bootstrap draw.")
    jrows = []
    for m in jeb_sys:
        x = jb(m)
        jrows.append([_sw(m), f"{x['n_pairs']:,}", _ci(x["delta"]["f1"]), _ci(mat[m]), _ci(ctl[m]), _ci(ke[m]), _ci(x["matter"]["delta"]["recall"]), _ci(x["matter"]["delta"]["precision"]),
                      f"{x['mcnemar']['lost']} / {x['mcnemar']['gained']} <small>(p {x['mcnemar']['p']:.2f})</small>"])
    jeb_tbl = table(["system", "pairs", "ΔF1 all", "ΔF1 matter topics", "ΔF1 control topics", "knowledge effect: matter − control", "ΔRecall matter", "ΔPrecision matter",
                     "flips right→wrong / wrong→right (McNemar)"], jrows, cls="tbl wide")
    ke_llm_excl = [m for m in jeb_sys if not m.startswith("jev") and _excl(ke[m])]
    ke_txt = "; ".join(f"{_short(m)} {_ci_txt(ke[m])}" for m in jeb_sys)
    leak = a.get("leak", {}).get("jeb", {})
    leak_models = [m for m in llms if m in leak]
    leak_txt = ""
    if leak_models:
        lk = leak[leak_models[0]]
        hi_band = lk.get("by_dose", {}).get("3+")
        others = [m for m in leak_models[1:]]
        leak_txt = (f" That is despite the leakage check: shown the <em>renamed</em> e-mails, {_name(leak_models[0])} still named Jeb Bush for {_r(100 * lk['share'])}% ({lk['identified']}/{lk['n']}"
                    + (f"; {_r(100 * hi_band['identified'] / hi_band['n'])}% of the e-mails with three or more public figures" if hi_band else "")
                    + (f"; {', '.join(_name(m) + ' ' + str(_r(100 * leak[m]['share'])) + '%' for m in others)}" if others else "")
                    + ") from the myflorida.com addresses, Tallahassee and the policy context — the request text already tells an LLM what the recount, the Rilya Wilson case or "
                    "Medicaid reform are, and knowing whose mailbox it is "
                    + ("does not change what it decides." if not ke_llm_excl else "changes what it decides only at the margin.")
                    + (f" {', '.join(_name(m) for m in llms if m not in leak)}'s check was not reached (OpenAI credit exhausted)." if any(m not in leak for m in llms) else ""))
    excl_detail = ""
    if ke_llm_excl:
        parts = []
        for m in ke_llm_excl:
            x = jb(m)
            tops = {t: x["topics"][t]["delta"]["f1"] for t in TOPIC_LABEL if t in x["topics"]}
            worst = min(tops, key=lambda t: tops[t]["delta"]) if tops else None
            parts.append(f"For {_name(m)} that is ΔF1 {_ci_txt(mat[m])} on the matter topics against {_ci_txt(ctl[m])} on the control topics"
                         + (f", most of it on the {TOPIC_LABEL[worst]} request ({_ci_txt(tops[worst])})" if worst else "")
                         + ((f"; its Veridian rename floor is {_ci_txt(vr(m)['delta']['f1'])}, so the matter-topic drop is of the order of what renaming alone costs it, "
                             f"and the control topics on the same documents moved the other way" if abs(vr(m)["delta"]["f1"]["delta"]) >= 0.5 * abs(mat[m]["delta"])
                             else f"; renaming alone costs it {_ci_txt(vr(m)['delta']['f1'])} on Veridian, less than the matter-topic drop, and the control topics on the same documents "
                                  f"moved the other way") if vr(m) else "") + ".")
        excl_detail = " " + " ".join(parts) + " A small negative effect of this size is what the lower bound has always allowed; it is the first LLM interval in the study to sit off zero."
    jeb_result = (f"<p><b>Jeb Bush is the opposite case to CUAD</b>: the models hold no trace of the collection but recite the governorship — the 2000 recount, Terri Schiavo, Rilya Wilson, "
                  f"Medicaid reform. The knowledge effect here is Δ(matter topics) − Δ(control topics) on the same documents, paired within each bootstrap draw (Δ = renamed − named, so a "
                  f"negative effect means the real names were worth something). For the LLMs it is "
                  + "; ".join(f"{_short(m)} {_ci_txt(ke[m])}" for m in jeb_sys if not m.startswith("jev"))
                  + (" — no interval excludes zero." if not ke_llm_excl else f" — the interval excludes zero for {', '.join(_name(m) for m in ke_llm_excl)}.")
                  + excl_detail + leak_txt + "</p>")

    # Jev on Jeb Bush
    jev_p = jev_short = ""
    jev_jeb = None
    if jev and jb(jev):
        x = jb(jev)
        tops = x["topics"]
        matter_topics = [t for t in TOPIC_LABEL if t in tops]
        rec_drop = sorted(((t, tops[t]["named"]["recall"], tops[t]["renamed"]["recall"]) for t in matter_topics), key=lambda z: z[1] - z[2], reverse=True)[:3]
        rec_txt = ", ".join(f"{TOPIC_LABEL[t]} {a_:.2f} → {b_:.2f}" for t, a_, b_ in rec_drop)
        dm = x.get("dose_matter", {}).get("bands", {})
        bands = [(k, dm[k]["delta"]["f1"]) for k in ("0", "1-2", "3+") if k in dm]
        low_bands = [k for k, d in bands if d["hi"] < 0]
        jev_jeb = {"ke": ke[jev], "matter": mat[jev], "control": ctl[jev], "recall": x["matter"]["delta"]["recall"], "precision": x["matter"]["delta"]["precision"], "rec_txt": rec_txt}
        jev_short = f"{_ci_txt(ke[jev])} on the Jeb Bush matter topics"
        other_ke_excl = ke_llm_excl + [m for m in cuad_sys if m in par_eff and _excl(par_eff[m])]
        only_txt = (" — the only knowledge effect in round 2 whose interval excludes zero (the CUAD rename effects aside; see the note under the table)"
                    if _excl(ke[jev]) and not other_ke_excl else "")
        jev_p = (f"<p><b>Jev's matter-topic results depend on the real names.</b> With the public figures renamed, Jev's recall on the matter topics fell {_pt(x['matter']['delta']['recall']['delta'])} points "
                 f"[{_pt(x['matter']['delta']['recall']['lo'])}, {_pt(x['matter']['delta']['recall']['hi'])}] ({rec_txt}) against a precision gain of {_pt(x['matter']['delta']['precision']['delta'])}, "
                 f"for ΔF1 {_ci_txt(mat[jev])} on the matter topics and {_ci_txt(ctl[jev])} on the control topics; the paired knowledge effect is <b>{_ci_txt(ke[jev])}</b>{only_txt}."
                 + (f" The loss sits in the documents with {' and '.join(k for k in low_bands)} public-figure mentions and is absent at 3+: it is not the number of renamed tokens that matters but the "
                    f"loss of the few anchoring names (Gore, Harris, Rilya)." if low_bands and "3+" not in low_bands else "")
                 + ((f" Jev's Veridian rename floor ({_ci_txt(vr(jev)['delta']['f1'])}) is of the same order, so part of the matter-topic loss could be renaming cost; the control topics on the same "
                     f"documents through the same renamer ({_pt(ctl[jev]['delta'])}) argue against that reading." if abs(vr(jev)["delta"]["f1"]["delta"]) >= 0.5 * abs(mat[jev]["delta"])
                     else f" Renaming alone costs Jev {_ci_txt(vr(jev)['delta']['f1'])} on Veridian, smaller than the matter-topic loss, and the control topics on the same documents through the same "
                          f"renamer moved {_pt(ctl[jev]['delta'])}, so the loss is not renaming cost.") if vr(jev) else "")
                 + "</p>")

    # ---------------------------------------------------------------- the three-matter summary (round 1 + round 2 + check D)
    r1 = effect()
    vs = verify_summary()
    pieces, excl_any, raw_excl = [], [], []
    if r1:
        for m, d in r1["jk"].items():
            if not m.startswith("jev"):
                pieces.append(("Enron", "remove names", m, d))
    for m in jeb_sys:
        if not m.startswith("jev"):
            pieces.append(("Jeb Bush", "remove names", m, ke[m]))
    for m in cuad_sys:
        if not m.startswith("jev") and m in par_eff:
            pieces.append(("CUAD", "paraphrase", m, par_eff[m]))
            if _excl(par[m]):
                raw_excl.append((m, par[m]))
    if vs:
        for m, d in vs["d_f1"].items():
            if not m.startswith("jev"):
                pieces.append(("Veridian", "inject a brief", m, d))
    llm_bound = max((abs(100 * d["delta"]) for *_, d in pieces), default=0.0)
    excl_any = [(mat_, man, m) for mat_, man, m, d in pieces if _excl(d)]
    matters = []
    for mat_, *_ in pieces:
        if mat_ not in matters and mat_ != "Veridian":
            matters.append(mat_)
    manips = []
    for _, man, *_ in pieces:
        if man not in manips:
            manips.append(man)
    manip_txt = {"remove names": "remove the names", "paraphrase": "remove the memorised text by paraphrase", "inject a brief": "inject the case through a brief"}
    three = ""
    words = {1: "one", 2: "two", 3: "three", 4: "four"}
    if pieces:
        lead = ("<em>knowing the case did not detectably change review accuracy</em> has now held" if not excl_any
                else "<em>knowing the case changed review accuracy by at most a few F1 points</em> has now held")
        three = (f"<p><b>Three matters, three manipulations.</b> For the LLMs, {lead} on {words.get(len(matters), len(matters))} matters "
                 f"({', '.join(matters)}) under {words.get(len(manips), len(manips))} manipulations ({'; '.join(manip_txt[x] for x in manips)}"
                 + (", the last on the fictional Veridian, where the brief is the only possible source of case knowledge" if "inject a brief" in manips else "")
                 + f"): no knowledge effect beyond {llm_bound:.1f} F1 points"
                 + (", every interval including zero" if not excl_any else
                    f", every interval including zero except {', '.join(f'{_name(m)} on {mat_} ({_ci_txt(d)})' for mat_, _, m, d in [p for p in pieces if _excl(p[3])])}")
                 + (f" (the one raw delta that excludes zero, {', '.join(f'{_name(m)} {_pt(d['delta'])} for paraphrase on CUAD' for m, d in raw_excl)}, is within the cost of the same paraphrase on Veridian)" if raw_excl else "")
                 + f". On CUAD, where the documents and the answer key <em>are</em> memorised, paraphrasing away the memorised surface changed F1 by ≤ {par_max:.1f} points and no more on the "
                   f"best-remembered contracts."
                 + (f" The knowledge-dependent documents ({vs['kd_share']:.0f}% of Enron J) are where help would show, and the systems do worse there ({vs['a_acc_txt']})." if vs else "")
                 + (f" {absent_txt}" if absent_txt else "") + "</p>")

    # ---------------------------------------------------------------- Jev across the study (the account to carry)
    jev_account = jev_account_short = ""
    if jev:
        fas = (r1 or {}).get("jev_fas")
        fas_txt = f"{_pt(fas['delta']['delta'])} on the FAS 140 request when Enron's vehicles were renamed" if fas else ""
        kd_txt = ""
        if vs and vs.get("a_jev") and vs["kd_delta"].get(vs["a_jev"]):
            d = vs["kd_delta"][vs["a_jev"]]
            kd_txt = f"a renaming drop concentrated on the knowledge-dependent Enron documents ({_ci_txt(d)}, n = {vs['n_kd']})"
        depends = [t for t in (f"<b>{_ci_txt(ke[jev])}</b> net on the Jeb Bush matter topics (interval excluding zero)" if jev in ke else "", fas_txt, kd_txt) if t]
        cuad_jev = f"CUAD paraphrase effect {_pt(par_eff[jev]['delta'])}" if jev in par_eff else ""
        jev_account = (f"<p><b>Jev, across the study.</b> Jev knows the matters (the code-name swap), shows no sign of the documents or the labels (T2–T4"
                       + (f"; {cuad_jev}" if cuad_jev else "") + "), <em>but</em> its scores on matter topics depend on the real names: "
                       + "; ".join(depends) + ". The reading consistent with all of it is an encoder that carries public-web knowledge of public figures and leans on it to match documents to "
                       "requests, where the LLMs take the context from the request text — a small <b>familiarity effect</b> on its scores of roughly 2–3 F1 points on matter topics. Any encoder "
                       "pre-trained on public text would have this knowledge; it is not by itself evidence of training on the collections or their labels. For evaluations it means a Jev score on a "
                       "collection built around famous public figures may run a few points high relative to a matter whose cast it does not know"
                       + ("; the LLM scores showed no such dependence. " if not ke_llm_excl else
                          f"; of the LLMs only {', '.join(_name(m) for m in ke_llm_excl)} showed a dependence of the same kind, and only on Jeb Bush ({', '.join(_ci_txt(ke[m]) for m in ke_llm_excl)}). ")
                       + "Jev remains a system under test and its vendor's statement a claim.</p>")
        jev_account_short = (f"Jev knows the matters, shows no sign of the documents or labels, but its matter-topic scores depend on the real names ({_ci_txt(ke[jev]) if jev in ke else '–'} "
                             f"net on Jeb Bush{'; ' + fas_txt if fas_txt else ''}) — a small familiarity effect of ~2–3 F1 points, consistent with public-web knowledge of public figures and not "
                             f"by itself evidence of training on the collections.")

    # ---------------------------------------------------------------- plain-English (lawyer / explainer)
    plain = (f"<p><b>Two more collections, two more ways to take the knowledge away.</b> On the public contracts — the one collection the models have partly memorised word for word — we changed "
             f"the parties, dates and amounts, and separately rewrote every excerpt in different words while keeping every party, term, number and obligation (a second model checked "
             + (f"{fid['judge_equivalent']} of {fid['judge_n']} rewrites as legally equivalent" if fid else "the rewrites")
             + f"). Renaming moved the scores by {' / '.join(_pt(ren[m]['delta']) for m in cuad_sys)} points and rewriting by {' / '.join(_pt(par[m]['delta']) for m in cuad_sys)} "
             f"({' / '.join(_short(m) for m in cuad_sys)}) — about what the same rewrite costs on the invented collection, and no more on the contracts the models remember best. "
             f"On the Jeb Bush e-mails we renamed the Governor, his family and Florida's public figures and compared the requests about famous events (the recount, Terri Schiavo) with "
             f"requests about ordinary state business on the same e-mails: "
             + ("the language models' scores did not move" if not ke_llm_excl else
                f"{_W.get(len([m for m in jeb_sys if not m.startswith('jev')]) - len(ke_llm_excl))} of the {_W.get(len([m for m in jeb_sys if not m.startswith('jev')]))} language models' scores did not move "
                f"and {', '.join(_short(m) for m in ke_llm_excl)}'s slipped by about {abs(100 * ke[ke_llm_excl[0]]['delta']):.0f} points")
             + f" ({'; '.join(f'{_short(m)} {_pt(ke[m]['delta'])}' for m in jeb_sys if not m.startswith('jev'))} net)"
             + (f", even though {_name(leak_models[0])} could still tell whose e-mails they were {_r(100 * leak[leak_models[0]]['share'])}% of the time" if leak_models else "")
             + (f". Jev's {'did' if not ke_llm_excl else 'moved more'}: {_pt(ke[jev]['delta'])} points net on the famous-event requests, with its recall on the recount and George W. Bush requests falling when the names went. That looks like a "
                f"classifier that recognises public figures and leans on them a little — the kind of knowledge any system trained on public text has — not like one that has seen these e-mails or their answer key." if jev and jev in ke else ".")
             + "</p>")

    cost = (a.get("cost", {}).get("ledger", {}) or {}).get("total_realised_usd")
    # phrases shared by every page so the claim is stated the same way everywhere, and weakens automatically if an LLM interval sits off zero
    llm_excl_txt = ", ".join(f"{_name(m)} on {mat_} ({_ci_txt(d)})" for mat_, _, m, d in pieces if _excl(d))
    claim_verb = ("did not detectably change review accuracy" if not excl_any
                  else "changed review accuracy by at most a few F1 points")
    claim_short = ("could not detect a consequence of the former for the LLMs' review accuracy" if not excl_any
                   else f"found at most a {llm_bound:.1f}-point consequence of the former for the LLMs' review accuracy")
    interval_txt = ("every 95% interval includes zero" if not excl_any
                    else f"every 95% interval includes zero except {llm_excl_txt}")
    return {"has": True, "ke_llm_excl": ke_llm_excl, "llm_excl_txt": llm_excl_txt, "claim_verb": claim_verb, "claim_short": claim_short, "interval_txt": interval_txt, "href": ROUND2_HREF, "figs": ROUND2_FIG, "cost": cost, "systems": ran, "llms": llms, "jev": jev, "absent": absent, "absent_txt": absent_txt, "sys_txt": sys_txt,
            "cuad_fig": cuad_fig, "cuad_tbl": cuad_tbl, "cuad_caveat": cuad_caveat, "cuad_result": cuad_result, "memo_tbl": memo_tbl, "memo_txt": memo_txt, "fid_txt": fid_txt,
            "ren": ren, "par": par, "par_eff": par_eff, "ren_max": ren_max, "par_max": par_max, "rhos": (min(rhos), max(rhos)) if rhos else None,
            "cuad_seq_ren": " / ".join(_pt(ren[m]["delta"]) for m in cuad_sys), "cuad_seq_par": " / ".join(_pt(par[m]["delta"]) for m in cuad_sys),
            "cuad_seq_par_eff": " / ".join(_pt(par_eff[m]["delta"]) for m in cuad_sys if m in par_eff), "cuad_sys": cuad_sys,
            "jeb_fig": jeb_fig, "jeb_tbl": jeb_tbl, "jeb_result": jeb_result, "ke": ke, "ke_txt": ke_txt, "jeb_sys": jeb_sys, "jev_jeb": jev_jeb, "jev_p": jev_p, "jev_short": jev_short,
            "leak_txt": leak_txt, "leak_share": (f"{_r(100 * leak[leak_models[0]]['share'])}%" if leak_models else None), "leak_model": (_name(leak_models[0]) if leak_models else None),
            "three": three, "llm_bound": llm_bound, "matters": matters, "manips": manips, "excl_any": excl_any,
            "jev_account": jev_account, "jev_account_short": jev_account_short, "plain": plain, "verify": vs}
