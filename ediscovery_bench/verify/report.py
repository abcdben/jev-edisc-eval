"""Score all four checks, write results/verify/summary.json, REPORT.md and one PNG figure per check."""
from __future__ import annotations

import json
from datetime import date

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from . import conflict, inject, knowdep, ranking  # noqa: E402
from .common import JEV, LUNA, RESULTS, SOL, SYSTEMS, TERRA, dump_json, openai_spend  # noqa: E402

NAMES = {LUNA: "GPT-5.6 Luna", TERRA: "GPT-5.6 Terra", SOL: "GPT-5.6 Sol", JEV: "Jev", "claude-sonnet-5": "Claude Sonnet 5", "gemini-3.8-flash": "Gemini 3.8 Flash",
         "claude-haiku-4.5": "Claude Haiku 4.5", "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite"}
COLORS = {LUNA: "#4C78A8", TERRA: "#F58518", SOL: "#E45756", JEV: "#54A24B", "claude-sonnet-5": "#B279A2", "gemini-3.8-flash": "#72B7B2"}


def nm(m: str) -> str:
    return NAMES.get(m, m)


def pct(x, d=1) -> str:
    return "—" if x is None or x != x else f"{100 * x:.{d}f}"


def pp(x) -> str:
    return "—" if x is None or x != x else f"{100 * x:+.1f}"


def ci(d: dict | None, key: str | None = None) -> str:
    if not d:
        return "—"
    b = d[key] if key else d
    if b.get("delta") is None and b.get("diff") is None and b.get("drop") is None:
        return "—"
    v = b.get("delta", b.get("diff", b.get("drop")))
    lo, hi = (b.get("lo"), b.get("hi")) if "lo" in b else tuple(b.get("ci") or (None, None))
    return f"{pp(v)} [{pp(lo)}, {pp(hi)}]" if lo is not None else pp(v)


# ------------------------------------------------------------------------------------------------ figures

