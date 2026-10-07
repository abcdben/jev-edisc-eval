"""Two shorter write-ups of the contamination probe, generated from results/contam/summary.json:

  report_short.html      — a compact study report (about a fifth of paper.html): question, design, results, meaning, limits.
  explainer_lawyer.html  — a plain-English guide for a lawyer with no data-science background. Every chart is introduced with
                           how to read it; every statistical term is defined where it appears; analogies carry the ideas.

Both reuse the SVG generators in html.py so the figures match the full report's.
"""
from __future__ import annotations

from pathlib import Path

from .effect import effect as _effect
from .effect2 import effect2 as _effect2
from .jevnative import jev_native as _jev_native
from .verify_summary import verify_summary as _verify

_WORDS = {1: "one", 2: "two", 3: "three", 4: "four"}
from .html import (CORPUS_SHORT, MODEL_META, SET_LABEL, SET_ORDER, SET_ROLE, _composite, _esc, _ladder, _part1, _part2, _pct, _sd, dotplot, legend, table)
from .paper import PAPER_CSS, RUN_DATE, _Fig, _models
from .run import RESULTS_DIR

SHORT_CSS = PAPER_CSS + """
.paper.short{max-width:900px}
.paper .lead{font-size:16px;color:var(--ink-2);margin:0 0 18px}
.box{background:var(--panel);border:1px solid var(--line);padding:12px 16px;margin:14px 0;font-size:14px}
.box b.t{display:block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);margin-bottom:6px}
.howto{border-left:3px solid #9fb6cf;padding:6px 12px;margin:10px 0 6px;color:var(--ink-2);font-size:13.5px;background:#f6f9fc}
.howto b{color:var(--ink)}
.analogy{border-left:3px solid #d9b56a;padding:6px 12px;margin:10px 0;color:var(--ink-2);font-size:13.5px;background:#fbf7ee}
.analogy b{color:var(--ink)}
.term{border-bottom:1px dotted var(--ink-3)}
.takeaway{border:1px solid var(--line);border-radius:6px;padding:12px 16px;margin:14px 0;background:#fff}
.takeaway b.t{display:block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);margin-bottom:6px}
.paper.guide h2{font-size:21px;margin-top:38px}
.paper.guide p,.paper.guide li{font-size:15px;line-height:1.55}
.paper.guide .pcap{font-size:13px}
.compact td,.compact th{font-size:12.5px;vertical-align:top}
.m0{table-layout:fixed;width:100%}.m0 th:first-child{width:26%}.m0 td,.m0 th,table.tbl.m0 tbody th{word-wrap:break-word;white-space:normal}
.paper .legend{margin:6px 0 14px}
"""


def _tri(models, fn, fmt=_pct):
    out = []
    for m in models:
        try:
            v = fn(m)
        except (KeyError, TypeError):
            v = None
        out.append("–" if v is None else fmt(v))
    return " / ".join(out)


def _first(s: str, n: int = 110) -> str:
    s = (s or "").replace("**", "").replace("*", "").strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _m0_table(summary, models, cls="tbl compact m0"):
    MI = summary["matter_id"]
    rows_def = [
        ("enron", "Enron, as TREC's pseudonymised complaint (\"Volteron Corp.\")", "Enron"),
        ("enron_k", "Enron mailbox, TREC's oil-spill complaint (\"Bleak Horizon\")", "a real oil-spill case (Deepwater Horizon)"),
        ("jebbush", "Jeb Bush governorship, sketch with all names removed", "Jeb Bush"),
        ("mnk", "Mallinckrodt opioid litigation, sketch with all names removed", "Mallinckrodt"),
        ("endo", "Endo opioid litigation, sketch with all names removed (post-cutoff corpus)", "Endo"),
        ("microsoft", "U.S. v. Microsoft, sketch with all names removed (ceiling)", "Microsoft"),
        ("veridian", "Veridian ApexHip, fictional matter, sketch with all names removed (floor)", "\"this is not a real case\""),
    ]
    rows = []
    for k, label, want in rows_def:
        cells = [label + f'<br><span class="small">right answer: {want}</span>']
        for m in models:
            r = MI[m].get(k)
            if not r:
                cells.append("–")
                continue
            ok = r["hit"] or (k == "veridian" and not r["templates"]) or (k == "veridian" and "no identifiable" in r["first_line"].lower())
            mark = "✓" if ok else "✗"
            cells.append(f"<b>{mark}</b> {_esc(_first(r['first_line'], 95))}")
        rows.append(cells)
    return table(["what the model was shown"] + [MODEL_META[m][0] for m in models], rows, cls=cls)


def _part1_table(summary, models):
    V, ER, EG, LR = summary["verbatim"], summary["entity_recall"], summary["entity_recog"], summary["label_recall"]
    corp = [("veridian", "Veridian (fictional) · floor"), ("jebbush", "Jeb Bush e-mails"), ("enron", "Enron e-mails"), ("mnk", "Mallinckrodt e-mails"),
            ("endo", "Endo opioid e-mails · post-cutoff"), ("cuad", "CUAD contracts"), ("canon", "Founding documents · ceiling"), ("titanic", "Titanic CSV · ceiling")]
    rows = []
    for c, lbl in corp:
        rows.append([lbl,
                     _tri(models, lambda m: V[m][c]["lcs_f_mean"], lambda v: f"{v:.2f}"),
                     _tri(models, lambda m: V[m][c]["frac_run_ge15"]),
                     _tri(models, lambda m: ER[m][c]["hit_rate"]),
                     _tri(models, lambda m: EG[m][c]["dprime"], lambda v: f"{v:.1f}"),
                     _tri(models, lambda m: LR[m][c]["acc"])])
    return table(["corpus", "verbatim overlap (LCS-F1)", "docs with ≥ 15-word exact run", "name recall", "name recognition d′", "label guess accuracy (chance 50%)"], rows, cls="tbl compact")


