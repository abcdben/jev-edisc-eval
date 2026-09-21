import { useMemo, useState } from "react";
import {
  ABLATION_GROUPS, CORPORA, DATA, DEFAULT_ON, KIND_LABEL, KIND_ORDER, PRIMARY, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER,
  corpusKey, fmtCI, fmtHours, fmtInt, fmtMs, fmtPct, fmtUSD, pick, variantColor,
  type Gray, type IssueScore, type Kind, type Level, type PRF, type Rec,
} from "./data";
import { Control, Hint, Seg, type TipLine } from "./components/ui";
import { PRScatter, type PRItem } from "./components/PRScatter";
import { PRRows } from "./components/PRRows";
import { OpsBars, type BarItem } from "./components/OpsBars";

type Chart = "map" | "ranked";

/** Recall/precision card with a map (scatter with interval boxes) or ranked (rows with whiskers) view. */
function PRCard({ items, v, hint, defaultChart, defaultZoom, emptyText }: { items: PRItem[]; v: View; hint: string; defaultChart: Chart; defaultZoom: boolean; emptyText?: string }) {
  const [chart, setChart] = useState<Chart>(defaultChart);
  const [zoom, setZoom] = useState(defaultZoom);
  return (
    <div className="card">
      <div className="card-t">
        <h3>Recall and precision</h3>
        <span className="unit">{describe(v)}</span>
        <span className="right">
          <Seg value={chart} onChange={setChart} options={[{ id: "map", label: "map", title: "Recall against precision, one box per model" }, { id: "ranked", label: "ranked", title: "Rows sorted by F1, whiskers for the intervals" }]} />
          <Seg value={zoom ? "zoom" : "full"} onChange={(z) => setZoom(z === "zoom")} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }]} />
          <Hint left text={hint} />
        </span>
      </div>
      {chart === "map" ? <PRScatter items={items} zoom={zoom} emptyText={emptyText} /> : <PRRows items={items} zoom={zoom} sortBy="f1" />}
      <div className="legend-note">
        {chart === "map" ? <span>Dot: point estimate. Box: 95% interval on recall (width) and precision (height).</span> : <span>Sorted by F1. Dot: point estimate. Whisker: 95% interval.</span>}
        {items.some((i) => i.dashed) && <span className="k"><span style={{ width: 14, height: 10, border: "1px dashed #7b5ea7", display: "inline-block", borderRadius: 2 }} />dashed: supervised on a split of this corpus</span>}
        {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
      </div>
    </div>
  );
}

type View = { corpus: string; tag: string; arm: "multi" | "single"; gray: Gray; level: Level; issue: string | null };

// ------------------------------------------------------------------------------------------------
// tooltip content

function qualityLines(r: Rec, v: View): { lines: TipLine[]; notes: string[] } {
  const p = pick(r, v.level, v.gray, v.issue);
  const lines: TipLine[] = [["Recall", fmtCI(p.recall)], ["Precision", fmtCI(p.precision)]];
  const notes: string[] = [];
  if (p.detail && "tp" in p.detail) {
    const m = p.detail as PRF;
    lines.push(["F1", m.f1 == null ? "—" : fmtPct(m.f1)]);
    lines.push(["Elusion", fmtCI(m.elusion)]);
    lines.push(["TP / FP / FN / TN", `${fmtInt(m.tp)} / ${fmtInt(m.fp)} / ${fmtInt(m.fn)} / ${fmtInt(m.tn)}`]);
    lines.push(["Gold positives", fmtInt(m.tp + m.fn)]);
    if (m.tp + m.fp === 0) notes.push("Flagged nothing: precision is undefined.");
  } else if (p.detail) {
    const s = p.detail as IssueScore;
    lines.push(["Gold positives for this issue", fmtInt(s.n_pos)]);
    lines.push(["Documents", fmtInt(s.n)]);
  }
  if (r.subset) notes.push(`Scored on ${r.subset}; intervals are wider accordingly.`);
  if (r.lever && !r.primary) notes.push(r.lever);
  const meta = PRIMARY_BY_KEY[r.model];
  if (meta) notes.push(meta.note);
  return { lines, notes };
}

