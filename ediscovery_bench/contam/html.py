"""Self-contained HTML report for the contamination probe: results/contam/contamination_report.html.

Reads results/contam/summary.json, scored_items.jsonl, the probe items and the raw model responses. All charts
are inline SVG drawn here (no JS, no external assets), so the file can be mailed or opened from disk.
"""
from __future__ import annotations

import html as H
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from .build import CORPORA, OUT_DIR
from .run import RESULTS_DIR, load_results
from .ladder import LADDER
from .score import CORPUS_ORDER, ENTITY_ORDER, LABEL_ORDER, REFUSAL_KIND_LABEL

MODEL_META = {  # colour encodes size so the scale gradient is visible across every chart
    "gpt-5.6-luna": ("GPT-5.6 Luna", "small", "#8ec1e6"),
    "gpt-5.6-terra": ("GPT-5.6 Terra", "mid", "#2f7fc1"),
    "gpt-5.6-sol": ("GPT-5.6 Sol", "large", "#143a66"),
    "claude-haiku-4.5": ("Claude Haiku 4.5", "small", "#e8b89a"),
    "claude-sonnet-5": ("Claude Sonnet 5", "mid", "#c9743a"),
    "gemini-3.5-flash-lite": ("Gemini 3.5 Flash-Lite", "small", "#a9d9a4"),
    "gemini-3.8-flash": ("Gemini 3.8 Flash", "mid", "#3f9a4f"),
    "jev": ("Jev", "classifier", "#7a4fa3"),
}
CORPUS_SHORT = {
    "veridian": "Veridian (synthetic)", "jebbush": "Jeb Bush e-mails", "enron": "Enron e-mails", "mnk": "Mallinckrodt e-mails", "endo": "Endo opioid e-mails",
    "cuad": "CUAD contracts", "canon": "Founding documents", "titanic": "Titanic CSV", "bigthorium": "Big Thorium (Relativity demo)",
}
ROLE = {"veridian": "floor", "canon": "ceiling", "titanic": "ceiling"}
# real corpora flagged for a property that is not a role on the scale; bigthorium = public documents, invented case (a second floor)
TAG = {"endo": "post-cutoff", "bigthorium": "public-invented"}
ROLE_COLOR = {"floor": "#3f9a4f", "ceiling": "#c9743a", "effect": "#7a4fa3", "post-cutoff": "#7a4fa3", "public-invented": "#2a8a8a"}
ROLE_TEXT = {"public-invented": "public, invented"}  # chip text where the role key is not the words we want on the page


def role_text(role: str | None) -> str:
    return ROLE_TEXT.get(role or "", role or "")


# Spectrum order for the y axes: floor first, then the real corpora, then the ceilings.
SPECTRUM = ["veridian", "bigthorium", "jebbush", "enron", "mnk", "endo", "cuad", "canon", "titanic"]
ENTITY_SPECTRUM = ["veridian", "bigthorium", "jebbush", "enron", "mnk", "endo", "canon"]
LABEL_SPECTRUM = ["veridian", "jebbush", "enron", "mnk", "endo", "titanic"]

INK, INK3, INK4, LINE, PANEL = "#1b1c1a", "#7c7e79", "#a7a9a3", "#dfdfd8", "#fafaf7"


def _pct(v, nd=0):
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{100 * v:.{nd}f}%"


def _sd(v, nd=0):
    """Signed percentage-point delta without a '-0%' artefact."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    r = round(100 * v, nd)
    r = 0.0 if r == 0 else r
    return f"{r:+.{nd}f}%"


def _num(v, nd=2):
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def _esc(s) -> str:
    return H.escape(str(s), quote=True)


def _pool_rows(summary: dict) -> list[tuple[str, dict]]:
    return [(CORPUS_SHORT.get(c, c).split(" (")[0], x) for c, x in (summary.get("v_pool") or {}).items()]


def _pool_class_text(x: dict) -> str:
    labels = {"boilerplate": "boilerplate rules", "public_reproduction": "public text", "template_boilerplate": "template (screen)", "low_information": "low information"}
    return ", ".join(f"{labels.get(k, k)} {v}" for k, v in x["by_class"].items() if k != "kept")


def _bp_method(summary: dict) -> str:
    """Method-section sentences on the two-stage verbatim pool filter, numbers from summary.json."""
    pool = summary.get("v_pool") or {}
    if not pool:
        return ""
    n_all = sum(x["n_candidates"] for x in pool.values())
    n_rules = sum(x["by_class"].get("boilerplate", 0) for x in pool.values())
    n_screen = sum(v for x in pool.values() for k, v in x["by_class"].items() if k not in ("kept", "boilerplate"))
    n_rep = sum(x.get("n_replacements", 0) for x in pool.values())
    exempt = [n for n, x in _pool_rows(summary) if x.get("screen_exempt")]
    kept = ", ".join(f"{n} {x['n_kept']}" for n, x in _pool_rows(summary))
    return (f"A window is a fair test only if its continuation is text that only someone who had seen this collection could produce, so candidate windows pass "
            f"two filters before scoring. Rules (<code>contam/boilerplate.py</code>) remove boilerplate any model writes from genre knowledge (confidentiality and "
            f"privilege disclaimers, signature and footer blocks, forwarded-message headers, unsubscribe footers, auto-replies and bounces, scanner notices, "
            f"protective-order legends), degraded text (OCR noise, degenerate repetition, key: value lists and tables, openings with too little real content) and "
            f"templates or duplicates recurring across the corpus (8-gram document frequency). A small-model screen (<code>contam/screen.py</code>; GPT-5.6 Luna, "
            f"temperature 0) then reads prefix and true continuation and assigns one of four classes — <i>original internal</i>, <i>public reproduction</i> (a "
            f"Federal Register notice, statute, court filing, press release, news or wire story, newsletter, product label, SEC filing or standard clause copied "
            f"into the document), <i>template / boilerplate</i>, <i>low information</i> (header-only or garbled opening; continuation predictable from the prefix) "
            f"— and only <i>original internal</i> windows enter the pool."
            + (f" The {' and '.join(exempt)} anchors are public text by design and are exempt from the public-reproduction class only." if exempt else "")
            + f" Of {n_all} candidate windows, {n_rules} fail the rules and a further {n_screen} fail the screen; the builder draws replacements from the same "
            f"deterministic order until each corpus has its quota ({n_rep} replacement windows in all). Windows in the pool: {kept}. Excluded windows stay in "
            f"the item file and are scored for the record only.")


def _pool_items(models: list[str]) -> list[dict]:
    """Verbatim rows of scored_items.jsonl that are in the pool."""
    si = RESULTS_DIR / "scored_items.jsonl"
    if not si.exists():
        return []
    return [r for r in (json.loads(l) for l in si.open()) if r["probe"] == "verbatim" and r["model"] in models and r.get("v_pool") == "kept"]


def _v_maxrun(summary: dict, corpus: str) -> str:
    models = summary.get("models") or []
    runs = [r["max_run"] for r in _pool_items(models) if r["corpus"] == corpus]
    return str(max(runs)) if runs else "–"


def _v_outliers(summary: dict, models: list[str]) -> str:
    """The long-run paragraph of §8, derived: how many pool windows on the e-mail corpora reach ≥ 8 words, the longest, and what the
    excluded long runs were."""
    rows = _pool_items(models)
    V = summary["verbatim"]
    email = ("enron", "jebbush", "mnk", "endo")
    long_ = [r for r in rows if r["corpus"] in email and r["max_run"] >= 8]
    n_docs = len({r["item_id"] for r in long_})
    longest = max((r["max_run"] for r in long_), default=0)
    novel_docs = len({r["item_id"] for r in long_ if r["novel_run"] >= 8})
    zero = [CORPUS_SHORT.get(c, c).split(" (")[0] for c in email if not any(r["corpus"] == c for r in long_)]
    big = models[-1]
    return ("<p>With the pool filtered, the e-mail corpora have almost no long runs left to inspect: "
            f"{n_docs} window{'s' if n_docs != 1 else ''} across the four corpora reach{'es' if n_docs == 1 else ''} an exact run of ≥ 8 words for any model "
            f"(longest {longest}; {novel_docs} with a novel run of ≥ 8)" + (f", and {' and '.join(zero)} ha{'s' if len(zero) == 1 else 've'} none at all. " if zero else ". ") +
            "The long runs the earlier pool contained were all chaff and are now excluded with their reasons recorded: a 60-word repeated disk-space error "
            "message in Enron (degenerate repetition), a list of internet-famous one-liners (public text), a Federal Register / DEA notice quoted inside a "
            "Mallinckrodt e-mail (34 words — public text, memorised from its source and not from the mailbox), a weekly sales-report template whose bullets "
            "repeat from the prompt (repetition), and an automated expense-report notification (auto-message). "
            f"<b>CUAD</b> is different in kind: {_pct(V[big]['cuad']['frac_run_ge15'])} of pool excerpts have ≥ 15-word runs for the large model after standard "
            "clauses and mirrored provisions are removed, including a SpinCo/RemainCo licence reproduced with its party-specific defined terms intact. Those are not boilerplate.</p>")


def _refusal_paragraph(summary: dict, models: list[str]) -> str:
    """§8 paragraph on refusals, derived from summary['verbatim'][m][c]['refusal_rate' | 'refusal_kinds' | 'lcs_f_mean_all']."""
    V = summary["verbatim"]
    corp = [c for c in SPECTRUM if any(c in V.get(m, {}) for m in models)]
    rates = {m: {c: V[m][c]["refusal_rate"] for c in corp if c in V.get(m, {})} for m in models}
    total = {m: sum(V[m][c].get("n_refused", 0) for c in rates[m]) for m in models}
    refusers = [m for m in models if total[m]]
    short = lambda c: CORPUS_SHORT.get(c, c).split(" (")[0]  # noqa: E731
    out = ("<p><b>Refusals are a policy reading, not a memorisation reading.</b> A response that opens \"I can’t provide the continuation of a "
           "private e-mail\" tells us what the model will do with someone else's correspondence, not whether it has seen it, so every number in this "
           "section — LCS-F1, runs, the strip plot and the Mann-Whitney test against the floor — is computed over the <i>answered</i> items only, "
           "for the real corpora and for Veridian alike, with the refusal rate shown beside it (the refusals-as-zero mean is kept in the summary as "
           "<code>lcs_f_mean_all</code>). The detector requires the response to <i>open</i> with a first-person refusal and to name what is withheld "
           "within its first 30 words; an e-mail that happens to continue \"I apologize for missing the call\" is not a refusal. ")
    if not refusers:
        return out + "No model refused any pool item.</p>"
    for m in refusers:
        r = rates[m]
        hi = [c for c in corp if c in r and r[c] >= 0.1]
        zero = [c for c in corp if c in r and r[c] == 0]
        kinds = Counter()
        for c in r:
            kinds.update(V[m][c].get("refusal_kinds") or {})
        kind_word = {"private": "citing private or non-user-provided text", "copyright": "citing copyright", "other": "giving no reason"}
        kind_txt = ", ".join(f"{n} {kind_word.get(k, k)}" for k, n in kinds.most_common())
        out += (f"<b>{MODEL_META[m][0]}</b> refused {total[m]} of {sum(V[m][c]['n'] for c in r)} pool items ({kind_txt}) and the rate is sharply "
                f"corpus-dependent: " + ", ".join(f"{short(c)} {_pct(r[c])}" for c in corp if c in r and r[c] > 0)
                + (f"; none on {', '.join(short(c) for c in zero)}" if zero else "") + ". ")
        if "veridian" in hi:
            d = V[m]["veridian"]
            email = [c for c in ("enron", "jebbush", "mnk", "endo") if c in r]
            p_old = " / ".join(f"{V[m][c]['vs_control']['lcs_f_p_greater_all']:.3f}" for c in email)
            p_new = " / ".join(f"{V[m][c]['vs_control']['lcs_f_p_greater']:.2f}" for c in email)
            out += (f"The fictional floor is refused most of all — modern-looking corporate e-mail about a product-liability matter reads as private — "
                    f"so scoring refusals as zero would have pushed its LCS-F1 from {d['lcs_f_mean']:.3f} down to {d['lcs_f_mean_all']:.3f} and the e-mail corpora "
                    f"({' / '.join(short(c) for c in email)}) to p = {p_old} against it; on answered items they are p = {p_new}. ")
        if "enron" in zero and ("endo" in hi or "veridian" in hi):
            out += "That the 2001 Enron mail is never refused while the 2010s Endo and Veridian mail is suggests the policy keys on how recent and how corporate the text looks, not on its source. "
    others = [m for m in models if not total[m]]
    if others:
        out += " and ".join(MODEL_META[m][0] for m in others) + (" refused nothing" if len(others) > 1 else " refused nothing") + f" at <code>effort=none</code>. "
    return out + "</p>"


def _bp_paragraph(summary: dict) -> str:
    """Report paragraph on the verbatim pool filter with the per-corpus, per-class counts."""
    pool = summary.get("v_pool") or {}
    if not pool:
        return ""
    rows = [f"<b>{n}</b> {x['n_kept']}/{x['n_candidates']} kept" + (f" ({_pool_class_text(x)})" if _pool_class_text(x) else "")
            + (f", {x['n_replacements']} replacements" if x.get("n_replacements") else "") for n, x in _pool_rows(summary)]
    exempt = [n for n, x in _pool_rows(summary) if x.get("screen_exempt")]
    return ("<p><b>Chaff is not memorisation.</b> A window whose true continuation is a confidentiality disclaimer, a signature block or a forwarded-message header "
            "tests genre knowledge, not training data: every model writes \"This e-mail and any attachments are confidential…\" from scratch. A window whose "
            "continuation is a Federal Register notice, a wire story or a newsletter forwarded into the mailbox tests memorisation of the public web, not of the "
            "collection (the 34-word Mallinckrodt run that was the e-mail corpora's longest is a DEA notice from the Federal Register). And a window whose opening is "
            "header-only or garbled, or whose continuation is a table, a list or a repeat, cannot identify the document even to a model that memorised it. Such windows "
            "are removed in two stages — rules (<code>contam/boilerplate.py</code>) and a GPT-5.6 Luna screen (<code>contam/screen.py</code>) that keeps only "
            "<i>original internal</i> text — and the builder replaces them from the same deterministic order, so the quota per corpus is met with clean windows. "
            "Every V number on this page, including the strip plot and the composite, is computed on the pool; excluded windows stay in the file, are scored for the "
            "record and are flagged per item in <code>scored_items.jsonl</code>. "
            + (f"The {' and '.join(exempt)} anchors are public text by design and are exempt from the public-text class. " if exempt else "")
            + "Pool per corpus: " + "; ".join(rows) + ".</p>")


# ------------------------------------------------------------------------------------------------ SVG primitives

def _svg(w, h, body, cls="fig"):
    return f'<svg class="{cls}" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" xmlns="http://www.w3.org/2000/svg">{body}</svg>'


def dotplot(rows, models, xmin, xmax, ticks, fmt, title, ref=None, width=620, label_w=170, row_h=30, note=None, labels=None, roles=None):
    """rows: [(row_key, {model: (v, lo, hi)})]. One dot per model per row, offset vertically; whiskers for CIs.
    Row labels / roles default to the corpus tables; pass `labels` / `roles` dicts for other row kinds."""
    labels = labels or CORPUS_SHORT
    roles = roles if roles is not None else {**ROLE, **TAG}
    pad_t, pad_b, pad_r = 10, 26, 16
    plot_w = width - label_w - pad_r
    h = pad_t + row_h * len(rows) + pad_b
    x = lambda v: label_w + (v - xmin) / (xmax - xmin) * plot_w  # noqa: E731
    out = []
    for t in ticks:
        out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{pad_t}" y2="{h - pad_b + 4}" stroke="{LINE}" stroke-width="1"/>')
        out.append(f'<text x="{x(t):.1f}" y="{h - pad_b + 17}" font-size="10.5" text-anchor="middle" fill="{INK3}">{_esc(fmt(t))}</text>')
    if ref is not None:
        out.append(f'<line x1="{x(ref):.1f}" x2="{x(ref):.1f}" y1="{pad_t - 4}" y2="{h - pad_b + 4}" stroke="{INK3}" stroke-width="1" stroke-dasharray="3 3"/>')
    offs = {m: (i - (len(models) - 1) / 2) * 7 for i, m in enumerate(models)}
    for r_i, (ck, vals) in enumerate(rows):
        cy = pad_t + row_h * r_i + row_h / 2
        if r_i:
            out.append(f'<line x1="0" x2="{width}" y1="{cy - row_h / 2:.1f}" y2="{cy - row_h / 2:.1f}" stroke="{LINE}" stroke-width="0.6"/>')
        role = roles.get(ck)
        lbl = labels.get(ck, ck)
        out.append(f'<text x="{label_w - 10}" y="{cy + 4:.1f}" font-size="11.5" text-anchor="end" fill="{INK}">{_esc(lbl)}</text>')
        if role:
            out.append(f'<text x="{label_w - 10}" y="{cy + 14:.1f}" font-size="9" text-anchor="end" fill="{ROLE_COLOR[role]}" letter-spacing="0.06em">{role_text(role).upper()}</text>')
        for m in models:
            if m not in vals or vals[m] is None or vals[m][0] is None:
                continue
            v, lo, hi = vals[m]
            col = MODEL_META[m][2]
            yy = cy + offs[m]
            if lo is not None and hi is not None and not (isinstance(lo, float) and math.isnan(lo)):
                out.append(f'<line x1="{x(max(xmin, lo)):.1f}" x2="{x(min(xmax, hi)):.1f}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{col}" stroke-width="1.4" opacity="0.8"/>')
            out.append(f'<circle cx="{x(min(max(v, xmin), xmax)):.1f}" cy="{yy:.1f}" r="4.2" fill="{col}" stroke="#fff" stroke-width="1"><title>{_esc(MODEL_META[m][0])}: {_esc(fmt(v))}</title></circle>')
    cap = f'<div class="figtitle">{_esc(title)}</div>'
    foot = f'<p class="fignote">{_esc(note)}</p>' if note else ""
    return f'<figure>{cap}{_svg(width, h, "".join(out))}{foot}</figure>'


def ladderplot(rungs, per_model, models, title, note=None, width=848, label_w=320, row_h=24, bar_w=90, mark_w=70):
    """One row per matter, ordered by public footprint. Left: a grey bar for log10(12-month Wikipedia pageviews). Middle: M1 recall
    share per model. Right: M0 identification marks (filled = named the matter, hollow = did not, '?' = said it did not know).
    The study's own matters are highlighted."""
    pad_t, pad_b, gap = 22, 26, 14
    plot_x0 = label_w + bar_w + gap
    plot_w = width - plot_x0 - mark_w - gap
    h = pad_t + row_h * len(rungs) + pad_b
    maxlog = max([math.log10(1 + (r["footprint"].get("views_12m") or 0)) for _, r in rungs] + [1])
    x = lambda v: plot_x0 + v * plot_w  # noqa: E731
    out = [f'<text x="{label_w + bar_w / 2:.1f}" y="{pad_t - 9}" font-size="9" text-anchor="middle" fill="{INK3}" letter-spacing="0.06em">PAGEVIEWS (LOG)</text>',
           f'<text x="{x(0.5):.1f}" y="{pad_t - 9}" font-size="9" text-anchor="middle" fill="{INK3}" letter-spacing="0.06em">M1 · SHARE OF FACT CHECKLIST</text>',
           f'<text x="{width - mark_w / 2 - gap / 2:.1f}" y="{pad_t - 9}" font-size="9" text-anchor="middle" fill="{INK3}" letter-spacing="0.06em">M0 · NAMED IT</text>']
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{pad_t}" y2="{h - pad_b + 4}" stroke="{LINE}" stroke-width="1"/>')
        out.append(f'<text x="{x(t):.1f}" y="{h - pad_b + 17}" font-size="10.5" text-anchor="middle" fill="{INK3}">{int(t * 100)}%</text>')
    offs = {m: (i - (len(models) - 1) / 2) * 6 for i, m in enumerate(models)}
    moffs = {m: (i - (len(models) - 1) / 2) * 14 for i, m in enumerate(models)}
    for r_i, (k, r) in enumerate(rungs):
        cy = pad_t + row_h * r_i + row_h / 2
        if r_i:
            out.append(f'<line x1="0" x2="{width}" y1="{cy - row_h / 2:.1f}" y2="{cy - row_h / 2:.1f}" stroke="{LINE}" stroke-width="0.6"/>')
        if r.get("study"):
            out.append(f'<rect x="0" y="{cy - row_h / 2:.1f}" width="{width}" height="{row_h}" fill="#e9eff6" opacity="0.8"/>')
        role = r.get("expected") if r.get("expected") in ROLE_COLOR else None
        lbl = r["label"]
        out.append(f'<text x="{label_w - 8}" y="{cy + 4:.1f}" font-size="11" text-anchor="end" fill="{INK}" font-weight="{"600" if r.get("study") else "400"}">{_esc(lbl)}</text>')
        if role:
            out.append(f'<text x="{6}" y="{cy + 4:.1f}" font-size="8.5" fill="{ROLE_COLOR[role]}" letter-spacing="0.06em">{role_text(role).upper()}</text>')
        elif r.get("study"):
            out.append(f'<text x="{6}" y="{cy + 4:.1f}" font-size="8.5" fill="{INK3}" letter-spacing="0.06em">STUDY</text>')
        fp = r["footprint"]
        v = fp.get("views_12m") or 0
        if fp.get("title"):
            bw = bar_w * math.log10(1 + v) / maxlog
            out.append(f'<rect x="{label_w}" y="{cy - 6:.1f}" width="{bw:.1f}" height="12" fill="{INK4}" opacity="0.55"><title>{_esc(fp["title"])}: {v:,} views</title></rect>')
        else:
            txt = ("straddles cutoff" if r.get("note") else "post-cutoff") if r.get("expected") == "none" else ("fictional" if r.get("expected") in ("floor", "public-invented") else "no article")
            out.append(f'<text x="{label_w + 2}" y="{cy + 3.5:.1f}" font-size="9" fill="{INK3}">{txt}</text>')
        unk_drawn = False
        for m in models:
            pm = per_model.get(m, {}).get(k)
            if not pm:
                continue
            col = MODEL_META[m][2]
            if pm.get("share") is not None:
                yy = cy + offs[m]
                out.append(f'<circle cx="{x(pm["share"]):.1f}" cy="{yy:.1f}" r="4" fill="{col}" stroke="#fff" stroke-width="1"><title>{_esc(MODEL_META[m][0])}: {pm["n_hit"]}/{pm["n"]}</title></circle>')
            elif pm.get("unknown") and not unk_drawn:
                unk_drawn = True
                out.append(f'<text x="{x(0) + 6}" y="{cy + 3.5:.1f}" font-size="9" fill="{INK3}">all three: unknown</text>')
            mx = width - mark_w / 2 - gap / 2 + moffs[m]
            if pm.get("id_hit"):
                out.append(f'<circle cx="{mx:.1f}" cy="{cy:.1f}" r="4" fill="{col}"><title>{_esc(MODEL_META[m][0])}: identified</title></circle>')
            elif pm.get("id_unknown"):
                out.append(f'<text x="{mx:.1f}" y="{cy + 3.5:.1f}" font-size="10" text-anchor="middle" fill="{col}">?</text>')
            elif pm.get("id_hit") is False:
                out.append(f'<circle cx="{mx:.1f}" cy="{cy:.1f}" r="4" fill="none" stroke="{col}" stroke-width="1.3"><title>{_esc(MODEL_META[m][0])}: {_esc(pm.get("id_first_line") or "")}</title></circle>')
    cap = f'<div class="figtitle">{_esc(title)}</div>'
    foot = f'<p class="fignote">{_esc(note)}</p>' if note else ""
    return f'<figure>{cap}{_svg(width, h, "".join(out))}{foot}</figure>'


