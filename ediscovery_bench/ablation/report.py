"""Self-contained HTML report for the pseudonymisation ablation: results/ablation/ablation_report.html.

Reuses the SVG primitives and stylesheet from contam.html (import only)."""
from __future__ import annotations

import json
import math
from pathlib import Path

from ..contam.html import CSS, INK, INK3, INK4, LINE, MODEL_META, PANEL, _esc, _svg, dotplot, table
from .run import ALL_MODELS, JEV, RESULTS
from .score import ARM_LABEL, COND_LABEL, CONTROL_TOPIC

MODEL_META.setdefault(JEV, ("Jev (TypeSafe)", "classifier", "#3f9a4f"))
ARM_SHORT = {"enron_j": "Enron J", "enron_k": "Enron K (control)", "veridian": "Veridian (fictional)", "mnk": "Mallinckrodt ± brief"}
ARM_ROLE = {"veridian": "floor"}
TOPIC_LABEL = {"prepay_transactions": "201 Prepay transactions", "fas140": "202 FAS 140 transactions", "financial_forecasts": "203 Financial forecasts",
               "document_destruction": "204 Document destruction", "energy_schedules": "205 Energy schedules", "financial_analysts": "206 Analyst contacts",
               "fantasy_football": "207 Fantasy football (in-mailbox control)", "oil_gas_drilling": "301 Oil & gas drilling", "spill_response": "302 Spill response",
               "lobbying": "303 Lobbying", "all": "all requests"}


def _pp(v, nd=1):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    r = round(100 * v, nd)
    r = 0.0 if r == 0 else r
    return f"{r:+.{nd}f}"


def _ci(d: dict | None, k="f1"):
    if not d or not d.get(k) or d[k].get("delta") is None:
        return "–"
    x = d[k]
    return f"{_pp(x['delta'])} <small>[{_pp(x['lo'])}, {_pp(x['hi'])}]</small>"


def _f(v, nd=3):
    return "–" if v is None or (isinstance(v, float) and math.isnan(v)) else f"{v:.{nd}f}"


def _sig(d: dict | None, k="f1") -> str:
    """'' if the CI covers zero."""
    if not d or not d.get(k) or d[k].get("lo") is None:
        return ""
    return "<sup>†</sup>" if (d[k]["lo"] > 0 or d[k]["hi"] < 0) else ""


# ------------------------------------------------------------------------------------------------ figures

def deltaplot(rows, models, title, labels, roles=None, note=None, width=700, label_w=230, xmin=-0.12, xmax=0.08, pending=None, step=2):
    """rows: [(key, {model: (delta, lo, hi)})] in percentage points of F1 / recall / precision. Dashed zero line."""
    ticks = [t / 100 for t in range(int(round(xmin * 100)), int(round(xmax * 100)) + 1, step)]
    fig = dotplot(rows, models, xmin, xmax, ticks, lambda t: f"{100*t:+.0f}", title, ref=0.0, width=width, label_w=label_w, row_h=12 * len(models) + 14,
                  note=note, labels=labels, roles=roles or {})
    if pending:
        fig = fig.replace("</figure>", f'<p class="fignote pending">{_esc(pending)}</p></figure>')
    return fig