def _m2_totals_fig(summary, models):
    EP = summary["evidence_prior"]
    rows = [(st, {m: (EP[m][st]["n_discriminative_named_total"], None, None) for m in models if st in EP.get(m, {})}) for st in SET_ORDER]
    mx = max([v[0] for _, d in rows for v in d.values()] + [10])
    top = 10 * ((mx + 9) // 10)
    return dotplot(rows, models, 0, top, list(range(0, top + 1, 10)), lambda v: f"{v:.0f}",
                   "Case knowledge that would actually help find documents: useful named terms per request set", labels=SET_LABEL, roles=SET_ROLE, label_w=300, width=700)


def _common(summary):
    models = _models(summary)
    V, ER, EG, LR, BK = summary["verbatim"], summary["entity_recall"], summary["entity_recog"], summary["label_recall"], summary["bench_knowledge"]
    MI, MR, EP, MD = summary["matter_id"], summary["matter_recall"], summary["evidence_prior"], summary["metadata_relevance"]
    L = summary.get("ladder", {})
    pm = L.get("per_model", {})
    rungs = L.get("rungs", {})
    big = models[-1]
    corr = L.get("corr_views_recall", {})
    real = [k for k, r in rungs.items() if not r.get("study") and k not in ("meyer", "near", "veridian", "microsoft")]
    study_real = [k for k in ("jebbush", "mnk", "endo") if k in rungs]
    n_real = len(real) + len(study_real)  # + Jeb Bush, Mallinckrodt and Endo as real study matters
    ided_all = sum(1 for k in real + study_real + ["near"] if all(pm[m][k]["id_hit"] for m in models))
    n_ided_pool = len(real) + len(study_real) + 1
    meyer_terra = next((pm[m]["meyer"]["id_first_line"] for m in models if pm[m]["meyer"]["id_first_line"] and not pm[m]["meyer"]["id_unknown"] and not pm[m]["meyer"]["id_hit"]), None)
    terra = next((m for m in models if "terra" in m), models[1] if len(models) > 1 else models[0])
    # calibrated phrases shared by both pages: correlation with its significance, the one ladder miss, the refusal rates behind the answered-only verbatim numbers
    short = lambda m: MODEL_META[m][0].split()[-1]  # noqa: E731
    corr_txt = ", ".join(f"{short(m)} {corr[m]['spearman']:+.2f} ({'p = ' + format(corr[m]['p'], '.3f') if corr[m]['p'] < 0.05 else 'not significant, p = ' + format(corr[m]['p'], '.2f')})"
                         for m in models if m in corr)
    enron_miss = [short(m) for m in models if not MI[m].get("enron", {}).get("hit")]
    miss_txt = (f" (the one miss across the study's {n_ided_pool + 1} real matters is {', '.join(enron_miss)} reading TREC's pseudonymised Enron complaint as Reliant Energy, "
                f"a company in the same scandal)") if enron_miss else ""
    luna = models[0]
    refusal_txt = (f"{short(luna)} declined to continue {_pct(V[luna]['veridian']['refusal_rate'])} of the fictional floor's e-mails and {_pct(V[luna]['endo']['refusal_rate'])} of Endo's as "
                   f"\"private\" ({_pct(V[luna]['enron']['refusal_rate'])} of Enron's); refusals are excluded from every verbatim number on both sides and reported as that rate.")
    return dict(models=models, V=V, ER=ER, EG=EG, LR=LR, BK=BK, MI=MI, MR=MR, EP=EP, MD=MD, L=L, pm=pm, rungs=rungs, big=big, corr=corr,
                n_real=n_real, study_real=study_real, ided_all=ided_all, n_ided_pool=n_ided_pool, meyer_terra=meyer_terra, terra=terra,
                corr_txt=corr_txt, miss_txt=miss_txt, refusal_txt=refusal_txt, cost=sum(summary["cost_usd"].values()))


# ------------------------------------------------------------------------------------------------ the short report

def build_short_report(summary: dict, out_path: Path = RESULTS_DIR / "report_short.html") -> Path:
    c = _common(summary)
    models, V, ER, EG, LR, MR, EP, MD, pm, big = (c[k] for k in ("models", "V", "ER", "EG", "LR", "MR", "EP", "MD", "pm", "big"))
    short = lambda m: MODEL_META[m][0].split()[-1]  # noqa: E731
    tri = lambda fn, fmt=_pct: _tri(models, fn, fmt)  # noqa: E731
    F = _Fig()
    p1 = _part1(summary, models)
    p2 = _part2(summary, models)
    lad = _ladder(summary, models)
    corr_txt, miss_txt, refusal_txt = c["corr_txt"], c["miss_txt"], c["refusal_txt"]

    fig_v = F.fig(p1["fig_v_lcs"], "Verbatim recall. Shown the first ~150 words of a document, the model writes the next 60; the score is the word overlap with the true "
                  "continuation (LCS-F1: 1.0 = word-perfect). Bars are 95% bootstrap confidence intervals over 60 documents per corpus.")
    fig_e = F.fig(p1["fig_e_d"], "Knowledge of the people. Thirty names from each mailbox were each paired with their true organisation and with four wrong ones. "
                  "d′ is the gap between the 'yes' rate on true pairings and on wrong ones, in standard-deviation units; 0 means no discrimination.")
    fig_l = F.fig(p1["fig_l"], "Label memorisation. Given only a document identifier and the topic, guess the published relevance label; 100 pairs per corpus, "
                  "balanced within topic so the topic carries no information. Dashed line: chance. Titanic is the positive control.")
    fig_m1 = F.fig(p2["fig_m1"], "Knowledge of the case. Share of a 16–20 item fact checklist (parties, allegations, people, events, outcome) the model states when asked to "
                   "describe the matter by name. Veridian omitted: every model said it did not know it.")
    fig_m2 = F.fig(_m2_totals_fig(summary, models), "Actionable case knowledge. Before seeing any document, the model listed the 25 most specific things it expected responsive "
                   "documents to contain. A named term (person, organisation, code name, product, place) counts if it was not in the prompt, occurs in at least two judged "
                   "documents, and is at least twice as common among responsive documents as overall. Totals across the set's requests.")
    fig_m3 = F.fig(p2["fig_m3_llm"], "Does knowing the people change a header-level relevance call? Accuracy from Date + Subject (hollow) and from Date + From + To + Cc + Subject "
                   "(filled) on the same balanced e-mails; the arrow is what the names added. Grey tick: a keyword baseline. Dashed line: chance.")
    eff = _effect(summary)
    nat = _jev_native(summary)
    jev_line = ((f"Jev’s knowledge effect is indistinguishable from the LLMs’. The tests built for its own interface then gave the account to carry: "
                 f"{nat['overall']} {nat['t1_jev_line']} (<a href=\"{nat['href']}\">classifier-native report</a>.)") if nat and eff else
                (f"Jev’s result is the same as the LLMs’ overall, with one request (FAS 140, {eff['jev_fas']['lost']} positives lost on renaming) recorded as evidence to follow up on the "
                 f"vendor’s no-pre-training claim." if eff and eff.get("jev_fas") else ""))
    eff2 = _effect2()
    ver = _verify()
    if eff and eff2:
        n_m, n_x = _WORDS.get(len(eff2["matters"]), len(eff2["matters"])), _WORDS.get(len(eff2["manips"]), len(eff2["manips"]))
        jev_r2 = (f" Jev’s matter-topic scores on Jeb Bush did depend on the real names ({eff2['jev_short']}) where {'the LLMs’ did not' if not eff2.get('llm_excl_txt') else 'two of the three LLMs’ did not'} — a small familiarity effect, consistent with public-web "
                  f"knowledge of public figures and not by itself evidence of training on the collection; a Jev score on a famous-figure collection may run a few points high." if eff2.get("jev_short") else "")
        item_effect = (f"<li><b>Exposure is not effect — measured on {n_m} matters.</b> We reviewed the same documents twice under {n_x} manipulations: every person and organisation renamed "
                       f"(Enron; the public figures on Jeb Bush), the memorised text paraphrased away (CUAD, the one collection the models partly recite), and the case supplied in a brief "
                       f"(the fictional Veridian). For the LLMs, knowing the case {eff2['claim_verb']}: no knowledge effect beyond {eff2['llm_bound']:.1f} F1 points net of "
                       f"control, {eff2['interval_txt']}; on Enron F1 moved by {eff['seq_j']} points ({eff['sys_txt']}), on CUAD paraphrase changed it by ≤ {eff2['par_max']:.1f} points and no more "
                       f"on the best-remembered contracts"
                       + (f"; the {ver['kd_share']:.0f}% of Enron documents whose relevance needs outside knowledge of the case — where help would show — are where every system does worse" if ver else "") + ". "
                       f"The caveats: the models still recognised Enron from the fact pattern in {eff['leak_share']} of renamed documents, so the Enron number is a floor; {eff2['absent_txt'] or ''} "
                       f"{jev_line}{jev_r2} Full tables: <a href=\"{eff['href']}\">ablation report</a>, <a href=\"{eff2['href']}\">round 2</a>"
                       + (f", <a href=\"{ver['href']}\">generalisation checks</a>" if ver else "") + ".</li>")
        fig_effect = F.fig(eff["fig"], "The effect test, round 1. Change in F1 when every name in the documents is replaced (renamed − named, percentage points, 95% CI), on the Enron scandal "
                           "requests, the unrelated requests from the same mailbox, and the fictional Veridian; bottom row: scandal minus control, the effect of knowing the case.")
        fig_effect += F.fig(eff2["cuad_fig"], "Round 2, CUAD. Change in F1 under renaming and under paraphrase (perturbed − named, percentage points, 95% CI by contract); the Veridian row is the "
                            "cost of the same paraphrase on an unseen corpus, the last row the knowledge effect net of it.")
        fig_effect += F.fig(eff2["jeb_fig"], "Round 2, Jeb Bush. Change in F1 on the matter topics and on control topics on the same documents when the public figures are renamed; third row: "
                            "the knowledge effect (matter − control).")
    elif eff:
        item_effect = (f"<li><b>Exposure is not effect — measured.</b> We reviewed the same Enron documents with every person and organisation consistently renamed. F1 moved by "
                       f"{eff['seq_j']} points ({eff['sys_txt']}) on the scandal requests and the knowledge effect (scandal minus control requests) is within ±3 points for every system, "
                       f"no interval excluding zero; renaming itself flips {eff['flip_txt']} of labels. The caveat: the models still recognised Enron from the fact pattern in "
                       f"{eff['leak_share']} of renamed documents, so this bounds the name-carried effect on one matter at this sample size; it does not rule out smaller effects, other matters, or knowledge that survives renaming. {jev_line} "
                       f"Full tables: <a href=\"{eff['href']}\">ablation report</a>.</li>")
        fig_effect = F.fig(eff["fig"], "The effect test. Change in F1 when every name in the documents is replaced (renamed − named, percentage points, 95% CI), on the Enron scandal "
                           "requests, the unrelated requests from the same mailbox, and the fictional Veridian; bottom row: scandal minus control, the effect of knowing the case.")
    else:
        item_effect = ("<li><b>Exposure is not yet effect.</b> These probes show the knowledge exists and is usable; they do not show how many points it adds to a review score. The decisive "
                       "test is to review the same Enron documents with every name consistently replaced and compare.</li>")
        fig_effect = ""
    if eff2:
        limit_effect = (f"<li>The effect test bounds the LLMs' knowledge effect on {_WORDS.get(len(eff2['matters']), len(eff2['matters']))} matters under renaming, paraphrase and brief injection "
                        f"(≤ {eff2['llm_bound']:.1f} F1 points); it does not rule out smaller effects or knowledge that survives every manipulation. The Enron renaming is a floor (the case is recognised "
                        f"from the fact pattern); the CUAD paraphrase control is e-mail, not unseen contracts; {eff2['absent_txt'] or ''}</li>"
                        + (f"<li>{ver['b_caveat']}</li>" if ver else ""))
    else:
        limit_effect = "<li>The effect test bounds name-carried knowledge on one matter at one sample size; it does not rule out smaller effects, other matters, or knowledge that survives renaming.</li>"
    fig_lad = F.fig(lad["fig"], "The ladder of real matters, ordered by public footprint (12-month English-Wikipedia pageviews, grey bar, log scale). Dots: share of the fact "
                    "checklist recalled. Right: whether the model identified the matter from a sketch with every proper noun removed (filled = yes; hollow = named something "
                    "else; ? = said it could not tell). Shaded rows are the study's own matters and the Microsoft ceiling.") if lad.get("has") else ""
    fig_lad2 = F.fig(lad["fig2"], f"Public footprint against recall for matters with a Wikipedia article. Spearman rank correlation: {corr_txt}.") if lad.get("has") else ""

    tbl_corp = F.tbl(table(["corpus", "role", "public since", "how it could be in training data"], [
        ["Enron e-mails (TREC Legal 2009–10)", "study", "2003", "in standard web-scale training sets; two decades of research use"],
        ["Jeb Bush e-mails (TREC 2016)", "study", "2015", "posted on the web by the campaign; press coverage"],
        ["Mallinckrodt opioid e-mails", "study", "2021–23", "public archive behind a search interface; quoted in filings"],
        ["Endo opioid e-mails", 'study · <span class="role post-cutoff">post-cutoff</span>', "2024–26", "same archive, but a production published after the models' training cutoff; the Endo matter itself is public and old"],
        ["CUAD contracts", "study", "2021", "an NLP benchmark; the contracts are SEC filings"],
        ["Veridian ApexHip", '<span class="role floor">floor</span>', "written 2026", "fictional; cannot be in any training set"],
        ["Founding documents; Titanic CSV", '<span class="role ceiling">ceiling</span>', "1787; 2012", "among the most copied texts and datasets on the web"],
        ["U.S. v. Microsoft", '<span class="role ceiling">ceiling</span>', "1998", "famous case built on e-mail evidence"],
    ], cls="tbl compact"), "Corpora and anchors.")
    cmx = _composite(summary, models, m3_ref="§5", native_ref='<a href="contamination_report.html#jevnative">full report §21</a>')
    tbl_cmx = F.tbl(cmx["fig"] + f'<details><summary>Per-channel breakdown and scaling</summary>{cmx["note"]}{cmx["tbl"]}</details>',
                    "Contamination scores, dataset × model: position between the fictional floor (0) and the saturated ceilings (100), averaged over the document-level channels "
                    "(docs), the matter-level channels (case) and all channels (all).") if cmx.get("has") else ""
    tbl_p1 = F.tbl(_part1_table(summary, models), f"Document-level results, {' / '.join(short(m) for m in models)}. Each cell lists the three models in order of size.")
    tbl_m0 = F.tbl(_m0_table(summary, models), "Identifying the matter from a description with the names changed or removed. First line of each model's answer.")

    enron_disc = f"{tri(lambda m: EP[m]['enron_j']['n_discriminative_named_total'], str)} → {tri(lambda m: EP[m]['enron_j_named']['n_discriminative_named_total'], str)}"
    meyer_line = f" One model ({MODEL_META[c['terra']][0]}) instead invented a case: <i>{_esc(_first(c['meyer_terra'], 120))}</i>" if c["meyer_terra"] else ""

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Is the case inside the model? Short report</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{SHORT_CSS}</style></head>
<body><main class="paper short">
<h1>Is the case inside the model? A short report on training-data contamination in eDiscovery test collections</h1>
<div class="authors">JND eDiscovery · AI team — {RUN_DATE} · condensed from the full report</div>
<p class="lead">We tested whether three OpenAI language models already know the public document collections used to evaluate AI relevance review, and whether
what they know is the kind of thing that would make a relevance call easier. We found no evidence that the models have memorised the e-mail collections; the <em>cases</em> they know in detail; and {'we could not detect a consequence of that case knowledge for review accuracy' if not (eff2 and eff2.get('llm_excl_txt')) else f'the consequence of that case knowledge for review accuracy was at most {eff2[chr(108)+chr(108)+chr(109)+chr(95)+chr(98)+chr(111)+chr(117)+chr(110)+chr(100)]:.1f} F1 points'}.</p>

<h2>1. The question</h2>
<p>An evaluation of a language model on a public test collection is only informative if the model has not seen the answers. For legal review there are two ways it
could have: it may have absorbed the <b>documents</b> (the texts, the people, the published labels) during training, or it may know the <b>case</b> the documents
come from, the way anyone who followed the news knows what Enron did. The second kind of knowledge does not require having seen a single e-mail, and a test aimed at
documents will not detect it. We measured both, on five public collections and against a floor and a ceiling. One of the five, the Endo opioid e-mails, was published after the models' training
data ends: a real collection whose publication date rules it out of training, from a case they can know.</p>

<h2>2. Design</h2>
{tbl_corp}
<p><b>Anchors.</b> No free-text score has a natural zero: a model that knows nothing still writes a plausible continuation and still says "yes" to some names. Every
probe is therefore run identically on a fictional matter written in 2026 (<b>floor</b>: the score of knowing nothing) and on material every model has seen many
times (<b>ceiling</b>). A result is read as a position between the two. <b>Models.</b> GPT-5.6 Luna, Terra and Sol (small, medium, large), temperature 0,
reasoning off, the settings a review pipeline would use. <b>Cost.</b> ${c['cost']:.0f} for the whole battery across three models.</p>
{legend(models)}
<p><b>Part I, the documents.</b> Four probes: <b>V</b> verbatim recall (finish the document; the windows are filtered in two stages — rules, then a
small-model screen — so that boilerplate, public text copied into the corpus and low-information openings are not counted as tests; a model that declines to
continue "a private e-mail" is counted as a refusal, not as a miss, on the real corpora and the fictional floor alike); <b>E</b> knowledge of the people (free recall of 30 names per
mailbox, then recognition against true and wrong organisations); <b>B</b> knowledge of the benchmark (recite its topics or categories); <b>L</b> memorised
labels (guess the published relevance label from the document identifier alone, 50% = chance).</p>
<p><b>Part II, the case.</b> Four probes: <b>M0</b> identify the matter from a complaint with the names changed or a sketch with the names removed; <b>M1</b>
recall the record against a fact checklist; <b>M2</b> predict what responsive documents will contain, scored against the actual labels; <b>M3</b> judge relevance
from e-mail headers with and without the sender and recipients. Controls: Veridian (floor), <em>U.S. v. Microsoft</em> (ceiling), and two Enron contrasts —
the real scandal versus an invented oil-spill fact pattern on the same mailbox, and the complaint under its pseudonym versus with Enron named.</p>
<p><b>The ladder.</b> {c['n_real'] - len(c['study_real'])} further real matters from the last century, chosen in families that mirror the collections (accounting frauds, opioid cases,
e-mail scandals in public life, device mass torts, landmark disputes) plus two SEC cases filed in 2026, after the models' training cutoff. Each got M0 and M1.
Public footprint is measured by Wikipedia pageviews.</p>

<h2>3. Results: at a glance</h2>
<p>Three numbers per dataset and model, before the detail: how far the documents are inside the model, how far the case is, and the mean of the two kinds. The gap between the first two is the study's main finding. For the largest model the order is {" → ".join(CORPUS_SHORT.get(d, d).split(" (")[0] for d in cmx["order"])}:
CUAD scores on its documents, Enron on its case, and the fictional floor scores near zero as it should.</p>
{tbl_cmx}

<h2>4. Results: the documents</h2>
{fig_v}
<p>The four e-mail collections sit at the floor on verbatim recall: LCS-F1 {tri(lambda m: V[m]['enron']['lcs_f_mean'], lambda v: f"{v:.2f}")} on Enron,
{tri(lambda m: V[m]['jebbush']['lcs_f_mean'], lambda v: f"{v:.2f}")} on Jeb Bush, {tri(lambda m: V[m]['mnk']['lcs_f_mean'], lambda v: f"{v:.2f}")} on Mallinckrodt and
{tri(lambda m: V[m]['endo']['lcs_f_mean'], lambda v: f"{v:.2f}")} on Endo,
against {tri(lambda m: V[m]['veridian']['lcs_f_mean'], lambda v: f"{v:.2f}")} on the fictional corpus and {tri(lambda m: V[m]['canon']['lcs_f_mean'], lambda v: f"{v:.2f}")}
on the founding documents — indistinguishable from the floor on the e-mails the models agreed to continue, with no 15-word exact run surviving the chaff filter. This is
absence of evidence from 60 windows per collection, made informative by the same test finding the founding documents and the contracts; the Enron e-mails are in
public training sets, so presence in training is likely and it is <em>memory</em> of them that is not detectable. {refusal_txt} CUAD is different:
{tri(lambda m: V[m]['cuad']['lcs_f_mean'], lambda v: f"{v:.2f}")}, with {_pct(V[big]['cuad']['frac_run_ge15'])} of contracts producing an exact run of 15 or more
words for the largest model — consistent with memorisation of republished public contracts, with the caveat that the floor is e-mail and legal drafting is more predictable,
so part of the gap may be genre; a post-cutoff set of EDGAR contracts would separate the two. Memorisation also rises with model size on every corpus where there is any, as the literature predicts.</p>
{fig_e}
<p>The models can name almost nobody from the mailboxes ({tri(lambda m: ER[m]['enron']['hit_rate'])} of Enron names, {tri(lambda m: ER[m]['mnk']['hit_rate'])} of
Mallinckrodt names, versus {tri(lambda m: ER[m]['canon']['hit_rate'])} of the framers). Recognition is more sensitive: the largest model says "yes" to
{_pct(EG[big]['enron']['hit_rate'])} of Enron names and {_pct(EG[big]['mnk']['hit_rate'])} of Mallinckrodt names with their true organisation and to
{_pct(EG[big]['enron']['fa_rate'])} / {_pct(EG[big]['mnk']['fa_rate'], 1)} of wrong pairings, so it does recognise the famous few. On Endo, the post-cutoff collection,
it recognises {_pct(EG[big]['endo']['hit_rate'])} of names, the same as on the fictional corpus. The middle model says "yes" to most
pairings including wrong ones (false-alarm rate {_pct(EG[c['terra']]['enron']['fa_rate'])} on Enron), which d′ corrects for. Knowledge is confined to the top
prominence tier: the executives who were in the news, not the mailbox.</p>
{fig_l}
<p>No label leakage: accuracy is {tri(lambda m: LR[m]['enron']['acc'])} on Enron, {tri(lambda m: LR[m]['jebbush']['acc'])} on Jeb Bush,
{tri(lambda m: LR[m]['mnk']['acc'])} on Mallinckrodt, {tri(lambda m: LR[m]['endo']['acc'])} on Endo, all within the chance interval. The test has power: on Titanic it recovers a passenger's fate from the row id
and name at {tri(lambda m: LR[m]['titanic']['acc'])}. Nobody can recite the TREC topics (0 of 34, 0 of 4, at most 1 of 7); everyone recites all 41 CUAD categories.</p>
{tbl_p1}

<h2>5. Results: the case</h2>
{tbl_m0}
<p>Changing the names does not hide the case. TREC's "Volteron" complaint is read as Enron by two models (the third names Reliant Energy, a company in the same
scandal); the oil-spill complaint is read as Deepwater Horizon by all three; the de-identified sketches of Jeb Bush, Mallinckrodt, Endo and Microsoft are all identified.
For the fictional Veridian, two models confidently name a real company (Zimmer Biomet) as the matter it is "modelled on"; only the largest says there is no real case.</p>
{fig_m1}
<p>Enron is known like a textbook case: {tri(lambda m: MR[m]['enron']['share'])} of the checklist, the same as the Microsoft ceiling
({tri(lambda m: MR[m]['microsoft']['share'])}). Jeb Bush ({tri(lambda m: MR[m]['jebbush']['share'])}) and Mallinckrodt ({tri(lambda m: MR[m]['mnk']['share'])}) are
known as outlines; Mallinckrodt in particular is known as a bankruptcy and a settlement, not as the conduct alleged. Endo ({tri(lambda m: MR[m]['endo']['share'])}) is known
better than Mallinckrodt by every model although its documents, published after the cutoff, are at the floor on every document probe. All three models say they do not know Veridian.</p>
{fig_m2}
<p>This is the sharpest result. Under the pseudonym, the models volunteer almost no useful named terms for the Enron scandal requests
({tri(lambda m: EP[m]['enron_j']['n_discriminative_named_total'], str)}). Name the company and the same requests yield {enron_disc}: Raptor, LJM, Chewco, Fastow,
Arthur Andersen, Duncan, Temple, the special-purpose vehicles and the Andersen partners in the shredding, each present in the judged documents and over-represented
among the responsive ones. The unrelated oil-spill requests on the same mailbox yield {tri(lambda m: EP[m]['enron_k']['n_discriminative_named_total'], str)}, Veridian
{tri(lambda m: EP[m]['veridian']['n_discriminative_named_total'], str)}, Mallinckrodt {tri(lambda m: EP[m]['mnk']['n_discriminative_named_total'], str)}, Endo {tri(lambda m: EP[m]['endo']['n_discriminative_named_total'], str)}. Generic keywords
discriminate at a similar rate on every corpus; the difference is case knowledge, and on Enron it is usable as search terms before a single document is read.</p>
{fig_m3}
<p>Knowing the people changes little at the header level. From the subject line alone the models already call responsiveness at
{tri(lambda m: MD[m]['by_set']['enron_j']['acc_subject'])} on Enron and {tri(lambda m: MD[m]['by_set']['mnk']['acc_subject'])} on Mallinckrodt; adding From/To/Cc moves
that by {tri(lambda m: MD[m]['by_set']['enron_j']['delta_people'], _sd)} and {tri(lambda m: MD[m]['by_set']['mnk']['delta_people'], _sd)}. The one caveat runs the other
way: Veridian's subject lines are more diagnostic than any real corpus's ({tri(lambda m: MD[m]['by_set']['veridian']['acc_subject'])}), a realism warning for the
synthetic matter.</p>

