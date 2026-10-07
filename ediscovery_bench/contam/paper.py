"""Two write-ups of the contamination probe, generated from results/contam/summary.json:

  paper.html      — an arXiv-style study report: abstract, method, results with every figure and table worth keeping, discussion,
                    limitations, references.
  explainer.html  — a short plain-language walk from the question to the conclusion, with terms defined where they first appear.

Both reuse the SVG generators in html.py so the figures are identical to the full report's.
"""
from __future__ import annotations

import json
from pathlib import Path

from .effect import effect as _effect
from .effect2 import effect2 as _effect2
from .jevnative import jev_native as _jev_native
from .verify_summary import verify_summary as _verify
from .html import (CORPUS_SHORT, CSS, MODEL_META, SET_LABEL, SET_ORDER, SET_ROLE, SPECTRUM, _bp_method, _composite, _endo_paragraph, _esc, _ladder, _ladder_narrative, _part1, _part2, _pct, _sd, dotplot, legend, table)
from .run import RESULTS_DIR

RUN_DATE = "3 October 2026"


# ------------------------------------------------------------------------------------------------ helpers

def _models(summary):
    pref = ["gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol"]
    return [m for m in pref if m in summary["models"]] + [m for m in summary["models"] if m not in pref]


def _fig_m2_totals(summary, models):
    EP = summary["evidence_prior"]
    rows = [(st, {m: (EP[m][st]["n_discriminative_named_total"], None, None) for m in models if st in EP.get(m, {})}) for st in SET_ORDER]
    mx = max([v[0] for _, d in rows for v in d.values()] + [10])
    top = 10 * ((mx + 9) // 10)
    return dotplot(rows, models, 0, top, list(range(0, top + 1, 10)), lambda v: f"{v:.0f}",
                   "M2 · Discriminative named terms per request set (total across the set's requests)", labels=SET_LABEL, roles=SET_ROLE, label_w=300, width=700)


class _Fig:
    """Numbered figures and tables."""

    def __init__(self):
        self.nf = 0
        self.nt = 0

    def fig(self, html: str, caption: str) -> str:
        self.nf += 1
        return f'<div class="pfig" id="fig{self.nf}"><div class="pcap"><b>Figure {self.nf}.</b> {caption}</div>{html}</div>'

    def tbl(self, html: str, caption: str, appendix: bool = False) -> str:
        if appendix:
            return f'<div class="ptbl" id="tabA1"><div class="pcap"><b>Table A1.</b> {caption}</div>{html}</div>'
        self.nt += 1
        return f'<div class="ptbl" id="tab{self.nt}"><div class="pcap"><b>Table {self.nt}.</b> {caption}</div>{html}</div>'


def _seq(vals, fmt):
    return " / ".join(fmt(v) if v is not None else "–" for v in vals)


PAPER_CSS = CSS + """
.paper{max-width:940px}
.paper h1{font-size:26px;line-height:1.2;margin:0 0 6px}
.paper .authors{color:var(--ink-3);margin-bottom:18px}
.paper .abstract{background:var(--panel);border:1px solid var(--line);padding:16px 20px;margin:18px 0 26px;font-size:14.5px}
.paper .abstract b{letter-spacing:.08em;text-transform:uppercase;font-size:11px;color:var(--ink-3);display:block;margin-bottom:6px}
.paper h2{font-size:19px;margin:34px 0 10px;border:0;padding:0;text-transform:none;letter-spacing:0;color:var(--ink)}
.paper h3{font-size:15.5px;margin:22px 0 8px}
.paper h4{font-size:14px;margin:16px 0 6px}
.pfig,.ptbl{margin:18px 0 24px}
.pcap{font-size:12.5px;color:var(--ink-2);margin:0 0 6px;line-height:1.45}
.pfig figure{margin:0}.pfig .figtitle{display:none}
.paper .refs{font-size:13px}.paper .refs li{margin-bottom:5px}
.paper .def{border-left:3px solid var(--line);padding:4px 12px;margin:10px 0;color:var(--ink-2);font-size:13.5px}
.paper .def b{color:var(--ink)}
.paper .toc{columns:2;font-size:13px;margin:0 0 14px}.paper .toc a{display:block;color:var(--ink-2);text-decoration:none;margin:2px 0}
.kf{counter-reset:k}.kf li{margin:8px 0}
.gloss{display:grid;grid-template-columns:170px 1fr;gap:6px 14px;font-size:13.5px;margin:12px 0 18px}
.gloss dt{font-weight:600}.gloss dd{margin:0;color:var(--ink-2)}
.step{display:grid;grid-template-columns:34px 1fr;gap:12px;margin:14px 0}
.howto{border-left:3px solid #9fb6cf;padding:6px 12px;margin:10px 0 6px;color:var(--ink-2);font-size:13.5px;background:#f6f9fc}
.analogy{border-left:3px solid #d9b56a;padding:6px 12px;margin:10px 0;color:var(--ink-2);font-size:13.5px;background:#fbf7ee}
.step .n{width:30px;height:30px;border-radius:50%;background:var(--ink);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:14px}
.step h3{margin:4px 0 6px}
@media print{.pfig,.ptbl{break-inside:avoid}}
"""


# ------------------------------------------------------------------------------------------------ the paper

def _bigthorium_paper_section() -> str:
    """§10A, present only when the Big Thorium probes/ablation have been run (results/contam/bigthorium_summary.json)."""
    from .bigthorium import section_html  # noqa: PLC0415
    html = section_html(heading="10A. Public documents, invented case: Relativity's Big Thorium demo workspace")
    return html.replace('<h3 id="bigthorium">', '<h2 id="s10a">').replace("</h3>", "</h2>", 1) if html else ""


def build_paper(summary: dict, out_path: Path = RESULTS_DIR / "paper.html") -> Path:
    models = _models(summary)
    L, T, S = (models + [None, None, None])[:3]
    N = lambda m: MODEL_META[m][0]  # noqa: E731
    short = lambda m: MODEL_META[m][0].split()[-1]  # noqa: E731
    F = _Fig()
    eff = _effect(summary)
    eff2 = _effect2()
    ver = _verify()
    nat = _jev_native(summary)
    p1 = _part1(summary, models)
    p2 = _part2(summary, models)
    lad = _ladder(summary, models)
    V, EG, ER, BK, LR = summary["verbatim"], summary["entity_recog"], summary["entity_recall"], summary["bench_knowledge"], summary["label_recall"]
    MR, EP, MD, MI = summary["matter_recall"], summary["evidence_prior"], summary["metadata_relevance"], summary["matter_id"]
    cost = sum(summary["cost_usd"].values())
    words = {1: "one", 2: "two", 3: "three", 4: "four"}

    abstract_native = (f" For the decision model itself we add four classifier-native probes (a code-name swap, a minimal-edit label flip, paraphrase sensitivity, published versus "
                       f"unpublished labels): the {nat['overall_short']}.") if nat else ""
    abstract_r2 = ((f" A second round carried the test to Jeb Bush (matter versus control topics, public figures renamed) and to CUAD, the one corpus whose documents are memorised, "
                    f"where paraphrase removes the memorised text that renaming leaves; a brief-injection check supplied the case for the fictional Veridian. For the LLMs, knowing the case "
                    f"{eff2['claim_verb']} on {words.get(len(eff2['matters']), len(eff2['matters']))} matters ({', '.join(eff2['matters'])}) under "
                    f"{words.get(len(eff2['manips']), len(eff2['manips']))} manipulations: no knowledge effect beyond {eff2['llm_bound']:.1f} F1 points, {eff2['interval_txt'].replace('every 95% interval includes zero', 'intervals including zero')}; paraphrasing "
                    f"CUAD changed F1 by ≤ {eff2['par_max']:.1f} points and no more on the best-remembered contracts"
                    + (f"; the {ver['kd_share']:.0f}% of Enron J documents that are knowledge-dependent are where help would show, and every system is less accurate there" if ver else "")
                    + (f". Jev's matter-topic scores depend on the real names ({eff2['jev_short']}): a small familiarity effect consistent with public-web knowledge of public figures, "
                       f"not by itself evidence of training on the collections." if eff2.get("jev_short") else "."))
                   if eff2 else "")
    abstract_effect = ((f"We then ran the effect test the probes pointed to: a full-document pseudonymisation ablation on {len(eff['systems'])} systems (the three LLMs and Jev). "
                        f"Renaming every person and organisation changes F1 by {eff['seq_j']} points on the Enron scandal requests and the knowledge effect (scandal minus control requests) is "
                        f"within ±3 points for every system, no interval excluding zero — a floor rather than a ceiling, since the models still identify Enron from the fact pattern in "
                        f"{eff['leak_share']} of the renamed documents.{abstract_r2}"
                        + ("" if eff2 else " That bounds the effect of name-mediated case knowledge on one matter at this sample size; it does not rule out smaller effects, other matters, or "
                                           "knowledge that survives renaming, so a clean test needs a corpus the models have not seen.")
                        + abstract_native)
                       if eff else "The decisive test of effect is a full-document pseudonymisation ablation, which these results locate on Enron." + abstract_native)

    def v(c, k, fmt=lambda x: f"{x:.2f}"):
        return _seq([V[m][c][k] for m in models], fmt)

    def v_runs_txt() -> str:
        """Derived: how many pool windows on the e-mail corpora reach an exact run of ≥ 8 words for any model, and the longest."""
        si = RESULTS_DIR / "scored_items.jsonl"
        rows = [r for r in (json.loads(l) for l in si.open()) if r["probe"] == "verbatim" and r["model"] in models and r.get("v_pool") == "kept"
                and r["corpus"] in ("enron", "jebbush", "mnk", "endo")] if si.exists() else []
        long_ = [r for r in rows if r["max_run"] >= 8]
        n = len({r["item_id"] for r in long_})
        longest = max((r["max_run"] for r in long_), default=0)
        zero = [CORPUS_SHORT.get(c, c).split(" (")[0] for c in ("enron", "jebbush", "mnk", "endo") if not any(r["corpus"] == c for r in long_)]
        return (f"In the filtered pool {n} window{'s' if n != 1 else ''} across the four e-mail corpora reach{'es' if n == 1 else ''} an exact run of ≥ 8 words for any "
                f"model (longest {longest} words)" + (f"; {' and '.join(zero)} ha{'s' if len(zero) == 1 else 've'} none." if zero else "."))

    def v_sig_txt() -> str:
        """Which (model, e-mail corpus) pairs beat the floor at p < 0.05 on LCS-F1 — derived, so the sentence tracks the numbers."""
        hits = [(m, c) for c in ("enron", "jebbush", "mnk", "endo") for m in models
                if ((V[m].get(c) or {}).get("vs_control") or {}).get("lcs_f_p_greater", 1) < 0.05]
        if not hits:
            return "the difference does not reach p &lt; 0.05 for any model on any of them"
        return "the difference reaches p &lt; 0.05 only for " + ", ".join(f"{N(m)} on {CORPUS_SHORT.get(c, c).split(' (')[0]}" for m, c in hits)

    def v_refusal_txt() -> str:
        """Derived: which model refuses, on which corpora, and what the refusals-as-zero convention would have done to its floor."""
        corp = [c for c in SPECTRUM if c in V[models[0]]]
        parts = []
        for m in models:
            r = {c: V[m][c]["refusal_rate"] for c in corp if c in V[m]}
            n_ref = sum(V[m][c].get("n_refused", 0) for c in r)
            if not n_ref:
                continue
            nz = [c for c in corp if c in r and r[c] > 0]
            zero = [c for c in corp if c in r and r[c] == 0 and c in ("enron", "jebbush", "mnk", "endo", "veridian", "cuad")]
            s = (f"{N(m)} refuses {n_ref} pool continuations as private or copyrighted text, at a rate that depends on the corpus — "
                 + ", ".join(f"{CORPUS_SHORT.get(c, c).split(' (')[0]} {_pct(r[c])}" for c in nz)
                 + (f", none on {', '.join(CORPUS_SHORT.get(c, c).split(' (')[0] for c in zero)}" if zero else "") + ".")
            if r.get("veridian", 0) >= 0.1:
                d = V[m]["veridian"]
                email = [c for c in ("enron", "jebbush", "mnk", "endo") if c in r]
                s += (f" The fictional floor is refused most; had refusals been scored as zero its LCS-F1 would read {d['lcs_f_mean_all']:.3f} instead of "
                      f"{d['lcs_f_mean']:.3f} and the e-mail corpora would test at p = "
                      + " / ".join(f"{V[m][c]['vs_control']['lcs_f_p_greater_all']:.3f}" for c in email) + " against it, where on answered items they test at p = "
                      + " / ".join(f"{V[m][c]['vs_control']['lcs_f_p_greater']:.2f}" for c in email) + ".")
            parts.append(s)
        none = [N(m) for m in models if not sum(V[m][c].get("n_refused", 0) for c in corp if c in V[m])]
        if none:
            parts.append(" and ".join(none) + (" refuse nothing." if len(none) > 1 else " refuses nothing."))
        return ("Refusals are excluded from every V statistic on both sides of the comparison and reported as a separate rate (Table 3), because a "
                "refusal is a policy reading, not a memorisation reading. " + " ".join(parts))

    def eg(c, k, fmt=_pct):
        return _seq([EG[m][c][k] for m in models], fmt)

    def mr(k, key="share"):
        return _seq([MR[m][k].get(key) for m in models], _pct)

    def ep(st, k, fmt=str):
        return _seq([EP[m][st][k] for m in models], fmt)

    def md(st, k, fmt=_pct):
        return _seq([MD[m]["by_set"][st][k] for m in models], fmt)

    def bk(q):
        return _seq([len(BK[m][q]["recovered"]) for m in models], str) + f" of {BK[models[0]][q]['n_keys']}"

    def lr(c):
        return _seq([LR[m][c]["acc"] for m in models], _pct)

    big = models[-1]
    corr = lad.get("corr", {})
    corr_txt = ", ".join(f"{short(m)} ρ = {c['spearman']:+.2f}" for m in models if (c := corr.get(m)))
    sol_terms = EP[big]["enron_j_named"]["per_request"]

    def disc_terms(key, n=5):
        return ", ".join(t["term"] for t in sol_terms.get(key, {}).get("top_terms", []) if t["named"] and t["discriminative"])[:n * 30]

    ladder_rungs = summary.get("ladder", {}).get("rungs", {})
    n_rungs = sum(1 for r in ladder_rungs.values() if not r.get("study"))
    _pm = lad.get("pm", {})
    _real_rungs = [k for k, r in ladder_rungs.items() if r.get("expected") not in ("none", "floor", "public-invented")]
    n_real_rungs = len(_real_rungs)
    n_real_ided = sum(1 for k in _real_rungs if all(_pm.get(m, {}).get(k, {}).get("id_hit") for m in models))
    _missed = [(k, m) for k in _real_rungs for m in models if not _pm.get(m, {}).get(k, {}).get("id_hit")]
    ladder_miss_txt = ("; the one miss is " + ", ".join(f"{short(m)} on {ladder_rungs[k].get('label', k).split(' (')[0]}" for k, m in _missed)
                       + (" (it names Reliant Energy, a company in the same scandal)" if _missed and _missed[0][0] == "enron" else "")) if _missed else ""
    n_enron_ided = sum(1 for m in models if MI[m].get("enron", {}).get("hit"))
    corr_small_txt = ", ".join(f"{c['spearman']:+.2f} (p = {c['p']:.3f})" for m in models[:-1] if (c := corr.get(m)))
    _m3_pairs = [x for m in models for x in MD[m]["by_set"].values() if x.get("delta_people_ci")]
    n_m3_pairs = len(_m3_pairs)
    n_m3_sig = sum(1 for x in _m3_pairs if x["delta_people_ci"][0] > 0 or x["delta_people_ci"][1] < 0)
    endo_par = _endo_paragraph(summary, models, link=' (Tables 3–10, Figure 15)')

    # ---------------------------------------------------------------- figures (numbered in order of appearance)
    fig_v_lcs = F.fig(p1["fig_v_lcs"], "Verbatim memorisation (V). Mean LCS-F1 between the model's 60-word continuation and the true continuation, "
                      "with 95% bootstrap confidence intervals; 60 documents per corpus (20 CSV chunks for Titanic). Veridian is the floor a plausible "
                      "in-genre continuation reaches with no knowledge; the two anchors are the ceiling.")
    fig_v_strip = F.fig(p1["fig_v_strip"], "Verbatim memorisation (V), per document. Longest run of consecutive words reproduced exactly (of 60). "
                        "Each dot is one document; bars are means; the dashed line marks 15 words, the threshold we treat as unambiguous memorisation.")
    fig_e_d = F.fig(p1["fig_e_d"], "Entity recognition (E2) as a signal-detection problem. d′ = z(hit rate) − z(false-alarm rate) over 30 names per corpus, "
                    "each asked against its true organisation and four foils. Zero means the model cannot tell the true organisation from a foil.")
    fig_heat = F.fig(p1["fig_heat"], "Entity recognition (E2): share of 'yes' answers by the source of the names (rows) and the organisation asked about (columns). "
                     "A diagonal pattern is knowledge; a bright column is a yes-saying bias toward that organisation.")
    fig_tiers = F.fig(p1["fig_tiers"], "Entity recognition (E2) by prominence tier. Names are ranked by how often they appear in the corpus; the top ten, the middle ten "
                      "and ten from the long tail are probed. Knowledge limited to the top tier is knowledge of the public story, not of the mailbox.")
    fig_l = F.fig(p1["fig_l"], "Label memorisation (L). Accuracy at guessing the published relevance label from a document identifier alone, 100 pairs per corpus "
                  "balanced within each topic so that the topic carries no label information (dashed line: chance = 50%). Titanic is the positive control: the "
                  "passenger's survival from the row's id and name.")
    fig_m1 = F.fig(p2["fig_m1"], "Matter recall (M1). Share of a hand-written checklist of 16–20 facts about each matter (parties, allegations, people, events, "
                   "outcome) that the model states when asked to describe the matter by name. Veridian is omitted: every model answered that it did not know it.")
    fig_m1c = F.fig(p2["fig_m1c"], "Matter recall (M1) by category of fact. 'People' is the category that bears most directly on review: who the custodians are and what they did.")
    fig_m2t = F.fig(_fig_m2_totals(summary, models), "Evidence prior (M2): discriminative named terms per request set, totalled over the set's requests. A term is "
                    "<em>named</em> if the model typed it as a person, organisation, code name, product or place and wrote it as a proper noun; <em>novel</em> if it was not "
                    "in the prompt; <em>grounded</em> if it occurs in ≥ 2 judged documents; <em>discriminative</em> if, in addition, it occurs in ≥ 2 responsive documents at "
                    "≥ 2× its overall rate (lift ≥ 2). The two Complaint J rows differ only in whether the company is named.")
    fig_m2c = F.fig(p2["fig_m2c"], "Evidence prior (M2): novel named terms the model volunteered per request (of 25 asked), before any check against the documents.")
    fig_m2a = F.fig(p2["fig_m2a"], "Evidence prior (M2): share of the novel named terms that are grounded in the judged documents.")
    fig_m2b = F.fig(p2["fig_m2b"], "Evidence prior (M2): share of the novel named terms that are discriminative.")
    fig_m2d = F.fig(p2["fig_m2d"], "Evidence prior (M2), generic keywords. The same scoring applied to terms typed as keyword or period. This is vocabulary — what any "
                    "competent reviewer would search for — and it discriminates at a similar rate on every corpus, including the fictional one.")
    fig_m3 = F.fig(p2["fig_m3"], "Metadata-only relevance (M3). Accuracy of a relevance call from Date + Subject alone (hollow circle) and from Date + From + To + Cc + Subject "
                   "(filled circle) on the same balanced sample of e-mails; the arrow is what seeing the people added. Grey tick: a lexical baseline (a request-title "
                   "word appears in the subject). Dashed line: chance. Purple: Jev, the classifier under evaluation, posed the same context, request and header block "
                   "through its API. Its vendor states it is not pre-trained on public text; that claim is under test here, and its flat arrows are consistent with it without "
                   "establishing it, since the LLMs' arrows are equally flat.")
    fig_lad = F.fig(lad["fig"], "The ladder. Real matters ordered by 12-month English-Wikipedia pageviews (grey bar, log scale). Dots: M1 recall share, counting only facts "
                    "the question did not itself state. Right: M0 identification from a sketch with every proper noun removed (filled = named it; hollow = named "
                    "something else; ? = said it could not tell). Shaded rows are the study's matters and the Microsoft ceiling.") if lad.get("has") else ""
    fig_lad2 = F.fig(lad["fig2"], f"Public footprint against recall, matters with a Wikipedia article. Spearman rank correlation: {corr_txt}.") if lad.get("has") else ""
    fig_eff = F.fig(eff["fig"], "The effect test: change in F1 when every person and organisation in the documents is consistently renamed (renamed − named, percentage points, "
                    "paired bootstrap 95% CI over documents), on the Enron Complaint J requests, the Complaint K control requests from the same mailbox, and the fictional Veridian; "
                    "last row: ΔF1(J) − ΔF1(K), the knowledge effect net of the cost of renaming. Jev (purple) ran as a fourth system.") if eff else ""

    # ---------------------------------------------------------------- tables
    tbl_corpora = F.tbl(table(["corpus", "role", "public since", "exposure route", "items"], [
        ["Enron e-mails (EDRM v2; TREC Legal 2009–10)", "study", "2003–2009", "component of The Pile; Kaggle; two decades of papers", "V 60 · E 30+150 · L 100 · M"],
        ["Jeb Bush e-mails (TREC 2016 Total Recall)", "study", "2015–2016", "posted on the web by the campaign; press quotation; NIST distribution", "V 60 · E 30+150 · L 100 · M (600-doc subset)"],
        ["Mallinckrodt opioid e-mails (OIDA)", "study", "2021–2023", "UCSF/JHU archive behind a search interface; quoted in MDL filings", "V 60 · E 30+150 · L 100 · M"],
        ["Endo opioid e-mails (OIDA)", "study · <span class=\"role post-cutoff\">post-cutoff</span>", "2024–2026", "UCSF/JHU archive; production published after the models' training cutoff, so the documents should be unseen while the matter is public", "V 60 · E 30+150 · L 100 · M"],
        ["CUAD contracts", "study", "2021", "NLP benchmark; the contracts are SEC EDGAR exhibits", "V 60 · B 41"],
        ["Veridian ApexHip (synthetic)", "<span class=\"role floor\">floor</span>", "written 2026-09", "cannot be in any training set", "all probes"],
        ["Founding documents (Federalist, Constitution, Declaration)", "<span class=\"role ceiling\">ceiling</span>", "1787–88", "among the most replicated texts on the web", "V 60 · E 30+150 · B 20 (20 Newsgroups)"],
        ["Kaggle Titanic train.csv", "<span class=\"role ceiling\">ceiling</span>", "2012", "replicated on millions of repositories", "V 20 · L 100"],
        ["U.S. v. Microsoft", "<span class=\"role ceiling\">ceiling</span> (M0, M1)", "1998–2002", "famous case built on e-mail evidence", "M0 · M1"],
    ], cls="tbl wide"), "Corpora, their roles and how they could have entered training data. V = verbatim, E = entity recall + recognition, B = benchmark knowledge, "
        "L = label recall, M = matter probes.")
    cmx = _composite(summary, models, m3_ref='<a href="#m3">§8.4</a>', native_ref='<a href="#jevnative">§10</a>')
    tbl_cmx = F.tbl(cmx["fig"] + f'<details><summary>Per-channel breakdown and scaling</summary>{cmx["note"]}{cmx["tbl"]}</details>',
                    "Contamination scores, dataset × model. Each channel's headline metric is placed between the floor (Veridian, 0) and a ceiling (100) for that model; <em>docs</em> averages the "
                    "document-level channels, <em>case</em> the matter-level channels, <em>all</em> every available channel with equal weight. Last column: channels probed, documents / case.") if cmx.get("has") else ""
    tbl_v = F.tbl(p1["tbl_v"], "Verbatim memorisation (V). Mean LCS-F1 (stars: one-sided Mann–Whitney test against Veridian; * p &lt; 0.05, ** p &lt; 0.01, *** p &lt; 0.001), "
                  "share of documents with an exact run of ≥ 8 and ≥ 15 words, mean longest run — all over answered items, on both sides of the test — and the refusal rate over all pool items.")
    tbl_e = F.tbl(p1["tbl_e"], "Entity knowledge (E). Free recall: share of 30 names for which the model volunteers the right organisation. Recognition: hit rate against the "
                  "true organisation, false-alarm rate against foils, d′, and hit rate by prominence tier (top / mid / tail).")
    tbl_b = F.tbl(p1["tbl_b"], "Benchmark knowledge (B). Share of the benchmark's own topics or categories recited from memory.")
    tbl_l = F.tbl(p1["tbl_l"], "Label memorisation (L). Accuracy on 100 within-topic-balanced pairs with Wilson 95% intervals; stars: two-sided binomial test against 50%.")
    tbl_m0 = F.tbl(p2["tbl_m0"], "Matter identification (M0). First line of each model's answer to 'which real company or case is this modelled on?' for the pseudonymised TREC "
                   "complaints and the de-identified sketches.")
    tbl_m1 = F.tbl(p2["tbl_m1"], "Matter recall (M1). Share of the checklist recovered; 'beyond context' restricts to facts the study's task context does not already state; "
                   "the facts the model missed.")
    tbl_m2 = F.tbl(p2["tbl_m2"], "Evidence prior (M2) by request set. Means over requests; totals are counts of distinct discriminative named terms.")
    tbl_m2_terms = F.tbl(p2["tbl_m2_terms"], f"Evidence prior (M2), {N(big)}, request by request. Bold terms are named things the model expected to find that do occur in the "
                         "judged documents and are over-represented among the responsive ones (lift and responsive-document count shown). Last column: the model's own "
                         "one-sentence statement of how much it knew.", appendix=True)
    tbl_m3 = F.tbl(p2["tbl_m3"], "Metadata-only relevance (M3). Accuracy with and without the people fields, paired difference with a bootstrap 95% interval over e-mails, "
                   "lexical baseline, calls fixed / broken by the people, and the rate of 'responsive' calls. The Jev rows are the classifier under evaluation, run on the "
                   "same e-mails through its API (no criteria). Its vendor states it is not pre-trained on public text; that is a claim under test, and a flat Δ people cannot "
                   "establish it because the LLMs' Δ is equally flat.")
    tbl_eff = F.tbl(eff["tbl"], "The effect test by system: ΔF1 per arm, the knowledge effect, the renaming cost on Veridian recall, the share of labels that flipped, and the "
                    "Mallinckrodt contrast (bare request vs a short case brief).") if eff else ""
    # round 2 and the generalisation checks (figures and tables are numbered in reading order, so they are created here, after the round-1 pieces)
    fig_cuad = F.fig(eff2["cuad_fig"], "Round 2, CUAD: change in F1 when the parties, dates, amounts and jurisdictions of each contract are renamed, and when each excerpt is paraphrased "
                     "(perturbed − named, percentage points, cluster-bootstrap 95% CI by contract); the Veridian row is the cost of the same paraphrase on an unseen e-mail corpus and the "
                     "last row the paraphrase knowledge effect net of it.") if eff2 else ""
    tbl_cuad = F.tbl(eff2["cuad_tbl"] + eff2["cuad_caveat"], "Round 2, CUAD, by system: ΔF1 under renaming and paraphrase, the two Veridian controls, the knowledge effects net of them, "
                     "label flips, and the Spearman correlation between a contract's Δaccuracy and its memorisation score (no dose–response).") if eff2 else ""
    fig_jeb = F.fig(eff2["jeb_fig"], "Round 2, Jeb Bush: change in F1 when the Governor, his family and Florida's public figures are renamed, on the matter topics (the governorship events the "
                    "models recite) and on control topics on the same documents; third row: the knowledge effect, Δ(matter) − Δ(control), paired within each bootstrap draw; last row: the "
                    "round-1 Veridian renaming floor.") if eff2 else ""
    tbl_jeb = F.tbl(eff2["jeb_tbl"], "Round 2, Jeb Bush, by system: ΔF1 overall, on matter and control topics, the knowledge effect, ΔRecall and ΔPrecision on the matter topics, and label flips.") if eff2 else ""
    tbl_verify = F.tbl(ver["verdict_tbl"], "The generalisation checks: verdict for the claim and the derived one-line reading of each.") if ver else ""
    fig_verify = F.fig(ver["d_fig"], "Check D: change in F1 when a fictional case brief is supplied for Veridian, the one matter no system can know (with brief − without, percentage points, "
                       "cluster-bootstrap 95% CI over documents), beside the round-1 Mallinckrodt brief arm.") if ver else ""
    tbl_verify_d = F.tbl(ver["d_tbl"], "Check D by system: precision, recall and F1 without and with the Veridian brief, the paired deltas, labels changed, flips and the Mallinckrodt comparison.") if ver else ""
    tbl_verify_a = F.tbl(ver["a_tbl"], "Check A by system: named accuracy on knowledge-dependent and self-contained Enron J documents, the renaming ΔF1 on each subset, and their difference.") if ver else ""
    tbl_lad = F.tbl(lad["tbl"], "The ladder, rung by rung: family, year, Wikipedia footprint (flagged where the lookup fell back to a company page), pre-registered "
                    "expectation, M0 marks, M1 shares, and the facts the largest model missed.") if lad.get("has") else ""
    tbl_native = F.tbl(nat["t1_tbl"], "The code-name swap (T1) by matter and system: relevant-call rate on the real-token version minus the fictional-token version, percentage points, "
                       "paired bootstrap 95% interval over pairs; Jev's Δ on decoy pairs (where case knowledge should lower the call) and its signal − decoy contrast.") if nat else ""

    # ---- the classifier-native probes (after the ablation's Jev material; the two together are the account of the decision model)
    if nat:
        native_items = "".join(f"<li><b>{t}</b> {x}</li>" for t, x in (("Bare token (FAS 140).", nat["bare_txt"]), ("T2 · minimal-edit label flip.", nat["t2_txt"]),
                                                                       ("T3 · paraphrase sensitivity (Jev only; it returns a probability).", nat["t3_txt"]),
                                                                       ("T4 · published versus unpublished labels.", nat["t4_txt"])) if x)
        native_spend = f" Spend: OpenAI ${nat['cost_openai']:.2f}, Jev ${nat['cost_jev']:.2f}." if nat["cost_openai"] is not None and nat["cost_jev"] is not None else ""
        native_section = f"""<h3 id="jevnative">Classifier-native probes of the decision model</h3>
<p>Every probe above except M3 is a generative question that a classifier cannot be asked, and the ablation removes one channel — proper names in full documents. To test the
decision model on its own terms we add four probes that use only what its interface offers, a relevance call and its probability, each a paired design with bootstrap intervals
[18]. The GPT-5.6 models are the positive comparison (systems known to carry matter knowledge) and Veridian the synthetic floor; no system is a clean reference, and every result
is stated as evidence consistent or inconsistent with the vendor's statement that Jev is trained on synthetic data.{native_spend}</p>
<p><b>T1 · code-name swap.</b> The same templated document twice, differing in one token — a real matter token (an Enron vehicle, a Florida controversy, an opioid brand) or a
fictional token of the same shape — under a request that describes the conduct without naming the token. On <em>signal</em> pairs a case-aware reader calls the real version
relevant more often; on <em>decoy</em> pairs the real token is something a case-aware reader knows is <em>not</em> what was asked, so knowledge lowers the call. {nat['t1_result']}</p>
{tbl_native}
<ul>{native_items}</ul>
{nat['reading']}"""
        discussion_native = (f" The decision model's own profile, from the classifier-native probes, is the same as the LLMs': {nat['overall_short']}. The one thing those probes cannot "
                             f"do is separate a base model pre-trained on public text from synthetic training data distilled from a model that knows these matters.")
        limitation_native = "".join(f"<li>{x}</li>" for x in nat["limitations"])
        conclusion_native = f" {nat['overall']}"
    else:
        native_section, discussion_native, limitation_native, conclusion_native = "", "", "", ""

    # ---- round 2 (CUAD and Jeb Bush) and the generalisation checks
    if eff2:
        round2_section = f"""<h3 id="effect2">Round 2: the memorised corpus and the public-figure mailbox</h3>
<p>The Enron ablation bounds the knowledge effect on the matter the LLMs know best, but every Enron document still describes the Enron scandal after renaming, and the gap between
what the models recall and what they could use may differ where the memory is of a different kind. Round 2 carried the design to the two cases Part I singled out. On CUAD the
memory is of the <em>text</em>: the contracts are republished and partly recitable, so besides renaming the parties, dates, amounts and jurisdictions we paraphrased every excerpt
with a model not under test, which removes the memorised surface that renaming leaves — a finish-the-document check confirms the paraphrase reduces verbatim retrievability — and
measured each contract's memorisation score so that the change in accuracy can be read against it. On Jeb Bush the memory is of <em>public figures</em>: the Governor, his family and
Florida's officials, whom all three models recite; the design is matter topics (the governorship events) against control topics on the same documents, with the figures renamed.
Systems: {eff2['sys_txt']}. {eff2['absent_txt']} Veridian is the control for both (renamed in round 1; paraphrased here). Method, per-topic
tables and the paraphrase fidelity check are in the round-2 report [19]; the spend was ${eff2['cost']:,.2f}.</p>
{eff2['cuad_result']}
{fig_cuad}
{tbl_cuad}
<details><summary>Memorisation under the manipulations (finish-the-document)</summary>{eff2['memo_tbl']}{eff2['memo_txt']}</details>
{eff2['jeb_result']}
{eff2['jev_p']}
{fig_jeb}
{tbl_jeb}
{eff2['three']}
{eff2['jev_account']}"""
    else:
        round2_section = ""
    if ver:
        verify_section = f"""<h3 id="verify">Generalisation checks</h3>
<p>Four checks, each cheap, each aimed at a way the ablation's null could be an artefact of what was measured rather than of what the models can use; details in the checks report
[20], spend ${ver['spend'].get('total', 0):.2f}.</p>
<ul>
<li><b>A · Knowledge-dependence.</b> {ver['a_line']}</li>
<li><b>B · Ranking stability.</b> {ver['b_line']}</li>
<li><b>C · Counterfactual conflicts.</b> {ver['c_line']}</li>
<li><b>D · Brief injection on Veridian.</b> {ver['d_line']}</li>
</ul>
{tbl_verify}
{fig_verify}
{tbl_verify_d}
{tbl_verify_a}
{ver['overall']}
{ver['carry']}"""
    else:
        verify_section = ""

    if eff:
        effect_section = f"""<h2 id="s10">10. Results: the effect — the pseudonymisation ablation</h2>
<p>The probes above measure what is in the model. Having found the case knowledge largest and most specific on the Enron Complaint J requests, we ran the effect test there:
a fixed sample of documents classified twice, once as-is and once with every person and organisation consistently renamed, on three arms — the Complaint J requests, the
Complaint K requests from the same mailbox as a control, and Veridian, where the names carry no knowledge and renaming can only cost — plus a Mallinckrodt arm that supplies a
short case brief instead of removing names. Jev ran as a fourth system. The method, per-request tables, dose–response by number of knowledge-bearing names and the leakage check are
in the ablation report [17]; the spend was ${eff['cost']:,.2f}.</p>
{eff['result']}
{fig_eff}
{tbl_eff}
{eff['leak']}
{eff['jev']}
{eff['brief']}
{round2_section}
{verify_section}
{native_section}"""
        r2_disc = ""
        if eff2:
            r2_disc = (f" Round 2 narrows the second reading. On CUAD the memory is of the text itself, and paraphrase — which measurably reduces verbatim retrievability — changed F1 by "
                       f"≤ {eff2['par_max']:.1f} points, within the cost of the same paraphrase on Veridian and with no dose–response across contracts; on Jeb Bush, where "
                       + (f"{eff2['leak_model']} still identifies the mailbox in {eff2['leak_share']} of renamed e-mails" if eff2.get("leak_share") else "the mailbox is still recognisable from the policy context")
                       + ", the matter-topic knowledge effect is "
                       f"{'; '.join(f'{MODEL_META[m.split('@')[0]][0].split()[-1]} {100 * eff2['ke'][m]['delta']:+.1f}' for m in eff2['jeb_sys'] if not m.startswith('jev'))}"
                       + (f"; and supplying the case for Veridian through a brief moved F1 by {ver['d_seq']}" if ver else "") + ". "
                       f"For the LLMs the first reading now holds on {words.get(len(eff2['matters']), len(eff2['matters']))} matters under {words.get(len(eff2['manips']), len(eff2['manips']))} "
                       f"manipulations — remove the names, remove the memorised text, inject the case — with no knowledge effect beyond {eff2['llm_bound']:.1f} points"
                       + (f", and the knowledge-dependent documents ({ver['kd_share']:.0f}% of Enron J), where help would show, are where every system does worse" if ver else "") + ". "
                       + (f"Jev is the exception that sharpens the point: it knows the matters, shows no sign of the documents or labels, yet its matter-topic scores depend on the real names "
                          f"({eff2['jev_short']}; FAS 140 on Enron; the knowledge-dependent Enron documents) — consistent with an encoder carrying public-web knowledge of public figures "
                          f"and leaning on it to match, a familiarity effect of roughly 2–3 F1 points that an evaluation on a famous-figure collection should expect, and not by itself evidence "
                          f"of training on the collections. " if eff2.get("jev_short") else "")
                       + (f"One pattern runs the other way and is left open: system ordering is not stable across corpora (Kendall W = {ver['W']:.2f}) and the LLM − Jev gap widens with "
                          f"the LLMs' case knowledge (mean-LLM − Jev F1: {ver['gap_txt']} pp); contamination predicts that, but so does corpus type, and four systems cannot separate them." if ver else ""))
        discussion_effect = (f"<p>Following Magar and Schwartz [5], the probes measure exposure; §10 measures exploitation on the corpus where exposure was greatest, and finds it "
                             f"small: the knowledge effect is within ±3 points of F1 for every system, with no interval excluding zero and no consistent sign across the LLMs, while "
                             f"renaming itself flips {eff['flip_txt']} of labels and costs recall on the fictional corpus. Two readings are consistent with this. The first is that the case "
                             f"knowledge Part II documented is genuinely worth little to a full-document relevance call: the document says what it says, and a reader who knows the "
                             f"Raptor vehicles by name gains little over one who reads the paragraph describing them. The second is that the ablation could not remove the knowledge, "
                             f"because the models recognise the case from the fact pattern in {eff['leak_share']} of renamed documents and could apply what they know to the renamed "
                             f"text. The leakage check favours the second as at least a partial explanation, which makes the Enron Δ a lower bound. Either way the evidence is that the names "
                             f"are not the main channel — the same conclusion M3 reached at the header level."
                             + (r2_disc if eff2 else f" What the ablation establishes is a bound on one matter at this sample size, not the absence of an effect; the clean test moves off Enron: "
                                                     f"a real matter that post-dates the models' cutoff, held out and re-dated as models update.")
                             + f"{discussion_native}</p>")
        changes_enron = (f"with the measured effect: renaming the documents moves F1 by {eff['seq_j']} points ({eff['sys_txt']}), a floor rather than a ceiling because the case is "
                         f"recognised regardless.")
        changes_r2 = ""
        if eff2:
            changes_r2 = (f"<li>For the LLMs, report the knowledge effect as bounded on {words.get(len(eff2['matters']), len(eff2['matters']))} matters (no effect beyond {eff2['llm_bound']:.1f} F1 "
                          f"points under renaming, paraphrase and brief injection); CUAD's memorisation caveat stands as a caveat on exposure, not on its F1 (paraphrase ≤ {eff2['par_max']:.1f} points).</li>"
                          + (f"<li>Expect a Jev score on a famous-figure collection to run a few points high relative to an unknown matter: its matter-topic scores depend on the real names "
                             f"({eff2['jev_short']}), a familiarity effect of roughly 2–3 F1 points that is consistent with public-web knowledge of public figures and is not by itself "
                             f"evidence of training on the collections.</li>" if eff2.get("jev_short") else "")
                          + (f"<li>Check A's knowledge-dependent documents ({ver['kd_share']:.0f}% of Enron J) are the natural stratum for any future effect test: it is where help would show, "
                             f"and every system is less accurate there." if ver else ""))
        limitation_effect = (f"<li><b>The Enron effect test is bounded, not clean.</b> Renaming removes the names and not the fact pattern; the models identify Enron in {eff['leak_share']} "
                             f"of renamed documents ({eff['leak_names']}). The measured knowledge effect is therefore a lower bound, and a fact-pattern-free rewrite of a real matter is "
                             f"not possible without destroying the documents.</li>"
                             + (f"<li><b>Round 2 ran without {' and '.join(MODEL_META[m.split('@')[0]][0] for m in eff2['absent'])}.</b> {eff2['absent_txt']} The three-matter statement rests on "
                                f"two LLMs for Jeb Bush and CUAD.</li>" if eff2 and eff2.get("absent") else "")
                             + ("<li><b>The CUAD paraphrase control is not genre-matched.</b> The cost of paraphrase was measured on Veridian e-mail, not on unseen contracts; a post-cutoff "
                                "EDGAR sample with expert clause labels is the clean control and was not affordable. The within-CUAD dose–response is the primary control.</li>" if eff2 else "")
                             + (f"<li>{ver['b_caveat']}</li>" if ver else "")
                             + ("<li><b>Check A's tagger is a system under test</b> (Luna); the tags describe documents, not calls, and are shared across systems, so a tagger bias would shift "
                                "the knowledge-dependent share rather than any system's contrast. Check D ran on a stratified half of the Veridian documents for cost.</li>" if ver else "")
                             + f"{limitation_native}")
        conclusion_effect = ((f"The effect test it pointed to has been run on {words.get(len(eff2['matters']), len(eff2['matters']))} matters: removing every name from the Enron documents, "
                              f"renaming the public figures in the Jeb Bush e-mails and paraphrasing away the memorised text of the CUAD contracts — and, in the other direction, supplying the "
                              f"case for Veridian through a brief — changed the LLMs' F1 by no more than {eff2['llm_bound']:.1f} points net of control, with {eff2['interval_txt'].replace('every 95% interval includes zero', 'every interval including zero')}; "
                              f"the Enron number is a floor, limited by the models' ability to recognise the case without its names, and the decisive clean test remains a corpus the models have "
                              f"never seen."
                              + (f" Jev, the system under test, knows the matters and shows no sign of their documents or labels, but its matter-topic scores depend on the real names "
                                 f"({eff2['jev_short']}): a small familiarity effect to expect on famous-figure collections, not a contamination verdict." if eff2.get("jev_short") else "")
                              + conclusion_native)
                             if eff2 else
                             (f"The effect test it pointed to has been run: removing every name from the Enron documents changes F1 by {eff['seq_j']} points across four systems, with "
                              f"a knowledge effect indistinguishable from zero at this sample size — a bound on name-mediated knowledge for one matter, limited by the models' ability to "
                              f"recognise the case without its names, and one that moves the decisive test to a corpus the models have never seen.{conclusion_native}"))
    else:
        effect_section = ('<h2 id="s10">10. Results: the effect — the pseudonymisation ablation</h2><p>The full-document ablation has not been run; when it has, its result is reported here.</p>'
                          + native_section)
        discussion_effect = ("<p>Following Magar and Schwartz [5], our probes mostly measure exposure. The decisive test is a full-document pseudonymisation ablation — classify a "
                             "fixed sample twice, as-is and with every person and organisation consistently renamed — and these results say where to run it: on the Enron Complaint J "
                             "requests first. If the drop on Enron exceeds the drop on Veridian, the matter knowledge is doing work.</p>")
        changes_enron = "and run the full-document ablation there first."
        changes_r2 = ""
        limitation_effect = "<li><b>Exposure, not effect</b>, for every probe but M3; the ablation in §11.2 is the test this study motivates but does not perform.</li>" + limitation_native
        conclusion_effect = "It points to the one experiment — full-document pseudonymisation on Enron — that would measure how much the knowledge is worth." + conclusion_native


    # ---------------------------------------------------------------- numbers for the prose
    enron_disc = f"{ep('enron_j', 'n_discriminative_named_total')} → {ep('enron_j_named', 'n_discriminative_named_total')}"
    sig_m3 = [(m, st) for m in models for st in ("veridian", "jebbush", "enron_k", "enron_j", "mnk", "endo") if MD[m]["by_set"].get(st) and MD[m]["by_set"][st]["delta_people_ci"][0] > 0]
    sig_txt = "; ".join(f"{short(m)} on {st.replace('_', ' ')} ({_sd(MD[m]['by_set'][st]['delta_people'], 1)}, CI [{_sd(MD[m]['by_set'][st]['delta_people_ci'][0], 1)}, {_sd(MD[m]['by_set'][st]['delta_people_ci'][1], 1)}])" for m, st in sig_m3) or "none"
    jev_m3_par = ""
    if summary.get("classifier_models"):
        jm = MD[summary["classifier_models"][0]]["by_set"]
        jd = [x["delta_people"] for x in jm.values()]
        j_sig = [st for st, x in jm.items() if x["delta_people_ci"][0] > 0 or x["delta_people_ci"][1] < 0]
        j_sig_txt = "no interval excludes zero" if not j_sig else "the interval excludes zero only on " + ", ".join(st.replace("_", " ") for st in j_sig)
        jev_m3_par = ("<p>Jev, the classifier the main study evaluates, can be posed this one probe, and was: the same context, request and header block through its API, "
                      f"{sum(x['n'] for x in jm.values()) * 2:,} calls. From the subject alone it calls {_pct(jm['enron_j']['acc_subject'])} on the Enron scandal requests, "
                      f"{_pct(jm['mnk']['acc_subject'])} on Mallinckrodt and {_pct(jm['jebbush']['acc_subject'])} on Jeb Bush; adding the people moves it by "
                      f"{_sd(min(jd))} to {_sd(max(jd))}, and {j_sig_txt}: the same flat pair the LLMs show. Jev’s vendor states it is not pre-trained on public text; we "
                      "treat that as a claim to test. The flat people effect is consistent with the claim but does not establish it, since the LLMs — which "
                      f"demonstrably know the people (§7, §8.2) — show nearly the same flatness ({n_m3_sig} of {n_m3_pairs} LLM intervals exclude zero); M3 therefore has little power to detect people-knowledge in any system, and "
                      "the full-document test is the ablation of §10" + (", and the probes built for a classifier's interface follow it there" if nat else "") + ". What M3 does separate is the subject-only call: the LLMs sit 10–14 points above Jev "
                      "on the Enron scandal requests, which is reading of the subject line rather than a people effect.</p>")

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Is the case inside the model? Measuring training-data contamination for eDiscovery benchmarks</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{PAPER_CSS}</style></head>
<body><main class="paper">
<h1>Is the case inside the model? Measuring training-data contamination for eDiscovery relevance-review benchmarks</h1>
<div class="authors">JND eDiscovery · AI team — draft of {RUN_DATE}</div>

<div class="abstract"><b>Abstract</b>
Evaluations of large language models (LLMs) on legal document review reuse public corpora — the Enron e-mails, the Jeb Bush e-mails, the Mallinckrodt opioid
documents, the CUAD contracts — that are old enough and public enough to be in the models' training data; we add a fifth, the Endo opioid e-mails, published in
2024–26 after the models' cutoffs. We ask whether that exposure exists, through which
channel, and whether it is the kind of knowledge that would change a relevance call. We separate two units of contamination. The <em>document</em> unit asks
whether the model has absorbed the texts, the people in them, the benchmark's topics or its published labels; we probe each with a cheap, controlled test
calibrated against a fictional corpus (floor) and saturated public texts (ceiling). The <em>matter</em> unit, specific to litigation, asks whether the model knows
the case: recognises it when the names are changed, recalls its record, can predict what responsive documents contain, and reads e-mail headers with knowledge
of who the people are. Across three OpenAI models of increasing size, we found no evidence of document-level memorisation of the e-mail corpora: on answered
items the finish-the-document score is indistinguishable from the 2026 synthetic floor (verbatim LCS-F1 {v('enron', 'lcs_f_mean')} for Enron against a floor of
{v('veridian', 'lcs_f_mean')}), no 15-word exact run survives a two-stage chaff filter, staff recall is 0 of 30 names on Mallinckrodt and Endo and a handful of
famous names on Enron and Jeb Bush, and published labels are guessed at chance — under a probe that does detect memorisation on the public-domain anchors
(ceiling {v('canon', 'lcs_f_mean')}) and on CUAD, which sits above the e-mail floor in a way consistent with memorisation of republished public contracts (the
floor is not genre-matched, so part of that gap may be the predictability of legal drafting). The Enron corpus is in open training sets, so presence in training
data is likely; what is not detectable is document-level memory, consistent with memorisation tracking repetition rather than presence [7]. At the matter level the
picture inverts: the TREC Legal Track's pseudonymised Enron complaint is decoded by {n_enron_ided} of three models (the third names a company in the same scandal),
{mr('enron')} of the Enron record is recited, and naming the company turns {enron_disc} grounded, label-discriminative named terms per model
— deal names, special-purpose vehicles and the Andersen partners in the shredding — while the same mailbox's unrelated oil-spill requests yield
{ep('enron_k', 'n_discriminative_named_total')}. Knowing the people adds little to a relevance call made from headers once the subject line is known
(paired differences within ±3 points; {n_m3_sig} of {n_m3_pairs} model × request-set intervals exclude zero). A ladder of {n_rungs} real matters at graded public exposure, with two
post-cutoff cases as a real-but-unseen floor, identifies {n_real_ided} of {n_real_rungs} real matters from a nameless sketch for every model; recall is graded by
public footprint for the two smaller models (Spearman {corr_small_txt}) and not significantly for the largest ({corr.get(big, {}).get('spearman', 0):+.2f}, p = {corr.get(big, {}).get('p', 1):.2f}),
and only matters after the training cutoff are unknown. The evidence points to matter-level exposure being common and document-level exposure being rare for
internal e-mail, and to pseudonymising a complaint being no defence. Endo shows the Enron pattern from the other side:
every model identifies the matter and recalls {mr('endo')} of its record, while its documents — published after the cutoff — show no document-level signal (LCS-F1 {v('endo', 'lcs_f_mean')}, name
recall 0%, labels at chance), as expected; it is the held-out benchmark we recommend going forward. {abstract_effect} The probe battery costs about ${cost:,.0f} across three models.
</div>

<div class="toc">
<a href="#s1">1. Introduction</a><a href="#s2">2. Related work</a><a href="#s3">3. Corpora and anchors</a><a href="#s4">4. Part I: document-level probes</a>
<a href="#s5">5. Part II: matter-level probes</a><a href="#s6">6. The ladder</a><a href="#s7">7. Results: documents and people</a><a href="#s8">8. Results: the case</a>
<a href="#s9">9. Results: the ladder</a><a href="#s10">10. Results: the effect</a><a href="#s11">11. Discussion</a><a href="#s12">12. Limitations</a><a href="#s13">13. Conclusion</a><a href="#refs">References</a><a href="#appx">Appendix</a>
</div>

<h2 id="s1">1. Introduction</h2>
<p>A relevance-review benchmark compares a classifier's judgments with human relevance judgments over a collection of documents. When the classifier is a large
language model, there is a confound that does not arise for a classifier trained only on the collection: the model may already have seen the documents, the
people who wrote them, the published judgments, or the questions, during pre-training. This is the <em>training-data contamination</em> problem, well studied for
NLP benchmarks [1–5]. It matters here because an evaluation of LLMs against a purpose-built review system (Jev, whose vendor states it is a System
One classifier not pre-trained on public text — a claim this study treats as under test, not as given) is meant to predict performance on a <em>client's</em> collection, which no model has seen. Any score that depends on prior exposure does not transfer.</p>
<p>Legal review adds a second, distinct route. A review is organised around a <em>matter</em>: a complaint, its allegations, the parties and their officers, the
record the parties fought over, and the outcome. The study's real corpora come from three of the most heavily documented matters in American legal history —
the Enron collapse, the opioid multidistrict litigation, and a two-term governorship whose controversies were national news. A reviewer who knows the case knows
which transactions were later found fraudulent, which executives were indicted, which code names mattered and in which year the shredding happened; such a
reviewer reads an e-mail from the CFO about an offshore vehicle as responsive to a debt-concealment request without the request saying "offshore vehicle". A model
can carry that knowledge without having memorised a single e-mail, and a contamination test aimed at documents will clear it.</p>
<p>We therefore measure contamination at two units. <b>Part I</b> treats each corpus as text and probes four channels — verbatim memorisation, entity knowledge,
benchmark knowledge, label memorisation — each with a cheap test read against a floor (a fictional corpus written in 2026) and a ceiling (texts every model has
certainly seen many times). <b>Part II</b> treats each corpus as a matter and probes four things a case-aware reviewer has: recognition of the matter from a
de-identified description, recall of its record, a prior over what responsive documents contain (checked against the labels), and header-level judgments with
and without the people. A <b>ladder</b> of {n_rungs} real matters at graded public exposure, including two cases filed after the models' training cutoff, calibrates
the matter probes between the floor and the ceiling.</p>
<p>Our contributions are (i) a controlled, inexpensive battery for document-level contamination with explicit floor and ceiling anchors; (ii) a set of
matter-level probes specific to litigation, including one (M2) that scores a model's expectations against the documents' actual labels and so measures whether
case knowledge is <em>actionable</em>; (iii) a calibration ladder with a post-cutoff control; and (iv) results on three models showing that for these corpora the
document unit and the matter unit give different answers, and which one matters for evaluation.</p>

<h2 id="s2">2. Related work</h2>
<p>Verbatim extraction and quantification of memorisation in language models were established by Carlini et al. [6, 7], who showed that memorisation grows with
model scale, with the number of times a sequence appears in training data, and with the length of the prompt; our verbatim probe (V) follows their
prompt-and-continue design and our scale gradient reproduces their first finding. Bordt et al. [8] showed that LLMs reproduce rows of widely replicated tabular
datasets, including the Kaggle Titanic data, and that this leaks the label column; the Titanic rows are our positive control for both verbatim and label
memorisation. Benchmark contamination has been surveyed and measured by Sainz et al. [1], Golchin and Surdeanu [2], Oren et al. [3] and Shi et al. [4]; Magar and
Schwartz [5] drew the distinction we rely on between <em>exposure</em> (the data is in the model) and <em>exploitation</em> (the model's score benefits from it). Our
probes measure exposure; one of them (M3) is a small test of exploitation, and the pseudonymisation ablation of §10 is the full one.</p>
<p>The corpora are standard in information retrieval and eDiscovery research: the Enron corpus [9], used by the TREC Legal Track [10, 11] whose pseudonymised
complaints we reuse as identification probes; the Jeb Bush e-mails of the TREC Total Recall Track [12]; the CUAD contract benchmark [13]; and the Opioid Industry
Documents Archive. Technology-assisted review and its evaluation against manual review are described by Grossman and Cormack [14]. We are not aware of prior work
measuring whether review models know the <em>matters</em> behind these collections.</p>

<h2 id="s3">3. Corpora and anchors</h2>
<p>The study's six corpora, the two positive controls and the matter-level ceiling are listed in Table 1 with the route by which each could have entered training
data. The design principle is that no free-text score has a natural zero: a model that knows nothing still produces a plausible continuation in the right genre
and still says "yes" to some foils. Every number is therefore read as a position between the floor and the ceiling, measured with the same prompts and the same
scorer.</p>
{tbl_corpora}
<div class="def"><b>Floor.</b> Veridian is a synthetic medical-device litigation (a metal-on-metal hip MDL) with fictional parties, people, documents and
requests, written in September 2026. It is what a model scores when it can know nothing. <b>Ceilings.</b> The Federalist Papers, Constitution and Declaration
(verbatim and entity channels; the framers as names; the 20 Newsgroups categories as a benchmark), the Kaggle Titanic training set (verbatim and label channels),
and <em>U.S. v. Microsoft</em> (matter channels) are what a model scores when it has certainly seen the material many times. <b>Post-cutoff real corpus.</b> Endo is
neither anchor: a real production from the Opioid Industry Documents Archive published in 2024–26, after every model's training cutoff, from a matter (Endo's Opana ER
litigation and 2022 bankruptcy) that is itself old and public. Its documents should therefore behave like Veridian's and its matter like a real one; it is run through
every channel. Its relevance labels come from a three-OpenAI-model panel (Anthropic and Gemini keys were absent), unlike Mallinckrodt's mixed panel.</div>

<h2 id="s4">4. Part I: document-level probes</h2>
<p>Four channels, one probe each, run identically on every corpus. Models answer at temperature 0 with the study's own decoding settings
(<code>reasoning.effort = none</code>), so the probe measures what the review configuration brings.</p>
<h3>4.1 V · Verbatim memorisation</h3>
<p>The model is shown the first ~150 words of a document and asked to continue with the next 60 words. We score the continuation against the true text with the
F1 of the longest common subsequence of words (<b>LCS-F1</b>), the longest run of consecutive words reproduced exactly, and a <b>novelty</b> condition: a run only
counts if it contains at least one 5-gram absent from the prompt (digits masked), so that copying the prompt (a repeated error message, a template with new figures) is not memorisation. We
report the share of documents with runs ≥ 8 and ≥ 15 words. Significance against the floor uses a one-sided Mann–Whitney U test on per-document LCS-F1;
intervals are bootstrap 95% intervals of the mean. {_bp_method(summary)}</p>
<h3>4.2 E · Entity knowledge</h3>
<p>Thirty personal names per corpus are extracted from headers, ranked by frequency and sampled from three prominence tiers (top, middle, long tail). <b>E1, free
recall</b>: "Who is {{name}}?" scored on whether the answer names the corpus's organisation; "unknown" answers are counted separately. <b>E2, recognition</b>:
"Was {{name}} associated with {{organisation}}?" asked for the true organisation and for four foils drawn from the other corpora, which turns the probe into a
signal-detection task with a hit rate, a false-alarm rate and <b>d′ = z(hits) − z(false alarms)</b> [15]. Recognition is more sensitive than recall; the false-alarm
rate is what makes it interpretable, since a model that says "yes" to everything has a high hit rate and a d′ near zero.</p>
<h3>4.3 B · Benchmark knowledge</h3>
<p>The model is asked to list, from memory, the benchmark's own topics or categories: the 34 TREC 2016 Total Recall topics, the 7 and 4 TREC Legal 2009 and 2010
topics, the 41 CUAD clause categories, the 20 Newsgroups categories (ceiling), facts about the Opioid Industry Documents Archive, and whether the Veridian matter
exists (floor; any confident description is a confabulation). Scoring is keyword recovery against the published lists.</p>
<h3>4.4 L · Label memorisation</h3>
<p>Given only a document identifier and the topic, the model is asked for the published relevance label. One hundred pairs per corpus are balanced
<em>within each topic</em> so that the topic carries no label information; the topic-only ceiling is therefore exactly 50%. The Titanic positive control asks for a
passenger's survival from the row's id and name after balancing on sex and age. Accuracy is reported with Wilson 95% intervals and a two-sided binomial test
against 50%. (A first version balanced across the whole corpus and produced a spurious 70% on Mallinckrodt from topic prevalence alone; see §11.)</p>

<h2 id="s5">5. Part II: matter-level probes</h2>
<p>Each probe corresponds to something a case-aware reviewer has. Controls: Veridian is the floor throughout; <em>U.S. v. Microsoft</em> is the ceiling for M0
and M1; Enron supplies two within-corpus contrasts — the TREC 2009 Complaint J requests (the actual scandal) against the TREC 2010 Complaint K requests (an
oil-spill fact pattern laid over the same mailbox), and the Complaint J requests under TREC's pseudonym against the same requests with the company named.</p>
<h3>5.1 M0 · Matter identification</h3>
<p>The model sees ~2,500 characters of the TREC complaint — written to be fictional: "Volteron Corp." with Enron's exact class period, prepay transactions and
FAS 140; the "Bleak Horizon" oil spill — or a short sketch of a matter with every proper noun removed, and is asked which real company or case it is modelled on.
A hit names the real matter (keyword match against answer keys). For Veridian the correct answer is "no real matter"; we record which real template it is mapped
to (DePuy ASR, Zimmer, Stryker…), since a synthetic matter built on a famous archetype inherits some of the archetype's knowledge.</p>
<h3>5.2 M1 · Matter recall</h3>
<p>"Describe {{matter}}: parties, key allegations, key people, main events with dates, outcome." The answer is graded against a hand-written checklist of 16–20
facts in five categories, matched as whole words. Each fact is flagged as <em>in context</em> if the study's task context already states it (reciting it is not an
advantage) or <em>beyond context</em>; we report both shares. Veridian is asked under its full fictional caption; the right answer is "I do not know this matter".</p>
<h3>5.3 M2 · Evidence prior</h3>
<p>Given exactly what the study gives it — the matter context and one request — the model lists, as a review lead who has seen no documents, the 25 most specific
things it expects responsive documents to contain, each typed as person, organisation, code name, product, place, period or keyword. Scoring is against the
labelled corpus. Terms present in the prompt are discarded (<em>novel</em>). A <em>named</em> term is typed as an entity and written as a proper noun. A term is
<em>grounded</em> if it occurs in ≥ 2 judged documents for the request, and <em>discriminative</em> if it also occurs in ≥ 2 responsive documents at a <b>lift</b> of
≥ 2 — that is, at least twice as frequent among responsive documents as among all judged documents. A grounded, discriminative named term is a piece of case
knowledge that a search or classifier could use directly. Generic keywords are scored the same way and reported separately as a vocabulary baseline.</p>
<h3>5.4 M3 · Metadata-only relevance</h3>
<p>A balanced sample of responsive and non-responsive e-mails per request (20 + 20; 15 + 15 for Jeb Bush) is judged twice from headers alone: with Date, From,
To, Cc and Subject, and with Date and Subject only. The paired difference is what seeing the people added. Chance is 50% by construction; a lexical baseline (a
request-title word in the subject) shows what keyword matching achieves. Intervals on the paired difference are bootstrap 95% intervals over e-mails. Veridian's
fictional names make it the control for the people channel; for Enron the context states that Volteron is Enron, so the headers cannot also reveal the company.</p>