def flipbars(summary, models, arm, title, width=700, label_w=170):
    """Stacked horizontal bars per model: right→wrong (positives lost | false positives added) and wrong→right."""
    pm = summary["arms"][arm]["per_model"]
    row_h, pad_t, pad_b, pad_r = 30, 10, 26, 16
    h = pad_t + row_h * len(models) + pad_b
    mx = max([pm[m]["flips"]["right_to_wrong"] + pm[m]["flips"]["wrong_to_right"] for m in models if pm.get(m, {}).get("status") == "ok"] + [1])
    plot_w = width - label_w - pad_r
    sc = plot_w / (mx * 1.1)
    out = []
    for i, m in enumerate(models):
        cy = pad_t + row_h * i + row_h / 2
        out.append(f'<text x="{label_w - 10}" y="{cy + 4:.1f}" font-size="11.5" text-anchor="end" fill="{INK}">{_esc(MODEL_META[m][0])}</text>')
        r = pm.get(m, {})
        if r.get("status") != "ok":
            out.append(f'<text x="{label_w + 4}" y="{cy + 4:.1f}" font-size="11" fill="{INK4}">{_esc(summary["jev_status"] if m == JEV else "no data")}</text>')
            continue
        fl = r["flips"]
        x0 = label_w
        for val, col, lab in ((fl["positives_lost"], "#c0392b", "responsive → missed (recall lost)"), (fl["false_pos_added"], "#e8a07a", "non-responsive → flagged (precision lost)"),
                              (fl["wrong_to_right"], "#8ec1e6", "wrong → right")):
            w = val * sc
            if val:
                out.append(f'<rect x="{x0:.1f}" y="{cy - 9:.1f}" width="{w:.1f}" height="18" fill="{col}"><title>{lab}: {val}</title></rect>')
                if w > 18:
                    out.append(f'<text x="{x0 + w / 2:.1f}" y="{cy + 4:.1f}" font-size="10.5" text-anchor="middle" fill="#fff">{val}</text>')
            x0 += w
        out.append(f'<text x="{x0 + 6:.1f}" y="{cy + 4:.1f}" font-size="10.5" fill="{INK3}">of {r["n_pairs"]}</text>')
    key = ('<div class="legend small"><span><i style="background:#c0392b"></i>responsive → missed (recall lost)</span>'
           '<span><i style="background:#e8a07a"></i>non-responsive → flagged (precision lost)</span><span><i style="background:#8ec1e6"></i>wrong → right</span></div>')
    return f'<figure><div class="figtitle">{_esc(title)}</div>{_svg(width, h, "".join(out))}{key}</figure>'


def doseplot(summary, models, arm, title, width=700):
    rows = []
    for band in ("0", "1-2", "3+"):
        vals = {}
        for m in models:
            r = summary["arms"][arm]["per_model"].get(m, {})
            d = r.get("dose", {}).get(band)
            if d:
                vals[m] = (d["delta"]["f1"]["delta"], d["delta"]["f1"]["lo"], d["delta"]["f1"]["hi"])
        n = next((summary["arms"][arm]["per_model"][m]["dose"][band]["n"] for m in models if band in summary["arms"][arm]["per_model"].get(m, {}).get("dose", {})), 0)
        rows.append((band, vals))
    labels = {}
    for band, _ in rows:
        n = next((summary["arms"][arm]["per_model"][m]["dose"][band]["n"] for m in models if band in summary["arms"][arm]["per_model"].get(m, {}).get("dose", {})), 0)
        labels[band] = f"{band} knowledge-bearing names (n={n})"
    return deltaplot(rows, models, title, labels, note="ΔF1 (renamed − named) in percentage points, by how many curated knowledge-bearing names (people, SPEs, code names, auditors, banks' counterparties) the original document contained. Whiskers: 95% bootstrap CI by document.",
                     xmin=-0.15, xmax=0.1, label_w=250, step=5)


# ------------------------------------------------------------------------------------------------ report

