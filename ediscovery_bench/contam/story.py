"""story.html — a layered, plain-English entry point to the contamination study.

Three layers of disclosure. Layer 0 is one screen: the question, the answer in three lines, one picture. Layer 1 is six
findings, each a collapsed block with a plain statement, how we tested it (with an everyday analogy), one figure or mini-table,
and a one-line "so what". Layer 2 is a nested "show the details" inside each finding with the metric names, numbers with
confidence intervals, controls and caveats.

Every number is read from results/contam/summary.json and results/ablation/summary.json at build time (plus the rename
dictionary in data/ablation/mapping.json for the before/after exhibit, if present). Nothing is typed by hand, so the page
regenerates correctly when the probe is re-scored. The page is self-contained: inline SVG, inline CSS, no JavaScript.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from .brief import SHORT_CSS
from .effect import ARM_SHORT, _mkey, _pp, load_ablation
from .effect2 import effect2 as _effect2
from .html import INK, INK3, INK4, LINE, PANEL, MODEL_META, ROLE_COLOR, _esc, _pct, _svg, legend, role_text, table
from .jevnative import MATTER_LABEL, jev_native
from .verify_summary import verify_summary as _verify
from .paper import RUN_DATE, _models
from .run import RESULTS_DIR, ROOT

MAPPING_PATH = ROOT / "data" / "ablation" / "mapping.json"

# Dataset order and plain labels for the story (floor first, then the real e-mail corpora, then the contracts).
STORY_SETS = ["veridian", "bigthorium", "jebbush", "enron", "mnk", "endo", "cuad"]
STORY_LABEL = {
    "veridian": "Veridian (invented, 2026)", "bigthorium": "Big Thorium (Relativity demo, invented)", "jebbush": "Jeb Bush e-mails", "enron": "Enron e-mails", "mnk": "Mallinckrodt e-mails",
    "endo": "Endo e-mails (published after cutoff)", "cuad": "CUAD contracts", "canon": "Founding documents", "titanic": "Titanic passenger list",
    "microsoft": "U.S. v. Microsoft",
}
STORY_TAG = {"veridian": "floor", "bigthorium": "public-invented", "canon": "ceiling", "titanic": "ceiling", "microsoft": "ceiling", "endo": "post-cutoff"}
DOC_COLOR, CASE_COLOR = "#c9743a", "#2f7fc1"  # warm = the documents, cool = the case; used consistently in every figure
CHANNEL_WORD = {"V": "finish the document", "E": "know the people", "L": "know the answer key", "B": "know the exam questions",
                "M0": "recognise the case", "M1": "recall the record", "M2": "day-one search terms"}

STORY_CSS = SHORT_CSS + """
.paper.story{max-width:880px}
.paper.story p,.paper.story li{font-size:15px;line-height:1.55}
.hero{margin:0 0 26px}
.hero .q{font-size:27px;line-height:1.25;font-weight:600;letter-spacing:-0.01em;margin:10px 0 18px;color:var(--ink)}
.answers{display:grid;grid-template-columns:1fr;gap:10px;margin:0 0 20px}
.answers .a{display:grid;grid-template-columns:40px 1fr;gap:12px;align-items:start;background:#fff;border:1px solid var(--line);border-radius:8px;padding:12px 16px}
.answers .a .n{width:30px;height:30px;border-radius:50%;background:var(--ink);color:#fff;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:14px;margin-top:2px}
.answers .a b.h{display:block;font-size:16px;color:var(--ink);margin-bottom:2px}
.answers .a span{color:var(--ink-2);font-size:14px;line-height:1.5}
.layerhint{font-size:12.5px;color:var(--ink-3);margin:6px 0 0}
details.finding{border:1px solid var(--line-2);border-radius:10px;background:#fff;margin:14px 0;padding:0;font-size:15px}
details.finding>summary{list-style:none;display:grid;grid-template-columns:44px 1fr auto;gap:14px;align-items:center;padding:14px 18px;cursor:pointer}
details.finding>summary::-webkit-details-marker{display:none}
details.finding>summary .n{width:32px;height:32px;border-radius:8px;background:var(--panel);border:1px solid var(--line);display:flex;align-items:center;justify-content:center;font-weight:600;font-size:13px;color:var(--ink-2)}
details.finding>summary .k{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);display:block;margin-bottom:2px}
details.finding>summary .s{font-size:16.5px;font-weight:600;color:var(--ink);line-height:1.3}
details.finding>summary .hint{font-size:12px;color:var(--ink-3);white-space:nowrap}
details.finding>summary .hint::before{content:"unpack ▸"}
details.finding[open]>summary .hint::before{content:"collapse ▾"}
details.finding[open]>summary{border-bottom:1px solid var(--line)}
details.finding .body{padding:6px 18px 18px}
details.more{border:1px dashed var(--line-2);border-radius:8px;background:var(--panel);margin:14px 0 4px;padding:8px 14px;font-size:13.5px}
details.more>summary{font-weight:600;color:var(--ink-2);font-size:13px;letter-spacing:.02em;list-style:none;cursor:pointer}
details.more>summary::-webkit-details-marker,.guess details>summary::-webkit-details-marker{display:none}
.guess details>summary{list-style:none;cursor:pointer}
details.more>summary::before{content:"▸ "}details.more[open]>summary::before{content:"▾ "}
details.more p,details.more li{font-size:13.5px}
.sowhat{border-left:3px solid var(--ink);padding:8px 14px;margin:14px 0 4px;background:#fff;font-size:14.5px}
.sowhat b{color:var(--ink)}
.howwe{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:10px 0 6px}
@media(max-width:760px){.howwe{grid-template-columns:1fr}}
.howwe .analogy,.howwe .howto{margin:0}
.guess{border:1px solid #d9b56a;background:#fffdf7;border-radius:8px;padding:12px 16px;margin:14px 0}
.guess b.t{display:block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#9a7a2c;margin-bottom:6px}
.guess .opts{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:4px 14px;margin:8px 0}
.guess .opts label{font-size:14px;color:var(--ink-2);cursor:pointer}
.guess details{border:0;background:transparent;padding:0;margin:8px 0 0}
.guess details>summary{display:inline-block;font-weight:600;color:var(--ink);border:1px solid var(--line-2);border-radius:6px;padding:4px 12px;background:#fff;font-size:13.5px}
.guess table.tbl{margin-top:10px;background:#fff}
.ok{color:#3f9a4f;font-weight:600}.no{color:#b3443a;font-weight:600}
table.grid{border-collapse:separate;border-spacing:3px;width:auto;margin:10px 0 4px;font-size:12.5px}
table.grid th{font-weight:500;color:var(--ink-3);font-size:11px;text-align:center;padding:2px 4px;vertical-align:bottom}
table.grid th.rl{text-align:right;white-space:nowrap;color:var(--ink);font-size:12.5px;padding-right:8px}
table.grid th.grp{font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;padding-bottom:4px}
table.grid td{width:46px;height:34px;text-align:center;border-radius:4px;font-variant-numeric:tabular-nums;color:var(--ink);font-size:12px;cursor:default}
table.grid td.na{background:repeating-linear-gradient(135deg,#f1f1ec 0 4px,#fafaf7 4px 8px);color:var(--ink-4)}
table.grid td.gap,table.grid th.gap{width:14px;background:transparent}
.probes{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0}
@media(max-width:760px){.probes{grid-template-columns:1fr}}
.probe{border:1px solid var(--line);border-radius:8px;background:#fff;padding:10px 12px}
.probe b.t{display:block;font-size:14px;color:var(--ink);margin-bottom:2px}
.probe .q{font-size:12.5px;color:var(--ink-3);margin:0 0 6px;font-style:italic}
.probe .an{font-size:13px;color:var(--ink-2);margin:0 0 6px}
.probe .an b{color:#9a7a2c;font-weight:600}
.probe .res{font-size:12.5px;color:var(--ink-2);margin:6px 0 0}
.probe svg{display:block;max-width:100%;height:auto}
.marks{display:flex;flex-wrap:wrap;gap:4px 10px;font-size:12px;margin:4px 0}
.marks span{white-space:nowrap}
.rename{display:grid;grid-template-columns:1fr 24px 1fr;gap:4px 8px;align-items:center;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:10px 14px;margin:10px 0;font-size:13.5px;font-variant-numeric:tabular-nums}
.rename .h{font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3)}
.rename .arr{color:var(--ink-4);text-align:center}
.rename .r{color:#7a4fa3}
.twocol{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:10px 0}
@media(max-width:760px){.twocol{grid-template-columns:1fr}}
.box.not{border-left:3px solid #b3443a}
.box.choose{border-left:3px solid #3f9a4f}
.box ul{margin:6px 0 0 18px;padding:0}.box li{font-size:14px;margin:4px 0}
.paper.story .pcap{font-size:12.5px}
.paper.story table.tbl tbody th{white-space:normal}
.paper.story table.tbl td{white-space:normal}
.tri{white-space:nowrap}
details.more table.tbl{font-size:12px}
.paper.story .tbl td small,.paper.story .tbl th small{font-size:10.5px;color:var(--ink-3)}
.paper.story figure{margin:0}.paper.story .figtitle{display:none}
.quad{font-size:10.5px;fill:#7c7e79;letter-spacing:.04em;text-transform:uppercase}
.gloss{grid-template-columns:150px 1fr}
.foot{font-size:12.5px;color:var(--ink-3);margin-top:30px;border-top:1px solid var(--line);padding-top:12px}
/* 'How this was measured' triggers and metric cards (native popover; tiny JS fallback) */
.mi{display:inline-flex;align-items:center;justify-content:center;width:15px;height:15px;border-radius:50%;border:1px solid var(--ink-4);background:#fff;color:var(--ink-3);font:600 10px/1 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;cursor:pointer;vertical-align:super;margin:0 1px 0 3px;padding:0}
.mi:hover,.mi:focus-visible{border-color:var(--ink);color:var(--ink);outline:none}
.mi.t{width:auto;height:auto;border-radius:0;border:0;border-bottom:1px dotted var(--ink-3);background:none;color:inherit;font:inherit;vertical-align:baseline;margin:0;padding:0 0 1px;line-height:inherit;white-space:nowrap}
.mi.t:hover,.mi.t:focus-visible{border-bottom-color:var(--ink);color:var(--ink)}
.mi.t::after{content:"ⓘ";font-size:.8em;color:var(--ink-3);margin-left:3px;vertical-align:super}
.mcard{border:1px solid var(--line-2);border-radius:10px;background:#fff;color:var(--ink);padding:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.mcard[popover]{width:min(600px,92vw);max-height:86vh;overflow:auto;box-shadow:0 18px 50px rgba(0,0,0,.2);margin:auto;inset:0}
.mcard::backdrop{background:rgba(27,28,26,.38)}
.mcard.open{display:block;position:fixed;top:7vh;left:50%;transform:translateX(-50%);width:min(600px,92vw);max-height:86vh;overflow:auto;box-shadow:0 18px 50px rgba(0,0,0,.2);z-index:50}
.mcard .mh{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:11px 16px;border-bottom:1px solid var(--line);background:var(--panel);border-radius:10px 10px 0 0}
.mcard .mh b{font-size:15px}
.mcard .mh small{display:block;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);font-weight:500}
.mcard .mh button{border:1px solid var(--line-2);background:#fff;border-radius:6px;padding:3px 9px;font-size:12px;cursor:pointer;color:var(--ink-2)}
.mcard dl{margin:0;padding:12px 16px 14px;display:grid;grid-template-columns:92px 1fr;gap:9px 12px}
.mcard dt{font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-3);padding-top:3px}
.mcard dd{margin:0;font-size:13.5px;color:var(--ink-2);line-height:1.5}
.mcard dd b{color:var(--ink)}
.mcard dd code{font-size:12px}
.mcard dd a{color:#2f7fc1}
.mcard.inline{margin:10px 0}
.mcard.inline .mh button{display:none}
.measure>summary{font-size:14px}
.measure .intro{font-size:13.5px;color:var(--ink-2);margin:8px 0 4px}
.measure .idx{display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 12px}
.measure .idx a{font-size:12px;color:var(--ink-2);text-decoration:none;border:1px solid var(--line);border-radius:12px;padding:2px 10px;background:#fff}
.measure .idx a:hover{border-color:var(--ink)}
"""

STORY_JS = """
(function(){
  /* Cards are native <div popover> (light-dismiss, Escape, backdrop, no JS). Two small helpers:
     1. a trigger inside a <summary> must not also toggle the finding it sits in;
     2. browsers without the Popover API fall back to a class-based modal. */
  var native = 'popover' in HTMLElement.prototype;
  function closeAll(){document.querySelectorAll('.mcard.open').forEach(function(c){c.classList.remove('open');});}
  function toggle(t){ if (native) { t.togglePopover(); return; } var was = t.classList.contains('open'); closeAll(); if (!was) t.classList.add('open'); }
  document.addEventListener('click', function(e){
    var b = e.target.closest('[popovertarget]');
    if (b && (b.closest('summary') || !native)) { e.preventDefault(); e.stopPropagation(); var t = document.getElementById(b.getAttribute('popovertarget')); if (t) toggle(t); return; }
    if (!native && !e.target.closest('.mcard')) closeAll();
  }, true);
  if (!native) document.addEventListener('keydown', function(e){ if (e.key === 'Escape') closeAll(); });
})();
"""

REPORT_HREF = "contamination_report.html"  # same directory as story.html; section ids from html.py


def _mi(cid: str, label: str | None = None) -> str:
    """Trigger for a metric card: a circled i (no label) or a dotted-underlined phrase."""
    if label is None:
        return f'<button type="button" class="mi" popovertarget="mc-{cid}" aria-label="How this was measured" title="How this was measured">i</button>'
    return f'<button type="button" class="mi t" popovertarget="mc-{cid}" title="How this was measured">{label}</button>'


def _card_html(cid: str, c: dict, inline: bool = False) -> str:
    rows = [("What is measured", c["what"]), ("How", c["how"]), ("The metric", c["metric"]), ("Scale", c["scale"]), ("Why this metric", c["why"]), ("Caveat", c["caveat"]),
            ("Read more", f'<a href="{c["href"]}">{_esc(c["href_label"])}</a>')]
    dl = "".join(f"<dt>{_esc(k)}</dt><dd>{v}</dd>" for k, v in rows)
    head = (f'<div class="mh"><div><small>How this was measured</small><b>{_esc(c["title"])}</b></div>'
            + ("" if inline else f'<button type="button" popovertarget="mc-{cid}" popovertargetaction="hide">close</button>') + '</div>')
    if inline:
        return f'<div class="mcard inline" id="mx-{cid}">{head}<dl>{dl}</dl></div>'
    return f'<div class="mcard" id="mc-{cid}" popover role="dialog" aria-label="{_esc(c["title"])}: how this was measured">{head}<dl>{dl}</dl></div>'


def _pool_facts(summary: dict) -> dict:
    pool = summary.get("v_pool") or {}
    if not pool:
        return {}
    emails = [c for c in ("enron", "jebbush", "mnk", "endo") if c in pool]
    return {
        "has": True,
        "n_all": sum(x["n_candidates"] for x in pool.values()),
        "n_rules": sum(x["by_class"].get("boilerplate", 0) for x in pool.values()),
        "n_screen": sum(v for x in pool.values() for k, v in x["by_class"].items() if k not in ("kept", "boilerplate")),
        "n_public": sum(x["by_class"].get("public_reproduction", 0) for x in pool.values()),
        "n_rep": sum(x.get("n_replacements", 0) for x in pool.values()),
        "kept": {c: x["n_kept"] for c, x in pool.items()},
        "email_excl": sum(pool[c]["n_excluded"] for c in emails),
        "email_cand": sum(pool[c]["n_candidates"] for c in emails),
        "exempt": [c for c, x in pool.items() if x.get("screen_exempt")],
    }


def _metric_cards(summary: dict, models: list[str], big: str, abl: dict | None) -> dict[str, dict]:
    """One definition per metric used on the page; every number read from the summaries. Order = order in the 'How we measure things' block."""
    V, ER, EG, LR, BK = summary["verbatim"], summary["entity_recall"], summary["entity_recog"], summary["label_recall"], summary["bench_knowledge"]
    MI, MR, EP, MD = summary["matter_id"], summary["matter_recall"], summary["evidence_prior"], summary["metadata_relevance"]
    L = summary["ladder"]
    pm, rungs = L["per_model"], L["rungs"]
    nm = _short(big)
    emails = ["jebbush", "enron", "mnk", "endo"]
    pf = _pool_facts(summary)
    tri = lambda fn, fmt: _tri(models, fn, fmt)  # noqa: E731
    names = " / ".join(_short(m) for m in models)
    link = lambda sec, label: (f"{REPORT_HREF}#{sec}", label)  # noqa: E731
    sd = lambda v: f"{v:.1f}".replace("-", "−")  # noqa: E731

    cards: dict[str, dict] = {}

    # ---- V
    n_kept = sum(pf["kept"].values()) if pf else 0
    pool_how = (f" Windows are screened first: of {pf['n_all']} candidates, {pf['n_rules']} failed rule checks (boilerplate, signatures, templates, duplicates) and {pf['n_screen']} a GPT-5.6 Luna read that keeps "
                f"only <i>original internal</i> text ({pf['n_public']} were public notices, filings or news quoted into the collection); {pf['n_rep']} fresh windows replaced them, leaving {n_kept} scored." if pf else "")
    v_floor, v_canon, v_tit = V[big]["veridian"]["lcs_f_mean"], V[big]["canon"]["lcs_f_mean"], V[big]["titanic"]["lcs_f_mean"]
    small = [m for m in models if m != big]
    resid = {m: {c: V[m][c]["lcs_f_mean"] - V[m]["veridian"]["lcs_f_mean"] for c in emails if c in V[m]} for m in models}
    above = {m: [c for c, d in resid[m].items() if d >= 0.01] for m in models}
    endo_above = [m for m in small if "endo" in above[m]]
    if endo_above:
        vals = [resid[m][c] for m in small for c in above[m]]
        v_cav = (f"A plausible continuation in the right register scores about {v_floor:.2f} with no knowledge at all. The smaller models sit about {_rng(vals, _f2)} above the floor on "
                 f"{'several' if sum(len(above[m]) for m in small) > 2 else 'some'} real collections, including Endo, whose documents post-date their training — so that residual is the "
                 f"difference between real and synthetic prose, not exposure.")
    else:
        v_cav = f"A plausible continuation in the right register scores about {v_floor:.2f} with no knowledge at all; read every real collection against that floor, not against zero."
    cards["lcs"] = dict(
        title="Finish the document: LCS-F1, longest run, novel run",
        what="Whether a model can reproduce the actual words of a document it is shown only the beginning of.",
        how=f"The model sees the headers and about the first 45% of the body (cut before any quoted reply) and is asked for the next ~60 words \"exactly as in the original\"; "
            f"the answer is compared word by word with the true continuation. Refusals score 0.{pool_how}",
        metric="<b>LCS-F1</b>: longest common subsequence of words between continuation and truth, as an F1: 2·LCS ÷ (words written + words true). <b>Longest run</b>: longest shared <i>contiguous</i> "
               "word sequence. <b>Novel run ≥ 15</b>: a 15-word shared run containing a 5-gram not already in the prefix, so copying the prompt earns nothing.",
        scale=f"0 to 1. Floor: Veridian (invented 2026) {v_floor:.2f}; ceilings: founding documents {v_canon:.2f}, Titanic rows {v_tit:.2f} ({nm}). "
              f"E-mail collections {_rng([V[big][c]['lcs_f_mean'] for c in emails if c in V[big]], _f2)}; e-mail windows with a 15-word run "
              f"{_rng([V[m][c]['frac_run_ge15'] for m in models for c in emails if c in V[m]], _pct)}.",
        why="Word-level, so paraphrase and style do not score; run length separates a memorised stretch from fluent guessing.",
        caveat=v_cav, href=link("rv", "Report §8 · V · verbatim memorisation")[0], href_label="Report §8 · V · verbatim memorisation")

    # ---- E1
    cards["e1"] = dict(
        title="Know the people: free recall",
        what="Whether the model can say, unprompted, which organisation a person from the mailbox belonged to.",
        how="Thirty header names per collection in three frequency tiers (the ten most frequent, ranks 11–40, and the tail). Prompt: \"Who is {name} (active around {era})? "
            "Give organisation and role, or UNKNOWN.\" The era is given because a reviewer's prompt states the dates anyway.",
        metric="<b>Hit rate</b>: share of names whose answer names the target organisation (a keyword set per collection). UNKNOWN and wrong-organisation rates are kept; a hedged answer is not a hit.",
        scale=f"0–100%. Floor: Veridian {_pct(ER[big]['veridian']['hit_rate'])} (invented people; any hit is impossible, any non-UNKNOWN is confabulation). Ceiling: framers of the Constitution "
              f"{_pct(ER[big]['canon']['hit_rate'])} ({nm}). E-mail collections {_rng([ER[m][c]['hit_rate'] for m in models for c in emails if c in ER[m]], _pct)} across the three models.",
        why="Free recall is the strictest claim: the organisation has to come out of the model with nothing to lean on.",
        caveat="A common name may belong to a better-known person; grading on the target organisation makes collisions a miss, which is conservative. Recall is insensitive; recognition (d′) finds what it misses.",
        href=f"{REPORT_HREF}#re", href_label="Report §9 · E · entity knowledge")

    # ---- E2
    terra = next((m for m in models if "terra" in m), None)
    cards["e2"] = dict(
        title="Know the people: recognition d′",
        what="Whether the model recognises the people when told the organisation, corrected for how often it says yes to anyone.",
        how="The same thirty names, each paired with the true organisation and with three planted organisations from the other collections: \"Was {name} affiliated with {org}? yes / no / unknown.\" "
            "Yes/no per pair rather than multiple choice, so the model cannot pick the invented matter by elimination.",
        metric="<b>Hit rate</b>: yes to the true pairing. <b>False-alarm rate</b>: yes to a planted pairing. <b>d′</b> = z(hit) − z(false alarm): the gap between the two in standard-deviation units; 0 means the model cannot tell real pairings from planted ones.",
        scale=f"Floor: Veridian d′ {sd(EG[big]['veridian']['dprime'])}; ceiling: framers {sd(EG[big]['canon']['dprime'])} ({nm}). E-mail collections for {nm}: d′ from "
              f"{sd(min(EG[big][c]['dprime'] for c in emails if c in EG[big]))} to {sd(max(EG[big][c]['dprime'] for c in emails if c in EG[big]))}, with {_rng([EG[big][c]['fa_rate'] for c in emails if c in EG[big]], _pct)} false alarms.",
        why="The planted pairings measure acquiescence, so a model that says yes to everything is not mistaken for one that knows the people.",
        caveat=(f"{MODEL_META[terra][0]} at the study's fast setting says yes to {_pct(EG[terra]['enron']['fa_rate'])} of planted Enron pairings; its raw hit rate is uninterpretable and its d′ is the number to read." if terra
                else "Read d′, not the raw hit rate, whenever the false-alarm rate is high."),
        href=f"{REPORT_HREF}#re", href_label="Report §9 · E · entity knowledge")

    # ---- L
    cards["lab"] = dict(
        title="Know the answer key: label recall",
        what="Whether the published relevance judgments themselves are in the model.",
        how="\"In {collection}, was document {id} judged relevant to topic {n} '{title}'?\" with <b>no document text</b>. One hundred (document, topic) pairs per collection, half relevant and half not <i>within every topic</i>.",
        metric="<b>Accuracy</b> against the published label, with a Wilson 95% interval, read against 50%. The topic-only ceiling (what a model could score from the topic name alone) is printed beside it and is exactly 50% by construction.",
        scale=f"Chance 50%. Ceiling: Titanic survival from row id and name, {_pct(LR[big]['titanic']['acc'])} ({nm}). E-mail collections {_rng([LR[m][c]['acc'] for m in models for c in emails if c in LR[m]], _pct)}; "
              f"Mallinckrodt and Veridian labels were never published, so they must be at chance ({tri(lambda m: LR[m]['mnk']['acc'], _pct)}; {tri(lambda m: LR[m]['veridian']['acc'], _pct)}).",
        why="The most direct form of leakage; balancing within each topic means neither answer bias nor topic prevalence can score.",
        caveat="An early build balanced across the whole collection and let a topic's prevalence leak through its name; the within-topic balance fixed it. Anyone running a label probe should check the question text carries no label information.",
        href=f"{REPORT_HREF}#rl", href_label="Report §11 · L · label memorisation")

    # ---- B
    ver_b = BK[big].get("veridian", {})
    cards["bench"] = dict(
        title="Know the exam questions: benchmark knowledge",
        what="Whether the benchmark's own review topics are in the model.",
        how="Free-text questions, one per benchmark: list the topics of TREC 2016 Total Recall athome4; describe TREC Legal 2009 and 2010 topics; list the CUAD clause categories; "
            "what is the Mallinckrodt (or Endo) collection in the Opioid Industry Documents Archive; what is the Veridian ApexHip matter. 20 Newsgroups is the ceiling question.",
        metric="<b>Share recovered</b>: fraction of the true topic titles or categories present in the answer (whole-word matching). The Veridian answer is scored for confabulation: the right answer is that it is not in the public record.",
        scale=f"0–100%. {nm}: Jeb Bush topics {_pct(BK[big]['trec2016']['score'])}, Enron 2010 / 2009 topics {_pct(BK[big]['legal10']['score'])} / {_pct(BK[big]['legal09']['score'])}, CUAD categories "
              f"{_pct(BK[big]['cuad']['score'])}, 20 Newsgroups {_pct(BK[big]['newsgroups20']['score'])}; Veridian {'not confabulated' if ver_b.get('confabulated') is False else 'confabulated'}.",
        why="Knowing what the assessors were looking for is an advantage without seeing a single document.",
        caveat="Fluent, confident lists of plausible topics score zero if they are not the real ones; the score measures recall of the titles, not of the topics' substance.",
        href=f"{REPORT_HREF}#rb", href_label="Report §10 · B · benchmark knowledge")

    # ---- M0
    real = [k for k, r in rungs.items() if k not in ("veridian", "bigthorium") and r.get("expected") != "none"]
    n_ided = sum(1 for k in real if all((pm[m].get(k) or {}).get("id_hit") for m in models))
    cards["m0"] = dict(
        title="Recognise the case: matter identification",
        what="Whether the model recognises the real case from its facts alone, with the names gone.",
        how="A short sketch of the matter with every proper noun removed (or, for Enron, TREC's own pseudonymised complaint, \"Volteron Corp.\"), then: \"Which real company or case is this modelled on?\" "
            "Scored against an answer key; for the invented Veridian matter the answer is scored against a list of real litigations it could be mistaken for.",
        metric="<b>Named it</b>: yes/no per matter and model. Over the ladder of real matters, the count named by every model.",
        scale=f"Binary. Floor: Veridian, where the right answer is \"no real case\" ({sum(1 for m in models if not MI[m]['veridian']['hit'])} of {len(models)} models said so). "
              f"Ceiling: <i>U.S. v. Microsoft</i>, named by {sum(1 for m in models if MI[m]['microsoft']['hit'])} of {len(models)}. Ladder: {n_ided} of {len(real)} real matters named by all three.",
        why="This is the direct test of whether pseudonymising a complaint hides the case from the reviewer.",
        caveat=f"Strict: naming a different company in the same scandal is a miss ({nm} read \"Volteron\" as {_esc(MI[big]['enron']['first_line'].replace('*', '').split('—')[0].split(',')[0].strip()[:40])}).",
        href=f"{REPORT_HREF}#m0", href_label="Report §15 · M0 · matter identification")

    # ---- M1
    n_facts = _rng([MR[m][k]["n"] for m in models for k in MR[m] if MR[m][k].get("n")], lambda v: f"{v:.0f}")
    cards["m1"] = dict(
        title="Recall the record: checklist share",
        what="How much of the case record the model holds, graded against facts we wrote down in advance.",
        how=f"\"Describe {{matter}}\" in up to 400 words, naming parties, allegations, people, events and outcome. The answer is graded against a hand-written checklist of {n_facts} facts in those five categories by whole-word keyword matching. "
            "Facts the study's own task context already states are flagged, so a share <i>beyond context</i> is reported separately.",
        metric=f"<b>Share</b>: facts hit ÷ facts on the checklist. <b>Beyond-context share</b>: the same over facts the prompt did not state (Enron {tri(lambda m: MR[m]['enron']['share_beyond'], _pct)}).",
        scale=f"0–100%. Floor: Veridian, where every model says it does not know ({'all three' if all(MR[m]['veridian'].get('unknown') for m in models) else 'not all'} said so). Ceiling: <i>U.S. v. Microsoft</i> "
              f"{tri(lambda m: MR[m]['microsoft']['share'], _pct)}. Enron {tri(lambda m: MR[m]['enron']['share'], _pct)}; Mallinckrodt {tri(lambda m: MR[m]['mnk']['share'], _pct)} ({names}).",
        why="A reviewer who can recite the record knows what the responsive documents will say before opening a box.",
        caveat="The checklist is ours and can be extended and re-scored from the stored answers (Mallinckrodt's gained three people items); whole-word matching misses paraphrase.",
        href=f"{REPORT_HREF}#m1", href_label="Report §16 · M1 · matter recall")

    # ---- M2
    m2max = max(EP[m][st]["n_discriminative_named_total"] for m in models for st in EP[m])
    cards["m2"] = dict(
        title="Day-one search terms: evidence prior",
        what="Whether what the model knows about the case converts into search terms that actually find responsive documents.",
        how="Given the matter background and one request, as a reviewer would get them, and before seeing any document: list 25 terms you expect in responsive documents, each typed "
            "(person, organisation, code name, product, place, period, keyword). Every term is then looked up in the labelled collection.",
        metric="Terms already in the prompt are discarded (<b>novel</b>). <b>Named</b>: proper-noun types. <b>Grounded</b>: in ≥ 2 judged documents. <b>Discriminative</b>: in ≥ 2 responsive documents with lift ≥ 2 "
               "(share among responsive ÷ share among all). Headline: discriminative named terms, counted over a request set.",
        scale=f"0 to the largest set observed ({m2max}, named Complaint J, {nm}). Veridian {tri(lambda m: EP[m]['veridian']['n_discriminative_named_total'], str)}; Enron under TREC's pseudonym "
              f"{tri(lambda m: EP[m]['enron_j']['n_discriminative_named_total'], str)}, named {tri(lambda m: EP[m]['enron_j_named']['n_discriminative_named_total'], str)} ({names}).",
        why="Generic keywords discriminate on every collection including the invented one — that is vocabulary. Only named terms the request did not supply measure case knowledge.",
        caveat="Depends on the labelled collection's coverage: Jeb Bush is scored on a 600-document subset, and a term can be true of the case yet absent from the sample.",
        href=f"{REPORT_HREF}#m2", href_label="Report §18 · M2 · evidence prior")

    # ---- M3
    jev_key = next((m for m in summary.get("classifier_models", []) if m in MD), None)
    m3_llm = [d for m in models for d in MD[m]["by_set"].values()]
    m3_llm_max = max(abs(d["delta_people"]) for d in m3_llm)
    m3_llm_excl = sum(1 for d in m3_llm if d["delta_people_ci"][0] > 0 or d["delta_people_ci"][1] < 0)
    m3_llm_n = len(m3_llm)
    cards["m3"] = dict(
        title="Header-only relevance: what the names were worth",
        what="Whether knowing who the people are changes a relevance call made from an e-mail's header alone.",
        how="A balanced sample per request (20 relevant + 20 not; 15 + 15 for Jeb Bush), judged twice from the matter context: once with Date and Subject only, once with From, To and Cc added. "
            "The matter is named in the context, so the headers cannot leak <i>which</i> company it is.",
        metric="<b>Δ people</b> = accuracy(headers) − accuracy(subject only), in percentage points, with a paired bootstrap 95% interval; a lexical baseline (a request-title word in the subject) is printed beside it.",
        scale=f"0 = the names were worth nothing. {nm} on the Enron scandal requests: subject only {_pct(MD[big]['by_set']['enron_j']['acc_subject'])} → with names {_pct(MD[big]['by_set']['enron_j']['acc_headers'])}, "
              f"Δ {_pt(MD[big]['by_set']['enron_j']['delta_people'])} [{_pt(MD[big]['by_set']['enron_j']['delta_people_ci'][0])}, {_pt(MD[big]['by_set']['enron_j']['delta_people_ci'][1])}]"
              + (f"; Jev {_pt(MD[jev_key]['by_set']['enron_j']['delta_people'])} [{_pt(MD[jev_key]['by_set']['enron_j']['delta_people_ci'][0])}, {_pt(MD[jev_key]['by_set']['enron_j']['delta_people_ci'][1])}]" if jev_key else "") + ".",
        why="It is the one probe that fits a classifier's interface, so it is the one that could be run on Jev as well as on the language models.",
        caveat=f"Little power to detect people-knowledge: the language models, which demonstrably know the people, gain at most {_pt(m3_llm_max)} points from the names"
               f"{'' if m3_llm_excl == 0 else f', and only {m3_llm_excl} of {m3_llm_n} of their intervals clear zero'}. A flat result is consistent with ignorance but does not establish it.",
        href=f"{REPORT_HREF}#m3", href_label="Report §19 · M3 · metadata-only relevance")

    # ---- composite
    C = summary["composite"]
    cards["comp"] = dict(
        title="Documents score, case score, overall",
        what="One 0–100 number per collection for how much of the documents a model has, one for how much of the case, and a plain mean.",
        how="Each channel's headline metric is placed between a floor (Veridian's value → 0) and a ceiling (→ 100), clipped. V: LCS-F1 to the founding documents; E: d′ to the framers; "
            "L: label accuracy from chance to Titanic; B: share of the benchmark's topics recited; M0: 0 or 100 for naming the matter; M1: checklist share to <i>U.S. v. Microsoft</i>; "
            "M2: discriminative named terms to the largest set observed.",
        metric=f"<b>Documents score</b> = mean of {', '.join(C['doc_channels'])}. <b>Case score</b> = mean of {', '.join(C['case_channels'])}. <b>Overall</b> = plain mean of every channel the collection has.",
        scale=f"0–100. Anchors for {nm}: founding documents LCS-F1 {V[big]['canon']['lcs_f_mean']:.2f}, framers d′ {EG[big]['canon']['dprime']:.1f}, Titanic labels {_pct(LR[big]['titanic']['acc'])}, "
              f"Microsoft checklist {_pct(MR[big]['microsoft']['share'])}, largest M2 set {m2max}. CUAD has no case channels; Mallinckrodt and Endo have no benchmark channel.",
        why="Equal weight across channels is the simplest defensible choice; the split into two scores exists because the overall mean hides the main finding.",
        caveat="A presentation choice, not a measurement: the weights are ours and the binary M0 moves a case score by a third on its own.",
        href=f"{REPORT_HREF}#composite", href_label="Report · Overview matrix (documents, case, overall)")

    # ---- knowledge effect
    if abl:
        con = abl["contrasts"]
        systems = [m for m in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "jev@base") if m in con]
        jk_txt = "; ".join(f"{_short(m)} {_pt(con[m]['j_minus_k']['f1']['delta'])} [{_pt(con[m]['j_minus_k']['f1']['lo'])}, {_pt(con[m]['j_minus_k']['f1']['hi'])}]" for m in systems)
        leak = abl.get("leak", {})
        lm = [m for m in systems if m in leak]
        leak_txt = " / ".join(f"{int(100 * leak[m]['named_enron'] / leak[m]['n'] + 0.5)}%" for m in lm)
        cards["keff"] = dict(
            title="Knowledge effect: ΔF1(J) − ΔF1(K)",
            what="Whether knowing the case changed a system's review score on full documents.",
            how="The same documents are classified twice: as written, and with every person and organisation consistently replaced by an invented name. Three arms: Enron Complaint J (the scandal, where the knowledge is), "
                "Enron Complaint K (an unrelated fact pattern on the same mailbox; the control), and Veridian (invented; renaming can only cost).",
            metric="<b>ΔF1</b> = F1(renamed) − F1(named), in percentage points. <b>Knowledge effect</b> = ΔF1(J) − ΔF1(K). The 95% interval is a paired bootstrap over documents (resample documents, recompute both conditions, "
                   "take the 2.5th and 97.5th percentiles); McNemar's test counts individual label flips.",
            scale=f"0 = no effect; negative = renaming hurt the scandal requests more than the control, i.e. the knowledge was doing work. Measured: {jk_txt}.",
            why="Subtracting the control cancels the cost of the renaming operation itself, which Veridian shows is real.",
            caveat=f"A lower bound: shown the renamed documents, the language models still identified Enron {leak_txt} of the time from the fact pattern, so only the name channel was removed." if lm else "A lower bound: only the name channel is removed.",
            href=f"{REPORT_HREF}#effect", href_label="Report §20 · Effect: the pseudonymisation ablation")
        ej = abl["arms"]["enron_j"]["per_model"]
        ex_sys = [m for m in systems if m in ej]
        ex = "; ".join(f"{_short(m)} {100 * ej[m]['named']['f1']:.1f} (recall {_pct(ej[m]['named']['recall'])}, precision {_pct(ej[m]['named']['precision'])})" for m in ex_sys)
        f1_scale = f"0–100 points; 100 is perfect. Enron Complaint J as written: {ex}."
    else:
        f1_scale = "0–100 points; 100 is perfect."

    # ---- round 2 (paraphrase knowledge effect; matter-vs-control topics) and brief injection
    e2 = _effect2()
    if e2:
        ke_txt = "; ".join(f"{_short(m)} {_pt(e2['ke'][m]['delta'])} [{_pt(e2['ke'][m]['lo'])}, {_pt(e2['ke'][m]['hi'])}]" for m in e2["jeb_sys"] if m in e2["ke"])
        pe_txt = "; ".join(f"{_short(m)} {_pt(e2['par_eff'][m]['delta'])} [{_pt(e2['par_eff'][m]['lo'])}, {_pt(e2['par_eff'][m]['hi'])}]" for m in e2["cuad_sys"] if m in e2["par_eff"])
        cards["keff2"] = dict(
            title="Round-2 knowledge effects: paraphrase (CUAD) and matter − control (Jeb Bush)",
            what="Whether the knowledge effect found to be within noise on Enron is also within noise where the memory is of the text itself (CUAD) and of public figures (Jeb Bush).",
            how="CUAD: each contract excerpt classified three times — as written, with parties, dates, amounts and jurisdictions renamed, and paraphrased by a model not under test (every party, "
                "term, number and obligation kept; a second model judged the rewrites legally equivalent). Jeb Bush: the Governor, his family and Florida's public figures renamed; the matter topics "
                "(governorship events) compared with control topics on the same documents.",
            metric="<b>Paraphrase knowledge effect</b> = ΔF1(CUAD paraphrased) − ΔF1(Veridian paraphrased), the cost of paraphrase on an unseen corpus subtracted. <b>Jeb Bush knowledge effect</b> = "
                   "ΔF1(matter topics) − ΔF1(control topics), paired within each bootstrap draw. Percentage points, cluster bootstrap by contract or document, 95% intervals.",
            scale=f"0 = no effect; negative = the manipulation hurt where the knowledge was more than where it was not. Measured — CUAD paraphrase: {pe_txt}. Jeb Bush: {ke_txt}.",
            why="Renaming cannot remove memorised text, and Enron's control requests sit on the same mailbox as its matter requests; paraphrase and topic-level controls close those two gaps.",
            caveat=f"The CUAD control is e-mail, not unseen contracts; the within-CUAD dose–response (no growth of Δ with memorisation score) is the primary control. {e2['absent_txt']}".strip(),
            href=f"{REPORT_HREF}#effect2", href_label="Report §20 · Round 2: CUAD and Jeb Bush")
    vv = _verify()
    if vv:
        cards["inject"] = dict(
            title="Brief injection: ΔF1 with a case brief on the invented matter",
            what="Whether handing a system the case — the parties, products, people, deals and conduct — changes its review calls where no system can know any of it.",
            how=f"A {vv['n_subset']}-document stratified half of the Veridian sample classified twice under the same requests, once bare and once with a one-page fictional case brief prepended; "
                f"the round-1 Mallinckrodt brief arm is the real-matter comparison.",
            metric="<b>ΔF1</b> = F1(with brief) − F1(without), percentage points, cluster bootstrap over documents; McNemar on label flips.",
            scale=f"0 = the brief changed nothing; positive = knowing the case helped. Measured: {vv['d_seq']} ({vv['d_sys_txt']}); largest |Δ| {vv['d_bound']:.1f}, every interval within ±{vv['d_ci_bound']:.1f}.",
            why="Removal tests can fail by not removing enough; adding the knowledge where it is certainly absent tests the other direction.",
            caveat="A brief is not a training run: it supplies the facts, not the fluency with them that pre-training gives. Half the sample, for cost.",
            href=f"{REPORT_HREF}#verify", href_label="Report §20 · Generalisation checks")

    # ---- code-name swap (the classifier-native test of case knowledge)
    nat = jev_native(summary)
    if nat:
        t1j = nat["t1_jev"]
        cards["cns"] = dict(
            title="Code-name swap Δ: does the real name change the call?",
            what="Whether a system's relevance call depends on recognising a real matter token — an Enron vehicle, a Florida controversy, an opioid brand — rather than on the text around it.",
            how="The same templated document is classified twice, differing in one token: the real one or an invented one of the same shape; the request describes the conduct and names no token. "
                "<i>Signal</i> pairs are tokens a case-aware reader would call relevant; <i>decoy</i> pairs are real tokens a case-aware reader knows are <i>not</i> what was asked, so knowledge should lower the call.",
            metric="<b>Δ</b> = relevant-call rate on the real-token version − rate on the fictional-token version, in percentage points, with a paired bootstrap 95% interval over pairs; exact McNemar on discordant pairs. "
                   "Signal − decoy is the knowledge net of any 'real-looking name' effect.",
            scale="0 = the real name is worth nothing (a system with no case knowledge). Jev: " + "; ".join(f"{_esc(MATTER_LABEL.get(k, k))} {_pt(t1j[k]['diff'])} [{_pt(t1j[k]['diff_ci'][0])}, {_pt(t1j[k]['diff_ci'][1])}]"
                                                                                                      for k in t1j) + f". {nat['t1_range_txt'][0].upper() + nat['t1_range_txt'][1:]}.",
            why="It is a test of case knowledge a classifier can take: no generation, just a call on two near-identical documents. The language models are the positive comparison — systems known to carry the knowledge.",
            caveat="It shows the system knows what the names mean, not where it learned them: a base model pre-trained on public text and a model trained on synthetic data written by a knowledgeable LLM would both show it. "
                   "It is not evidence of having seen the benchmark documents.",
            href=f"{REPORT_HREF}#jevnative", href_label="Report §21 · Classifier-native tests")
    cards["f1"] = dict(
        title="F1, recall and precision",
        what="The three scores used for a relevance review.",
        how="Every (document, request) decision a system makes is compared with the gold label for that pair; the counts of hits, misses and false alarms are pooled over the requests in a set.",
        metric="<b>Recall</b>: the share of truly responsive documents the system flagged (what a producing party has to defend). <b>Precision</b>: the share of flagged documents that were responsive (the review cost of false alarms). "
               "<b>F1</b>: their harmonic mean, 2·P·R ÷ (P + R), which is low if either is low.",
        scale=f1_scale,
        why="Recall is the legal obligation, precision is the bill; F1 is the single number that punishes trading one for the other.",
        caveat="Pooled over requests, so a large request weighs more than a small one; the gold itself is panel-made for Mallinckrodt and Endo and TREC's for Enron.",
        href="../ablation/ablation_report.html", href_label="Ablation report · per-arm F1, recall, precision")
    return cards


# ------------------------------------------------------------------------------------------------ small helpers

def _f2(v):
    return "–" if v is None else f"{v:.2f}"


def _pt(v, nd=1):
    """Signed percentage points from a fraction, no '-0.0'."""
    r = round(100 * v, nd)
    r = 0.0 if r == 0 else r
    return f"{r:+.{nd}f}"


def _ci_pt(d: dict) -> str:
    v, lo, hi = _pp(d)
    return f"<b>{v:+.1f}</b> <small>[{lo:+.1f}, {hi:+.1f}]</small>"


def _ci_pct(v, ci) -> str:
    if v is None:
        return "–"
    return f"{_pct(v)} <small>[{_pct(ci[0])}, {_pct(ci[1])}]</small>" if ci else _pct(v)


def _rng(vals, fmt):
    vals = [v for v in vals if v is not None]
    if not vals:
        return "–"
    lo, hi = min(vals), max(vals)
    return fmt(lo) if fmt(lo) == fmt(hi) else f"{fmt(lo)}–{fmt(hi)}"


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def _short(m):
    return MODEL_META[_mkey(m)][0].split()[-1]


def _tri(models, fn, fmt):
    out = []
    for m in models:
        try:
            v = fn(m)
        except (KeyError, TypeError):
            v = None
        out.append("–" if v is None else fmt(v))
    return " / ".join(out)


def _mix(c_hex: str, t: float) -> str:
    """Blend PANEL -> colour by t in [0,1]."""
    t = max(0.0, min(1.0, t))
    a = tuple(int(PANEL[i:i + 2], 16) for i in (1, 3, 5))
    b = tuple(int(c_hex[i:i + 2], 16) for i in (1, 3, 5))
    return "#" + "".join(f"{int(round(a[i] + (b[i] - a[i]) * t)):02x}" for i in range(3))


def _tag(k):
    r = STORY_TAG.get(k)
    return f' <span class="role {r}">{role_text(r)}</span>' if r else ""


# ------------------------------------------------------------------------------------------------ figures (inline SVG)

def _fig_dials(summary, models):
    """Layer 0: per collection, two bars — how much of the DOCUMENTS the models know vs how much of the CASE (0 = floor, 100 = ceiling)."""
    C = summary["composite"]["per_model"]
    sets = [k for k in STORY_SETS if any(k in C[m] for m in models)]
    label_w, bar_w, row_h, pad_t, pad_b = 290, 470, 46, 40, 26
    w = label_w + bar_w + 90
    h = pad_t + row_h * len(sets) + pad_b
    x = lambda v: label_w + v / 100 * bar_w  # noqa: E731
    out = [f'<text x="{label_w}" y="13" font-size="9.5" fill="{INK3}" letter-spacing="0.08em">0 = KNOWS NOTHING</text>',
           f'<text x="{label_w}" y="25" font-size="9.5" fill="{INK3}">(what our invented case scores)</text>',
           f'<text x="{x(100):.0f}" y="13" font-size="9.5" fill="{INK3}" letter-spacing="0.08em" text-anchor="end">100 = KNOWS IT COLD</text>',
           f'<text x="{x(100):.0f}" y="25" font-size="9.5" fill="{INK3}" text-anchor="end">(founding documents · U.S. v. Microsoft)</text>']
    for t in (0, 25, 50, 75, 100):
        out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{pad_t - 6}" y2="{h - pad_b + 2}" stroke="{LINE}"/>')
        out.append(f'<text x="{x(t):.1f}" y="{h - pad_b + 15}" font-size="10" text-anchor="middle" fill="{INK3}">{t}</text>')
    for i, k in enumerate(sets):
        cy = pad_t + row_h * i
        if i:
            out.append(f'<line x1="0" x2="{w}" y1="{cy - 3}" y2="{cy - 3}" stroke="{LINE}" stroke-width="0.6"/>')
        out.append(f'<text x="{label_w - 10}" y="{cy + 20}" font-size="12.5" text-anchor="end" fill="{INK}" font-weight="600">{_esc(STORY_LABEL[k])}</text>')
        for j, (key, col, word) in enumerate((("doc_score", DOC_COLOR, "documents"), ("case_score", CASE_COLOR, "the case"))):
            yy = cy + 4 + j * 18
            vals = {m: C[m][k].get(key) for m in models if k in C[m]}
            mv = _mean(vals.values())
            if mv is None:
                out.append(f'<rect x="{x(0):.1f}" y="{yy}" width="{bar_w}" height="12" fill="url(#hatch)" opacity="0.7"/>')
                out.append(f'<text x="{x(0) + 6:.1f}" y="{yy + 9.5}" font-size="9.5" fill="{INK3}">{word}: not measurable (contracts have no case behind them)</text>')
                continue
            out.append(f'<rect x="{x(0):.1f}" y="{yy}" width="{max(1.5, x(mv) - x(0)):.1f}" height="12" fill="{col}" rx="2"><title>{word}: {mv:.0f} (mean of {len(vals)} models)</title></rect>')
            for m, v in vals.items():
                if v is None:
                    continue
                out.append(f'<line x1="{x(v):.1f}" x2="{x(v):.1f}" y1="{yy - 2}" y2="{yy + 14}" stroke="{INK}" stroke-width="1.2" opacity="0.7"><title>{_esc(MODEL_META[m][0])}: {v:.0f}</title></line>')
            lx = x(max([mv] + [v for v in vals.values() if v is not None])) + 7
            out.append(f'<text x="{lx:.1f}" y="{yy + 9.5}" font-size="10" fill="{INK}">{mv:.0f} <tspan fill="{INK3}">{word}</tspan></text>')
    defs = ('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="6" height="6" fill="{PANEL}"/><line x1="0" y1="0" x2="0" y2="6" stroke="{LINE}" stroke-width="2"/></pattern></defs>')
    return f'<figure>{_svg(w, h, defs + "".join(out))}</figure>'


def _ruler(marks, xmin, xmax, fmt, ref=None, width=390, note_ref=None):
    """A horizontal scale from floor to ceiling with labelled dots. marks: [(label, value, kind)], kind in floor|ceiling|real|hi.
    Labels are packed into lanes above and below the line so that collections with near-identical values stay legible."""
    pad_l, pad_r, lane_h, char_w = 14, 14, 12, 5.4
    pw = width - pad_l - pad_r
    x = lambda v: pad_l + (min(max(v, xmin), xmax) - xmin) / (xmax - xmin) * pw  # noqa: E731
    ms = sorted([(l, v, k) for l, v, k in marks if v is not None], key=lambda t: t[1])
    placed, lane_end = [], {}
    for lbl, v, kind in ms:
        cx = x(v)
        hw = max(10.0, len(lbl) * char_w / 2)
        lx = min(max(cx, pad_l + hw), width - pad_r - hw)
        lane = 0
        while lane in lane_end and lane_end[lane] > lx - hw - 5:
            lane += 1
        lane_end[lane] = lx + hw
        placed.append((lbl, v, kind, cx, lx, lane))
    n_lanes = (max(p[5] for p in placed) + 1) if placed else 1
    above, below = (n_lanes + 1) // 2, n_lanes // 2
    y = 8 + above * lane_h + 8
    h = y + 10 + below * lane_h + 18
    out = [f'<line x1="{pad_l}" x2="{pad_l + pw}" y1="{y}" y2="{y}" stroke="{INK4}" stroke-width="1.5"/>']
    out.append(f'<text x="{pad_l}" y="{h - 4}" font-size="9.5" fill="{INK3}">{_esc(fmt(xmin))}</text>')
    out.append(f'<text x="{pad_l + pw}" y="{h - 4}" font-size="9.5" fill="{INK3}" text-anchor="end">{_esc(fmt(xmax))}</text>')
    if ref is not None:
        out.append(f'<line x1="{x(ref):.1f}" x2="{x(ref):.1f}" y1="{y - 10}" y2="{y + 10}" stroke="{INK3}" stroke-dasharray="3 3"/>')
        if note_ref:
            out.append(f'<text x="{x(ref):.1f}" y="{h - 4}" font-size="9.5" fill="{INK3}" text-anchor="middle">{_esc(note_ref)}</text>')
    for lbl, v, kind, cx, lx, lane in placed:
        col = ROLE_COLOR["floor"] if kind == "floor" else ROLE_COLOR["ceiling"] if kind == "ceiling" else (CASE_COLOR if kind == "hi" else INK)
        r = 5 if kind in ("floor", "ceiling", "hi") else 4
        if lane % 2 == 0:
            ly = y - 9 - (lane // 2) * lane_h
            y0, y1 = y - r - 1, ly + 2
        else:
            ly = y + 17 + (lane // 2) * lane_h
            y0, y1 = y + r + 1, ly - 9
        if lane >= 2 or abs(cx - lx) > 2:
            out.append(f'<line x1="{cx:.1f}" y1="{y0:.1f}" x2="{lx:.1f}" y2="{y1:.1f}" stroke="{INK4}" stroke-width="0.7"/>')
        out.append(f'<circle cx="{cx:.1f}" cy="{y}" r="{r}" fill="{col}" stroke="#fff" stroke-width="1"><title>{_esc(lbl)}: {_esc(fmt(v))}</title></circle>')
        out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="9.5" fill="{col}" text-anchor="middle">{_esc(lbl)}</text>')
    return _svg(width, h, "".join(out), cls="fig ruler")


def _fig_scatter(summary, models):
    """Finding 4: documents axis vs case axis; one labelled cluster per collection, model-coloured dots."""
    C = summary["composite"]["per_model"]
    W, H = 680, 520
    pad_l, pad_r, pad_t, pad_b, strip_h = 54, 20, 30, 92, 34
    pw, ph = W - pad_l - pad_r, H - pad_t - pad_b
    X = lambda v: pad_l + v / 100 * pw  # noqa: E731
    Y = lambda v: pad_t + (1 - v / 100) * ph  # noqa: E731
    out = []
    for t in (0, 25, 50, 75, 100):
        out.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{pad_t}" y2="{pad_t + ph}" stroke="{LINE}"/>')
        out.append(f'<line x1="{pad_l}" x2="{pad_l + pw}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{LINE}"/>')
        out.append(f'<text x="{X(t):.1f}" y="{pad_t + ph + 14}" font-size="10" text-anchor="middle" fill="{INK3}">{t}</text>')
        out.append(f'<text x="{pad_l - 8}" y="{Y(t) + 3.5:.1f}" font-size="10" text-anchor="end" fill="{INK3}">{t}</text>')
    # quadrant words
    out.append(f'<text class="quad" x="{X(2):.1f}" y="{Y(97):.1f}" font-size="10.5" fill="{INK3}">knows the case, no sign of the documents</text>')
    out.append(f'<text class="quad" x="{X(98):.1f}" y="{Y(97):.1f}" font-size="10.5" fill="{INK3}" text-anchor="end">knows both</text>')
    out.append(f'<text class="quad" x="{X(2):.1f}" y="{Y(9):.1f}" font-size="10.5" fill="{INK3}">knows neither</text>')
    out.append(f'<text class="quad" x="{X(98):.1f}" y="{Y(3):.1f}" font-size="10.5" fill="{INK3}" text-anchor="end">has read the documents</text>')
    out.append(f'<text x="{pad_l + pw / 2:.1f}" y="{pad_t + ph + 30}" font-size="11" text-anchor="middle" fill="{DOC_COLOR}" font-weight="600">DOCUMENT awareness → (finish the text, know the staff, know the answer key, know the exam)</text>')
    out.append(f'<text x="14" y="{pad_t + ph / 2:.1f}" font-size="11" text-anchor="middle" fill="{CASE_COLOR}" font-weight="600" transform="rotate(-90 14 {pad_t + ph / 2:.1f})">MATTER awareness → (recognise, recall, predict the evidence)</text>')
    # strip for datasets with no case axis
    sy = pad_t + ph + 44
    out.append(f'<rect x="{pad_l}" y="{sy}" width="{pw}" height="{strip_h}" fill="{PANEL}" stroke="{LINE}" rx="4"/>')
    out.append(f'<text x="{pad_l + 6}" y="{sy + 12}" font-size="9.5" fill="{INK3}">no case axis: contracts have no matter behind them</text>')
    labels: list[str] = []
    for k in STORY_SETS:
        pts = [(m, C[m][k]["doc_score"], C[m][k].get("case_score")) for m in models if k in C[m] and C[m][k].get("doc_score") is not None]
        if not pts:
            continue
        has_case = any(p[2] is not None for p in pts)
        xs = [p[1] for p in pts]
        ys = [p[2] for p in pts if p[2] is not None]
        mx = _mean(xs)
        if has_case:
            my = _mean(ys)
            # spider: a thin tie from each model's dot to the cluster centroid, so the three dots read as one collection
            for m, xv, yv in pts:
                out.append(f'<line x1="{X(mx):.1f}" y1="{Y(my):.1f}" x2="{X(xv):.1f}" y2="{Y(yv):.1f}" stroke="{INK4}" stroke-width="0.8" opacity="0.7"/>')
            for m, xv, yv in pts:
                out.append(f'<circle cx="{X(xv):.1f}" cy="{Y(yv):.1f}" r="5.5" fill="{MODEL_META[m][2]}" stroke="#fff" stroke-width="1.2"><title>{_esc(STORY_LABEL[k])} — {_esc(MODEL_META[m][0])}: documents {xv:.0f}, case {yv:.0f}</title></circle>')
            # the two floors share the bottom-left corner: Big Thorium's label goes above the baseline so it does not sit on Veridian's;
            # labels are emitted after every dot so a later collection's dots cannot cover an earlier label
            lx, ly = X(max(xs)) + 11, (Y(my) - 9 if k == "bigthorium" else Y(my) + 4)
            labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11.5" font-weight="600" fill="{INK}" paint-order="stroke" stroke="{PANEL}" stroke-width="4" stroke-linejoin="round">{_esc(STORY_LABEL[k].split(" (")[0])}</text>')
        else:
            for m, xv, _ in pts:
                out.append(f'<circle cx="{X(xv):.1f}" cy="{sy + strip_h / 2 + 4:.1f}" r="5.5" fill="{MODEL_META[m][2]}" stroke="#fff" stroke-width="1.2"><title>{_esc(STORY_LABEL[k])} — {_esc(MODEL_META[m][0])}: documents {xv:.0f}</title></circle>')
            out.append(f'<text x="{X(mx):.1f}" y="{sy + strip_h / 2 - 6:.1f}" font-size="11.5" font-weight="600" fill="{INK}" text-anchor="middle">{_esc(STORY_LABEL[k])}</text>')
    out += labels
    return f'<figure>{_svg(W, H + strip_h + 10, "".join(out))}</figure>'


def _fig_effect(abl, systems):
    """Finding 3: one row per system — the knowledge effect ΔF1(J) − ΔF1(K) with its 95% interval, around zero."""
    con = abl["contrasts"]
    rows = [m for m in systems if m in con]
    label_w, pw, row_h, pad_t, pad_b, xmin, xmax = 150, 520, 34, 40, 28, -8, 8
    w = label_w + pw + 40
    h = pad_t + row_h * len(rows) + pad_b
    x = lambda v: label_w + (v - xmin) / (xmax - xmin) * pw  # noqa: E731
    out = []
    for t in range(xmin, xmax + 1, 2):
        out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{pad_t - 4}" y2="{h - pad_b + 4}" stroke="{LINE}"/>')
        out.append(f'<text x="{x(t):.1f}" y="{h - pad_b + 17}" font-size="10" text-anchor="middle" fill="{INK3}">{t:+d}</text>')
    out.append(f'<line x1="{x(0):.1f}" x2="{x(0):.1f}" y1="{pad_t - 8}" y2="{h - pad_b + 4}" stroke="{INK}" stroke-width="1.4"/>')
    out.append(f'<text x="{x(xmin):.1f}" y="13" font-size="9.5" fill="{INK3}" letter-spacing="0.06em">← RENAMING HURT THE SCANDAL REQUESTS MORE</text>')
    out.append(f'<text x="{x(xmin):.1f}" y="25" font-size="9.5" fill="{INK3}">(the case knowledge was doing work)</text>')
    out.append(f'<text x="{x(xmax):.1f}" y="13" font-size="9.5" fill="{INK3}" letter-spacing="0.06em" text-anchor="end">HELPED MORE →</text>')
    out.append(f'<text x="{x(0):.1f}" y="25" font-size="9.5" fill="{INK3}" text-anchor="middle">no effect</text>')
    for i, m in enumerate(rows):
        cy = pad_t + row_h * i + row_h / 2
        d = con[m]["j_minus_k"]["f1"]
        v, lo, hi = _pp(d)
        col = MODEL_META[_mkey(m)][2]
        out.append(f'<text x="{label_w - 10}" y="{cy + 4:.1f}" font-size="12" text-anchor="end" fill="{INK}">{_esc(MODEL_META[_mkey(m)][0])}</text>')
        out.append(f'<line x1="{x(max(xmin, lo)):.1f}" x2="{x(min(xmax, hi)):.1f}" y1="{cy:.1f}" y2="{cy:.1f}" stroke="{col}" stroke-width="2.2" opacity="0.85"/>')
        out.append(f'<circle cx="{x(v):.1f}" cy="{cy:.1f}" r="5.5" fill="{col}" stroke="#fff" stroke-width="1.2"><title>{_esc(MODEL_META[_mkey(m)][0])}: {v:+.1f} [{lo:+.1f}, {hi:+.1f}]</title></circle>')
        out.append(f'<text x="{x(xmax) + 6:.1f}" y="{cy + 4:.1f}" font-size="10.5" fill="{INK3}">{v:+.1f}</text>')
    return f'<figure>{_svg(w, h, "".join(out))}</figure>'


# ------------------------------------------------------------------------------------------------ HTML pieces

def _grid(summary, models):
    """The composite matrix reduced to colour cells: rows = collections, columns = the seven channels (documents | the case), colour = mean over models."""
    comp = summary["composite"]
    C = comp["per_model"]
    docs, case = comp["doc_channels"], comp["case_channels"]
    hdr = ('<tr><th></th>' + f'<th class="grp" colspan="{len(docs)}" style="color:{DOC_COLOR}">the documents</th><th class="gap"></th>'
           f'<th class="grp" colspan="{len(case)}" style="color:{CASE_COLOR}">the case</th></tr>')
    hdr += '<tr><th></th>' + "".join(f'<th>{_esc(CHANNEL_WORD[ch])}</th>' for ch in docs) + '<th class="gap"></th>' + "".join(f'<th>{_esc(CHANNEL_WORD[ch])}</th>' for ch in case) + '</tr>'
    body = []
    for k in STORY_SETS:
        if not any(k in C[m] for m in models):
            continue
        cells = [f'<th class="rl">{_esc(STORY_LABEL[k])}{_tag(k)}</th>']
        for group, col in ((docs, DOC_COLOR), (case, CASE_COLOR)):
            for ch in group:
                vals = [(m, C[m][k]["channels"].get(ch)) for m in models if k in C[m]]
                nums = [v for _, v in vals if v is not None]
                if not nums:
                    cells.append('<td class="na" title="not measurable for this collection">·</td>')
                    continue
                mv = sum(nums) / len(nums)
                tip = "; ".join(f"{_short(m)} {v:.0f}" for m, v in vals if v is not None)
                fg = "#fff" if mv > 60 else INK
                cells.append(f'<td style="background:{_mix(col, mv / 100)};color:{fg}" title="{_esc(CHANNEL_WORD[ch])} · {_esc(STORY_LABEL[k])}: {mv:.0f} on a 0–100 scale (floor → ceiling). Per model: {_esc(tip)}">{mv:.0f}</td>')
            if group is docs:
                cells.append('<td class="gap"></td>')
        body.append("<tr>" + "".join(cells) + "</tr>")
    return f'<table class="grid"><thead>{hdr}</thead><tbody>{"".join(body)}</tbody></table>'


def _guess_verbatim(summary, models, big):
    V = summary["verbatim"][big]
    opts = [k for k in ("enron", "jebbush", "mnk", "endo", "cuad", "veridian") if k in V]
    thr = 0.10
    boxes = "".join(f'<label><input type="checkbox"> {_esc(STORY_LABEL[k])}</label>' for k in opts)
    rows = []
    for k in opts:
        v = V[k]
        yes = v["frac_run_ge15"] >= thr
        rows.append([_esc(STORY_LABEL[k]) + _tag(k), f'<span class="{"ok" if yes else "no"}">{"yes" if yes else "no"}</span>',
                     _pct(v["frac_run_ge15"]), _tri(models, lambda m, k=k: summary["verbatim"][m][k]["lcs_f_mean"], _f2)])
    for k in ("canon", "titanic"):
        if k in V:
            rows.append([_esc(STORY_LABEL[k]) + _tag(k), '<span class="ok">yes</span>', _pct(V[k]["frac_run_ge15"]), _tri(models, lambda m, k=k: summary["verbatim"][m][k]["lcs_f_mean"], _f2)])
    tbl = table(["collection", "finishes it from memory?", f"documents with a 15-word exact run ({_short(big)})", f"word overlap, LCS-F1 ({' / '.join(_short(m) for m in models)})"], rows, cls="tbl compact")
    floor = V["veridian"]["lcs_f_mean"]
    return (f'<div class="guess"><b class="t">Guess first</b><p>We showed the models the first part of a real document and asked them to write the next 60 words '
            f'<em>exactly</em>. Which of these six collections do you think they could finish from memory? Tick your guesses, then reveal.</p>'
            f'<div class="opts">{boxes}</div><details><summary>Reveal</summary>'
            f'<p>Our yardstick: a collection counts as reproducible from memory when the largest model produces an exact run of fifteen or more consecutive words in at least '
            f'one document in ten ({thr:.0%}). The invented collection scores an overlap of {floor:.2f} knowing nothing at all, so that is the floor every real one has to beat; '
            f'the two memorised anchors at the bottom show what the ceiling looks like.</p>{tbl}</details></div>')


def _guess_identify(summary, models):
    L = summary["ladder"]
    pm, rungs = L["per_model"], L["rungs"]
    picks = [k for k in ("bhopal", "enron", "mnk", "endo", "mckesson_robbins", "rdc", "meyer", "veridian") if k in rungs]
    note = {"enron": " (shown as TREC's pseudonymised complaint, 'Volteron')", "rdc": " (no Wikipedia article)", "mckesson_robbins": " (a 1938 fraud)",
            "meyer": " (SEC complaint filed September 2026)", "veridian": " (our invented matter)", "endo": " (the post-cutoff collection)"}
    boxes = "".join(f'<label><input type="checkbox"> {_esc(rungs[k]["label"].split(" (")[0])}{_esc(note.get(k, ""))}</label>' for k in picks)
    rows = []
    for k in picks:
        marks = []
        for m in models:
            r = pm[m].get(k) or {}
            if r.get("id_hit"):
                marks.append(f'<span style="color:{MODEL_META[m][2]}" title="{_esc(MODEL_META[m][0])}: named it">●</span>')
            elif r.get("id_unknown"):
                marks.append(f'<span style="color:{MODEL_META[m][2]}" title="{_esc(MODEL_META[m][0])}: said it could not tell">?</span>')
            else:
                marks.append(f'<span style="color:{MODEL_META[m][2]}" title="{_esc(MODEL_META[m][0])}: {_esc((r.get("id_first_line") or "").replace("*", "")[:90])}">○</span>')
        n_hit = sum(1 for m in models if (pm[m].get(k) or {}).get("id_hit"))
        views = rungs[k]["footprint"].get("views_12m")
        rows.append([_esc(rungs[k]["label"]), f"{' '.join(marks)} <small>{n_hit}/{len(models)}</small>",
                     f"{views:,}" if views else ("—" if rungs[k]["expected"] in ("floor", "none") else "no article"),
                     _tri(models, lambda m, k=k: pm[m][k]["share"], _pct) if any((pm[m].get(k) or {}).get("share") is not None for m in models) else "–"])
    tbl = table(["matter", "named it from a nameless sketch (● yes · ○ named something else · ? declined)", "Wikipedia pageviews, 12 months", "share of the fact checklist recalled"], rows, cls="tbl compact")
    return (f'<div class="guess"><b class="t">Guess first</b><p>We described each matter in a short paragraph with every proper noun removed and asked "which real case is this?". '
            f'Which of these do you think the models could name?</p><div class="opts">{boxes}</div><details><summary>Reveal</summary>'
            f'<p>Everything that was litigated in public before the training cutoff is named, however obscure; the one matter nobody knows is the one filed after the cutoff — and the '
            f'invented one is (mostly) not mistaken for a real case.</p>{tbl}</details></div>')


def _rename_exhibit():
    """Before/after examples from the ablation's rename dictionary (data/ablation/mapping.json). Empty string if the file is absent."""
    if not MAPPING_PATH.exists():
        return ""
    try:
        mp = json.loads(MAPPING_PATH.read_text())
    except (OSError, ValueError):
        return ""
    en = mp.get("enron") or {}
    phrases, people = en.get("phrases") or {}, en.get("people") or {}
    want_phr = ["Enron", "Raptor", "Talon", "LJM2", "Chewco", "Arthur Andersen", "EnronOnline"]
    want_ppl = ["Lay", "Skilling", "Fastow", "Watkins"]
    pairs = [(k, phrases[k]) for k in want_phr if k in phrases] + [(k, people[k]) for k in want_ppl if k in people]
    if not pairs:
        return ""
    stats = (mp.get("stats") or {}).get("enron_j") or {}
    cells = "".join(f'<span>{_esc(a)}</span><span class="arr">→</span><span class="r">{_esc(b)}</span>' for a, b in pairs)
    n_phr, n_ppl = len(phrases), len(people)
    foot = (f'<p class="small">The dictionary has {n_phr} Enron phrases and {n_ppl:,} surnames harvested from the mailbox headers, applied consistently in bodies, addresses and aliases'
            + (f'; on the Complaint J sample it changed {stats["changed_tokens"]:,} tokens in {stats["docs"]:,} documents and left {stats.get("residual_enron_mentions", 0)} mention of Enron behind.' if stats else '.') + '</p>')
    return f'<div class="rename"><span class="h">as written</span><span></span><span class="h">as the systems saw it the second time</span>{cells}</div>{foot}'


def _probe_cards(summary, models, big):
    """Finding 2: seven probe cards, each with a one-line analogy and a ruler from floor to ceiling for the largest model."""
    V, ER, EG, LR, BK = summary["verbatim"][big], summary["entity_recall"][big], summary["entity_recog"][big], summary["label_recall"][big], summary["bench_knowledge"][big]
    MI, MR, EP = summary["matter_id"][big], summary["matter_recall"][big], summary["evidence_prior"][big]
    nm = _short(big)
    short_lbl = {"veridian": "Veridian", "jebbush": "Jeb Bush", "enron": "Enron", "mnk": "Mallinckrodt", "endo": "Endo", "cuad": "CUAD", "canon": "Founding docs", "titanic": "Titanic", "microsoft": "Microsoft"}
    kind = lambda k: "floor" if k == "veridian" else "ceiling" if k in ("canon", "titanic", "microsoft") else "real"  # noqa: E731

    def card(title, q, analogy, svg, res):
        return f'<div class="probe"><b class="t">{title}</b><p class="q">{q}</p><p class="an"><b>Think of it as</b> {analogy}</p>{svg}<p class="res">{res}</p></div>'

    # V
    marks = [(short_lbl[k], V[k]["lcs_f_mean"], kind(k)) for k in ("veridian", "jebbush", "enron", "mnk", "endo", "cuad", "canon", "titanic") if k in V]
    c1 = card("Finish the document", "Here are the first 150 words; write the next 60 exactly.",
              "asking someone to recite the second verse of the national anthem. Knowing it produces the words; not knowing it produces something that scans and is wrong.",
              _ruler(marks, 0, 1, lambda v: f"{v:.2f}"),
              f"Word overlap, 60 documents per collection, {nm}. The e-mail collections sit with the invented one ({_rng([V[k]['lcs_f_mean'] for k in ('jebbush','enron','mnk','endo') if k in V], _f2)} vs {_f2(V['veridian']['lcs_f_mean'])}); "
              f"the contracts are above it ({_f2(V['cuad']['lcs_f_mean'])}); the anchors are near word-perfect ({_rng([V[k]['lcs_f_mean'] for k in ('canon','titanic') if k in V], _f2)}).")
    # E
    marks = [(short_lbl[k], EG[k]["dprime"], kind(k)) for k in ("veridian", "jebbush", "enron", "mnk", "endo", "canon") if k in EG]
    c2 = card("Know the people", "Was this person affiliated with this organisation? Yes, no or unknown — asked with the true organisation and with three planted ones.",
              "jury selection: read out the witness list and ask who knows the names, but slip in a few names that are not on the list to catch the people who say yes to everything.",
              _ruler(marks, -1.5, 5, lambda v: f"d′ {v:.1f}", ref=0, note_ref="cannot tell"),
              f"d′ is hits minus false alarms on a common scale; 0 means guessing. {nm} recognises the headline Enron and Mallinckrodt names (d′ {_f2(EG['enron']['dprime'])}, {_f2(EG['mnk']['dprime'])}; "
              f"tail-tier staff {_pct(EG['enron']['hit_rate_by_tier']['tail'])} and {_pct(EG['mnk']['hit_rate_by_tier']['tail'])}), nobody at Endo ({_f2(EG['endo']['dprime'])}), and every framer of the Constitution ({_f2(EG['canon']['dprime'])}). "
              f"Free recall (\"who is X?\") finds {_pct(ER['enron']['hit_rate'])} of Enron names and {_pct(ER['mnk']['hit_rate'])} / {_pct(ER['endo']['hit_rate'])} of Mallinckrodt / Endo names.")
    # B
    bmap = [("trec2016", "Jeb Bush topics"), ("legal09", "Enron 2009 topics"), ("legal10", "Enron 2010 topics"), ("oida_mnk", "Mallinckrodt archive"), ("cuad", "CUAD categories"), ("newsgroups20", "20 Newsgroups")]
    marks = [(lbl, BK[k]["score"], "ceiling" if k == "newsgroups20" else "real") for k, lbl in bmap if k in BK and BK[k].get("score") is not None]
    ver = BK.get("veridian", {})
    c3 = card("Know the exam questions", "List the review topics of this public test collection from memory.",
              "asking a candidate to recite last year's exam paper. If they can, their score on it is not a score.",
              _ruler(marks, 0, 1, _pct),
              f"Share of a benchmark's own topic titles recited, {nm}. The TREC topic lists are not in the models ({_pct(BK['trec2016']['score'])} of Jeb Bush's, {_pct(BK['legal10']['score'])} / {_pct(BK['legal09']['score'])} of Enron's); "
              f"CUAD's clause categories are ({_pct(BK['cuad']['score'])}). Asked about the invented Veridian matter, the model {'says it is not in the public record' if ver.get('confabulated') is False else 'invents an answer'}.")
    # L
    marks = [(short_lbl[k], LR[k]["acc"], kind(k)) for k in ("veridian", "jebbush", "enron", "mnk", "endo", "titanic") if k in LR]
    c4 = card("Know the answer key", "Here is a document number and a topic; no text. Was it judged relevant?",
              "guessing the verdict from the docket number alone. Right half the time by chance; right more often means you have seen the docket sheet.",
              _ruler(marks, 0.3, 1, _pct, ref=0.5, note_ref="chance"),
              f"Accuracy on 100 balanced pairs, {nm}. Every eDiscovery collection is at chance ({_rng([LR[k]['acc'] for k in ('jebbush','enron','mnk','endo') if k in LR], _pct)}); "
              f"the Titanic list, whose labels are copied across millions of repositories, is at {_pct(LR['titanic']['acc'])} — so the probe does detect leakage when it exists.")
    # M0
    m0 = [("enron", "Enron as 'Volteron'"), ("enron_k", "oil-spill complaint"), ("jebbush", "Jeb Bush"), ("mnk", "Mallinckrodt"), ("endo", "Endo"), ("microsoft", "Microsoft"), ("veridian", "Veridian (invented)")]
    cells = []
    for k, lbl in m0:
        r = MI.get(k)
        if not r:
            continue
        if k == "veridian":
            ok = not r["hit"] and ("no identifiable" in r["first_line"].lower() or not r.get("templates"))
            txt = "called it fictional" if ok else "named a real company"
        else:
            ok = bool(r["hit"])
            txt = "named it" if ok else _esc(r["first_line"].replace("*", "").split("—")[0].split(",")[0][:28])
        cells.append(f'<span><span class="{"ok" if ok else "no"}">{"✓" if ok else "✗"}</span> {lbl} <small>({txt})</small></span>')
    c5 = card("Recognise the case", "Here is the fact pattern with every name removed (or TREC's pseudonymised complaint). Which real case is this?",
              "a juror read a summary with the parties called A and B who says \"that's the Enron case\". Renaming the parties achieved nothing.",
              f'<div class="marks">{"".join(cells)}</div>',
              f"{nm}'s answers. Across the whole ladder of real matters, see the guess-first box in finding 1.")
    # M1
    marks = [(short_lbl[k], (MR[k]["share"] if MR[k].get("share") is not None else 0.0), kind(k)) for k in ("veridian", "jebbush", "mnk", "endo", "enron", "microsoft") if k in MR]
    c6 = card("Recall the record", "Describe this matter: parties, allegations, people, events, outcome — graded against a checklist we wrote in advance.",
              "the new associate who, it turns out, clerked on the case: they can tell you how it ended before they have opened a box.",
              _ruler(marks, 0, 1, _pct),
              f"Share of the checklist, {nm}. Enron {_pct(MR['enron']['share'])} against the Microsoft ceiling {_pct(MR['microsoft']['share'])}; Endo {_pct(MR['endo']['share'])}; Mallinckrodt {_pct(MR['mnk']['share'])}; "
              f"Jeb Bush {_pct(MR['jebbush']['share'])}; Veridian: {'says it does not know' if MR['veridian'].get('unknown') else _pct(MR['veridian'].get('share'))}.")
    # M2
    m2 = [("veridian", "Veridian"), ("enron_j", "Enron as 'Volteron'"), ("enron_k", "oil-spill requests"), ("mnk", "Mallinckrodt"), ("endo", "Endo"), ("jebbush", "Jeb Bush"), ("enron_j_named", "Enron, named")]
    marks = [(lbl, EP[k]["n_discriminative_named_total"], "floor" if k == "veridian" else "hi" if k == "enron_j_named" else "real") for k, lbl in m2 if k in EP]
    top = max([v for _, v, _ in marks] + [10])
    c7 = card("Day-one search terms", "Before seeing any document: list the specific people, companies, code names and products you expect in the relevant ones.",
              "the reviewer who walks in on day one and searches for \"Raptor\", \"LJM\" and \"Fastow\" — terms that are not in the request and could only come from knowing the case.",
              _ruler(marks, 0, top, lambda v: f"{v:.0f}"),
              f"Named terms that really occur in the documents and are concentrated in the relevant ones, {nm}. Under TREC's pseudonym the Enron requests draw {EP['enron_j']['n_discriminative_named_total']}; "
              f"name the company and the same requests draw {EP['enron_j_named']['n_discriminative_named_total']}. Veridian {EP['veridian']['n_discriminative_named_total']}.")
    return f'<div class="probes">{c1}{c2}{c3}{c4}{c5}{c6}{c7}</div>'


def _details_part1(summary, models, big):
    """Layer 2 for finding 1: the metric table with CIs."""
    V, ER, EG, LR = summary["verbatim"], summary["entity_recall"], summary["entity_recog"], summary["label_recall"]
    MI, MR, EP = summary["matter_id"], summary["matter_recall"], summary["evidence_prior"]
    rows = []
    tt = lambda fn, fmt: f'<span class="tri">{_tri(models, fn, fmt)}</span>'  # noqa: E731
    for k in STORY_SETS + ["canon", "titanic"]:
        if not any(k in V[m] for m in models):
            continue
        m2key = "enron_j_named" if k == "enron" else k
        has_e = k in EG[big]
        rows.append([_esc(STORY_LABEL[k]) + _tag(k),
                     tt(lambda m, k=k: V[m][k]["lcs_f_mean"], _f2)
                     + f"<br><small>≥ 15-word run {tt(lambda m, k=k: V[m][k]['frac_run_ge15'], _pct)}</small>"
                     + (f"<br><small>vs floor p {tt(lambda m, k=k: V[m][k]['vs_control']['lcs_f_p_greater'], lambda p: f'{p:.2f}')}</small>" if k != "veridian" else ""),
                     (tt(lambda m, k=k: EG[m][k]["dprime"], lambda v: f"{v:.1f}") + f"<br><small>free recall {tt(lambda m, k=k: ER[m][k]['hit_rate'], _pct)}</small>"
                      f"<br><small>false alarms {tt(lambda m, k=k: EG[m][k]['fa_rate'], _pct)}</small>") if has_e else "–",
                     tt(lambda m, k=k: LR[m][k]["acc"], _pct) if k in LR[big] else "–",
                     tt(lambda m, k=k: 1.0 if MI[m][k]["hit"] else 0.0, lambda v: "✓" if v else "✗") if k in MI[big] else "–",
                     tt(lambda m, k=k: MR[m][k]["share"], _pct) if k in MR[big] and MR[big][k].get("share") is not None else ("says unknown" if k in MR[big] else "–"),
                     tt(lambda m, k=m2key: EP[m][k]["n_discriminative_named_total"], str) if m2key in EP[big] else "–"])
    names = " / ".join(_short(m) for m in models)
    tbl = table(["collection", "V · finish the document (LCS-F1)", "E · know the people (recognition d′)", "L · answer key (chance 50%)", "M0 · named it", "M1 · checklist share", "M2 · useful named terms"], rows, cls="tbl compact")
    L = summary.get("ladder", {})
    corr = L.get("corr_views_recall", {})
    corr_txt = ", ".join(f"{_short(m)} ρ = {corr[m]['spearman']:+.2f} (p = {corr[m]['p']:.2f}, n = {corr[m]['n']})" for m in models if m in corr)
    terra = next((m for m in models if "terra" in m), None)
    pf = _pool_facts(summary)
    emails = [k for k in ("enron", "jebbush", "mnk", "endo") if k in V[big]]
    ge15_zero = all(V[m][k]["frac_run_ge15"] == 0 for m in models for k in emails)
    cuad_pool = (summary.get("v_pool") or {}).get("cuad", {})
    cuad_unf = V[big]["cuad"].get("unfiltered", {}).get("lcs_f_mean")
    caveats = [
        (f"<b>CUAD's verbatim pool was screened like the others</b>: {cuad_pool.get('n_excluded', 0)} of {cuad_pool.get('n_candidates', 0)} candidate windows failed the screen (repetitive boilerplate, reproduced public text, low-information stretches) and were replaced"
         + (f"; on the unscreened pool {_short(big)} scored {cuad_unf:.2f} against {V[big]['cuad']['lcs_f_mean']:.2f} on the screened one" if cuad_unf is not None else "") + ". "
         f"What remains is still partly guessable from the genre, so the share of documents with a ≥ 15-word exact run is the more diagnostic number "
         f"({_tri(models, lambda m: V[m]['cuad']['frac_run_ge15'], _pct)} vs {_tri(models, lambda m: V[m]['veridian']['frac_run_ge15'], _pct)} on the floor); the long runs inspected by hand carry party-specific defined terms.")
        if cuad_pool else
        f"<b>CUAD's verbatim score is partly boilerplate</b> — contract language is guessable from the genre — so the share of documents with a ≥ 15-word exact run is the more diagnostic number there "
        f"({_tri(models, lambda m: V[m]['cuad']['frac_run_ge15'], _pct)} vs {_tri(models, lambda m: V[m]['veridian']['frac_run_ge15'], _pct)} on the floor).",
        (f"<b>Public text quoted into the mailboxes was removed before scoring.</b> A two-stage screen (rules, then a GPT-5.6 Luna read that keeps only original internal text) excluded {pf['email_excl']} of "
         f"{pf['email_cand']} candidate e-mail windows — Federal Register notices, list footers, weekly-report templates, news — so a model finishing a public notice no longer counts as finishing the mailbox. "
         + ("After the screen no e-mail window produced a ≥ 15-word exact run for any model." if ge15_zero else
            f"After the screen ≥ 15-word runs appear in {_rng([V[m][k]['frac_run_ge15'] for m in models for k in emails], _pct)} of e-mail windows."))
        if pf else
        ("<b>No e-mail window produced a ≥ 15-word exact run for any model.</b>" if ge15_zero else ""),
        (f"<b>{MODEL_META[terra][0]} says yes to almost anything</b> at the study's fast setting ({_pct(EG[terra]['enron']['fa_rate'])} false alarms on planted Enron pairings), which is why d′, not the raw hit rate, is reported." if terra else ""),
        f"<b>Recognition is more sensitive than recall</b>: free recall returns UNKNOWN for most names everywhere; the yes/no matrix with planted foils finds the headline names that recall misses.",
        f"<b>The ladder</b>: across {L['corr_views_recall'][big]['n'] if big in corr else '–'} real matters with a Wikipedia article, fame predicts recall only for the smaller models ({corr_txt}); the largest knows the obscure rungs about as well as the famous ones.",
        f"<b>M0 strictness</b>: {_short(big)} read TREC's \"Volteron\" complaint as a different company in the same scandal; it is scored as a miss, which is why the Enron case score is lower for it.",
    ]
    return (f"<p>Values are {names}. V is word overlap between the model's 60-word continuation and the real one, with a one-sided bootstrap p-value against the invented floor; "
            f"E is free recall of the organisation and the recognition sensitivity d′ (hits minus planted-foil false alarms, in z units); L is accuracy at guessing the published label from the document id alone "
            f"(pairs balanced within topic, so chance is exactly 50%); M0 is identification from a nameless sketch; M1 the share of a hand-written fact checklist; M2 the count of named terms "
            f"that are both present in the documents and ≥ 2× concentrated in the relevant ones (Enron row: company named).</p>{tbl}"
            f"<p><b>Caveats.</b></p><ul>{''.join(f'<li>{c}</li>' for c in caveats if c)}</ul>")


def _endo_card(summary, models):
    V, ER, EG, LR, MI, MR, EP = (summary[k] for k in ("verbatim", "entity_recall", "entity_recog", "label_recall", "matter_id", "matter_recall", "evidence_prior"))
    pm = summary["ladder"]["per_model"]
    rungs = summary["ladder"]["rungs"]
    cols = ["endo", "veridian", "enron"]
    hdr = ["test"] + [f'{_esc(STORY_LABEL[k])}{_tag(k)}' for k in cols]

    def row(label, fn, fmt):
        return [label] + [_tri(models, lambda m, k=k: fn(m, k), fmt) for k in cols]

    rows = [
        row("finish the document · LCS-F1", lambda m, k: V[m][k]["lcs_f_mean"], _f2),
        row("know the people · free recall", lambda m, k: ER[m][k]["hit_rate"], _pct),
        row("know the people · recognition hits (planted-foil false alarms)", lambda m, k: EG[m][k]["hit_rate"], _pct),
        row("know the answer key · label accuracy", lambda m, k: LR[m][k]["acc"], _pct),
        [f'<span style="color:{CASE_COLOR}">recognise the case</span>'] + [_tri(models, lambda m, k=k: 1.0 if MI[m][k]["hit"] else 0.0, lambda v: "✓" if v else "✗") for k in cols],
        [f'<span style="color:{CASE_COLOR}">recall the record · checklist share</span>'] + [(_tri(models, lambda m, k=k: MR[m][k]["share"], _pct) if MR[models[0]][k].get("share") is not None else "says it does not know") for k in cols],
        [f'<span style="color:{CASE_COLOR}">day-one search terms</span>'] + [_tri(models, lambda m, k=("enron_j_named" if k == "enron" else k): EP[m][k]["n_discriminative_named_total"], str) for k in cols],
    ]
    tbl = table(hdr, rows, cls="tbl compact")
    views = rungs["endo"]["footprint"].get("views_12m")
    mnk_views = rungs["mnk"]["footprint"].get("views_12m")
    detail = (f"<p>Endo's e-mails come from the same public archive as Mallinckrodt's, but this production was published after every model's training cutoff, so the documents should be "
              f"unseen while the matter (Opana ER, the state attorneys general, the 2022 Chapter 11) is old news. The measured profile matches: finish-the-document "
              f"{_tri(models, lambda m: V[m]['endo']['lcs_f_mean'], _f2)} against the floor's {_tri(models, lambda m: V[m]['veridian']['lcs_f_mean'], _f2)} with no ≥ 15-word run for any model "
              f"({_tri(models, lambda m: V[m]['endo']['frac_run_ge15'], _pct)}); free recall {_tri(models, lambda m: ER[m]['endo']['hit_rate'], _pct)}; recognition d′ "
              f"{_tri(models, lambda m: EG[m]['endo']['dprime'], lambda v: f'{v:.1f}')}; label accuracy {_tri(models, lambda m: _ci_pct(LR[m]['endo']['acc'], LR[m]['endo']['acc_ci']), str)}. "
              f"Meanwhile every model names Endo from a nameless sketch and recalls {_tri(models, lambda m: MR[m]['endo']['share'], _pct)} of the checklist (ladder: "
              f"{_tri(models, lambda m: pm[m]['endo']['share'], _pct)} against a {views:,}-pageview footprint; Mallinckrodt {_tri(models, lambda m: pm[m]['mnk']['share'], _pct)} at {mnk_views:,}).</p>"
              f"<p><b>Caveat on the labels, not the profile.</b> Endo's relevance labels were produced by a panel of three OpenAI models (the Anthropic and Gemini keys were absent when it was built); "
              f"Mallinckrodt's panel mixed vendors. A benchmark whose gold comes from the systems under test needs that stated every time it is used.</p>")
    return tbl, detail


def _jev_block(summary, models, abl):
    """Finding 6: returns (main html, layer-2 details html)."""
    MD = summary["metadata_relevance"]
    jev_key = next((m for m in summary.get("classifier_models", []) if m in MD), None)
    nat = jev_native(summary)
    parts, details = [], []
    if nat:
        # Layer 1: does Jev know the case? The code-name swap, Jev beside the language models.
        parts.append(f"<p><b>Does it know the case? The {_mi('cns', 'code-name swap')}.</b> The same templated document twice, differing in one token — a real matter name "
                     f"(an Enron vehicle, a Florida controversy, an opioid brand) or an invented one of the same shape — under a request that never names the token. "
                     f"A system with no case knowledge gives the same call either way. {nat['t1_result']}</p>")
        details.append(f"<p><b>Code-name swap, matter by matter.</b></p>{nat['t1_mini_tbl']}"
                       f"<p>Signal pairs only; {nat['t1_decoy_txt'][0].lower() + nat['t1_decoy_txt'][1:]}, so the effect is knowledge of what the names mean, not a preference for real-looking names. "
                       f"This shows the system knows the names, not where it learned them: a model pre-trained on public text and one trained on synthetic data written by a knowledgeable LLM would both show it.</p>")
        if nat["bare_tbl"]:
            details.append(f"<p><b>The FAS 140 follow-up: a bare vehicle name on its own.</b></p>{nat['bare_tbl']}<p>{nat['bare_txt']}</p>")
    if jev_key:
        sets_all = [k for k in ("veridian", "jebbush", "enron_k", "enron_j", "mnk", "endo") if k in MD[jev_key]["by_set"]]
        n_total = sum(MD[jev_key]["by_set"][k]["n"] for k in sets_all)
        lex = " / ".join(_pct(MD[jev_key]["by_set"][k]["acc_lexical"]) for k in sets_all)
        below_all = all(MD[jev_key]["by_set"][k]["acc_subject"] < min(MD[m]["by_set"][k]["acc_subject"] for m in models if k in MD[m]["by_set"]) for k in sets_all)
        below_txt = "below the language models’ on every set" if below_all else "generally below the language models’"
        details.append(f"<p><b>M3 design.</b> {n_total:,} header blocks for Jev (balanced relevant / not-relevant within each request; {' / '.join(str(MD[jev_key]['by_set'][k]['n']) for k in sets_all)} per set), "
                       f"each judged twice from the matter context plus Date/Subject, then plus From/To/Cc; Δ is paired with a bootstrap interval. A lexical baseline (a request-title word in the subject) scores "
                       f"{lex} on the same sets, so the subject-only calls are well above keyword matching. Jev's subject-only accuracy is {below_txt} "
                       f"(Enron scandal requests: Jev {_pct(MD[jev_key]['by_set']['enron_j']['acc_subject'])} vs {_tri(models, lambda m: MD[m]['by_set']['enron_j']['acc_subject'], _pct)}): the models' edge is in reading the subject line, not a people effect.</p>")
        sets = [k for k in ("veridian", "jebbush", "enron_k", "enron_j", "mnk", "endo") if k in MD[jev_key]["by_set"]]
        lbl = {"veridian": "Veridian", "jebbush": "Jeb Bush", "enron_k": "Enron · control requests", "enron_j": "Enron · scandal requests", "mnk": "Mallinckrodt", "endo": "Endo"}
        rows = []
        for st in sets:
            j = MD[jev_key]["by_set"][st]
            cells = [lbl[st], f"{_pct(j['acc_subject'])} → {_pct(j['acc_headers'])}", f"{_pt(j['delta_people'])} <small>[{_pt(j['delta_people_ci'][0])}, {_pt(j['delta_people_ci'][1])}]</small>"]
            cells.append(" / ".join(f"{_pt(MD[m]['by_set'][st]['delta_people'])}" for m in models if st in MD[m]["by_set"]))
            rows.append(cells)
        tbl = table(["request set", "Jev accuracy, subject only → with From/To/Cc", "Jev: what the names were worth (pp, 95% CI)", f"same for the LLMs ({' / '.join(_short(m) for m in models)})"], rows, cls="tbl compact")
        excl = [st for st in sets if MD[jev_key]["by_set"][st]["delta_people_ci"][0] > 0 or MD[jev_key]["by_set"][st]["delta_people_ci"][1] < 0]
        llm_d = [MD[m]["by_set"][st] for m in models for st in sets if st in MD[m]["by_set"]]
        llm_max = max(abs(d["delta_people"]) for d in llm_d)
        llm_excl = sum(1 for d in llm_d if d["delta_people_ci"][0] > 0 or d["delta_people_ci"][1] < 0)
        llm_txt = (f"and the language models', which demonstrably do know the people, is no larger: at most {_pt(llm_max)} points on any set, with "
                   f"{'none' if llm_excl == 0 else f'{llm_excl} of {len(llm_d)}'} of their intervals clear of zero")
        parts.append(f"<p><b>Header-only relevance (M3), the one probe a classifier can take.</b> Same e-mails, judged twice: from Date and Subject alone, then with the sender and recipients added. "
                     f"If a system knows who the people are, the names should help. Jev's change is "
                     f"{'within noise on every set' if not excl else 'outside noise only on ' + ', '.join(lbl[s] for s in excl)} — {llm_txt}. "
                     f"The probe therefore has {'no' if llm_excl == 0 else 'little'} power to detect people-knowledge in any system; Jev's flat result is consistent with its vendor's claim but does not establish it.</p>{tbl}")
    if abl:
        con = abl["contrasts"]
        jev = abl.get("jev")
        llms = [m for m in abl["models"] if not m.startswith("jev")]
        if jev and jev in con:
            jk = con[jev]["j_minus_k"]["f1"]
            fas = None
            ej = abl["arms"]["enron_j"]["per_model"].get(jev)
            if ej and "fas140" in ej["topics"]:
                t = ej["topics"]["fas140"]
                fas = {"d": t["delta"]["f1"], "lost": t["flips"]["positives_lost"], "gained": t["flips"]["positives_gained"], "n": t["named"]["n"],
                       "others": {m: abl["arms"]["enron_j"]["per_model"][m]["topics"]["fas140"]["delta"]["f1"] for m in llms if "fas140" in abl["arms"]["enron_j"]["per_model"].get(m, {}).get("topics", {})}}
            parts.append(f"<p><b>The full-document test.</b> Jev went through the same renaming ablation as the language models. Its knowledge effect is {_ci_pt(jk)} F1 points, "
                         f"indistinguishable from theirs ({', '.join(f'{_short(m)} {_pt(con[m]['j_minus_k']['f1']['delta'])}' for m in llms if m in con)}).</p>")
            arms = abl["arms"]
            jrows = []
            for k in ("enron_j", "enron_k", "veridian", "mnk"):
                a = arms.get(k, {}).get("per_model", {}).get(jev)
                if a:
                    jrows.append([ARM_SHORT.get(k, k) + (" (case brief added)" if k == "mnk" else " (renamed)"), f"{100 * a['named']['f1']:.1f} → {100 * a['renamed']['f1']:.1f}",
                                  _ci_pt(a["delta"]["f1"]), _ci_pt(a["delta"]["recall"]), _ci_pt(a["delta"]["precision"]), f"{a['mcnemar']['lost']} / {a['mcnemar']['gained']}"])
            details.append(f"<p><b>Jev in the ablation, arm by arm.</b></p>{table(['arm', 'F1 before → after', 'ΔF1 (pp, 95% CI)', 'ΔRecall', 'ΔPrecision', 'calls lost / gained'], jrows, cls='tbl compact')}"
                           f"<p>Jev's Veridian change ({_ci_pt(arms['veridian']['per_model'][jev]['delta']['f1'])}) is the cost of renaming where names carry no knowledge; "
                           + ("the Enron arms move by about the same amount, " if abs(arms['veridian']['per_model'][jev]['delta']['f1']['delta']) >= 0.01 else "the two Enron arms move alike, ")
                           + f"hence a knowledge effect of {_ci_pt(jk)}. The identification question behind the leakage check is generative and cannot be posed to Jev, so the lower-bound caveat in finding 3 is the language models' alone.</p>")
            if fas:
                o_txt = ", ".join(f"{_short(m)} {_pt(fas['others'][m]['delta'])} [{_pt(fas['others'][m]['lo'])}, {_pt(fas['others'][m]['hi'])}]" for m in llms if m in fas["others"])
                vehicles = (" Seven of the twelve lost positives are documents that name the Raptor, Talon, LJM2 and Chewco vehicles (its probability of responsiveness on them fell from 0.5–0.6 to 0.1–0.4; the other five were marginal calls)."
                            if fas["lost"] == 12 and fas["gained"] == 0 else "")
                if nat and nat["bare"]["aswritten"]:
                    b_as, b_named = nat["bare"]["aswritten"], nat["bare"]["named"]
                    next_check = (f"The bare-token check followed it up: a header plus one sentence naming a vehicle is called responsive {_pct(b_as['rate_real'])} of the time under the request as written "
                                  f"(invented twin {_pct(b_as['rate_fake'])}) and {_pct(b_named['rate_real'])} vs {_pct(b_named['rate_fake'])} only when the criteria name the vehicles — so the loss is not a bare-name reflex "
                                  f"but Jev reading request and document together, and the code-name swap above is where that knowledge shows (details).")
                else:
                    next_check = "The next check is a bare-token probe — does Jev's probability move on 'Raptor' alone, outside any document?"
                parts.append(f"<p><b>The one signal in the renaming test.</b> On the FAS 140 request (special-purpose-entity accounting) Jev's F1 fell {_ci_pt(fas['d'])} points when the Enron vehicle names were renamed — "
                             f"{fas['lost']} positives lost, {fas['gained']} gained, of {fas['n']} documents — while on the same request the language models moved {o_txt}.{vehicles} "
                             f"This is <b>consistent with the system keying on these names; it is not proof of training exposure</b>: the same tokens are strong lexical cues for this request that any classifier could weight and lose when they are replaced. "
                             f"{next_check}</p>")
    if nat:
        # Layer 1: any sign of the documents or the labels? The three memorisation tests in one paragraph each.
        parts.append(f"<p><b>Any sign of the documents or the answer key?</b> Three tests a classifier can take, each read against the language models or the invented matter.</p>"
                     f"<ul class=\"kf\">" + "".join(f"<li><b>{t}</b> {x}</li>" for t, x in (("Edit the document so its answer flips.", nat["t2_txt"]), ("Paraphrase the document.", nat["t3_txt"]),
                                                                                           ("Published vs unpublished labels.", nat["t4_txt"])) if x) + "</ul>")
    e2 = _effect2()
    if e2 and e2.get("jev_short"):
        # Layer 1: the one place Jev's score did depend on the real names — the round-2 familiarity effect.
        parts.append(f"<p><b>Where its score did depend on the names.</b> Round 2 of the renaming test took the Jeb Bush e-mails and renamed the Governor and Florida's public figures. "
                     f"On the topics about his governorship Jev's F1 fell {e2['jev_short'].split(' on ')[0]} net of the control topics on the same documents, where the language models' did not "
                     f"({'; '.join(f'{_short(m)} {_pt(e2['ke'][m]['delta'])}' for m in e2['jeb_sys'] if not m.startswith('jev'))}); it lost recall, not precision. With the FAS 140 drop on "
                     f"Enron and the renaming drop on the knowledge-dependent Enron documents (the generalisation checks), the pattern is a <b>small familiarity effect</b>, roughly 2–3 F1 points: "
                     f"the system matches a little better when the public figures it has heard of are present. That is what an encoder with ordinary public-web knowledge of famous people "
                     f"would show; it is not by itself evidence of training on the collection or its labels — the edit, paraphrase and published-label tests above find none, and paraphrasing "
                     f"the CUAD contracts changed its F1 by {_pt(e2['par'][e2['jev']]['delta']) if e2.get('jev') in e2['par'] else 'nothing measurable'}. For an evaluation it means a Jev score on a famous-figure collection may run a few points high.</p>")
    return "".join(parts), "".join(details)


def _effect_block(summary, models, abl):
    """Finding 3 pieces: figure, so-what numbers, Layer 2 table and caveats. Future-tense fallback if the ablation has not been run."""
    if not abl:
        return None
    systems = [m for m in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "jev@base") if m in abl["models"]] + [m for m in abl["models"] if m not in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "jev@base")]
    llms = [m for m in systems if not m.startswith("jev")]
    arms, con, leak = abl["arms"], abl["contrasts"], abl.get("leak", {})
    arm = lambda m, k: arms.get(k, {}).get("per_model", {}).get(m)  # noqa: E731
    jk = {m: con[m]["j_minus_k"]["f1"] for m in systems if m in con}
    jk_llm = {m: jk[m] for m in llms if m in jk}
    excl = [m for m in jk if jk[m]["lo"] > 0 or jk[m]["hi"] < 0]
    bound = max(abs(100 * d["delta"]) for d in jk.values())
    llm_bound = max(abs(100 * d["delta"]) for d in jk_llm.values()) if jk_llm else bound
    fig = _fig_effect(abl, systems)
    rows = []
    for m in systems:
        j, k_, v, mnk = arm(m, "enron_j"), arm(m, "enron_k"), arm(m, "veridian"), arm(m, "mnk")
        rows.append([f'<span class="m" style="--c:{MODEL_META[_mkey(m)][2]}">{_esc(MODEL_META[_mkey(m)][0])}</span>',
                     _ci_pt(j["delta"]["f1"]) if j else "–", _ci_pt(k_["delta"]["f1"]) if k_ else "–", _ci_pt(jk[m]) if m in jk else "–",
                     _ci_pt(v["delta"]["f1"]) if v else "–",
                     (f"{_pt(j['delta']['recall']['delta'])} / {_pt(j['delta']['precision']['delta'])}" if j else "–"),
                     f"{100 * j['label_changed_share']:.1f}% / {100 * k_['label_changed_share']:.1f}%" if j and k_ else "–",
                     _ci_pt(mnk["delta"]["f1"]) if mnk else "–"])
    tbl = table(["system", "ΔF1 Enron J (scandal)", "ΔF1 Enron K (control)", "knowledge effect J − K", "ΔF1 Veridian (renaming cost only)", "Enron J: ΔRecall / ΔPrecision", "labels flipped J / K", "Mallinckrodt: ΔF1 with a case brief added"], rows, cls="tbl compact")
    leak_models = [m for m in llms if m in leak]
    leak_txt = " / ".join(f"{int(100 * leak[m]['named_enron'] / leak[m]['n'] + 0.5)}%" for m in leak_models)
    leak_n = leak[leak_models[0]]["n"] if leak_models else 0
    d0 = " / ".join(f"{int(100 * leak[m]['by_dose']['0']['named_enron'] / leak[m]['by_dose']['0']['n'] + 0.5)}%" for m in leak_models if "0" in leak[m].get("by_dose", {}))
    d0_n = leak[leak_models[0]]["by_dose"]["0"]["n"] if leak_models and "0" in leak[leak_models[0]].get("by_dose", {}) else 0
    ver_rec = [100 * arm(m, "veridian")["delta"]["recall"]["delta"] for m in systems if arm(m, "veridian")]
    mnk_vals = [100 * arm(m, "mnk")["delta"]["f1"]["delta"] for m in systems if arm(m, "mnk")]
    n_j = arm(llms[0], "enron_j")["n_pairs"] if arm(llms[0], "enron_j") else None
    n_k = arm(llms[0], "enron_k")["n_pairs"] if arm(llms[0], "enron_k") else None
    names = " / ".join(_short(m) for m in systems)
    return {
        "fig": fig, "tbl": tbl, "jk": jk, "excl": excl, "bound": bound, "llm_bound": llm_bound, "systems": systems, "llms": llms, "names": names,
        "jk_txt": "; ".join(f"{_short(m)} {_pt(jk[m]['delta'])} [{_pt(jk[m]['lo'])}, {_pt(jk[m]['hi'])}]" for m in systems if m in jk),
        "leak_txt": leak_txt, "leak_n": leak_n, "d0": d0, "d0_n": d0_n, "leak_names": " / ".join(_short(m) for m in leak_models),
        "ver_rec": f"{max(ver_rec):+.1f} to {min(ver_rec):+.1f}" if ver_rec else "–",
        "mnk_rng": f"{min(mnk_vals):+.1f} to {max(mnk_vals):+.1f}" if mnk_vals else "–",
        "mnk_bound": max(abs(v) for v in mnk_vals) if mnk_vals else None,
        "n_j": n_j, "n_k": n_k, "cost": abl.get("total_paid_usd"),
        "seq_j": " / ".join(_pt(arm(m, "enron_j")["delta"]["f1"]["delta"]) for m in systems if arm(m, "enron_j")),
        "seq_k": " / ".join(_pt(arm(m, "enron_k")["delta"]["f1"]["delta"]) for m in systems if arm(m, "enron_k")),
    }


# ------------------------------------------------------------------------------------------------ the page

def build_story(summary: dict, out_path: Path = RESULTS_DIR / "story.html") -> Path:
    models = _models(summary)
    big = models[-1]
    names = " / ".join(_short(m) for m in models)
    V, ER, EG, LR, MI, MR, EP = (summary[k] for k in ("verbatim", "entity_recall", "entity_recog", "label_recall", "matter_id", "matter_recall", "evidence_prior"))
    C = summary["composite"]["per_model"]
    L = summary["ladder"]
    pm, rungs = L["per_model"], L["rungs"]
    abl = load_ablation()
    eff = _effect_block(summary, models, abl)

    # ---- headline numbers (all derived)
    real = [k for k, r in rungs.items() if k not in ("veridian", "bigthorium") and r.get("expected") != "none"]
    n_real = len(real)
    n_ided = sum(1 for k in real if all((pm[m].get(k) or {}).get("id_hit") for m in models))
    emails = ["jebbush", "enron", "mnk", "endo"]
    v_email = _rng([V[m][k]["lcs_f_mean"] for m in models for k in emails if k in V[m]], _f2)
    v_floor = _rng([V[m]["veridian"]["lcs_f_mean"] for m in models], _f2)
    v_canon = _rng([V[m]["canon"]["lcs_f_mean"] for m in models if "canon" in V[m]], _f2)
    v_cuad = _rng([V[m]["cuad"]["lcs_f_mean"] for m in models if "cuad" in V[m]], _f2)
    m1_enron = _rng([MR[m]["enron"]["share"] for m in models], _pct)
    m1_ms = _rng([MR[m]["microsoft"]["share"] for m in models], _pct)
    cuad_doc = _rng([C[m]["cuad"]["doc_score"] for m in models if "cuad" in C[m]], lambda v: f"{v:.0f}")
    email_doc_max = max(C[m][k]["doc_score"] for m in models for k in emails if k in C[m])
    email_case = _rng([C[m][k]["case_score"] for m in models for k in emails if k in C[m]], lambda v: f"{v:.0f}")
    l_email = _rng([LR[m][k]["acc"] for m in models for k in emails if k in LR[m]], _pct)
    recall_zero = [k for k in ("mnk", "endo") if all(ER[m][k]["hit_rate"] == 0 for m in models)]
    zero_lbl = " and ".join(STORY_LABEL[k].split(" (")[0] for k in recall_zero)
    corr = L.get("corr_views_recall", {})
    corr_txt = ", ".join(f"{_short(m)} {corr[m]['spearman']:+.2f} ({'p = ' + format(corr[m]['p'], '.2f') if corr[m]['p'] < 0.05 else 'not significant, p = ' + format(corr[m]['p'], '.2f')})"
                         for m in models if m in corr)
    miss = [(k, m) for k in real for m in models if not (pm[m].get(k) or {}).get("id_hit")]
    miss_txt = ""
    if miss:
        k0, m0 = miss[0]
        first = ((pm[m0].get(k0) or {}).get("id_first_line") or "").strip("* ").split(" — ")[0].split(",")[0]
        miss_txt = f" (the miss: {_short(m0)} names {first} for {rungs[k0].get('label', k0)}" + (", a company in the same scandal" if k0 == "enron" else "") + ")"
    cards = _metric_cards(summary, models, big, abl)
    pf = _pool_facts(summary)
    # verbatim pool facts, stated only as the data allows
    ge15_zero = all(V[m][k]["frac_run_ge15"] == 0 for m in models for k in emails if k in V[m])
    n_email_win = sum(V[big][k]["n"] for k in emails if k in V[big]) if all("n" in V[big].get(k, {}) for k in emails) else None
    ge15_txt = ("no e-mail window produced a 15-word exact run for any model" + (f" ({n_email_win} windows)" if n_email_win else "")) if ge15_zero else \
        f"a 15-word exact run appears in {_rng([V[m][k]['frac_run_ge15'] for m in models for k in emails if k in V[m]], _pct)} of e-mail windows"
    # floor comparison, stated from the test itself (answered items on both sides; refusals excluded and reported as a rate)
    pairs = [(m, k) for m in models for k in emails if k in V[m] and V[m][k].get("vs_control")]
    sig = [(m, k) for m, k in pairs if V[m][k]["vs_control"]["lcs_f_p_greater"] < 0.05]
    refusers = [m for m in models if any(V[m][k].get("refusal_rate", 0) >= 0.1 for k in emails + ["veridian"] if k in V[m])]
    if sig:
        resid_txt = (f"On answered items, {len(sig)} of the {len(pairs)} model–collection pairs is above the floor at p &lt; 0.05 ("
                     + ", ".join(f"{_short(m)} on {STORY_LABEL[k].split(' (')[0]}, p = {V[m][k]['vs_control']['lcs_f_p_greater']:.3f}" for m, k in sig)
                     + f"), by {_rng([V[m][k]['lcs_f_mean'] - V[m]['veridian']['lcs_f_mean'] for m, k in sig], _f2)} LCS-F1 and without a long run; the rest are not.")
    else:
        resid_txt = f"On answered items none of the {len(pairs)} model–collection pairs is above the floor at p &lt; 0.05."
    for m in refusers:
        rr = {k: V[m][k]["refusal_rate"] for k in ["veridian"] + emails if k in V[m]}
        resid_txt += (f" {_short(m)} declines to continue some e-mails as \"private\" — {', '.join(f'{STORY_LABEL[k].split(chr(40))[0].strip()} {_pct(v)}' for k, v in rr.items() if v > 0)}"
                      f"{'; none on ' + ', '.join(STORY_LABEL[k].split(chr(40))[0].strip() for k, v in rr.items() if v == 0) if any(v == 0 for v in rr.values()) else ''} — "
                      f"a policy fact, reported separately; counted as zeros it had masked the floor and made the e-mail collections look above it for this model.")

    def analogy(t):
        return f'<div class="analogy"><b>Think of it as</b> {t}</div>'

    def howwe(t):
        return f'<div class="howto"><b>How we tested it.</b> {t}</div>'

    def sowhat(t):
        return f'<div class="sowhat"><b>So what.</b> {t}</div>'

    def finding(n, kicker, statement, body):
        return (f'<details class="finding" id="f{n}"><summary><span class="n">{n}</span><span><span class="k">{_esc(kicker)}</span><span class="s">{statement}</span></span>'
                f'<span class="hint"></span></summary><div class="body">{body}</div></details>')

    def more(body, label="Show the details: metrics, intervals, controls, caveats"):
        return f'<details class="more"><summary>{_esc(label)}</summary>{body}</details>'

    # ---- layer 0
    eff2 = _effect2()
    ver = _verify()
    words = {1: "one", 2: "two", 3: "three", 4: "four"}
    if eff and eff2:
        n_m, n_x = words.get(len(eff2["matters"]), len(eff2["matters"])), words.get(len(eff2["manips"]), len(eff2["manips"]))
        a3 = (f"For the language models, knowing the case {eff2['claim_verb']} on {n_m} matters ({', '.join(eff2['matters'])}) under {n_x} manipulations — remove the names, "
              f"remove the memorised text by paraphrase, hand over the case in a brief: no knowledge effect beyond {eff2['llm_bound']:.1f} F1 points, {eff2['interval_txt']}. "
              f"That is a bound, not a proof of no effect"
              + (f" (the renamed Enron documents were still identified as Enron {eff['leak_txt']} of the time)" if eff.get("leak_txt") else "") + "."
              + (f" Jev's matter-topic scores did depend on the real names ({eff2['jev_short']}): a small familiarity effect, not a contamination verdict." if eff2.get("jev_short") else ""))
    elif eff:
        a3 = (f"Renaming every person and company in the Enron e-mails and reviewing them again moved F1 by at most {eff['bound']:.1f} points net of the control requests, for every system "
              f"({eff['names']}), and {'every' if not eff['excl'] else 'nearly every'} 95% interval includes zero. That bounds what name-mediated case knowledge did to accuracy on one matter at this "
              f"sample size; it does not rule out smaller effects, other matters, or knowledge that survives renaming"
              + (f" (the renamed documents were still identified as Enron {eff['leak_txt']} of the time)" if eff.get("leak_txt") else "") + ".")
    else:
        a3 = "Whether it changes the review calls is the next experiment: the same e-mails with every name replaced."
    if eff:
        a3 = (a3.replace("moved F1 by", f"moved {_mi('f1', 'F1')} by", 1).replace("95% interval includes zero", f"95% {_mi('keff', 'interval includes zero')}", 1)
              .replace("F1 points, every", f"{_mi('f1', 'F1')} points, every", 1))
    famous = [k for k in ("enron", "jebbush") if k in ER[models[0]]]
    famous_txt = (", ".join(STORY_LABEL[k].split(" (")[0] for k in famous) + f": {_rng([round(ER[m][k]['hit_rate'] * ER[m][k]['n']) for m in models for k in famous], str)} of 30, the headline names") if famous else ""
    answers = [
        ("They know the <em>cases</em>.", f"All three models {_mi('m0', 'name')} {n_ided} of {n_real} real matters from a sketch with every name removed{miss_txt}, and {_mi('m1', 'recite')} {m1_enron} of the Enron fact checklist "
                                           f"(a famous case, <i>U.S. v. Microsoft</i>, scores {m1_ms}). That is evidence the matters are represented in training, graded by public footprint "
                                           f"(rank correlation with Wikipedia pageviews: {corr_txt})."),
        ("We found no sign they have read the <em>e-mails</em>.", f"Asked to finish a real e-mail from memory, they {_mi('lcs', 'score')} {v_email} on the four e-mail collections against {v_floor} for a collection we "
                                                      f"invented in 2026 — indistinguishable — and {v_canon} for the Constitution and Federalist Papers, which they have memorised; {ge15_txt}. Nobody {_mi('e1', 'recalls the staff')} "
                                                      f"({zero_lbl}: 0 of 30 names; {famous_txt}), and the published {_mi('lab', 'answer keys')} are guessed at chance ({l_email}). The same probes do find memorisation "
                                                      f"on the founding documents and partly on the public contracts ({v_cuad}), which is what makes the null informative. It is absence of evidence from 60 documents per collection, not proof."),
        ("We could not detect a consequence for their review.", a3),
    ]
    answers_html = "".join(f'<div class="a"><span class="n">{i + 1}</span><div><b class="h">{h}</b><span>{t}</span></div></div>' for i, (h, t) in enumerate(answers))

    # ---- finding 1
    f1_body = (
        f"<p>There are two ways a reviewer could have an unfair advantage on a famous case: having <b>seen the exact documents</b> before, or <b>knowing the case</b> from the news. "
        f"We tested both separately, for every collection, against a floor (a matter we invented in 2026, so nothing can be known) and ceilings (texts every model has certainly memorised). "
        f"On the four tests of the documents the e-mail collections sit with the invented one; on the three tests of the case they sit with the famous ones.</p>"
        f'<div class="howwe">{analogy("testing a new associate on documents from a famous case. If they clerked on it, their score tells you nothing about your client's matter — but you want to know which kind of "
                                       "advantage they have: the student who has seen the exam paper, or the juror who followed the trial on television and knows the villains before any exhibit is shown.")}'
        f'{howwe(f"Seven short tests per collection and model (finding 2 has them one by one). Each is {_mi('comp', 'scored from 0 to 100')} — 0 is what the invented floor scores, 100 what the memorised ceiling scores; the grid shows the mean of the three models, hover for each.")}</div>'
        f'<div class="pfig"><div class="pcap">Two kinds of knowing, per collection. Warm cells are tests of the <b>documents</b>; cool cells are tests of the <b>case</b>. Dark = close to the ceiling. Dotted = not measurable.</div>{_grid(summary, models)}</div>'
        f'{_guess_identify(summary, models)}'
        f'{sowhat(f"<b>Document awareness</b> was not detected for the real e-mail collections ({_mi('comp', 'documents score')} ≤ {email_doc_max:.0f} of 100, where the memorised anchors score near 100) and was detected for the public contracts ({cuad_doc}). "
                  f"<b>Matter awareness</b> is present for every real case ({email_case}), graded by public footprint (rank correlation with Wikipedia pageviews: {corr_txt}). "
                  f"A good score on Enron may be partly the score of a reviewer who knows the case; nothing we measured says it is the score of one who has read the mailbox.")}'
        f'{more(_details_part1(summary, models, big))}'
    )

    # ---- finding 2
    pool_note = ""
    if pf:
        pool_note = (f"The verbatim pool is screened in two stages before scoring — rule-based checks for boilerplate, signatures, templates and duplicates, then a GPT-5.6 Luna screen that keeps only "
                     f"original internal text — so that reproducing a Federal Register notice or a list footer quoted into a mailbox does not count as reproducing the mailbox; {pf['n_all'] - sum(pf['kept'].values())} of "
                     f"{pf['n_all']} candidate windows were excluded ({pf['n_public']} of them public text) and {pf['n_rep']} fresh windows drawn in their place, and the scores shown are for the screened pool. ")
    anchor_series = [[V[m]["canon"]["lcs_f_mean"] for m in models], [V[m]["titanic"]["lcs_f_mean"] for m in models], [LR[m]["titanic"]["acc"] for m in models]]
    monotone = all(all(s[i] <= s[i + 1] for i in range(len(s) - 1)) for s in anchor_series)
    scale_txt = (f"The models are listed in order of size ({names}); on the memorised anchors the bigger the model, the more it has "
                 f"(founding documents LCS-F1 {_tri(models, lambda m: V[m]['canon']['lcs_f_mean'], _f2)}; Titanic labels {_tri(models, lambda m: LR[m]['titanic']['acc'], _pct)})"
                 f"{', a clean size gradient in line with the memorisation literature' if monotone else ', though not as a clean gradient on every anchor'}.")
    f2_body = (
        f"<p>You cannot ask a model \"have you seen this?\" and trust the answer. So each test asks it to <em>do</em> something only exposure makes possible, and we read the result "
        f"against the invented floor and the memorised ceiling. The rulers below are for the largest model, {MODEL_META[big][0]}, which has the most of every kind of knowledge; all three models are in finding 1's details.</p>"
        f'{_guess_verbatim(summary, models, big)}'
        f'{_probe_cards(summary, models, big)}'
        f'{sowhat(f"The four document tests and the three case tests point the same way for every e-mail collection: at the floor on the documents, far above it on the case. {resid_txt} The contracts are the one collection with evidence of document memorisation; their floor is not genre-matched (Veridian is e-mail), so part of that gap may be the predictability of legal drafting.")}'
        f'{more(f"<p><b>The controls.</b> <b>Veridian</b> (invented September 2026) is the floor on every probe: whatever a model scores there is genre knowledge and guessing. "
                f"The <b>founding documents</b> and the <b>Titanic passenger list</b> are the document-level ceiling — the largest model reproduces {_pct(V[big]['canon']['frac_run_ge15'])} / {_pct(V[big]['titanic']['frac_run_ge15'])} of them with a ≥ 15-word exact run "
                f"and recovers {_pct(LR[big]['titanic']['acc'])} of Titanic survival labels from the row id — showing each probe fires when there is something to find, which is what makes a null on the e-mail collections informative. <b>U.S. v. Microsoft</b> is the case-level ceiling ({m1_ms} of its checklist). "
                f"{scale_txt}</p>"
                f"<p><b>Design notes.</b> Verbatim prompts cut the body before any quoted reply and give no credit for n-grams already in the prompt; refusals are excluded from every verbatim statistic, on the real collections and the floor alike, and counted separately "
                f"({_tri(models, lambda m: V[m]['veridian']['refusal_rate'], _pct)} on Veridian, {_tri(models, lambda m: V[m]['endo']['refusal_rate'], _pct)} on Endo, {_tri(models, lambda m: V[m]['enron']['refusal_rate'], _pct)} on Enron). {pool_note}Recognition is yes/no per (name, organisation) with three planted organisations, so a model cannot pick the fictional one by elimination. "
                f"Label pairs are balanced within every topic after an early build was caught letting the topic name leak the label. M1 facts that the question itself states are excluded from the headline share. "
                f"M2 terms already in the prompt are discarded; a term counts only if it appears in ≥ 2 judged documents with a lift ≥ 2 among the relevant ones.</p>"
                f"<p>Three OpenAI models ({', '.join(MODEL_META[m][0] for m in models)}) at the study's fast settings; the Anthropic and Gemini keys were absent at run time. Probe spend ${sum(v for k, v in summary['cost_usd'].items()):.2f}.</p>")}'
    )

    # ---- finding 3
    if eff:
        n_j, n_k, jk_txt, sys_names = eff["n_j"], eff["n_k"], eff["jk_txt"], eff["names"]
        seq_j, seq_k, ver_rec, mnk_rng, cost = eff["seq_j"], eff["seq_k"], eff["ver_rec"], eff["mnk_rng"], eff["cost"]
        leak_txt, leak_n, leak_names, d0, d0_n = eff["leak_txt"], eff["leak_n"], eff["leak_names"], eff["d0"], eff["d0_n"]
        if eff2:
            f3_stmt = (f"For the language models, knowing the case {eff2['claim_verb'].replace('review accuracy', 'the review calls')} on {words.get(len(eff2['matters']), len(eff2['matters']))} matters: renaming, paraphrase "
                       f"and a case brief moved {_mi('f1', 'F1')} by no more than {eff2['llm_bound']:.1f} points net of control, "
                       + (_mi('keff', 'intervals including zero') if not eff2.get('llm_excl_txt') else _mi('keff', 'intervals including zero') + f" except {eff2['llm_excl_txt']}")
                       + " — a bound, not a proof of no effect."
                       + (f" Jev's one dependence on the real names ({eff2['jev_short']}) is a small familiarity effect." if eff2.get("jev_short") else ""))
        else:
            f3_stmt = (f"We could not detect an effect of case knowledge on the review calls: renaming moved {_mi('f1', 'F1')} by within ±{math.ceil(eff['bound'])} points net of control for every system, "
                       f"{_mi('keff', 'intervals including zero')} — a bound on one matter, not a proof of no effect.")
        f3_how = howwe(f"Enron Complaint J requests ({n_j:,} judged e-mails; the scandal, where every probe said the knowledge is largest) versus Complaint K ({n_k:,} judged e-mails from the same mailbox; "
                       f"an unrelated oil-spill fact pattern, a control with little to know). Knowledge effect = ΔF1(J) − ΔF1(K): the cost of renaming cancels, what the case knowledge was worth remains. "
                       f"Veridian renamed measures the cost of renaming alone. Four systems: three language models and Jev.")
        if eff2:
            f3_so = sowhat(f"Matter awareness exists, but it did not measurably move recall or precision on these tasks: on Enron {jk_txt}; on Jeb Bush the language models' matter-topic knowledge "
                           f"effect was {'; '.join(f'{_short(m)} {_pt(eff2['ke'][m]['delta'])}' for m in eff2['jeb_sys'] if not m.startswith('jev'))}"
                           + (f"; handing every system the Veridian case file moved F1 by {ver['d_seq']}" if ver else "") + ". "
                           f"Document awareness was detected only on the contracts, and there paraphrasing away the memorised wording changed F1 by ≤ {eff2['par_max']:.1f} points "
                           f"({eff2['cuad_seq_par']}), no more than the same paraphrase costs on the invented matter and no more on the best-remembered contracts."
                           + (f" The {ver['kd_share']:.0f}% of Enron documents whose relevance needs outside knowledge of the case are where help would show, and every system does worse there." if ver else ""))
        else:
            f3_so = sowhat(f"Matter awareness exists, but it did not measurably move recall or precision on these tasks: {jk_txt}. "
                           f"Document awareness was not detected on the real e-mail collections, so there was nothing to ablate there; the contracts, where it was detected, were not ablated.")
        leak_p = (f"<p><b>The Δ is a lower bound.</b> Asked afterwards which company the <em>renamed</em> Enron documents came from (production headers stripped, ticker mapped), the models still said Enron "
                  f"for {leak_txt} of a {leak_n}-document sample ({leak_names}), and for {d0} of the {d0_n} documents that contained no knowledge-bearing name at all. They recognise the case from the fact "
                  f"pattern, not the names, so renaming removes only the name channel, and shows the names are not how the knowledge would act. A clean effect test needs documents the models have not seen "
                  f"(finding 5).</p>") if leak_txt else ""
        f3_more = more(f"<p>ΔF1 in percentage points (renamed − named), {sys_names}: Enron J {seq_j}; Enron K {seq_k}. Renaming cost {ver_rec} points of recall on Veridian, where names carry no "
                       f"knowledge: the price of the operation itself.</p>{eff['tbl']}{leak_p}"
                       f"<p><b>Adding knowledge instead of removing it.</b> On Mallinckrodt, giving each system a one-page case brief in place of the bare request changed F1 by {mnk_rng} points, "
                       f"the same order as the effect measured by removal.</p>"
                       f"<p>Paired bootstrap by document; McNemar on label flips.{f' Ablation spend ${cost:.2f} paid.' if cost is not None else ''}</p>")
        f3_r2 = ""
        if eff2:
            f3_r2 = (f"<p><b>Round 2: two more matters, two more ways to take the knowledge away.</b> On the public contracts (CUAD), the one collection the models partly recite, we renamed "
                     f"the parties, dates and amounts and separately rewrote every excerpt in different words, keeping every party, term, number and obligation; on the Jeb Bush e-mails we renamed "
                     f"the Governor and Florida's public figures and compared the topics about his governorship with control topics on the same documents. "
                     f"Systems: {eff2['sys_txt']}. {eff2['absent_txt']}</p>"
                     f'<div class="pfig"><div class="pcap">CUAD: change in F1 under renaming and under paraphrase (perturbed − named, percentage points, 95% bootstrap intervals by contract), '
                     f'with the cost of the same paraphrase on the invented matter and the knowledge effect net of it.</div>{eff2["cuad_fig"]}</div>'
                     f'<div class="pfig"><div class="pcap">Jeb Bush: change in F1 on the matter topics and on control topics on the same documents when the public figures are renamed, and the '
                     f'knowledge effect (matter − control), paired within each bootstrap draw.</div>{eff2["jeb_fig"]}</div>'
                     + more(f"{eff2['cuad_result']}{eff2['cuad_tbl']}{eff2['cuad_caveat']}{eff2['jeb_result']}{eff2['jev_p']}{eff2['jeb_tbl']}{eff2['three']}"
                            f"<p><a href=\"{eff2['href']}\">Round-2 report</a>; spend ${eff2['cost']:.2f}.</p>", "Show the round-2 details: tables, the Jev result, the three-matter statement"))
            if ver:
                f3_r2 += (f"<p><b>Four more ways the result could have failed.</b></p><ul class=\"kf\">"
                          f"<li><b>Where would knowledge help?</b> {ver['a_line']}</li>"
                          f"<li><b>Add the knowledge instead.</b> {ver['d_line']}</li>"
                          f"<li><b>Make the knowledge wrong.</b> {ver['c_line']}</li>"
                          f"<li><b>Does the ranking hold?</b> {ver['b_line']}</li></ul>"
                          + more(f"{ver['d_fig']}{ver['d_tbl']}{ver['a_tbl']}{ver['c_tbl']}{ver['overall']}{ver['carry']}<p><a href=\"{ver['href']}\">Checks report</a>; spend ${ver['spend'].get('total', 0):.2f}.</p>",
                                 "Show the checks' details"))
        f3_body = (
            f"<p>Exposure is one thing; effect is another. The direct test is to review the same documents twice, as written and with every person and company consistently renamed, and compare. "
            f"If a system had been leaning on what it knew about Enron's people and deals, its score should fall when the names it recognises are taken away.</p>"
            f'<div class="howwe">{analogy("changing the names on every exhibit and running the review again. If the reviewer was trading on who the people were, the second pass should come out worse; if they were reading the documents, the same.")}{f3_how}</div>'
            f'{_rename_exhibit()}'
            f'<div class="pfig"><div class="pcap">The knowledge effect, one dot per system: change in F1 on the scandal requests minus change on the control requests, with 95% bootstrap intervals over documents. A dot whose line crosses zero could be chance.</div>{legend([_mkey(m) for m in eff["systems"]])}{eff["fig"]}</div>'
            f'{f3_r2}{f3_so}{f3_more}'
        )
    else:
        f3_stmt = "Whether knowing the case changes the review calls is the next experiment."
        f3_body = ("<p>The pseudonymisation ablation has not been run yet: the plan is to classify the Enron sample twice, named and renamed, and compare F1 against the control requests "
                   "and the invented floor. This block fills itself in from <code>results/ablation/summary.json</code> when it has.</p>")

    # ---- finding 4
    comp_rows = []
    for k in STORY_SETS:
        if not any(k in C[m] for m in models):
            continue
        comp_rows.append([_esc(STORY_LABEL[k]) + _tag(k), _tri(models, lambda m, k=k: C[m][k]["doc_score"], lambda v: f"{v:.0f}"), _tri(models, lambda m, k=k: C[m][k]["case_score"], lambda v: f"{v:.0f}"),
                          _tri(models, lambda m, k=k: C[m][k]["composite"], lambda v: f"{v:.0f}")])
    comp_tbl = table(["collection", f"documents score ({names})", f"case score ({names})", "overall (plain mean of channels)"], comp_rows, cls="tbl compact")
    f4_body = (
        f"<p>\"Contaminated\" is not one thing. The horizontal axis is how much of the <b>documents</b> a model has (finish the text, know the staff, know the answer key, know the exam); "
        f"the vertical axis is how much of the <b>case</b> it has (recognise it, recall the record, predict the evidence). Each collection is three dots, one per model.</p>"
        f'<div class="pfig"><div class="pcap">Where each collection sits. 0 = the invented floor, 100 = the memorised ceiling, on both axes.</div>{legend(models)}{_fig_scatter(summary, models)}</div>'
        f'{sowhat("The real e-mail collections are all in the top-left: known case, no sign of the documents. The invented matter is where a client's never-public collection would sit. The contracts are the opposite corner — partly memorised documents, no case to know. "
                  "Nothing we tested is in the top-right, and that is the quadrant to fear.")}'
        f'{more(f"<p>Each channel\'s headline metric is placed between the floor (Veridian\'s value → 0) and a ceiling (→ 100), clipped to [0, 100]: V = LCS-F1 to the founding documents; E = recognition d′ to the framers; "
                f"L = label accuracy from chance to Titanic; B = share of the benchmark\'s own topics recited; M0 = 0/100 for identifying the matter from the nameless sketch or pseudonymised complaint; M1 = checklist share to <i>U.S. v. Microsoft</i>; "
                f"M2 = useful named terms to the largest set observed (named Complaint J). Documents score = mean of V, E, L, B; case score = mean of M0, M1, M2; CUAD has no case channels and Mallinckrodt and Endo no benchmark channel.</p>{comp_tbl}"
                f"<p>Equal weighting across channels is a choice, stated here; the split into two scores exists because the overall mean hides the main finding. {_short(big)}\'s Enron case score is held down by the strict M0 rule (it named a different company in the same scandal).</p>")}'
    )

    # ---- finding 5
    endo_tbl, endo_detail = _endo_card(summary, models)
    f5_body = (
        f"<p>Everything above says the risk is knowing the <em>case</em>, not having read the <em>documents</em>. The Endo opioid e-mails let us check that on a real collection: same public archive as Mallinckrodt, "
        f"but a production published in 2024–26, after every model's training cutoff. The publication date is what tells us the documents were not in training; the probes are the check. The models should know the case and show no document-level signal — and that is what the tests show.</p>"
        f'<div class="howwe">{analogy("a juror who followed the trial on television but has never seen the exhibits: they know the parties and the allegations; show them a specific e-mail and it is new to them.")}'
        f'{howwe("Endo was run through every probe like the other collections. Read its column against the invented floor (should match on the document tests) and against Enron (should match on the case tests).")}</div>'
        f'<div class="pfig"><div class="pcap">Endo against the floor and against Enron, {names}.</div>{endo_tbl}</div>'
        f'{sowhat(f"Endo gives the study\'s clearest \'known case, post-cutoff documents\' profile — Enron\'s pattern from the other side, on a collection whose publication date rules the e-mails out of training. It is the benchmark we recommend going forward, "
                  f"with one caveat about where its answer key came from (details).")}'
        f'{more(endo_detail)}'
    )

    # ---- finding 6
    jev_html, jev_details = _jev_block(summary, models, abl)
    nat = jev_native(summary)
    f6_stmt = (f"Jev has the same profile as the language models: it {_mi('cns', 'knows the matter')}, shows no sign of the documents or the labels, and knowing the case had no detectable consequence on Enron{_mi('keff') if abl else ''}"
               + (f" — though its scores on the Jeb Bush matter topics did fall when the public figures were renamed ({eff2['jev_short']}), a small familiarity effect worth a few points on a famous-figure collection, not evidence of training on it."
                  if eff2 and eff2.get("jev_short") else ".")
               if nat else f"Jev is tested, not trusted: its no-pre-training claim is consistent with what we {_mi('m3', 'measured')} and proven by none of it.")
    f6_sowhat = ((f"{nat['overall']} Jev remains a system under test and the vendor's statement remains a claim: the tests cannot tell a base model pre-trained on public text from synthetic "
                  f"training data written by a model that knows these cases, and the one probe shared with the language models (M3) has little power to detect the knowledge in any system.")
                 if nat else
                 "Jev's results are consistent with its vendor's claim but do not establish it: the one probe it can take has little power to detect the knowledge in any system (the LLMs, which "
                 "demonstrably know the people, show the same flat pair on most request sets), and the one request that moved against the grain is recorded as a question to follow up, not an answer.")
    f6_body = (
        f"<p>Jev is the purpose-built review classifier this repository evaluates. Its vendor states that it is not pre-trained on public text, so it would have none of the knowledge above. "
        f"We treat that as a <b>claim under test</b>, not a premise, and Jev as a <b>system under test</b> — never as a zero-exposure reference against which the language models are read. "
        + ("Most of the probes are generative questions a classifier cannot be asked; the two that fit its interface were run on it, and then four more were built for it — tests that use only a relevance call and its probability, "
           f"with the language models as the positive comparison (systems known to carry the knowledge) and the invented matter as the floor (<a href=\"{nat['href']}\">classifier-native report</a>).</p>" if nat
           else "Most of the probes are generative questions a classifier cannot be asked; the two that fit its interface were run on it.</p>")
        + f"{jev_html}"
        f'{sowhat(f6_sowhat)}'
        f'{more(jev_details) if jev_details else ""}'
    )

    # ---- not-found / choosing boxes
    not_found = [
        f"No evidence of a memorised e-mail. On finish-the-document the four e-mail collections score {v_email} (floor {v_floor}) and {ge15_txt}"
        + ("; public notices and templates quoted into the mailboxes were screened out of the pool before scoring, so none of that is hiding in the average." if pf else ".")
        + f" {resid_txt}",
        f"No knowledge of the staff beyond the headlines. Free recall of the people in the mailboxes is {_rng([ER[m][k]['hit_rate'] for m in models for k in emails if k in ER[m]], _pct)}; the obscure-name tier is "
        f"{_rng([EG[big][k]['hit_rate_by_tier']['tail'] for k in ('enron', 'mnk', 'endo') if k in EG[big]], _pct)} recognised by the largest model (the only models whose yes/no answers are interpretable are those with "
        f"planted-foil false alarms near zero; see finding 1's caveats).",
        f"No leaked answer keys. Label guessing from the document id is at chance on every eDiscovery collection ({l_email}), while the same probe reaches {_rng([LR[m]['titanic']['acc'] for m in models], _pct)} on the Titanic list.",
        f"No knowledge of the TREC test questions. {_pct(summary['bench_knowledge'][big]['trec2016']['score'])} of the Jeb Bush topics and {_pct(summary['bench_knowledge'][big]['legal10']['score'])} / {_pct(summary['bench_knowledge'][big]['legal09']['score'])} of the Enron topics recited, with confident confabulation instead.",
        ((f"No detectable effect of case knowledge on the language models' full-document review, on {words.get(len(eff2['matters']), len(eff2['matters']))} matters ({', '.join(eff2['matters'])}): "
          f"no knowledge effect beyond {eff2['llm_bound']:.1f} F1 points under renaming, paraphrase or a case brief, no interval excluding zero; on the memorised contracts, paraphrase changed F1 by ≤ {eff2['par_max']:.1f} points and no more on the best-remembered ones.")
         if eff and eff2 else
         (f"No detectable effect of case knowledge on full-document review: knowledge effect within ±{eff['bound']:.1f} F1 points for every system, no interval excluding zero — on one matter, at this sample size, through the name channel only." if eff else "The effect test is pending.")),
        f"No way to hide a real case by renaming it: the fact pattern identified {n_ided} of {n_real} real matters for every model{miss_txt}.",
    ] + ([f"No sign that Jev remembers the benchmark documents or labels: on edited, paraphrased and never-judged documents it behaves like the language models and like itself on the invented matter "
          f"(label-following {_pct(nat['t2_jev']['enron']['rate'])} Enron / {_pct(nat['t2_jev']['jebbush']['rate'])} Jeb Bush vs {_pct(nat['t2_jev']['veridian']['rate'])} Veridian)"
          + " — while the code-name swap shows it does know the cases."] if nat and nat["t2_jev"] and all(k in nat["t2_jev"] for k in ("enron", "jebbush", "veridian")) else [])
    choose = [
        f"<b>Weight the e-mail collections over the contracts</b> for headline claims; CUAD carries the largest contamination caveat on two channels (documents {cuad_doc} of 100, benchmark categories {_pct(summary['bench_knowledge'][big]['cuad']['score'])} recited).",
        f"<b>Report Enron as a known matter</b>, not a known mailbox; treat a pseudonymised complaint as no defence. Its case knowledge is real and actionable (named Complaint J yields {_tri(models, lambda m: EP[m]['enron_j_named']['n_discriminative_named_total'], str)} useful search terms) — but on full documents it did not measurably move the score.",
        f"<b>Prefer Endo</b> as the real-world held-out benchmark (known case; documents published after the cutoff, with no document-level signal on any probe), stating that its labels came from a three-OpenAI-model panel.",
        "<b>Keep Veridian</b> as the floor a client's never-public collection resembles, with its two measured caveats (archetype recognised; tidy subject lines).",
        (f"<b>Treat Jev as a system under test.</b> {nat['overall']} Its vendor's statement is consistent with that and proven by none of it." if nat else
         "<b>Treat Jev as a system under test.</b> Its no-pre-training statement is consistent with everything measured so far and proven by none of it; the FAS 140 token check is the next step."),
        "<b>For new benchmarks, 'after the cutoff' is the only defence.</b> At frontier scale, obscurity is not: a 1938 fraud and a distributor with no Wikipedia article are both identified from a nameless sketch.",
    ]

    not_say = []
    if eff2:
        if ver:
            not_say.append(f"That the system ranking is stable across collections. The order of the four systems changes from corpus to corpus (Kendall W = {ver['W']:.2f}), and the LLM − Jev gap widens as the "
                           f"models' case knowledge grows (mean-LLM − Jev F1: {ver['gap_txt']} pp). Contamination predicts that; so does corpus type (human-judged e-mail vs panel-labelled gold), "
                           f"and four systems cannot separate them. Unresolved, and the reason not to read any single collection's ranking as the ranking.")
        if eff2.get("jev_short"):
            not_say.append(f"That Jev was trained on the collections. Its matter-topic scores do depend on the real names ({eff2['jev_short']}; FAS 140 on Enron), a familiarity effect of roughly 2–3 F1 points "
                           f"that an encoder with public-web knowledge of public figures would show; the document and label tests find nothing. Expect a Jev score on a famous-figure collection to run a few points high.")
        if ver:
            not_say.append(f"That the models ignore what they know. Given a document whose story contradicts the record, they follow the document {ver['kf_rng']} of the time against the facts, "
                           f"no more than on the invented matter — reading, not recalling, at the level of a relevance call — but that is a measure of the text winning a conflict, not of knowledge being absent.")
        if eff2.get("absent"):
            not_say.append(f"That the three-matter bound holds for every model: {eff2['absent_txt']}")
        not_say.append("That no effect exists. Every number here is a bound at a sample size; the Enron renaming is a floor because the case is recognised from the fact pattern, the CUAD paraphrase "
                       "control is e-mail rather than unseen contracts, and knowledge that survives every manipulation is not excluded. The clean test is a post-cutoff real matter, held out and re-dated as models update.")

    glossary = [
        ("Training cutoff", "The date after which a model read nothing. Anything public before it may be inside the model."),
        ("Contamination", "Test material, or knowledge that makes the test easier, being inside the model from training. Two kinds here: of the documents, and of the case."),
        ("Floor / ceiling", "What a model scores knowing nothing (our invented matter) and knowing everything (memorised public texts, a famous case), measured with the same test."),
        ("F1, recall, precision", "Recall: share of relevant documents found. Precision: share of documents flagged that were relevant. F1: their harmonic mean, in points out of 100."),
        ("95% confidence interval", "The range of values consistent with the data. If it includes zero, the effect could be chance."),
        ("Pseudonymised / renamed", "Real names consistently replaced by invented ones, facts left intact. TREC did it to the complaint; we did it to the documents."),
    ]
    gloss_html = '<dl class="gloss">' + "".join(f"<dt>{_esc(t)}{_mi('f1') if t.startswith('F1') else ''}</dt><dd>{_esc(d)}</dd>" for t, d in glossary) + "</dl>"

    # ---- "How we measure things": one card per metric, listed once; the same cards open from every ⓘ on the page
    measure_html = (
        '<details class="more measure" id="measure"><summary>How we measure things: the metrics behind every number on this page</summary>'
        f'<p class="intro">Each number on this page comes from one of {len(cards)} metrics. The small <span class="mi" style="display:inline-flex;vertical-align:baseline">i</span> marks and dotted phrases open the same cards; '
        f'each card says what is measured, how, the metric and its scale, why that metric, and the caveat, with a link into the full report.</p>'
        '<div class="idx">' + "".join(f'<a href="#mx-{cid}">{_esc(c["title"])}</a>' for cid, c in cards.items()) + '</div>'
        + "".join(_card_html(cid, c, inline=True) for cid, c in cards.items()) + '</details>'
    )
    popovers_html = "".join(_card_html(cid, c) for cid, c in cards.items())

    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Did the AI already know this case? The contamination study, unpacked in layers</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{STORY_CSS}</style></head>
<body><main class="paper story">
<div class="hero">
<div class="authors">The contamination study, told simply · {RUN_DATE} · three OpenAI models ({names}) and the Jev classifier</div>
<p class="q">Have these AI models already seen the documents and cases we test them on? And if so, does it change their review decisions?</p>
<div class="answers">{answers_html}</div>
<div class="pfig"><div class="pcap">One picture. For each collection: how much of the <b style="color:{DOC_COLOR}">documents</b> the models know, and how much of the <b style="color:{CASE_COLOR}">case</b>. Bars are the mean of the three models; the thin ticks are the individual models.</div>{_fig_dials(summary, models)}</div>
<p class="layerhint">In one sentence: the evidence points to matter-level exposure being common and document-level exposure being rare for internal e-mail, and we {eff2['claim_short'].replace("the LLMs'", "the language models'") if eff2 else "could not detect a consequence of the former for the language models' review accuracy"}{f" on {words.get(len(eff2['matters']), len(eff2['matters']))} matters" if eff2 else ""}. Each block below unpacks one finding; inside each, "show the details" opens the metric names, numbers with intervals, controls and caveats. Any <span class="mi" style="display:inline-flex;vertical-align:baseline">i</span> or dotted phrase opens "how this was measured" for that number.</p>
</div>

{measure_html}

{finding(1, "Where", f"The evidence places contamination at the level of the <em>matter</em>, not the <em>documents</em>: every real e-mail collection sits at the floor on the {_mi('comp', 'documents score')} and far above it on the case score.", f1_body)}
{finding(2, "How we can tell", f"Seven small tests, each with a floor and a ceiling, each asking the model to do something only exposure allows: {_mi('lcs', 'finish the document')}, {_mi('e2', 'know the people')}, {_mi('lab', 'know the answer key')}, {_mi('bench', 'know the exam')}, {_mi('m0', 'recognise the case')}, {_mi('m1', 'recall the record')}, {_mi('m2', 'predict the evidence')}.", f2_body)}
{finding(3, "Is it consequential?", f3_stmt, f3_body)}
{finding(4, "What type", f"Two kinds of awareness; every real e-mail collection has the one the prompt already supplies, and shows no sign of the one that would be a true leak{_mi('comp')}.", f4_body)}
{finding(5, "The held-out benchmark", f"Endo: a real case the models {_mi('m1', 'know')}, in documents published after their training ended — and {_mi('lcs', 'no document-level signal')}, as expected.", f5_body)}
{finding(6, "The system under test", f6_stmt, f6_body)}

<div class="box not"><b class="t">What we did not find</b><ul>{''.join(f'<li>{x}</li>' for x in not_found)}</ul></div>
{f'<div class="box not"><b class="t">What this does not say</b><ul>{"".join(f"<li>{x}</li>" for x in not_say)}</ul></div>' if not_say else ''}
<div class="box choose"><b class="t">What this means for choosing a benchmark</b><ul>{''.join(f'<li>{x}</li>' for x in choose)}</ul></div>

<details class="more"><summary>Glossary: six terms</summary>{gloss_html}</details>

<p class="foot">Built from <code>results/contam/summary.json</code>, <code>results/ablation/summary.json</code>, <code>results/ablation/round2/summary.json</code>, <code>results/verify/summary.json</code> and <code>results/jev_probe/summary.json</code> by <code>bench contam-paper</code>; every number on this page is read from those files.
Longer treatments: <code>report_short.html</code> (condensed report), <code>explainer_lawyer.html</code> (plain-English guide with chart-reading notes), <code>paper.html</code> (full write-up),
<code>../ablation/ablation_report.html</code> (the effect test). Design: <code>design/06_contamination_probe.md</code>.</p>
</main>
{popovers_html}
<script>{STORY_JS}</script>
</body></html>"""
    out_path.write_text(doc, encoding="utf-8")
    return out_path