<h2>6. Results: the ladder</h2>
{fig_lad}
{fig_lad2}
<p>All {c['ided_all']} real matters that predate the training cutoff are identified by every model from a sketch with the names removed, down to a 1938 accounting fraud and a regional
drug distributor with no Wikipedia article{miss_txt}. Recall is high across the board (Bhopal {tri(lambda m: pm[m]['bhopal']['share'])}; McKesson & Robbins
{tri(lambda m: pm[m]['mckesson_robbins']['share'])}); public footprint predicts it for the two smaller models and not significantly for the largest ({corr_txt}; {c['corr'][big]['n']} matters, a small sample for the contrast). The only matter the models do not know is the
one filed after their training data ends: Meyer (SEC, September 2026) scores {tri(lambda m: pm[m]['meyer']['share'])}.{meyer_line} Among real matters,
Mallinckrodt ({tri(lambda m: pm[m]['mnk']['share'])}) is the least known; Endo ({tri(lambda m: pm[m]['endo']['share'])}) sits just above it, and its opioid peers Teva
({tri(lambda m: pm[m]['teva']['share'])}) and JUUL ({tri(lambda m: pm[m]['juul']['share'])}), with public footprints of {c['rungs']['teva']['footprint']['views_12m']:,} and
{c['rungs']['juul']['footprint']['views_12m']:,} pageviews against Endo's {c['rungs']['endo']['footprint']['views_12m']:,} and Mallinckrodt's {c['rungs']['mnk']['footprint']['views_12m']:,},
are identified by every model and recalled near the Enron end of the scale.</p>

