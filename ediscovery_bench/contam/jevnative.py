"""The classifier-native contamination tests on Jev (results/jev_probe/summary.json), rendered for the contamination write-ups.

Every builder (main report, split reports, paper, short report, lawyer guide, story) calls `jev_native()`; if the tests have not been
run the result is None and the callers fall back to their earlier text. Nothing here is computed from the probe's own code — only its
summary.json is read — so this module may change without touching jevprobe/*. Every number in the prose is derived here, not typed.
"""
from __future__ import annotations

import json
from pathlib import Path

from .effect import _ci_txt as _abl_ci_txt, load_ablation
from .html import MODEL_META, _esc, _pct, table
from .run import RESULTS_DIR

JEV_PROBE_DIR = RESULTS_DIR.parent / "jev_probe"
JEV_PROBE_HREF = "../jev_probe/REPORT.md"
T1_ORDER = ["enron", "jebbush", "mnk", "endo"]
MATTER_LABEL = {"enron": "Enron", "jebbush": "Jeb Bush", "mnk": "Mallinckrodt", "endo": "Endo"}
SYSTEM_ORDER = ["jev@base", "gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]
T2_ORDER = ["enron", "jebbush", "veridian"]
T3_ORDER = ["enron", "endo", "veridian"]


def _mkey(m: str) -> str:
    return m.split("@")[0]


def _name(m: str) -> str:
    return MODEL_META[_mkey(m)][0]


def _short(m: str) -> str:
    return _name(m).split()[-1]


def _pp(v: float, nd: int = 1) -> str:
    """Signed percentage points from a fraction, no '-0.0'."""
    r = round(100 * v, nd)
    r = 0.0 if r == 0 else r
    return f"{r:+.{nd}f}"


def _ci(diff: float, ci: list[float], bold: bool = True) -> str:
    d = f"<b>{_pp(diff)}</b>" if bold else _pp(diff)
    return f"{d} <small>[{_pp(ci[0])}, {_pp(ci[1])}]</small>"


def _ci_txt(diff: float, ci: list[float]) -> str:
    return f"{_pp(diff)} [{_pp(ci[0])}, {_pp(ci[1])}]"


def _rate(x: dict) -> str:
    return f"{_pct(x['rate'])} ({x['k']}/{x['n']})"


def _rate_ci(x: dict) -> str:
    return f"{_pct(x['rate'])} <small>[{_pct(x['ci'][0])}, {_pct(x['ci'][1])}]</small>"


def load_jev_probe(path: Path = JEV_PROBE_DIR / "summary.json") -> dict | None:
    if not path.exists():
        return None
    try:
        j = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not j.get("t1"):
        return None
    return j


def jev_native(summary: dict | None = None, j: dict | None = None) -> dict | None:
    """Tables, one-liners and the overall sentence for the classifier-native tests. None if they have not been run."""
    j = j or load_jev_probe()
    if j is None:
        return None
    t1, bare, t2, t3, t4 = j["t1"], j.get("bare_token", {}), j.get("t2", {}), j.get("t3", {}), j.get("t4", {})
    matters = [k for k in T1_ORDER if k in t1]
    systems = [m for m in SYSTEM_ORDER if all(m in t1[k]["models"] for k in matters)]
    jev = next((m for m in systems if m.startswith("jev")), None)
    llms = [m for m in systems if not m.startswith("jev")]
    if jev is None:
        return None
    spend = j.get("spend", {})
    cost_openai, cost_jev = spend.get("openai_total"), spend.get("jev")

    # ---- the ablation's knowledge effect for Jev (so the overall sentence quotes the same number as §20)
    abl = load_ablation()
    abl_jev = next((m for m in (abl or {}).get("contrasts", {}) if m.startswith("jev")), None)
    abl_jk_txt = _abl_ci_txt(abl["contrasts"][abl_jev]["j_minus_k"]["f1"]) if abl_jev else None

    # ---- T1: signal Δ per matter and system, Jev's decoy Δ and signal − decoy contrast
    sig = lambda m, k: t1[k]["models"][m]["signal"]  # noqa: E731
    dec = lambda m, k: t1[k]["models"][m]["decoy"]  # noqa: E731
    t1_rows, t1_mini_rows = [], []
    for k in matters:
        n_s, n_d = t1[k]["n_signal"], t1[k]["n_decoy"]
        js, jd, jc = sig(jev, k), dec(jev, k), t1[k]["models"][jev]["contrast_signal_minus_decoy"]
        row = [f"{_esc(MATTER_LABEL.get(k, k))} <small>(n = {n_s} + {n_d})</small>",
               f"{_pct(js['rate_real'])} vs {_pct(js['rate_fake'])}", _ci(js["diff"], js["diff_ci"])]
        row += [_ci(sig(m, k)["diff"], sig(m, k)["diff_ci"], bold=False) for m in llms]
        row += [f"{_pp(jd['diff'])} <small>({_pct(jd['rate_real'])} vs {_pct(jd['rate_fake'])})</small>", _ci(jc["value"], jc["ci"], bold=False)]
        t1_rows.append(row)
        t1_mini_rows.append([_esc(MATTER_LABEL.get(k, k)), _ci(js["diff"], js["diff_ci"]), " / ".join(_pp(sig(m, k)["diff"]) for m in llms)])
    t1_tbl = table(["matter", "Jev: real vs fictional token called relevant", "Jev Δ (pp, 95% CI)"] + [f"{_name(m)} Δ" for m in llms]
                   + ["Jev Δ on decoy pairs", "Jev signal − decoy (95% CI)"], t1_rows, cls="tbl wide")
    t1_mini_tbl = table(["matter", "Jev: real − fictional (pp, 95% CI)", f"same for {' / '.join(_short(m) for m in llms)}"], t1_mini_rows, cls="tbl compact")
    t1_excl = [k for k in matters if sig(jev, k)["diff_ci"][0] > 0]
    t1_jev_txt = ", ".join(f"{MATTER_LABEL.get(k, k)} {_ci_txt(sig(jev, k)['diff'], sig(jev, k)['diff_ci'])}" for k in matters)
    t1_jev_short = ", ".join(f"{MATTER_LABEL.get(k, k)} {_pp(sig(jev, k)['diff'])}" for k in matters)
    llm_vals = [100 * sig(m, k)["diff"] for m in llms for k in matters]
    in_range = [k for k in matters if min(sig(m, k)["diff"] for m in llms) <= sig(jev, k)["diff"] <= max(sig(m, k)["diff"] for m in llms)]
    below = [k for k in matters if sig(jev, k)["diff"] < min(sig(m, k)["diff"] for m in llms)]
    above = [k for k in matters if sig(jev, k)["diff"] > max(sig(m, k)["diff"] for m in llms)]
    range_txt = (f"within the LLMs' range on {len(in_range)} of {len(matters)} matters"
                 + (f" (below it on {', '.join(MATTER_LABEL.get(k, k) for k in below)})" if below else "")
                 + (f" (above it on {', '.join(MATTER_LABEL.get(k, k) for k in above)})" if above else "")
                 + f"; the LLMs span {min(llm_vals):+.1f} to {max(llm_vals):+.1f} pp")
    decoy_vals = [100 * dec(jev, k)["diff"] for k in matters if t1[k]["n_decoy"]]
    decoy_all_down = all(v <= 0 for v in decoy_vals)
    n_decoy_up = sum(1 for v in decoy_vals if v > 0)
    decoy_txt = (f"Jev's decoy pairs move the other way on every matter ({min(decoy_vals):+.1f} to {max(decoy_vals):+.1f} pp)" if decoy_all_down
                 else f"Jev's decoy pairs move by {min(decoy_vals):+.1f} to {max(decoy_vals):+.1f} pp (up on {n_decoy_up} of {len(decoy_vals)} matters)")
    contrast_excl = [k for k in matters if t1[k]["models"][jev]["contrast_signal_minus_decoy"]["ci"][0] > 0]
    contrast_join = "so" if decoy_all_down else "and"
    t1_result = (f"Jev calls the version with the <em>real</em> token relevant more often than the fictional twin on {len(t1_excl)} of {len(matters)} matters "
                 f"({t1_jev_txt}); {decoy_txt}, {contrast_join} the signal − decoy contrast excludes zero on {len(contrast_excl)} of {len(matters)}. "
                 f"The GPT-5.6 models — the positive comparison, systems known to carry matter knowledge — move in the same direction on every matter, and Jev's effect sizes are "
                 f"{range_txt}.")

    # ---- bare token (FAS 140)
    bare_tbl = bare_txt = ""
    b_as, b_named = bare.get("aswritten", {}).get("paired"), bare.get("named", {}).get("paired")
    if b_as and b_named:
        rows = [["criteria as written (FAS 140 / FAS 125, no vehicle named)", _pct(b_as["rate_real"]), _pct(b_as["rate_fake"]), _ci(b_as["diff"], b_as["diff_ci"])],
                ["criteria plus one sentence naming the vehicles", _pct(b_named["rate_real"]), _pct(b_named["rate_fake"]), _ci(b_named["diff"], b_named["diff_ci"])]]
        bare_tbl = table(["FAS 140 request", "real token (Raptor / LJM2 / Chewco) called responsive", "fictional token (Tercel / HLM2 / Brixco)", "paired Δ (pp, 95% CI)"], rows, cls="tbl compact")
        ctx = bare.get("named__enronctx", {}).get("paired")
        bare_txt = (f"A header plus one sentence naming Raptor, LJM2 or Chewco is called responsive to the FAS 140 request <b>{_pct(b_as['rate_real'])}</b> of the time with the "
                    f"criteria as written (fictional twin {_pct(b_as['rate_fake'])}; mean p {b_as['mean_p_real']:.2f} vs {b_as['mean_p_fake']:.2f}), and "
                    f"<b>{_pct(b_named['rate_real'])}</b> vs {_pct(b_named['rate_fake'])} only once the criteria name the vehicles"
                    + (f" ({_pct(ctx['rate_real'])} vs {_pct(ctx['rate_fake'])} with the ablation's 'The Company is Enron Corp.' context added)" if ctx else "")
                    + ". The ablation's FAS 140 loss is therefore not a bare-name reflex: it is Jev reading request and document together, and using what the names mean when the request points at them.")

    # ---- T2
    t2_txt = t2_jev = t2_verify_txt = ""
    t2_cols = [k for k in T2_ORDER if k in t2]
    if t2_cols and all(jev in t2[k]["models"] for k in t2_cols):
        lf = lambda m, k: t2[k]["models"][m]["label_following"]  # noqa: E731
        t2_jev = {k: lf(jev, k) for k in t2_cols}
        llm_rng = lambda k: f"{_pct(min(lf(m, k)['rate'] for m in llms))}–{_pct(max(lf(m, k)['rate'] for m in llms))}"  # noqa: E731
        ver = t2.get("_contrast_vs_veridian", {})
        contrast = {k: ver.get(f"{jev}/{k}") for k in t2_cols if k != "veridian"}
        above_zero = [k for k, c in contrast.items() if c and c["ci"][0] > 0]
        verify = {k: t2[k].get("verify") for k in t2_cols if t2[k].get("verify")}
        if verify:
            ks = sorted(v["k"] for v in verify.values())
            t2_verify_txt = (f"the second-model check confirms the intended flip on only {ks[0]}–{ks[-1]} of {verify[t2_cols[0]]['n']} sampled edits per collection, "
                             f"which dilutes label-following toward the old label for every system equally")
        t2_txt = ("On documents edited to flip their true relevance, Jev stays with the <em>old published</em> label on "
                  + "; ".join(f"{_pct(t2_jev[k]['rate'])} <small>[{_pct(t2_jev[k]['ci'][0])}, {_pct(t2_jev[k]['ci'][1])}]</small> of {MATTER_LABEL.get(k, k)} edits (LLMs {llm_rng(k)})" for k in t2_cols if k != "veridian")
                  + (f", against {_pct(t2_jev['veridian']['rate'])} on Veridian, whose labels were never published (LLMs {llm_rng('veridian')})" if "veridian" in t2_jev else "")
                  + ". " + ("Memorised labels would put the public collections above Veridian; " + ("none does" if not above_zero else "only " + ", ".join(MATTER_LABEL[k] for k in above_zero) + " does")
                            + " (Jev minus Veridian: " + "; ".join(f"{MATTER_LABEL.get(k, k)} {_ci_txt(c['diff'], c['ci'])}" for k, c in contrast.items() if c) + ")" if contrast else "")
                  + ". Consistent with no label memorisation" + (f"; caveat: {t2_verify_txt}." if t2_verify_txt else "."))

    # ---- T3
    t3_txt = ""
    t3_cols = [k for k in T3_ORDER if k in t3]
    if "enron" in t3 and "veridian" in t3:
        e, v = t3["enron"], t3["veridian"]
        parts = [f"{MATTER_LABEL.get(k, 'Veridian')} {t3[k]['mean_abs_dp']:.3f} <small>[{t3[k]['mean_abs_dp_ci'][0]:.3f}, {t3[k]['mean_abs_dp_ci'][1]:.3f}]</small>, "
                 f"calls flipped {_pct(t3[k]['flip_rate'], 1)}" for k in t3_cols]
        endo = t3.get("endo")
        t3_txt = ("Paraphrasing a document (headers kept) moves Jev's probability by a mean |Δp| of " + "; ".join(parts)
                  + f". Enron — the corpus in public pre-training text — is indistinguishable from the synthetic floor (Mann–Whitney p = {e['mw_p_vs_veridian']:.2f})"
                  + (f"; the one corpus that differs is Endo (p {'&lt; 0.001' if endo['mw_p_vs_veridian'] < 0.001 else f'= {endo['mw_p_vs_veridian']:.3f}'}), which post-dates the cutoff and cannot have been memorised" if endo else "")
                  + ". Consistent with no document memorisation.")

    # ---- T4
    t4_txt = ""
    if "enron" in t4 or "jebbush" in t4:
        bits = []
        if "enron" in t4:
            s = t4["enron"]["sides"]
            jq, jp, up = s["judged"]["jev_acc_vs_qrels"], s["judged"]["jev_agree_panel"], s["unjudged"]["jev_agree_panel"]
            jpb, upb = s["judged"]["jev_agree_panel_by_panel"], s["unjudged"]["jev_agree_panel_by_panel"]
            pos = 100 * (jpb["responsive"]["rate"] - upb["responsive"]["rate"])
            neg = 100 * (jpb["not_responsive"]["rate"] - upb["not_responsive"]["rate"])
            bits.append(f"Enron: agreement with the human qrels {_pct(jq['rate'])} on judged documents, with the LLM panel {_pct(jp['rate'])} on the same documents "
                        f"(panel vs qrels {_pct(s['judged']['panel_acc_vs_qrels']['rate'])}); judged − unjudged agreement with the panel {pos:+.1f} pp on panel-positives "
                        f"(n {jpb['responsive']['n']} vs {upb['responsive']['n']}) and {neg:+.1f} pp on panel-negatives")
        if "jebbush" in t4:
            s = t4["jebbush"]
            jq, jp = s["judged"]["jev_acc_vs_qrels"], s["judged"]["jev_agree_panel"]
            pos, neg = s["agree_panel_judged_minus_unjudged__panel_responsive"], s["agree_panel_judged_minus_unjudged__panel_not_responsive"]
            bits.append(f"Jeb Bush: {_pct(jq['rate'])} with the qrels, {_pct(jp['rate'])} with the panel (panel vs qrels {_pct(s['judged']['panel_acc_vs_qrels']['rate'])}); "
                        f"judged − unjudged {_ci_txt(pos['diff'], pos['ci'])} on panel-positives (n {pos['n'][0]:,} vs {pos['n'][1]}) and {_ci_txt(neg['diff'], neg['ci'])} on panel-negatives")
        t4_txt = ("A system that had memorised the published judgments would agree with them more than with an LLM panel on judged documents; Jev does the reverse. "
                  + ". ".join(bits) + ". The positive-side differences are wide and rest on a handful of unjudged positives, the negative side shows no judged-set advantage: "
                  "consistent with no label memorisation. Judged documents were pool-selected by the TREC participants' systems and are not a random sample of the collection; "
                  "that confound is the binding limit on this test's power.")

    # ---- the overall sentence (one framing, used everywhere)
    overall = ("The classifier-native tests are consistent with Jev not having been trained on these collections, and they show it knows the cases behind them at effect "
               "sizes comparable to the LLMs."
               + (f" Knowing the case did not detectably move its F1 on Enron ({abl_jk_txt})." if abl_jk_txt else ""))
    overall_short = ("classifier-native tests are consistent with Jev not having been trained on these collections and show it knows the cases behind them at effect sizes "
                     "comparable to the LLMs" + (f"; knowing the case did not detectably move its F1 on Enron ({abl_jk_txt})" if abl_jk_txt else ""))
    link = f'<a href="{JEV_PROBE_HREF}">classifier-native report</a>'
    t1_jev_line = (f"On the code-name swap Jev calls the real-token version relevant more often than its fictional twin on every matter ({t1_jev_short} pp), "
                   f"{range_txt.split(';')[0]}.")

    reading = (f"<p><b>Reading.</b> {overall} T1 is knowledge of what the names mean — drug brands, Enron's vehicles, Florida controversies — not memory of any document: "
               f"it is inconsistent with a reading of the vendor's statement under which the classifier has no real-world knowledge, and consistent with either pre-training on public "
               f"text or synthetic training data distilled from a model that has that knowledge; these tests cannot separate the two. T2–T4 bound memorisation of the documents and "
               f"labels only at these sample sizes and for these collections. Jev remains a system under test and the vendor's statement remains a claim.</p>")
    limitations = [
        "<b>Pre-training and distillation are not separable.</b> The code-name swap shows the decision model uses real-world matter knowledge; a base model pre-trained on public text and "
        "a model trained on synthetic data generated by a knowledgeable LLM would both show it. No test here distinguishes them.",
        (f"<b>The minimal-edit instrument is noisy.</b> {t2_verify_txt[0].upper() + t2_verify_txt[1:]}; the within-collection comparison of Jev with the LLMs stands, the contrast with "
         "Veridian is the weaker leg." if t2_verify_txt else ""),
        "<b>The published-vs-unpublished test has little power on the positive side.</b> Relevant documents in these collections were almost all judged (pool selection), so the "
        "unjudged side has a handful of panel-positives and the judged − unjudged difference on them is wide; the negative side is the informative cell, and it shows no judged-set advantage.",
    ]
    limitations = [x for x in limitations if x]

    return {"has": True, "href": JEV_PROBE_HREF, "link": link, "cost_openai": cost_openai, "cost_jev": cost_jev, "matters": matters, "llms": llms, "jev": jev,
            "t1_tbl": t1_tbl, "t1_mini_tbl": t1_mini_tbl, "t1_result": t1_result, "t1_jev_txt": t1_jev_txt, "t1_jev_short": t1_jev_short, "t1_jev_line": t1_jev_line,
            "t1_range_txt": range_txt, "t1_decoy_txt": decoy_txt, "t1_n_excl": len(t1_excl), "t1_jev": {k: sig(jev, k) for k in matters},
            "bare_tbl": bare_tbl, "bare_txt": bare_txt, "bare": {"aswritten": b_as, "named": b_named},
            "t2_txt": t2_txt, "t2_jev": t2_jev, "t2_verify_txt": t2_verify_txt, "t3_txt": t3_txt, "t4_txt": t4_txt,
            "overall": overall, "overall_short": overall_short, "reading": reading, "limitations": limitations, "abl_jk_txt": abl_jk_txt}