function opsLines(r: Rec): { lines: TipLine[]; notes: string[] } {
  const o = r.ops;
  return {
    lines: [
      ["Documents scored", fmtInt(o.n_docs)],
      ["Decisions", fmtInt(o.n_decisions)],
      ["Median time per document", fmtMs(o.doc_latency_p50_ms)],
      ["p95 time per document", fmtMs(o.doc_latency_p95_ms)],
      ["Hours per 100k docs, 1 stream", fmtHours(o.hours_per_100k_docs)],
      ["Paid cost per document", o.cost_per_doc == null ? "—" : `$${o.cost_per_doc.toFixed(5)}`],
      ["Cost per 100k documents", o.cost_per_doc == null ? "—" : fmtUSD(o.cost_per_doc * 1e5)],
      ["Tokens in / out per doc", o.tokens_in_per_doc == null ? "—" : `${fmtInt(Math.round(o.tokens_in_per_doc))} / ${fmtInt(Math.round(o.tokens_out_per_doc ?? 0))}`],
      ["Pricing", o.pricing_modes.join(", ") || "rented GPU"],
      ["Resolved model", o.model_resolved.join(", ")],
    ],
    notes: [`Latency: ${o.latency_source}.`],
  };
}

// ------------------------------------------------------------------------------------------------

function useRows(v: View) {
  return useMemo(() => DATA.records.filter((r) => r.corpus === v.corpus && r.tag === v.tag && r.arm === v.arm), [v.corpus, v.tag, v.arm]);
}

function OpsPair({ recs, colorOf, nameOf }: { recs: Rec[]; colorOf: (r: Rec) => string; nameOf: (r: Rec) => string }) {
  const time: BarItem[] = recs.map((r) => ({
    id: r.model, name: nameOf(r), color: colorOf(r), value: r.ops.hours_per_100k_docs, label: fmtHours(r.ops.hours_per_100k_docs), tip: opsLines(r), subset: r.subset,
  }));
  const cost: BarItem[] = recs.map((r) => ({
    id: r.model, name: nameOf(r), color: colorOf(r), value: r.ops.cost_per_doc == null ? null : r.ops.cost_per_doc * 1e5,
    label: r.ops.cost_per_doc == null ? "—" : fmtUSD(r.ops.cost_per_doc * 1e5), tip: opsLines(r), subset: r.subset,
  }));
  return (
    <div className="ops-grid">
      <div className="card">
        <div className="card-t">
          <h3>Review time</h3><span className="unit">per 100,000 documents, single stream</span>
          <span className="right"><Hint left text="Median wall-clock time of the model's own calls per document, one request at a time, scaled to 100,000 documents. In the 'all issues per call' arm that is one call per document; in 'one issue per call' it is the sum over issues. Every service accepts parallel requests, so absolute hours shrink with concurrency for all models alike; the ratios are the comparison. Laya and Gemma ran on one A100." /></span>
        </div>
        <OpsBars items={time} axis="hours" />
      </div>
      <div className="card">
        <div className="card-t">
          <h3>Cost</h3><span className="unit">per 100,000 documents, as paid</span>
          <span className="right"><Hint left text="What was actually paid to the vendor, summed over the model's decisions and scaled to 100,000 documents. OpenAI ran on flex pricing (half of list); Anthropic used prompt caching on the all-issues arm. Laya, Gemma and the keyword floor ran on rented hardware (about $2 per A100-hour) and show $0 here; their cost is the review-time panel." /></span>
        </div>
        <OpsBars items={cost} axis="US dollars" />
      </div>
    </div>
  );
}

// ------------------------------------------------------------------------------------------------