def build_report(summary: dict, out_path: Path = RESULTS / "ablation_report.html") -> Path:
    models = [m for m in ALL_MODELS if m in summary["models"] or m == JEV]
    llms = summary["llm_models"]
    jev_ok = summary["jev_present"]
    pend = None if jev_ok else f"Jev: {summary['jev_status']}"
    arms = list(summary["arms"])
    A = summary["arms"]

    def ok(arm, m):
        return A[arm]["per_model"].get(m, {}).get("status") == "ok"

    # --- headline: ΔF1 per arm per model
    rows_f1 = [(arm, {m: tuple(A[arm]["per_model"][m]["delta"]["f1"][k] for k in ("delta", "lo", "hi")) for m in models if ok(arm, m)}) for arm in arms]
    rows_r = [(arm, {m: tuple(A[arm]["per_model"][m]["delta"]["recall"][k] for k in ("delta", "lo", "hi")) for m in models if ok(arm, m)}) for arm in arms]
    rows_p = [(arm, {m: tuple(A[arm]["per_model"][m]["delta"]["precision"][k] for k in ("delta", "lo", "hi")) for m in models if ok(arm, m)}) for arm in arms]

    # --- knowledge-effect contrasts (identical for all four systems)
    contrast_rows = []
    for m in models:
        c = summary["contrasts"].get(m, {})
        pj, pk, pv = (A[a]["per_model"].get(m, {}) for a in ("enron_j", "enron_k", "veridian"))
        name = f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>'
        if pj.get("status") != "ok":
            contrast_rows.append([name, f'<span class="dim">{_esc(summary["jev_status"] if m == JEV else "no data")}</span>', "", "", "", ""])
            continue
        contrast_rows.append([name, _ci(pj.get("delta")) + _sig(pj.get("delta")), _ci(pk.get("delta")) + _sig(pk.get("delta")), _ci(pv.get("delta")) + _sig(pv.get("delta")),
                              _ci(c.get("j_minus_k")) + _sig(c.get("j_minus_k")), _ci(c.get("j_minus_veridian")) + _sig(c.get("j_minus_veridian"))])

    # --- main table per arm × model × condition
    main_rows = []
    for arm in arms:
        for m in models:
            r = A[arm]["per_model"].get(m, {})
            name = f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>'
            if r.get("status") != "ok":
                main_rows.append([_esc(ARM_SHORT[arm]), name, "–", f'<span class="dim">{_esc(summary["jev_status"] if m == JEV else "no data")}</span>', "", "", "", "", "", "", "", ""])
                continue
            n_, rn = r["named"], r["renamed"]
            main_rows.append([_esc(ARM_SHORT[arm]), name, f"{r['n_pairs']}<br><small>{r['n_docs']} docs</small>",
                              f"{_f(n_['precision'])} / {_f(n_['recall'])} / <b>{_f(n_['f1'])}</b>", f"{_f(rn['precision'])} / {_f(rn['recall'])} / <b>{_f(rn['f1'])}</b>",
                              _ci(r["delta"], "precision"), _ci(r["delta"], "recall"), _ci(r["delta"]) + _sig(r["delta"]),
                              f"{r['flips']['right_to_wrong']} ↓ / {r['flips']['wrong_to_right']} ↑", f"{r['mcnemar']['p']:.3g}", f"{100*r['label_changed_share']:.1f}%",
                              f"${r['cost_usd']['named'] + r['cost_usd']['renamed']:.2f}"])
    main_tbl = table(["arm", "model", "pairs", "P / R / F1 — A", "P / R / F1 — B", "ΔP (pp)", "ΔR (pp)", "ΔF1 (pp) [95% CI]", "right→wrong / wrong→right", "McNemar p", "labels changed", "paid"], main_rows, cls="tbl main")

    # --- per-topic tables (Enron arms)
    topic_html = ""
    for arm in ("enron_j", "enron_k"):
        trs = []
        topics = sorted({t for m in models if ok(arm, m) for t in A[arm]["per_model"][m]["topics"]}, key=lambda t: TOPIC_LABEL.get(t, t))
        for t in topics:
            for m in models:
                if not ok(arm, m) or t not in A[arm]["per_model"][m]["topics"]:
                    continue
                r = A[arm]["per_model"][m]["topics"][t]
                trs.append([_esc(TOPIC_LABEL.get(t, t)), f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>', r["named"]["n"],
                            f"{_f(r['named']['precision'])} / {_f(r['named']['recall'])} / <b>{_f(r['named']['f1'])}</b>", f"{_f(r['renamed']['precision'])} / {_f(r['renamed']['recall'])} / <b>{_f(r['renamed']['f1'])}</b>",
                            _ci(r["delta"], "recall"), _ci(r["delta"], "precision"), _ci(r["delta"]) + _sig(r["delta"]), f"{r['flips']['right_to_wrong']} ↓ / {r['flips']['wrong_to_right']} ↑", f"{r['mcnemar']['p']:.3g}"])
        topic_rows = []
        for t in topics:
            vals = {m: tuple(A[arm]["per_model"][m]["topics"][t]["delta"]["f1"][k] for k in ("delta", "lo", "hi")) for m in models if ok(arm, m) and t in A[arm]["per_model"][m]["topics"]}
            topic_rows.append((t, vals))
        topic_html += f"<h4>{_esc(ARM_LABEL[arm])}</h4>" + deltaplot(topic_rows, models, f"ΔF1 by request — {ARM_SHORT[arm]}", TOPIC_LABEL, xmin=-0.3, xmax=0.2, label_w=270, pending=pend, step=5) + \
            table(["request", "model", "n", "P / R / F1 — named", "P / R / F1 — renamed", "ΔR", "ΔP", "ΔF1 [95% CI]", "flips", "McNemar p"], trs)

    # --- leak
    leak = summary.get("leak", {})
    leak_rows = []
    for m, v in leak.items():
        leak_rows.append([f'<span class="m" style="--c:{MODEL_META.get(m, ("", "", "#999"))[2]}">{_esc(MODEL_META.get(m, (m,))[0])}</span>', f"{v['named_enron']} / {v['n']}", f"{100*v['named_enron']/max(1,v['n']):.0f}%",
                          " · ".join(f"{b}: {d['named_enron']}/{d['n']}" for b, d in v["by_dose"].items()), f"{v['cannot_tell']}",
                          "; ".join(f"{g} ({n})" for g, n in v["top_guesses"][:4])])
    leak_ex = ""
    for m, v in leak.items():
        for ex in v.get("examples_enron", [])[:2]:
            leak_ex += f"<div><b>{_esc(MODEL_META.get(m, (m,))[0])}</b><pre>{_esc(ex)}</pre></div>"
    leak1 = summary.get("leak_v1", {})
    leak1_rows = [[f'<span class="m" style="--c:{MODEL_META.get(m, ("", "", "#999"))[2]}">{_esc(MODEL_META.get(m, (m,))[0])}</span>', f"{v['named_enron']} / {v['n']}", f"{100*v['named_enron']/max(1,v['n']):.0f}%",
                   " · ".join(f"{b}: {d['named_enron']}/{d['n']}" for b, d in v["by_dose"].items())] for m, v in leak1.items()]
    leak1_html = ""
    if leak1_rows:
        leak1_html = ("<h4>First pass: names renamed, production metadata left in</h4>"
                      "<p>The first renaming pass left the EDRM production headers (<code>X-SDOC</code>, <code>X-ZLID: zl-edrm-enron-v2-…</code>) and the ticker <code>ENE</code> in place. "
                      "The models named Enron from those alone, and from the Exchange address format, so the headers were removed from both conditions and the ticker mapped before any scoring run.</p>"
                      + table(["model", "named Enron", "share", "by dose (0 · 1–2 · 3+)"], leak1_rows))

    # --- control topic
    ctrl_rows = []
    for m in models:
        t = (summary.get("control_topic") or {}).get(m)
        if t:
            ctrl_rows.append([f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>', t["named"]["n"], _f(t["named"]["f1"]), _f(t["renamed"]["f1"]), _ci(t["delta"]) + _sig(t["delta"]), f"{t['mcnemar']['p']:.3g}"])

    # --- MNK brief
    mnk_rows = []
    for m in models:
        r = A["mnk"]["per_model"].get(m, {})
        if r.get("status") == "ok":
            mnk_rows.append([f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>', r["n_pairs"], f"{_f(r['named']['precision'])} / {_f(r['named']['recall'])} / <b>{_f(r['named']['f1'])}</b>",
                             f"{_f(r['renamed']['precision'])} / {_f(r['renamed']['recall'])} / <b>{_f(r['renamed']['f1'])}</b>", _ci(r["delta"], "recall"), _ci(r["delta"], "precision"), _ci(r["delta"]) + _sig(r["delta"]), f"{r['mcnemar']['p']:.3g}"])
        elif m == JEV:
            mnk_rows.append([f'<span class="m" style="--c:{MODEL_META[m][2]}">{_esc(MODEL_META[m][0])}</span>', "–", f'<span class="dim">{_esc(summary["jev_status"])}</span>', "", "", "", "", ""])

    cost_rows = [[_esc(MODEL_META.get(m, (m,))[0]), v["rows"], f"${v['paid_usd']:.2f}", f"${v['list_usd']:.2f}"] for m, v in summary["cost"].items()]
    ms = summary.get("mapping_stats", {})
    mz = summary.get("mapping_sizes", {})

    legend = '<div class="legend">' + "".join(f'<span><i style="background:{MODEL_META[m][2]}"></i>{_esc(MODEL_META[m][0])}</span>' for m in models) + "</div>"
    headline = _headline(summary, models)

    body = f"""
<header>
<h1>Does what the model already knows change its review decisions? A pseudonymisation ablation</h1>
<p class="sub">The same documents are reviewed twice by each model: once as they are (Enron named as Enron, real names of people, entities and
code names) and once with every knowledge-bearing name replaced by an invented one and the matter context changed to match. The documents, the
requests and the gold labels are otherwise identical, so any change in precision or recall is attributable to the names — either because the
system used what it knew about them (<em>knowledge</em>) or because renaming damaged the text (<em>text damage</em>). Two assumption-free baselines
separate the two: Complaint K requests on the same mailbox (knowledge-poor, same renaming dictionary) and the fictional Veridian corpus (renaming
cost only). Four systems are under test: GPT-5.6 Luna, Terra and Sol, and Jev. Jev's vendor states it is not pre-trained on these corpora; we treat
that as a claim and test it — if Jev's J − K effect is near zero the claim survives this test; if it is positive and comparable to the LLMs', it does not.</p>
{legend}
<nav><a href="#headline">Headline</a><a href="#design">Design</a><a href="#main">Main table</a><a href="#flips">Flips</a><a href="#topics">By request</a>
<a href="#dose">Dose–response</a><a href="#leak">Residual leakage</a><a href="#control">Control topic</a><a href="#mnk">Mallinckrodt ± brief</a><a href="#cost">Cost</a></nav>
</header>

<h2 id="headline">Headline</h2>
{headline}
<div class="grid2">
{deltaplot(rows_f1, models, "ΔF1 (renamed − named), pooled over knowledge requests", ARM_SHORT, roles=ARM_ROLE, pending=pend, note="Percentage points. For Mallinckrodt the pair is (no brief → with brief), so a positive Δ means the brief helped. Whiskers: 95% bootstrap CI clustered by document. All four systems are analysed identically.")}
{deltaplot(rows_r, models, "ΔRecall (renamed − named)", ARM_SHORT, roles=ARM_ROLE, pending=pend)}
{deltaplot(rows_p, models, "ΔPrecision (renamed − named)", ARM_SHORT, roles=ARM_ROLE, pending=pend)}
</div>

<h3>Knowledge effect</h3>
<p>Isolating knowledge from text damage without assuming anything about any system. <b>J − K</b>: both arms are Enron mailboxes renamed with the
same dictionary, but Complaint K's requests (oil and gas drilling, spill response, lobbying) are about subject matter the public Enron story says
little about, so K's Δ is mostly renaming cost. <b>J − Veridian</b>: Veridian is fictional, so its Δ is renaming cost on a corpus nobody can know.
A negative knowledge effect means the system lost more on the knowledge-rich requests than on the baseline when the names were removed.
The same contrasts are computed for Jev; they are the direct test of the vendor's no-pre-training claim.</p>
{table(["system", "ΔF1 Enron J", "ΔF1 Enron K", "ΔF1 Veridian", "knowledge effect J − K", "J − Veridian"], contrast_rows)}
<p class="fignote">† marks a 95% CI that excludes zero. Contrasts are differences of independent bootstrap distributions.</p>

<h2 id="design">Design</h2>
<table class="tbl kv"><tbody>
<tr><th>Samples</th><td>Enron J: {ms.get('enron_j',{}).get('docs','–')} e-mails from the TREC Legal 2010 learning collection, stratified by request (201–207) and label, one judged request per document.
Enron K: {ms.get('enron_k',{}).get('docs','–')} e-mails from the TREC Legal 2010 interactive collection (301–303). Veridian: {ms.get('veridian',{}).get('docs','–')} documents, all ten requests. Mallinckrodt: all 1,840 documents, eight requests.
Documents under 200 or over 12,000 characters excluded.</td></tr>
<tr><th>Renaming</th><td>Deterministic dictionary substitution (no LLM in the loop): {mz.get('enron_phrases','–')} curated Enron phrases (company, subsidiaries, SPEs, code names, auditor, law firm, counterparties) and
{mz.get('enron_people','–')} surnames ({len(json.loads((Path(__file__).resolve().parents[2]/'data'/'ablation'/'mapping.json').read_text())['enron']['people']) if (Path(__file__).resolve().parents[2]/'data'/'ablation'/'mapping.json').exists() else '–'} incl. every surname seen in a header field), case-shape preserving, applied in e-mail addresses, Lotus Notes paths and routing tokens too.
Veridian: {mz.get('veridian_phrases','–')} phrases and {mz.get('veridian_people','–')} surnames. Tokens changed: Enron J {ms.get('enron_j',{}).get('changed_tokens','–'):,}, Enron K {ms.get('enron_k',{}).get('changed_tokens','–'):,}, Veridian {ms.get('veridian',{}).get('changed_tokens','–'):,}. Residual "Enron" strings: {ms.get('enron_j',{}).get('residual_enron_mentions','–')}.</td></tr>
<tr><th>Conditions</th><td><b>Named</b>: original text; Enron context ends "The Company is Enron Corp." <b>Renamed</b>: substituted text; context ends "The Company is Volteron Corp." (Veridian: context and requests pass through the same renamer.)
<b>Mallinckrodt</b>: original text both times; the treated condition appends a one-page neutral case brief (parties, MDL 2804, SOM, chargeback data, Exalgo, 2017 DEA settlement, 2020 Chapter 11) to the matter context.</td></tr>
<tr><th>Systems</th><td>{", ".join(MODEL_META[m][0] for m in models)}. OpenAI models at effort "none" on the flex tier; Jev 1.13.0 (Noul form, structured state with matter_context). One call per document carrying all requests for that arm.
Jev's vendor states it is not pre-trained on these corpora; we treat that as a claim and test it with the same contrasts as the LLMs.</td></tr>
<tr><th>Statistics</th><td>Paired on (document, request). Δ with 2,000-replicate bootstrap by document; exact McNemar on discordant pairs. Dose = number of curated knowledge-bearing substitutions in the original (company name and unit abbreviations excluded).</td></tr>
</tbody></table>

<h2 id="main">Main table</h2>
<p>Condition A is the named / no-brief condition; B is renamed / with-brief. "Labels changed" is the share of (document, request) pairs whose label differed between conditions regardless of correctness.</p>
{main_tbl}

<h2 id="flips">Where the changes land</h2>
<div class="grid2">
{"".join(flipbars(summary, models, arm, f"{ARM_SHORT[arm]}: pairs that changed correctness") for arm in arms)}
</div>

<h2 id="topics">By request</h2>
<p>Pooled effects hide request-level ones. The list below names every (system, request) pair whose ΔF1 CI excludes zero; the tables and plots follow.</p>
{_notable(summary, models)}
{topic_html}

<h2 id="dose">Dose–response</h2>
<p>If knowledge is doing the work, documents dense with recognisable names should lose more when renamed than documents with none. If renaming
itself does the damage, the pattern should be the same for Jev.</p>
{doseplot(summary, models, "enron_j", "Enron J — ΔF1 by knowledge-bearing names per document")}
{doseplot(summary, models, "enron_k", "Enron K (control) — ΔF1 by knowledge-bearing names per document")}

<h2 id="leak">Residual leakage: can Enron be pseudonymised at all?</h2>
<p>Renaming only matters if it works. Each LLM was shown {next((v['n'] for v in leak.values()), 0)} renamed Enron J documents (half drawn from the highest-dose band) and asked which real company they come from.
The share that still says "Enron" bounds what the ablation can measure: where the model recognises the matter anyway, renaming removes the names but not the knowledge, and the Δ below is a lower bound on the knowledge effect.
Jev is not in this table: it returns a probability for a stated criterion, not free text, so the identification question cannot be posed to it. Its exposure is tested instead through its own J − K and Veridian contrasts above.</p>
{table(["model", "named Enron", "share", "by dose (0 · 1–2 · 3+)", "'cannot tell'", "top first answers"], leak_rows) if leak_rows else '<p class="dim">leak check not run</p>'}
<details><summary>Example attributions (final renaming)</summary><div class="ex">{leak_ex}</div></details>
{leak1_html}

<h2 id="control">In-mailbox control request</h2>
<p>Request 207 (fantasy football) comes from the same mailboxes and is renamed by the same dictionary, but knowledge of the Enron story cannot help with it. A Δ here, for any system, is renaming cost.</p>
{table(["model", "n", "F1 named", "F1 renamed", "ΔF1 [95% CI]", "McNemar p"], ctrl_rows) if ctrl_rows else '<p class="dim">no rows</p>'}

<h2 id="mnk">Mallinckrodt: adding knowledge instead of removing it</h2>
<p>The mirror experiment. The documents are unchanged; the treated condition gives the system the public story of the litigation in a one-page brief. If what a system already knows helps its decisions, the brief should help most the systems that know least. Jev's gain here is a second, independent read on how much of the public story it already carries.</p>
{table(["model", "pairs", "P / R / F1 — no brief", "P / R / F1 — with brief", "ΔR", "ΔP", "ΔF1 [95% CI]", "McNemar p"], mnk_rows)}

<h2 id="cost">Cost</h2>
{table(["model", "rows", "paid", "list"], cost_rows)}
<p>Total ${summary['total_paid_usd']:.2f} paid (${summary['total_list_usd']:.2f} list).</p>
<p class="fignote">Generated by <code>bench ablation-report</code> from results/ablation/. Companion files: summary.json, REPORT.md, leak_check.jsonl.</p>
"""
    css = CSS + """
.pending{color:#c9743a}
table.tbl.main td{font-size:12px}
"""
    html = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Pseudonymisation ablation</title><style>{css}</style></head><body><main>{body}</main></body></html>'
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html)
    return out_path


def _notable(summary: dict, models: list[str]) -> str:
    items = []
    for arm in ("enron_j", "enron_k"):
        for m in models:
            r = summary["arms"][arm]["per_model"].get(m, {})
            if r.get("status") != "ok":
                continue
            for t, v in r["topics"].items():
                d = v["delta"]["f1"]
                if d["delta"] is None or d["lo"] is None or not (d["lo"] > 0 or d["hi"] < 0):
                    continue
                fl = v["flips"]
                items.append((arm, m, t, d, fl, v))
    if not items:
        return '<p class="dim">No request-level ΔF1 with a CI excluding zero.</p>'
    items.sort(key=lambda x: x[3]["delta"])
    li = []
    for arm, m, t, d, fl, v in items:
        li.append(f"<li><b>{_esc(MODEL_META[m][0])}</b>, {_esc(TOPIC_LABEL.get(t, t))} ({_esc(ARM_SHORT[arm])}): ΔF1 {_pp(d['delta'])} pp [{_pp(d['lo'])}, {_pp(d['hi'])}] — "
                  f"recall {_f(v['named']['recall'])} → {_f(v['renamed']['recall'])}, precision {_f(v['named']['precision'])} → {_f(v['renamed']['precision'])}; "
                  f"{fl['positives_lost']} responsive documents lost, {fl['false_pos_added']} false positives added, {fl['wrong_to_right']} corrected.</li>")
    return "<ul>" + "".join(li) + "</ul>"


def _headline(summary: dict, models: list[str]) -> str:
    A = summary["arms"]
    items = []
    for m in models:
        rj, rk, rv, rm = (A[a]["per_model"].get(m, {}) for a in ("enron_j", "enron_k", "veridian", "mnk"))
        name = MODEL_META[m][0]
        if rj.get("status") != "ok":
            items.append(f"<li><b>{_esc(name)}</b>: {_esc(summary['jev_status'] if m == JEV else 'no data')}.</li>")
            continue
        c = summary["contrasts"].get(m, {})
        parts = [f"Enron J F1 {_f(rj['named']['f1'])} → {_f(rj['renamed']['f1'])} (Δ {_pp(rj['delta']['f1']['delta'])} pp; recall {_pp(rj['delta']['recall']['delta'])}, precision {_pp(rj['delta']['precision']['delta'])})"]
        if rk.get("status") == "ok":
            parts.append(f"Enron K Δ {_pp(rk['delta']['f1']['delta'])}")
        if rv.get("status") == "ok":
            parts.append(f"Veridian Δ {_pp(rv['delta']['f1']['delta'])}")
        if c.get("j_minus_k") and c["j_minus_k"]["f1"]["delta"] is not None:
            parts.append(f"<b>knowledge effect J − K {_pp(c['j_minus_k']['f1']['delta'])} pp [{_pp(c['j_minus_k']['f1']['lo'])}, {_pp(c['j_minus_k']['f1']['hi'])}]</b>")
        if rm.get("status") == "ok":
            parts.append(f"Mallinckrodt brief Δ {_pp(rm['delta']['f1']['delta'])} pp")
        tail = ""
        if m == JEV and c.get("j_minus_k") and c["j_minus_k"]["f1"]["delta"] is not None:
            lo, hi = c["j_minus_k"]["f1"]["lo"], c["j_minus_k"]["f1"]["hi"]
            verdict = "the CI includes zero, so the vendor's no-pre-training claim survives this test" if lo <= 0 <= hi else \
                      ("the effect is negative and its CI excludes zero — not consistent with the claim" if hi < 0 else "the effect is positive and its CI excludes zero")
            tail = f" <i>Vendor claim under test: {verdict}.</i>"
        items.append(f"<li><b>{_esc(name)}</b>: " + "; ".join(parts) + "." + tail + "</li>")
    return "<ul>" + "".join(items) + "</ul>"