<h2 id="s6">6. The ladder</h2>
<p>Two anchors fix the ends of the matter scale but not its shape. We ran M0 and M1 on {n_rungs} further real matters from the last ninety years, chosen in
families that mirror the corpora: accounting and securities frauds (WorldCom, HealthSouth, Peregrine Systems, Equity Funding 1973, McKesson &amp; Robbins 1938);
opioid cases (Purdue, Insys, Rochester Drug Co-operative); e-mail in public life (the Clinton server, Bridgegate, the Sony Pictures hack); device mass torts
(Dalkon Shield, DePuy ASR, 3M Combat Arms earplugs, Bair Hugger); landmark disputes (Bhopal, Texaco v. Pennzoil, Dieselgate, Theranos, FTX); and two
<b>post-cutoff controls</b> — SEC actions filed in 2026 against Meyer Global Management and against the former officers of Near Intelligence — which are real but
cannot be in training data. Ladder rubrics have 10–18 facts; facts stated in the question itself (the names in "Describe the SEC's case against X") are excluded
from the share, so an answer that echoes the question earns nothing. An independent exposure proxy is recorded for every matter: the English Wikipedia article's
length, number of language editions and last-twelve-months pageviews (none for the fictional and post-cutoff matters; a company page, flagged, where no article
exists for the case).</p>