def scatter(points, models, title, note=None, width=760, height=420, xlabel="", ylabel=""):
    """points: [(key, label, x, {model: y}, highlight)]. x linear (already transformed), y in [0,1]."""
    pad_l, pad_r, pad_t, pad_b = 44, 16, 14, 40
    xs = [p[2] for p in points]
    xmin, xmax = (min(xs), max(xs)) if xs else (0, 1)
    xmin, xmax = math.floor(xmin), math.ceil(xmax) if xmax > math.floor(xmax) else xmax + 1
    pw, ph = width - pad_l - pad_r, height - pad_t - pad_b
    X = lambda v: pad_l + (v - xmin) / (xmax - xmin) * pw  # noqa: E731
    Y = lambda v: pad_t + (1 - v) * ph  # noqa: E731
    out = []
    for t in range(int(xmin), int(xmax) + 1):
        out.append(f'<line x1="{X(t):.1f}" x2="{X(t):.1f}" y1="{pad_t}" y2="{pad_t + ph}" stroke="{LINE}"/>')
        out.append(f'<text x="{X(t):.1f}" y="{pad_t + ph + 15}" font-size="10" text-anchor="middle" fill="{INK3}">10{"⁰¹²³⁴⁵⁶⁷"[t] if 0 <= t <= 7 else "^" + str(t)}</text>')
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        out.append(f'<line x1="{pad_l}" x2="{pad_l + pw}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" stroke="{LINE}"/>')
        out.append(f'<text x="{pad_l - 6}" y="{Y(t) + 3.5:.1f}" font-size="10" text-anchor="end" fill="{INK3}">{int(t * 100)}%</text>')
    out.append(f'<text x="{pad_l + pw / 2:.1f}" y="{height - 6}" font-size="10" text-anchor="middle" fill="{INK3}">{_esc(xlabel)}</text>')
    out.append(f'<text x="12" y="{pad_t + ph / 2:.1f}" font-size="10" text-anchor="middle" fill="{INK3}" transform="rotate(-90 12 {pad_t + ph / 2:.1f})">{_esc(ylabel)}</text>')
    for p_i, (k, lbl, xv, ys, hl) in enumerate(sorted(points, key=lambda p: p[2])):
        vals = [v for v in ys.values() if v is not None]
        if not vals:
            continue
        left = (p_i % 2 == 1) and not hl  # alternate label side to thin the overlap
        # thin vertical tie between the models' points for the same matter
        out.append(f'<line x1="{X(xv):.1f}" x2="{X(xv):.1f}" y1="{Y(max(vals)):.1f}" y2="{Y(min(vals)):.1f}" stroke="{INK4}" stroke-width="{1.2 if hl else 0.6}" opacity="0.7"/>')
        for m in models:
            v = ys.get(m)
            if v is None:
                continue
            out.append(f'<circle cx="{X(xv):.1f}" cy="{Y(v):.1f}" r="{4.6 if hl else 3.6}" fill="{MODEL_META[m][2]}" stroke="#fff" stroke-width="1"><title>{_esc(lbl)} — {_esc(MODEL_META[m][0])}: {v:.0%}</title></circle>')
        if hl:
            out.append(f'<text x="{X(xv) + 7:.1f}" y="{Y(sum(vals) / len(vals)) + 3.5:.1f}" font-size="10" fill="{INK}" font-weight="600">{_esc(lbl)}</text>')
        else:
            lx = X(xv) - 6 if left else X(xv) + 6
            out.append(f'<text x="{lx:.1f}" y="{Y(sum(vals) / len(vals)) + 3.5:.1f}" font-size="8" fill="{INK3}" text-anchor="{"end" if left else "start"}">{_esc(lbl)}</text>')
    cap = f'<div class="figtitle">{_esc(title)}</div>'
    foot = f'<p class="fignote">{_esc(note)}</p>' if note else ""
    return f'<figure>{cap}{_svg(width, height, "".join(out))}{foot}</figure>'


def legend(models):
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{MODEL_META[m][2]}"></i>{_esc(MODEL_META[m][0])} <small>({MODEL_META[m][1]})</small></span>' for m in models
    ) + "</div>"


def stripplot(per_model_runs, models, title, width=300, label_w=130, row_h=26):
    """Small multiples: one panel per model; per corpus row, one dot per document at x = longest exact run (0-60 words)."""
    panels = []
    xmax = 60
    pad_t, pad_b, pad_r = 28, 30, 10
    plot_w = width - label_w - pad_r
    rows = [c for c in SPECTRUM if any(c in per_model_runs.get(m, {}) for m in models)]
    h = pad_t + row_h * len(rows) + pad_b
    for p_i, m in enumerate(models):
        lw = label_w if p_i == 0 else 10
        w = plot_w + lw + pad_r
        x = lambda v: lw + v / xmax * plot_w  # noqa: E731
        out = [f'<text x="{lw}" y="14" font-size="11.5" font-weight="600" fill="{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</text>']
        for t in (0, 15, 30, 45, 60):
            out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{pad_t}" y2="{h - pad_b + 4}" stroke="{LINE}"/>')
            out.append(f'<text x="{x(t):.1f}" y="{h - pad_b + 16}" font-size="10" text-anchor="middle" fill="{INK3}">{t}</text>')
        out.append(f'<line x1="{x(15):.1f}" x2="{x(15):.1f}" y1="{pad_t}" y2="{h - pad_b + 4}" stroke="{INK3}" stroke-dasharray="3 3"/>')
        for r_i, c in enumerate(rows):
            cy = pad_t + row_h * r_i + row_h / 2
            if p_i == 0:
                out.append(f'<text x="{lw - 8}" y="{cy + 4:.1f}" font-size="11" text-anchor="end" fill="{INK}">{_esc(CORPUS_SHORT[c])}</text>')
            runs = per_model_runs.get(m, {}).get(c, [])
            n = len(runs)
            for i, v in enumerate(sorted(runs)):
                jit = ((i * 7919) % 17 - 8) * 0.9  # deterministic jitter
                out.append(f'<circle cx="{x(min(v, xmax)):.1f}" cy="{cy + jit:.1f}" r="2.4" fill="{MODEL_META[m][2]}" fill-opacity="0.55"/>')
            if n:
                mean = sum(runs) / n
                out.append(f'<line x1="{x(mean):.1f}" x2="{x(mean):.1f}" y1="{cy - 10:.1f}" y2="{cy + 10:.1f}" stroke="{INK}" stroke-width="1.6"><title>mean {mean:.1f} words</title></line>')
        panels.append(_svg(w, h, "".join(out), cls="fig strip"))
    cap = f'<div class="figtitle">{_esc(title)}</div>'
    return cap + '<div class="panels">' + "".join(panels) + "</div>"


def heatmap(summary, models, title):
    """Entity recognition: rows = corpus the names came from, cols = organisation asked about; cell = yes rate."""
    cell, lw, th = 54, 118, 70
    orgs = ENTITY_SPECTRUM
    panels = []
    for p_i, m in enumerate(models):
        eg = summary["entity_recog"].get(m, {})
        lwp = lw
        w = lwp + cell * len(orgs) + 8
        h = th + cell * len(orgs) + 8
        out = [f'<text x="{lwp}" y="14" font-size="11.5" font-weight="600" fill="{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</text>']
        for j, o in enumerate(orgs):
            cx = lwp + cell * j + cell / 2
            out.append(f'<text x="{cx:.1f}" y="{th - 8}" font-size="9.5" text-anchor="middle" fill="{INK3}">{_esc(CORPUS_SHORT[o].split(" (")[0].replace(" e-mails", "").replace(" documents", " docs"))}</text>')
        for i, c in enumerate(orgs):
            cy = th + cell * i
            out.append(f'<text x="{lwp - 8}" y="{cy + cell / 2 + 4:.1f}" font-size="10.5" text-anchor="end" fill="{INK}">{_esc(CORPUS_SHORT[c].split(" (")[0].replace(" e-mails", ""))}</text>')
            rates = eg.get(c, {}).get("yes_rate_by_asked_org", {})
            for j, o in enumerate(orgs):
                v = rates.get(o)
                cx = lwp + cell * j
                if v is None:
                    out.append(f'<rect x="{cx}" y="{cy}" width="{cell - 2}" height="{cell - 2}" fill="#f3f2ee"/>')
                    continue
                a = 0.08 + 0.92 * v
                fill = "#2f7fc1" if c == o else "#c9743a"
                out.append(f'<rect x="{cx}" y="{cy}" width="{cell - 2}" height="{cell - 2}" fill="{fill}" fill-opacity="{a:.2f}" stroke="{LINE}"/>')
                tc = "#fff" if v > 0.55 else INK
                out.append(f'<text x="{cx + cell / 2 - 1:.1f}" y="{cy + cell / 2 + 4:.1f}" font-size="11" text-anchor="middle" fill="{tc}">{_pct(v)}</text>')
                if c == o:
                    out.append(f'<rect x="{cx + 0.5}" y="{cy + 0.5}" width="{cell - 3}" height="{cell - 3}" fill="none" stroke="{INK}" stroke-width="1.2"/>')
        out.append(f'<text x="{lwp + cell * len(orgs) / 2:.1f}" y="{h - 2}" font-size="9.5" text-anchor="middle" fill="{INK3}">organisation asked about →</text>')
        panels.append(_svg(w, h, "".join(out), cls="fig heat"))
    cap = f'<div class="figtitle">{_esc(title)}</div>'
    return cap + '<div class="panels">' + "".join(panels) + "</div>" + \
        '<p class="fignote">Rows: the corpus the 30 names were drawn from. Columns: the organisation the model was asked about. ' \
        'Outlined diagonal cells are the true pairing (hit rate); off-diagonal cells are false alarms. Veridian names are fictional, so every yes in that row is a false alarm.</p>'


def tierbars(summary, models, title):
    """Grouped bars: recognition hit rate by name tier (top / mid / tail) per corpus, one panel per model."""
    tiers = ("top", "mid", "tail")
    shades = {"top": 1.0, "mid": 0.65, "tail": 0.32}
    rows = ENTITY_SPECTRUM
    bw, gap, lw, pad_t, pad_b, pad_r, plot_w = 7, 3, 118, 26, 26, 8, 170
    row_h = bw * 3 + gap * 2 + 12
    panels = []
    for p_i, m in enumerate(models):
        eg = summary["entity_recog"].get(m, {})
        lwp = lw if p_i == 0 else 8
        w = lwp + plot_w + pad_r
        h = pad_t + row_h * len(rows) + pad_b
        x = lambda v: lwp + v * plot_w  # noqa: E731
        out = [f'<text x="{lwp}" y="14" font-size="11.5" font-weight="600" fill="{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</text>']
        for t in (0, 0.5, 1):
            out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{pad_t}" y2="{h - pad_b + 3}" stroke="{LINE}"/>')
            out.append(f'<text x="{x(t):.1f}" y="{h - pad_b + 14}" font-size="10" text-anchor="middle" fill="{INK3}">{_pct(t)}</text>')
        for r_i, c in enumerate(rows):
            y0 = pad_t + row_h * r_i + 6
            if p_i == 0:
                out.append(f'<text x="{lwp - 8}" y="{y0 + row_h / 2 - 2:.1f}" font-size="11" text-anchor="end" fill="{INK}">{_esc(CORPUS_SHORT[c].split(" (")[0].replace(" e-mails", ""))}</text>')
            by = eg.get(c, {}).get("hit_rate_by_tier", {})
            for k, t in enumerate(tiers):
                v = by.get(t)
                yy = y0 + k * (bw + gap)
                if v is None:
                    continue
                out.append(f'<rect x="{x(0):.1f}" y="{yy}" width="{max(0.5, v * plot_w):.1f}" height="{bw}" fill="{MODEL_META[m][2]}" fill-opacity="{shades[t]}"><title>{t}: {_pct(v)}</title></rect>')
        panels.append(_svg(w, h, "".join(out), cls="fig"))
    cap = f'<div class="figtitle">{_esc(title)}</div>'
    key = '<div class="legend small"><span><i style="background:#555;opacity:1"></i>top-10 names</span><span><i style="background:#555;opacity:.65"></i>ranks 11–40</span><span><i style="background:#555;opacity:.32"></i>tail (1–2 documents)</span></div>'
    return cap + '<div class="panels">' + "".join(panels) + "</div>" + key


def gridmap(row_keys, row_labels, col_keys, col_labels, values, models, title, note=None, cell=56, lw=150, th=58):
    """Small multiples of a rate grid: values[model][row][col] in 0..1 (or None). Blue intensity = rate."""
    panels = []
    for p_i, m in enumerate(models):
        lwp = lw if p_i == 0 else 8
        w = lwp + cell * len(col_keys) + 8
        h = th + cell * len(row_keys) + 6
        out = [f'<text x="{lwp}" y="14" font-size="11.5" font-weight="600" fill="{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</text>']
        for j, c in enumerate(col_keys):
            out.append(f'<text x="{lwp + cell * j + cell / 2:.1f}" y="{th - 8}" font-size="9.5" text-anchor="middle" fill="{INK3}">{_esc(col_labels[c])}</text>')
        for i, r in enumerate(row_keys):
            cy = th + cell * i
            if p_i == 0:
                out.append(f'<text x="{lwp - 8}" y="{cy + cell / 2 + 4:.1f}" font-size="10.5" text-anchor="end" fill="{INK}">{_esc(row_labels[r])}</text>')
            for j, c in enumerate(col_keys):
                v = (values.get(m, {}).get(r) or {}).get(c)
                cx = lwp + cell * j
                if v is None:
                    out.append(f'<rect x="{cx}" y="{cy}" width="{cell - 2}" height="{cell - 2}" fill="#f3f2ee"/>')
                    out.append(f'<text x="{cx + cell / 2 - 1:.1f}" y="{cy + cell / 2 + 4:.1f}" font-size="10" text-anchor="middle" fill="{INK4}">–</text>')
                    continue
                out.append(f'<rect x="{cx}" y="{cy}" width="{cell - 2}" height="{cell - 2}" fill="#2f7fc1" fill-opacity="{0.06 + 0.94 * v:.2f}" stroke="{LINE}"/>')
                out.append(f'<text x="{cx + cell / 2 - 1:.1f}" y="{cy + cell / 2 + 4:.1f}" font-size="11" text-anchor="middle" fill="{"#fff" if v > 0.55 else INK}">{_pct(v)}</text>')
        panels.append(_svg(w, h, "".join(out), cls="fig heat"))
    cap = f'<div class="figtitle">{_esc(title)}</div>'
    foot = f'<p class="fignote">{_esc(note)}</p>' if note else ""
    return cap + '<div class="panels">' + "".join(panels) + "</div>" + foot


def pairedplot(rows, models, title, labels, roles=None, width=620, label_w=250, row_h=None, note=None, xmin=0.3, xmax=1.0, ref=0.5):
    """rows: [(key, {model: (acc_subject, acc_headers, acc_lexical)})]. For every model an arrow from the subject-only accuracy
    (open circle) to the headers accuracy (filled circle); the grey tick is the lexical baseline; dashed line = chance."""
    roles = roles or {}
    row_h = row_h or (10 * len(models) + 14)
    pad_t, pad_b, pad_r = 10, 26, 16
    plot_w = width - label_w - pad_r
    h = pad_t + row_h * len(rows) + pad_b
    x = lambda v: label_w + (min(max(v, xmin), xmax) - xmin) / (xmax - xmin) * plot_w  # noqa: E731
    out = []
    for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0):
        if xmin <= t <= xmax:
            out.append(f'<line x1="{x(t):.1f}" x2="{x(t):.1f}" y1="{pad_t}" y2="{h - pad_b + 4}" stroke="{LINE}"/>')
            out.append(f'<text x="{x(t):.1f}" y="{h - pad_b + 17}" font-size="10.5" text-anchor="middle" fill="{INK3}">{_pct(t)}</text>')
    out.append(f'<line x1="{x(ref):.1f}" x2="{x(ref):.1f}" y1="{pad_t - 4}" y2="{h - pad_b + 4}" stroke="{INK3}" stroke-dasharray="3 3"/>')
    for r_i, (ck, vals) in enumerate(rows):
        cy0 = pad_t + row_h * r_i
        if r_i:
            out.append(f'<line x1="0" x2="{width}" y1="{cy0:.1f}" y2="{cy0:.1f}" stroke="{LINE}" stroke-width="0.6"/>')
        out.append(f'<text x="{label_w - 10}" y="{cy0 + row_h / 2 + 4:.1f}" font-size="11.5" text-anchor="end" fill="{INK}">{_esc(labels.get(ck, ck))}</text>')
        if roles.get(ck):
            out.append(f'<text x="{label_w - 10}" y="{cy0 + row_h / 2 + 14:.1f}" font-size="9" text-anchor="end" fill="{ROLE_COLOR[roles[ck]]}" letter-spacing="0.06em">{role_text(roles[ck]).upper()}</text>')
        for k, m in enumerate(models):
            if m not in vals or vals[m] is None:
                continue
            a_s, a_h, a_l = vals[m]
            yy = cy0 + 9 + k * 10
            col = MODEL_META[m][2]
            if a_l is not None:
                out.append(f'<line x1="{x(a_l):.1f}" x2="{x(a_l):.1f}" y1="{yy - 4:.1f}" y2="{yy + 4:.1f}" stroke="{INK4}" stroke-width="1.5"><title>lexical baseline {_pct(a_l)}</title></line>')
            out.append(f'<line x1="{x(a_s):.1f}" x2="{x(a_h):.1f}" y1="{yy:.1f}" y2="{yy:.1f}" stroke="{col}" stroke-width="1.6"/>')
            out.append(f'<circle cx="{x(a_s):.1f}" cy="{yy:.1f}" r="3.6" fill="{PANEL}" stroke="{col}" stroke-width="1.6"><title>{_esc(MODEL_META[m][0])} subject only: {_pct(a_s)}</title></circle>')
            out.append(f'<circle cx="{x(a_h):.1f}" cy="{yy:.1f}" r="4" fill="{col}" stroke="#fff" stroke-width="1"><title>{_esc(MODEL_META[m][0])} with From/To/Cc: {_pct(a_h)}</title></circle>')
    cap = f'<div class="figtitle">{_esc(title)}</div>'
    key = ('<div class="legend small"><span><i style="background:transparent;border:1.6px solid #555;border-radius:50%"></i>subject only</span>'
           '<span><i style="background:#555;border-radius:50%"></i>with From / To / Cc</span><span><i style="background:#a7a9a3;width:2px;height:12px"></i>lexical baseline (title word in subject)</span>'
           '<span><i style="background:transparent;border-top:1px dashed #7c7e79;height:0"></i>chance 50%</span></div>')
    foot = f'<p class="fignote">{_esc(note)}</p>' if note else ""
    return f'<figure>{cap}{_svg(width, h, "".join(out))}{key}{foot}</figure>'


# ------------------------------------------------------------------------------------------------ tables

def table(headers, rows, cls="tbl", colgroups=None):
    th = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" if i else f"<th scope=\"row\">{c}</th>" for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'


def _stars(p):
    if p is None or (isinstance(p, float) and math.isnan(p)):
        return ""
    return "<sup>***</sup>" if p < 0.001 else "<sup>**</sup>" if p < 0.01 else "<sup>*</sup>" if p < 0.05 else ""


def _corpus_th(c):
    role = ROLE.get(c) or TAG.get(c)
    tag = f' <span class="role {role}">{role_text(role)}</span>' if role else ""
    return f"{_esc(CORPUS_SHORT.get(c, c))}{tag}"


# ------------------------------------------------------------------------------------------------ report