<h2>7. What it means</h2>
<ol class="kf">
<li><b>The evidence points to the matter, not the document, as the unit of contamination.</b> A document-level test finds nothing on the Enron e-mails; a matter-level test finds the case known nearly in full and the
knowledge convertible into discriminative search terms. For evaluating legal review, document-level checks are necessary and not sufficient.</li>
<li><b>Pseudonymising a complaint is no defence.</b> The fact pattern identified {c['ided_all']} of {c['n_ided_pool']} nameless sketches for every model; the names are redundant.</li>
<li><b>Scale appears to erase obscurity.</b> Every publicly litigated matter on our ladder is known in detail by the largest model, and only matters after the training cutoff are unknown. A
client's live matter is in that last category, which is the situation an evaluation should imitate.</li>
<li><b>Endo is that situation, on a real collection.</b> A production published in 2024–26 from a matter that is itself old and public: the models identify the case and recall
{tri(lambda m: MR[m]['endo']['share'])} of its record, yet on every document probe the collection sits at the fictional floor (verbatim
{tri(lambda m: V[m]['endo']['lcs_f_mean'], lambda v: f"{v:.2f}")}, name recall 0%, labels at chance) — no document-level signal, as its publication date predicts; the date is the proof and the probes are the check.
It is the clearest "known case, post-cutoff documents" profile in the study and shows from the other side what Enron showed: a matter can be in the model while its documents are not. We recommend Endo as the held-out
benchmark going forward, with one caveat on its gold rather than its profile: its relevance labels come from a panel of three OpenAI models (the Anthropic and Gemini keys were
absent), unlike Mallinckrodt's mixed panel.</li>
{item_effect}
</ol>
{fig_effect}

