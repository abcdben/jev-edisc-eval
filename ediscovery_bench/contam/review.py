"""Review interface for the verbatim (finish-the-document) probe: results/contam/verbatim_review.html.

One self-contained page. Every probed document is shown with the true continuation and each model's continuation side by side,
with the words they share highlighted; the list can be filtered by corpus and model, sorted by any score, and searched.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

from ..config import MODELS
from .boilerplate import REASON_LABEL
from .build import OUT_DIR
from .html import CORPUS_SHORT, MODEL_META, ROLE, TAG, role_text
from .run import MAX_TOKENS, RESULTS_DIR, load_results
from .score import TOK_RE, common_runs, score_verbatim
from .screen import CLASS_LABEL

MIN_RUN = 3  # shortest shared run worth highlighting


def _spans(text: str):
    low = text.lower()
    if len(low) != len(text):
        text = low
    return [(m.group(0), m.start(), m.end()) for m in TOK_RE.finditer(low)], text


def _mark(text: str, marks: dict[int, tuple[int, bool]]) -> str:
    """marks: token index -> (run length, novel). Wrap marked tokens in <mark> with a class for run length and novelty."""
    spans, text = _spans(text)
    out, pos = [], 0
    i = 0
    while i < len(spans):
        tok, s, e = spans[i]
        if i not in marks:
            i += 1
            continue
        L, novel = marks[i]
        j = i
        while j + 1 < len(spans) and (j + 1) in marks and marks[j + 1] == (L, novel):
            j += 1
        out.append(html.escape(text[pos:s]))
        cls = "r15" if L >= 15 else "r8" if L >= 8 else "r3"
        out.append(f'<mark class="{cls}{"" if novel else " copy"}" title="{L}-word run{"" if novel else " (also in the prompt)"}">{html.escape(text[s:spans[j][2]])}</mark>')
        pos = spans[j][2]
        i = j + 1
    out.append(html.escape(text[pos:]))
    return "".join(out)


def _split_long(prefix: str, max_words: int = 250, keep_words: int = 150) -> tuple[str, str]:
    """For a long opening, split off the early part so it can be collapsed; the last ~keep_words stay visible so the hand-off
    into the continuation is always on screen. Returns (early, visible) with early + visible == prefix. Prefer a line break."""
    low = prefix.lower()
    toks = list(TOK_RE.finditer(low))
    if len(toks) <= max_words or len(low) != len(prefix):
        return "", prefix
    pos = toks[-keep_words].start()
    nl = prefix.rfind("\n", 0, pos)
    cut = nl + 1 if nl >= 0 and pos - nl < 400 else pos
    return prefix[:cut], prefix[cut:]


def _align(prefix: str, target: str, resp: str):
    tgt = TOK_RE.findall(target.lower())
    gen_all = TOK_RE.findall(resp.lower())
    gen = gen_all[: len(tgt) + 5]
    pre = TOK_RE.findall(prefix.lower())
    pre5 = {tuple(pre[i:i + 5]) for i in range(len(pre) - 4)}
    mt: dict[int, tuple[int, bool]] = {}
    mg: dict[int, tuple[int, bool]] = {}
    for L, ia, ib in common_runs(gen, tgt):
        if L < MIN_RUN:
            continue
        seg = tgt[ib:ib + L]
        novel = L < 5 or any(tuple(seg[k:k + 5]) not in pre5 for k in range(L - 4))
        for k in range(L):
            if mg.get(ia + k, (0, False))[0] < L:
                mg[ia + k] = (L, novel)
            if mt.get(ib + k, (0, False))[0] < L:
                mt[ib + k] = (L, novel)
    return _mark(target, mt), _mark(resp, mg), len(gen_all)


POOL_FIELDS = ("v_pool", "v_exclude_reason", "v_screen_class", "v_screen_reason", "v_screen_exempt", "boilerplate", "boilerplate_reason", "boilerplate_reasons")
CLASS_SHORT = {"public_reproduction": "public text", "template_boilerplate": "template", "low_information": "low information"}


def _load_pool_flags(path: Path = RESULTS_DIR / "scored_items.jsonl") -> dict[str, dict]:
    """item_id -> pool-quality fields written by score.verbatim_pool (identical across models, so the first row per item wins)."""
    flags: dict[str, dict] = {}
    if not path.exists():
        return flags
    for line in path.open():
        if '"verbatim"' not in line:
            continue
        r = json.loads(line)
        if r.get("probe") == "verbatim" and r.get("v_pool") and r["item_id"] not in flags:
            flags[r["item_id"]] = {k: r.get(k) for k in POOL_FIELDS}
    return flags


def _pool_fields(f: dict | None) -> dict:
    """Card fields for the pool badge: pool, exempt, and for excluded windows a humanised short reason (why) and a full tooltip (tip)."""
    if not f:
        return {"pool": None}
    out: dict = {"pool": f["v_pool"], "exempt": bool(f.get("v_screen_exempt"))}
    if f["v_pool"] != "excluded":
        return out
    reason = f.get("v_exclude_reason") or ""
    screen = (f.get("v_screen_reason") or "").strip().rstrip(".")
    if reason.startswith("boilerplate:"):
        rules = f.get("boilerplate_reasons") or [reason.split(":", 1)[1]]
        why = f"boilerplate: {REASON_LABEL.get(rules[0], rules[0])}"
        tip = "Boilerplate rule(s): " + "; ".join(REASON_LABEL.get(x, x) for x in rules)
        if screen:
            tip += f". Screen: {CLASS_LABEL.get(f.get('v_screen_class'), f.get('v_screen_class'))} — {screen}"
    else:
        cls = CLASS_SHORT.get(reason, reason.replace("_", " "))
        short = re.sub(r"^(?:the\s+)?(?:continuation|window|prefix)\s+", "", screen, flags=re.I)  # "Continuation reproduces a…" -> "reproduces a…"
        why = f"{cls}: {short}" if short else cls
        tip = f"Screen: {CLASS_LABEL.get(reason, reason)}" + (f" — {screen}" if screen else "")
    out.update(why=html.escape(why), tip=html.escape(tip, quote=True))
    return out


CSS = """
:root{--ink:#1f2328;--ink2:#4b5563;--ink3:#7a8190;--line:#e3e6ea;--panel:#f6f7f8;--blue:#2f7fc1}
*{box-sizing:border-box}body{margin:0;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;color:var(--ink);background:#fff}
header{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--line);padding:12px 20px;z-index:5}
h1{font-size:18px;margin:0 0 6px}
.bar{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;font-size:13px}
.bar label{display:inline-flex;align-items:center;gap:4px}
.bar select,.bar input[type=search]{font:inherit;padding:3px 6px;border:1px solid var(--line);border-radius:4px}
.bar input[type=search]{width:220px}
.stats{color:var(--ink2);font-size:13px;margin-top:6px}
main{padding:14px 20px;max-width:1400px}
.card{border:1px solid var(--line);border-radius:6px;margin:0 0 14px;background:#fff}
.card .hd{display:flex;flex-wrap:wrap;gap:6px 14px;align-items:baseline;padding:8px 12px;background:var(--panel);border-bottom:1px solid var(--line);font-size:12.5px}
.card .hd b{font-size:13px}
.role{font-size:10px;letter-spacing:.08em;text-transform:uppercase;padding:1px 5px;border-radius:3px;background:#eef1f4;color:var(--ink3)}
.role.floor{background:#e3effa;color:#2a5f8f}.role.ceiling{background:#fbe9d9;color:#9a5a24}.role.public-invented{background:#dff2f2;color:#1f6b6b}
.pool{font-size:10px;letter-spacing:.06em;text-transform:uppercase;padding:1px 6px;border-radius:3px;white-space:nowrap;max-width:60ch;overflow:hidden;text-overflow:ellipsis;vertical-align:baseline}
.pool.kept{background:#dff3e4;color:#1d6b3a}
.pool.ex{background:#eceef1;color:#5b6472;text-transform:none;letter-spacing:0;font-size:11px}
.pool.ex b{text-transform:uppercase;letter-spacing:.06em;font-size:10px;font-weight:600}
.pool.exempt{background:none;color:#a7adb7;padding-left:0;text-transform:none;letter-spacing:0;font-size:11px}
.ref{font-size:10px;letter-spacing:.06em;text-transform:uppercase;padding:1px 6px;border-radius:3px;white-space:nowrap;background:#fdeccd;color:#8a5a12;font-weight:600}
.ref.empty{background:none;color:#a7adb7;font-weight:400;padding-left:0}
.note{font-size:12px;color:var(--ink3);margin-top:4px}.note a{color:var(--blue)}
.score{font-variant-numeric:tabular-nums}
.score.hi{color:#9a2d1f;font-weight:600}.score.mid{color:#9a5a24;font-weight:600}
.hd .rtoggle{margin-left:auto;font:inherit;font-size:12px;color:var(--blue);background:none;border:0;padding:0;cursor:pointer;text-decoration:underline}
.tag{display:inline-block;font-size:9.5px;letter-spacing:.08em;text-transform:uppercase;line-height:1.4;padding:1px 5px;border-radius:3px;vertical-align:1px;white-space:nowrap;user-select:none}
.tag.shown{background:#e4e7eb;color:#5b6472;margin-right:6px}
.tag.actual{background:#1f2328;color:#fff;margin:0 6px}
.tag.mdl{background:#2a5f8f;color:#fff;margin-right:6px}
.doc{padding:12px 14px 10px;font-size:13.5px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;border-left:4px solid #d4d8de}
.doc .pre{color:var(--ink2)}
.doc .early{display:none;color:var(--ink2)}.doc.open .early{display:inline}
.doc .act{color:var(--ink)}
.doc .toggle{font:inherit;font-size:12px;color:var(--blue);background:none;border:0;padding:0;cursor:pointer;text-decoration:underline;white-space:normal;margin-right:4px}
.gen{margin:0 14px 12px 14px;padding:8px 10px 8px 12px;border-left:4px solid var(--mc,#2f7fc1);background:#fafbfc;border-radius:0 4px 4px 0;font-size:13.5px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word}
.gen .n{color:var(--ink3);font-size:11.5px;margin-right:6px;white-space:nowrap}
.prompt{display:none;background:#f3f4f6;border-bottom:1px solid var(--line);padding:10px 12px;font-size:12.5px;color:var(--ink2)}
.prompt.open{display:block}
.prompt .lbl{display:block;font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--ink3);margin-bottom:4px}
.prompt .msg{margin-top:8px}
.prompt pre{margin:0;padding:8px 10px;background:#fff;border:1px solid var(--line);border-radius:4px;font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:var(--ink);white-space:pre-wrap;word-wrap:break-word}
mark{border-radius:2px;padding:0 1px}
mark.r3{background:#dbe9f7}mark.r8{background:#f7d9a8}mark.r15{background:#f2a29a}
mark.copy{background:#e6e6e6;text-decoration:underline dotted}
.legend{font-size:12px;color:var(--ink2);margin-top:6px}.legend mark{margin-right:8px}
.model{display:inline-block;width:9px;height:9px;border-radius:2px;vertical-align:middle;margin-right:4px}
.more{display:block;margin:10px auto 30px;padding:8px 18px;font:inherit;border:1px solid var(--line);border-radius:4px;background:var(--panel);cursor:pointer}
.empty{color:var(--ink3);padding:30px;text-align:center}
"""

JS = r"""
const D = window.__DATA__;
const models = D.models, meta = D.meta;
const $ = s => document.querySelector(s);
const PAGE = 40;
let shown = PAGE;
function rows() {
  const corp = [...document.querySelectorAll('.corp:checked')].map(x => x.value);
  const mod = $('#model').value;
  const sort = $('#sort').value;
  const q = $('#q').value.trim().toLowerCase();
  const minrun = +$('#minrun').value;
  const pool = $('#pool').value;
  const showRef = $('#refusals').checked;
  let out = [];
  for (const d of D.docs) {
    if (!corp.includes(d.corpus)) continue;
    if (pool !== 'all' && d.pool !== pool) continue;
    for (const m of models) {
      if (mod !== 'all' && mod !== m) continue;
      const r = d.r[m]; if (!r) continue;
      if (!showRef && r.refusal) continue;
      if (r.max_run < minrun) continue;
      if (q && !(d.doc_id.toLowerCase().includes(q) || d.target_txt.includes(q) || r.resp_txt.includes(q))) continue;
      out.push({d, m, r});
    }
  }
  const key = {lcs: x => x.r.lcs_f, run: x => x.r.max_run, novel: x => x.r.novel_run, corpus: x => D.corpusOrder.indexOf(x.d.corpus)};
  const dir = $('#dir').value === 'desc' ? -1 : 1;
  const k = key[sort];
  out.sort((a, b) => dir * (k(a) - k(b)) || a.d.doc_id.localeCompare(b.d.doc_id) || models.indexOf(a.m) - models.indexOf(b.m));
  return out;
}
function scoreCls(v, hi, mid) { return v >= hi ? 'score hi' : v >= mid ? 'score mid' : 'score'; }
// The exact request: D.prompt holds the (shared, HTML-escaped) system message and the instruction text around the opening;
// d.user/d.system are set only for a document whose stored messages could not be rebuilt from the opening shown above.
function userMsg(d) { return d.user !== undefined ? d.user : D.prompt.pre + d.early + d.pre + D.prompt.post; }
function systemMsg(d) { return d.system !== undefined ? d.system : D.prompt.system; }
function promptPanel(d, m, r) {
  const p = D.params[m];
  const temp = r.temp0 ? 'temperature 0' : 'temperature: vendor default (0 was rejected)';
  const effort = p.effort ? `reasoning.effort ${p.effort}` : 'no reasoning parameter';
  return `<div class="prompt"><span class="lbl">exact request sent to ${meta[m][0]} (${p.model_id}) — OpenAI Responses API · max_output_tokens ${D.prompt.max_tokens} · ${temp} · ${effort}</span>
    <div class="msg"><span class="lbl">system (instructions)</span><pre>${systemMsg(d)}</pre></div>
    <div class="msg"><span class="lbl">user (input)</span><pre>${userMsg(d)}</pre></div></div>`;
}
function card(x) {
  const {d, m, r} = x;
  const mm = meta[m];
  const role = D.role[d.corpus] ? `<span class="role ${D.role[d.corpus]}">${D.roleText[D.role[d.corpus]] || D.role[d.corpus]}</span>` : '';
  const pool = d.pool === 'kept' ? `<span class="pool kept" title="in the final verbatim pool: passed the boilerplate rules and the screen">in pool</span>${d.exempt ? '<span class="pool exempt" title="public text by design; exempt from the public-reproduction class">ceiling (exempt)</span>' : ''}`
    : d.pool === 'excluded' ? `<span class="pool ex" title="${d.tip}"><b>excluded</b> · ${d.why}</span>` : '';
  return `<div class="card">
    <div class="hd"><b>${D.corpusLabel[d.corpus]}</b>${role}${pool}<span><i class="model" style="background:${mm[2]}"></i>${mm[0]}</span>
      <span>LCS-F1 <span class="${scoreCls(r.lcs_f, .5, .3)}">${r.lcs_f.toFixed(2)}</span></span>
      <span>longest run <span class="${scoreCls(r.max_run, 15, 8)}">${r.max_run}</span> words</span>
      <span>novel run <span class="${scoreCls(r.novel_run, 15, 8)}">${r.novel_run}</span></span>
      ${r.refusal ? `<span class="ref" title="the model declined to continue the text (${r.refusal_kind}); refusals are excluded from the headline scores and reported as a rate">refused · ${r.refusal_kind}</span>` : r.refusal_kind === 'empty' ? '<span class="ref empty" title="the model returned no text; scored 0, not counted as a refusal">empty response</span>' : ''}
      <span style="color:#7a8190">${d.doc_id}</span><button class="rtoggle" type="button">show full request</button></div>
    ${promptPanel(d, m, r)}
    <div class="doc" style="--mc:${mm[2]}"><span class="tag shown" title="the opening sent to the model (${d.prefix_words} words)">shown to the model</span>${d.early ? `<button class="toggle" type="button" data-n="${d.early_words}">… show the ${d.early_words} earlier words</button><span class="early">${d.early}</span>` : ''}<span class="pre">${d.pre}</span><span class="tag actual" title="what the document actually says next (${d.n_target} words)">actual continuation</span><span class="act">${r.tgt}</span></div>
    <div class="gen" style="--mc:${mm[2]}"><span class="tag mdl">model wrote</span><span class="n">${r.gen_words} words</span>${r.resp}</div>
  </div>`;
}
function render(reset) {
  if (reset) shown = PAGE;
  const out = rows();
  const n = out.length;
  const ans = out.filter(x => !x.r.refusal), na = ans.length;  // headline statistics are over answered items, as in the report
  const mean = na ? ans.reduce((s, x) => s + x.r.lcs_f, 0) / na : 0;
  const ge8 = na ? ans.filter(x => x.r.max_run >= 8).length / na : 0;
  const ge15 = na ? ans.filter(x => x.r.max_run >= 15).length / na : 0;
  // pool counts are per document for the selected corpora (independent of the model / run / search filters), so they match summary.v_pool
  const corp = [...document.querySelectorAll('.corp:checked')].map(x => x.value);
  const pd = D.docs.filter(d => corp.includes(d.corpus));
  const kept = pd.filter(d => d.pool === 'kept').length, excl = pd.length - kept;
  const where = corp.length === 1 ? ` in ${D.corpusLabel[corp[0]]}` : corp.length === D.corpusOrder.length ? ' across all corpora' : ` in ${corp.length} corpora`;
  $('#pool-stats').textContent = `${kept} kept · ${excl} excluded${where}`;
  const nref = out.filter(x => x.r.refusal).length;
  $('#stats').textContent = n ? `${n} continuations shown${nref ? ` · of which ${nref} refusal${nref === 1 ? '' : 's'}` : ''} · mean LCS-F1 ${mean.toFixed(2)} · ${(100*ge8).toFixed(0)}% with an exact run ≥ 8 words · ${(100*ge15).toFixed(0)}% ≥ 15 words` : 'nothing matches';
  const main = $('#list');
  main.innerHTML = out.slice(0, shown).map(card).join('') || '<div class="empty">No items match.</div>';
  $('#more').style.display = shown < n ? 'block' : 'none';
  $('#more').textContent = `show ${Math.min(PAGE, n - shown)} more (${n - shown} remaining)`;
}
document.querySelectorAll('header input, header select').forEach(el => el.addEventListener('input', () => render(true)));
$('#more').addEventListener('click', () => { shown += PAGE; render(false); });
$('#list').addEventListener('click', e => {
  const rb = e.target.closest('.rtoggle');
  if (rb) {
    const p = rb.closest('.card').querySelector('.prompt'); p.classList.toggle('open');
    rb.textContent = p.classList.contains('open') ? 'hide full request' : 'show full request';
    return;
  }
  const b = e.target.closest('.toggle'); if (!b) return;
  const doc = b.closest('.doc'); doc.classList.toggle('open');
  b.textContent = doc.classList.contains('open') ? 'hide the earlier words' : `… show the ${b.dataset.n} earlier words`;
});
render(true);
"""


def build_verbatim_review(out_path: Path = RESULTS_DIR / "verbatim_review.html", models: list[str] | None = None) -> Path:
    items = [json.loads(l) for l in (OUT_DIR / "probes.jsonl").open() if '"probe": "verbatim"' in l]
    bt_probes = OUT_DIR / "bigthorium_probes.jsonl"  # Big Thorium's windows live in their own item file; responses are in the same per-model results
    if bt_probes.exists():
        items += [json.loads(l) for l in bt_probes.open() if '"probe": "verbatim"' in l]
    items = [it for it in items if it["probe"] == "verbatim"]
    models = models or [m for m in ("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol") if (RESULTS_DIR / f"{m}.jsonl").exists()]
    res = {m: load_results(m) for m in models}
    corpus_order = ["enron", "jebbush", "mnk", "endo", "cuad", "veridian", "bigthorium", "canon", "titanic"]
    # The request run.py sends is item["system"] / item["user"] verbatim (see run_model -> TextClient.complete). The user message
    # wraps the opening in a fixed instruction, so store that wrapper once and splice the opening back in on the client. If any
    # item breaks the pattern, its full user message is embedded instead, so what is displayed is always exactly what was sent.
    system_msgs = {it["system"] for it in items}
    wrappers = set()
    for it in items:
        u, p = it["user"], it["gold"]["prefix"]
        i = u.find(p)
        wrappers.add((u[:i], u[i + len(p):]) if i >= 0 else None)
    shared = len(system_msgs) == 1 and len(wrappers) == 1 and None not in wrappers
    pre, post = wrappers.pop() if shared else ("", "")
    system_msg = system_msgs.pop() if shared else None
    pool_flags = _load_pool_flags()
    n_fallback = 0
    docs = []
    for it in items:
        g = it["gold"]
        early, visible = _split_long(g["prefix"])
        d = {"doc_id": it["meta"].get("doc_id", it["item_id"].split(":", 2)[-1]), "corpus": it["corpus"],
             "early": html.escape(early), "early_words": len(TOK_RE.findall(early.lower())), "pre": html.escape(visible),
             "prefix_words": len(TOK_RE.findall(g["prefix"].lower())), "n_target": len(TOK_RE.findall(g["target"].lower())),
             "target_txt": g["target"].lower(), "r": {}, **_pool_fields(pool_flags.get(it["item_id"]))}
        rebuilt = pre + early + visible + post
        if not shared or rebuilt != it["user"] or it["system"] != system_msg:
            d["user"], d["system"] = html.escape(it["user"]), html.escape(it["system"])
            n_fallback += 1
        for m in models:
            r = res[m].get(it["item_id"])
            if not r:
                continue
            resp = r["response"]
            sc = score_verbatim(it, resp)
            tgt_html, resp_html, n_gen = _align(g["prefix"], g["target"], resp)
            d["r"][m] = {"resp": resp_html, "resp_txt": resp.lower(), "tgt": tgt_html, "lcs_f": sc["lcs_f"], "max_run": sc["max_run"],
                         "novel_run": sc["novel_run"], "refusal": sc["refusal"], "refusal_kind": sc.get("refusal_kind"), "gen_words": sc["gen_words"],
                         "temp0": bool(r.get("temperature0", True))}
        if d["r"]:
            docs.append(d)
    if n_fallback:
        print(f"[contam-review] {n_fallback} item(s) embed their full prompt (no shared wrapper, or opening could not be re-spliced byte-for-byte)")
    docs.sort(key=lambda d: (corpus_order.index(d["corpus"]) if d["corpus"] in corpus_order else 99, d["doc_id"]))
    data = {"models": models, "meta": {m: list(MODEL_META[m]) for m in models}, "docs": docs, "corpusOrder": corpus_order,
            "corpusLabel": {c: CORPUS_SHORT.get(c, c) for c in corpus_order}, "role": {c: ROLE.get(c) or TAG.get(c) for c in corpus_order},
            "roleText": {r: role_text(r) for r in set(list(ROLE.values()) + list(TAG.values()))},
            "prompt": {"system": html.escape(system_msg or ""), "pre": html.escape(pre), "post": html.escape(post), "max_tokens": MAX_TOKENS["verbatim"]},
            "params": {m: {"model_id": MODELS[m].model_id, "effort": MODELS[m].effort} for m in models}}
    js = JS.replace("${r.tgt}", "${r.tgt}")
    corp_boxes = "".join(f'<label><input type="checkbox" class="corp" value="{c}" checked> {html.escape(CORPUS_SHORT.get(c, c))}</label>' for c in corpus_order)
    model_opts = '<option value="all">all three</option>' + "".join(f'<option value="{m}">{html.escape(MODEL_META[m][0])}</option>' for m in models)
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Finish-the-document probe · review</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head><body>
<header><h1>Finish-the-document probe · every continuation, in context</h1>
<div class="bar">
  <span>corpus:</span>{corp_boxes}
  <label>model <select id="model">{model_opts}</select></label>
  <label>sort by <select id="sort"><option value="lcs">LCS-F1 (overlap)</option><option value="run">longest exact run</option><option value="novel">longest novel run</option><option value="corpus">corpus</option></select>
  <select id="dir"><option value="desc">high → low</option><option value="asc">low → high</option></select></label>
  <label>longest run ≥ <input type="number" id="minrun" value="0" min="0" max="65" style="width:56px;font:inherit;padding:3px 6px;border:1px solid var(--line);border-radius:4px"></label>
  <label>pool <select id="pool"><option value="kept">kept (final pool)</option><option value="excluded">excluded</option><option value="all">all</option></select></label>
  <label><input type="checkbox" id="refusals" checked> show refusals</label>
  <input type="search" id="q" placeholder="search text or document id">
</div>
<div class="stats"><span id="pool-stats"></span> · <span id="stats"></span></div>
<div class="legend">Shared words are highlighted by the length of the exact run they belong to: <mark class="r3">3–7 words</mark><mark class="r8">8–14 words</mark><mark class="r15">15 or more</mark>
<mark class="copy">run that also appears in the prompt (copying, not memory)</mark>. LCS-F1: word overlap in order, 1.0 = word-perfect; about 0.15 is the floor for a plausible continuation with no knowledge of the text.</div>
<div class="note">Pool: every candidate window passes a two-stage filter before it counts — deterministic rules drop e-mail boilerplate, degraded text and corpus-wide templates, then a GPT-5.6 Luna screen keeps only original internal text (rejecting public text reproduced in the collection and low-information windows); excluded windows stay here for the record, marked with their reason. <a href="contamination_report.html#probes">Method (report §5)</a> · <a href="contamination_report.html#rv">counts per corpus (§8)</a>.</div>
<div class="note">Refusals (<span class="ref">refused · private</span> etc.): the model declined to continue the text; they are excluded from the headline LCS-F1 and run statistics (here and in the report) and reported separately as a refusal rate.</div>
</header>
<main><div id="list"></div><button class="more" id="more">more</button></main>
<script>window.__DATA__ = {json.dumps(data, ensure_ascii=False).replace("</", "<\\/")};</script>
<script>{js}</script>
</body></html>"""
    out_path.write_text(page, encoding="utf-8")
    return out_path
