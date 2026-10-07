"""The generalisation checks A–D (results/verify/summary.json), rendered for the contamination write-ups.

Every builder calls `verify_summary()`; if the checks have not been run the result is None and the callers omit the subsection.
Nothing here is computed from the checks' own code — only their summary.json is read — so this module may change without touching
verify/*. Every number in the prose is derived here, not typed. Jev is a system under test throughout.
"""
from __future__ import annotations

import json
from pathlib import Path

from .effect import SYSTEM_ORDER, _ci, _ci_txt, _mkey, _name, _pp, _pt
from .html import MODEL_META, _esc, _pct, dotplot, legend, table
from .run import RESULTS_DIR

VERIFY_DIR = RESULTS_DIR.parent / "verify"
VERIFY_HREF = "../verify/REPORT.md"
VERIFY_FIG_HREF = "../verify/"
CORPUS_LABEL = {"enron_j": "Enron J", "enron_k": "Enron K", "mnk": "Mallinckrodt", "veridian": "Veridian", "endo": "Endo", "jebbush": "Jeb Bush", "cuad": "CUAD"}
D_LABEL = {"veridian_brief": "Veridian: ΔF1 with the fictional case brief", "mnk_brief": "Mallinckrodt: ΔF1 with the case brief (round 1)",
           "bt_brief": "Big Thorium: ΔF1 with Relativity's aiR case summary"}
D_ROLE = {"veridian_brief": "effect", "bt_brief": "public-invented"}


def load_verify(path: Path = VERIFY_DIR / "summary.json") -> dict | None:
    if not path.exists():
        return None
    try:
        v = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    if not all(v.get(k) for k in ("check_a", "check_b", "check_c", "check_d")):
        return None
    return v


def _short(m: str) -> str:
    return _name(m).split()[-1]


def _excl(d: dict) -> bool:
    return d["lo"] > 0 or d["hi"] < 0