<h2>8. Limitations</h2>
<ul>
<li>Three models from one vendor; the fact checklists and ladder sketches are hand-written; the "named / discriminative" scoring is a rule, not a human judgment.</li>
<li>Wikipedia pageviews are a crude footprint; three ladder matters have no article and are plotted separately.</li>
<li>The post-cutoff sketches carry dates, which lets a model refuse on the date alone; a date-free variant would be a stricter test.</li>
<li>Veridian is one fictional matter built on a famous archetype (metal-on-metal hips), and inherits some of the archetype's knowledge.</li>
<li>The document-level result is a null from 60 windows per collection and one prompt form: "no evidence of memorisation", not proof of absence. CUAD's floor is e-mail rather than contracts; a post-cutoff EDGAR contract set is the missing control.</li>
{limit_effect}
</ul>
<p class="small">Full report with every probe, table and model answer: <code>results/contam/paper.html</code>, <code>results/contam/contamination_report.html</code>.
Plain-English guide: <code>results/contam/explainer_lawyer.html</code>. Generated by <code>bench contam-paper</code>.</p>
</main></body></html>"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path


# ------------------------------------------------------------------------------------------------ the lawyer's guide

def build_lawyer_guide(summary: dict, out_path: Path = RESULTS_DIR / "explainer_lawyer.html") -> Path:
    c = _common(summary)
    models, V, ER, EG, LR, MR, EP, MD, pm, big = (c[k] for k in ("models", "V", "ER", "EG", "LR", "MR", "EP", "MD", "pm", "big"))
    short = lambda m: MODEL_META[m][0].split()[-1]  # noqa: E731
    tri = lambda fn, fmt=_pct: _tri(models, fn, fmt)  # noqa: E731
    p1 = _part1(summary, models)
    p2 = _part2(summary, models)
    lad = _ladder(summary, models)
    names = " / ".join(short(m) for m in models)
    order_note = f"Throughout, numbers are given for the three models in order of size: {names}."

    def cap(html, text):
        return f'<div class="pfig"><div class="pcap">{text}</div>{html}</div>'

    def howto(text):
        return f'<div class="howto"><b>How to read this chart.</b> {text}</div>'

    def analogy(text):
        return f'<div class="analogy"><b>Analogy.</b> {text}</div>'

    def takeaway(text):
        return f'<div class="takeaway"><b class="t">What this tells us</b>{text}</div>'

    f2 = lambda v: f"{v:.2f}"  # noqa: E731
    eff = _effect(summary)
    eff2 = _effect2()
    ver = _verify()
    nat = _jev_native(summary)
    lawyer_jev = ((f"Jev, the classifier under evaluation, has the same profile as the language models: {nat['overall'][0].lower() + nat['overall'][1:]} "
                   f"{nat['t1_jev_line']} One request where its score fell when Enron’s off-books vehicles were renamed was followed up and is not a bare-name effect.") if nat else
                  "Jev came out the same as the language models, which is consistent with its vendor’s claim; one request where its score fell when Enron’s off-books vehicles were renamed is noted as a question to follow up.")
    if eff2 and eff2.get("jev_short"):
        lawyer_jev += (f" The one place Jev’s score did depend on the real names is the Florida e-mails: on the topics about Governor Bush’s administration its F1 fell {eff2['jev_short'].split(' on ')[0]} "
                       f"when the public figures were renamed, where the language models’ did not. That is the kind of small familiarity a system with ordinary public knowledge of famous people would show, "
                       f"worth a few points on a famous-figure collection; it is not by itself evidence that it was trained on the collection.")
    if eff and eff2:
        n_means = 8
        n_m, n_x = _WORDS.get(len(eff2["matters"]), len(eff2["matters"])), _WORDS.get(len(eff2["manips"]), len(eff2["manips"]))
        lawyer_effect = f"""<h2>7. So does the knowledge actually change the calls?</h2>
{analogy("Change the names on every exhibit, then run the review again. If the reviewer was trading on who the people were, the second pass should come out worse; if they were "
         "reading the documents, it should come out the same.")}
{eff["plain"]}
{howto(eff["plain_howto"])}
{cap(eff["fig"], "The effect test, round 1: change in F1 when every name was replaced, by request set and system; bottom row is the knowledge effect.")}
{analogy("Then do it two more ways. On the contracts the reviewer can partly recite, rewrite every page in different words (same parties, same numbers, same obligations) so the memorised wording is gone. "
         "On the Florida e-mails, rename the Governor and the public figures and compare the topics about his administration with topics on the same e-mails that are not. And on the invented matter, "
         "do the opposite: hand the reviewer the case file and see whether the calls change.")}
{eff2["plain"]}
{cap(eff2["cuad_fig"], "Round 2, the contracts: change in F1 when the parties and amounts were renamed and when the text was paraphrased; the Veridian row is what the same paraphrase costs on a collection nobody knows, and the last row is the difference.")}
{cap(eff2["jeb_fig"], "Round 2, the Florida e-mails: change in F1 on the topics about the Governor’s administration and on unrelated topics on the same e-mails when the public figures were renamed; third row is the difference.")}
{ver["plain"] if ver else ""}
{takeaway(f"For the language models, knowing the case {eff2['claim_verb'].replace('review accuracy', 'the review calls')} on {n_m} matters ({', '.join(eff2['matters'])}) under {n_x} manipulations — take the names away, take the memorised "
          f"wording away, hand over the case file: no knowledge effect beyond {eff2['llm_bound']:.1f} points of F1 net of control, {eff2['interval_txt']}. On the contracts, where the text really is memorised, "
          f"rewording changed F1 by at most {eff2['par_max']:.1f} points and no more on the best-remembered ones"
          + (f"; the few Enron e-mails ({ver['kd_share']:.0f}%) whose relevance needs outside knowledge of the case are where help would show, and every system did worse on them" if ver else "") + ". "
          f"It is still a bound, not a proof: the models recognised the Enron story in {eff['leak_share']} of the renamed documents, so that number is a floor. {eff2['absent_txt']} "
          f"The evidence is that the names are not the main channel and that, at the level of a relevance call, the models read the document rather than recall the case. {lawyer_jev}")}
"""
        lawyer_item5 = (f"<li><b>We measured what the knowledge is worth, on {n_m} matters and in {n_x} ways, and could not detect an effect for the language models — which bounds it without ruling it out.</b> "
                        f"Renaming every person and company in the Enron e-mails moved the scores by {eff['seq_j']} points ({eff['sys_txt']}); renaming the public figures in the Florida e-mails, rewording the memorised "
                        f"contracts and handing over the case file for the invented matter moved them by no more than {eff2['llm_bound']:.1f} points net of control. The models still recognised Enron from the story in "
                        f"{eff['leak_share']} of the renamed documents, so the Enron number is a floor; smaller effects and knowledge that survives every manipulation are not excluded, and the clean test is a real matter "
                        f"the models have never seen."
                        + (f" Jev’s one dependence on the real names ({eff2['jev_short']}) is a small familiarity effect to expect on famous-figure collections, not a contamination verdict." if eff2.get("jev_short") else "")
                        + "</li>")
    elif eff:
        n_means = 8
        lawyer_effect = f"""<h2>7. So does the knowledge actually change the calls?</h2>
{analogy("Change the names on every exhibit, then run the review again. If the reviewer was trading on who the people were, the second pass should come out worse; if they were "
         "reading the documents, it should come out the same.")}
{eff["plain"]}
{howto(eff["plain_howto"])}
{cap(eff["fig"], "The effect test: change in F1 when every name was replaced, by request set and system; bottom row is the knowledge effect.")}
{takeaway(f"We could not detect a change in the review calls from knowing the case: renaming moved F1 by at most {max(abs(100 * x['delta']) for x in eff['jk'].values()):.1f} points net of control for every system, and {eff['excl_txt']}. "
          f"But the test could only take the names away, not the story, and the models recognised the story in {eff['leak_share']} of the renamed documents; so this bounds the effect that works through "
          f"the names, on one matter, at this sample size — it does not rule out smaller effects, other matters, or knowledge that survives renaming. The evidence is that the names are not the main channel. {lawyer_jev}")}
"""
        lawyer_item5 = ("<li><b>We measured what the knowledge is worth through the names, and could not detect an effect — which bounds it, on one matter, without ruling it out.</b> Renaming every person and company "
                        f"in the Enron e-mails moved the scores by {eff['seq_j']} points ({eff['sys_txt']}), within the noise of the renaming itself — but the models still recognised the case "
                        f"from the story in {eff['leak_share']} of the renamed documents, so the names are evidently not the main channel and the effect we measured is a floor: smaller effects, other matters and "
                        "knowledge that survives renaming are not excluded. The clean test is a real matter the models have never seen.</li>")
    else:
        n_means = 7
        lawyer_effect = ""
        lawyer_item5 = ("<li><b>We have shown the knowledge exists; we have not yet measured how many points it is worth.</b> The next experiment is to review the same Enron e-mails with every "
                        "name consistently replaced and compare the scores.</li>")
    meyer_terra = c["meyer_terra"]
    terra_name = MODEL_META[c["terra"]][0]
    corr_txt, miss_txt, refusal_txt = c["corr_txt"], c["miss_txt"], c["refusal_txt"]

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Does the AI already know this case? A plain-English guide</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{SHORT_CSS}</style></head>
<body><main class="paper guide">
<h1>Does the AI already know this case?</h1>
<div class="authors">A plain-English guide to the contamination study · {RUN_DATE}</div>
<p class="lead">We are testing how well AI language models decide whether documents are relevant to a request. The documents we test them on are public: the Enron
e-mails, the Jeb Bush e-mails, the Mallinckrodt opioid e-mails, a set of public contracts, and the Endo opioid e-mails. Public means the AI may have read them while
it was being built — except the last, a collection published after the models stopped learning. This guide explains how we checked, what we found, and what it means for
trusting the test results. No background in statistics is assumed.</p>