def _part1(summary: dict, models: list[str]) -> dict:
    """Part I figures and tables (verbatim, entities, benchmark, labels); shared by the full report and the paper."""
    V, ER, EG, BK, LR = summary["verbatim"], summary["entity_recall"], summary["entity_recog"], summary["bench_knowledge"], summary["label_recall"]
    # per-item data for the strip plot
    per_model_runs: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    si = RESULTS_DIR / "scored_items.jsonl"
    if si.exists():
        for line in si.open():
            r = json.loads(line)
            # the strip shows the scored pool (two-stage filter) and, like every V number, only answered items: a refusal has no run
            if r["probe"] == "verbatim" and r["model"] in models and r.get("v_pool") == "kept" and not r.get("refusal"):
                per_model_runs[r["model"]][r["corpus"]].append(int(r["max_run"]))

    # ---- figures ------------------------------------------------------------------------------------------
    pct_fmt = lambda v: f"{100 * v:.0f}%"  # noqa: E731
    fig_v_lcs = dotplot(
        [(c, {m: (V[m][c]["lcs_f_mean"], *V[m][c]["lcs_f_ci"]) for m in models if c in V.get(m, {})}) for c in SPECTRUM],
        models, 0, 1, [0, 0.25, 0.5, 0.75, 1], lambda v: f"{v:.2f}", "V · Verbatim: LCS-F1 of the 60-word continuation (mean, 95% bootstrap CI)",
    )
    fig_v_run = dotplot(
        [(c, {m: (V[m][c]["frac_run_ge15"], None, None) for m in models if c in V.get(m, {})}) for c in SPECTRUM],
        models, 0, 1, [0, 0.25, 0.5, 0.75, 1], pct_fmt, "V · Verbatim: share of documents with an exact run of ≥ 15 consecutive words",
    )
    fig_v_strip = stripplot(per_model_runs, models, "V · Verbatim: longest exact run per document (words, of 60). Dots are documents; the bar is the mean; dashed line = 15 words.")
    fig_e_d = dotplot(
        [(c, {m: (EG[m][c]["dprime"], None, None) for m in models if c in EG.get(m, {})}) for c in ENTITY_SPECTRUM],
        models, -0.5, 5, [0, 1, 2, 3, 4, 5], lambda v: f"{v:.0f}", "E2 · Entity recognition: d′ = z(hit rate) − z(false-alarm rate)", ref=0,
        note="0 = no discrimination between the true organisation and foils; 4.8 is the practical maximum with 30 names and no false alarms.",
    )
    fig_e_hit = dotplot(
        [(c, {m: (EG[m][c]["hit_rate"], *EG[m][c]["hit_ci"]) for m in models if c in EG.get(m, {})}) for c in ENTITY_SPECTRUM],
        models, 0, 1, [0, 0.25, 0.5, 0.75, 1], pct_fmt, "E2 · Entity recognition: hit rate (yes to the true organisation; Wilson 95% CI)",
    )
    fig_e_fa = dotplot(
        [(c, {m: (EG[m][c]["fa_rate"], *EG[m][c]["fa_ci"]) for m in models if c in EG.get(m, {})}) for c in ENTITY_SPECTRUM],
        models, 0, 1, [0, 0.25, 0.5, 0.75, 1], pct_fmt, "E2 · Entity recognition: false-alarm rate (yes to a foil organisation)",
    )
    fig_e_recall = dotplot(
        [(c, {m: (ER[m][c]["hit_rate"], *ER[m][c]["hit_ci"]) for m in models if c in ER.get(m, {})}) for c in ENTITY_SPECTRUM],
        models, 0, 1, [0, 0.25, 0.5, 0.75, 1], pct_fmt, "E1 · Entity free recall: answers that name the corpus's organisation (Wilson 95% CI)",
    )
    fig_heat = heatmap(summary, models, "E2 · Entity recognition matrix: yes-rate by (source of names × organisation asked about)")
    fig_tiers = tierbars(summary, models, "E2 · Recognition hit rate by how prominent the name is in the corpus")
    fig_l = dotplot(
        [(c, {m: (LR[m][c]["acc"], *LR[m][c]["acc_ci"]) for m in models if c in LR.get(m, {})}) for c in LABEL_SPECTRUM],
        models, 0.3, 1, [0.3, 0.5, 0.7, 0.9], pct_fmt, "L · Label recall from the document id alone: accuracy on 100 within-topic-balanced pairs (Wilson 95% CI)", ref=0.5,
        note="Dashed line: chance (50%), which is also the ceiling for any answer based on the topic or the passenger's title alone.",
    )

    # ---- tables -------------------------------------------------------------------------------------------
    def vrow(m):
        cells = [f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>']
        for c in SPECTRUM:
            x = V.get(m, {}).get(c)
            if not x:
                cells.append("–")
                continue
            st = _stars(x["vs_control"]["lcs_f_p_greater"]) if x.get("vs_control") else ""
            cells.append(f'{_num(x["lcs_f_mean"], 3)}{st}<br><small>run ≥8: {_pct(x["frac_run_ge8"])} · ≥15: {_pct(x["frac_run_ge15"])} · mean {x["max_run_mean"]:.1f} w · refuse {_pct(x["refusal_rate"])}</small>')
        return cells
    tbl_v = table(["model"] + [_corpus_th(c) for c in SPECTRUM], [vrow(m) for m in models])

    def erow(m):
        cells = [f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>']
        for c in ENTITY_SPECTRUM:
            x, y = ER.get(m, {}).get(c), EG.get(m, {}).get(c)
            if not x or not y:
                cells.append("–")
                continue
            tiers = " / ".join(_pct(y["hit_rate_by_tier"].get(t)) for t in ("top", "mid", "tail"))
            cells.append(f'recall {_pct(x["hit_rate"])} <small>(unknown {_pct(x["unknown_rate"])})</small><br>'
                         f'recog hit {_pct(y["hit_rate"])} · FA {_pct(y["fa_rate"])} · d′ {y["dprime"]:.1f}<br><small>by tier {tiers}</small>')
        return cells
    tbl_e = table(["model"] + [_corpus_th(c) for c in ENTITY_SPECTRUM], [erow(m) for m in models])

    bq = [("trec2016", "TREC 2016 athome4 topics (34)"), ("legal10", "TREC Legal 2010 topics (4)"), ("legal09", "TREC Legal 2009 topics (7)"),
          ("cuad", "CUAD clause categories (41)"), ("oida_mnk", "OIDA / Mallinckrodt facts (4)"), ("newsgroups20", "20 Newsgroups categories (20) <span class=\"role ceiling\">ceiling</span>"),
          ("veridian", "Veridian ApexHip: confabulated? <span class=\"role floor\">floor</span>"),
          ("relativity_air_demo", "Relativity aiR demo set (Big Thorium): company, counter-party, matter (3) <span class=\"role public-invented\">public, invented</span>")]

    def brow(m):
        cells = [f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>']
        for q, _ in bq:
            x = BK.get(m, {}).get(q)
            if not x:
                cells.append("–")
            elif q == "veridian":
                cells.append("yes" if x.get("confabulated") else "no (said it did not know)")
            elif q == "relativity_air_demo":
                cells.append(f'{_pct(x["score"])} <small>({len(x["recovered"])}/{x.get("n_keys", 3)}: {_esc(", ".join(x["recovered"]) or "nothing")})</small>')
            else:
                cells.append(f'{_pct(x["score"])} <small>({len(x["recovered"])}/{x["n_keys"]})</small>')
        return cells
    tbl_b = table(["model"] + [t for _, t in bq], [brow(m) for m in models])

    def lrow(m):
        cells = [f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>']
        for c in LABEL_SPECTRUM:
            x = LR.get(m, {}).get(c)
            if not x:
                cells.append("–")
                continue
            lo, hi = x["acc_ci"]
            cells.append(f'{_pct(x["acc"])}{_stars(x["p_vs_chance"])} <small>[{_pct(lo)}–{_pct(hi)}]</small><br><small>topic-only ceiling {_pct(x["topic_only_ceiling"])} · answered {x["answered"]}/{x["n"]}</small>')
        return cells
    tbl_l = table(["model"] + [_corpus_th(c) for c in LABEL_SPECTRUM], [lrow(m) for m in models])

    return {"fig_v_lcs": fig_v_lcs, "fig_v_run": fig_v_run, "fig_v_strip": fig_v_strip, "fig_e_d": fig_e_d, "fig_e_hit": fig_e_hit, "fig_e_fa": fig_e_fa, "fig_e_recall": fig_e_recall, "fig_heat": fig_heat, "fig_tiers": fig_tiers, "fig_l": fig_l, "tbl_v": tbl_v, "tbl_e": tbl_e, "tbl_b": tbl_b, "tbl_l": tbl_l, "bq": bq}


def _main_parts(summary: dict) -> dict:
    """The main report in named pieces (head, header, method, results, part2, closing, appendix, tail) so that split.py can reuse them."""
    models = [m for m in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol") if m in summary["models"]] + \
             [m for m in summary["models"] if m not in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol")]
    V, ER, EG, BK, LR = summary["verbatim"], summary["entity_recall"], summary["entity_recog"], summary["bench_knowledge"], summary["label_recall"]

    p1 = _part1(summary, models)
    cmx = _composite(summary, models)
    fig_v_lcs, fig_v_run, fig_v_strip, fig_e_d, fig_e_hit, fig_e_fa, fig_e_recall, fig_heat, fig_tiers, fig_l, tbl_v, tbl_e, tbl_b, tbl_l, bq = (p1[k] for k in ['fig_v_lcs', 'fig_v_run', 'fig_v_strip', 'fig_e_d', 'fig_e_hit', 'fig_e_fa', 'fig_e_recall', 'fig_heat', 'fig_tiers', 'fig_l', 'tbl_v', 'tbl_e', 'tbl_b', 'tbl_l', 'bq'])

    # ---- examples --------------------------------------------------------------------------------------------
    examples_html = _examples(models)
    bench_html = _bench_answers(BK, models, bq)

    # ---- Part II: knowing the case -------------------------------------------------------------------------
    part2 = _part2(summary, models)

    cost = sum(summary["cost_usd"].values())
    n_items = sum(1 for _ in (OUT_DIR / "probes.jsonl").open()) if (OUT_DIR / "probes.jsonl").exists() else 0
    endo_overview = _endo_paragraph(summary, models, link=True)

    head = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Training-data contamination probe · eDiscovery benchmark corpora</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>{CSS}</style></head>
<body><main>
"""
    header = f"""<header>
<h1>Are the benchmark corpora — and the cases behind them — already inside the models?</h1>
<p class="sub">A training-data contamination probe for the eDiscovery relevance-review study, in two parts. Part I asks whether the <em>documents and people</em> of six corpora are inside three models (four channels, two calibration anchors). Part II asks whether the <em>legal matters</em> behind the corpora are — the allegations, the players, the record, the outcome — and whether that knowledge is actionable for a relevance call. Run 2026-10-03; {n_items:,} probe items per model; total API spend ${cost:.2f}.</p>
<nav><span class="navpart">Part I · documents &amp; people</span><a href="#q">1 Question</a><a href="#channels">2 Channels</a><a href="#design">3 Principles</a><a href="#controls">4 Controls</a><a href="#probes">5 Probes</a><a href="#setup">6 Setup</a><a href="#composite">Overview</a><a href="#spectrum">7 Spectrum</a><a href="#rv">8 Verbatim</a><a href="#re">9 Entities</a><a href="#rb">10 Benchmark</a><a href="#rl">11 Labels</a><a href="#profile">12 Verdicts</a>
<span class="navpart">Part II · the case</span><a href="#legal">13 Why the case matters</a><a href="#mprobes">14 Matter probes</a><a href="#m0">15 Identification</a><a href="#m1">16 Recall</a><a href="#ladder">17 The ladder</a><a href="#m2">18 Evidence prior</a><a href="#m3">19 Metadata effect</a><a href="#effect">20 Effect</a><a href="#effect2">20b Round 2: CUAD &amp; Jeb Bush</a><a href="#verify">20c Generalisation checks</a><a href="#jevnative">21 Classifier-native tests</a><a href="#verdicts2">22 Combined verdicts</a><a href="#caveats">23 Caveats</a><a href="#next">24 Next</a></nav>
</header>
"""
    method = f"""<section id="method">
<h2>Part I — Are the documents and the people inside the model?</h2>
<h2 class="sub2">Methodology</h2>

<h3 id="q">1. The question</h3>
<p>The main study scores TypeSafe's Jev against frontier LLMs on relevance review over six corpora. Four of the six are real and have been public for years: the Enron e-mails (released 2003, part of The Pile), the Jeb Bush e-mails (posted on the web by the Bush campaign in 2015, then distributed by NIST), the Mallinckrodt opioid e-mails (UCSF/JHU archive, 2021–23) and CUAD (an NLP benchmark whose contracts are SEC filings). Veridian, written by us in September 2026, is guaranteed to post-date every model's training data; and the sixth corpus, the Endo opioid e-mails (the same UCSF/JHU archive, but a production published in 2024–26, after the models' cutoffs), is real and <em>should</em> post-date it — a held-out collection from a matter the models can know.</p>
<p>If an LLM has already absorbed a corpus — its documents, the people in it, the benchmark built on it, or even the published relevance judgments — its score on that corpus may not transfer to a client's never-seen collection. Jev, whose vendor states it is a System One classifier not pre-trained on public text, would not enjoy the same help if that claim holds; the claim is itself under test in this repository; the full-document ablation (§20) tested it and found Jev's knowledge effect indistinguishable from zero on Enron at that sample size — consistent with the claim, not a demonstration of it{_jev_r2_intro(summary)} — and the classifier-native tests (§21) then probed it through its own interface: {_native_sentence(summary)} So before leaning on any corpus for a headline claim, we want to know: <em>how much of this does the model already know?</em></p>

<h3 id="channels">2. What "already knows" could mean: four channels</h3>
<p>"Contamination" is not one thing. A model could be advantaged through four distinct routes, and each calls for a different measurement.</p>
{table(["channel", "what the model would have absorbed", "how it would help a relevance classifier", "how we detect it"], [
    ["<b>V</b> Verbatim memorisation", "the documents themselves", "recognising a document it has seen (and perhaps its context) rather than reading it", "ask it to continue a document from its opening"],
    ["<b>E</b> Entity knowledge", "the people and organisations in the matter", "resolving ambiguous references (\"Mr. Shaw\", \"the Medicaid meeting\", a custodian's role) that a fresh reviewer would have to infer", "ask who the correspondents are, and whether a name belongs to the organisation"],
    ["<b>B</b> Benchmark knowledge", "the test's own topics and definitions", "knowing what the assessors were looking for, beyond the request text we provide", "ask it to list the benchmark's topics from memory"],
    ["<b>L</b> Label memorisation", "the published relevance judgments", "would invalidate the evaluation outright", "ask for a judgment given only a document id, no text"],
], cls="tbl wide")}
<p>The channels are ordered from "plausible and benign-ish" to "fatal". V and E are the ones most likely to be doing real work in a review task; L is the one that would make a result meaningless; B sits between.</p>

<h3 id="design">3. Design principles</h3>
<ol>
<li><b>Measure exposure, not effect.</b> This probe asks whether the knowledge is <em>in</em> the model. Whether it <em>helps</em> is a separate experiment — the pseudonymisation ablation, reported in §20 — which this probe told us where to run; Part II (§13–19) takes the intermediate step of asking whether the <em>case</em>, as opposed to the documents, is in the model.</li>
<li><b>One cheap probe per channel, no document classification.</b> Every item is a short prompt; the whole battery for three models cost ${cost:.2f}. The study's expensive runs are untouched.</li>
<li><b>Identical treatment for every corpus.</b> Same prompts, same sampling procedure, same scorer; corpora differ only in the material drawn from them.</li>
<li><b>Interpret only relative to controls.</b> Free-text scores have no natural zero (see §4), so every number is read as a position between a floor and a ceiling measured the same way.</li>
<li><b>Same decoding as the study.</b> Each model runs at the study's floor effort setting (<code>reasoning.effort=none</code>) and temperature 0, so this is the configuration whose knowledge we actually care about.</li>
</ol>

<h3 id="controls">4. Why the controls are the point</h3>
<p>Suppose a model continues an Enron e-mail and matches 17% of the original words. Is that memorisation? Not necessarily: e-mails are formulaic, and a model that has never seen the message can still guess "Please let me know if you have any questions" from the register. The raw score is uninterpretable without knowing what guessing alone produces.</p>
<p><b>The floor.</b> Veridian is the answer to "what does a model score when it can know nothing?" It is a corpus of e-mails, memos, chat logs and calendar invites in the same register as the real corpora, written in 2026. Its score on every probe is the genre-knowledge baseline, and any real corpus has to beat it.</p>
<p><b>The ceiling.</b> The first version of this plan used Enron as the contaminated anchor: it is in The Pile, so surely a model has memorised it. The first run falsified that — no model reproduced Enron e-mail text — which left the top of the scale undefined. We therefore added explicit positive controls: material that every model has certainly seen many times, chosen so that each channel has one.</p>
{table(["anchor", "channel", "what it is", "why it anchors the top"], [
    ["<b>canon</b>", "V, E, B", "Federalist Papers, US Constitution, Declaration of Independence (Project Gutenberg); the 30 framers as the cast; 20 Newsgroups as the benchmark", "among the most-replicated English texts on the web; the framers are universally documented; 20 Newsgroups is in every ML tutorial"],
    ["<b>endo</b> <span class=\"role post-cutoff\">post-cutoff</span>", "all", "Endo opioid e-mails: an OIDA production published 2024–26, after every model's training cutoff; the Endo matter itself (Opana ER, 2017–22) is public and old", "not an anchor but a real-world check on the floor: documents published after the models' training data ends, from a case they can know — expected to show Veridian's profile on a real collection"],
    ["<b>titanic</b>", "V, L", "the Kaggle <code>train.csv</code> (891 passengers): CSV row completion for V, PassengerId + name → Survived for L", "the textbook case of row-level memorisation of a labelled dataset; replicated on millions of GitHub repositories"],
], cls="tbl wide")}
<p>With both ends measured, each real corpus can be placed on the spectrum between "knows nothing" and "has it by heart". That is the deliverable.</p>

<h3 id="probes">5. The probes, item by item</h3>
<h4>V · Verbatim continuation</h4>
<p>60 documents per corpus (20 for the Titanic CSV). The prompt shows the headers and the first ~45% of the body and asks for "the next 60 words, exactly as in the original if you recognise it, your best guess otherwise". Two pitfalls are handled at construction: the body is cut <em>before</em> the first quoted reply or forwarded header, because a reply chain is guessable from the headers; and any run of words that already appears in the prompt (digits masked) earns no credit (the <em>novel</em> flag), because a model can copy a repeated template without remembering anything. A third is handled by a two-stage quality filter on the windows themselves — rules for boilerplate and degraded text, then a small-model screen that keeps only original, custodian-authored text and rejects public text reproduced inside the corpus and low-information windows (details and counts in §8). Scores: word-level LCS-F1 against the true continuation; the longest run of consecutive matching words; the share of documents with a run of ≥ 8 and ≥ 15 words. A refusal ("I can’t provide the continuation of a private e-mail…") is detected when the response opens with one and names what it withholds; refusals are excluded from every V statistic, for the real corpora and the floor alike, and reported as a separate rate (§8).</p>
<h4>E1 · Entity free recall</h4>
<p>30 names per corpus, extracted from the From/To/Cc headers and tiered by how many documents they appear in: the 10 most frequent, 10 from ranks 11–40, and 10 from the tail (1–2 documents). The split matters: Ken Lay is world knowledge, a tail-tier correspondent is only knowable from the mailbox. Prompt: "Who is {{name}}, active around {{era}}? Name their organisation and role, or answer UNKNOWN." A hit is an answer that names the corpus's organisation. Veridian's cast is fictional, so a hit is impossible and any non-UNKNOWN answer is a confabulation. (For the canon anchor the cast is fixed and tiered by fame instead.)</p>
<h4>E2 · Entity recognition matrix</h4>
<p>Free recall is a strict test; people often recognise what they cannot recall, and so do models. Each name is therefore also asked, yes/no, against its own organisation <em>and</em> each of the other five (Enron, the Bush administration, Mallinckrodt/Covidien, Endo Pharmaceuticals, Veridian Orthopedics, the framing of the Constitution). Hit rate is yes to the true organisation; the false-alarm rate on foils is the model's acquiescence baseline; d′ combines them. Asking pairwise rather than multiple-choice prevents answering by elimination ("never heard of him → must be the fictional company").</p>
<h4>B · Benchmark knowledge</h4>
<p>Seven free-text questions: list the TREC 2016 athome4 topics; describe TREC Legal 2010 topics 301–304 and 2009 topics 201–207; list CUAD's clause categories; describe the Mallinckrodt collection in the Opioid Industry Documents Archive; describe the (fictional) Veridian ApexHip matter; list the 20 Newsgroups. Graded by the fraction of true titles recovered, and for Veridian by whether the model confabulated or said it did not know.</p>
<h4>L · Label recall from the id alone</h4>
<p>100 (document, topic) pairs per corpus with no document text: "According to the published judgments, was document {{id}} relevant to topic {{t}}?" The pairs are balanced 50/50 <em>within each topic</em>, so that the topic named in the prompt carries no label information and chance is exactly 50%. This was not the original design: the first build balanced across the whole corpus, and the largest model scored 70% on Mallinckrodt — a corpus whose labels were never published — simply by saying "relevant" to every broad issue and "not relevant" to every narrow one. The report now prints the best any topic-only rule could score on the sample beside each accuracy. For Titanic the same logic balances within the passenger's title (Mr/Mrs/Miss/Master), since the title reveals sex and age, which predict survival.</p>

<h3 id="setup">6. Setup</h3>
{table(["", ""], [
    ["corpora", "Enron (EDRM v2 via TREC Legal 2010, 46k docs with text), Jeb Bush (TREC 2016 local subset, 600), Mallinckrodt (1,840), Endo (2,000; labels from a three-OpenAI-model panel), CUAD (6,494 excerpts), Veridian (1,954), canon (85 Federalist essays + Constitution articles + Declaration), Titanic (891 rows)"],
    ["models", ", ".join(f"{MODEL_META[m][0]} ({MODEL_META[m][1]})" for m in models) + ". Anthropic and Gemini models are in the roster but were not run (keys absent); the runner is resumable."],
    ["decoding", "temperature 0; <code>reasoning.effort=none</code>; max 400 output tokens for continuations, 16 for one-word answers"],
    ["items", f"{n_items:,} per model; verbatim: {sum(x['n_candidates'] for x in (summary.get('v_pool') or {}).values()):,} windows in the file, "
              f"{sum(x['n_kept'] for x in (summary.get('v_pool') or {}).values()):,} in the scored pool after the two-stage filter; 149 recall, 745 recognition, 7 benchmark, 500 label"],
    ["statistics", "bootstrap 95% CIs on means; Wilson CIs on rates; one-sided Mann-Whitney vs Veridian for verbatim; two-sided binomial vs 50% for label recall; d′ with the ½-count correction"],
    ["reproducibility", "<code>bench contam-build</code> is deterministic (seed 7); <code>bench contam-run</code> resumes; <code>bench contam-report</code> and <code>bench contam-html</code> regenerate everything from the per-item records"],
], cls="tbl kv")}
<p><b>Pre-registered expectations</b> (written before the run): V: Enron &gt; Jeb Bush &gt; CUAD &gt; Mallinckrodt ≈ Veridian. E: Enron's famous executives ≈ 100%, tail &gt; 0; Jeb Bush top tier high, tail low; Mallinckrodt low throughout; Veridian 0. B: everyone knows CUAD; TREC topics partially. L: chance everywhere. Several of these turned out wrong, which is noted where it happens.</p>
</section>
"""
    results = f"""<section id="results">
<h2 class="sub2">Results</h2>

<h3 id="composite">Overview · documents, case and overall scores per dataset and model</h3>
<p>Before the probe-by-probe results, the whole study on one grid. Each number is a 0–100 <b>contamination score</b>: the dataset's position between the fictional floor (0) and the saturated ceilings (100). Under each model there are three — the <b>documents</b> score (V, E, L, B), the <b>case</b> score (M0, M1, M2) and the overall mean — because the two kinds of knowledge diverge: Enron is near the floor on its documents and near the ceiling on its case. For the largest model the order is {" → ".join(CORPUS_SHORT.get(d, d).split(" (")[0] for d in cmx["order"])}; the two top datasets get there for different reasons — CUAD scores on its documents, Enron on its case. In one sentence: the evidence points to matter-level exposure being common and document-level exposure being rare for internal e-mail, and we {_claim_short(summary)}{_three_matters_short(summary)}.</p>
{endo_overview}
{cmx["fig"]}
<details><summary>Per-channel breakdown and how each channel is scaled</summary>{cmx["note"]}{cmx["tbl"]}</details>
<p class="small">The two halves are also published separately, each with its own matrix: <a href="report_documents.html">knowledge of the benchmark data</a> (Part I) and <a href="report_case.html">knowledge of the case</a> (Part II and the ladder).</p>

<h3 id="spectrum">7. The spectrum</h3>
<p>Each chart below places the eight corpora on one probe's scale, floor at the top and ceilings at the bottom. The reading is the same everywhere: the ceilings are near the maximum, the floor is low but not zero, and the five real eDiscovery corpora sit much closer to the floor — with one exception, CUAD, on documents. Endo, the post-cutoff collection, sits with Veridian on every document channel.</p>
{legend(models)}
<div class="grid2">{fig_v_lcs}{fig_v_run}</div>
<div class="grid2">{fig_e_d}{fig_l}</div>
<p>Two things are visible before any table. First, the scale gradient: on every anchor the large model (dark) is above the mid model, which is above the small one — Federalist LCS-F1 0.36 → 0.63 → 0.94, Titanic labels 70 → 75 → 84%. Second, on the real corpora that gradient is faint: the models differ far less about Enron than about the Constitution.</p>

<h3 id="rv">8. V · Verbatim memorisation</h3>
{fig_v_strip}
<p>The strip plot is the most honest view of verbatim memorisation: it is sparse and bimodal, not a gentle mean. On the canon anchor the large model reproduces 56 of 60 words on average and 98% of essays have a ≥ 15-word exact run; on the Titanic CSV every chunk is reproduced down to ticket numbers and fares. On the e-mail corpora almost every document sits at 2–4 words, which is what two people writing English will share by accident.</p>
{_bp_paragraph(summary)}
{_refusal_paragraph(summary, models)}
{_v_outliers(summary, models)}
{tbl_v}
<p class="fignote">LCS-F1 of the continuation over answered items; stars: one-sided Mann-Whitney vs Veridian, answered items on both sides (* p&lt;0.05, ** p&lt;0.01, *** p&lt;0.001). Sub-line: share of answered documents with an exact run ≥ 8 / ≥ 15 words, mean longest run, and the refusal rate over all pool items.</p>

<h3 id="re">9. E · Entity knowledge</h3>
<div class="grid2">{fig_e_recall}{fig_e_hit}</div>
<div class="grid2">{fig_e_fa}<div></div></div>
{fig_heat}
<p>The matrix separates two very different behaviours. Luna and Sol answer yes almost only on the diagonal: false alarms of {_pct(EG[models[0]]['enron']['fa_rate'])} / {_pct(EG[models[0]]['mnk']['fa_rate'])} and {_pct(EG[models[-1]]['enron']['fa_rate'])} / {_pct(EG[models[-1]]['mnk']['fa_rate'], 1)} on the Enron and Mallinckrodt foils (Sol's one Mallinckrodt false alarm places an opioid-company employee at Endo, the other opioid maker), and their hit rates ({_pct(min(EG[m][c]['hit_rate'] for m in (models[0], models[-1]) for c in ('enron', 'mnk') if EG[m][c]['hit_rate'] > 0))}–{_pct(max(EG[m][c]['hit_rate'] for m in (models[0], models[-1]) for c in ('enron', 'mnk')))}) are therefore real. Terra at <code>effort=none</code> is a yes-sayer — {_pct(min(EG[models[1]][c]['fa_rate'] for c in ('enron', 'mnk', 'jebbush', 'endo')))}–{_pct(max(EG[models[1]][c]['fa_rate'] for c in ('enron', 'mnk', 'jebbush', 'endo')))} yes to foils on the real e-mail corpora, {_pct(EG[models[1]]['mnk']['yes_rate_by_asked_org'].get('veridian', 0))} yes to Mallinckrodt names being at Veridian, a company that does not exist — so its {_pct(min(EG[models[1]][c]['hit_rate'] for c in ('enron', 'mnk', 'jebbush')))}–{_pct(max(EG[models[1]][c]['hit_rate'] for c in ('enron', 'mnk', 'jebbush')))} hit rates mean little and its d′ ({min(EG[models[1]][c]['dprime'] for c in ('enron', 'mnk', 'jebbush')):.1f}–{max(EG[models[1]][c]['dprime'] for c in ('enron', 'mnk', 'jebbush')):.1f}) is the number to read. The canon anchor shows what saturation looks like: 97–100% hits, 0% false alarms, d′ 4.3–4.8 for every model.</p>
{fig_tiers}
<p>The tier breakdown is where the "surrounding details" question is answered. On <b>Enron</b> the knowledge is confined to the famous: Dasovich, Belden, Whalley, Lavorato, Kean — people in the scandal literature — and 0% of tail-tier correspondents for Luna and Sol. On <b>Jeb Bush</b> the same: Shanahan, Stutler, Castille, Fasano — Florida public figures — and little below. On the <b>canon</b> anchor the tail (Jacob Broom, Richard Bassett, William Few) is recognised as reliably as Washington. The eDiscovery corpora are nowhere near that.</p>
<p>The <b>Mallinckrodt</b> result is the one that changes a decision. Free recall is 0% for every model — "Who is Karen Harper?" gets UNKNOWN — but the large model says yes to "was Karen Harper at Mallinckrodt/Covidien" for {_pct(EG[models[-1]]['mnk']['hit_rate'])} of names with {_pct(EG[models[-1]]['mnk']['fa_rate'], 1)} false alarms (d′ {EG[models[-1]]['mnk']['dprime']:.1f}): Harper, Buist, Tetzlaff, Cardetti, Kadlic, Kilper, Wickline. These are real employees named in MDL 2804 filings and press coverage. The e-mails are not memorised, but the cast is recognised from the litigation record. Recall alone would have missed it. <b>Endo</b>, the other opioid corpus, shows the opposite: recognition {' / '.join(_pct(EG[m]['endo']['hit_rate']) for m in models)} with d′ at or below zero for every model — the Endo cast, whose production was published after the cutoff, is not recognised even by the model that recognises Mallinckrodt's.</p>
{tbl_e}

<h3 id="rb">10. B · Benchmark knowledge</h3>
{tbl_b}
<p>The benchmark channel is open for CUAD and closed for TREC. Every model recites CUAD's 41 clause categories and the 20 newsgroups; no model recovers a single athome4 topic (34 of them) or a TREC Legal 2010 topic, and all three confabulate plausible Enron-scandal topics (California crisis, Arthur Andersen, LJM) in place of the real ones (oil and gas drilling, spill response, lobbying, privilege). The TREC-based arms of the study are therefore not helped by topic knowledge. The Veridian question was answered honestly by all three — "not in the public record; possibly synthetic" — which is the right answer.</p>

<h3 id="rl">11. L · Label memorisation</h3>
{tbl_l}
<p>With the within-topic balance in place, every eDiscovery corpus is at chance (45–54%) and the topic-only ceiling is 50% by construction. The Titanic anchor shows the probe is not simply inert: from PassengerId and name alone, after sex and age are balanced out, the models recover 70%, 75% and 84% of survival outcomes. Label leakage is detectable when it exists; on the eDiscovery corpora we found none, at a sample of 100 pairs per corpus (the 95% interval around chance is roughly ±10 points).</p>

<h3 id="profile">12. Per-corpus verdicts</h3>
{table(["corpus", "documents (V)", "cast (E)", "benchmark (B)", "labels (L)", "verdict for the study"], [
    [_corpus_th("veridian"), "floor", "0% hits, 97% UNKNOWN; no confabulation", "not confabulated", "chance", "At the floor on all four channels, as designed; its archetype is recognised (§15) and Luna refuses " + _pct(V[models[0]]["veridian"]["refusal_rate"]) + " of its e-mails as private (§8)."],
    *([[_corpus_th("bigthorium"), "at the floor (LCS-F1 " + " / ".join(f'{V[m]["bigthorium"]["lcs_f_mean"]:.2f}' for m in models if V.get(m, {}).get("bigthorium")) + "; no ≥ 15-word run; ≥ 8-word runs in " + " / ".join(_pct(V[m]["bigthorium"]["frac_run_ge8"]) for m in models if V.get(m, {}).get("bigthorium")) + " of windows; rules-only screen)",
       "recall 0/30 for every model; recognition " + " / ".join(_pct(EG[m]["bigthorium"]["hit_rate"]) for m in models if EG.get(m, {}).get("bigthorium")) + " hits",
       "demo-set facts " + " / ".join(f'{len(BK[m]["relativity_air_demo"]["recovered"])}/{BK[m]["relativity_air_demo"].get("n_keys", 3)}' for m in models if BK.get(m, {}).get("relativity_air_demo")) + "; the sketch is matched to real procurement-bribery cases, never to Big Thorium",
       "not probed",
       "Public documents, invented case: the demo workspace is downloadable, yet behaves like the floor on every channel measured — no verbatim memory, no cast, no case. The second floor beside Veridian in §20 and §21A."]]
      if any(V.get(m, {}).get("bigthorium") for m in models) else []),
    [_corpus_th("jebbush"), "at the floor on answered items; no ≥ 15-word run for any model", "famous Florida figures only; Sol d′ 1.4", "0/34 topics", "chance", "No document-level signal found despite the 2015 web release. What the models know is Florida public life, which the prompt's matter background already supplies."],
    [_corpus_th("enron"), "at the floor on answered items; longest run in the pool " + _v_maxrun(summary, "enron") + " words", "scandal-famous executives only; tail 0%; d′ 1.7–2.2", "0/4, 0–1/7; confabulated", "chance", "The evidence is of exposure to the Enron <em>story</em>, not the mailbox — although the corpus is in open training sets (The Pile), no document-level memory is detectable here. Part II (§18) shows the case itself is in the model; the ablation (§20) bounds the effect of removing the names at a couple of F1 points."],
    [_corpus_th("mnk"), "at the floor; longest run in the pool " + _v_maxrun(summary, "mnk") + " words (a 34-word Federal Register notice is excluded as public text)", "recall 0%, but Sol recognises 30% of staff with 0% false alarms", "knows what OIDA is", "chance", "No document-level signal; the cast is partly recognised by the largest model from the litigation record. Supplying a case brief (§20) moves F1 by under a point."],
    [_corpus_th("endo"), "at the floor (LCS-F1 " + " / ".join(f'{V[m]["endo"]["lcs_f_mean"]:.2f}' for m in models if V.get(m, {}).get("endo")) + ")", "recall 0/30 for every model; recognition " + " / ".join(f'{_pct(EG[m]["endo"]["hit_rate"])}' for m in models if EG.get(m, {}).get("endo")) + " hits", "n/a (no published topics)", "chance (" + " / ".join(_pct(LR[m]["endo"]["acc"]) for m in models if LR.get(m, {}).get("endo")) + ")", "The post-cutoff collection: no document-level signal and an unrecognised cast, as the publication date predicts. The document-level profile Veridian was written to imitate, on a real corpus. Recommended held-out benchmark going forward."],
    [_corpus_th("cuad"), "<b>above the e-mail floor</b>: ≥15-word runs in " + _pct(min(V[m]["cuad"]["frac_run_ge15"] for m in models if V.get(m, {}).get("cuad"))) + "–" + _pct(max(V[m]["cuad"]["frac_run_ge15"] for m in models if V.get(m, {}).get("cuad"))) + " of excerpts, party-specific", "n/a", "<b>41/41</b> categories", "n/a", "Consistent with memorisation of republished public contracts; the floor is not genre-matched, so part of the gap may be the predictability of legal drafting. Report with that caveat; do not use for headline claims."],
    [_corpus_th("canon"), "saturated (0.94 LCS-F1, 98% long runs for Sol)", "saturated (100% hits, 0% FA)", "20/20", "n/a", "Ceiling behaves as a ceiling."],
    [_corpus_th("titanic"), "saturated (rows reproduced verbatim)", "n/a", "n/a", "<b>70–84%</b>", "The label probe detects leakage when it exists."],
], cls="tbl wide")}
</section>
"""
    from .bigthorium import section_html as _bigthorium_section  # noqa: PLC0415  (empty string unless results/contam/bigthorium_summary.json exists)
    part2_html = _part2_html(part2, summary, models).replace('<h3 id="verdicts2">', _m3_jev_note(summary, models) + '\n' + _effect_section(summary) + '\n' + _jev_native_section(summary) + '\n' + _bigthorium_section() + '\n<h3 id="verdicts2">', 1)
    closing = f"""<section id="closing">
<h3 id="caveats">23. Caveats</h3>
<ul>
<li><b>Three models, one vendor.</b> The Anthropic and Gemini arms of the study have not been probed; the runner will fill them in when keys are available. The within-vendor scale gradient suggests the pattern will hold, but that is an expectation, not a measurement.</li>
<li><b>Embedded public text</b> (government notices, licence banners, jokes) is memorised from its public source and the verbatim probe cannot tell that apart from corpus memorisation. The top runs per corpus were inspected by hand; a cross-check against a web index would automate it.</li>
<li><b>CUAD's floor is not genre-matched.</b> Veridian is e-mail; legal drafting is more predictable than e-mail, so part of CUAD's gap above the floor may be genre rather than memorisation even after standard clauses and mirrored provisions are filtered out of the pool. The long party-specific runs are the number that cannot be explained that way. A post-cutoff EDGAR contract sample is the control that would separate the two, and is the next addition to the battery.</li>
<li><b>The document-level null is absence of evidence</b>, from 60 windows per corpus, 60 words each, at temperature 0, with one prompt form. It is informative because the same probe fires on the canon anchor and on CUAD, and it is bounded: a model could hold a few documents of a 46,000-document mailbox verbatim without a 60-window sample finding them. The Enron corpus is in open training sets (The Pile), so presence in training data is likely; what is not detectable is document-level memory, which in the literature tracks repetition rather than presence.</li>
<li><b>Refusals.</b> {MODEL_META[models[0]][0]} declines to continue {_pct(V[models[0]]["veridian"]["refusal_rate"])} of Veridian's and {_pct(V[models[0]]["endo"]["refusal_rate"])} of Endo's e-mails as private, and {_pct(V[models[0]]["enron"]["refusal_rate"])} of Enron's; the other models {_pct(max(V[m][c]["refusal_rate"] for m in models[1:] for c in V[m]))}. Refusals are excluded from every V statistic on both sides; scored as zeros they had masked the floor for Luna, and the earlier reading of a small-model residual above the floor as a genre effect is withdrawn.</li>
<li><b>The pool filter is a judgement.</b> The rules are deterministic; the screen is a small model at temperature 0 whose verdicts are cached and inspectable (<code>results/contam/v_screen.jsonl</code>). It is lenient rather than strict — a few predictable continuations survive it — and the <em>novel</em> flag and the per-item review page are the backstop.</li>
<li><b>Jeb Bush text</b> is available locally only for the 600-document subset, so its name tiers are shallow (the top tier starts at 14 documents) and its verbatim sample is drawn from a narrower pool than the others.</li>
<li><b>Name collisions.</b> A common name may belong to a better-known person (a Veridian tail name collided with a real analyst). Grading on the target organisation makes collisions a miss, which is conservative.</li>
<li><b>Benchmark grading is keyword-based</b> and coarse; one of Sol's seven TREC 2009 guesses ("204 — document destruction") matched by what is probably coincidence.</li>
<li><b>Exposure is mostly not effect.</b> Parts I and the first three matter probes measure what is <em>in</em> the model; M3 and the ablation (§20) measure a change in a relevance call. The round-1 ablation removes only the names, and the models still recognise the case from the fact pattern in most renamed documents, so its small Δ is a lower bound on the effect of case knowledge, not the whole of it; round 2 adds paraphrase (which removes the memorised text) and the brief-injection check adds the knowledge instead of removing it, and neither moved the LLMs' F1 beyond noise.</li>
{_round2_caveats(summary)}
<li><b>Matter rubrics are hand-written and keyword-graded.</b> Each checklist has 16–20 items chosen to span parties, allegations, people, events and outcome; a model can know a fact and phrase it in a way the keywords miss, so recall shares are lower bounds. The 'beyond context' split depends on what the study's task context happens to state.</li>
<li><b>The Jeb Bush evidence prior and metadata probes</b> run on the 600-document local subset (the collection is not redistributable), so their grounding counts are small and their per-request samples are 15 + 15.</li>
<li><b>Lift is estimated on judged documents</b>, whose sampling (TREC's stratified draws for Enron) differs from the collection; a term's lift is relative to the judged set, not to the whole mailbox.</li>
<li><b>The ladder's footprint proxy is rough.</b> Wikipedia pageviews measure public attention, not what is crawlable: two rungs with no article at all are recalled at 80–100% by the mid and large models, and for five matters the lookup falls back to a company or biography page broader than the case (flagged in the table). The rank correlation it supports (≈ +0.5 for the smaller models, ≈ +0.2 for the largest) should be read as "fame is a usable prior for small models", not as a measurement of exposure.</li>
<li><b>The post-cutoff sketches carry their dates.</b> The models decline the 2026 matter partly <em>because</em> the sketch says 2026; a date-free version would test whether they know they do not know. The mid model's confident mis-identification of that matter is a reminder that "named a case" is not "named the right case" — M0 is graded against answer keys, and a wrong confident answer is a hollow mark, not a hit.</li>
<li><b>Ladder rubrics are shorter</b> (10–18 facts) and were written from the public record by the author, not drawn from the study's task contexts; a few items are strict (Equity Funding's reinsurance mechanism, Bhopal's Sevin) and the shares are lower bounds as elsewhere.</li>
<li><b>Veridian's template.</b> The synthetic matter was written to resemble real metal-on-metal hip litigation, and the models say so (§15). Its documents and cast are novel; its <em>archetype</em> is not. That is the right floor for 'knows the documents' and a slightly generous floor for 'knows the kind of case'.</li>
{"".join(f"<li>{x}</li>" for x in (_native(summary) or {}).get("limitations", []))}
</ul>

<h3 id="next">24. What this decides</h3>
<ol>
<li><b>Weight the study's conclusions toward the e-mail corpora and Veridian</b>; report CUAD with the two-channel contamination caveat.</li>
<li><b>Treat Enron as a known case, not an unknown mailbox.</b> We found no document-level memory (Part I), but the matter is in the model (Part II): the pseudonymised complaint is identified by two of three models (the third names Reliant, a company in the same scandal), the record is recited {' / '.join(_pct(summary['matter_recall'][m]['enron']['share']) for m in models)}, and naming the company unlocks real, discriminative names. Any Enron result should be reported as "on a matter the model knows".</li>
{_report_effect_item(summary)}
{_anomaly_item(summary)}
<li><b>Pseudonymising the complaint is not a defence.</b> TREC's "Bleak Horizon" was decoded by every model and "Volteron" by {sum(1 for m in models if summary['matter_id'][m]['enron']['hit'])} of {len(models)} from the fact pattern alone (the other named Reliant Energy, a company in the same scandal), and the nameless ladder sketches identified {sum(1 for k, r in summary['ladder']['rungs'].items() if r.get('expected') not in ('none', 'floor') and all(summary['ladder']['per_model'][m][k]['id_hit'] for m in models))} of {sum(1 for r in summary['ladder']['rungs'].values() if r.get('expected') not in ('none', 'floor'))} real matters for every model. If a client corpus is to be used as a clean test, the <em>documents</em> must be renamed, not just the pleading — and even then the fact pattern remains (§20).</li>
<li><b>Probe the Anthropic and Gemini models</b> with the same battery (≈ $12 more, dominated by the metadata probe) before publishing cross-vendor comparisons.</li>
<li><b>Adopt the battery for future corpus selection:</b> any candidate corpus and its matter can be placed on these spectra for a few dollars before a single document is classified. The ladder (§17) is the scale to place it on: at frontier scale, assume any matter with a public docket is known in detail, and treat only post-cutoff matters — or synthetic ones — as genuinely unseen.</li>
<li><b>Build the next clean real corpus from a post-cutoff matter.</b> The two 2026 SEC actions on the ladder behave like Veridian on recall while being real; a document collection from a matter that arose after the models' cutoff (and is re-dated as models update) would give the study a real-world floor to set beside the synthetic one.</li>
</ol>
</section>
"""
    appendix = f"""<section id="appendix">
<h2>Appendix</h2>
<h3>A. What the long runs look like</h3>
<p>For each corpus with at least one ≥ 8-word run: the end of the prompt, the true continuation, and what the large model wrote. Matching stretches are the evidence; mismatches show where memory ends. (Jeb Bush: no document qualified.)</p>
{examples_html}
<h3>B. Benchmark-knowledge answers, verbatim</h3>
{bench_html}
<p class="fignote">Generated from <code>results/contam/summary.json</code> by <code>bench contam-html</code>. Design notes: <code>design/06_contamination_probe.md</code>.</p>
</section>
"""
    return {"models": models, "head": head, "header": header, "method": method, "results": results, "part2": part2_html, "closing": closing,
            "appendix": appendix, "tail": "</main></body></html>", "cmx": cmx, "p1": p1, "part2_parts": part2}


def build_html(summary: dict, out_path: Path = RESULTS_DIR / "contamination_report.html") -> Path:
    P = _main_parts(summary)
    doc = "".join(P[k] for k in ("head", "header", "method", "results", "part2", "closing", "appendix", "tail"))
    out_path.write_text(doc, encoding="utf-8")
    return out_path


SET_LABEL = {
    "veridian": "Veridian (synthetic)", "jebbush": "Jeb Bush (local subset)", "enron_k": "Enron · Complaint K topics (oil spill)",
    "enron_j": "Enron · Complaint J topics (pseudonym)", "enron_j_named": "Enron · Complaint J topics (company named)", "mnk": "Mallinckrodt",
    "endo": "Endo (held-out, post-cutoff)",
}
SET_LABEL_SHORT = {"veridian": "Veridian", "jebbush": "Jeb Bush", "enron_k": "Enron K", "enron_j": "Enron J", "mnk": "Mallinckrodt", "endo": "Endo"}
SET_ROLE = {"veridian": "floor", "endo": "post-cutoff"}
SET_ORDER = ["veridian", "jebbush", "enron_k", "enron_j", "enron_j_named", "mnk", "endo"]
META_SET_ORDER = ["veridian", "jebbush", "enron_k", "enron_j", "mnk", "endo"]
MATTER_SHORT = {"veridian": "Veridian ApexHip MDL", "jebbush": "Jeb Bush governorship", "enron": "Enron", "mnk": "Mallinckrodt opioids", "endo": "Endo opioids", "microsoft": "U.S. v. Microsoft"}
MATTER_ROLE_ = {"veridian": "floor", "endo": "post-cutoff", "microsoft": "ceiling"}
CATS = ["parties", "allegations", "people", "events", "outcome"]


def _mcell(m):
    return f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>'


def _endo_paragraph(summary: dict, models: list[str], link: bool = False) -> str:
    """The Endo reading: documents unseen, case known. Data-driven; empty if Endo is not in the summary."""
    V, ER, EG, LR, MI, MR, EP = (summary.get(k, {}) for k in ("verbatim", "entity_recall", "entity_recog", "label_recall", "matter_id", "matter_recall", "evidence_prior"))
    C = summary.get("composite", {}).get("per_model", {})
    if not any(V.get(m, {}).get("endo") for m in models):
        return ""
    N = lambda m: MODEL_META[m][0]  # noqa: E731
    sq = lambda f: " / ".join(f(m) for m in models)  # noqa: E731
    v_rng = sorted(V[m]["endo"]["lcs_f_mean"] for m in models if V.get(m, {}).get("endo"))
    ver = sorted(V[m]["veridian"]["lcs_f_mean"] for m in models if V.get(m, {}).get("veridian"))
    recog = sorted(round(30 * EG[m]["endo"]["hit_rate"]) for m in models if EG.get(m, {}).get("endo"))
    ided = [N(m) for m in models if MI.get(m, {}).get("endo", {}).get("hit")]
    m1 = sorted(MR[m]["endo"]["share"] for m in models if MR.get(m, {}).get("endo"))
    m1_mnk = sorted(MR[m]["mnk"]["share"] for m in models if MR.get(m, {}).get("mnk"))
    cmx = sq(lambda m: f'{C[m]["endo"]["doc_score"]:.0f}·{C[m]["endo"]["case_score"]:.0f}·{C[m]["endo"]["composite"]:.0f}' if C.get(m, {}).get("endo") and C[m]["endo"]["composite"] is not None else "–")
    ref = ' (<a href="#profile">Part I verdicts</a>, <a href="#verdicts2">Part II verdicts</a>, <a href="#ladder">ladder</a>)' if link is True else (link or "")
    return (f'<p><b>Endo, the post-cutoff corpus.</b> The sixth corpus was added for one reason: it is a real collection published after the models stopped learning, from a matter they can know. '
            f'Its publication date (2024–26) is what establishes that the documents were not in training; the probes are the check, and they show no document-level signal, as expected. '
            f'It gives the study\'s clearest "known case, post-cutoff documents" profile. On every document channel it sits at the Veridian floor — verbatim LCS-F1 '
            f'{v_rng[0]:.2f}–{v_rng[-1]:.2f} against Veridian\'s {ver[0]:.2f}–{ver[-1]:.2f}, free recall of its cast 0/30 for every model, recognition {recog[0]}–{recog[-1]} yes of 30, labels at chance '
            f'({sq(lambda m: _pct(LR[m]["endo"]["acc"]))}) — while the case behind it is known: identified from a nameless sketch by {", ".join(ided) if ided else "no model"}, '
            f'{_pct(m1[0])}–{_pct(m1[-1])} of the fact checklist recalled (better than Mallinckrodt\'s {_pct(m1_mnk[0])}–{_pct(m1_mnk[-1])}), '
            f'{sq(lambda m: str(EP[m]["endo"]["n_discriminative_named_total"]) if EP.get(m, {}).get("endo") else "–")} discriminative named terms. Composite documents·case·overall: {cmx} ({sq(N)}). '
            f'Endo is the Enron pattern from the other side — a matter in the model, documents that are not — on a collection where the date, not the probe, supplies the proof; it is consistent with the unit of contamination being the matter rather than the document. It is the recommended held-out '
            f'benchmark going forward. One caveat on its gold rather than its profile: Endo\'s relevance labels come from a three-OpenAI-model panel (the Anthropic and Gemini keys were absent), '
            f'unlike Mallinckrodt\'s mixed panel.{ref}</p>')


def _effect(summary: dict):
    """The pseudonymisation-ablation result (results/ablation/summary.json) or None if it has not been run."""
    from .effect import effect  # noqa: PLC0415

    return effect(summary)


def _effect2(summary: dict | None = None):
    """Round 2 of the ablation (results/ablation/round2/summary.json: CUAD rename + paraphrase, Jeb Bush matter vs control) or None if it has not been run."""
    from .effect2 import effect2  # noqa: PLC0415

    return effect2()


def _verify(summary: dict | None = None):
    """The generalisation checks A–D (results/verify/summary.json) or None if they have not been run."""
    from .verify_summary import verify_summary  # noqa: PLC0415

    return verify_summary()


def _abl_sentence(summary: dict, jev: bool = False) -> str:
    """One sentence on the ablation result, with a link; future-tense fallback if it has not been run."""
    e = _effect(summary)
    if not e:
        return ("whether Jev was trained on these corpora is a vendor claim this study tests only where a probe can be posed — the ablation study (results/ablation/) is the direct test"
                if jev else "the full-document pseudonymisation ablation (results/ablation/) is the direct test of effect and has not yet been run")
    e2 = _effect2(summary)
    if jev:
        r2 = (f' In round 2 its matter-topic scores on Jeb Bush fell with the public figures renamed ({e2["jev_short"]}) where the LLMs’ did not — a small familiarity effect, consistent with '
              f'public-web knowledge of public figures and not by itself evidence of training on the collection.' if e2 and e2.get("jev_short") else "")
        return (f'{e["one_sentence_jev"]}{r2} (<a href="{e["href"]}">ablation report</a>; §20)')
    r2 = (f' Round 2 extends the null to {" and ".join(m for m in e2["matters"] if m != "Enron")} for the LLMs (no knowledge effect beyond {e2["llm_bound"]:.1f} points).'
          if e2 and e2.get("matters") else "")
    return f'{e["one_sentence"]}{r2} (<a href="{e["href"]}">ablation report</a>; §20)'


def _jev_r2_intro(summary: dict) -> str:
    """The §1 clause on Jev's round-2 result (Jeb Bush matter topics); empty if round 2 has not run."""
    e2 = _effect2(summary)
    if not e2 or not e2.get("jev_short"):
        return ""
    return (f", though round 2 found its matter-topic scores on Jeb Bush do depend on the real names ({e2['jev_short']}), a small familiarity effect consistent with public-web knowledge "
            f"of public figures and not by itself evidence of training on the collection")


def _claim_short(summary: dict) -> str:
    """'could not detect a consequence of the former for the LLMs' review accuracy', weakened automatically if an LLM round-2 interval sits off zero."""
    e2 = _effect2(summary)
    return e2["claim_short"] if e2 and e2.get("claim_short") else "could not detect a consequence of the former for the LLMs' review accuracy"


def _three_matters_short(summary: dict) -> str:
    """' on three matters (Enron, Jeb Bush, CUAD)' for the overview sentence; empty before round 2."""
    e2 = _effect2(summary)
    if not e2 or not e2.get("matters"):
        return " (§20)"
    words = {1: "one", 2: "two", 3: "three", 4: "four"}
    return f" on {words.get(len(e2['matters']), len(e2['matters']))} matters ({_and(e2['matters'])}; §20)"


def _and(xs) -> str:
    xs = list(xs)
    if not xs:
        return ""
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _round2_caveats(summary: dict) -> str:
    """§23 items that exist only once round 2 and the generalisation checks have run: Terra absent, the Jev familiarity effect, ranking stability."""
    e2, v = _effect2(summary), _verify(summary)
    items = []
    if e2 and e2.get("absent"):
        items.append(f"<li><b>Round 2 ran without {' and '.join(MODEL_META[_mkey_(m)][0] for m in e2['absent'])}.</b> {e2['absent_txt']} The three-matter statement therefore rests on "
                     f"{' and '.join(MODEL_META[_mkey_(m)][0] for m in e2['llms'])} for Jeb Bush and CUAD, and on all three LLMs only for Enron and the Veridian brief check.</li>")
    if e2 and e2.get("jev_short"):
        items.append(f"<li><b>Jev's familiarity effect is small and is not a contamination verdict.</b> Its matter-topic scores depend on the real names ({e2['jev_short']}; FAS 140 on Enron; "
                     f"the knowledge-dependent Enron documents), which is what an encoder with public-web knowledge of public figures would show; it is not by itself evidence of training on the "
                     f"collections or their labels, and T2–T4 and the CUAD paraphrase find no sign of either. For evaluations: a Jev score on a famous-figure collection may run a few points high "
                     f"relative to an unknown matter.</li>")
    if e2 and e2.get("cuad_sys"):
        items.append("<li><b>The CUAD paraphrase control is not genre-matched.</b> The cost of paraphrase was measured on Veridian e-mail, not on unseen contracts; a post-cutoff EDGAR sample with "
                     "expert clause labels is the clean control and was not affordable. The within-CUAD dose–response (no growth of Δ with the contract's memorisation score) is the primary control.</li>")
    if v and v.get("b_caveat"):
        items.append(f"<li>{v['b_caveat']}</li>")
    return "".join(items)


def _mkey_(m: str) -> str:
    return m.split("@")[0]


def _verdict_r2(summary: dict, corpus: str) -> str:
    """The round-2 clause for the §22 verdicts table (Jeb Bush, CUAD); empty before round 2."""
    e2 = _effect2(summary)
    if not e2:
        return ""
    if corpus == "jebbush" and e2.get("ke"):
        llm = "; ".join(f"{MODEL_META[_mkey_(m)][0].split()[-1]} {e2['ke'][m]['delta'] * 100:+.1f}" for m in e2["jeb_sys"] if not m.startswith("jev"))
        jev = f"; Jev {e2['jev_short'].split(' on ')[0]} — a small familiarity effect, not by itself evidence of training on the collection" if e2.get("jev_short") else ""
        excl = [MODEL_META[_mkey_(m)][0].split()[-1] for m in e2.get("ke_llm_excl", [])]
        head = ("produced no LLM knowledge effect on the matter topics" if not excl else f"produced a knowledge effect on the matter topics that excludes zero only for {' and '.join(excl)}")
        return f" Round 2 (§20): renaming the Governor and Florida's public figures {head} ({llm} net of the control topics{jev})."
    if corpus == "cuad" and e2.get("cuad_sys"):
        return (f" The memorisation does not translate into review accuracy, though: paraphrasing away the memorised surface changed F1 by ≤ {e2['par_max']:.1f} points "
                f"({e2['cuad_seq_par']}), no more than the same paraphrase costs on Veridian and no more on the best-remembered contracts (§20).")
    return ""


def _report_effect_item(summary: dict) -> str:
    """§24 item 3: the effect as measured, with its bound — one matter before round 2, three after."""
    e2, v = _effect2(summary), _verify(summary)
    if not e2:
        return ("<li><b>Report the effect as measured, with its bound.</b> The full-document ablation (§20) puts the knowledge effect within ±3 points of F1 for every system, with no interval "
                "excluding zero. That bounds the effect of name-mediated knowledge on one matter at this sample size; it does not rule out smaller effects, other matters, or knowledge that "
                "survives renaming — the case is recognised from the fact pattern in most renamed documents, so the number is a floor. A date-free, fact-pattern-free rewrite of Enron is not "
                "possible without destroying the documents; the clean effect test needs a corpus the models have not seen — a post-cutoff real matter (the Endo opioid production, or the 2026 "
                "SEC actions on the ladder once their documents are available), held out and re-dated as models update.</li>")
    words = {1: "one", 2: "two", 3: "three", 4: "four"}
    n_m = words.get(len(e2["matters"]), len(e2["matters"]))
    kd = (f" The knowledge-dependent documents ({v['kd_share']:.0f}% of Enron J) are where help would show, and every system does worse there; supplying the case through a brief on "
          f"Veridian moved F1 by {v['d_seq']} ({v['d_sys_txt']})." if v else "")
    return (f"<li><b>Report the effect as measured, with its bound — now on {n_m} matters.</b> For the LLMs, knowing the case {e2['claim_verb']} on {_and(e2['matters'])} "
            f"under {words.get(len(e2['manips']), len(e2['manips']))} manipulations (remove the names, remove the memorised text by paraphrase, inject the case through a brief): no knowledge effect "
            f"beyond {e2['llm_bound']:.1f} F1 points, {e2['interval_txt'].replace('every 95% interval includes zero', 'intervals including zero')}; on CUAD, where the documents <em>are</em> memorised, paraphrasing away the memorised surface changed F1 by "
            f"≤ {e2['par_max']:.1f} points and no more on the best-remembered contracts.{kd} That still bounds rather than excludes: smaller effects and knowledge that survives every manipulation "
            f"remain possible, the Enron renaming is a floor because the case is recognised from the fact pattern, and the clean test remains a post-cutoff real matter held out and re-dated as "
            f"models update. {e2['jev_account_short']}</li>")


def _native(summary: dict | None = None):
    """The classifier-native tests on Jev (results/jev_probe/summary.json) or None if they have not been run."""
    from .jevnative import jev_native  # noqa: PLC0415

    return jev_native(summary)


def _native_sentence(summary: dict, ref: str | None = "§21") -> str:
    """The one Jev sentence used everywhere, with a link to the classifier-native report; a pointer if the tests have not been run."""
    n = _native(summary)
    if not n:
        return "the classifier-native tests (results/jev_probe/) have not been run."
    return f'{n["overall"]} ({n["link"]}{"; " + ref if ref else ""})'


def _anomaly_item(summary: dict) -> str:
    """§24 item on the FAS 140 anomaly: the follow-up it called for has been run, so the item reports the answer when it exists."""
    e, n = _effect(summary), _native(summary)
    fas = e and e.get("jev_fas")
    if not fas:
        return ""
    d = fas["delta"]["delta"]
    lead = (f"Jev lost {abs(100 * d):.0f} points of F1 on the FAS 140 request when the Raptor, Talon, LJM2 and Chewco vehicles were renamed, while the LLMs gained")
    if not n or not n["bare"]["aswritten"]:
        return (f"<li><b>Follow up the one anomaly.</b> {lead}; a token check (does Jev's probability move on the bare token 'Raptor', outside any document?) separates "
                f"Enron-specific knowledge from lexical weight and is the next test of the vendor's claim.</li>")
    b_as, b_named = n["bare"]["aswritten"], n["bare"]["named"]
    return (f"<li><b>The one anomaly, followed up.</b> {lead}. The bare-token check (§21) finds that a header plus one sentence naming a vehicle is called responsive "
            f"{_pct(b_as['rate_real'])} of the time under the request as written (fictional twin {_pct(b_as['rate_fake'])}) and {_pct(b_named['rate_real'])} vs {_pct(b_named['rate_fake'])} "
            f"only when the criteria name the vehicles: the loss is not a bare-name reflex but Jev reading request and document together. The code-name swap on four matters "
            f"then showed the same case knowledge at effect sizes comparable to the LLMs ({n['t1_jev_short']} pp). {n['overall']}</li>")


def _classifiers(summary: dict) -> list[str]:
    """Models that could only be posed M3 (Jev): shown in the M3 figure and tables, nowhere else."""
    return [m for m in summary.get("classifier_models", []) if m in summary.get("metadata_relevance", {})]


COMPOSITE_CHANNEL_LABEL = {"V": "V · verbatim", "E": "E · people", "L": "L · labels", "B": "B · benchmark topics",
                           "M0": "M0 · identified", "M1": "M1 · case recall", "M2": "M2 · usable terms"}
COMPOSITE_RAW_FMT = {"V": lambda v: f"{v:.2f}", "E": lambda v: f"d′ {v:.1f}", "L": _pct, "B": _pct, "M0": lambda v: "yes" if v else "no",
                     "M1": _pct, "M2": lambda v: f"{v:.0f} terms"}


JEV_NOTE = ("Jev is the purpose-built review classifier evaluated in this repository. Its vendor states that it is a System One classifier not pre-trained on "
            "public text; this study treats that as a claim to test, not as a fact. Jev cannot be posed the generative probes (continue a document, name a person, "
            "describe a case, list expected terms), so none of the seven composite channels can be measured for it and its cells read n/t (not testable with this "
            "probe). The one probe that fits its interface, M3 header-only relevance, was run on it: {m3}. That flat people effect is consistent with the claim but "
            "does not establish it: the LLMs, which demonstrably know the people, show nearly the same flatness ({m3_llm_sig}), so M3 has little power to detect people-knowledge in any system. "
            "{abl} The tests that fit a classifier's interface were then run on it: {native}")


def _m3_llm_sig(summary: dict, models: list[str]) -> str:
    """How many LLM (model, request-set) people-effect intervals on M3 exclude zero — the power statement must be measured, not asserted."""
    MD = summary.get("metadata_relevance", {})
    pairs = [(m, st, x) for m in models for st, x in MD.get(m, {}).get("by_set", {}).items() if x.get("delta_people_ci")]
    sig = [(m, st, x) for m, st, x in pairs if x["delta_people_ci"][0] > 0 or x["delta_people_ci"][1] < 0]
    if not pairs:
        return "no LLM M3 data"
    if not sig:
        return f"none of the {len(pairs)} LLM model × request-set intervals excludes zero"
    return (f"{len(sig)} of the {len(pairs)} LLM model × request-set intervals exclude zero: "
            + ", ".join(f"{MODEL_META[m][0]} on {SET_LABEL_SHORT.get(st, st)} {_sd(x['delta_people'])}" for m, st, x in sig))


def _jev_m3_summary(summary: dict) -> str:
    """One sentence of Jev's M3 numbers for the composite note; empty if M3 was not run on it."""
    cls = _classifiers(summary)
    if not cls:
        return "not run (no TypeSafe API key)"
    md = summary["metadata_relevance"][cls[0]].get("by_set", {})
    parts = [f"{SET_LABEL_SHORT.get(st, st)} {_pct(x['acc_subject'])} → {_pct(x['acc_headers'])} ({_sd(x['delta_people'])})"
             for st in META_SET_ORDER if (x := md.get(st))]
    sig = [SET_LABEL_SHORT.get(st, st) for st, x in md.items() if x["delta_people_ci"][0] > 0 or x["delta_people_ci"][1] < 0]
    tail = " — no paired difference excludes zero" if not sig else " — the paired difference excludes zero on " + ", ".join(sig)
    return "accuracy from the subject alone → with From/To/Cc added (Δ people): " + "; ".join(parts) + tail


def _m3_jev_note(summary: dict, models: list[str]) -> str:
    """Jev on M3, next to the LLMs (shown at the end of the M3 section)."""
    cls = _classifiers(summary)
    box = '<div style="background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:10px 14px;margin:14px 0"><p style="margin:0">'
    if not cls:
        return (box + '<b>Jev on this probe.</b> M3 is the one probe in the battery that matches Jev’s interface (a relevance call from a fixed set of fields), '
                'so it is where a direct comparison would go. It was not run: Jev is reached through the TypeSafe API and no <code>TYPESAFE_API_KEY</code> is '
                'configured in this environment.</p></div>')
    MD = summary["metadata_relevance"]
    j = cls[0]
    jm = MD[j]["by_set"]

    def row(st):
        x = jm.get(st)
        if not x:
            return None
        llm = " / ".join(f"{_pct(y['acc_subject'])} → {_pct(y['acc_headers'])} ({_sd(y['delta_people'])})" if (y := MD.get(m, {}).get("by_set", {}).get(st)) else "–" for m in models)
        lo, hi = x["delta_people_ci"]
        return [_esc(SET_LABEL[st]), str(x["n"]), f"{_pct(x['acc_subject'])} → <b>{_pct(x['acc_headers'])}</b>", f"<b>{_sd(x['delta_people'])}</b> <small>[{_sd(lo)}, {_sd(hi)}]</small>",
                _pct(x["acc_lexical"]), llm]
    tbl = table(["request set", "e-mails", "Jev: subject only → with From/To/Cc", "Jev Δ people (95% CI)", "lexical", "LLMs: subject → headers (Δ), " + " / ".join(MODEL_META[m][0] for m in models)],
                [r for st in META_SET_ORDER if (r := row(st))], cls="tbl wide")
    deltas = [x["delta_people"] for x in jm.values()]
    sub = [x["acc_subject"] for x in jm.values()]
    j_sig = [SET_LABEL_SHORT.get(st, st) for st, x in jm.items() if x["delta_people_ci"][0] > 0 or x["delta_people_ci"][1] < 0]
    j_sig_txt = "no interval excludes zero" if not j_sig else "the interval excludes zero only on " + ", ".join(j_sig)
    gap = " / ".join(f"{100 * (MD[m]['by_set']['enron_j']['acc_subject'] - jm['enron_j']['acc_subject']):.0f}" for m in models if MD.get(m, {}).get("by_set", {}).get("enron_j")) if "enron_j" in jm else "–"
    return (box + f'<b>Jev on this probe.</b> M3 is the one probe in the battery that matches Jev’s interface (a relevance call from a fixed set of fields), so it is the '
            f'one place a direct comparison can be made. Jev saw the same matter context, request and header block through its classifier API (one question per request, '
            f'no criteria; {sum(x["n"] for x in jm.values()) * 2:,} calls, ${summary["cost_usd"].get(j, 0):.2f}). Its paired Δ people runs from {_sd(min(deltas))} to {_sd(max(deltas))} '
            f'and {j_sig_txt}: the same flat pair the LLMs show, on the real corpora as on the fictional one. Jev’s vendor states it is not pre-trained on public text; we treat '
            f'that as a claim to test. The flat people effect is consistent with the claim but does not establish it, since the LLMs — which demonstrably know the people (Part I, '
            f'M1) — show nearly the same flatness ({_m3_llm_sig(summary, models)}); M3 therefore has little power to detect people-knowledge in any system. The full-document test is the ablation: {_abl_sentence(summary, jev=True)}. '
            f'What M3 does separate is the subject-only call: from the subject alone the LLMs are {gap} points above Jev on the Enron scandal requests '
            f'({" / ".join(_pct(x) for x in sub)} for Jev across the five sets, against a lexical baseline of {_pct(min(x["acc_lexical"] for x in jm.values()))}–{_pct(max(x["acc_lexical"] for x in jm.values()))}). '
            f'That gap is reading of the subject line, not a people effect; the people channel adds nothing measurable to either kind of model. '
            f'The tests built for a classifier’s interface are in §21: {_native_sentence(summary, ref=None)}</p>{tbl}</div>')


def _composite(summary: dict, models: list[str], kind: str = "all", jev: bool = True, m3_ref: str = '<a href="#m3">§19</a>',
               native_ref: str = '<a href="#jevnative">§21</a>') -> dict:
    """The contamination scores as a dataset x model matrix, ranked by the largest model, plus a per-channel breakdown.
    kind = "all": three cells per model (documents / case / overall); "docs": the documents score only; "case": the case score only."""
    C = summary.get("composite")
    if not C:
        return {"has": False}
    big = models[-1]
    chans_all = C["channels"]
    doc_ch, case_ch = C.get("doc_channels", ["V", "E", "L", "B"]), C.get("case_channels", ["M0", "M1", "M2"])
    key = {"all": "composite", "docs": "doc_score", "case": "case_score"}[kind]
    chans = {"all": chans_all, "docs": doc_ch, "case": case_ch}[kind]
    datasets = [d for d in C["datasets"] if kind == "all" or C["per_model"][big][d].get(key) is not None]
    order = sorted(datasets, key=lambda d: -(C["per_model"][big][d].get(key) or 0))

    def cell(v, cls=""):
        if v is None:
            return f'<td class="cmx-c {cls}">–</td>'
        a = 0.06 + 0.94 * v / 100
        tc = "#fff" if v > 55 else INK
        return f'<td class="cmx-c {cls}" style="background:rgba(47,127,193,{a:.2f});color:{tc}">{v:.0f}</td>'

    sw = lambda m: f'<span style="display:inline-block;width:9px;height:9px;border-radius:2px;background:{MODEL_META[m][2]};vertical-align:middle;margin-right:5px"></span>'  # noqa: E731
    nat = _native(summary) if jev else None
    jev_cell = '<td class="cmx-c cmx-jev" title="not testable with this probe: Jev is a classifier, so the generative probes cannot be posed to it">n/t<sup>†</sup></td>'
    # the case columns carry a second mark when a classifier-native test did detect case knowledge in Jev (a different instrument, not a composite channel)
    jev_case_cell = ('<td class="cmx-c cmx-jev" title="not testable with this probe; case knowledge was detected by the classifier-native code-name swap">n/t<sup>†‡</sup></td>'
                     if nat and nat["t1_n_excl"] else jev_cell)
    if kind == "all":
        head1 = "".join(f'<th colspan="3" class="cmx-g">{sw(m)}{_esc(MODEL_META[m][0])}</th>' for m in models)
        head2 = "".join('<th class="cmx-s">docs</th><th class="cmx-s">case</th><th class="cmx-s cmx-all">all</th>' for _ in models)
        if jev:
            head1 += '<th colspan="3" class="cmx-g cmx-jevh">Jev <small>(classifier)</small></th>'
            head2 += '<th class="cmx-s">docs</th><th class="cmx-s">case</th><th class="cmx-s cmx-all">all</th>'
        thead = f'<tr><th rowspan="2">dataset</th>{head1}<th rowspan="2">channels<br><small>docs / case</small></th></tr><tr>{head2}</tr>'
    else:
        head1 = "".join(f'<th class="cmx-g">{sw(m)}{_esc(MODEL_META[m][0])}</th>' for m in models)
        if jev:
            head1 += '<th class="cmx-g cmx-jevh">Jev <small>(classifier)</small></th>'
        thead = f'<tr><th>dataset</th>{head1}<th>channels</th></tr>'
    body = []
    for d in order:
        cells = []
        for m in models:
            r = C["per_model"][m][d]
            if kind == "all":
                cells.append(cell(r.get("doc_score")) + cell(r.get("case_score")) + cell(r.get("composite"), "cmx-all"))
            else:
                cells.append(cell(r.get(key), "cmx-all"))
        if jev:
            has_case = d not in ("cuad",) and C["per_model"][big][d].get("case_score") is not None
            case_c = jev_case_cell if has_case else jev_cell
            cells.append({"all": jev_cell + case_c + jev_cell, "docs": jev_cell, "case": case_c}[kind])
        r0 = C["per_model"][big][d]
        nchan = f'{r0["n_doc"]} / {r0["n_case"]}' if kind == "all" else f'{r0["n_doc"] if kind == "docs" else r0["n_case"]} of {len(chans)}'
        role = ROLE.get(d) or TAG.get(d)
        lbl = _esc(CORPUS_SHORT.get(d, d)) + (f' <span class="role {role}">{role_text(role)}</span>' if role else "")
        body.append(f'<tr><th scope="row">{lbl}</th>{"".join(cells)}<td class="small" style="white-space:nowrap">{nchan}</td></tr>')
    scope = {"all": ('<b>docs</b> averages the document-level channels (V verbatim, E people, L labels, B benchmark topics; up to 4); <b>case</b> averages the matter-level '
                     'channels (M0 identified, M1 recall, M2 usable terms; up to 3); <b>all</b> is the mean of every available channel. The last column is how many channels '
                     'of each kind the dataset was probed on: CUAD has no case channels, so its score is a documents score.'),
             "docs": ('Each cell is the <b>documents score</b>: the mean over the document-level channels (V verbatim, E people, L labels, B benchmark topics) on which the '
                      'dataset was probed; the last column counts them. Mallinckrodt has no published topic list, so no B channel.'),
             "case": ('Each cell is the <b>case score</b>: the mean over the matter-level channels (M0 identified from a nameless description, M1 recall of the record, M2 usable '
                      'named terms). CUAD is a contract benchmark with no matter behind it and is omitted.')}[kind]
    jev_foot = (f' <sup>†</sup> n/t = not testable with this probe. Jev is a classifier, so the generative probes cannot be posed to it; the one probe it can take (M3) is '
                f'reported in {m3_ref} and shows no detectable people effect; whether Jev was trained on these corpora is a vendor claim this study tests only where a probe can be '
                f'posed. {_abl_sentence(summary, jev=True)}.'
                + (f' <sup>‡</sup> Case knowledge <em>was</em> detected in Jev by a different instrument, the classifier-native code-name swap ({nat["t1_jev_short"]} pp; {native_ref}): '
                   f'{nat["overall"]} ({nat["link"]}).' if nat and nat["t1_n_excl"] else "")) if jev else ''
    fig = (f'<table class="tbl cmx"><thead>{thead}</thead><tbody>{"".join(body)}</tbody></table>'
           f'<p class="fignote">0 = indistinguishable from the fictional floor on every channel; 100 = at the ceiling on every channel. {scope} Rows are ranked by the largest '
           f'model.{jev_foot}</p>')
    rows = []
    for d in order:
        for m in models:
            r = C["per_model"][m][d]
            cells = [f'{_esc(CORPUS_SHORT.get(d, d))}', f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>']
            for ch in chans:
                pos, raw = r["channels"].get(ch), r["raw"].get(ch)
                cells.append('<span class="small">n/a</span>' if pos is None else f'<b>{pos:.0f}</b> <small>{_esc(COMPOSITE_RAW_FMT[ch](raw))}</small>')
            if kind == "all":
                for k in ("doc_score", "case_score", "composite"):
                    cells.append(f'<b>{r[k]:.0f}</b>' if r.get(k) is not None else "–")
            else:
                cells.append(f'<b>{r[key]:.0f}</b>' if r.get(key) is not None else "–")
            rows.append(cells)
    tail_cols = ["documents", "case", "overall"] if kind == "all" else [{"docs": "documents score", "case": "case score"}[kind]]
    tbl = table(["dataset", "model"] + [COMPOSITE_CHANNEL_LABEL[c] for c in chans] + tail_cols, rows, cls="tbl wide")
    scaling = {"V": "<b>V</b> mean LCS-F1 from Veridian’s value (0) to the founding documents’ (100)",
               "E": "<b>E</b> recognition d′ from Veridian to the framers",
               "L": "<b>L</b> label accuracy from chance (50%, where Veridian sits by construction) to Titanic",
               "B": "<b>B</b> share of the benchmark’s own topics recited, 0 to 100% (Mallinckrodt has no published topic list, so no B)",
               "M0": "<b>M0</b> 0 or 100 for identifying the matter from the pseudonymised complaint or nameless sketch (strict: Sol’s “Reliant Energy” for the Enron complaint counts as a miss)",
               "M1": "<b>M1</b> fact-checklist share from Veridian (0) to <em>U.S. v. Microsoft</em>",
               "M2": "<b>M2</b> discriminative named terms (best of the dataset’s request sets; for Enron that is the named Complaint J set) from Veridian to the largest set observed for that model"}
    agg = {"all": ("The documents score is the mean of V, E, L, B; the case score the mean of M0, M1, M2; the overall score the plain mean of every available channel, so "
                   "document-level and matter-level knowledge are weighted equally in it; that is a choice, not a fact, which is why the two sub-scores are shown."),
           "docs": "The documents score is the plain mean of the available document-level channels.",
           "case": "The case score is the plain mean of the available matter-level channels."}[kind]
    note = (f'<p class="small">How each channel is scaled to 0–100 for a given model: {"; ".join(scaling[c] for c in chans)}. Values are clipped to [0, 100]. {agg} '
            'Small numbers in each cell are the raw metric.</p>')
    if jev:
        note += (f'<p class="small"><b>Jev.</b> {JEV_NOTE.format(m3=_jev_m3_summary(summary), m3_llm_sig=_m3_llm_sig(summary, models), abl=_abl_sentence(summary, jev=True), native=_native_sentence(summary, ref=native_ref))}</p>')
    return {"has": True, "fig": fig, "tbl": tbl, "note": note, "order": order, "kind": kind}


def _part2(summary: dict, models: list[str]) -> dict:
    MI, MR, EP, MD = summary.get("matter_id", {}), summary.get("matter_recall", {}), summary.get("evidence_prior", {}), summary.get("metadata_relevance", {})
    pct_fmt = lambda v: f"{100 * v:.0f}%"  # noqa: E731
    have = any(MI.get(m) or MR.get(m) or EP.get(m) or MD.get(m) for m in models)
    if not have:
        return {"has": False}

    # M1 figures
    rows_all = [(k, {m: (MR[m][k]["share"], None, None) for m in models if MR.get(m, {}).get(k) and MR[m][k]["share"] is not None}) for k in ("jebbush", "enron", "mnk", "endo", "microsoft")]
    rows_beyond = [(k, {m: (MR[m][k]["share_beyond"], None, None) for m in models if MR.get(m, {}).get(k) and MR[m][k]["share_beyond"] is not None}) for k in ("jebbush", "enron", "mnk", "endo", "microsoft")]
    fig_m1 = dotplot(rows_all, models, 0, 1, [0, 0.25, 0.5, 0.75, 1], pct_fmt, "M1 · Matter recall: share of the fact checklist recovered from the matter's name alone",
                     labels=MATTER_SHORT, roles=MATTER_ROLE_, note="Veridian is omitted: it is fictional, so the right answer is 'unknown' (see the table).")
    fig_m1b = dotplot(rows_beyond, models, 0, 1, [0, 0.25, 0.5, 0.75, 1], pct_fmt, "M1 · The same, restricted to facts the study's task context does not already state",
                      labels=MATTER_SHORT, roles=MATTER_ROLE_)
    grid_vals = {m: {k: MR[m][k]["by_cat"] for k in ("jebbush", "enron", "mnk", "endo", "microsoft") if MR.get(m, {}).get(k)} for m in models}
    fig_m1c = gridmap(["jebbush", "enron", "mnk", "endo", "microsoft"], MATTER_SHORT, CATS, {c: c for c in CATS}, grid_vals, models,
                      "M1 · Recall by category of fact", note="Share of checklist items recovered within each category. 'People' is the category that bears most directly on review: who the custodians are and what they did.")

    # M0 / M1 table
    sk_order = [("veridian", "Veridian sketch <span class=\"role floor\">floor</span>"), ("bigthorium", "Big Thorium sketch <span class=\"role public-invented\">public, invented</span>"), ("jebbush", "Jeb Bush sketch"), ("enron", "Complaint J (Volteron = Enron)"),
                ("enron_k", "Complaint K (Bleak Horizon = Deepwater Horizon)"), ("mnk", "Mallinckrodt sketch"), ("endo", "Endo sketch <span class=\"role post-cutoff\">post-cutoff corpus</span>"), ("microsoft", "Microsoft sketch <span class=\"role ceiling\">ceiling</span>")]

    def m0row(m):
        cells = [_mcell(m)]
        for k, _ in sk_order:
            x = MI.get(m, {}).get(k)
            if not x:
                cells.append("–")
            elif x["control"]:
                cells.append(("<b>said unknown / fictional</b>" if x["unknown"] else "<b>named a real matter</b>") + (f"<br><small>{_esc('; '.join(x['templates']))}</small>" if x["templates"] else "")
                             + f"<br><small class=\"q\">{_esc(x['first_line'].replace('**', '')[:110])}</small>")
            else:
                cells.append(("<b>identified</b>" if x["hit"] else ("unknown" if x["unknown"] else ("<b>named a real matter instead</b>" if k == "bigthorium" else "<b>missed</b>")))
                             + (f"<br><small>{_esc('; '.join(x['templates']))}</small>" if k == "bigthorium" and x.get("templates") else "")
                             + f"<br><small class=\"q\">{_esc(x['first_line'].replace('**', '')[:110])}</small>")
        return cells
    tbl_m0 = table(["model"] + [t for _, t in sk_order], [m0row(m) for m in models], cls="tbl wide")

    def m1row(m):
        cells = [_mcell(m)]
        for k in ("veridian", "bigthorium", "jebbush", "enron", "mnk", "endo", "microsoft"):
            x = MR.get(m, {}).get(k)
            if not x:
                cells.append("–")
            elif k == "bigthorium":
                cells.append(("said unknown" if x["unknown"] else f"<b>answered</b> ({x['n_words']} words)") + f' · {x["n_hit"]}/{x["n"]} facts<br><small class="q">{_esc(x["response"][:110])}</small>')
            elif x["control"]:
                cells.append(("said unknown" if x["unknown"] else f"<b>confabulated</b> ({x['n_words']} words)") + (f"<br><small>template: {_esc('; '.join(x['templates']))}</small>" if x["templates"] else ""))
            else:
                missed = ", ".join(x["missed"][:6]) + (" …" if len(x["missed"]) > 6 else "")
                cells.append(f'{_pct(x["share"])} <small>({x["n_hit"]}/{x["n"]})</small> · beyond context {_pct(x["share_beyond"])}<br><small>missed: {_esc(missed) or "nothing"}</small>')
        return cells
    tbl_m1 = table(["model", "Veridian <span class=\"role floor\">floor</span>", "Big Thorium <span class=\"role public-invented\">public, invented</span>", "Jeb Bush", "Enron", "Mallinckrodt", "Endo <span class=\"role post-cutoff\">post-cutoff</span>", "U.S. v. Microsoft <span class=\"role ceiling\">ceiling</span>"],
                   [m1row(m) for m in models], cls="tbl wide")

    # M2 figures and tables
    def ep_rows(k):
        return [(st, {m: (EP[m][st][k], None, None) for m in models if EP.get(m, {}).get(st) and EP[m][st].get(k) is not None}) for st in SET_ORDER]
    fig_m2a = dotplot(ep_rows("grounded_rate_named"), models, 0, 1, [0, 0.25, 0.5, 0.75, 1], pct_fmt,
                      "M2 · Evidence prior: share of volunteered named terms (not in the prompt) that exist in the corpus (≥ 2 judged documents)", labels=SET_LABEL, roles=SET_ROLE, label_w=300, width=700)
    fig_m2b = dotplot(ep_rows("discriminative_rate_named"), models, 0, 1, [0, 0.25, 0.5, 0.75, 1], pct_fmt,
                      "M2 · Evidence prior: share of those named terms that discriminate (≥ 2× as frequent in responsive documents)", labels=SET_LABEL, roles=SET_ROLE, label_w=300, width=700)
    fig_m2c = dotplot(ep_rows("n_novel_named_mean"), models, 0, 20, [0, 5, 10, 15, 20], lambda v: f"{v:.0f}",
                      "M2 · How many named terms beyond the prompt the model volunteers per request (of 25 asked)", labels=SET_LABEL, roles=SET_ROLE, label_w=300, width=700)
    fig_m2d = dotplot(ep_rows("discriminative_rate_generic"), models, 0, 1, [0, 0.25, 0.5, 0.75, 1], pct_fmt,
                      "M2 · For comparison: discriminative share of generic keywords (vocabulary, not case knowledge)", labels=SET_LABEL, roles=SET_ROLE, label_w=300, width=700)

    def m2row(m, st):
        x = EP.get(m, {}).get(st)
        if not x:
            return None
        return [_mcell(m), _esc(SET_LABEL[st]), str(x["n_requests"]), _num(x["n_novel_named_mean"], 1), _pct(x["grounded_rate_named"]), _pct(x["discriminative_rate_named"]),
                _pct(x["grounded_rate_generic"]), _pct(x["discriminative_rate_generic"]), str(x["n_discriminative_named_total"])]
    tbl_m2 = table(["model", "request set", "requests", "named terms beyond prompt / request", "grounded (named)", "discriminative (named)", "grounded (generic)", "discriminative (generic)", "discriminative named terms, total"],
                   [r for m in models for st in SET_ORDER if (r := m2row(m, st))], cls="tbl wide")

    # the actual discriminative named terms, per request, for the largest model present
    big = models[-1]
    ev_rows = []
    for st in SET_ORDER:
        x = EP.get(big, {}).get(st)
        if not x:
            continue
        for key, r in x["per_request"].items():
            disc = [t for t in r["top_terms"] if t["named"] and t["discriminative"]]
            grounded_only = [t for t in r["top_terms"] if t["named"] and t["grounded"] and not t["discriminative"]]
            ev_rows.append([_esc(SET_LABEL[st]), _esc(r["title"]) + (" <span class=\"tag\">scandal</span>" if r.get("scandal") else ""), str(r["n_novel_named"]),
                            ", ".join(f'<b>{_esc(t["term"])}</b> <small>×{t["lift"]:.1f}, {t["df_pos"]} resp.</small>' for t in disc) or "<span class=\"dim\">none</span>",
                            ", ".join(_esc(t["term"]) for t in grounded_only[:6]) or "<span class=\"dim\">–</span>",
                            f'<small class="q">{_esc((r.get("note") or "")[:160])}</small>'])
    tbl_m2_terms = table(["request set", "request", "named terms beyond prompt", "discriminative named terms (lift, responsive docs containing it)", "grounded but not discriminative", "model's own note on what it knows"], ev_rows, cls="tbl wide terms")

    # M3 figure and tables; the classifier (Jev) is a real column here, since M3 is the one probe its interface can take
    m3_models = models + _classifiers(summary)
    md_rows = []
    for st in META_SET_ORDER:
        vals = {}
        for m in m3_models:
            x = MD.get(m, {}).get("by_set", {}).get(st)
            if x:
                vals[m] = (x["acc_subject"], x["acc_headers"], x["acc_lexical"])
        if vals:
            md_rows.append((st, vals))
    jev_note = (" Jev (purple) saw the same context, request and header block through its classifier API. Its vendor states it is not pre-trained on public text; "
                "that is a claim under test here, and its flat arrows are consistent with it without establishing it, since the LLMs' arrows are equally flat."
                if _classifiers(summary) else "")
    m3_title = "M3 · Metadata-only relevance: accuracy from Date + Subject (open) → with From / To / Cc added (filled); balanced requests, chance 50%"
    m3_note = "The length of each arrow is the accuracy that seeing who sent and received the e-mail adds. On Veridian the names are fictional, so its arrows measure what header structure alone (domains, distribution lists) is worth."
    fig_m3 = pairedplot(md_rows, m3_models, m3_title, labels=SET_LABEL, roles=SET_ROLE, note=m3_note + jev_note)
    # the same figure without the classifier, for the short report and the lawyer's guide (which leave Jev out)
    fig_m3_llm = pairedplot([(st, {m: v for m, v in vals.items() if m in models}) for st, vals in md_rows], models, m3_title, labels=SET_LABEL, roles=SET_ROLE, note=m3_note)

    def m3row(m, st):
        x = MD.get(m, {}).get("by_set", {}).get(st)
        if not x:
            return None
        lo, hi = x["delta_people_ci"]
        d = x["delta_people"]
        return [_mcell(m), _esc(SET_LABEL[st]), str(x["n"]),
                f'{_pct(x["acc_headers"])}{_stars(x["p_headers_vs_chance"])} <small>[{_pct(x["acc_headers_ci"][0])}–{_pct(x["acc_headers_ci"][1])}]</small>',
                f'{_pct(x["acc_subject"])}{_stars(x["p_subject_vs_chance"])} <small>[{_pct(x["acc_subject_ci"][0])}–{_pct(x["acc_subject_ci"][1])}]</small>',
                f'<b>{_sd(d)}</b> <small>[{_sd(lo)}, {_sd(hi)}]</small>',
                _pct(x["acc_lexical"]), f'{x["fixed_by_people"]} / {x["broken_by_people"]}', f'{_pct(x["resp_rate_headers"])} / {_pct(x["resp_rate_subject"])}']
    tbl_m3 = table(["model", "request set", "e-mails", "with From/To/Cc", "subject only", "Δ people (95% CI)", "lexical baseline", "calls fixed / broken by the people", "'responsive' rate (headers / subject)"],
                   [r for m in m3_models for st in META_SET_ORDER if (r := m3row(m, st))], cls="tbl wide")

    # per-request M3 for the largest model: where do the people help?
    pr_rows = []
    for st in META_SET_ORDER:
        x = MD.get(big, {}).get("by_set", {}).get(st)
        if not x:
            continue
        for t, y in x["by_topic"].items():
            pr_rows.append((st, t, y))
    pr_rows.sort(key=lambda r: -r[2]["delta_people"])
    tbl_m3_topics = table(["request set", "request", "e-mails", "with From/To/Cc", "subject only", "Δ people", "lexical"],
                          [[_esc(SET_LABEL[st]), _esc(t), str(y["n"]), _pct(y["acc_headers"]), _pct(y["acc_subject"]), _sd(y["delta_people"]), _pct(y["acc_lexical"])]
                           for st, t, y in pr_rows], cls="tbl")

    return {"has": True, "big": big, "fig_m1": fig_m1, "fig_m1b": fig_m1b, "fig_m1c": fig_m1c, "tbl_m0": tbl_m0, "tbl_m1": tbl_m1,
            "fig_m2a": fig_m2a, "fig_m2b": fig_m2b, "fig_m2c": fig_m2c, "fig_m2d": fig_m2d, "tbl_m2": tbl_m2, "tbl_m2_terms": tbl_m2_terms,
            "fig_m3": fig_m3, "fig_m3_llm": fig_m3_llm, "tbl_m3": tbl_m3, "tbl_m3_topics": tbl_m3_topics}


def _ladder(summary: dict, models: list[str]) -> dict:
    """Figures and table for the ladder of real matters (§17)."""
    L = summary.get("ladder")
    if not L or not L.get("per_model"):
        return {"has": False}
    rungs, pm = L["rungs"], L["per_model"]
    # order: matters with an article by 12-month views (desc); then no-article real matters; then post-cutoff; floor last
    def sort_key(kv):
        k, r = kv
        fp = r["footprint"]
        if r["expected"] == "floor":
            return (3, 1, k)
        if r["expected"] == "public-invented":
            return (3, 0, k)  # the second floor sits just above Veridian at the bottom of the ladder
        if r["expected"] == "none":
            return (2, 0, k)
        if fp.get("title"):
            return (0, -(fp.get("views_12m") or 0), k)
        return (1, 0, k)
    ordered = sorted(rungs.items(), key=sort_key)
    fig = ladderplot(ordered, pm, models, "The ladder: public footprint, recall of the record, and identification from a de-identified sketch",
                     note="Rows are real matters ordered by 12-month English-Wikipedia pageviews (grey bar, log scale; window "
                          f"{'–'.join(L['footprint_window']) if L.get('footprint_window') else 'last 12 complete months'}). Dots: share of a hand-written fact "
                          "checklist recovered when asked to describe the matter by name. Right: filled = named the matter from a sketch with every proper noun "
                          "removed; hollow = named something else; ? = said it could not tell. Shaded rows are the study's own matters and the Microsoft ceiling.")
    pts = []
    for k, r in rungs.items():
        fp = r["footprint"]
        if not fp.get("title"):
            continue
        ys = {m: pm.get(m, {}).get(k, {}).get("share") for m in models}
        if all(v is None for v in ys.values()):
            continue
        pts.append((k, r["label"].split(" (")[0], math.log10(1 + (fp.get("views_12m") or 0)), ys, bool(r.get("study"))))
    corr = L.get("corr_views_recall", {})
    corr_txt = "; ".join(f"{MODEL_META[m][0]} ρ = {c['spearman']:+.2f} (n = {c['n']})" for m, c in corr.items() if m in models)
    fig2 = scatter(pts, models, "Does public footprint predict how much of the record the model has?",
                   note=f"Spearman rank correlation between log pageviews and recall share across matters with a Wikipedia article: {corr_txt}. "
                        "Veridian, Big Thorium, the post-cutoff matters and rungs without an article are omitted here and shown in the ladder above.",
                   xlabel="12-month English-Wikipedia pageviews of the matter's article (log scale)", ylabel="M1 · share of the fact checklist")
    fam = L["families"]
    big = models[-1]
    rows = []
    for k, r in ordered:
        fp = r["footprint"]
        fcell = (f'{_esc(fp["title"])}{" <span class=\"dim\">(" + _esc(fp["proxy"]) + ")</span>" if fp.get("proxy") else ""}<br><small>{(fp.get("views_12m") or 0):,} views · {fp.get("langs", 0)} langs · {fp.get("length", 0) // 1000}k</small>'
                 if fp.get("title") else ("<span class=\"dim\">fictional</span>" if r["expected"] == "floor" else "<span class=\"dim\">no article</span>"))
        idc = " ".join(
            (f'<span style="color:{MODEL_META[m][2]}">●</span>' if pm.get(m, {}).get(k, {}).get("id_hit") else
             (f'<span style="color:{MODEL_META[m][2]}">?</span>' if pm.get(m, {}).get(k, {}).get("id_unknown") else f'<span style="color:{MODEL_META[m][2]}">○</span>'))
            for m in models if pm.get(m, {}).get(k))
        shares = " / ".join((_pct(pm[m][k]["share"]) if pm.get(m, {}).get(k, {}).get("share") is not None else ("unk." if pm.get(m, {}).get(k, {}).get("unknown") else "–")) for m in models)
        bigm = pm.get(big, {}).get(k, {})
        missed = ", ".join(bigm.get("missed") or []) if bigm.get("missed") else ("said unknown" if bigm.get("unknown") else "")
        rows.append([f"<b>{_esc(r['label'])}</b>" if r.get("study") else _esc(r["label"]), _esc(fam.get(r["family"], r["family"]).split(" (")[0]), str(r["year"]),
                     fcell, _esc(r["expected"]), idc, shares, f"<small>{_esc(missed)}</small>"])
    tbl = table(["matter", "family", "year", "public footprint (en.wikipedia)", "expected", "M0 named it", f"M1 share ({' / '.join(MODEL_META[m][0].split()[-1] for m in models)})", f"{MODEL_META[big][0]} missed"],
                rows, cls="tbl wide")
    return {"has": True, "fig": fig, "fig2": fig2, "tbl": tbl, "ordered": ordered, "pm": pm, "corr": corr}


def _better_txt(models, pm, a, b, N):
    """'every model' / 'two of the three (X, Y)' for share(a) >= share(b)."""
    g = lambda m, k: pm.get(m, {}).get(k, {}).get("share") or 0  # noqa: E731
    w = [m for m in models if g(m, a) >= g(m, b)]
    if len(w) == len(models):
        return "every model"
    return f"{len(w)} of the {len(models)} ({', '.join(N(m) for m in w)})" if w else "no model"


def _ladder_narrative(summary: dict, models: list[str], lad: dict) -> str:
    """Interpretation for §17; the numbers are pulled from the summary, the sentences describe the 2026-10-03 run."""
    if not lad.get("has"):
        return ""
    L = summary["ladder"]
    rungs, pm = L["rungs"], lad["pm"]
    N = lambda m: MODEL_META[m][0]  # noqa: E731
    big, small = models[-1], models[0]

    def sh(m, k):
        v = pm.get(m, {}).get(k, {}).get("share")
        return _pct(v) if v is not None else "–"

    def ids(k):
        return [m for m in models if pm.get(m, {}).get(k, {}).get("id_hit")]

    def seq(k):
        return " / ".join(sh(m, k) for m in models)

    real = [k for k, r in rungs.items() if r["expected"] not in ("none", "floor", "public-invented")]
    all_id = [k for k in real if len(ids(k)) == len(models)]
    partial = [(k, [m for m in models if m not in ids(k)]) for k in real if 0 < len(ids(k)) < len(models)]
    none_id = [k for k in real if not ids(k)]
    corr = lad["corr"]
    corr_txt = ", ".join(f"{N(m)} {c['spearman']:+.2f} ({'p = ' + format(c['p'], '.3f') if c.get('p') is not None and c['p'] < 0.05 else 'not significant' + (', p = ' + format(c['p'], '.2f') if c.get('p') is not None else '')})"
                         for m in models if (c := corr.get(m)))
    # lowest real rung per model
    low = {m: min(real, key=lambda k: pm.get(m, {}).get(k, {}).get("share") if pm.get(m, {}).get(k, {}).get("share") is not None else 9) for m in models}
    noart = [k for k in real if not rungs[k]["footprint"].get("title")]
    noart_txt = "; ".join(f"{rungs[k]['label'].split(' (')[0]} {seq(k)}" for k in noart)
    post = [k for k, r in rungs.items() if r["expected"] == "none"]
    meyer, near = ("meyer" if "meyer" in rungs else None), ("near" if "near" in rungs else None)

    def idword(m, k):
        x = pm.get(m, {}).get(k, {})
        return "named it" if x.get("id_hit") else ("said it could not tell" if x.get("id_unknown") else "named a different case")
    meyer_txt = ""
    if meyer:
        meyer_txt = (", ".join(f"{N(m)} {idword(m, meyer)}" for m in models)
                     + "; asked to describe the case by name, all three decline (" + " / ".join(sh(m, meyer) for m in models) + " of the facts the question did not state)")
    near_txt = ""
    if near:
        near_txt = (", ".join(f"{N(m)} {idword(m, near)}" for m in models) + "; recall beyond the question " + seq(near))
    return f"""<p>The anchors fixed the ends of the scale; the ladder shows its shape, on matters chosen to resemble the study's own. Three things stand out. First, <b>the floor for a real, litigated matter is high</b>. The lowest real rung for each model is {', '.join(f"{N(m)}: {rungs[low[m]]['label'].split(' (')[0]} at {sh(m, low[m])}" for m in models)}; nothing that was ever charged, tried or settled in public comes out blank. A distributor criminally charged in 2019 that has no Wikipedia article at all, and the largest MDL in history, which also has none, are recalled at {noart_txt}. Legal matters live in sources — DOJ and SEC press releases, dockets, opinions, law-firm client alerts — that are crawled thoroughly and read rarely, so public <em>popularity</em> understates what the models carry.</p>
<p>Second, <b>scale flattens the ladder</b>. Across the matters with an article, the rank correlation between twelve-month pageviews and recall is {corr_txt}. For the small and mid models, fame predicts knowledge: a 1938 wholesaler fraud or a 1973 insurance fraud is half-known, a 2002 fraud that made the business pages for a season is two-thirds known, a byword is fully known. For {N(big)} the correlation is not significant at {len(real)} rungs — Texaco v. Pennzoil, HealthSouth, Dalkon Shield and Rochester Drug all score ≥ 90% — consistent with it knowing the obscure rungs about as well as the famous ones, though {len(real)} matters is a small sample for the comparison. The practical consequence for the study is that "obscure" is not a defence at frontier scale; only "after the cutoff" is.</p>
<p>Third, <b>identification is nearly binary</b>. {len(all_id)} of the {len(real)} real matters are named by every model from a sketch with every proper noun removed{'; ' + '; '.join(f"{rungs[k]['label'].split(' (')[0]} is missed only by {', '.join(N(m) for m in ms)}" for k, ms in partial) if partial else ''}{'; ' + ', '.join(rungs[k]['label'].split(' (')[0] for k in none_id) + ' by none' if none_id else ''}. Recognition of a fact pattern precedes recall of its details and is almost complete for anything that reached the national press, however long ago. A pseudonymised complaint or a redacted request is identifying information for any real matter the model has met at all; §15 showed that for Enron, and the ladder shows it is the rule.</p>
<p>The post-cutoff rungs are the control the fictional matter cannot supply: real cases the models cannot have read about. For the September 2026 adviser case, {meyer_txt}. {N(models[1]) if len(models) > 2 else ''}'s answer is worth reading: it names a specific prior SEC case, defendant and filing date that we cannot find and whose particulars reproduce the sketch — a confident, concrete identification of a matter that does not exist in its training data, where the other two models say the date is beyond what they can verify. Near Intelligence straddles the cutoff and behaves accordingly: {near_txt}. The models know the company's December 2023 collapse (it was news) and decline to describe the 2026 complaint; {N(big)} dates itself to a June 2024 cutoff in its answer. One caveat: the sketches carry their dates, and the models use "2026 is in the future" as a reason to decline. A stricter version would omit the date and see whether they still know they do not know.</p>
<p>Where the study's matters sit. <b>Enron</b> ({seq('enron')}) is in the top group with Bhopal, the Clinton server, Microsoft and WorldCom — the matters the models know almost entirely. <b>Jeb Bush</b> ({seq('jebbush')}) is well below the two e-mail scandals that share its family (Bridgegate {seq('bridgegate')}, the Clinton server {seq('clinton_email')}): a governorship is remembered as a list of controversies, not as a cast. <b>Mallinckrodt</b> ({seq('mnk')}) is the least-known real matter on the whole ladder for every model — below Rochester Drug and Insys, its opioid-family peers, and below a 1938 fraud. That is the useful surprise: of the real e-mail corpora, the one whose matter the models know least is a recent one, because its record is an MDL docket and a bankruptcy rather than a trial with a narrative. <b>Endo</b> ({seq('endo')}) sits just above it: the matter is known at least as well as Mallinckrodt's by {_better_txt(models, pm, 'endo', 'mnk', N)} despite a smaller public footprint ({rungs['endo']['footprint'].get('views_12m', 0):,} pageviews against {rungs['mnk']['footprint'].get('views_12m', 0):,}), while its documents, published after the cutoff, are at the floor — the ladder shows the case and Part I shows the collection, and they disagree in the direction the study wants. Its opioid peers added as rungs confirm the family: <b>Teva</b> ({seq('teva')}) and <b>JUUL</b> ({seq('juul')}), with footprints of {rungs['teva']['footprint'].get('views_12m', 0):,} and {rungs['juul']['footprint'].get('views_12m', 0):,}, are identified by every model and recalled at the Enron end of the scale. <b>Veridian</b> sits at the bottom with the post-cutoff case, where a floor should be. The ladder turns Part II's "high / medium / low" into positions among named peers, and it gives the study a way to place any future corpus before spending money on it: find the matter's rung, or — for a small model — read it off the footprint.</p>"""


def _part2_narrative(summary: dict, models: list[str]) -> dict[str, str]:
    """Interpretive paragraphs for Part II. Written against the 2026-10-03 run; the numbers are pulled from the summary so they stay current
    if the probes are re-run, while the sentences around them describe that run."""
    MI, MR, EP, MD = summary["matter_id"], summary["matter_recall"], summary["evidence_prior"], summary["metadata_relevance"]
    big = models[-1]
    N = lambda m: MODEL_META[m][0]  # noqa: E731

    def seq(key, st, fmt=lambda v: f"{v:.0f}"):
        return " / ".join(fmt(EP[m][st][key]) if EP.get(m, {}).get(st) and EP[m][st].get(key) is not None else "–" for m in models)

    def mseq(fn):
        return " / ".join(fn(m) for m in models)

    sd = _sd

    # M0
    id_hits = {k: [m for m in models if MI.get(m, {}).get(k, {}).get("hit")] for k in ("enron", "enron_k", "mnk", "endo", "jebbush", "microsoft")}
    enron_miss = [m for m in models if MI.get(m, {}).get("enron") and not MI[m]["enron"]["hit"]]
    def _ver_correct(m):
        x = MI.get(m, {}).get("veridian")
        return bool(x) and (x["unknown"] or bool(re.search(r"composite|fabricat|fiction|no identifiable|not a real|hypothetical", (x["first_line"] or "").lower())))
    ver_correct = [m for m in models if _ver_correct(m)]
    ver_named = [m for m in models if MI.get(m, {}).get("veridian") and not _ver_correct(m)]
    m0 = f"""<p>Every model decodes every real matter from its fact pattern. Complaint K's "Bleak Horizon" is Deepwater Horizon for all three, with BP, Transocean and Halliburton supplied unprompted; the Mallinckrodt, Endo, Jeb Bush and Microsoft sketches — which contain no proper noun at all — are named at once{'' if len(id_hits['endo']) == len(models) else ' (Endo by ' + (', '.join(N(m) for m in id_hits['endo']) or 'no model') + ')'}. Complaint J, TREC's pseudonymised Enron, is identified as Enron by {', '.join(N(m) for m in id_hits['enron']) or 'no model'}{'; ' + ', '.join(N(m) for m in enron_miss) + ' instead names Reliant Energy, another Houston company caught up in the California crisis, reading the complaint\'s invented code name "RND7" as a disguised Reliant trading strategy' if enron_miss else ''}. Either way the pseudonym does what a pseudonym must not: it sends the reader to a real case, with that case's record attached.</p>
<p>The fictional matter shows the other failure. {', '.join(N(m) for m in ver_named) or 'No model'} state{'s' if len(ver_named) == 1 else ''} confidently that Veridian is Zimmer Biomet — because the sketch says Warsaw, Indiana and metal-on-metal, and Warsaw is where Zimmer Biomet is. {', '.join(N(m) for m in ver_correct) or 'No model'} give{'s' if len(ver_correct) == 1 else ''} the correct answer ("no identifiable real company; a composite") while listing the three real litigations it is a composite of. So the synthetic control is clean at the level of documents and people, but its <em>archetype</em> is recognised, and a model reviewing Veridian documents is bringing some knowledge of how metal-on-metal hip litigation went. That is the floor's one impurity, and it is now measured rather than assumed.</p>"""

    # M1
    def share(m, k, key="share"):
        x = MR.get(m, {}).get(k)
        return _pct(x[key]) if x and x.get(key) is not None else "–"
    m1 = f"""<p>Enron and Microsoft behave like the ceiling they were expected to be: {mseq(lambda m: share(m, 'enron'))} of the Enron checklist and {mseq(lambda m: share(m, 'microsoft'))} of Microsoft's, and on Enron the <em>beyond-context</em> share is higher still ({mseq(lambda m: share(m, 'enron', 'share_beyond'))}) because what the models add is exactly what the complaint does not say: Fastow, Skilling, Lay, Causey, Watkins, LJM and the Raptors, Andersen, Dynegy, the 2006 convictions, Sarbanes-Oxley. The two Enron items every model misses are telling: "document shredding" and "the California trading schemes" — the operational facts behind TREC topics 204 and 205 — are absent from essays that otherwise recite the case in full. The models know Enron as a <em>securities fraud</em>; the parts of the record that TREC's requests actually target are the parts they skip.</p>
<p>Mallinckrodt is known as a <em>procedural</em> story. The models score {mseq(lambda m: share(m, 'mnk'))} overall but {mseq(lambda m: share(m, 'mnk', 'share_beyond'))} on the beyond-context facts — the MDL, Judge Polster, SpecGx, the 2017 DEA settlement, the 2020 Chapter 11, the trust — while missing almost every allegation item: Exalgo, suspicious-order monitoring, chargeback data, pill mills, quota. Those are the facts the study's task context supplies, so the models are not advantaged by knowing them; but it also means the models do not independently know what the review is <em>about</em>. They know how the case ended, not what the e-mails say.</p>
<p>Jeb Bush is the weakest of the real matters ({mseq(lambda m: share(m, 'jebbush'))}) and the category grid shows why: the <b>people</b> row is 0% for every model. The recount, Schiavo, One Florida, the hurricanes and the vouchers are recalled; James Crosby, the lieutenant governors, Jerry Regier are not. Public controversies are known; the administration's cast is not. Veridian is the floor as designed: all three models answer that they do not know the matter, in {mseq(lambda m: str(MR[m]['veridian']['n_words']) if MR.get(m, {}).get('veridian') else '–')} words, without inventing a single fact.</p>"""

    # M2
    tot = lambda st: seq("n_discriminative_named_total", st)  # noqa: E731
    m2 = f"""<p>This is the probe that turns exposure into something a classifier could use, and it produces the sharpest result in the study. Under TREC's pseudonym the models volunteer almost no real names for the Enron scandal requests — {seq('n_novel_named_mean', 'enron_j', lambda v: f'{v:.1f}')} named terms per request beyond the prompt, {tot('enron_j')} discriminative in total across seven requests — and their notes say why: "I know only the supplied fictionalized complaint summary." Name the company and the same requests yield {seq('n_novel_named_mean', 'enron_j_named', lambda v: f'{v:.1f}')} named terms per request, {seq('grounded_rate_named', 'enron_j_named', _pct)} of them real, and <b>{tot('enron_j_named')} discriminative named terms</b> (Luna / Terra / Sol). For {N(big)} they are the actual record of the case: Mahonia and Yosemite and Delta for prepay; Raptor I–IV, Talon and Chewco for FAS 140; David Duncan, Nancy Temple and Michael Odom — the Andersen partners in the shredding — for document destruction; Fastow, Skilling, Lay and the analysts' banks for analyst contacts. Each is over-represented among the responsive documents by a factor of 2.7 to 11.7. A reviewer who searched for them first would be most of the way to the responsive set before reading anything.</p>
<p>The Complaint K requests are the within-corpus control: same mailbox, same models, requests that are not Enron's story. They yield {tot('enron_k')} discriminative named terms. The knowledge is specific to the case, not to the corpus. Mallinckrodt sits low ({tot('mnk')}) but not at zero: {N(big)} names <b>Xartemis XR</b>, a Mallinckrodt opioid the task context does not mention, Broward County and South Florida for the pill-mill request, and DEA's Office of Diversion Control for quota — the vocabulary of someone who has read the complaints. Jeb Bush yields {tot('jebbush')} on a 600-document subset, with real Florida officials at the top (Coleman Stipanovich at the State Board of Administration for Movie Gallery, Jerry Regier at DCF for Rilya Wilson, Alan Levine at AHCA for Medicaid), which is the "surrounding details" channel Part I only glimpsed through the recognition matrix.</p>
<p>Veridian gives the floor its number: {tot('veridian')} discriminative named terms across ten requests, and they are domain institutions rather than case facts — FDA, the NJR and AJRR joint registries. Generic keywords (right-hand chart) discriminate at 20–40% on every corpus including Veridian; that is vocabulary, and it is what a reviewer with no knowledge of the case brings. The named-term rate is the case-knowledge signal, and it separates the pseudonymised Enron, the named Enron and the fictional matter by an order of magnitude.</p>"""

    # M3
    def md_get(m, st, k):
        x = MD.get(m, {}).get("by_set", {}).get(st)
        return x[k] if x else None
    sig = [(m, st) for m in models for st in META_SET_ORDER if (x := MD.get(m, {}).get("by_set", {}).get(st)) and x["delta_people_ci"][0] > 0]
    m3 = f"""<p>The arrows are short. Given the matter, the request and the subject line, the models already call responsiveness at {mseq(lambda m: _pct(md_get(m, 'enron_j', 'acc_subject')))} on the Enron scandal requests, {mseq(lambda m: _pct(md_get(m, 'mnk', 'acc_subject')))} on Mallinckrodt and {mseq(lambda m: _pct(md_get(m, 'jebbush', 'acc_subject')))} on Jeb Bush — far above the lexical baseline of 52–64%, which is the models reading the subject line semantically rather than matching words. Adding who sent and received the e-mail moves those numbers by {mseq(lambda m: sd(md_get(m, 'enron_j', 'delta_people')))} on Enron and by {mseq(lambda m: sd(md_get(m, 'veridian', 'delta_people')))} on Veridian. {('Only ' + '; '.join(f'{N(m)} on {SET_LABEL[st]}' for m, st in sig) + ' clear' + ('s' if len(sig) == 1 else '') + ' zero, by two to three points.') if sig else 'No paired difference excludes zero.'} At the level of a relevance call made from metadata, knowing the people is worth almost nothing once the subject is known — on the real corpora as on the fictional one.</p>
<p>Two further readings. First, the Veridian numbers ({mseq(lambda m: _pct(md_get(m, 'veridian', 'acc_subject')))} from the subject alone) are higher than any real corpus's, which says something about the synthetic matter rather than about contamination: its subject lines are more diagnostic than real ones. That is a realism caveat for the main study, and it is a finding this probe produced for free. Second, the per-request table shows that where the people do help (Medicaid reform, financial forecasts, Rilya Wilson, prepay) the gain is 5–10 points on 30–40 e-mails, which is the scale of effect the full-document ablation should be powered to see.</p>"""

    # verdicts
    verd = table(["corpus", "Part I · documents & people", "Part II · the case", "combined reading for the study"], [
        [_corpus_th("veridian"), "floor on every channel", "called a composite by " + (', '.join(N(m) for m in ver_correct) or 'no model') + "; mapped to Zimmer Biomet by " + (', '.join(N(m) for m in ver_named) or 'no model') + "; recall 'unknown'; " + tot('veridian') + " discriminative named terms (domain institutions); people add " + mseq(lambda m: sd(md_get(m, 'veridian', 'delta_people'))),
         "At the floor on documents, people and facts, as a fictional matter must be. Its <em>archetype</em> (metal-on-metal hip MDL) is known, and its subject lines are easier than real ones. Still the right no-knowledge control; report both caveats."],
        [_corpus_th("jebbush"), "no document-level signal; famous Florida figures recognised, tail not", "identified from a sketch by all; record " + mseq(lambda m: share(m, 'jebbush')) + " with the cast at 0%; " + tot('jebbush') + " discriminative named terms (agencies and their heads); people add " + mseq(lambda m: sd(md_get(m, 'jebbush', 'delta_people'))),
         "The <em>issues</em> are known (they were national news); the <em>people</em> in the mailbox mostly are not. Knowledge the models have is close to what the task context already gives them. Low risk." + _verdict_r2(summary, "jebbush")],
        [_corpus_th("enron"), "documents at floor; scandal executives recognised, tail 0%", "pseudonymised complaint decoded; record " + mseq(lambda m: share(m, 'enron')) + "; <b>" + tot('enron_j') + " → " + tot('enron_j_named') + "</b> discriminative named terms pseudonym → named; K topics " + tot('enron_k') + "; people add " + mseq(lambda m: sd(md_get(m, 'enron_j', 'delta_people'))),
         "<b>The case is in the model; we found no sign the mailbox is.</b> The knowledge is real, specific to the scandal requests, and actionable as search terms — but it lies dormant under the pseudonym and adds little at the metadata level. Report Enron as a known matter; the full-document ablation (§20) bounds the name-mediated knowledge effect at a few points of F1 with intervals through zero, with the caveat that the models still recognise the case after renaming, so smaller or name-independent effects are not excluded."],
        [_corpus_th("mnk"), "documents at floor; Sol recognises 30% of staff", "identified from a sketch by all; procedural record " + mseq(lambda m: share(m, 'mnk', 'share_beyond')) + " but allegations ~17%; " + tot('mnk') + " discriminative named terms (Xartemis XR, Broward County, Office of Diversion Control); people add " + mseq(lambda m: sd(md_get(m, 'mnk', 'delta_people'))),
         "Known as a settlement and a bankruptcy, not as a set of e-mails. Modest case knowledge, concentrated in the large model. Medium risk; a case brief moves F1 by under a point (§20)."],
        [_corpus_th("endo"), "documents at the floor; cast unknown (recall 0%)", "identified from a sketch by " + (', '.join(N(m) for m in id_hits['endo']) or 'no model') + "; record " + mseq(lambda m: share(m, 'endo')) + " (better than Mallinckrodt's " + mseq(lambda m: share(m, 'mnk')) + "); " + tot('endo') + " discriminative named terms; people add " + mseq(lambda m: sd(md_get(m, 'endo', 'delta_people'))),
         "<b>The case is known and the documents show no signal, as a post-cutoff collection should — Enron's pattern from the other side.</b> A real collection published after the cutoff gives the floor Veridian imitates, with a known matter attached. Recommended held-out benchmark; its labels come from a three-OpenAI-model panel, unlike Mallinckrodt's mixed panel, which is a caveat on its gold rather than on its contamination profile."],
        [_corpus_th("cuad"), "documents above the e-mail floor (consistent with memorisation of republished contracts; floor not genre-matched); benchmark categories recited", "n/a (not a litigation matter)", "Unchanged from Part I: most exposed corpus; do not use for headline claims." + _verdict_r2(summary, "cuad")],
    ], cls="tbl wide")
    verdicts = f"""<p>Part I and Part II answer different questions about the same corpora, and for Enron they answer them differently. The table reads across both.</p>
{verd}
<p>The general lesson is about the unit of contamination. For a text benchmark the unit is the document; for a legal review it is the <em>matter</em>, and the evidence here is that a matter can be thoroughly inside a model while no document-level memory of its e-mails is detectable — for Enron, a corpus that is in open training sets, memorisation evidently tracks repetition rather than presence. The first battery would have cleared Enron; the second does not. Both are needed, and the second is the one specific to eDiscovery.</p>"""
    return {"m0": m0, "m1": m1, "m2": m2, "m3": m3, "verdicts": verdicts}


def _part2_html(p2: dict, summary: dict, models: list[str]) -> str:
    if not p2.get("has"):
        return ('<section id="part2"><h2>Part II — Is the case inside the model?</h2><p>No matter-probe results yet. Run '
                '<code>bench contam-run -p matter_id -p matter_recall -p evidence_prior -p metadata_relevance</code> and re-score.</p></section>')
    big_name = MODEL_META[p2["big"]][0]
    narrative = _part2_narrative(summary, models)
    lad = _ladder(summary, models)
    ladder_narrative = _ladder_narrative(summary, models, lad)
    if not lad.get("has"):
        lad = {"fig": "<p>No ladder results yet. Run <code>bench contam-run -p matter_id -p matter_recall -c ladder</code> and re-score.</p>", "fig2": "", "tbl": ""}
    return f"""<section id="part2">
<h2>Part II — Is the case inside the model?</h2>
<h2 class="sub2">Methodology</h2>

<h3 id="legal">13. Why the case matters: the legal frame</h3>
<p>Part I treated the corpora as text: are the documents memorised, are the correspondents known, are the benchmark's topics and labels known? It found the e-mail corpora near the floor on documents and the cast known only where it is famous. That is reassuring, and it is also the wrong unit of analysis for legal discovery.</p>
<p>A relevance review is not defined by a corpus. It is defined by a <em>matter</em>: a complaint, the allegations in it, the parties and their people, the factual record the parties will fight over, and — once it is over — the outcome. A reviewer who already knows the case reads every document differently from one who does not. They know which transactions were later found to be fraudulent, which executives were indicted, which code names mattered, which customers were the "pill mills", which year the shredding happened. They can tell that an e-mail from the CFO about an offshore vehicle is responsive to a request about debt-concealment without the request saying "offshore vehicle". The request text and the task context we give every model are the same; the <em>prior</em> each model brings to them is not.</p>
<p>Four of the study's six corpora come from matters that are among the most-documented in American legal history. Enron is the textbook corporate fraud; the Mallinckrodt and Endo documents come from the opioid MDL, the largest civil litigation of its era; the Jeb Bush e-mails are the public record of a two-term governorship whose controversies (the 2000 recount, Terri Schiavo) were national news. Jev has read none of this. If a frontier model has, then on these corpora it is not a fresh reviewer but a reviewer who has read the press, the indictments and the settlements — and its score is partly a score for hindsight.</p>
<p>So Part II asks a different question from Part I: <b>not "has the model seen these documents?" but "does the model know this case, and is what it knows the kind of knowledge that changes a relevance call?"</b> Four things a case-aware reviewer has, each of which becomes a probe:</p>
{table(["what a case-aware reviewer has", "how it helps a relevance call", "probe"], [
    ["<b>recognises the matter</b> even when names are changed", "every pseudonymised complaint or redacted request becomes the real case in the reviewer's head, with everything that comes with it", "<b>M0</b> identification from a de-identified sketch"],
    ["<b>knows the record</b>: allegations, players, timeline, outcome", "a prior over what responsive documents are about, who wrote them and when; hindsight about which conduct was later found wrongful", "<b>M1</b> recall against a fact checklist"],
    ["<b>knows what to look for</b> before opening a document", "the names, deal names, products and code words that mark responsive documents — the terms an informed reviewer searches for first", "<b>M2</b> evidence prior, scored against the labelled corpus"],
    ["<b>knows who the people are</b>", "a judgment from the sender and recipients alone, before reading the body: the CFO's e-mail to the bank is probably about the deal", "<b>M3</b> metadata-only relevance, with and without the people"],
], cls="tbl wide")}
<p>M0 and M1 measure <em>exposure</em> to the case, as Part I did for the documents. M2 is the bridge: it measures whether the exposure is <em>actionable</em>, by checking the model's expectations against the documents' actual labels. M3 is a small <em>effect</em> test: it changes what the model sees and watches whether the relevance call changes.</p>

<h3 id="mprobes">14. The matter probes and their controls</h3>
<h4>M0 · Matter identification</h4>
<p>For Enron we use the TREC Legal Track's own pleadings, which were written to be fictional: Complaint J puts Enron's exact class period (June 1, 1999 – December 2, 2001), prepay transactions, FAS 140, shredding and energy-schedule manipulation under the name "Volteron Corp."; Complaint K is an oil-spill class action over the sinking of the "Bleak Horizon". The model sees ~2,500 characters of each complaint and is asked which real company or case it is modelled on. For Mallinckrodt, Endo, Jeb Bush, Veridian and the ceiling matter we write a short sketch with every proper noun removed. A hit names the real matter. For Veridian the correct answer is "no real matter"; we record whether the model instead names a real template (DePuy ASR, Zimmer Biomet, Stryker…), because a synthetic matter built on a famous archetype inherits some of that archetype's knowledge.</p>
<h4>M1 · Matter recall against a checklist</h4>
<p>"Describe {{matter}}: parties, key allegations, key people, main events with dates, outcome." Graded against a hand-written checklist of 16–20 facts per matter spanning five categories (parties, allegations, people, events, outcome), keyword-matched on whole words. Two refinements make the number meaningful for the study. First, every item is flagged as <em>in context</em> or <em>beyond context</em>: the study's task context already tells every model that Mallinckrodt is accused of weak suspicious-order monitoring, so reciting that is not an advantage; knowing about the 2017 DEA settlement or the Chapter 11 is. We report both the total and the beyond-context share. Second, the Veridian matter is asked under its full fictional caption (MDL No. 3102, N.D. Ind.); the right answer is "I do not know this matter", and anything else is a confabulation whose length we record.</p>
<h4>M2 · Evidence prior</h4>
<p>The model is given exactly what it gets in the study — the matter context and one request — and asked, as the review lead with no documents yet seen, for the 25 most specific things it expects in responsive documents, each typed as a person, organisation, code name, product, place, period or keyword. Scoring is against the labelled corpus. Terms already present in the context or request are discarded (the model was told those). Of the remaining <em>named</em> terms we ask two questions: is it <b>grounded</b> — does it actually occur in at least two judged documents? — and is it <b>discriminative</b> — is it at least twice as frequent among responsive documents as overall (lift ≥ 2, in ≥ 2 responsive documents)? A grounded, discriminative named term is a piece of case knowledge that a search or a classifier could use directly. Generic keywords ("spreadsheet", "wholesaler") are scored the same way but reported separately: they measure vocabulary, not knowledge of the case.</p>
<p>Enron supplies two built-in contrasts. The seven Complaint J requests (201–207) are the real scandal — prepay, FAS 140, forecasts, shredding, energy schedules, analysts — plus one control topic, fantasy football, that TREC added for exactly this reason; the three Complaint K requests (301–303: oil and gas drilling, spill response, lobbying) are not Enron's story at all. And the Complaint J requests are run twice: once as TREC wrote them, under the "Volteron" pseudonym, and once with the company named. The difference between those two runs is the knowledge that the pseudonym suppressed, and the difference between J and K is the knowledge that is specific to the actual case.</p>
<h4>M3 · Metadata-only relevance</h4>
<p>For each request we draw a balanced sample of responsive and non-responsive e-mails (20 + 20; 15 + 15 for Jeb Bush) and show the model the matter context, the request and <em>only the header metadata</em> — no body. Each e-mail is shown twice: with Date, From, To, Cc and Subject, and with Date and Subject alone. The paired difference in accuracy is what seeing the people added. Because the sample is balanced within every request, chance is 50% and the request itself carries no label information; a lexical baseline (a request-title word appearing in the subject line) shows what plain keyword matching achieves on the same e-mails. Veridian is the control for the people channel: its names are fictional, so any lift its headers give comes from structure (domains, distribution lists, FDA addresses), not from knowing who anyone is. For Enron the context states that "Volteron" is Enron, so that the headers condition does not also reveal which company it is.</p>
<h4>The ladder · real matters at graded exposure</h4>
<p>Two anchors fix the ends of a scale; they do not show its shape. To read the study's matters as positions rather than as isolated numbers, M0 and M1 are also run on a <em>ladder</em> of {len(LADDER)} real matters from the last ninety years, chosen in families that mirror the corpora: accounting and securities frauds for Enron (WorldCom, HealthSouth, Peregrine Systems, Equity Funding, McKesson &amp; Robbins); opioid cases for Mallinckrodt and Endo (Purdue, Insys, Rochester Drug Co-operative, Teva, JUUL as the adjacent public-nuisance case); e-mail in public life for Jeb Bush (the Clinton server, Bridgegate, the Sony Pictures hack); device mass torts for Veridian (Dalkon Shield, DePuy ASR, the 3M earplugs, Bair Hugger); landmark disputes across the century (Bhopal, Texaco v. Pennzoil, Dieselgate, Theranos, FTX); and two <b>post-cutoff controls</b> — SEC accounting-fraud actions filed in 2026 against the former officers of Near Intelligence and against Meyer Global Management — which are real but cannot be in the training data. Each rung gets the same de-identified sketch and the same checklist grading as the study's matters (10–18 facts each). Alongside, an independent proxy for public exposure is recorded for every matter: the length, number of language editions and last-twelve-months pageviews of its English Wikipedia article (none for the fictional and post-cutoff matters, and for a few real ones that have no article). The expectation is a gradient — recall rising with footprint within each family — with the post-cutoff matters behaving like Veridian.</p>
<h4>Controls and expectations</h4>
{table(["", "role", "why"], [
    ["Veridian", "<span class=\"role floor\">floor</span>", "a fictional matter: identification should fail, recall should be 'unknown', no named term can be grounded except by accident, and headers carry no knowledge of people"],
    ["U.S. v. Microsoft", "<span class=\"role ceiling\">ceiling</span> (M0, M1)", "a famous case built on e-mail evidence; shows what saturation of case knowledge looks like on the two exposure probes"],
    ["Enron Complaint K vs J", "within-corpus contrast (M2, M3)", "same mailbox, same models; one set of requests is the real scandal and the other is not"],
    ["Enron pseudonym vs named", "within-request contrast (M2)", "same requests, same documents; the only change is whether the company is named"],
    ["The ladder", "calibration (M0, M1)", "real matters at graded public footprint, in families matching the corpora; two post-cutoff cases as a real-but-unseen floor"],
], cls="tbl kv")}
<p><b>Pre-registered expectations</b> (written before the run): M0: Enron and Microsoft identified by every model; Mallinckrodt by the large model; Jeb Bush by all; Veridian not identified but mapped to a metal-on-metal template. M1: Enron ≈ Microsoft &gt; Jeb Bush &gt; Mallinckrodt; Veridian unknown. M2: discriminative named terms concentrated in the Enron scandal requests and larger when the company is named; near zero on Veridian; Mallinckrodt small except for DEA/regulator names. M3: headers add more on Enron than on Veridian; largest gains on requests whose responsive documents cluster on a few custodians.</p>
</section>

<section id="results2">
<h2 class="sub2">Results</h2>

<h3 id="m0">15. M0 · The pseudonyms do not hold</h3>
{p2["tbl_m0"]}
{narrative["m0"]}

<h3 id="m1">16. M1 · How much of the record is in the model</h3>
{legend(models)}
<div class="grid2">{p2["fig_m1"]}{p2["fig_m1b"]}</div>
{p2["fig_m1c"]}
{p2["tbl_m1"]}
{narrative["m1"]}

<h3 id="ladder">17. The ladder: where the study's matters sit among real cases</h3>
{legend(models)}
{lad["fig"]}
{lad["fig2"]}
{ladder_narrative}
{lad["tbl"]}
<p class="fignote">Expected: the pre-registered guess at exposure (high / mid / low; 'none' = post-cutoff). M0 marks per model: ● named the matter, ○ named something else, ? said it could not tell. The last column lists the facts the largest model did not mention.</p>

<h3 id="m2">18. M2 · Is the knowledge actionable? The evidence prior against the labels</h3>
<div class="grid2">{p2["fig_m2c"]}{p2["fig_m2a"]}</div>
<div class="grid2">{p2["fig_m2b"]}{p2["fig_m2d"]}</div>
{narrative["m2"]}
{p2["tbl_m2"]}
<p class="fignote">Rates are means over requests. 'Named' = person, organisation, code name, product or place; 'generic' = keyword or period. Grounded: occurs in ≥ 2 judged documents for the request. Discriminative: grounded, in ≥ 2 responsive documents, and lift ≥ 2.</p>
<h4>What the discriminative terms are — {_esc(big_name)}, request by request</h4>
<p>The table is the evidence behind the rates. Each row is one request; the bold terms are named things the model expected to find, which do occur in the judged documents and are over-represented in the responsive ones. The last column is the model's own one-sentence statement of how much it knew.</p>
{p2["tbl_m2_terms"]}

<h3 id="m3">19. M3 · Does knowing the people move the call?</h3>
{p2["fig_m3"]}
{narrative["m3"]}
{p2["tbl_m3"]}
<p class="fignote">Stars: two-sided binomial vs 50% (* p&lt;0.05, ** p&lt;0.01, *** p&lt;0.001). Δ people: paired bootstrap 95% CI over e-mails. 'Fixed / broken': e-mails the subject-only condition got wrong that the headers got right, and the reverse.</p>
<h4>Per request — {_esc(big_name)}, sorted by how much the people helped</h4>
{p2["tbl_m3_topics"]}

<h3 id="verdicts2">22. Combined verdicts: documents, people and the case</h3>
{narrative["verdicts"]}
</section>"""


def _effect_section(summary: dict, heading: str = "20. Effect: the pseudonymisation ablation") -> str:
    """The results of the full-document effect test, data-driven from results/ablation/summary.json; a short pointer if it has not run."""
    e = _effect(summary)
    if not e:
        return (f'<h3 id="effect">{heading}</h3><p>The full-document pseudonymisation ablation (results/ablation/) has not been run yet; when it has, its result is reported here.</p>')
    return f"""<h3 id="effect">{heading}</h3>
<p>Everything above measures what is <em>in</em> the model. The ablation measures what it is <em>worth</em>: a fixed sample of documents is classified twice, once as-is and once with every
person and organisation consistently renamed, on the Enron Complaint J requests (where Part II found the knowledge), on the Complaint K requests from the same mailbox (control), and on
Veridian (fictional, so renaming can only cost). Jev ran as a fourth system. Full method, per-request tables and the dose–response analysis are in the
<a href="{e["href"]}">ablation report</a>; spend ${e["cost"]:,.2f}.</p>
{e["fig"]}
{e["result"]}
{e["tbl"]}
<p class="fignote">Paired bootstrap 95% intervals over documents; 'labels flipped' is the share of documents whose call changed in either direction; the Mallinckrodt column compares the bare request with a short case brief rather than named with renamed.</p>
{e["leak"]}
{e["jev"]}
{e["brief"]}
{_effect_round2_html(summary)}
{_verify_html(summary)}
"""


def _img(src: str, alt: str) -> str:
    """A results figure embedded by relative path (the PNGs live beside their summary.json; the page is otherwise self-contained)."""
    return f'<figure><img src="{_esc(src)}" alt="{_esc(alt)}" style="max-width:100%;height:auto;border:1px solid var(--line);border-radius:6px;background:#fff"></figure>'


def _effect_round2_html(summary: dict) -> str:
    """Round 2 of the ablation (CUAD rename + paraphrase; Jeb Bush matter vs control), the three-matter summary and the Jev account; empty if round 2 has not run."""
    e2 = _effect2(summary)
    if not e2:
        return ""
    cost = f" Spend ${e2['cost']:,.2f} paid." if e2.get("cost") is not None else ""
    return f"""<h4 id="effect2">Round 2 · CUAD (rename and paraphrase) and Jeb Bush (matter vs control topics)</h4>
<p>Round 1 could not cover the two corpora where the question has a different shape: CUAD, the one corpus with document-level memorisation, where the models hold the <em>text</em>
and renaming parties removes nothing that memory is keyed on; and Jeb Bush, where the models hold no trace of the collection but recite the governorship — the familiar matter,
unfamiliar documents case. Round 2 ran both on {e2["sys_txt"]}. {e2["absent_txt"]} Method, per-request tables, dose–response and the leakage check are in the
<a href="{e2["href"]}">round-2 report</a>.{cost}</p>
{e2["cuad_fig"]}
{e2["cuad_result"]}
{e2["cuad_tbl"]}
{e2["cuad_caveat"]}
<p class="fignote">Cluster bootstrap by contract (B = 2000); flips are individual (excerpt, clause) decisions out of 14,400. The last column is the Spearman correlation between a contract's
Δaccuracy and its memorisation score (finish-the-document LCS-F1 on its own text, pooled over the LLMs); a dose–response would show as a negative ρ.</p>
<details><summary>What the perturbations do to verbatim retrievability (finish-the-document probe, scored against the original continuation)</summary>{e2["memo_tbl"]}
<p class="fignote">Two windows per contract; the paraphrased and renamed versions of the same windows, scored against the <em>original</em> continuation. {e2["memo_txt"]}</p></details>
{e2["jeb_fig"]}
{e2["jeb_result"]}
{e2["jev_p"]}
{e2["jeb_tbl"]}
<p class="fignote">1,000 e-mails × 12 requests; cluster bootstrap by document. Matter topics: the 2000 recount, Rilya Wilson, Medicaid reform, George W. Bush, Terri Schiavo.
Control topics: movie gallery, condominiums, bottled water, marketing, faith-based initiatives, NRA (two requests).</p>
<details><summary>The round-2 report's own figures (PNG, relative path)</summary>{_img(e2["figs"]["cuad"], "CUAD: effect of renaming and paraphrasing on F1")}
{_img(e2["figs"]["jeb"], "Jeb Bush: renaming the Governor and Florida's public figures, matter vs control topics")}</details>
{e2["three"]}
{e2["jev_account"]}
"""


def _verify_html(summary: dict) -> str:
    """The generalisation checks A–D in one subsection: a verdict line each, the brief-injection figure, and links to the full report; empty if they have not run."""
    v = _verify(summary)
    if not v:
        return ""
    sp = v.get("spend", {})
    spend = f" New OpenAI spend ${sp['total']:.2f} of a ${sp['cap']:.0f} cap." if sp.get("total") is not None and sp.get("cap") is not None else ""
    return f"""<h4 id="verify">Generalisation checks: four ways the result could have failed</h4>
<p>Four checks on the claim <em>on the matters tested, knowing the case {_effect2(summary)['claim_verb'] if _effect2(summary) else 'did not detectably change review accuracy'}</em>, each chosen so that it could have undermined it; each is read
in claim language and Jev is a system under test throughout. Full tables and figures in the <a href="{v["href"]}">verification report</a>.{spend}</p>
<ul>
<li><b>A · Knowledge-dependence (Enron J).</b> {v["a_line"]}</li>
<li><b>B · Ranking stability.</b> {v["b_line"]}</li>
<li><b>C · Counterfactual conflicts.</b> {v["c_line"]}</li>
<li><b>D · Knowledge injection on Veridian.</b> {v["d_line"]}</li>
</ul>
{v["d_fig"]}
{v["d_tbl"]}
<p class="fignote">Check D: the without-brief side is the round-1 named run restricted to the same {v["n_subset"]} documents; cluster bootstrap over documents; McNemar on label flips.</p>
<details><summary>Check A by system, and check C pooled over the four real matters</summary>{v["a_tbl"]}{v["c_tbl"]}</details>
<p><b>Reading.</b> {v["overall"]} Carry-forward wording: <em>{v["carry"]}</em></p>
"""


def _jev_native_section(summary: dict, heading: str = "21. Classifier-native tests: Jev through its own interface") -> str:
    """The tests that fit a classifier (results/jev_probe/summary.json), data-driven; a short pointer if they have not run."""
    n = _native(summary)
    if not n:
        return (f'<h3 id="jevnative">{heading}</h3><p>The classifier-native tests (results/jev_probe/) have not been run yet; when they have, their results are reported here.</p>')
    llm_names = ", ".join(MODEL_META[m.split("@")[0]][0] for m in n["llms"])
    spend = (f' Spend: OpenAI ${n["cost_openai"]:.2f}, Jev ${n["cost_jev"]:.2f}.' if n["cost_openai"] is not None and n["cost_jev"] is not None else "")
    one_liners = "".join(f"<li><b>{t}</b> {x}</li>" for t, x in (("Bare token (FAS 140).", n["bare_txt"]), ("T2 · minimal-edit label flip.", n["t2_txt"]),
                                                               ("T3 · paraphrase sensitivity (Jev only; it returns a probability).", n["t3_txt"]),
                                                               ("T4 · published vs unpublished labels.", n["t4_txt"])) if x)
    return f"""<h3 id="jevnative">{heading}</h3>
<p>Every probe above except M3 is a generative question, and the ablation (§20) removed one channel — proper names in full documents. These tests use only what a classifier
offers: a relevance call and its probability. Each is a paired design with bootstrap intervals; the GPT-5.6 models ({llm_names}) are the <em>positive</em> comparison (systems
known to carry matter knowledge) and Veridian the synthetic floor, so no system here is a clean reference. Jev is a system under test throughout, and every result is stated as
evidence consistent or inconsistent with its vendor's statement that it is trained on synthetic data — never as proof. Method, per-token tables and the full T4 breakdown are in
the <a href="{n["href"]}">classifier-native report</a>.{spend}</p>
<p><b>T1 · code-name swap.</b> The same templated document twice, differing in one token: a real matter token (an Enron vehicle, a Florida controversy, an opioid brand or
subsidiary) or a fictional token of the same shape; the request describes the conduct without naming the token. On <em>signal</em> pairs a case-aware reader calls the real
version relevant more often; on <em>decoy</em> pairs the real token is something a case-aware reader knows is <em>not</em> what the request asks for (Azurix, FCAT, Ofirmev,
Lidoderm…), so knowledge should lower the call. A system with no case knowledge gives the same call either way. {n["t1_result"]}</p>
{n["t1_tbl"]}
<p class="fignote">Δ = relevant-call rate on the real-token version minus the fictional-token version, percentage points, paired bootstrap 95% interval over pairs; n = signal + decoy pairs
per matter. The LLM columns are the same documents through the study's relevance prompt. The last column subtracts Jev's decoy Δ from its signal Δ: knowledge of what the names mean,
net of any 'real-looking name' effect.</p>
<ul>{one_liners}</ul>
{n["reading"]}
"""


def _examples(models) -> str:
    probes = OUT_DIR / "probes.jsonl"
    if not probes.exists():
        return "<p>(probe items not available)</p>"
    items = {json.loads(l)["item_id"]: json.loads(l) for l in probes.open()}
    m = "gpt-5.6-sol" if "gpt-5.6-sol" in models else models[-1]
    res = load_results(m)
    si = RESULTS_DIR / "scored_items.jsonl"
    best: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for line in si.open():
        r = json.loads(line)
        if r["probe"] == "verbatim" and r["model"] == m and r["max_run"] >= 8 and r["corpus"] != "jebbush":
            best[r["corpus"]].append((r["max_run"], r["item_id"]))
    out = []
    for c in SPECTRUM:
        if c not in best:
            continue
        for run, iid in sorted(best[c], reverse=True)[:2]:
            it = items.get(iid)
            if not it or iid not in res:
                continue
            pre = it["gold"]["prefix"][-260:]
            tgt = it["gold"]["target"][:320]
            gen = (res[iid].get("response") or "")[:320]
            out.append(
                f'<details><summary>{_esc(CORPUS_SHORT[c])} — <code>{_esc(it["meta"]["doc_id"])}</code> — longest exact run {run} words ({_esc(MODEL_META[m][0])})</summary>'
                f'<div class="ex"><div><b>end of prompt</b><pre>…{_esc(pre)}</pre></div><div><b>true continuation</b><pre>{_esc(tgt)}</pre></div><div><b>model wrote</b><pre>{_esc(gen)}</pre></div></div></details>'
            )
    return "".join(out) or "<p>(none)</p>"


def _bench_answers(BK, models, bq) -> str:
    out = []
    for m in models:
        for q, title in bq:
            x = BK.get(m, {}).get(q)
            if not x:
                continue
            rec = f' — recovered {len(x["recovered"])}/{x["n_keys"]}' if x.get("recovered") is not None and x.get("n_keys") else ""
            out.append(f'<details><summary>{_esc(MODEL_META[m][0])} — {title}{rec}</summary><pre class="ans">{_esc((x.get("response") or "").strip()[:2500])}</pre></details>')
    return "".join(out)


CSS = """
:root{--bg:#f3f2ee;--panel:#fafaf7;--ink:#1b1c1a;--ink-2:#4b4d49;--ink-3:#7c7e79;--ink-4:#a7a9a3;--line:#dfdfd8;--line-2:#c9cac2;--floor:#3f9a4f;--ceiling:#c9743a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
main{max-width:1180px;margin:0 auto;padding:36px 28px 80px}
header h1{font-size:24px;font-weight:600;letter-spacing:-0.01em;margin:0 0 8px}
header .sub{color:var(--ink-2);max-width:900px;margin:0 0 14px}
nav{display:flex;flex-wrap:wrap;gap:4px 14px;font-size:12px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:8px 0;margin-bottom:28px}
nav a{color:var(--ink-3);text-decoration:none}
nav a:hover{color:var(--ink)}
h2{font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);font-weight:600;margin:44px 0 8px;border-bottom:1px solid var(--line-2);padding-bottom:6px}
h3{font-size:18px;font-weight:600;margin:30px 0 8px;letter-spacing:-0.01em}
h4{font-size:14px;font-weight:600;margin:18px 0 4px}
p,li{color:var(--ink-2);max-width:900px}
p b,li b{color:var(--ink)}
code{font-size:12.5px;background:var(--panel);border:1px solid var(--line);border-radius:3px;padding:0 4px}
table.tbl{border-collapse:collapse;width:100%;font-size:12.5px;margin:12px 0 6px;background:var(--panel);border:1px solid var(--line);font-variant-numeric:tabular-nums}
table.tbl th,table.tbl td{padding:7px 10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
table.tbl thead th{font-weight:500;color:var(--ink-3);font-size:11.5px;background:var(--bg)}
table.tbl tbody th{font-weight:500;white-space:nowrap}
table.tbl td small{color:var(--ink-3);font-size:11px}
table.cmx{width:auto}table.cmx td.cmx-c{text-align:center;font-variant-numeric:tabular-nums;min-width:52px;padding:7px 6px;font-size:14px}
table.cmx td.cmx-all{font-weight:600;border-right:2px solid #fff}table.cmx th.cmx-g{text-align:center;border-left:2px solid #fff}
table.cmx th.cmx-s{text-align:center;font-size:10.5px;letter-spacing:.04em;text-transform:uppercase;padding:3px 4px}table.cmx th.cmx-all{font-weight:600;color:var(--ink)}
table.cmx td.cmx-jev{background:repeating-linear-gradient(135deg,#f1f1ec 0 4px,#fafaf7 4px 8px);color:var(--ink-3)}table.cmx th.cmx-jevh{color:var(--ink-3)}
table.cmx tbody th .role{margin-left:6px}
table.tbl sup{color:var(--ink-3);font-size:9px}
table.tbl.kv tbody th{width:140px;color:var(--ink-3);font-weight:500}
table.tbl.kv thead{display:none}
.m{display:inline-block;padding-left:12px;position:relative;white-space:nowrap}
.m::before{content:"";position:absolute;left:0;top:5px;width:8px;height:8px;border-radius:2px;background:var(--c)}
.role{display:inline-block;font-size:9px;letter-spacing:.06em;text-transform:uppercase;border:1px solid;border-radius:3px;padding:0 4px;vertical-align:1px;margin-left:4px}
.role.floor{color:var(--floor);border-color:var(--floor)}
.role.ceiling{color:var(--ceiling);border-color:var(--ceiling)}
.role.post-cutoff{color:#7a4fa3;border-color:#7a4fa3}
.role.public-invented{color:#2a8a8a;border-color:#2a8a8a}
.legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--ink-2);margin:10px 0 6px}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px}
.legend small{color:var(--ink-4)}
.legend.small{font-size:11px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px 24px;margin:10px 0 14px}
@media(max-width:900px){.grid2{grid-template-columns:1fr}}
svg.fig{display:block;max-width:100%;height:auto;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:6px}
svg.fig text{font-family:inherit}
.panels{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-start}
.panels svg.fig{border:0;background:transparent;padding:0}
.panels{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:10px}
figure{margin:0}
.figtitle{font-size:12.5px;font-weight:600;margin:14px 0 6px;line-height:1.35}
h2.sub2{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--ink-3);border-bottom:1px solid var(--line);padding-bottom:6px;margin:26px 0 8px}
.navpart{display:block;width:100%;font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);margin:6px 0 2px}
.tag{display:inline-block;font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;color:#c9743a;border:1px solid #e3b48f;border-radius:3px;padding:0 4px;margin-left:4px;vertical-align:middle}
.dim{color:var(--ink-4)}
small.q{color:var(--ink-3);font-style:italic}
.tbl.terms td{vertical-align:top;font-size:12px}
.fignote{font-size:11.5px;color:var(--ink-3);margin:6px 0 0}
details{border:1px solid var(--line);border-radius:6px;background:var(--panel);margin:8px 0;padding:6px 12px;font-size:12.5px}
summary{cursor:pointer;color:var(--ink-2)}
.ex{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin:8px 0 4px}
@media(max-width:900px){.ex{grid-template-columns:1fr}}
.ex b{font-size:11px;color:var(--ink-3);text-transform:uppercase;letter-spacing:.05em}
pre{white-space:pre-wrap;word-break:break-word;font:11.5px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--bg);border:1px solid var(--line);border-radius:4px;padding:8px;margin:4px 0 0;color:var(--ink-2)}
pre.ans{max-height:360px;overflow:auto}
"""
