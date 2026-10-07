"""The contamination report split in two, each with its own matrix at the top:

  report_documents.html — Part I: knowledge of the benchmark data (verbatim, entities, benchmark topics, labels).
  report_case.html      — Part II + the ladder: knowledge of the case (M0–M3, the ladder of real matters).

Both are assembled from the same pieces as contamination_report.html (html._main_parts), so figures, tables and narrative are identical;
only the framing, the navigation and the matrix at the top differ.
"""
from __future__ import annotations

import re
from pathlib import Path

from .html import CORPUS_SHORT, _composite, _effect, _endo_paragraph, _main_parts, legend
from .run import RESULTS_DIR


def _retitle(head: str, title: str) -> str:
    return re.sub(r"<title>.*?</title>", f"<title>{title}</title>", head, count=1)


def _nav(links: list[tuple[str, str]], part_label: str) -> str:
    return f'<nav><span class="navpart">{part_label}</span>' + "".join(f'<a href="#{a}">{t}</a>' for a, t in links) + "</nav>"


def build_documents_report(summary: dict, out_path: Path = RESULTS_DIR / "report_documents.html") -> Path:
    P = _main_parts(summary)
    models = P["models"]
    cmx = _composite(summary, models, kind="docs", m3_ref='<a href="report_case.html#m3">the case report, M3</a>',
                     native_ref='<a href="report_case.html#jevnative">the case report, classifier-native tests</a>')
    n = len(models)
    head = _retitle(P["head"], "Knowledge of the benchmark data · contamination report, Part I")
    nav = _nav([("composite", "Overview"), ("q", "1 Question"), ("channels", "2 Channels"), ("design", "3 Principles"), ("controls", "4 Controls"), ("probes", "5 Probes"),
                ("setup", "6 Setup"), ("spectrum", "7 Spectrum"), ("rv", "8 Verbatim"), ("re", "9 Entities"), ("rb", "10 Benchmark"), ("rl", "11 Labels"),
                ("profile", "12 Verdicts"), ("appendix", "Appendix")], "Part I · documents &amp; people")
    order = " → ".join(CORPUS_SHORT.get(d, d).split(" (")[0] for d in cmx["order"])
    e = _effect(summary)
    from .effect2 import effect2 as _effect2  # noqa: PLC0415
    e2 = _effect2()
    effect_line = (f' Whether the knowledge changes a relevance call is measured in the <a href="report_case.html#effect">effect section</a> of the case report: renaming every '
                   f'person and organisation changes F1 by {e["seq_j"]} points ({e["sys_txt"]}) on the Enron scandal requests, within the noise of renaming'
                   + (f'; <a href="report_case.html#effect2">round 2</a> finds the same for the LLMs on Jeb Bush and on CUAD, where paraphrasing away the memorised text changed F1 by '
                      f'≤ {e2["par_max"]:.1f} points' if e2 else "") + "." if e else "")
    header = f"""<header>
<h1>Do the models already know the benchmark data?</h1>
<p class="sub">Part I of the contamination probe: whether the <em>documents and people</em> of the study's corpora — the Enron, Jeb Bush, Mallinckrodt and Endo e-mails, the CUAD
contracts — are inside {n} models, through four channels (verbatim text, the people, the benchmark's own topics, its published labels), each read against a fictional floor
and saturated ceilings. The companion report, <a href="report_case.html">knowledge of the case</a>, asks whether the <em>legal matters</em> behind the corpora are inside the
models; the <a href="contamination_report.html">full report</a> has both.{effect_line}</p>
{nav}
</header>
<section id="overview">
<h2 class="sub2">Overview</h2>
<h3 id="composite">One documents score per dataset and model</h3>
<p>Each cell places a dataset between the fictional floor (0: the model knows nothing about it) and the saturated ceilings (100: the founding documents, the Titanic list),
averaged over the document-level channels it was probed on. For the largest model the order is {order}. The e-mail corpora are in the single digits to mid-teens; CUAD,
a public NLP benchmark built from SEC filings, is the one dataset the models have partly memorised. Endo, a real collection published after the models' training cutoff,
sits at the floor on every channel — the profile Veridian was written to imitate, on real documents.</p>
{legend(models)}
{cmx["fig"]}
<details><summary>Per-channel breakdown and how each channel is scaled</summary>{cmx["note"]}{cmx["tbl"]}</details>
</section>
"""
    doc = head + header + P["method"] + P["results"] + P["appendix"] + P["tail"]
    out_path.write_text(doc, encoding="utf-8")
    return out_path


def build_case_report(summary: dict, out_path: Path = RESULTS_DIR / "report_case.html") -> Path:
    P = _main_parts(summary)
    models = P["models"]
    cmx = _composite(summary, models, kind="case", m3_ref='<a href="#m3">the M3 section</a>', native_ref='<a href="#jevnative">§21</a>')
    n = len(models)
    head = _retitle(P["head"], "Knowledge of the case · contamination report, Part II")
    nav = _nav([("composite", "Overview"), ("legal", "13 Why the case matters"), ("mprobes", "14 Matter probes"), ("m0", "15 Identification"), ("m1", "16 Recall"),
                ("ladder", "17 The ladder"), ("m2", "18 Evidence prior"), ("m3", "19 Metadata effect"), ("effect", "20 Effect"), ("effect2", "20b Round 2"), ("verify", "20c Checks"),
                ("jevnative", "21 Classifier-native tests"),
                ("verdicts2", "22 Combined verdicts"), ("caveats", "23 Caveats"), ("next", "24 Next")], "Part II · the case")
    order = " → ".join(CORPUS_SHORT.get(d, d).split(" (")[0] for d in cmx["order"])
    header = f"""<header>
<h1>Do the models already know the case?</h1>
<p class="sub">Part II of the contamination probe: whether the <em>legal matters</em> behind the study's corpora — the Enron collapse, the Jeb Bush governorship, the
Mallinckrodt and Endo opioid litigations — are inside {n} models: recognised through a pseudonym, recalled as a record, usable as search terms, and whether knowing the people
changes a relevance call made from e-mail headers; then a ladder of real matters that places the study's cases among a century of litigation; and finally the
<a href="#effect">effect test</a> — the same documents classified with every name replaced. The companion report,
<a href="report_documents.html">knowledge of the benchmark data</a>, asks whether the <em>documents</em> are inside the models; the
<a href="contamination_report.html">full report</a> has both.</p>
{nav}
</header>
<section id="overview">
<h2 class="sub2">Overview</h2>
<h3 id="composite">One case score per dataset and model</h3>
<p>Each cell places a matter between the fictional floor (0: Veridian, which every model says it has never heard of) and the ceiling (100: <em>U.S. v. Microsoft</em>, and
for usable terms the richest request set observed), averaged over the three matter-level channels. For the largest model the order is {order}. The contrast with the
documents report is the study's main finding: the same Enron e-mails that sit near the floor on their text come from a case that sits near the ceiling. Endo shows the
same split from the other side: a case the models know, whose documents were published after their cutoff.</p>
{legend(models)}
{cmx["fig"]}
{_endo_paragraph(summary, models, link=' (<a href="#verdicts2">combined verdicts</a>, <a href="#ladder">ladder</a>)')}
<details><summary>Per-channel breakdown and how each channel is scaled</summary>{cmx["note"]}{cmx["tbl"]}</details>
</section>
"""
    doc = head + header + P["part2"] + P["closing"] + P["tail"]
    out_path.write_text(doc, encoding="utf-8")
    return out_path