<h2>1. The worry, in one picture</h2>
{analogy("Imagine testing a new associate by having them review documents from a famous case and comparing their calls with the court's. If the associate "
         "clerked on that case, their score tells you nothing about how they would do on your client's matter. There are two ways they could have an unfair "
         "advantage. They might have <b>seen the exact documents</b> before, the way a student might have seen the exam paper. Or they might <b>know the case</b> "
         "from the news, the way a juror who followed a trial on television knows who the villains were before any evidence is shown. The second does not require "
         "having seen a single document, and it is the one lawyers would worry about first.")}
<p>A language model learns from an enormous collection of text, most of it from the public internet, up to a fixed date called its <span class="term">training
cutoff</span>. Anything public before that date may be inside it. We call it <span class="term">contamination</span> when test material, or knowledge that makes
the test easier, is inside the model. The study measures both kinds: knowledge of the <b>documents</b> (Part I) and knowledge of the <b>case</b> (Part II).</p>

<h2>2. How you test something that cannot be cross-examined</h2>
<p>You cannot simply ask the model "have you seen this before?"; it will answer confidently either way. So we test it the way a tribunal tests a witness: with
questions whose answers we already know, and with control questions that calibrate the answers.</p>
<ul>
<li><b>The floor.</b> We wrote an entirely fictional lawsuit in September 2026, <i>Veridian ApexHip</i>, with invented company, people, documents and requests. The
model cannot have seen it. Whatever score it gets on Veridian is the score of <em>knowing nothing</em>, because even a model that knows nothing produces
plausible-sounding answers.</li>
<li><b>The ceiling.</b> We ran the same tests on material every model has certainly seen many times: the Federalist Papers and the Constitution, a famous public
spreadsheet (the Titanic passenger list), and for case knowledge <i>U.S. v. Microsoft</i>. That is the score of <em>knowing everything</em>.</li>
<li><b>The real collections</b> are read as a position between the two.</li>
<li><b>The late arrival.</b> One real collection, the Endo opioid e-mails, was published in 2024–26, after the models' training data ends. The models can know the
<em>case</em> (Endo's opioid litigation was in the news for years) but the documents post-date its training data. It should show the floor's profile on a real collection, and the probes check whether it does.</li>
</ul>
{analogy("A polygraph is calibrated by asking the subject questions where the truth is known (\"is your name John?\") before asking the ones that matter. The floor "
         "and ceiling are our calibration questions. A number on its own means little; a number that sits on the floor, or near the ceiling, means a lot.")}
<p>We tested three OpenAI models of increasing size, GPT-5.6 Luna, Terra and Sol; think of them as a junior, a mid-level and a senior. {order_note} The whole exercise cost
about ${c['cost']:.0f} in API fees. In every chart below the three models are drawn in these colours:</p>
{legend(models)}
<p>Two statistical terms recur. A <span class="term">95% confidence interval</span> is the range of values consistent with the data; if it excludes a value (say
50%), the result is unlikely to be luck. Something is <span class="term">statistically significant</span> when the chance of seeing it by luck alone is below 5%.</p>

<h2>3. Part I: has the model seen the documents?</h2>

<h3>Test 1 · Finish the document</h3>
<p>We show the model the first 150 words of a real document and ask it to write the next 60. Then we compare what it wrote with what the document actually says.
The score, <span class="term">LCS-F1</span>, is the share of words that match in the right order: 1.0 is word-perfect, and about 0.15 is what you get by writing
something plausible in the right style without knowing the text. Not every passage is a fair test: an e-mail that runs into a confidentiality footer, a forwarded
news story, or a table can be finished by anyone, so the passages are filtered first — by rule and then by a small model asked whether only someone who had seen
this collection could write the continuation — and only passages of original, internal text are scored.</p>
{analogy("Ask someone to recite the second verse of the national anthem. A person who knows it will get it word for word; a person who does not will produce "
         "something that scans and rhymes and is wrong. The score measures how much of the real verse came out.")}
{howto("Each row is a collection; each dot is one model; the horizontal bar through the dot is the 95% confidence interval. Further right means more of the real "
       "text came out. The fictional corpus (top) is the floor; the founding documents and the Titanic list (bottom) are the ceiling.")}
{cap(p1["fig_v_lcs"], "Finish-the-document test. Word overlap between the model's continuation and the real one, 60 documents per collection.")}
{takeaway(f"The four e-mail collections sit on the floor: Enron {tri(lambda m: V[m]['enron']['lcs_f_mean'], f2)}, Jeb Bush "
          f"{tri(lambda m: V[m]['jebbush']['lcs_f_mean'], f2)}, Mallinckrodt {tri(lambda m: V[m]['mnk']['lcs_f_mean'], f2)}, Endo {tri(lambda m: V[m]['endo']['lcs_f_mean'], f2)}, against "
          f"{tri(lambda m: V[m]['veridian']['lcs_f_mean'], f2)} for the fictional corpus and {tri(lambda m: V[m]['canon']['lcs_f_mean'], f2)} for the founding documents. "
          f"We found no evidence that the models have memorised the e-mails — an absence of evidence from 60 documents per collection, made informative by the same test finding the founding "
          f"documents and the contracts. The scores are over the e-mails each model agreed to continue: {refusal_txt} The Enron e-mails are in public training sets, so they were probably seen; what is "
          f"not detectable is memory of them. The contracts are the exception: {tri(lambda m: V[m]['cuad']['lcs_f_mean'], f2)}, and the largest model reproduces "
          f"15 or more consecutive words exactly in {_pct(V[big]['cuad']['frac_run_ge15'])} of them. Those contracts are public SEC filings and part of a well-known AI benchmark, so memorisation is the natural reading; "
          f"the caveat is that the floor is e-mail, and legal drafting is more predictable than e-mail, so a set of contracts filed after the models' cutoff would settle how much of the gap is memory. Every document's continuation, for all three models, "
          f"can be inspected side by side with the real text in <code>results/contam/verbatim_review.html</code>, with the filtered-out passages shown and labelled.")}

<h3>Test 2 · Do you know these people?</h3>
<p>We took thirty names from each mailbox, some famous, some middling, some obscure, and asked two things. First, "who is this person?", scored on whether the model
names the right organisation. Second, "was this person associated with [organisation]?", asked once with the true organisation and four times with wrong ones
drawn from the other collections.</p>
{analogy("At jury selection, you read out the witness list and ask whether anyone knows the names. A careful lawyer also slips in a few names that are not on "
         "the list, because some people will say yes to everything. The wrong pairings are our planted names: they tell us how often the model says yes when "
         "the answer is no.")}
{howto("Rows are where the names came from; columns are the organisation the model was asked about. Each cell is the percentage of 'yes' answers. If the model "
       "really knows the people, the cells on the diagonal (true pairings, outlined) should be dark and everything else light. A dark column means the model says "
       "yes to anyone paired with that organisation, which is guessing, not knowledge.")}
{cap(p1["fig_heat"], "Recognition test. Share of 'yes' answers for each combination of names (rows) and organisation asked about (columns).")}
{takeaway(f"Free recall is near zero: the models can name the organisation for {tri(lambda m: ER[m]['enron']['hit_rate'])} of the Enron names and "
          f"{tri(lambda m: ER[m]['mnk']['hit_rate'])} of the Mallinckrodt names, against {tri(lambda m: ER[m]['canon']['hit_rate'])} of the framers of the Constitution. "
          f"Recognition finds a little more: the largest model says yes to {_pct(EG[big]['enron']['hit_rate'])} of true Enron pairings and {_pct(EG[big]['enron']['fa_rate'])} of "
          f"wrong ones, so it does recognise the handful of executives who were in the news. The middle model says yes to almost everything (including "
          f"{_pct(EG[c['terra']]['enron']['fa_rate'])} of wrong Enron pairings), which is why the planted names matter. The knowledge is of the public story, not of the mailbox. "
          f"On Endo, the collection published after the cutoff, the largest model recognises {_pct(EG[big]['endo']['hit_rate'])} of the names, exactly as on the fictional one.")}

<h3>Test 3 · Do you know the exam questions?</h3>
<p>Each public collection comes with a published list of review topics (the "requests"). We asked the models to recite them from memory. Nobody can: 0 of the 34
Jeb Bush topics, 0 of 4 and at most 1 of 7 for the two Enron topic sets. Everyone recites all 41 categories of the contract benchmark. Asked about Veridian, every
model says it has never heard of it, which is correct.</p>

<h3>Test 4 · Do you know the answer key?</h3>
<p>The most direct form of cheating would be remembering the published answers. We gave the model only a document's identifier and the topic, and asked it to guess
the published relevance label. We arranged the pairs so that half are relevant and half are not within every topic, so guessing gives exactly 50%.</p>
{analogy("Guessing the verdict from the docket number alone. Anyone would be right half the time by chance; being right more often than that means they have seen "
         "the docket sheet.")}
{howto("Each dot is a model's accuracy; the dashed line is 50%, pure chance; the bars are confidence intervals. A dot whose bar does not cross the dashed line is "
       "significantly better than guessing. The Titanic row is a deliberate test of the test: the model is asked to guess whether a passenger survived from the row "
       "number and name, and that list is so widely copied that we expected it to succeed.")}
{cap(p1["fig_l"], "Answer-key test. Accuracy at guessing the published label from the document identifier alone; 100 documents per collection.")}
{takeaway(f"No leakage of the answer keys: {tri(lambda m: LR[m]['enron']['acc'])} on Enron, {tri(lambda m: LR[m]['jebbush']['acc'])} on Jeb Bush, "
          f"{tri(lambda m: LR[m]['mnk']['acc'])} on Mallinckrodt, {tri(lambda m: LR[m]['endo']['acc'])} on Endo, all within the range of chance. The test works: on Titanic the models score "
          f"{tri(lambda m: LR[m]['titanic']['acc'])}, because they have effectively memorised the passenger list.")}

<div class="box"><b class="t">Part I in one sentence</b>At the level of documents and people, the e-mail collections look like the fictional one; the models have not
memorised them. The contract collection is partly memorised.</div>

<h2>4. Part II: does the model know the case?</h2>
<p>This is the juror-who-watched-the-trial question. Four tests, each matching something a lawyer who knows the case would be able to do.</p>

<h3>Test 5 · Recognise the case with the names changed</h3>
<p>The organisers of the Enron test collection wrote fictional complaints so that reviewers would judge on the facts alleged, not on what they knew about Enron.
One renames the company "Volteron Corp." but keeps Enron's real class period, its prepay transactions and its accounting rules. Another lays an invented oil-spill
story over the same mailbox. We showed the models these complaints, and short descriptions of the other matters with every name removed, and asked: which real
company or case is this modelled on?</p>
{analogy("A juror is read a summary of the facts with the parties called A and B. If they say \"that's the Enron case\", renaming the parties achieved nothing.")}
{howto("One row per matter; one column per model; ✓ means the model named the right case (or, for the fictional Veridian, correctly said there is no real case).")}
{cap(_m0_table(summary, models), "Recognition from a description. First line of each model's answer.")}
{takeaway("Renaming does not hide the case. Two of three models read \"Volteron\" as Enron (the third names Reliant Energy, a company in the same scandal); all three "
          "read the oil-spill complaint as the Deepwater Horizon litigation; all three identify Jeb Bush, Mallinckrodt, Endo and Microsoft from sketches with no names in them. "
          "For the fictional Veridian, two models confidently name a real company it is \"modelled on\". That is a model doing what a witness should not: giving an "
          "answer rather than saying \"I do not know\".")}

<h3>Test 6 · Recall the record</h3>
<p>We asked each model to describe each matter by name, parties, allegations, people, events, outcome, and graded the answer against a checklist of 16 to 20 facts
we wrote in advance.</p>
{howto("Each row is a matter; each dot is the share of the checklist a model got right; further right is more. U.S. v. Microsoft is the ceiling: a case every "
       "model knows thoroughly. Veridian is absent because every model correctly said it had never heard of it.")}
{cap(p2["fig_m1"], "Recall of the record. Share of a fact checklist recovered when asked to describe the matter by name.")}
{takeaway(f"Enron is known like a textbook case: {tri(lambda m: MR[m]['enron']['share'])} of the checklist, the same as Microsoft "
          f"({tri(lambda m: MR[m]['microsoft']['share'])}). The models know the deal names, the special-purpose entities, the executives, the shredding, the convictions. "
          f"Jeb Bush ({tri(lambda m: MR[m]['jebbush']['share'])}) and Mallinckrodt ({tri(lambda m: MR[m]['mnk']['share'])}) are known in outline; Mallinckrodt is remembered as "
          f"a bankruptcy and a settlement, not for the conduct the complaints allege. Endo ({tri(lambda m: MR[m]['endo']['share'])}) is known better than Mallinckrodt by every "
          f"model, even though its e-mails, published after the cutoff, came out on the floor in every Part I test: the case is known, the documents are not.")}

<h3>Test 7 · Would that knowledge help find documents?</h3>
<p>Knowing the history is one thing; knowing it in a way that helps review is another. So we gave each model exactly what a reviewer gets, the case background and
one request, and asked: before you see any document, list the 25 most specific things you expect the relevant documents to contain. Then we checked the list
against the actual labelled documents. A named term (a person, company, code name, product or place) counts as <b>useful</b> if it was not already in the request,
it really appears in the documents, and it appears at least twice as often in the relevant documents as in documents generally. We call that last condition a
<span class="term">lift</span> of two or more.</p>
{analogy("A reviewer who has never seen the documents but knows the case will walk in and search for \"Raptor\", \"LJM\" and \"Fastow\" on day one. A reviewer who "
         "knows only what the request says will search for \"off-balance-sheet\" and \"debt\". Both are legitimate, but only the first is using knowledge from outside "
         "the record. The test counts how many such day-one search terms the model has.")}
{howto("Each row is a set of requests; each dot is the total number of useful named terms a model produced across that set. The two Enron rows for the scandal requests "
       "differ in only one way: in one the company is called \"Volteron\", in the other it is called Enron.")}
{cap(_m2_totals_fig(summary, models), "Useful day-one search terms. Named terms the model expected to find that are present in the documents and concentrated in the relevant ones.")}
{takeaway(f"This is the sharpest finding. With the company renamed, the Enron scandal requests draw {tri(lambda m: EP[m]['enron_j']['n_discriminative_named_total'], str)} "
          f"useful named terms. Name the company and the same requests draw {tri(lambda m: EP[m]['enron_j_named']['n_discriminative_named_total'], str)}: Raptor, LJM, Chewco, "
          f"Fastow, Arthur Andersen, the Andersen partners in the document shredding, each of which actually appears in the relevant e-mails more than in the rest. The "
          f"invented oil-spill requests on the same mailbox draw {tri(lambda m: EP[m]['enron_k']['n_discriminative_named_total'], str)}; the fictional Veridian "
          f"{tri(lambda m: EP[m]['veridian']['n_discriminative_named_total'], str)}; Mallinckrodt {tri(lambda m: EP[m]['mnk']['n_discriminative_named_total'], str)}. "
          f"On Enron, case knowledge is not just background: it converts directly into search terms that work.")}

<h3>Test 8 · Does knowing the people change a relevance call?</h3>
<p>The most review-like test. We took e-mails from each collection, half relevant and half not, and asked the model to judge relevance from the header alone, twice:
once from Date and Subject only, once with From, To and Cc added. If the model knows who the people are, the names should help.</p>
{analogy("Show a juror only the subject line of an e-mail, then show them the sender too. If the sender's name changes their mind about whether it matters, they "
         "know something about that person.")}
{howto("Each row is a set of requests. The hollow circle is accuracy from the subject line alone; the filled circle is accuracy with the names added; the arrow between "
       "them is what the names were worth. The grey tick is a simple keyword match, a baseline with no intelligence at all. The dashed line is 50%, chance.")}
{cap(p2["fig_m3_llm"], "Header-only relevance. Accuracy with and without the sender and recipients, on the same e-mails.")}
{takeaway(f"Very little. From the subject line alone the models already judge {tri(lambda m: MD[m]['by_set']['enron_j']['acc_subject'])} correctly on the Enron scandal requests "
          f"and {tri(lambda m: MD[m]['by_set']['mnk']['acc_subject'])} on Mallinckrodt; adding the people moves that by {tri(lambda m: MD[m]['by_set']['enron_j']['delta_people'], _sd)} "
          f"and {tri(lambda m: MD[m]['by_set']['mnk']['delta_people'], _sd)}. At the level of a quick header call, knowing who Andrew Fastow is adds almost nothing once you "
          f"can read the subject. One side finding: the fictional Veridian's subject lines are easier to call ({tri(lambda m: MD[m]['by_set']['veridian']['acc_subject'])}) "
          f"than any real collection's, which tells us our invented e-mails are a little too tidy.")}

<div class="box"><b class="t">Part II in one sentence</b>The models know the Enron case as thoroughly as any famous case, recognise it through a pseudonym, and can turn
that knowledge into working search terms; they know Jeb Bush and Mallinckrodt in outline; they know nothing about the fictional matter and say so (mostly).</div>

<h2>5. Where do these cases sit among real cases?</h2>
<p>Enron and Microsoft are extremes. To see where ordinary litigation falls, we ran the recognition and recall tests on {c['n_real'] - len(c['study_real'])} further real matters from the
last century, chosen to resemble our collections: accounting frauds from WorldCom back to a 1938 drug-wholesaler scandal, opioid cases from Purdue down to a
regional distributor, e-mail scandals such as the Clinton server and Bridgegate, device mass torts such as the Dalkon Shield, and landmark disputes from Bhopal to
FTX. We added two SEC cases filed in 2026, after the models' training cutoff: real cases that post-date the models' training data. We measured each matter's public footprint by
how often its Wikipedia article was viewed in the last year.</p>
{howto("One row per matter, most-viewed at the top. The grey bar is the Wikipedia footprint. The dots in the middle are how much of each matter's fact checklist the "
       "model recalled. On the right, a filled circle means the model identified the matter from a nameless sketch; a hollow one means it named something else; "
       "a question mark means it said it could not tell. Shaded rows are our own collections and the Microsoft ceiling.")}
{cap(lad["fig"], "The ladder of real matters, ordered by public footprint.") if lad.get("has") else ""}
{takeaway(f"Three things stand out. First, nothing publicly litigated on our ladder was obscure to these models: all {c['ided_all']} real matters that predate the training cutoff are identified by all three "
          f"from a nameless sketch, including a 1938 fraud and a distributor with no Wikipedia article{miss_txt}, and recall stays high down the ladder (Bhopal "
          f"{tri(lambda m: pm[m]['bhopal']['share'])}; McKesson & Robbins {tri(lambda m: pm[m]['mckesson_robbins']['share'])}). Fame predicts recall for the two smaller "
          f"models and not significantly for the largest (rank correlation {corr_txt}; +1 would mean fame perfectly predicts recall, 0 means no relationship; {c['corr'][big]['n']} matters is a small sample). Second, the only matter the models genuinely do "
          f"not know is the one filed after their training data ends: the September 2026 SEC case scores {tri(lambda m: pm[m]['meyer']['share'])}."
          + (f" {terra_name} did not say \"I don't know\"; it invented a case: <i>{_esc(_first(meyer_terra, 120))}</i>. That is the behaviour to watch for." if meyer_terra else "")
          + f" Third, among real matters Mallinckrodt ({tri(lambda m: pm[m]['mnk']['share'])}) is the least known, Endo ({tri(lambda m: pm[m]['endo']['share'])}) sits just above it "
          f"and Jeb Bush ({tri(lambda m: pm[m]['jebbush']['share'])}) in the middle. The two opioid cases that were bigger news, Teva ({tri(lambda m: pm[m]['teva']['share'])}) and "
          f"JUUL ({tri(lambda m: pm[m]['juul']['share'])}), are identified by every model and recalled almost as well as Enron — the family is known; Endo and Mallinckrodt are its quieter members.")}

<h2>6. The collection published after the models stopped learning</h2>
<p>Everything above says the danger is knowing the <em>case</em>, not having seen the <em>documents</em>. Endo lets us check that claim on a real collection. The Endo
opioid e-mails come from the same public archive as Mallinckrodt's, but this production was published in 2024–26, after the models' training cutoff. Endo's litigation,
on the other hand, is old news: Opana ER, the state attorneys general, the 2022 bankruptcy. So the models should know the case and should not know the documents.</p>
{analogy("A juror who followed the trial on television but has never seen the exhibits. They know who the parties are and what was alleged; show them a specific "
         "e-mail and they have never seen it before.")}
{takeaway(f"That is what we find. The models identify Endo from a nameless sketch and recall {tri(lambda m: MR[m]['endo']['share'])} of its record, more than for "
          f"Mallinckrodt. But on every document test the Endo e-mails score like the fictional collection: finish-the-document "
          f"{tri(lambda m: V[m]['endo']['lcs_f_mean'], f2)}, name recall 0%, name recognition {tri(lambda m: EG[m]['endo']['hit_rate'])}, answer-key guessing "
          f"{tri(lambda m: LR[m]['endo']['acc'])} — no document-level signal, as the publication date predicts; the date is the proof and the probes agree with it. Enron showed that a model can know a case "
          f"with no detectable memory of its e-mails; Endo shows the same profile from the other side, on a collection the date rules out of training. It is the collection we recommend testing on from now on. One caveat concerns its answer key rather than "
          f"the models: Endo's relevance labels were produced by a panel of three OpenAI models (the Anthropic and Gemini keys were absent when it was built), whereas "
          f"Mallinckrodt's panel mixed vendors.")}

{lawyer_effect}
<h2>{n_means}. What this means</h2>
<ol class="kf">
<li><b>We found no evidence that the e-mails themselves are memorised.</b> On every document-level test the Enron, Jeb Bush, Mallinckrodt and Endo documents, the people in them and the answer keys
look like the fictional collection — the same tests that do find the founding documents and the public contracts. It is an absence of evidence from 60 documents per collection, not a proof; the Enron e-mails are in public training sets, so they were probably seen, and what is not detectable is memory of them. The public contracts are the exception.</li>
<li><b>But the Enron case is thoroughly known,</b> and the knowledge is the useful kind: it produces search terms that find relevant documents. A good score on the
Enron collection may therefore be partly the score of a reviewer who already knows the case. Mallinckrodt and Jeb Bush are much less affected, and Mallinckrodt
is the closest thing we have to an unknown matter among public collections.</li>
<li><b>Renaming the parties is not a safeguard.</b> The fact pattern identified {c['ided_all']} of {c['n_ided_pool']} nameless sketches for every model{miss_txt}.</li>
<li><b>A real client matter is like the 2026 case,</b> not like Enron: filed after the cutoff, never public. That is the situation an evaluation should imitate, which
is why the fictional Veridian matter exists and why we would weight results on it and on Mallinckrodt more than results on Enron. Endo is the real-world version of
that situation — a known case whose documents post-date the models' training data, and show no document-level signal — and is the collection we recommend testing on going forward.</li>
{lawyer_item5}
</ol>

<h2>Glossary</h2>
<dl class="gloss">
<dt>Language model</dt><dd>An AI system trained to predict text by reading a very large body of writing. "Training" is that reading; the "cutoff" is the date after which nothing was read.</dd>
<dt>Contamination</dt><dd>Test material, or knowledge that makes the test easier, being inside the model from training.</dd>
<dt>Floor / ceiling</dt><dd>The score a model gets knowing nothing (our fictional case) and knowing everything (famous texts), measured with the same test. Real collections are read between them.</dd>
<dt>LCS-F1</dt><dd>A 0-to-1 score of how much of the real text the model's continuation reproduces, in order. 1.0 is word-perfect.</dd>
<dt>Hit / false alarm / d′</dt><dd>Saying "yes" when the answer is yes / when it is no. d′ ("d-prime") is the gap between the two; 0 means the model cannot tell real pairings from planted ones.</dd>
<dt>Confidence interval</dt><dd>The range of values consistent with the data (here at 95%). If it excludes a value, the result is unlikely to be luck.</dd>
<dt>Statistically significant</dt><dd>The probability of getting a result this strong by luck alone is below 5%.</dd>
<dt>Lift</dt><dd>How many times more often a term appears in the relevant documents than in documents overall. We count a term as useful at a lift of 2 or more.</dd>
<dt>Rank correlation</dt><dd>How well the ordering of one thing predicts the ordering of another, from −1 to +1. Used here for fame against recall.</dd>
<dt>Pseudonymised</dt><dd>Real names replaced with invented ones; the facts left intact.</dd>
<dt>Confabulation</dt><dd>A model producing a confident, specific, false answer instead of saying it does not know.</dd>
<dt>TREC</dt><dd>The Text REtrieval Conference, a long-running research programme whose Legal and Total Recall tracks produced the Enron and Jeb Bush test collections and their relevance judgments.</dd>
<dt>MDL</dt><dd>Multidistrict litigation: many related federal lawsuits consolidated before one judge for pre-trial proceedings.</dd>
</dl>
<p class="small">Short technical report: <code>results/contam/report_short.html</code>. Full report: <code>results/contam/paper.html</code>. Generated by <code>bench contam-paper</code>.</p>
</main></body></html>"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path