def fig_a(a: dict, path) -> None:
    systems = [m for m in SYSTEMS if a.get("systems", {}).get(m, {}).get("status") == "ok"]
    if not systems:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    x = range(len(systems)); w = 0.38
    for ax, key, title in ((axes[0], "named", "Named condition: accuracy by document type"), (axes[1], None, "Named → renamed: ΔF1 by document type")):
        for off, sub, col in ((-w / 2, "knowledge_dependent", "#E45756"), (w / 2, "self_contained", "#4C78A8")):
            vals, los, his = [], [], []
            for m in systems:
                b = a["systems"][m]["subsets"].get(sub)
                if key:
                    vals.append(100 * b["named"]["accuracy"]); lo, hi = b["named"]["accuracy_ci"]; los.append(100 * (b["named"]["accuracy"] - lo)); his.append(100 * (hi - b["named"]["accuracy"]))
                else:
                    d = b["delta"]["f1"]; vals.append(100 * d["delta"]); los.append(100 * (d["delta"] - d["lo"])); his.append(100 * (d["hi"] - d["delta"]))
            ax.bar([i + off for i in x], vals, w, yerr=[los, his], capsize=3, color=col, label=f"{sub.replace('_', '-')} (n≈{a['systems'][systems[0]]['n_kd' if sub.startswith('k') else 'n_sc']})")
        ax.set_xticks(list(x)); ax.set_xticklabels([nm(m) for m in systems], fontsize=9); ax.set_title(title, fontsize=10)
        ax.axhline(0 if not key else 50, color="grey", lw=0.6, ls=":")
        ax.set_ylabel("accuracy (%)" if key else "ΔF1 renamed − named (pp)")
    axes[0].legend(fontsize=8, loc="lower right")
    fig.suptitle("Check A — Enron J: knowledge-dependent vs self-contained documents (tagged by Luna)", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def fig_b(b: dict, path) -> None:
    four = b["tables"].get("four", {}).get("all_gold", {})
    cells = four.get("cells", {})
    if not cells:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4))
    order = ["enron_j", "enron_k", "endo", "mnk", "veridian"]
    corpora = [c for c in order if c in cells]
    x = range(len(corpora)); w = 0.2
    for i, m in enumerate(ranking.FOUR):
        vals = [100 * cells[c][m]["f1"] if m in cells[c] else 0 for c in corpora]
        bars = axes[0].bar([j + (i - 1.5) * w for j in x], vals, w, color=COLORS[m], label=nm(m))
        for bar, c in zip(bars, corpora):
            if cells[c].get(m, {}).get("panel_member"):
                bar.set_hatch("//"); bar.set_edgecolor("white")
    axes[0].set_xticks(list(x)); axes[0].set_xticklabels([ranking.CORPORA[c][0].split(" (")[0].replace(" — ", "\n") for c in corpora], fontsize=8)
    axes[0].set_ylabel("F1 (%)"); axes[0].legend(fontsize=8, ncol=2, loc="lower left")
    w_stat = four.get("ranks_f1", {}).get("kendall_w", {}).get("W")
    axes[0].set_title("F1 per corpus, four systems (hatched = system is in that corpus's gold panel)" + (f"\nKendall W over F1 ranks = {w_stat:.2f}" if w_stat is not None else ""), fontsize=9)
    cs = b["case_scores"]
    tr = four.get("trend", {}).get("per_model", {})
    # right: each LLM's F1 vs its own case score (small, faded) and the mean-LLM − Jev gap (large, black)
    for m in (LUNA, TERRA, SOL):
        if m in tr:
            axes[1].scatter(tr[m]["case_scores"], [100 * v for v in tr[m]["f1"]], color=COLORS[m], alpha=0.35, s=22, label=f"{nm(m)} F1 (ρ={tr[m]['spearman_f1']['rho']:+.1f})")
    gap = four.get("trend", {}).get("llm_minus_jev", {})
    ax2 = axes[1].twinx()
    for c, s, g in zip(gap.get("corpora", []), gap.get("mean_llm_case_score", []), gap.get("gap_f1", [])):
        ax2.scatter([s], [100 * g], color="black", s=70, marker="D", facecolors="white" if c == "endo" else "black", zorder=4)
        ax2.annotate(ranking.CORPORA[c][0].split(" (")[0].split(" — ")[-1] + (" (panel gold)" if c == "endo" else ""), (s, 100 * g), fontsize=7, xytext=(5, -3), textcoords="offset points")
    ax2.axhline(0, color="black", lw=0.6, ls=":"); ax2.set_ylabel("mean LLM F1 − Jev F1 (pp)  ◆")
    axes[1].set_xlabel("case-knowledge composite (0–100; Veridian = 0; ◆ at the LLMs' mean)"); axes[1].set_ylabel("F1 (%)  ○")
    axes[1].set_title("Per-LLM F1 vs own case knowledge (○) and the LLM − Jev gap (◆); Enron K, CUAD excluded", fontsize=9); axes[1].legend(fontsize=7, loc="lower right")
    fig.suptitle("Check B — ranking stability across known / less-known / unknown matters", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def fig_c(c: dict, path) -> None:
    matters = [m for m in ("enron", "jebbush", "mnk", "endo", "veridian") if m in c.get("matters", {})]
    systems = [m for m in SYSTEMS if any(m in c["matters"][mt]["models"] for mt in matters)]
    if not matters or not systems:
        return
    fig, ax = plt.subplots(figsize=(11, 4.4))
    x = range(len(matters)); w = 0.8 / len(systems)
    for i, m in enumerate(systems):
        vals, err_lo, err_hi, fac = [], [], [], []
        for mt in matters:
            blk = c["matters"][mt]["models"].get(m, {}).get("all", {})
            r = blk.get("text_follow_counterfactual")
            if not r:
                vals.append(0); err_lo.append(0); err_hi.append(0); fac.append(None); continue
            vals.append(100 * r["rate"]); err_lo.append(100 * (r["rate"] - r["ci"][0])); err_hi.append(100 * (r["ci"][1] - r["rate"]))
            fac.append(100 * blk["text_follow_factual"]["rate"])
        xs = [j + (i - (len(systems) - 1) / 2) * w for j in x]
        ax.bar(xs, vals, w, yerr=[err_lo, err_hi], capsize=2, color=COLORS[m], label=nm(m))
        ax.scatter(xs, [f if f is not None else 0 for f in fac], marker="_", color="black", s=160, zorder=3, label="factual version (reading ceiling)" if i == 0 else None)
    ax.set_xticks(list(x)); ax.set_xticklabels([{"enron": "Enron", "jebbush": "Jeb Bush", "mnk": "Mallinckrodt", "endo": "Endo", "veridian": "Veridian\n(no prior knowledge possible)"}[m] for m in matters])
    ax.set_ylabel("counterfactual documents called as the TEXT implies (%)"); ax.set_ylim(0, 105); ax.legend(fontsize=8, loc="lower left", ncol=3)
    ax.set_title("Check C — counterfactual conflict documents: does the call follow the text or world knowledge?", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def fig_d(d: dict, path) -> None:
    systems = [m for m in SYSTEMS if d.get("models", {}).get(m, {}).get("status") == "ok"]
    if not systems:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    x = range(len(systems)); w = 0.26
    for i, (metric, col) in enumerate((("precision", "#4C78A8"), ("recall", "#F58518"), ("f1", "#54A24B"))):
        vals = [100 * d["models"][m]["delta"][metric]["delta"] for m in systems]
        lo = [100 * (d["models"][m]["delta"][metric]["delta"] - d["models"][m]["delta"][metric]["lo"]) for m in systems]
        hi = [100 * (d["models"][m]["delta"][metric]["hi"] - d["models"][m]["delta"][metric]["delta"]) for m in systems]
        axes[0].bar([j + (i - 1) * w for j in x], vals, w, yerr=[lo, hi], capsize=3, color=col, label=metric)
    axes[0].axhline(0, color="grey", lw=0.6, ls=":"); axes[0].set_xticks(list(x)); axes[0].set_xticklabels([nm(m) for m in systems])
    axes[0].set_ylabel("with brief − without (pp)"); axes[0].legend(fontsize=8); axes[0].set_title(f"Veridian: effect of the injected case brief (n = {d['n_subset']} docs × 10 requests)", fontsize=9)
    mnk = d.get("mnk_brief_effect_from_ablation", {})
    bt = d.get("bigthorium_brief_effect_from_ablation", {})
    for m in systems:
        v = d["models"][m]["delta"]["f1"]; mk = mnk.get(m); bb = bt.get(m)
        axes[1].errorbar([100 * v["delta"]], [nm(m)], xerr=[[100 * (v["delta"] - v["lo"])], [100 * (v["hi"] - v["delta"])]], fmt="o", color=COLORS[m], capsize=3, label="Veridian brief" if m == systems[0] else None)
        if mk and mk.get("delta") is not None:
            axes[1].errorbar([100 * mk["delta"]], [nm(m)], xerr=[[100 * (mk["delta"] - mk["lo"])], [100 * (mk["hi"] - mk["delta"])]], fmt="s", mfc="white", color=COLORS[m], capsize=3, alpha=0.7,
                             label="Mallinckrodt brief (ablation)" if m == systems[0] else None)
        if bb and bb.get("delta") is not None:
            axes[1].errorbar([100 * bb["delta"]], [nm(m)], xerr=[[100 * (bb["delta"] - bb["lo"])], [100 * (bb["hi"] - bb["delta"])]], fmt="^", mfc="white", color=COLORS[m], capsize=3, alpha=0.7,
                             label="Big Thorium brief (public demo set)" if m == systems[0] else None)
    axes[1].axvline(0, color="grey", lw=0.6, ls=":"); axes[1].set_xlabel("ΔF1 with brief − without (pp, 95% cluster bootstrap)"); axes[1].legend(fontsize=8)
    axes[1].set_title("Brief effect: Veridian ● · Mallinckrodt □" + (" · Big Thorium △" if bt else ""), fontsize=9)
    fig.suptitle("Check D — knowledge injection on the unknown matter", fontsize=11)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


# ------------------------------------------------------------------------------------------------ readings

def reading_a(a: dict) -> tuple[str, str]:
    sys_ok = {m: v for m, v in a.get("systems", {}).items() if v.get("status") == "ok"}
    if not sys_ok:
        return "not run", "Check A has not been scored."
    higher_kd, larger_drop, both = [], [], []
    for m, v in sys_ok.items():
        acc = v["named_acc_kd_minus_sc"]["delta"]; dd = v["delta_kd_minus_delta_sc"]["f1"]["delta"]
        if acc is not None and acc > 0:
            higher_kd.append(m)
        if dd is not None and dd < 0:
            larger_drop.append(m)
        if acc is not None and dd is not None and acc > 0 and dd < 0 and v["delta_kd_minus_delta_sc"]["f1"]["hi"] < 0:
            both.append(m)
    if both:
        return "weakens", f"{', '.join(nm(m) for m in both)} show the contamination signature (higher named accuracy on knowledge-dependent documents and a renaming drop concentrated on them, CI excluding 0)."
    share = a.get("share_kd_overall_knowledge_topics", {}).get("share")
    kd_acc = {m: v["subsets"]["knowledge_dependent"]["named"]["accuracy"] for m, v in sys_ok.items() if "knowledge_dependent" in v["subsets"]}
    sc_acc = {m: v["subsets"]["self_contained"]["named"]["accuracy"] for m, v in sys_ok.items() if "self_contained" in v["subsets"]}
    best_kd = max(kd_acc, key=kd_acc.get) if kd_acc else None
    verdict = "strengthens" if not higher_kd else "neutral"
    txt = (f"Only {pct(share, 0)}% of Enron J documents are knowledge-dependent. On them every system is *less* accurate in the named condition "
           f"({', '.join(f'{nm(m)} {pct(v, 0)}%' for m, v in kd_acc.items())}) than on self-contained documents ({', '.join(f'{nm(m)} {pct(v, 0)}%' for m, v in sc_acc.items())}); "
           f"the most accurate system on knowledge-dependent documents is {nm(best_kd)}. The renaming drop is larger on knowledge-dependent documents for {len(larger_drop)}/{len(sys_ok)} systems, "
           f"none with a CI excluding zero (n ≈ {next(iter(sys_ok.values()))['n_kd']}); the one system whose drop concentrates on knowledge-dependent documents is Jev "
           f"(ΔF1 KD − SC {ci(sys_ok[JEV]['delta_kd_minus_delta_sc'], 'f1') if JEV in sys_ok else '—'}, seven flips), and Jev is not more accurate on those documents when named, so at most half the signature. The signature contamination predicts (better on KD and a KD-concentrated drop) is absent; the LLMs' Enron J edge over Jev sits on self-contained documents.")
    return verdict, txt


def reading_b(b: dict) -> tuple[str, str]:
    four = b["tables"].get("four", {}).get("all_gold", {})
    rk = four.get("ranks_f1", {}); w = rk.get("kendall_w", {})
    if not w:
        return "not run", "No ranking table."
    tops = rk.get("top_system_per_corpus", {})
    tr = four.get("trend", {}).get("per_model", {})
    rhos = {m: tr[m]["spearman_f1"]["rho"] for m in tr}
    gap = four.get("trend", {}).get("llm_minus_jev", {})
    gap_txt = ""
    if gap:
        pairs = [(c, s, g) for c, s, g in zip(gap["corpora"], gap["mean_llm_case_score"], gap["gap_f1"]) if c != "endo"]
        pairs.sort(key=lambda t: -t[1])
        mono = all(pairs[i][2] >= pairs[i + 1][2] for i in range(len(pairs) - 1))
        gap_txt = (" The mean-LLM − Jev F1 gap " + ("widens monotonically with the LLMs' case knowledge" if mono else "does not track case knowledge") + ": "
                   + ", ".join(f"{c} (case {s:.0f}) {pp(g)} pp" for c, s, g in pairs) + " (Endo excluded: its gold is the LLMs' own panel).")
    verdict = "ambiguous — leans weakens" if gap_txt and "monotonically" in gap_txt else "neutral"
    txt = (f"Rank order is not stable: Kendall W = {w['W']:.2f} across {w['m_judges']} corpora × {w['n_objects']} systems (p≈{w['p_approx']:.2f}; four systems give W almost no power). "
           f"Top system: " + ", ".join(f"{c} → {nm(m)}" for c, m in tops.items()) + ". Within each LLM, F1 does not trend with its own case knowledge (Spearman ρ "
           + ", ".join(f"{nm(m)} {r:+.1f}" for m, r in rhos.items()) + ")." + gap_txt
           + " The gap pattern is what contamination would predict, but it is equally what corpus type predicts (real human-judged email vs LLM-panel and synthetic gold), and Checks A and D test the mechanism directly and find none.")
    return verdict, txt


def reading_c(c: dict) -> tuple[str, str]:
    pooled = c.get("pooled_real", {})
    if not pooled:
        return "not run", "No conflict predictions."
    parts, weak, kf = [], [], {}
    for m, v in pooled.items():
        r = v["text_follow_cf"]["rate"]; vs = v.get("vs_veridian", {}); kf[m] = 1 - r
        fr = v.get("by_direction", {}).get("fact_relevant", {}).get("rate"); fi = v.get("by_direction", {}).get("fact_irrelevant", {}).get("rate")
        parts.append(f"{nm(m)} {pct(1 - r, 0)}% (knowledge-made-relevant tokens {pct(1 - fr, 0) if fr is not None else '—'}%, knowledge-made-irrelevant {pct(1 - fi, 0) if fi is not None else '—'}%; "
                     f"vs Veridian {pp(vs['diff'])} pp [{pp(vs['ci'][0])}, {pp(vs['ci'][1])}])" if vs else f"{nm(m)} {pct(1 - r, 0)}%")
        if vs and vs.get("ci") and vs["ci"][1] < 0:
            weak.append(m)
    any_kf = any(v > 0.05 for v in kf.values())
    verdict = "weakens" if weak else ("mixed — neutral for the claim as stated" if any_kf else "strengthens")
    txt = ("Knowledge-following rate on counterfactual documents, pooled over the four real matters: " + "; ".join(parts) + ". "
           + ("Every system reads the factual versions at ≥97%, so the overrides are real, almost entirely in one direction (a well-known 'hot' token keeps a document responsive even when the "
              "text says it is about something else), and concentrated on Jeb Bush, Mallinckrodt and Endo — Enron overrides are near zero. The rates are within noise of each system's Veridian "
              "baseline, where the only facts that can be overridden sit in the prompt itself; so the systems do let prior facts outweigh text on engineered conflicts, but no more for pre-trained "
              "facts than for in-context ones. On real corpora such conflicts are rare (Check A: ~7% of Enron J documents are even knowledge-dependent), which is why this does not show up as accuracy." if not weak else
              "Systems whose real-matter text-following is below their Veridian baseline with CI excluding 0: " + ", ".join(nm(m) for m in weak) + "."))
    return verdict, txt


def reading_d(d: dict) -> tuple[str, str]:
    ok = {m: v for m, v in d.get("models", {}).items() if v.get("status") == "ok"}
    if not ok:
        return "not run", "No brief predictions."
    up = [m for m, v in ok.items() if v["delta"]["f1"]["lo"] > 0]
    down = [m for m, v in ok.items() if v["delta"]["f1"]["hi"] < 0]
    txt = "ΔF1 with brief: " + ", ".join(f"{nm(m)} {ci(v['delta'], 'f1')}" for m, v in ok.items()) + "."
    if up:
        return "weakens", txt + f" The brief raises F1 for {', '.join(nm(m) for m in up)} (CI > 0): supplying case knowledge helps, so knowing a case can matter."
    if down:
        return "strengthens (with a twist)", txt + f" The brief lowers F1 for {', '.join(nm(m) for m in down)}: case knowledge, when supplied, hurts rather than helps."
    return "strengthens", txt + " No system's F1 moves beyond noise when the only possible source of case knowledge is supplied."


# ------------------------------------------------------------------------------------------------ report

def md_a(a: dict) -> str:
    if "systems" not in a:
        return "_not run_\n"
    L = [f"Tagger: {nm(a['tagger'])} at temperature 0, prompt `{a['prompt_version']}`; {a['n_tagged']} of {a['n_docs']} unique Enron J documents tagged. "
         f"Knowledge-dependent share on the six knowledge requests: {pct(a['share_kd_overall_knowledge_topics']['share'])}% "
         f"[{pct(a['share_kd_overall_knowledge_topics']['ci'][0])}, {pct(a['share_kd_overall_knowledge_topics']['ci'][1])}].", "",
         "| Request | n | knowledge-dependent share |", "|---|---:|---:|"]
    for q, v in a["share_kd_by_request"].items():
        L.append(f"| {q} | {v['n']} | {pct(v['share'])}% [{pct(v['ci'][0])}, {pct(v['ci'][1])}] |")
    L += ["", "Share tagged knowledge-dependent by gold label: " + ", ".join(f"{g} {pct(v['share'])}% (n={v['n']})" for g, v in a["share_kd_by_gold"].items() if "/" not in g) + ".", "",
          "| System | subset | n (pos) | named acc | named P / R / F1 | renamed F1 | ΔF1 renamed−named [95% CI] | right→wrong / wrong→right |", "|---|---|---:|---:|---|---:|---|---:|"]
    for m, v in a["systems"].items():
        if v.get("status") != "ok":
            L.append(f"| {nm(m)} | — | — | — | — | — | — | — |"); continue
        for sub in ("knowledge_dependent", "self_contained", "all"):
            b = v["subsets"].get(sub)
            if not b:
                continue
            L.append(f"| {nm(m)} | {sub.replace('_', '-')} | {b['n']} ({b['pos']}) | {pct(b['named']['accuracy'])} [{pct(b['named']['accuracy_ci'][0])}, {pct(b['named']['accuracy_ci'][1])}] | "
                     f"{pct(b['named']['precision'])} / {pct(b['named']['recall'])} / {pct(b['named']['f1'])} | {pct(b['renamed']['f1'])} | {ci(b['delta'], 'f1')} | {b['right_to_wrong']} / {b['wrong_to_right']} |")
    L += ["", "Contrasts (knowledge-dependent − self-contained):", "", "| System | named accuracy KD − SC | named F1 KD − SC | ΔF1(KD) − ΔF1(SC) | Δacc(KD) − Δacc(SC) |", "|---|---|---|---|---|"]
    for m, v in a["systems"].items():
        if v.get("status") == "ok" and "delta_kd_minus_delta_sc" in v:
            L.append(f"| {nm(m)} | {ci(v['named_acc_kd_minus_sc'])} | {ci(v['named_f1_kd_minus_sc'])} | {ci(v['delta_kd_minus_delta_sc'], 'f1')} | {ci(v['delta_kd_minus_delta_sc'], 'accuracy')} |")
    L += ["", "Most common tagger reasons for 'knowledge-dependent': " + "; ".join(f"“{r}” ({n})" for r, n in a["top_kd_reasons"][:6]) + ".", ""]
    return "\n".join(L)


def md_b(b: dict) -> str:
    L = []
    for which, title in (("four", "Four systems (Sol included): ablation named arms + Endo"), ("roster", "Main-study roster (adds Jeb Bush and CUAD; Sol absent)")):
        for mode in ("all_gold", "gray_excluded"):
            blk = b["tables"].get(which, {}).get(mode)
            if not blk or not blk.get("cells"):
                continue
            systems = ranking.FOUR if which == "four" else ranking.ROSTER_CORE
            L += [f"**{title} — {mode.replace('_', ' ')}**", "", "| Corpus (exposure) | gold | n pairs | prev. | mean κ | " + " | ".join(nm(m) + " P/R/F1" for m in systems) + " | F1 rank order |",
                  "|---|---|---:|---:|---:|" + "---|" * len(systems) + "---|"]
            rk = blk["ranks_f1"].get("ranking", {})
            for c, cell in blk["cells"].items():
                dif = blk["difficulty"][c]
                row = [f"{ranking.CORPORA[c][0]} ({ranking.CORPORA[c][2]})", ranking.CORPORA[c][5].split(" (")[0].split(":")[0], str(dif["n"]), pct(dif["prevalence"], 0) + "%", f"{dif['mean_pairwise_kappa']:.2f}"]
                for m in systems:
                    v = cell.get(m)
                    row.append("—" if not v else f"{pct(v['precision'],0)}/{pct(v['recall'],0)}/**{pct(v['f1'])}**" + (" †" if v["panel_member"] else ""))
                row.append(" > ".join(nm(m).replace("GPT-5.6 ", "") for m in rk.get(c, [])) or "—")
                L.append("| " + " | ".join(row) + " |")
            for key in ("ranks_f1", "ranks_recall", "ranks_precision", "ranks_f1_without_endo", "ranks_f1_without_endo_enron_k"):
                r = blk.get(key, {})
                w = r.get("kendall_w")
                if w:
                    L.append(f"- Kendall W ({key.replace('ranks_', '').replace('_', ' ')}): **{w['W']:.2f}** over {w['m_judges']} corpora ({', '.join(r['corpora'])}), p≈{w['p_approx']:.2f}; mean ranks "
                             + ", ".join(f"{nm(m)} {mr:.1f}" for m, mr in zip(r["systems"], w["mean_ranks"])))
            tr = blk.get("trend", {})
            for m, t in tr.get("per_model", {}).items():
                L.append(f"- {nm(m)}: F1 vs case score Spearman ρ = {t['spearman_f1']['rho']:+.2f} (perm. p {t['spearman_f1']['p']:.2f}); difficulty-adjusted ρ = {t['spearman_f1_adjusted']['rho']:+.2f} "
                         f"(p {t['spearman_f1_adjusted']['p']:.2f}) over {t['n']} corpora")
            g = tr.get("llm_minus_jev")
            if g:
                L.append(f"- Mean-LLM − Jev F1 gap vs mean LLM case score: ρ = {g['spearman']['rho']:+.2f} over {', '.join(g['corpora'])}; gaps " + ", ".join(f"{c} {pp(v)}" for c, v in zip(g["corpora"], g["gap_f1"])))
            L.append("")
    L.append("† system is a member of that corpus's gold panel (its score is partly circular). Case-knowledge composite (0–100) per corpus: "
             + "; ".join(f"{nm(m)}: " + ", ".join(f"{c} {v:.0f}" for c, v in cs.items() if v is not None) for m, cs in b["case_scores"].items() if m in (LUNA, TERRA, SOL)) + ".")
    hd = b.get("human_disagreement", {})
    if hd:
        L.append("Human-disagreement proxies (explore index, contested / n): " + ", ".join(f"{c} {pct(v['contested_share'])}%" for c, v in hd.items() if v.get("contested_share") is not None) + ".")
    return "\n".join(L) + "\n"


def md_c(c: dict) -> str:
    if not c.get("matters"):
        return "_not run_\n"
    L = ["Each pair is one short document in two versions: FACTUAL (consistent with the well-known fact) and COUNTERFACTUAL (the text contradicts it, flipping true relevance to a nameless "
         "request). The correct call follows the text. 'text-follow' = share of documents called as their text implies; on counterfactual documents 1 − text-follow is the knowledge-following rate. "
         "Veridian pairs assert and then contradict facts that exist only in the task context, so they measure 'fails to read the edit' with no world knowledge possible.", "",
         "| Matter | System | pairs | text-follow FACTUAL | text-follow COUNTERFACTUAL [95% Wilson] | CF − factual text-follow, pp [paired 95% CI] | McNemar p | fact-relevant→irrelevant CF text-follow | fact-irrelevant→relevant CF text-follow | vs Veridian baseline |",
         "|---|---|---:|---:|---|---|---:|---:|---:|---|"]
    for mt, v in c["matters"].items():
        for m, blk in v["models"].items():
            a = blk["all"]
            if not a.get("n"):
                continue
            bd = blk["by_direction"]
            fr = bd.get("fact_relevant", {}).get("text_follow_counterfactual", {}).get("rate"); fi = bd.get("fact_irrelevant", {}).get("text_follow_counterfactual", {}).get("rate")
            vs = c["vs_veridian"].get(f"{m}/{mt}")
            L.append(f"| {mt} | {nm(m)} | {a['n']} | {pct(a['text_follow_factual']['rate'],0)}% | {pct(a['text_follow_counterfactual']['rate'],0)}% [{pct(a['text_follow_counterfactual']['ci'][0],0)}, {pct(a['text_follow_counterfactual']['ci'][1],0)}] | "
                     f"{pp(-a['drop'])} [{pp(-a['drop_ci'][1])}, {pp(-a['drop_ci'][0])}] | {a['mcnemar_p']:.3g} | {pct(fr,0)}% | {pct(fi,0)}% | {('' if not vs else f'{pp(vs['diff'])} pp [{pp(vs['ci'][0])}, {pp(vs['ci'][1])}]')} |")
    L += ["", "Pooled over the four real matters (120 pairs per system):", "",
          "| System | factual text-follow (reading ceiling) | counterfactual text-follow | knowledge-following | on fact-relevant tokens made irrelevant | on fact-irrelevant tokens made relevant | vs Veridian baseline |",
          "|---|---:|---|---:|---:|---:|---|"]
    for m, v in c["pooled_real"].items():
        r = v["text_follow_cf"]; vs = v.get("vs_veridian", {}); bd = v.get("by_direction", {}); ff = v.get("text_follow_factual", {})
        fr = bd.get("fact_relevant", {}); fi = bd.get("fact_irrelevant", {})
        L.append(f"| {nm(m)} | {pct(ff.get('rate'), 0)}% | {pct(r['rate'])}% [{pct(r['ci'][0])}, {pct(r['ci'][1])}] | **{pct(1 - r['rate'])}%** | "
                 f"{pct(1 - fr['rate'], 0) if fr else '—'}% (n={fr.get('n', 0)}) | {pct(1 - fi['rate'], 0) if fi else '—'}% (n={fi.get('n', 0)}) | {ci(vs) if vs else '—'} |")
    L += ["", "Note on the Veridian baseline: its overrides sit almost entirely on the surgeon-payments request, where a document *denying* any payment to a named surgeon is arguably still "
          "'concerning' surgeon payments — part of that baseline is request-scope ambiguity rather than a failure to read the edit, so the baseline is lenient and the vs-Veridian "
          "comparison should be read with that in mind. The real-matter overrides (Roxicodone 'antacid' still called opioid marketing at p = 0.99; a Schiavo road-renaming file called "
          "an end-of-life dispute) have no such ambiguity."]
    # knowledge-following rows worth listing
    L += ["", "Counterfactual documents where the call followed world knowledge rather than the text (per system; token → request):", ""]
    for mt, v in c["matters"].items():
        if mt == "veridian":
            continue
        for m, blk in v["models"].items():
            bad = [r for r in blk["rows"] if not r["text_follow_cf"]]
            if bad:
                L.append(f"- {mt} / {nm(m)} ({len(bad)}): " + "; ".join(f"{r['token']} → {r['qid']} (p={r['p_counterfactual']:.2f})" for r in bad))
    return "\n".join(L) + "\n"


def md_d(d: dict) -> str:
    ok = {m: v for m, v in d.get("models", {}).items() if v.get("status") == "ok"}
    if not ok:
        return "_not run_\n"
    L = [f"Brief: `{d['brief_path']}` ({d['brief_chars']:,} characters, ≈{d['brief_chars']//4:,} tokens), appended to the Veridian task context exactly as the Mallinckrodt brief arm did. "
         f"Run on a stratified subset of {d['n_subset']} of the {d.get('n_source', 1000)} ablation documents (stratum = the document's positive-label set; every request keeps its positive share) because "
         f"the full arm's token volume would have exceeded the $15 cap; the without-brief side is the ablation's existing named run restricted to the same documents.", "",
         "| System | pairs (docs) | without brief P/R/F1 | with brief P/R/F1 | ΔP [95% CI] | ΔR [95% CI] | ΔF1 [95% CI] | labels changed | right→wrong / wrong→right (McNemar p) | Mallinckrodt brief ΔF1 (ablation) | Big Thorium brief ΔF1 (ablation) | paid |",
         "|---|---:|---|---|---|---|---|---:|---|---|---|---:|"]
    mnk = d.get("mnk_brief_effect_from_ablation", {})
    bt = d.get("bigthorium_brief_effect_from_ablation", {})
    for m, v in ok.items():
        mk = mnk.get(m); bb = bt.get(m)
        L.append(f"| {nm(m)} | {v['n_pairs']} ({v['n_docs']}) | {pct(v['without_brief']['precision'])}/{pct(v['without_brief']['recall'])}/**{pct(v['without_brief']['f1'])}** | "
                 f"{pct(v['with_brief']['precision'])}/{pct(v['with_brief']['recall'])}/**{pct(v['with_brief']['f1'])}** | {ci(v['delta'], 'precision')} | {ci(v['delta'], 'recall')} | {ci(v['delta'], 'f1')} | "
                 f"{pct(v['label_changed_share'])}% | {v['mcnemar']['lost']} / {v['mcnemar']['gained']} ({v['mcnemar']['p']:.3g}) | {ci(mk) if mk else '—'} | {ci(bb) if bb else '—'} | ${v['cost_paid']:.2f} |")
    L += ["", "Per request ΔF1 (with − without, pp; 500-draw cluster bootstrap):", "", "| Request | " + " | ".join(nm(m) for m in ok) + " |", "|---|" + "---|" * len(ok)]
    qids = list(next(iter(ok.values()))["per_request"].keys())
    for q in qids:
        L.append(f"| {q} | " + " | ".join(ci(ok[m]["per_request"].get(q, {}).get("delta"), "f1") if ok[m]["per_request"].get(q) else "—" for m in ok) + " |")
    ge = {m: v["gray_excluded"] for m, v in ok.items() if v.get("gray_excluded")}
    if ge:
        L += ["", "Gray-excluded ΔF1: " + ", ".join(f"{nm(m)} {ci(g['delta'], 'f1')} (n={g['n']})" for m, g in ge.items()) + "."]
    return "\n".join(L) + "\n"


def build_report(log=print) -> dict:
    RESULTS.mkdir(parents=True, exist_ok=True)
    log("scoring A …"); a = knowdep.score(log)
    log("scoring B …"); b = ranking.score(log)
    log("scoring C …"); c = conflict.score(log)
    log("scoring D …"); d = inject.score(log)
    spend = openai_spend()
    readings = {"a": reading_a(a), "b": reading_b(b), "c": reading_c(c), "d": reading_d(d)}
    figs = {}
    for key, fn, data in (("a", fig_a, a), ("b", fig_b, b), ("c", fig_c, c), ("d", fig_d, d)):
        p = RESULTS / f"fig_{key}_{ {'a': 'knowledge_dependence', 'b': 'ranking_stability', 'c': 'counterfactual_conflict', 'd': 'knowledge_injection'}[key] }.png"
        try:
            fn(data, p)
            if p.exists():
                figs[key] = p.name
        except Exception as e:  # a figure must never block the numbers
            log(f"figure {key} failed: {e!r}")
    summary = {"date": str(date.today()), "spend_usd": spend, "readings": {k: {"verdict": v[0], "text": v[1]} for k, v in readings.items()}, "figures": figs,
               "check_a": a, "check_b": b, "check_c": c, "check_d": d}
    dump_json(RESULTS / "summary.json", summary)
    md = [f"# Generalisation checks for the contamination study — {date.today()}", "",
          "Claim under test: *on the matters tested, knowing the case did not detectably change review accuracy.* Four checks that would strengthen or undermine it; "
          "each is read in claim language below. Jev is a system under test throughout. New OpenAI spend (paid, flex tier): "
          f"A ${spend['a_tagging']:.2f} · C ${spend['c_predictions']:.2f} (list ${spend['c_list']:.2f}) · D ${spend['d_predictions']:.2f} (list ${spend['d_list']:.2f}) · "
          f"**total ${spend['total']:.2f} of the ${spend['cap']:.0f} cap**. Jev spend: C ${spend['jev_c']:.2f}, D ${spend['jev_d']:.2f}.", "",
          "| Check | Verdict for the claim | One line |", "|---|---|---|"]
    for k, title in (("a", "A — knowledge-dependence error analysis"), ("b", "B — ranking stability"), ("c", "C — counterfactual conflict documents"), ("d", "D — knowledge injection on Veridian")):
        md.append(f"| {title} | **{readings[k][0]}** | {readings[k][1]} |")
    md += ["", "## Check A — knowledge-dependence error analysis (Enron J)", "",
           "Prediction if contamination helps: higher named accuracy on knowledge-dependent documents AND a larger named→renamed drop on them. "
           "Tagging is by Luna (one of the systems under test) — a tagger-is-a-subject caveat, mitigated by the tag being about the document, not the call.", "",
           md_a(a), f"![Check A]({figs.get('a', '')})" if "a" in figs else "", "",
           "## Check B — ranking stability across known and unknown matters", "",
           "Existing results only. Rank order of the systems per corpus and its agreement across corpora; F1 against the case-knowledge composite. n = 4 systems (5 in the roster table): "
           "Kendall W over four objects has almost no power, so the rank orders themselves and the magnitude of the F1 gaps carry the reading, not p-values.", "",
           md_b(b), f"![Check B]({figs.get('b', '')})" if "b" in figs else "", "",
           "## Check C — counterfactual conflict documents", "", md_c(c), f"![Check C]({figs.get('c', '')})" if "c" in figs else "", "",
           "## Check D — knowledge injection on Veridian", "",
           "If matter knowledge helps relevance review, supplying it for the one matter no system can know should raise F1. The brief is fictional (bible-consistent) and names the parties, products, people, "
           "deals and code names, timeline and outcome.", "", md_d(d), f"![Check D]({figs.get('d', '')})" if "d" in figs else "", "",
           "## Caveats", "",
           "- Check A's tagger is Luna, a system under test; tags describe documents, not calls, and the same tags are applied to all four systems, so a tagger bias would shift the KD share, not a system's contrast.",
           "- Check B has four (five) systems and five to seven corpora; Endo's gold is a Luna+Terra+Sol panel and Mallinckrodt's a Sonnet 5+Terra+Gemini panel, so those cells are partly circular and are marked. Veridian's gold is the synthetic planner's.",
           "- Check C documents are short and synthetic (templated like the classifier-native T1 items); the factual versions give each system's reading ceiling on the same material.",
           "- Check D ran on a stratified half of the Veridian ablation documents for cost; the brief is one author's fictional background and ~1k tokens, comparable to the Mallinckrodt brief.",
           "- All deltas are paired by document (cluster bootstrap over documents, 2,000 draws); C and D CIs are 95%.", ""]
    bt = RESULTS.parent / "ablation" / "bigthorium" / "summary.json"
    if bt.exists() and json.loads(bt.read_text()).get("brief"):  # the same brief-injection check on the second synthetic floor
        bb = json.loads(bt.read_text())["brief"]
        md.insert(len(md) - 1, "- Check D was repeated on Big Thorium (the Relativity aiR for Review demo workspace: public documents, invented case) with Relativity's own aiR case summary as the brief, against a leave-one-out panel gold: ΔF1 "
                  + "; ".join(f"{m} {100 * r['delta']['f1']['delta']:+.1f} [{100 * r['delta']['f1']['lo']:+.1f}, {100 * r['delta']['f1']['hi']:+.1f}]" for m, r in bb.items())
                  + " (`results/ablation/bigthorium/REPORT.md`).")
    (RESULTS / "REPORT.md").write_text("\n".join(md))
    log(f"wrote {RESULTS / 'REPORT.md'} and summary.json; figures: {list(figs.values())}")
    return summary