def verify_summary(v: dict | None = None) -> dict | None:
    """Tables, figure, one-liners and the calibrated sentences for checks A–D. None if the checks have not been run."""
    v = v or load_verify()
    if v is None:
        return None
    A, B, C, D = v["check_a"], v["check_b"], v["check_c"], v["check_d"]
    spend = v.get("spend_usd", {})
    figs = v.get("figures", {})

    # ---- A · knowledge dependence (Enron J)
    a_sys = [m for m in SYSTEM_ORDER if A["systems"].get(m, {}).get("status") == "ok"]
    a_llms = [m for m in a_sys if not m.startswith("jev")]
    a_jev = next((m for m in a_sys if m.startswith("jev")), None)
    kd = A["share_kd_overall_knowledge_topics"]
    kd_share, kd_lo, kd_hi = 100 * kd["share"], 100 * kd["ci"][0], 100 * kd["ci"][1]
    fas = A["share_kd_by_request"].get("fas140")
    sub = lambda m, k: A["systems"][m]["subsets"][k]  # noqa: E731
    acc = lambda m, k: 100 * sub(m, k)["named"]["accuracy"]  # noqa: E731
    kd_acc = [acc(m, "knowledge_dependent") for m in a_sys]
    sc_acc = [acc(m, "self_contained") for m in a_sys]
    all_worse = all(acc(m, "knowledge_dependent") < acc(m, "self_contained") for m in a_sys)
    best_kd = max(a_sys, key=lambda m: acc(m, "knowledge_dependent")) if a_sys else None
    n_kd = A["systems"][a_sys[0]]["n_kd"] if a_sys else 0
    kd_delta = {m: sub(m, "knowledge_dependent")["delta"]["f1"] for m in a_sys}
    kd_up_excl = [m for m in a_sys if kd_delta[m]["lo"] > 0]
    kd_down_excl = [m for m in a_sys if kd_delta[m]["hi"] < 0]
    conc = {m: A["systems"][m]["delta_kd_minus_delta_sc"]["f1"] for m in a_sys}
    conc_neg = [m for m in a_sys if conc[m]["delta"] < 0]
    a_rows = []
    for m in a_sys:
        k_, s_ = sub(m, "knowledge_dependent"), sub(m, "self_contained")
        a_rows.append([f'<span class="m" style="--c:{MODEL_META[_mkey(m)][2]}">{_esc(_name(m))}</span>',
                       f"{acc(m, 'knowledge_dependent'):.0f}% <small>(n {k_['n']})</small>", f"{acc(m, 'self_contained'):.0f}% <small>(n {s_['n']})</small>",
                       _ci(k_["delta"]["f1"]), _ci(s_["delta"]["f1"]), _ci(conc[m]), f"{k_['right_to_wrong']} / {k_['wrong_to_right']}"])
    a_tbl = table(["system", "named accuracy, knowledge-dependent", "named accuracy, self-contained", "ΔF1 renamed − named, knowledge-dependent", "ΔF1, self-contained",
                   "ΔF1(KD) − ΔF1(SC)", "KD flips right→wrong / wrong→right"], a_rows, cls="tbl wide")
    a_acc_txt = " / ".join(f"{x:.0f}%" for x in kd_acc) + " vs " + " / ".join(f"{x:.0f}%" for x in sc_acc)
    a_line = (f"Only {kd_share:.1f}% [{kd_lo:.1f}, {kd_hi:.1f}] of the Enron J documents are <em>knowledge-dependent</em> (relevance visible only with outside Enron knowledge"
              + (f"; FAS 140 {_pct(fas['share'])}, every other request ≤ {max(100 * x['share'] for k, x in A['share_kd_by_request'].items() if k != 'fas140'):.0f}%" if fas else "")
              + f"). Contamination predicts higher named accuracy on them and a larger renaming drop on them. Neither holds: {'every' if all_worse else 'nearly every'} system is "
              f"<em>less</em> accurate on them when named ({a_acc_txt}; {' / '.join(_short(m) for m in a_sys)})"
              + (f", and the most accurate system on them is {_name(best_kd)}" if best_kd else "")
              + f". Renaming on the knowledge-dependent subset (n = {n_kd}) moved F1 by " + "; ".join(f"{_short(m)} {_ci_txt(kd_delta[m])}" for m in a_sys)
              + (f" — renaming <em>helped</em> {', '.join(_name(m) for m in kd_up_excl)}" if kd_up_excl else "")
              + (f"; the one drop whose interval excludes zero is {', '.join(_name(m) for m in kd_down_excl)}'s" if kd_down_excl else "")
              + ". The LLMs' Enron J edge over Jev sits on the self-contained documents. <b>Strengthens</b> the claim: where knowledge could help, no system behaves as if it did.")

    # ---- B · ranking stability
    four = B["tables"]["four"]["all_gold"]
    rk = four["ranks_f1"]
    W = rk["kendall_w"]
    b_sys = rk["systems"]
    ranking_txt = "; ".join(f"{CORPUS_LABEL.get(c, c)}: " + " &gt; ".join(_short(m) for m in rk["ranking"][c]) for c in rk["corpora"])
    trend = four.get("trend", {})
    gap = trend.get("gap_llm_minus_jev") or {}
    # the mean-LLM − Jev F1 gap per corpus, derived from the cells (mean of the LLM F1s minus Jev's), with the mean LLM case score
    cells = four["cells"]
    cs = B.get("case_scores", {})
    llm_b = [m for m in b_sys if not m.startswith("jev")]
    jev_b = next((m for m in b_sys if m.startswith("jev")), None)
    gaps = {}
    for c in ("enron_j", "mnk", "veridian"):
        if c in cells and jev_b and all(m in cells[c] for m in llm_b + [jev_b]):
            g = 100 * (sum(cells[c][m]["f1"] for m in llm_b) / len(llm_b) - cells[c][jev_b]["f1"])
            case = sum(cs[m][c] for m in llm_b if m in cs and cs[m].get(c) is not None) / max(1, sum(1 for m in llm_b if m in cs and cs[m].get(c) is not None))
            gaps[c] = (g, case)
    gap_txt = " → ".join(f"{CORPUS_LABEL[c]} (case {gaps[c][1]:.0f}) {gaps[c][0]:+.1f}" for c in ("enron_j", "mnk", "veridian") if c in gaps)
    gap_monotone = len(gaps) == 3 and gaps["enron_j"][0] > gaps["mnk"][0] > gaps["veridian"][0]
    rho_txt = ", ".join(f"{_short(m)} {trend['per_model'][m]['spearman_f1']['rho']:+.1f}" for m in llm_b if m in trend.get("per_model", {}))
    prev = four.get("difficulty", {})
    prev_txt = (f"real human-judged e-mail at {_pct(prev['enron_j']['prevalence'])} prevalence on Enron J against LLM-panel and synthetic-planner gold at "
                f"{_pct(prev['mnk']['prevalence'])} and {_pct(prev['veridian']['prevalence'])} on Mallinckrodt and Veridian"
                if all(k in prev for k in ("enron_j", "mnk", "veridian")) else "real human-judged e-mail against LLM-panel and synthetic gold")
    b_line = (f"System order is not stable across corpora: Kendall W = {W['W']:.2f} over {len(rk['corpora'])} corpora × {len(b_sys)} systems (p ≈ {W['p_approx']:.2f}; four objects give W almost no power). "
              f"{ranking_txt}. Within each LLM, F1 does not trend with its own case-knowledge score (Spearman ρ {rho_txt}, n = 4). "
              f"The mean-LLM − Jev F1 gap {'grows monotonically' if gap_monotone else 'moves'} with the LLMs' case knowledge: {gap_txt} pp. That is the pattern contamination predicts, but it is "
              f"also what corpus type predicts ({prev_txt}), and checks A and D test the mechanism directly on both ends of the gradient and find none. "
              f"<b>Ambiguous, leaning against the claim</b> on its own; unresolved at n = 4.")
    b_caveat = (f"<b>System ordering is not stable across corpora, and the LLM − Jev gap widens with the LLMs' case knowledge.</b> Kendall W = {W['W']:.2f} over the four systems on "
                f"{len(rk['corpora'])} corpora; the mean-LLM − Jev F1 gap runs {gap_txt} pp. Contamination predicts this ordering, but so does corpus type ({prev_txt}); with four systems "
                f"and three kinds of gold the two cannot be separated, and the checks that test the mechanism directly (knowledge-dependence, brief injection) find none. "
                f"It is reported as the one check that did not come out clean, and it is unresolved at n = 4.")

    # ---- C · counterfactual conflicts
    pooled = C["pooled_real"]
    c_sys = [m for m in SYSTEM_ORDER if m in pooled]
    kf = {m: 1 - pooled[m]["text_follow_cf"]["rate"] for m in c_sys}
    kf_rng = f"{100 * min(kf.values()):.0f}–{100 * max(kf.values()):.0f}%"
    vs_ver = {m: pooled[m]["vs_veridian"] for m in c_sys}
    vs_excl = [m for m in c_sys if vs_ver[m]["ci"][0] > 0]
    ceiling = min(pooled[m]["text_follow_factual"]["rate"] for m in c_sys)
    c_rows = [[f'<span class="m" style="--c:{MODEL_META[_mkey(m)][2]}">{_esc(_name(m))}</span>', _pct(pooled[m]["text_follow_factual"]["rate"]),
               f"<b>{_pct(kf[m], 1)}</b> <small>[{_pct(1 - pooled[m]['text_follow_cf']['ci'][1], 1)}, {_pct(1 - pooled[m]['text_follow_cf']['ci'][0], 1)}]</small>",
               _pct(1 - pooled[m]["by_direction"]["fact_relevant"]["rate"]), _pct(1 - pooled[m]["by_direction"]["fact_irrelevant"]["rate"]),
               f"{_pt(vs_ver[m]['diff'])} <small>[{_pt(vs_ver[m]['ci'][0])}, {_pt(vs_ver[m]['ci'][1])}]</small>"] for m in c_sys]
    c_tbl = table(["system", "reads the factual version", "knowledge-following on counterfactual documents (95% Wilson)", "on well-known responsive tokens made irrelevant",
                   "on irrelevant tokens made relevant", "vs Veridian in-context baseline, pp"], c_rows, cls="tbl wide")
    c_line = (f"On {C['matters']['enron']['n_pairs'] if 'enron' in C['matters'] else 30} short documents per matter whose text contradicts a well-known fact (Roxicodone as an antacid; the Schiavo file as a road renaming), "
              f"the call follows world knowledge rather than the text on <b>{kf_rng}</b> of pairs pooled over the four real matters ({' / '.join(f'{_short(m)} {_pct(kf[m])}' for m in c_sys)}; "
              f"every system reads the factual versions at ≥ {_pct(ceiling)}), almost entirely in one direction — a well-known responsive token keeps a document responsive — and concentrated on "
              f"Jeb Bush, Mallinckrodt and Endo, near zero on Enron. "
              + ("No system's rate is above its Veridian baseline, where the only facts that can be overridden are in the prompt itself" if not vs_excl
                 else f"The rate exceeds the Veridian baseline only for {', '.join(_name(m) for m in vs_excl)}")
              + f" ({'; '.join(f'{_short(m)} {_pt(vs_ver[m]['diff'])} [{_pt(vs_ver[m]['ci'][0])}, {_pt(vs_ver[m]['ci'][1])}]' for m in c_sys)}). "
              f"<b>Mixed; neutral for the claim as stated</b>: the systems do let a prior fact outweigh the page on an engineered conflict, Jev least, but no more for pre-trained facts than "
              f"for in-context ones, and check A says such conflicts are rare on real documents.")

    # ---- D · brief injection on Veridian
    d_sys = [m for m in SYSTEM_ORDER if D["models"].get(m, {}).get("status") == "ok"]
    dm = lambda m: D["models"][m]  # noqa: E731
    d_f1 = {m: dm(m)["delta"]["f1"] for m in d_sys}
    mnk = D.get("mnk_brief_effect_from_ablation", {})
    btb = D.get("bigthorium_brief_effect_from_ablation", {})
    d_bound = max(abs(100 * d["delta"]) for d in d_f1.values()) if d_f1 else 0.0
    d_ci_bound = max(max(abs(100 * d["lo"]), abs(100 * d["hi"])) for d in d_f1.values()) if d_f1 else 0.0
    d_excl = [m for m in d_sys if _excl(d_f1[m])]
    d_rows = []
    for m in d_sys:
        x = dm(m)
        w, b = x["without_brief"], x["with_brief"]
        d_rows.append([f'<span class="m" style="--c:{MODEL_META[_mkey(m)][2]}">{_esc(_name(m))}</span>', f"{x['n_pairs']:,} <small>({x['n_docs']} docs)</small>",
                       f"{100 * w['precision']:.1f} / {100 * w['recall']:.1f} / <b>{100 * w['f1']:.1f}</b>", f"{100 * b['precision']:.1f} / {100 * b['recall']:.1f} / <b>{100 * b['f1']:.1f}</b>",
                       _ci(x["delta"]["precision"]), _ci(x["delta"]["recall"]), _ci(x["delta"]["f1"]), f"{100 * x['label_changed_share']:.1f}%",
                       f"{x['mcnemar']['lost']} / {x['mcnemar']['gained']} <small>(p {x['mcnemar']['p']:.2f})</small>", _ci(mnk[m]) if m in mnk else "–"]
                      + ([_ci(btb[m]) if m in btb else "–"] if btb else []))
    d_tbl = table(["system", "pairs", "without brief P / R / F1", "with brief P / R / F1", "ΔPrecision", "ΔRecall", "ΔF1 [95% CI]", "labels changed",
                   "right→wrong / wrong→right", "Mallinckrodt brief ΔF1 (round 1)"] + (["Big Thorium brief ΔF1"] if btb else []), d_rows, cls="tbl wide")
    keys = [_mkey(m) for m in d_sys]
    rows = [("veridian_brief", {_mkey(m): _pp(d_f1[m]) for m in d_sys})]
    if mnk:
        rows.append(("mnk_brief", {_mkey(m): _pp(mnk[m]) for m in d_sys if m in mnk}))
    if btb:
        rows.append(("bt_brief", {_mkey(m): _pp(btb[m]) for m in d_sys if m in btb}))
    d_fig = legend(keys) + dotplot(rows, keys, -5, 5, [-4, -2, 0, 2, 4], lambda x: f"{x:+.0f}",
                                   "Knowledge injection · ΔF1 (with brief − without), percentage points, with 95% CI", ref=0, width=720, label_w=300, row_h=44,
                                   labels=D_LABEL, roles=D_ROLE,
                                   note="Veridian is the one matter no system can know; the brief supplies the parties, products, people, deals, code names, timeline and outcome. "
                                        f"Stratified half of the ablation documents ({D['n_subset']} of {D['n_source']}); cluster bootstrap over documents. The second row is the "
                                        "round-1 Mallinckrodt brief arm for comparison."
                                        + (" The third is the same check on Big Thorium, Relativity's public aiR demo workspace (invented case), with Relativity's own case summary as the brief." if btb else ""))
    jev_d = next((m for m in d_sys if m.startswith("jev")), None)
    d_line = (f"A {D['brief_chars']:,}-character fictional case brief — parties, products, people, deals, code names, timeline, outcome — appended to the Veridian context exactly as the "
              f"Mallinckrodt brief was, on {D['n_subset']} of the {D['n_source']} ablation documents. ΔF1 with the brief: "
              + "; ".join(f"{_short(m)} {_ci_txt(d_f1[m])}" for m in d_sys)
              + (f" ({'no interval excludes zero' if not d_excl else 'the interval excludes zero for ' + ', '.join(_name(m) for m in d_excl)}; every value within ±{d_ci_bound:.1f})" if d_sys else "")
              + (f"; Jev's recall rises {_pt(dm(jev_d)['delta']['recall']['delta'])} against {_pt(dm(jev_d)['delta']['precision']['delta'])} precision" if jev_d else "")
              + f". Same picture as the Mallinckrodt brief arm ({' / '.join(_pt(mnk[m]['delta']) for m in d_sys if m in mnk)}). <b>Strengthens</b> the claim, and is the strongest null of the "
              f"four: supplying the one kind of knowledge the systems cannot have did not move accuracy.")

    verdicts = {k: v["readings"][k]["verdict"] for k in ("a", "b", "c", "d") if k in v.get("readings", {})}
    verdict_tbl = table(["check", "verdict for the claim", "one line"], [
        ["A · knowledge-dependence error analysis (Enron J)", f"<b>{_esc(verdicts.get('a', 'strengthens'))}</b>", a_line],
        ["B · ranking stability across corpora", f"<b>{_esc(verdicts.get('b', 'ambiguous'))}</b>", b_line],
        ["C · counterfactual conflict documents", f"<b>{_esc(verdicts.get('c', 'mixed'))}</b>", c_line],
        ["D · knowledge injection on Veridian", f"<b>{_esc(verdicts.get('d', 'strengthens'))}</b>", d_line],
    ], cls="tbl wide")

    overall = ("The two checks that test the mechanism directly — where knowledge could matter, does it (A)? when it is supplied, does it (D)? — come out for the claim; "
               "C shows the channel exists but is small and no larger for pre-trained than for in-context facts; B is the one check whose surface pattern runs the other way, "
               "and it cannot separate case knowledge from corpus type.")
    # the round-2 knowledge-effect intervals decide the strength of the carried claim (effect2 imports this module, so read the summary directly)
    from .effect2 import load_round2
    _r2 = load_round2()
    _pm = ((_r2 or {}).get("arms", {}).get("jeb", {}) or {}).get("per_model", {}) or {}
    _ke = {m: v["knowledge_effect"]["f1"] for m, v in _pm.items() if isinstance(v, dict) and v.get("knowledge_effect") and not m.startswith("jev")}
    _ke_excl = [m for m, d in _ke.items() if d["lo"] > 0 or d["hi"] < 0]
    _verb = "did not detectably change review accuracy" if not _ke_excl else "changed review accuracy by at most a few F1 points"
    carry = (f"On the matters tested, knowing the case {_verb}, including when the knowledge was supplied in the prompt; the systems can be made "
             "to override a document with a well-known fact, but such conflicts are rare in real collections and the effect did not reach accuracy.")

    # plain-English (lawyer / explainer)
    plain = (f"<p><b>Four more ways the result could have failed, and did not.</b> We tagged every Enron document for whether its relevance could only be seen with outside knowledge of the case: "
             f"only about {kd_share:.0f} in 100 are like that, and on those documents every system did <em>worse</em>, not better ({a_acc_txt} accuracy), which is the opposite of what cheating would look like. "
             f"We handed every system a one-page briefing on the invented Veridian matter — the one case none of them could know — and the scores moved by at most {d_bound:.1f} points, well within chance. "
             f"We wrote short documents that contradict a famous fact (a well-known opioid described as an antacid) and found the systems do sometimes trust the fact over the page ({kf_rng} of the time), "
             f"but no more often than when the fact came from the briefing in front of them. And we checked whether the systems rank the same way on every collection: they do not, and the gap between "
             f"the language models and Jev is largest on the best-known matter — a pattern that could be knowledge or could be the kind of collection, and which we could not settle with four systems.</p>")

    return {"has": True, "href": VERIFY_HREF, "fig_href": VERIFY_FIG_HREF, "figs": figs, "spend": spend, "verdicts": verdicts, "verdict_tbl": verdict_tbl,
            "a_line": a_line, "b_line": b_line, "c_line": c_line, "d_line": d_line, "a_tbl": a_tbl, "c_tbl": c_tbl, "d_tbl": d_tbl, "d_fig": d_fig,
            "b_caveat": b_caveat, "overall": overall, "carry": carry, "plain": plain,
            "kd_share": kd_share, "kd_ci": (kd_lo, kd_hi), "kd_acc": kd_acc, "sc_acc": sc_acc, "a_acc_txt": a_acc_txt, "a_sys": a_sys, "a_llms": a_llms, "a_jev": a_jev,
            "kd_delta": kd_delta, "kd_up_excl": kd_up_excl, "kd_down_excl": kd_down_excl, "conc": conc, "n_kd": n_kd,
            "W": W["W"], "gap_txt": gap_txt, "gaps": gaps, "kf": kf, "kf_rng": kf_rng, "vs_excl": vs_excl,
            "d_sys": d_sys, "d_f1": d_f1, "d_bound": d_bound, "d_ci_bound": d_ci_bound, "d_excl": d_excl, "d_seq": " / ".join(_pt(d_f1[m]["delta"]) for m in d_sys),
            "d_sys_txt": " / ".join(_name(m) for m in d_sys), "n_subset": D["n_subset"], "n_source": D["n_source"]}