<h2 id="s7">7. Results: documents and people</h2>
<p>Three OpenAI models were probed on {RUN_DATE}: {', '.join(f"{N(m)} ({MODEL_META[m][1]})" for m in models)}. Anthropic and Gemini models were not probed (keys
unavailable); the runner is resumable. Per-model spend: {', '.join(f"{short(m)} ${summary['cost_usd'][m]:.2f}" for m in models)}.</p>
<p>Table 2 summarises the whole results section in one grid: three 0–100 scores per dataset and model — documents, case, overall — with the per-channel scores behind them. The split is the study's main finding in miniature: Enron sits near the floor on its documents and near the ceiling on its case. For the largest model the
order is {" → ".join(CORPUS_SHORT.get(d, d).split(" (")[0] for d in cmx["order"])}. The sections that follow give the channels one by one.</p>
{tbl_cmx}
<h3>7.1 The controls behave</h3>
<p>The floor is not zero and the ceiling is near the maximum of each scale, which is what makes the real corpora readable (Figures 1–2, Table 3). A plausible
in-genre continuation with no knowledge scores LCS-F1 {v('veridian', 'lcs_f_mean')} with a longest exact run of 2–3 words. {N(big)} reproduces the Federalist Papers
nearly verbatim (LCS-F1 {V[big]['canon']['lcs_f_mean']:.2f}; {_pct(V[big]['canon']['frac_run_ge15'])} of excerpts with a ≥ 15-word run) and Titanic CSV rows including
ticket numbers and fares ({_pct(V[big]['titanic']['frac_run_ge15'])}); recognises every framer including the obscure ones with zero false alarms (d′ {EG[big]['canon']['dprime']:.1f});
recites all 20 newsgroups; and recovers {lr('titanic').split(' / ')[-1]} of Titanic passengers' survival from id and name against a 50% ceiling. The scale gradient
(Luna &lt; Terra &lt; Sol) is stark on the anchors: Federalist LCS-F1 {v('canon', 'lcs_f_mean')}, Titanic labels {lr('titanic')}.</p>
{fig_v_lcs}
{fig_v_strip}
{tbl_v}
<h3>7.2 The e-mail corpora are near the floor on documents; CUAD is not</h3>
<p>Enron (LCS-F1 {v('enron', 'lcs_f_mean')}), Jeb Bush ({v('jebbush', 'lcs_f_mean')}), Mallinckrodt ({v('mnk', 'lcs_f_mean')}) and the post-cutoff Endo ({v('endo', 'lcs_f_mean')}) sit within a few hundredths of the floor;
{v_sig_txt()}. {v_runs_txt()} The long runs the unfiltered pool contained were chaff, now excluded with their reasons recorded: a repeated
error log reproduced for 60 words (degenerate repetition), a list of internet-famous one-liners (public text), a Federal Register notice reproduced for
34 words inside a Mallinckrodt e-mail (public text — memorised from its source, not from the mailbox) and a weekly sales-report template whose bullets
repeat from the prompt. {v_refusal_txt()} <b>CUAD</b> is different: LCS-F1
{v('cuad', 'lcs_f_mean')} (p &lt; 10⁻¹² against the floor for every model), with {_pct(V[big]['cuad']['frac_run_ge15'])} of excerpts reproduced for ≥ 15 consecutive
words by {N(big)}, including 37–40-word stretches of a specific IP licence with its party-specific defined terms intact. Boilerplate inflates the mean; the long
party-specific runs are not boilerplate.</p>
<h3>7.3 Entity knowledge: the famous cast, not the mailbox</h3>
<p>Free recall returns "unknown" for 80–100% of names on every real corpus (Table 4); the few hits are the scandal-famous executives (Dasovich, Belden, Whalley
for Enron; Florida politicians for Jeb Bush) and none at all for Mallinckrodt. Recognition finds more (Figures 3–5). d′ on Enron is {eg('enron', 'dprime', lambda x: f'{x:.1f}')},
Mallinckrodt {eg('mnk', 'dprime', lambda x: f'{x:.1f}')}, Jeb Bush {eg('jebbush', 'dprime', lambda x: f'{x:.1f}')}, Veridian {eg('veridian', 'dprime', lambda x: f'{x:.1f}')}, Endo {eg('endo', 'dprime', lambda x: f'{x:.1f}')}. The
tier breakdown shows what kind of knowledge this is: hits are concentrated in the top and middle tiers and the long tail is near 0% for Luna and Sol on every real
corpus. The notable case is Mallinckrodt, where {N(big)} recalls nobody but says "yes" to {_pct(EG[big]['mnk']['hit_rate'])} of staff names with
{_pct(EG[big]['mnk']['fa_rate'], 1)} false alarms (d′ {EG[big]['mnk']['dprime']:.1f}): real employees named in MDL filings and press coverage, recognised but not recalled.
Endo's cast, by contrast, is recognised by nobody ({eg('endo', 'hit_rate')} hits, d′ ≤ 0 for every model): the other opioid maker's employees were in the record the models read,
Endo's production was not.
{N(T) if T else 'The mid model'} at this decoding setting is a yes-sayer (false-alarm rate {_pct(EG[T]['enron']['fa_rate']) if T else '–'} on Enron foils), so its hit
rates are uninterpretable alone and its d′ is the number to read.</p>
{fig_e_d}
{fig_heat}
{fig_tiers}
{tbl_e}
<h3>7.4 Nobody knows the TREC topics; everybody knows CUAD's</h3>
<p>The 34 Total Recall topics are recovered {bk('trec2016')} by every model, the Legal 2010 topics {bk('legal10')}, the Legal 2009 topics {bk('legal09')}; the models
confabulate plausible Enron-scandal topics instead (California crisis, Andersen, LJM). The 41 CUAD clause categories are recited {bk('cuad')}; the 20 newsgroups
{bk('newsgroups20')}. No model confabulates about Veridian. The benchmark's <em>questions</em> are not in these models for the TREC-based arms; they are for CUAD (Table 5).</p>
{tbl_b}
<h3>7.5 No label leakage</h3>
<p>Label recall is at chance on every eDiscovery corpus — {lr('enron')} on Enron, {lr('jebbush')} on Jeb Bush, {lr('mnk')} on Mallinckrodt, {lr('endo')} on Endo, {lr('veridian')} on Veridian —
against {lr('titanic')} on Titanic (Figure 6, Table 6). The probe detects leakage when it exists, so its chance-level readings are informative, not a null instrument.</p>
{fig_l}
{tbl_l}