function CompareSection({ v }: { v: View }) {
  const rows = useRows(v);
  const [on, setOn] = useState<Set<string>>(new Set(DEFAULT_ON));
  const primary = rows.filter((r) => r.primary);
  const byKind = KIND_ORDER.map((k) => ({ kind: k, recs: PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && r.kind === k) })).filter((g) => g.recs.length);
  const sel = PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && on.has(r.model));
  const toggle = (k: string) => setOn((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });
  const setGroup = (recs: Rec[], val: boolean) => setOn((s) => { const n = new Set(s); recs.forEach((r) => (val ? n.add(r.model) : n.delete(r.model))); return n; });

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    const meta = PRIMARY_BY_KEY[r.model];
    return { id: r.model, name: meta.short, color: meta.color, recall: p.recall, precision: p.precision, dashed: r.kind === "system1_ft", subset: r.subset, tip: qualityLines(r, v) };
  });

  return (
    <section className="section">
      <div className="sec-head">
        <h2>Compare models</h2>
        <span className="sub">Each dot is a model's recall and precision; the box around it is the 95% interval on both.</span>
      </div>
      <div className="sec-body">
        <aside className="picker">
          {byKind.map((g) => (
            <div className="grp" key={g.kind}>
              <div className="grp-t">
                <span>{KIND_LABEL[g.kind as Kind]}</span>
                <span>
                  <button onClick={() => setGroup(g.recs, true)}>all</button>&nbsp;·&nbsp;<button onClick={() => setGroup(g.recs, false)}>none</button>
                </span>
              </div>
              {g.recs.map((r) => {
                const m = PRIMARY_BY_KEY[r.model];
                return (
                  <button key={r.model} className={`pick${on.has(r.model) ? "" : " off"}`} onClick={() => toggle(r.model)} title={m.note}>
                    <span className="sw" style={{ background: m.color }} />
                    <span className="nm">{m.short}</span>
                    {r.subset && <span className="tag" title={`scored on ${r.subset}`}>subset</span>}
                    {r.kind === "system1_ft" && <span className="tag">supervised</span>}
                  </button>
                );
              })}
            </div>
          ))}
        </aside>
        <div>
          <PRCard
            items={items} v={v} defaultChart="map" defaultZoom={false}
            hint="Recall: gold-responsive items the model flagged, over all gold-responsive items. Precision: flagged items that were gold-responsive, over all flagged. Intervals are 95% Wilson score intervals. Because every document in each test set carries a gold label, the recall interval is computed over the gold-positive set and the precision interval over the model's flagged set, rather than from a review sample. All metrics use the model's own label, not a tuned threshold."
          />
          <OpsPair recs={sel} colorOf={(r) => PRIMARY_BY_KEY[r.model].color} nameOf={(r) => PRIMARY_BY_KEY[r.model].short} />
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------

function AblationSection({ v }: { v: View }) {
  const rows = useRows(v);
  const [grp, setGrp] = useState("jev");
  const [off, setOff] = useState<Set<string>>(new Set());
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useMemo(() => {
    const recs = rows.filter((r) => r.group === grp && r.variant);
    return VARIANT_ORDER.map((vv) => recs.find((r) => r.variant === vv)).filter((r): r is Rec => !!r);
  }, [rows, grp]);
  const sel = variants.filter((r) => !off.has(r.variant!));
  const color = (r: Rec) => variantColor(r.variant!, G.recipe);
  const name = (r: Rec) => VARIANT_LABEL[r.variant!] ?? r.variant!;
  const toggle = (vv: string) => setOff((s) => { const n = new Set(s); n.has(vv) ? n.delete(vv) : n.add(vv); return n; });

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    return { id: r.model, name: name(r), color: color(r), recall: p.recall, precision: p.precision, subset: r.subset, tip: qualityLines(r, v) };
  });

  return (
    <section className="section">
      <div className="sec-head">
        <h2>Configurations of one model</h2>
        <span className="sub">Each variant changes a single lever from the default. The recipe is the configuration carried into the comparison above.</span>
      </div>
      <div className="sec-body">
        <aside className="picker">
          <div className="grp">
            <div className="grp-t"><span>Model</span></div>
            <span className="select" style={{ display: "block" }}>
              <select value={grp} onChange={(e) => { setGrp(e.target.value); setOff(new Set()); }} style={{ width: "100%" }}>
                {ABLATION_GROUPS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
              </select>
            </span>
            <div style={{ color: "var(--ink-3)", fontSize: 12, marginTop: 8, lineHeight: 1.45 }}>{G.note}</div>
          </div>
          <div className="grp">
            <div className="grp-t">
              <span>Configurations</span>
              <span><button onClick={() => setOff(new Set())}>all</button>&nbsp;·&nbsp;<button onClick={() => setOff(new Set(variants.map((r) => r.variant!)))}>none</button></span>
            </div>
            {variants.map((r) => (
              <button key={r.model} className={`pick${off.has(r.variant!) ? " off" : ""}`} onClick={() => toggle(r.variant!)} title={r.lever ?? undefined}>
                <span className="sw" style={{ background: color(r) }} />
                <span className="nm">{name(r)}</span>
                {r.variant === G.recipe && <span className="star" title="recipe">★</span>}
                {r.subset && <span className="tag">subset</span>}
              </button>
            ))}
            {variants.length === 0 && <div className="empty">No configurations of this model were run on this corpus and arm.</div>}
          </div>
        </aside>
        <div>
          <PRCard
            items={items} v={v} defaultChart="ranked" defaultZoom={true}
            emptyText={variants.length ? "Select at least one configuration." : "No configurations available for this view."}
            hint="Same measurement as above. Differences between configurations are usually smaller than between model families, so this card defaults to ranked rows with the axes fitted to the data; switch to map and 0–100% to see the same points on the scale used above. Hover a configuration for what the lever changes."
          />
          <OpsPair recs={sel} colorOf={color} nameOf={name} />
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------

function describe(v: View): string {
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];
  const issue = v.issue ? `issue: ${meta.issues[v.issue]}` : v.level === "doc" ? "document-level, responsive to any issue" : "decision-level, every (document, issue) pair";
  const gold = v.issue ? "all gold labels" : v.gray === "all" ? "all gold labels" : "gray labels excluded";
  return `${issue} · ${gold} · ${v.arm === "multi" ? "all issues per call" : "one issue per call"}`;
}

export default function App() {
  const [corpus, setCorpus] = useState("mnk");
  const [tag, setTag] = useState<"" | "v0">("");
  const [arm, setArm] = useState<"multi" | "single">("multi");
  const [gray, setGray] = useState<Gray>("all");
  const [level, setLevel] = useState<Level>("doc");
  const [issue, setIssue] = useState<string | null>(null);
  const v: View = { corpus, tag: corpus === "trec" ? tag : "", arm, gray, level, issue };
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];
  const nModels = new Set(DATA.records.filter((r) => r.primary).map((r) => r.model)).size;
  const nConfigs = new Set(DATA.records.map((r) => r.model)).size;
  const nDocs = Object.values(DATA.corpora).filter((c) => !c.tag).reduce((a, c) => a + c.n_docs, 0);

  const pickCorpus = (c: string) => { setCorpus(c); setIssue(null); };

  return (
    <div className="page">
      <header className="masthead">
        <span className="eyebrow">Benchmark · document review · {new Date().getFullYear()}</span>
        <h1 className="title">System 1 decision models against <em>large language models</em> for relevance and issue review</h1>
        <p className="lede">
          Four labeled corpora, {nModels} classifiers, {nConfigs} configurations, one shared set of requests for production per corpus. Choose a corpus and the models you care about; every mark on the page can be hovered for the numbers behind it.
        </p>
        <div className="stats">
          <span className="stat"><span className="n">{fmtInt(nDocs)}</span><span className="l">gold-labeled documents</span></span>
          <span className="stat"><span className="n">{Object.values(DATA.corpora).filter((c) => !c.tag).reduce((a, c) => a + c.n_issues, 0)}</span><span className="l">issues (RFPs)</span></span>
          <span className="stat"><span className="n">{nModels}</span><span className="l">classifiers compared</span></span>
          <span className="stat"><span className="n">{fmtInt(DATA.records.filter((r) => r.primary).reduce((a, r) => a + r.ops.n_decisions, 0))}</span><span className="l">decisions scored (headline roster)</span></span>
        </div>
      </header>

      <div className="controls">
        <Control label="Corpus">
          <Seg value={corpus} onChange={pickCorpus} options={CORPORA.map((c) => ({ id: c.id, label: c.label, title: c.short }))} />
        </Control>
        {corpus === "trec" && (
          <Control label="Criteria">
            <Seg value={tag} onChange={setTag} options={[
              { id: "", label: "calibrated", title: "Criteria refined once on a 668-email calibration set disjoint from this evaluation set" },
              { id: "v0", label: "bare topic", title: "The NIST topic sentence as written, no iteration" },
            ]} />
          </Control>
        )}
        <Control label="Prompting">
          <Seg value={arm} onChange={setArm} options={[
            { id: "multi", label: "all issues per call", title: "One call per document answers every issue" },
            { id: "single", label: "one issue per call", title: "One call per (document, issue) pair" },
          ]} />
        </Control>
        <Control label="Scope">
          <span className="select">
            <select value={issue ?? (level === "doc" ? "__doc" : "__dec")} onChange={(e) => { const val = e.target.value; if (val === "__doc") { setIssue(null); setLevel("doc"); } else if (val === "__dec") { setIssue(null); setLevel("decision"); } else setIssue(val); }}>
              <option value="__doc">Any issue (document level)</option>
              <option value="__dec">Every decision (document × issue)</option>
              <optgroup label="Single issue">
                {Object.entries(meta.issues).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </optgroup>
            </select>
          </span>
          <Hint text="Document level: a document counts as responsive if it is positive for any issue, which is the relevance call a review team makes. Decision level pools every (document, issue) judgment. A single issue shows that issue's recall and precision on its own (all gold labels)." />
        </Control>
        <Control label="Gold">
          <Seg value={issue ? "all" : gray} onChange={setGray} options={[
            { id: "all", label: "all labels" },
            { id: "nogray", label: "exclude gray", title: issue ? "Not available for a single issue" : "Drop decisions whose gold label was flagged as debatable" },
          ]} />
        </Control>
      </div>

      <div style={{ marginTop: 18, color: "var(--ink-2)", fontSize: 13, display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
        <span style={{ fontFamily: "var(--serif)", fontSize: 18, color: "var(--ink)" }}>{meta.display}</span>
        <span style={{ color: "var(--ink-3)" }}>
          {fmtInt(meta.n_docs)} documents · {meta.n_issues} issues · {fmtInt(meta.n_pos_docs_any)} responsive to at least one ({fmtPct(meta.n_pos_docs_any / meta.n_docs, 0)}) · gold: {meta.gold}
        </span>
      </div>

      <CompareSection v={v} />
      <AblationSection v={v} />

      <footer className="foot">
        <div>
          <h4>What every model saw</h4>
          <p>The same document text, the same issue criteria and matter context, and returned a label plus a probability. Metrics use the model's own label. Jev and Laya rows are the default configuration unless marked recipe.</p>
        </div>
        <div>
          <h4>Intervals</h4>
          <p>95% Wilson score intervals. Recall is measured over the gold-positive set, precision over the flagged set. Where a model is scored on a stratified subset (marked *), intervals widen to match.</p>
        </div>
        <div>
          <h4>TREC criteria</h4>
          <p>Issue criteria were refined once on a 668-email calibration set that is disjoint from the evaluation set shown. The bare-topic toggle shows the NIST topic sentence with no iteration.</p>
        </div>
        <div>
          <h4>Absent cells</h4>
          <p>A few one-issue-per-call Laya configurations stalled and are omitted from that view. The fine-tuned Laya checkpoint on CUAD collapsed to a constant negative and is shown as such.</p>
        </div>
      </footer>
    </div>
  );
}