<h2 id="s8">8. Results: the case</h2>
<h3>8.1 M0 · The pseudonyms do not hold</h3>
<p>Every model decodes every real matter from its fact pattern (Table 7). Complaint K's "Bleak Horizon" is Deepwater Horizon for all three, with BP, Transocean and
Halliburton supplied unprompted; the Mallinckrodt, Endo, Jeb Bush and Microsoft sketches, which contain no proper noun, are named at once. Complaint J, TREC's
pseudonymised Enron, is identified as Enron by {', '.join(short(m) for m in models if MI[m]['enron']['hit'])}; {', '.join(short(m) for m in models if not MI[m]['enron']['hit']) or 'no model'}
names Reliant Energy — another Houston company caught up in the California crisis — reading the complaint's invented code name "RND7" as a disguised Reliant
strategy. Either way the pseudonym sends the reader to a real case. The fictional matter shows the complementary failure: {', '.join(short(m) for m in models if MI[m]['veridian']['templates'] and not any(w in (MI[m]['veridian']['first_line'] or '').lower() for w in ('composite', 'fabricat', 'no identifiable')))}
state confidently that Veridian is Zimmer Biomet (the sketch says Warsaw, Indiana, and that is where Zimmer Biomet is), while {N(big)} answers "no identifiable
real company; a composite" and lists the three litigations it is a composite of.</p>
{tbl_m0}
<h3>8.2 M1 · How much of the record is in the model</h3>
<p>Enron and Microsoft behave as a ceiling should: {mr('enron')} of the Enron checklist (beyond-context {mr('enron', 'share_beyond')}) and {mr('microsoft')} of
Microsoft's (Figures 7–8, Table 8). What the models add is exactly what the complaint does not say — Fastow, Skilling, Lay, Causey, Watkins, LJM and the Raptors,
Andersen, Dynegy, the 2006 convictions, Sarbanes-Oxley. The two Enron items every model misses are document shredding and the California trading schemes, the
operational facts behind TREC topics 204 and 205: the models know Enron as a securities fraud, and skip the parts of the record the requests target.
Mallinckrodt is known as a <em>procedural</em> story: {mr('mnk')} overall, {mr('mnk', 'share_beyond')} on beyond-context facts (the MDL, Judge Polster, SpecGx, the 2017
DEA settlement, the 2020 Chapter 11, the trust), with the operational allegations — Exalgo, suspicious-order monitoring, chargeback data, pill mills, quota — at
17% for every model. Endo, whose documents are post-cutoff, is nonetheless known better than Mallinckrodt by every model ({mr('endo')} overall, {mr('endo', 'share_beyond')}
beyond context): the Opana ER reformulation, the state attorneys general, the 2022 Chapter 11. Jeb Bush is the weakest real matter ({mr('jebbush')}) and the category grid says why: the <em>people</em> row is 0% for every model. Veridian:
all three models say they do not know the matter, in {_seq([MR[m]['veridian']['n_words'] for m in models], str)} words, without inventing a fact.</p>
{fig_m1}
{fig_m1c}
{tbl_m1}
<h3>8.3 M2 · Is the knowledge actionable?</h3>
<p>This probe turns exposure into something a classifier could use, and it produces the sharpest result in the study (Figures 9–12, Table 9). Under TREC's pseudonym
the models volunteer almost no real names for the Enron scandal requests — {ep('enron_j', 'n_novel_named_mean', lambda x: f'{x:.1f}')} novel named terms per request,
{ep('enron_j', 'n_discriminative_named_total')} discriminative in total across seven requests — and their notes say why ("I know only the supplied fictionalized
complaint summary"). Name the company and the same requests yield {ep('enron_j_named', 'n_novel_named_mean', lambda x: f'{x:.1f}')} named terms per request,
{ep('enron_j_named', 'grounded_rate_named', _pct)} of them grounded, and <b>{ep('enron_j_named', 'n_discriminative_named_total')} discriminative named terms</b>. For
{N(big)} they are the record of the case: {disc_terms('prepay_transactions')} for prepay; {disc_terms('fas140')} for FAS 140; {disc_terms('document_destruction')} —
the Andersen partners in the shredding — for document destruction; {disc_terms('financial_analysts')} for analyst contacts, each over-represented among responsive
documents by a factor of 2.7 to 11.7 (Table A1). The Complaint K requests on the same mailbox yield {ep('enron_k', 'n_discriminative_named_total')}: the knowledge is
specific to the case, not to the corpus. Mallinckrodt is low but not zero ({ep('mnk', 'n_discriminative_named_total')}; Endo {ep('endo', 'n_discriminative_named_total')}; {N(big)} names Xartemis XR, a Mallinckrodt
opioid the context does not mention, Broward County for the pill-mill request, and DEA's Office of Diversion Control for quota). Jeb Bush yields
{ep('jebbush', 'n_discriminative_named_total')} on a 600-document subset, led by real Florida officials (Stipanovich at the State Board of Administration,
Regier at DCF, Alan Levine at AHCA). Veridian gives the floor its number: {ep('veridian', 'n_discriminative_named_total')}, all domain institutions (FDA, the NJR and
AJRR registries). Generic keywords discriminate at {ep('veridian', 'discriminative_rate_generic', _pct)} on Veridian and {ep('enron_j_named', 'discriminative_rate_generic', _pct)}
on named Enron (Figure 13): that is vocabulary, and it is what a reviewer with no knowledge of the case brings.</p>
{fig_m2t}
{fig_m2c}
{fig_m2a}
{fig_m2b}
{fig_m2d}
{tbl_m2}
<p class="small">The request-by-request list of volunteered terms, with each model's own note on what it knew, is Table A1 in the appendix.</p>
<h3 id="m3">8.4 M3 · Knowing the people barely moves the metadata call</h3>
<p>Given the matter, the request and the subject line, the models already call responsiveness at {md('enron_j', 'acc_subject')} on the Enron scandal requests,
{md('mnk', 'acc_subject')} on Mallinckrodt, {md('endo', 'acc_subject')} on Endo and {md('jebbush', 'acc_subject')} on Jeb Bush, far above the lexical baseline of {_pct(MD[big]['by_set']['enron_k']['acc_lexical'])}–{_pct(MD[big]['by_set']['mnk']['acc_lexical'])}
(Figure 14, Table 10). Adding the sender and recipients changes accuracy by {md('enron_j', 'delta_people', _sd)} on Enron and {md('veridian', 'delta_people', _sd)} on Veridian; the only
paired differences whose 95% interval excludes zero are {sig_txt}. At the level of a relevance call made from metadata, knowing the people is worth almost nothing
once the subject is known, on the real corpora as on the fictional one. Two side findings: Veridian's subject-only accuracy ({md('veridian', 'acc_subject')}) is higher
than any real corpus's, which says the synthetic matter's subject lines are more diagnostic than real ones (a realism caveat for the main study); and per request,
where the people do help (Medicaid reform, financial forecasts, Rilya Wilson, prepay) the gain is 5–10 points on 30–40 e-mails, which is the scale of effect the
full-document ablation (§10) was powered to see.</p>
{jev_m3_par}
{fig_m3}
{tbl_m3}

<h2 id="s9">9. Results: the ladder</h2>
<p>Figure 15 orders the {n_rungs} real matters and the study's own matters by public footprint and shows, for each, how much of the fact checklist each model
recovered (M1) and whether it identified the matter from a de-identified sketch (M0); Figure 16 plots recall against footprint for the matters that have a
Wikipedia article, and Table 11 gives the numbers.</p>
{fig_lad}
{fig_lad2}
{_ladder_narrative(summary, models, lad) if lad.get('has') else ''}
{tbl_lad}

{effect_section}
{_bigthorium_paper_section()}
<h2 id="s11">11. Discussion</h2>
<h3>11.1 The unit of contamination</h3>
<p>For a text benchmark the unit of contamination is the document; for a legal review it is the matter. The two give different answers for Enron. Part I would
clear it: we found no evidence that an e-mail is reproduced, the correspondents beyond the famous few are unknown, the benchmark's topics are unknown, the labels are at chance.
That null is absence of evidence — 60 windows of a 46,000-document mailbox, one prompt form — but it is informative because the same probe fires on the anchors and
on CUAD, and it is consistent with what is known about memorisation: the Enron corpus is in The Pile, so its presence in open training data is likely, and
memorisation at this scale tracks how often a text is repeated rather than whether it is present at all [7]. Part II does
not clear it: the case is in the model nearly in full, is identified through TREC's pseudonym by two of three models (the third names Reliant, a company in the same scandal), and — once named — supplies dozens of real, label-discriminative search terms.
A model reviewing Enron e-mail for the prepay request is not a fresh reviewer; it is one who knows that Mahonia and Yosemite were the vehicles. Benchmarks built
on famous matters should be reported as such, and their results should not be the headline evidence for performance on a client's never-seen collection.</p>
{endo_par}
<h3>11.2 Exposure is not effect</h3>
{discussion_effect}
<h3>11.3 Pseudonymisation of the complaint is not a defence</h3>
<p>TREC's "Volteron" and "Bleak Horizon" were written to be fictional and are decoded by every model from the fact pattern; the ladder shows that a sketch with the
proper nouns removed identifies {n_real_ided} of {n_real_rungs} real matters for every model{ladder_miss_txt}. If a corpus is to be used as a clean test of a frontier model, the <em>documents</em> must be
renamed, not the pleadings — and even then the archetype may be recognised, as the Veridian-to-Zimmer mapping shows.</p>
<h3>11.4 Scale, obscurity and the cutoff</h3>
<p>Memorisation of documents grows with scale on the anchors, as expected [7], and so does knowledge of matters; but the ladder adds a shape. For the smaller models, how much of a
case is known tracks its public footprint (Spearman {corr_small_txt}); for the largest the correlation is not significant ({corr.get(big, {}).get('spearman', 0):+.2f}, p = {corr.get(big, {}).get('p', 1):.2f}, n = {corr.get(big, {}).get('n', 0)}),
consistent with it knowing a 1938 wholesaler fraud and a distributor with no Wikipedia article about as well as Theranos — though {corr.get(big, {}).get('n', 0)} matters is a small sample for the
contrast. Legal matters live in sources — DOJ and SEC releases, dockets, opinions, client alerts
— that are crawled thoroughly and read rarely. The practical rule for evaluation design is that at frontier scale "obscure" is not a defence; "after the cutoff" is.
The post-cutoff rungs are consistent with it: a September 2026 SEC action is unknown to all three models (two say so; the third names a case that does not exist), and a
company whose collapse was reported in December 2023 is recognised while its 2026 complaint is not.</p>
<h3>11.5 What this changes in the evaluation</h3>
<ol class="kf">
<li>Report CUAD with a two-channel contamination caveat (documents and benchmark) and do not use it for headline claims.</li>
<li>Treat Enron as a known case, not an unknown mailbox; report it as such, {changes_enron}</li>
<li>Weight conclusions toward the e-mail corpora and Veridian, with Veridian's two measured caveats: its archetype is recognised and its subject lines are easier than real ones.</li>
<li>Adopt Endo as the held-out benchmark: a real collection published after the cutoff, from a matter the models know, is the situation a client's review presents. Re-date the check as models update, and note that Endo's labels come from a single-vendor panel.</li>
<li>For future corpora, place the matter on the ladder before spending anything on classification; prefer post-cutoff productions, as Endo is, as real-world floors beside the synthetic one.</li>
{changes_r2}
</ol>

<h2 id="s12">12. Limitations</h2>
<ul>
<li><b>One vendor, three models.</b> The within-vendor scale gradient suggests the pattern holds elsewhere; that is an expectation, not a measurement.</li>
<li><b>Embedded public text</b> (government notices, news stories, licence banners, jokes) is memorised from its source and the verbatim probe cannot distinguish it from corpus memorisation. The pool screen removes what a small model recognises as public; what it misses is caught only by inspection of the long runs, which we did.</li>
<li><b>The document-level null is bounded.</b> Sixty windows per corpus, 60 words each, one prompt form, temperature 0. A model could hold a small number of documents from a large mailbox verbatim without a sample of this size finding them; what the probe supports is "no evidence of document-level memorisation", made informative by the fact that the same probe detects memorisation on the anchors and on CUAD.</li>
<li><b>CUAD's floor is not genre-matched.</b> Veridian is e-mail; legal drafting is more predictable than e-mail, so part of CUAD's gap above the floor may be genre rather than memorisation even after standard clauses and mirrored provisions are filtered out. The long party-specific runs cannot be explained that way. A post-cutoff EDGAR contract sample — contracts filed after the models' cutoffs, drawn and windowed like CUAD — is the control that would separate the two, and is the next addition to the battery.</li>
<li><b>Refusals.</b> {N(models[0])} declines to continue {_pct(V[models[0]]['veridian']['refusal_rate'])} of the fictional floor's e-mails and {_pct(V[models[0]]['endo']['refusal_rate'])} of Endo's as private, and {_pct(V[models[0]]['enron']['refusal_rate'])} of Enron's; the other models refuse nothing. That is a policy fact, reported as a rate; refusals are excluded from every verbatim statistic on both sides of the floor comparison. Scored as zeros they had masked the floor for that model, and an earlier reading of a small-model residual above the floor as a genre effect is withdrawn.</li>
<li><b>Keyword grading</b> throughout (benchmark lists, matter checklists) is conservative — a known fact phrased differently is a miss — so recall shares are lower bounds. One benchmark match ("204 — document destruction") is probably coincidence.</li>
<li><b>A sampling confound was caught and fixed</b> in the label probe: balancing across the corpus rather than within topic let topic prevalence masquerade as label knowledge (70% on Mallinckrodt from answering "relevant" to every broad issue). The report uses within-topic balancing and prints the topic-only ceiling.</li>
<li><b>Endo's labels</b> were produced by a three-OpenAI-model panel (the Anthropic and Gemini keys were absent when it was built), unlike Mallinckrodt's mixed-vendor panel; its contamination profile does not depend on the labels, but the L channel and any classification result on it do.</li>
<li><b>Jeb Bush</b> is available locally only as a 600-document subset, so its tiers are shallow and its M2/M3 samples small (15 + 15 per request).</li>
<li><b>Lift is relative to the judged set</b>, whose sampling (TREC's stratified draws) differs from the collection.</li>
<li><b>The footprint proxy is rough</b>: pageviews measure attention, not crawlability, and five lookups fall back to company pages (flagged).</li>
<li><b>The post-cutoff sketches carry their dates</b>, and the models cite the date as a reason to decline; a date-free variant would test whether they know what they do not know.</li>
{limitation_effect}
</ul>

<h2 id="s13">13. Conclusion</h2>
<p>We set out to learn whether the corpora used to evaluate LLMs on legal review are already inside the models. At the level of documents and people, we found no
evidence that the e-mail corpora are — on answered items they sit within a few hundredths of a floor set by a fictional corpus, under a probe that does detect
memorisation on the anchors — while CUAD sits above that floor in a way consistent with memorisation of republished contracts. At the level of the matter, Enron is inside the models nearly in full,
recognisable through a pseudonym and actionable as search terms once named, while Mallinckrodt is known as a settlement rather than as a set of e-mails and Jeb
Bush as a list of controversies without a cast. Knowing the people adds little to a call made from headers. A ladder of real matters identifies {n_real_ided} of {n_real_rungs} from a
nameless sketch for every model, graded by public footprint for the smaller models and not significantly for the largest, and only post-cutoff matters are unknown. Endo, a real production published after the cutoff, shows the two units
coming apart on one corpus: the matter known ({mr('endo')} of its record), the documents without signal, as the date predicts. The evidence points to matter-level exposure being common and
document-level exposure being rare for internal e-mail, and we {eff2['claim_short'].replace(" the LLMs'", '') if eff2 and eff2.get('claim_short') else 'could not detect a consequence of the former for review accuracy'}. The
cheap battery here places any corpus on that scale for a few dollars, and Endo is the held-out collection we recommend it be used beside. {conclusion_effect}</p>

<h2 id="refs">References</h2>
<ol class="refs">
<li>Sainz, O., Campos, J.A., García-Ferrero, I., Etxaniz, J., de Lacalle, O.L., Agirre, E. NLP evaluation in trouble: On the need to measure LLM data contamination for each benchmark. <em>Findings of EMNLP</em>, 2023.</li>
<li>Golchin, S., Surdeanu, M. Time travel in LLMs: Tracing data contamination in large language models. <em>ICLR</em>, 2024.</li>
<li>Oren, Y., Meister, N., Chatterji, N., Ladhak, F., Hashimoto, T. Proving test set contamination in black-box language models. <em>ICLR</em>, 2024.</li>
<li>Shi, W., Ajith, A., Xia, M., Huang, Y., Liu, D., Blevins, T., Chen, D., Zettlemoyer, L. Detecting pretraining data from large language models. <em>ICLR</em>, 2024.</li>
<li>Magar, I., Schwartz, R. Data contamination: From memorization to exploitation. <em>ACL</em>, 2022.</li>
<li>Carlini, N., Tramèr, F., Wallace, E., et al. Extracting training data from large language models. <em>USENIX Security</em>, 2021.</li>
<li>Carlini, N., Ippolito, D., Jagielski, M., Lee, K., Tramèr, F., Zhang, C. Quantifying memorization across neural language models. <em>ICLR</em>, 2023.</li>
<li>Bordt, S., Nori, H., Rodrigues, V., Nushi, B., Caruana, R. Elephants never forget: Memorization and learning of tabular data in large language models. <em>COLM</em>, 2024.</li>
<li>Klimt, B., Yang, Y. The Enron corpus: A new dataset for email classification research. <em>ECML</em>, 2004.</li>
<li>Hedin, B., Tomlinson, S., Baron, J.R., Oard, D.W. Overview of the TREC 2009 Legal Track. <em>TREC</em>, 2009.</li>
<li>Cormack, G.V., Grossman, M.R., Hedin, B., Oard, D.W. Overview of the TREC 2010 Legal Track. <em>TREC</em>, 2010.</li>
<li>Grossman, M.R., Cormack, G.V., Roegiest, A. TREC 2016 Total Recall Track overview. <em>TREC</em>, 2016.</li>
<li>Hendrycks, D., Burns, C., Chen, A., Ball, S. CUAD: An expert-annotated NLP dataset for legal contract review. <em>NeurIPS Datasets and Benchmarks</em>, 2021.</li>
<li>Grossman, M.R., Cormack, G.V. Technology-assisted review in e-discovery can be more effective and more efficient than exhaustive manual review. <em>Richmond Journal of Law &amp; Technology</em> 17(3), 2011.</li>
<li>Green, D.M., Swets, J.A. <em>Signal Detection Theory and Psychophysics</em>. Wiley, 1966.</li>
<li>Gao, L., Biderman, S., Black, S., et al. The Pile: An 800GB dataset of diverse text for language modeling. arXiv:2101.00027, 2020.</li>
<li>This repository. Pseudonymisation ablation: method, per-request tables, dose–response and leakage check. <code>results/ablation/ablation_report.html</code>, <code>results/ablation/REPORT.md</code>, <code>results/ablation/summary.json</code>.</li>
<li>This repository. Classifier-native contamination tests on Jev (code-name swap, bare token, minimal-edit label flip, paraphrase sensitivity, published vs unpublished labels): method, per-token tables and the T4 breakdown. <code>results/jev_probe/REPORT.md</code>, <code>results/jev_probe/summary.json</code>.</li>
<li>This repository. Pseudonymisation ablation, round 2: CUAD (renamed and paraphrased, with the finish-the-document memorisation check and the paraphrase fidelity judge) and Jeb Bush (matter vs control topics, public figures renamed). <code>results/ablation/round2/REPORT.md</code>, <code>results/ablation/round2/summary.json</code>, <code>design/07_ablation_round2.md</code>.</li>
<li>This repository. Generalisation checks A–D (knowledge-dependence, ranking stability, counterfactual conflicts, Veridian brief injection). <code>results/verify/REPORT.md</code>, <code>results/verify/summary.json</code>.</li>
</ol>

<h2 id="appx">Appendix: reproduction</h2>
<p>Code: <code>ediscovery_bench/contam/</code> (<code>build.py</code>, <code>matter.py</code>, <code>ladder.py</code>, <code>run.py</code>, <code>score.py</code>, <code>html.py</code>, <code>paper.py</code>).
Commands: <code>bench contam-build</code> (deterministic, seed 7; {sum(1 for _ in (RESULTS_DIR.parent.parent / 'data' / 'contam' / 'probes.jsonl').open()) if (RESULTS_DIR.parent.parent / 'data' / 'contam' / 'probes.jsonl').exists() else '—'} items),
<code>bench contam-run -m &lt;model&gt; -y</code> (resumable; per-item records in <code>results/contam/&lt;model&gt;.jsonl</code>), <code>bench contam-report</code>,
<code>bench contam-html</code>, <code>bench contam-paper</code>. Full per-probe tables and every model answer to the identification and recall probes are in
<code>results/contam/REPORT.md</code>; the complete report with methodology narrative is <code>results/contam/contamination_report.html</code>.
Total API spend for the three models: ${cost:.2f}.</p>
<h3>A.1 Evidence prior, request by request</h3>
{tbl_m2_terms}
</main></body></html>"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path


# ------------------------------------------------------------------------------------------------ the explainer

def build_explainer(summary: dict, out_path: Path = RESULTS_DIR / "explainer.html") -> Path:
    models = _models(summary)
    N = lambda m: MODEL_META[m][0]  # noqa: E731
    short = lambda m: MODEL_META[m][0].split()[-1]  # noqa: E731
    p1 = _part1(summary, models)
    p2 = _part2(summary, models)
    lad = _ladder(summary, models)
    V, EG, LR, MR, EP, MD = (summary["verbatim"], summary["entity_recog"], summary["label_recall"], summary["matter_recall"],
                             summary["evidence_prior"], summary["metadata_relevance"])
    big = models[-1]
    cost = sum(summary["cost_usd"].values())

    def seq(fn, fmt):
        return " / ".join(fmt(fn(m)) for m in models)
    corr = lad.get("corr", {})
    corr_txt = ", ".join(f"{short(m)} {c['spearman']:+.2f}" for m in models if (c := corr.get(m)))
    corr_small_txt = ", ".join(f"{short(m)} {c['spearman']:+.2f} (p = {c['p']:.3f})" for m in models[:-1] if (c := corr.get(m)))
    n_rungs = sum(1 for r in summary.get("ladder", {}).get("rungs", {}).values() if not r.get("study"))
    _rungs, _pm = summary.get("ladder", {}).get("rungs", {}), summary.get("ladder", {}).get("per_model", {})
    _real_rungs = [k for k, r in _rungs.items() if r.get("expected") not in ("none", "floor", "public-invented")]
    n_real_rungs = len(_real_rungs)
    n_real_ided = sum(1 for k in _real_rungs if all(_pm.get(m, {}).get(k, {}).get("id_hit") for m in models))
    _missed = [(k, m) for k in _real_rungs for m in models if not _pm.get(m, {}).get(k, {}).get("id_hit")]
    ladder_miss_txt = ("; the one miss is " + ", ".join(f"{short(m)} on {_rungs[k].get('label', k).split(' (')[0]}" for k, m in _missed)
                       + (" (it names Reliant Energy, a company in the same scandal)" if _missed and _missed[0][0] == "enron" else "")) if _missed else ""

    def step(n, title, body):
        return f'<div class="step"><div class="n">{n}</div><div><h3>{title}</h3>{body}</div></div>'

    eff = _effect(summary)
    eff2 = _effect2()
    ver = _verify()
    if eff:
        words = {1: "one", 2: "two", 3: "three", 4: "four"}
        r2_plain = ""
        if eff2:
            r2_plain = (f'<div class="analogy" style="margin-top:1em"><b>Then we did it two more ways.</b> On the contracts the models can partly recite, we rewrote every excerpt in different '
                        f'words (same parties, same numbers, same obligations) so the memorised wording was gone; on the Florida e-mails we renamed the Governor and the public figures and compared '
                        f'the topics about his governorship with topics on the same documents that are not; and on the fictional matter we did the opposite and <em>handed</em> the reviewer the case '
                        f'file.</div>' + eff2["plain"] + (ver["plain"] if ver else ""))
        step9 = step(9, "So does the knowledge actually change the calls?",
                     f'<div class="analogy"><b>Analogy.</b> Change the names on every exhibit and run the review again. A reviewer who was trading on who the people were should do worse '
                     f'the second time; one who was reading the documents should do the same.</div>'
                     + eff["plain"]
                     + f'<div class="howto"><b>How to read this chart.</b> {eff["plain_howto"]}</div>'
                     + eff["fig"] + r2_plain)
        concl4 = ((f"<li>Whether that knowledge raises a model’s review score was then measured directly, on {words.get(len(eff2['matters']), len(eff2['matters']))} matters and in "
                   f"{words.get(len(eff2['manips']), len(eff2['manips']))} ways: renaming every person and organisation in the Enron e-mails, renaming the public figures in the Florida e-mails, "
                   f"rewording the contracts the models can recite, and handing over the case file for the invented matter. For the three LLMs none of it changed the review score by more than "
                   f"{eff2['llm_bound']:.1f} points once the control is subtracted, and {eff2['interval_txt'].replace('every 95% interval includes zero', 'every interval includes zero')}. That is a bound, not a proof of no effect — the models still recognised Enron "
                   f"from the story in {eff['leak_share']} of the renamed documents — so the clean test remains a matter the models have not seen."
                   + (f" Jev did show one small dependence on the real names ({eff2['jev_short']}): the kind of familiarity a system with ordinary public knowledge of famous people would show, "
                      f"worth a few points on a famous-figure collection, and not by itself evidence that it was trained on the collection." if eff2.get("jev_short") else "") + "</li>")
                  if eff2 else
                  (f"<li>Whether that knowledge raises a model’s review score was then measured directly: renaming every person and organisation in the Enron e-mails moved F1 by "
                   f"{eff['seq_j']} points ({eff['sys_txt']}), a knowledge effect indistinguishable from zero for every system at this sample size. That bounds the effect of name-carried knowledge on one matter; "
                   f"it does not rule out smaller effects, other matters, or knowledge that survives renaming — the models still recognised the case from the story in {eff['leak_share']} of the renamed documents — "
                   f"so the clean test needs a matter the models have not seen.</li>"))
    else:
        step9 = ""
        concl4 = ("<li>Whether that knowledge actually raises a model's review score is the next experiment: classify the same Enron e-mails with and without every name consistently "
                  "replaced. These results say that is where to look.</li>")

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Does the model already know this case? A short guide to the contamination study</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{PAPER_CSS}</style></head>
<body><main class="paper">
<h1>Does the model already know this case?</h1>
<div class="authors">A short guide to the contamination study · {RUN_DATE} · companion to the full report and the paper</div>

<p>We are comparing Jev with large language models at deciding which documents are relevant to a legal request. The LLMs were trained on a large slice of
the public internet. Our test collections are public. So before trusting a score, we need to know: <b>has the model already seen this material — and does
that help it?</b> This guide walks from that question to the answer in eight steps, defining each term where it first appears.</p>

{step(1, "The question, made precise",
 '<p>A model can be helped by prior exposure in several different ways. We call any of them <b>contamination</b>: the test material, or knowledge that '
 'makes the test easier, was in the model’s <b>training data</b> (the text it learned from, which ends at a <b>cutoff date</b>). We split the question in two.</p>'
 '<ul><li><b>Does the model know the <em>documents</em>?</b> The e-mails themselves, the people who wrote them, the benchmark’s questions, the published answers.</li>'
 '<li><b>Does the model know the <em>case</em>?</b> Who the parties were, what was alleged, who did what, how it ended — the kind of knowledge a lawyer who followed the news would have, with or without ever seeing an e-mail.</li></ul>'
 '<p>The second question is the one specific to legal review, and it is the one a normal contamination test misses.</p>')}

{step(2, "The setup: five public corpora, one made up",
 f'<p>Four of the study’s six collections are real and old enough to be in training data: the <b>Enron</b> e-mails (public since 2003), the <b>Jeb Bush</b> '
 f'e-mails (2015), the <b>Mallinckrodt</b> opioid-litigation e-mails (2021–23) and the <b>CUAD</b> contracts (an NLP benchmark from 2021). The fifth, '
 f'<b>Endo</b>, is real but late: an opioid-litigation production published in 2024–26, after the models stopped learning, from a case that was in the news for years. '
 f'The sixth, <b>Veridian</b>, is a fictional hip-implant lawsuit we wrote in September 2026, with invented company, people and documents. No model can know it. '
 f'It is our <b>floor</b>: the score you get when you know nothing.</p>'
 f'<p>We also need a <b>ceiling</b> — material every model has certainly seen many times — so we know what "contaminated" looks like on each scale: the '
 f'Federalist Papers and Constitution, the Kaggle Titanic passenger list (a famous spreadsheet copied onto millions of websites), and for the case-level '
 f'tests, <em>U.S. v. Microsoft</em>.</p>'
 f'<p>Every test is run the same way on every collection, on three OpenAI models of increasing size ({", ".join(N(m) for m in models)}), and every number '
 f'is read as a position between the floor and the ceiling. The whole battery cost about ${cost:,.0f}.</p>')}

{step(3, "Testing for the documents (Part I)",
 '<p>Four quick tests, one per way the documents could be known:</p>'
 '<dl class="gloss">'
 '<dt>Verbatim</dt><dd>Show the model the first 150 words of a document; ask for the next 60. Score how much it reproduces exactly. <b>LCS-F1</b> is the overlap '
 'score we use (1.0 = word-perfect, ~0.15 = a plausible guess in the right style); we also count the longest run of consecutive words it gets right.</dd>'
 '<dt>People</dt><dd>Take 30 names from each mailbox — famous ones, middling ones and obscure ones. Ask "who is this?" (recall) and "was this person at '
 'Enron?" (recognition), the latter also for four wrong companies. <b>False alarms</b> — saying yes to the wrong company — tell us whether a "yes" means anything. '
 '<b>d′</b> ("d-prime") combines hits and false alarms into one number: 0 means the model cannot tell the right company from the wrong one; about 4.8 is perfect here.</dd>'
 '<dt>Benchmark</dt><dd>Ask the model to list the benchmark’s own questions and categories from memory.</dd>'
 '<dt>Labels</dt><dd>Give only a document’s ID number and ask whether it was judged relevant. We balance relevant and not-relevant within each topic so that '
 'guessing from the topic scores exactly 50%: anything above that is memorised answers.</dd>'
 '</dl>'
 '<p>Two statistics appear throughout. A <b>95% confidence interval</b> is the range of values consistent with the data; if it excludes a number (say 50%), the '
 'result is unlikely to be luck. A <b>p-value</b> is the probability of seeing a difference this large if there were really none; below 0.05 we call it significant.</p>')}

{step(4, "What the floor and ceiling look like",
 f'<p>The controls behave, which is what lets us read everything else. On the verbatim test, Veridian scores LCS-F1 {seq(lambda m: V[m]["veridian"]["lcs_f_mean"], lambda x: f"{x:.2f}")} '
 f'across the three models — the floor is not zero, because a good guess in the right style earns something. The largest model reproduces the Federalist Papers '
 f'at {V[big]["canon"]["lcs_f_mean"]:.2f} and copies Titanic rows, ticket numbers and all, in {_pct(V[big]["titanic"]["frac_run_ge15"])} of chunks. It recognises every one of the '
 f'framers of the Constitution with zero false alarms (d′ {EG[big]["canon"]["dprime"]:.1f}). And on the label test it guesses Titanic passengers’ survival from their row '
 f'and name {_pct(LR[big]["titanic"]["acc"])} of the time against a 50% ceiling. Bigger models memorise more: on every anchor the order is {" < ".join(short(m) for m in models)}.</p>'
 + legend(models) + p1["fig_v_lcs"])}

{step(5, "The real collections, at the document level",
 f'<p><b>The e-mail collections sit at the floor; we found no evidence of memorised e-mail.</b> Enron {seq(lambda m: V[m]["enron"]["lcs_f_mean"], lambda x: f"{x:.2f}")}, Jeb Bush {seq(lambda m: V[m]["jebbush"]["lcs_f_mean"], lambda x: f"{x:.2f}")}, '
 f'Mallinckrodt {seq(lambda m: V[m]["mnk"]["lcs_f_mean"], lambda x: f"{x:.2f}")}, Endo {seq(lambda m: V[m]["endo"]["lcs_f_mean"], lambda x: f"{x:.2f}")} — within a few hundredths of Veridian, on the e-mails the models agreed to continue. We read every long run by hand: they were a repeated '
 f'error message, a list of internet jokes, a government notice quoted inside an e-mail, and they are screened out. No e-mail body was reproduced in 60 windows per collection — which is absence of evidence, '
 f'made informative by the same test finding the Federalist Papers and the contracts. (The Enron e-mails are in public training sets, so the models have very likely seen them; what we do not find is memory of them, '
 f'which in the literature comes from repetition, not presence.) The models know the famous executives '
 f'(d′ {EG[big]["enron"]["dprime"]:.1f} on Enron for the largest model) and almost nobody else: the obscure-name tier is at 0%. Nobody can list the TREC benchmark’s '
 f'questions. Label guessing is at chance everywhere ({seq(lambda m: LR[m]["enron"]["acc"], _pct)} on Enron).</p>'
 f'<p><b>CUAD is the exception.</b> Its contracts are SEC filings and the benchmark is well known: LCS-F1 {seq(lambda m: V[m]["cuad"]["lcs_f_mean"], lambda x: f"{x:.2f}")}, '
 f'with the largest model reproducing 15 or more consecutive words in {_pct(V[big]["cuad"]["frac_run_ge15"])} of excerpts, and all 41 clause categories recited from memory. That is consistent with '
 f'memorisation of republished public contracts; one caveat is that our floor is e-mail, and legal drafting is more predictable than e-mail, so part of the gap may be the genre. A set of contracts filed after the models’ cutoff would settle it.</p>'
 + p1["fig_e_d"])}

{step(6, "Testing for the case (Part II)",
 '<p>Now the legal question. Four tests, each matching something a lawyer who knows the case would have:</p>'
 '<dl class="gloss">'
 '<dt>M0 · Recognise it</dt><dd>Show a description of the matter with every name removed or changed — including the TREC benchmark’s own <b>pseudonymised</b> '
 'complaints, which rename Enron "Volteron" — and ask which real case it is.</dd>'
 '<dt>M1 · Recall the record</dt><dd>"Describe the Enron scandal." Grade against a checklist of 16–20 facts: parties, allegations, people, events, outcome.</dd>'
 '<dt>M2 · Predict the evidence</dt><dd>Give the model only what it gets in the study — the matter and one request — and ask what it expects responsive documents to '
 'contain. Then check each named thing against the actual labelled documents. A term is <b>discriminative</b> if it really appears in responsive documents at least '
 'twice as often as in documents overall (<b>lift</b> ≥ 2). This is the test of whether the knowledge is <em>usable</em>.</dd>'
 '<dt>M3 · Read the headers</dt><dd>Judge relevance from an e-mail’s headers only, twice: with and without From/To/Cc. The difference is what knowing the people is worth.</dd>'
 '</dl>'
 '<p>Veridian is again the floor (the right answers are "no real case" and "I don’t know this matter"); <em>U.S. v. Microsoft</em> is the ceiling. Enron gives us '
 'two clean comparisons: its scandal requests against unrelated oil-spill requests on the same mailbox, and the pseudonym against the real name.</p>')}

{step(7, "What the case tests found",
 f'<p><b>The pseudonyms don’t hold.</b> Every model identifies the Deepwater Horizon complaint; "Volteron" is decoded as Enron by two of three (the third says Reliant Energy — '
 f'a real company in the same scandal). Two models even declare the fictional Veridian to be Zimmer Biomet, because the sketch says Warsaw, Indiana.</p>'
 f'<p><b>Enron is known like a textbook case.</b> {seq(lambda m: MR[m]["enron"]["share"], _pct)} of the checklist — the same as Microsoft '
 f'({seq(lambda m: MR[m]["microsoft"]["share"], _pct)}). Mallinckrodt is known as a settlement and a bankruptcy, not as a set of allegations ({seq(lambda m: MR[m]["mnk"]["share"], _pct)}); '
 f'Endo, whose e-mails were published after the cutoff, is known a little better ({seq(lambda m: MR[m]["endo"]["share"], _pct)}) — the case, not the documents. '
 f'Jeb Bush’s controversies are known; the people in his mailbox are not ({seq(lambda m: MR[m]["jebbush"]["share"], _pct)}, people 0%). All three models say they do not know Veridian.</p>'
 f'<p><b>The knowledge is usable — once the case is named.</b> Under TREC’s pseudonym the models offer {seq(lambda m: EP[m]["enron_j"]["n_discriminative_named_total"], str)} '
 f'discriminative real names for the Enron requests. Name the company and the same requests yield <b>{seq(lambda m: EP[m]["enron_j_named"]["n_discriminative_named_total"], str)}</b>: '
 f'the deal names, the special-purpose vehicles, the Andersen partners who did the shredding, each 3–12 times more common in responsive documents. The unrelated oil-spill '
 f'requests on the same mailbox yield {seq(lambda m: EP[m]["enron_k"]["n_discriminative_named_total"], str)}; Veridian yields {seq(lambda m: EP[m]["veridian"]["n_discriminative_named_total"], str)}.</p>'
 f'<p><b>But knowing the people adds almost nothing to a header-level call.</b> From the subject line alone the models are already at {seq(lambda m: MD[m]["by_set"]["enron_j"]["acc_subject"], _pct)} on Enron; '
 f'adding who sent and received the e-mail changes that by {seq(lambda m: MD[m]["by_set"]["enron_j"]["delta_people"], _sd)}. The knowledge is about what the documents <em>say</em>, '
 f'which a header does not show.</p>'
 + _fig_m2_totals(summary, models) + p2["fig_m3"])}

{step(8, "Putting the study's cases on a ladder of real ones",
 f'<p>A floor and a ceiling tell you the ends of the scale, not where "medium" is. So we ran the recognition and recall tests on {n_rungs} more real matters from the last ninety years — '
 f'frauds like WorldCom and a 1938 drug-wholesaler scandal, opioid cases like Purdue, e-mail scandals like the Clinton server, device cases like the Dalkon Shield — plus two SEC cases filed '
 f'in 2026, after the models’ training ended, as a <b>real-but-unseen</b> floor. For each we also recorded how much public attention it gets (Wikipedia pageviews).</p>'
 f'<p>Three things stand out. Nothing that was ever litigated in public comes out blank: even matters with no Wikipedia article are recalled at 80–100% by the larger models. '
 f'Fame predicts knowledge for the smaller models (rank correlation {corr_small_txt}) but not measurably for the largest ({corr.get(big, {}).get("spearman", 0):+.2f}, p = {corr.get(big, {}).get("p", 1):.2f}) — '
 f'at that scale, "obscure" looks like no protection; only "after the cutoff" is. The nameless sketches identified {n_real_ided} of {n_real_rungs} real matters for every model{ladder_miss_txt}. And the 2026 cases behave like Veridian: the models say they do not know them (one of them, asked to '
 f'identify the matter, confidently names a case that does not exist). Among real cases, Enron sits at the very top with Bhopal and the Clinton server; Mallinckrodt is the '
 f'least-known real matter on the whole ladder, with Endo just above it; Jeb Bush is in between. Endo is the study’s clearest case: the models know the matter, and its documents were '
 f'published after their training ended — the date is the proof, and the probes agree, showing no document-level signal — so it is the collection we recommend testing on from now on.</p>'
 + (lad["fig"] if lad.get("has") else ""))}

{step9}

<h2>The conclusion, in four sentences</h2>
<ol class="kf">
<li>At the level of documents and people, we found no evidence that the e-mail collections are inside the models — they score within a hair of a fictional corpus on a test that does catch memorised text — while CUAD scores above that floor, consistent with memorised public contracts.</li>
<li>At the level of the <em>case</em>, Enron is thoroughly inside the models, recognisable through a pseudonym and usable as search terms once named; Mallinckrodt and Jeb Bush much less so. Endo — a known case whose e-mails were published after the cutoff — shows the same split from the other side.</li>
<li>For legal review, then, the evidence points to the matter, not the document, as the unit of contamination; a test aimed at documents would have cleared Enron, and renaming the complaint is no defence.</li>
{concl4}
</ol>

<h2>Glossary</h2>
<dl class="gloss">
<dt>Training data / cutoff</dt><dd>The text a model learned from, and the date after which nothing is included.</dd>
<dt>Contamination</dt><dd>Test material, or knowledge that makes the test easier, being in the training data. <em>Exposure</em> = it is in there; <em>effect</em> = the score benefits.</dd>
<dt>Floor / ceiling</dt><dd>What a model scores knowing nothing (a fictional corpus) and knowing everything (famous texts), measured with the same test.</dd>
<dt>LCS-F1</dt><dd>Overlap between the model's continuation and the true text, based on the longest common subsequence of words; 1.0 is word-perfect.</dd>
<dt>Hit / false alarm / d′</dt><dd>Saying "yes" when the answer is yes / when it is no; d′ is the gap between the two expressed in standard-deviation units (0 = no discrimination).</dd>
<dt>Confidence interval</dt><dd>The range of values consistent with the data at a stated level (here 95%). Wilson intervals are used for proportions, bootstrap intervals for means and paired differences.</dd>
<dt>p-value</dt><dd>The probability of a result at least this extreme if there were truly no effect; below 0.05 is called significant.</dd>
<dt>Bootstrap</dt><dd>Re-sampling the data with replacement many times to see how much a statistic would vary.</dd>
<dt>Spearman rank correlation (ρ)</dt><dd>How well the ordering of one quantity predicts the ordering of another, from −1 to +1.</dd>
<dt>Pseudonymised</dt><dd>Real names replaced with invented ones; the facts are left intact.</dd>
<dt>Lift</dt><dd>How many times more often a term appears in responsive documents than in documents overall; ≥ 2 is our threshold for "discriminative".</dd>
<dt>MDL</dt><dd>Multidistrict litigation: many related federal lawsuits consolidated before one judge for pre-trial proceedings.</dd>
<dt>Bellwether</dt><dd>An early test trial in a mass tort, used to gauge how juries value the claims.</dd>
<dt>TREC</dt><dd>The Text REtrieval Conference, whose Legal and Total Recall tracks produced the Enron and Jeb Bush test collections and their relevance judgments.</dd>
</dl>
<p class="fignote">Full report: <code>results/contam/contamination_report.html</code>. Paper: <code>results/contam/paper.html</code>. Generated by <code>bench contam-paper</code>.</p>
</main></body></html>"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path
