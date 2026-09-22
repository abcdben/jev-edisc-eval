import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ABLATION_GROUPS, CORPORA, DATA, DEFAULT_CORPUS, DEFAULT_ON, GPU_NAME, GPU_USD_PER_HOUR, HUMAN_DEV_DOCS, HUMAN_DEV_DOCS_PER_HOUR, HUMAN_DEV_HOURS, HUMAN_DEV_USD, HUMAN_DEV_USD_PER_HOUR, PRIMARY, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER,
  corpusKey, costPerDoc, fmtCI, fmtHours, fmtInt, fmtMs, fmtPct, fmtUSD, isDecider, isGpuRow, isHidden, pick, siteCorpus, starOf, variantColor,
  type Gray, type Kind, type Level, type PRF, type Rec,
} from "./data";
import { Control, Hint, MethodContext, Seg, type HintItem, type TipLine } from "./components/ui";
import { PRScatter, type PRItem } from "./components/PRScatter";
import { PRRows } from "./components/PRRows";
import { OpsBars, type BarItem } from "./components/OpsBars";
import { Consistency, detFor, detLines } from "./components/Consistency";
import { HoverProvider, useHover } from "./components/hover";
import { ExplainButton, ExplainModal, type MetricSection, type Metrics } from "./components/Explain";
import { Picker, type PickGroup } from "./components/Picker";
import { MethodButton, MethodModal } from "./components/Method";
import { DisclaimerLink, DisclaimerModal, useDisclaimer } from "./components/Disclaimer";
import { Logo } from "./logos";

type Chart = "map" | "ranked";

/** Short group names for the one-line picker. */
/** Picker order: deciders first, then the LLMs (API and local share one group via the PRIMARY `kind` override), then TAR. Kinds with no roster member (`baseline`, `local_llm`) are dropped before rendering. */
const PICK_ORDER: Kind[] = ["system1", "system1_ft", "baseline", "llm", "local_llm", "tar"];
const KIND_SHORT: Record<Kind, string> = { system1: "Deciders", system1_ft: "Supervised", llm: "LLM", local_llm: "Local LLM", tar: "Classical TAR", baseline: "Floor" };

/** Recall/precision card with a map (scatter with interval boxes) or ranked (rows with whiskers) view. The chart mode is owned by the section so it can switch the dashboard layout. `explain` opens the details modal for a clicked mark or row (item ids are model keys). */
function PRCard({ items, hint, chart, onChart, defaultZoom, emptyText, logos = true, height = 380, explain }: { items: PRItem[]; hint: HintItem[]; chart: Chart; onChart: (c: Chart) => void; defaultZoom: boolean; emptyText?: string; logos?: boolean; height?: number; explain?: (k: string) => void }) {
  const setChart = onChart;
  const [zoom, setZoom] = useState(defaultZoom);
  const onSelect = explain && ((it: PRItem) => explain(it.id));
  const hover = useHover();
  return (
    <div className={`card${chart === "map" ? " fill" : ""}`}>
      <div className="card-t">
        <h3>Recall and precision</h3>
        <span className="right">
          <Seg value={chart} onChange={setChart} options={[{ id: "map", label: "map", title: "Recall against precision, one box per model" }, { id: "ranked", label: "ranked", title: "Rows sorted by F1, whiskers for the intervals" }]} />
          <Seg value={zoom ? "zoom" : "full"} onChange={(z) => setZoom(z === "zoom")} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }]} />
          <Hint items={hint} more="Method" />
        </span>
      </div>
      {chart === "map" ? <div className="chart-fill" style={{ minHeight: height }}><PRScatter items={items} zoom={zoom} emptyText={emptyText} logos={logos} fill onSelect={onSelect} highlight={hover.id} onHover={hover.set} /></div> : <PRRows items={items} zoom={zoom} sortBy="recall" logos={logos} onSelect={onSelect} highlight={hover.id} onHover={hover.set} />}
      <div className="legend-note">
        {chart === "map" ? <span>Dot: point estimate. Shaded box: 95% interval on recall (width) and precision (height).</span> : <span>Sorted by recall. Dot: point estimate. Whisker: 95% interval.</span>}
        {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
      </div>
    </div>
  );
}

type View = { corpus: string; tag: string; arm: "multi" | "single"; gray: Gray; level: Level; issue: string | null };

/** Recall and precision card, Compare models. */
const PR_ITEMS: HintItem[] = [
  { k: "Recall", v: <><b>Gold-responsive items the model flagged</b>, over all gold-responsive items.</> },
  { k: "Precision", v: <><b>Flagged items that were gold-responsive</b>, over all flagged.</> },
  { k: "Intervals", v: <mark><b>95% Wilson</b> score; recall over the gold-positive set, precision over the flagged set, since every document carries a gold label.</mark> },
  { k: "Label", v: <><b>The model's own label</b>, not a tuned threshold.</> },
  { k: "Scope", v: <><b>Document level</b>: responsive if positive for any issue. Decision level: every (document, issue) judgment pooled.</> },
  { k: "Gray", v: <>'Exclude gray' <b>drops decisions whose gold label was flagged as debatable</b>.</> },
  { k: "*", v: <><b>Scored on a stratified subset</b>; hover a row for the count. Intervals widen to match.</> },
  { k: "Deciders", v: <><b>Jev and Laya</b> are set in a heavier name in the tables.</> },
];
/** Recall and precision card, Configurations page. */
const CONFIG_PR_ITEMS: HintItem[] = [
  { k: "Measures", v: <><b>The same recall and precision</b> as on Compare models, for configurations of one model.</> },
  { k: "Default view", v: <><b>Ranked rows with axes fitted to the data</b>, since configurations differ less than model families; switch to map and 0–100% for the Compare scale.</> },
  { k: "Intervals", v: <><b>95% Wilson</b> score; * marks a stratified subset.</> },
  { k: "Levers", v: <><b>Hover a configuration</b> for what its lever changes.</> },
  { k: "★", v: <mark><b>The optimized configuration</b>, selected on the Veridian dev split.</mark> },
];

// ------------------------------------------------------------------------------------------------
// Metrics: the full figures for a row. Shown in the details modal's Metrics block; the chart hovers carry only the plotted value and one
// secondary line (qualitySub, opsSub).

/** The one secondary line of a recall/precision hover: what the point was scored on. */
function qualitySub(r: Rec, v: View): string | undefined {
  if (r.subset) return `scored on ${r.subset}`;
  const n = pick(r, v.level, v.gray, v.issue).detail?.n;
  return n ? `${fmtInt(n)} ${v.level === "decision" && !v.issue ? "decisions" : "documents"} scored` : undefined;
}

function qualityLines(r: Rec, v: View): { lines: TipLine[]; notes: string[] } {
  const p = pick(r, v.level, v.gray, v.issue);
  const lines: TipLine[] = [["Recall", fmtCI(p.recall)], ["Precision", fmtCI(p.precision)]];
  if (p.detail && "tp" in p.detail) {
    const m = p.detail as PRF;
    lines.push(["F1", m.f1 == null ? "—" : fmtPct(m.f1)]);
  }
  if (r.subset) lines.push(["Scored on", r.subset]);
  const notes: string[] = [];
  if (r.tar) {
    const t = r.tar;
    lines.push([t.kind === "cal" ? "Reviewed by hand" : "Coded for training", `${fmtInt(t.docs_reviewed)} of ${fmtInt(t.n_corpus)} (${fmtPct(t.review_share, 0)})`]);
    if (t.kind === "cal") {
      if (t.control_set) lines.push(["Control set", `${fmtInt(t.control_set.n)} random documents, coded first (${fmtInt(t.control_set.relevant_coded)} coded relevant)`]);
      const trueRecall = t.production?.recall ?? null;
      if (t.est_recall_at_stop != null) lines.push(["Estimated recall at stop", `${fmtPct(t.est_recall_at_stop)} · true ${fmtPct(trueRecall)} on the pool${t.reached_recall != null ? ` (reviewer read ${fmtPct(t.reached_recall)} of relevant)` : ""}`]);
      else if (t.stop) lines.push(["Stop", `${t.stop}${trueRecall != null ? ` · true recall ${fmtPct(trueRecall)} on the pool` : ""}`]);
      if (t.review_set_precision != null) lines.push(["Review-set precision", `${fmtPct(t.review_set_precision)} of documents read were relevant`]);
      if (t.classifier) lines.push(["Classifier alone on eval set", `recall ${fmtPct(t.classifier.eval.recall)} · precision ${fmtPct(t.classifier.eval.precision)} (cutoff set on the control set)`]);
    }
    if (t.recall_range) lines.push([`Recall across ${t.seeds} seeds`, `${fmtPct(t.recall_range[0])} – ${fmtPct(t.recall_range[1])}`]);
    if (t.kind === "cal") {
      notes.push("Plotted: the production set, every document the reviewer coded relevant (control set included), scored against gold on the pool CAL ran over. Its precision is the reviewer's, so the classifier's own quality is the 'classifier alone' line.");
      if (t.control_set && t.reviewer.miscode_rate > 0) notes.push("The recall estimate is against the reviewer's coding of the control set: documents the reviewer over-coded as relevant are never found by the classifier and hold the estimate below the true figure, so review runs past the target.");
      if (t.downsampled) notes.push(`Run on a ${fmtPct(t.pool_richness ?? 0, 0)}-rich pool of ${fmtInt(t.n_corpus)} documents (all gold-negatives plus a random draw of positives); the benchmark sample itself is 61% rich by design.`);
    }
  }
  if (r.lever && !r.primary) notes.push(r.lever);
  return { lines, notes };
}

/** "machine": the model's own time and bill. "human": adds the prompt/criteria development a person does for every non-TAR row. */
type OpsMode = "machine" | "human";

/** Hours and dollars per 100k documents for a record under the toggle; null when not measured or, for TAR in machine mode, not applicable. */
function opsValues(r: Rec, mode: OpsMode): { hours: number | null; usd: number | null } {
  const c = costPerDoc(r);
  if (r.tar) return mode === "machine" ? { hours: null, usd: null } : { hours: r.ops.hours_per_100k_docs, usd: c == null ? null : c * 1e5 };
  const add = mode === "human";
  return {
    hours: r.ops.hours_per_100k_docs == null ? null : r.ops.hours_per_100k_docs + (add ? HUMAN_DEV_HOURS : 0),
    usd: c == null ? null : c * 1e5 + (add ? HUMAN_DEV_USD : 0),
  };
}

/** The one secondary line of a Review time or Cost hover: the per-document time, or where the money went. */
function opsSub(r: Rec, mode: OpsMode, kind: "time" | "cost"): string {
  const human = mode === "human" ? " · incl. prompt development" : "";
  if (r.tar) return kind === "time" ? `${fmtInt(r.tar.docs_reviewed)} documents read by hand` : `reviewer at $${r.tar.reviewer.usd_per_hour}/h`;
  if (kind === "time") return `${fmtMs(r.ops.doc_latency_p50_ms)} per doc${human}`;
  return `as paid · ${isGpuRow(r) ? "GPU rental" : "API"}${human}`;
}

/** `timeMode` and `costMode` are the two cards' independent "+ human time" toggles. */
function opsLines(r: Rec, timeMode: OpsMode, costMode: OpsMode): { lines: TipLine[]; notes: string[] } {
  const o = r.ops;
  const c = costPerDoc(r);
  const usd100k = c == null ? "—" : fmtUSD(c * 1e5);
  if (r.tar) {
    const t = r.tar;
    return {
      lines: [
        ["Documents reviewed by hand", `${fmtInt(t.docs_reviewed)} of ${fmtInt(t.n_corpus)}`],
        ["Reviewer hours", fmtHours(t.hours)],
        ["Reviewer cost", fmtUSD(t.cost_usd)],
        ["Per 100k docs, scaled from this corpus", `${fmtHours(o.hours_per_100k_docs)} · ${usd100k}`],
      ],
      notes: [`${t.reviewer.docs_per_hour} docs/hour at $${t.reviewer.usd_per_hour}/hour; classifier compute not charged. A fixed coded sample does not scale with corpus size, so the per-100k figure is specific to a ${fmtInt(t.n_corpus)}-document collection.`],
    };
  }
  const lines: TipLine[] = [
    ["Time per 100k docs", fmtHours(o.hours_per_100k_docs)],
    ["Cost per 100k docs", usd100k],
  ];
  const notes: string[] = [];
  if (isGpuRow(r) && o.hours_per_100k_docs != null) {
    lines.push(["GPU rental", `${GPU_NAME} at $${GPU_USD_PER_HOUR.toFixed(2)}/h × ${fmtHours(o.hours_per_100k_docs)} = ${usd100k} per 100k`]);
    notes.push("Cost is the rented GPU time for the single-stream review time shown; serving many documents concurrently would lower it.");
  }
  if (timeMode === "human" || costMode === "human") {
    const tot = { hours: opsValues(r, timeMode).hours, usd: opsValues(r, costMode).usd };
    const shown = [timeMode === "human" ? fmtHours(tot.hours) : null, costMode === "human" ? fmtUSD(tot.usd) : null].filter(Boolean).join(" · ");
    lines.push(
      ["Prompt development", `${fmtHours(HUMAN_DEV_HOURS)} · ${fmtUSD(HUMAN_DEV_USD)} (${HUMAN_DEV_DOCS} docs at ${HUMAN_DEV_DOCS_PER_HOUR}/h, $${HUMAN_DEV_USD_PER_HOUR}/h; counted once per 100k-document project)`],
      ["Shown, machine + human", shown],
    );
    if (r.model === "laya-ft") notes.push("The labeled training data this checkpoint needed is not counted here, only the same 500-document iteration every row gets.");
  }
  lines.push(
    ["Median time per doc", fmtMs(o.doc_latency_p50_ms)],
    ["Tokens in / out per doc", o.tokens_in_per_doc == null ? "—" : `${fmtInt(Math.round(o.tokens_in_per_doc))} / ${fmtInt(Math.round(o.tokens_out_per_doc ?? 0))}`],
  );
  return { lines, notes };
}

/** The "+ human time" toggles are independent: Review time and Cost each remember their own mode. */
const OPS_MODE_KEYS = { time: "opsMode.time", cost: "opsMode.cost" } as const;
const readOpsMode = (k: keyof typeof OPS_MODE_KEYS): OpsMode => (localStorage.getItem(OPS_MODE_KEYS[k]) === "human" ? "human" : "machine");

/**
 * Everything the details modal's Metrics block lists for one row on one corpus: the recall/precision, review time and cost, and determinism
 * facts that the chart tooltips used to carry. `shown` picks the page's selection out of the corpus rows, the referent of "vs. lowest shown".
 */
function metricsFor(key: string, corpus: string, v: View, shown: (rows: Rec[]) => Rec[]): Metrics | null {
  const tag = corpus === "trec" ? v.tag : "";
  const rows = DATA.records.filter((r) => r.corpus === corpus && r.tag === tag && r.arm === v.arm);
  const r = rows.find((x) => x.model === key);
  if (!r) return null;
  const vv: View = { ...v, corpus, tag, issue: corpus === v.corpus ? v.issue : null };
  const meta = DATA.corpora[corpusKey(corpus, tag)];
  const timeMode = readOpsMode("time"), costMode = readOpsMode("cost");
  const group = ABLATION_GROUPS.find((g) => g.id === r.group);
  const name = PRIMARY_BY_KEY[r.model]?.short ?? (r.variant ? `${group?.label ?? r.family} · ${VARIANT_LABEL[r.variant] ?? r.variant}` : r.name);
  const color = PRIMARY_BY_KEY[r.model]?.color ?? (r.variant ? variantColor(r.variant, group?.recipe ?? "") : "var(--ink)");
  const scope = vv.issue ? meta.issues[vv.issue] : vv.level === "decision" ? "every decision" : "document level";
  const context = [meta.display, vv.arm === "single" ? "one issue per call" : "all issues per call", scope, !vv.issue && vv.gray === "nogray" ? "gray excluded" : null].filter(Boolean).join(" · ");
  const q = qualityLines(r, vv);
  const o = opsLines(r, timeMode, costMode);
  const peers = shown(rows);
  const lowest = (f: (x: Rec) => number | null) => { const vals = peers.map(f).filter((x): x is number => x != null && x > 0); return vals.length ? Math.min(...vals) : null; };
  const ratio = (label: string, val: number | null, best: number | null): TipLine[] => {
    if (val == null || !best || val / best <= 1.05) return [];
    const k = val / best;
    return [[label, `${k >= 10 ? Math.round(k) : k.toFixed(1)}×`]];
  };
  const mine = { hours: opsValues(r, timeMode).hours, usd: opsValues(r, costMode).usd };
  const sections: MetricSection[] = [
    { title: "Recall and precision", lines: q.lines, notes: q.notes },
    {
      title: timeMode === "human" || costMode === "human" ? "Review time and cost · machine + human" : "Review time and cost",
      lines: [...o.lines, ...ratio("Time vs. lowest shown", mine.hours, lowest((x) => opsValues(x, timeMode).hours)), ...ratio("Cost vs. lowest shown", mine.usd, lowest((x) => opsValues(x, costMode).usd))],
      notes: o.notes,
    },
  ];
  const det = detFor(r, vv.arm, "default"), t0 = detFor(r, vv.arm, "t0");
  if (det) { const d = detLines(det, r, name); sections.push({ title: "Determinism", lines: d.lines, notes: d.notes }); }
  if (t0) { const d = detLines(t0, r, name); sections.push({ title: "Determinism · temperature 0", lines: d.lines, notes: d.notes }); }
  return { name, color, context, sections };
}

// ------------------------------------------------------------------------------------------------

function useRows(v: View) {
  return useMemo(() => DATA.records.filter((r) => r.corpus === v.corpus && r.tag === v.tag && r.arm === v.arm), [v.corpus, v.tag, v.arm]);
}

const OPS_MODE_OPTIONS = [
  { id: "machine" as const, label: "machine only", title: "The model's own time and bill" },
  { id: "human" as const, label: "+ human time", title: `Adds ${fmtHours(HUMAN_DEV_HOURS)} and ${fmtUSD(HUMAN_DEV_USD)} of prompt development to every non-TAR row` },
];
/** The two rows shared by the Review time and Cost hints: what the '+ human time' toggle adds, and why TAR rows disappear without it. */
const HUMAN_ITEMS: HintItem[] = [
  { k: "+ human time", v: <>Adds prompt or criteria development: {HUMAN_DEV_DOCS} documents at {HUMAN_DEV_DOCS_PER_HOUR}/h and ${HUMAN_DEV_USD_PER_HOUR}/h, <b>{fmtHours(HUMAN_DEV_HOURS)} and {fmtUSD(HUMAN_DEV_USD)}</b>, once per 100k-document project.</> },
  { k: "TAR rows", v: <><b>Already human time</b>, so they are hidden in machine-only.</> },
];
const TIME_ITEMS: HintItem[] = [
  { k: "Measures", v: <><b>Median</b> wall-clock time per document for the model's own calls, one request at a time, scaled to 100,000 documents.</> },
  { k: "Arms", v: <><b>All issues per call</b>: one call per document. One issue per call: the sum over issues.</> },
  { k: "Parallelism", v: <mark>Every service accepts parallel requests, so hours shrink for all models alike; <b>compare the ratios, not the absolutes</b>.</mark> },
  { k: "GPU rows", v: <>Laya and Gemma ran on <b>one rented A100</b>.</> },
  ...HUMAN_ITEMS,
];
const COST_ITEMS: HintItem[] = [
  { k: "Measures", v: <><b>What was actually paid</b> to the vendor, summed over the model's decisions and scaled to 100,000 documents.</> },
  { k: "Pricing", v: <>OpenAI on <b>flex pricing (half of list)</b>; Anthropic with prompt caching on the all-issues arm.</> },
  { k: "GPU rows", v: <mark>Laya and Gemma: a rented {GPU_NAME} at ${GPU_USD_PER_HOUR.toFixed(2)}/h times the single-stream review time, so <b>an upper bound</b>.</mark> },
  ...HUMAN_ITEMS,
];

/** `decider` sets a row's name a step heavier (data.ts isDecider); Compare models passes it, the Configurations page (one family per chart) does not. */
function OpsCards({ recs, colorOf, nameOf, logos = true, explain, decider }: { recs: Rec[]; colorOf: (r: Rec) => string; nameOf: (r: Rec) => string; logos?: boolean; explain?: (k: string) => void; decider?: (r: Rec) => boolean }) {
  const [timeMode, setTimeMode] = useState<OpsMode>(() => readOpsMode("time"));
  const [costMode, setCostMode] = useState<OpsMode>(() => readOpsMode("cost"));
  const onSelect = explain && ((it: BarItem) => explain(it.id));
  const hover = useHover();
  useEffect(() => { localStorage.setItem(OPS_MODE_KEYS.time, timeMode); }, [timeMode]);
  useEffect(() => { localStorage.setItem(OPS_MODE_KEYS.cost, costMode); }, [costMode]);
  const empty = (r: Rec, mode: OpsMode) => (r.tar && mode === "machine" ? "human only" : undefined);
  const time: BarItem[] = recs.map((r) => {
    const { hours } = opsValues(r, timeMode);
    return { id: r.model, name: nameOf(r), color: colorOf(r), value: hours, label: fmtHours(hours), sub: opsSub(r, timeMode, "time"), subset: starOf(r), empty: empty(r, timeMode), decider: decider?.(r) };
  });
  const cost: BarItem[] = recs.map((r) => {
    const { usd } = opsValues(r, costMode);
    return { id: r.model, name: nameOf(r), color: colorOf(r), value: usd, label: fmtUSD(usd), sub: opsSub(r, costMode, "cost"), subset: starOf(r), empty: empty(r, costMode), decider: decider?.(r) };
  });
  return (
    <>
      <div className="card">
        <div className="card-t">
          <h3>Review time</h3><span className="unit">per 100k documents, single stream</span>
          <span className="right"><Seg value={timeMode} onChange={setTimeMode} options={OPS_MODE_OPTIONS} /><Hint items={TIME_ITEMS} more="Method" /></span>
        </div>
        <OpsBars items={time} axis="hours" unit="per 100k docs" logos={logos} onSelect={onSelect} highlight={hover.id} onHover={hover.set} />
      </div>
      <div className="card">
        <div className="card-t">
          <h3>Cost</h3><span className="unit">per 100k documents, as paid</span>
          <span className="right"><Seg value={costMode} onChange={setCostMode} options={OPS_MODE_OPTIONS} /><Hint items={COST_ITEMS} more="Method" /></span>
        </div>
        <OpsBars items={cost} axis="US dollars" unit="per 100k docs" logos={logos} onSelect={onSelect} highlight={hover.id} onHover={hover.set} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------------------------------------

/** A headline row's kind for grouping: the roster's override (Laya's fine-tuned row sits with the deciders) or the record's own. */
const kindOf = (r: Rec): Kind => PRIMARY_BY_KEY[r.model]?.kind ?? (r.kind as Kind);

/** The model multi-select for Compare models, rendered in the control bar. */
function ModelPicker({ v, on, setOn, explain }: { v: View; on: Set<string>; setOn: (s: Set<string>) => void; explain: (k: string) => void }) {
  const rows = useRows(v);
  const primary = rows.filter((r) => r.primary && PRIMARY_BY_KEY[r.model]);
  const byKind = PICK_ORDER.map((k) => ({ kind: k, recs: PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && kindOf(r) === k) })).filter((g) => g.recs.length);
  const avail = primary.filter((r) => on.has(r.model)).length;
  const groups: PickGroup[] = byKind.map((g) => ({
    id: g.kind, label: KIND_SHORT[g.kind as Kind],
    items: g.recs.map((r) => {
      const m = PRIMARY_BY_KEY[r.model];
      return { id: r.model, label: m.short, title: m.note, mark: <span style={{ color: m.color }}><Logo model={r.model} /></span>, suffix: starOf(r) ? <span className="sub" title={`scored on ${r.subset}`}>*</span> : undefined, detail: () => explain(r.model), accent: isDecider(kindOf(r)) ? m.color : undefined };
    }),
  }));
  return <Picker label="Models" summary={`${avail} of ${primary.length}`} groups={groups} on={on} onChange={setOn} onReset={() => setOn(new Set(DEFAULT_ON))} />;
}

function CompareSection({ v, on, explain }: { v: View; on: Set<string>; explain: (k: string) => void }) {
  const rows = useRows(v);
  const primary = rows.filter((r) => r.primary);
  const sel = PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && on.has(r.model));
  const [chart, setChart] = useState<Chart>("map");
  // the decider marker (data.ts isDecider: heavier name on rows) on every chart of this page, by the roster's kind (Laya's fine-tuned row is grouped with the deciders)
  const decider = (r: Rec) => isDecider(kindOf(r));

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    const meta = PRIMARY_BY_KEY[r.model];
    return { id: r.model, name: meta.short, color: meta.color, recall: p.recall, precision: p.precision, dashed: r.kind === "system1_ft", subset: starOf(r), sub: qualitySub(r, v), decider: decider(r) };
  });

  return (
    <section className="section">
      <HoverProvider>
        <div className={`dash${chart === "ranked" ? " ranked" : ""}`}>
          <PRCard
            items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={explain}
            hint={PR_ITEMS}
          />
          <div className="stack">
            <OpsCards recs={sel} colorOf={(r) => PRIMARY_BY_KEY[r.model].color} nameOf={(r) => PRIMARY_BY_KEY[r.model].short} explain={explain} decider={decider} />
            <ConsistencyCard recs={sel} colorOf={(r) => PRIMARY_BY_KEY[r.model].color} nameOf={(r) => PRIMARY_BY_KEY[r.model].short} arm={v.arm} onSelect={(r) => explain(r.model)} />
          </div>
        </div>
      </HoverProvider>
    </section>
  );
}

/** The Determinism card wired to the section's cross-chart hover (hover.tsx). */
function ConsistencyCard(props: Parameters<typeof Consistency>[0]) {
  const hover = useHover();
  return <Consistency {...props} highlight={hover.id} onHover={hover.set} />;
}

// ------------------------------------------------------------------------------------------------

function useVariants(v: View, grp: string) {
  const rows = useRows(v);
  return useMemo(() => {
    const recs = rows.filter((r) => r.group === grp && r.variant && !isHidden(r.model));
    return VARIANT_ORDER.map((vv) => recs.find((r) => r.variant === vv)).filter((r): r is Rec => !!r);
  }, [rows, grp]);
}

/** Model select + configuration multi-select for the Configurations page, rendered in the control bar. */
function VariantPicker({ v, grp, setGrp, off, setOff, explain }: { v: View; grp: string; setGrp: (g: string) => void; off: Set<string>; setOff: (s: Set<string>) => void; explain: (k: string) => void }) {
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useVariants(v, grp);
  const on = new Set(variants.filter((r) => !off.has(r.variant!)).map((r) => r.variant!));
  const groups: PickGroup[] = [{
    id: grp, label: G.label,
    items: variants.map((r) => ({
      id: r.variant!, label: VARIANT_LABEL[r.variant!] ?? r.variant!, title: r.lever ?? undefined,
      mark: <span className="sw" style={{ background: variantColor(r.variant!, G.recipe) }} />,
      suffix: <>{r.variant === G.recipe && <span className="star" title="optimized configuration: selected on the Veridian dev split">★</span>}{starOf(r) && <span className="sub" title={`scored on ${r.subset}`}>*</span>}</>,
      detail: () => explain(r.model),
    })),
  }];
  return (
    <>
      <Control label="Model">
        <span className="select">
          <select value={grp} onChange={(e) => { setGrp(e.target.value); setOff(new Set()); }}>
            {ABLATION_GROUPS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
          </select>
        </span>
      </Control>
      <Picker
        label="Configurations" summary={`${on.size} of ${variants.length}`} groups={groups} on={on}
        onChange={(next) => setOff(new Set(variants.map((r) => r.variant!).filter((vv) => !next.has(vv))))}
        onReset={() => setOff(new Set())}
        footer={<span className="pick-note">{G.note}</span>}
      />
    </>
  );
}

function AblationSection({ v, grp, off, explain }: { v: View; grp: string; off: Set<string>; explain: (k: string) => void }) {
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useVariants(v, grp);
  const sel = variants.filter((r) => !off.has(r.variant!));
  const color = (r: Rec) => variantColor(r.variant!, G.recipe);
  const name = (r: Rec) => VARIANT_LABEL[r.variant!] ?? r.variant!;
  const [chart, setChart] = useState<Chart>("ranked");

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    return { id: r.model, name: name(r), color: color(r), recall: p.recall, precision: p.precision, subset: starOf(r), sub: qualitySub(r, v) };
  });

  return (
    <section className="section">
      <HoverProvider>
        <div className={`dash${chart === "ranked" ? " ranked" : ""}`}>
          <PRCard
            items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={explain}
            emptyText={variants.length ? "Select at least one configuration." : "No configurations of this model were run on this corpus and arm."}
            logos={false}
            hint={CONFIG_PR_ITEMS}
          />
          <div className="stack"><OpsCards recs={sel} colorOf={color} nameOf={name} logos={false} explain={explain} /></div>
        </div>
      </HoverProvider>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------

type Page = "compare" | "configurations";
const PAGES: { id: Page; label: string }[] = [{ id: "compare", label: "Compare models" }, { id: "configurations", label: "Configurations of one model" }];

export default function App() {
  // The corpus is not persisted (hash or storage); siteCorpus still guards the state so an unlisted id (e.g. "veridian") can never render.
  const [corpus, setCorpusRaw] = useState(DEFAULT_CORPUS);
  const setCorpus = (c: string) => setCorpusRaw(siteCorpus(c));
  const [tag, setTag] = useState<"" | "v0">("");
  const [arm, setArm] = useState<"multi" | "single">("multi");
  const [gray, setGray] = useState<Gray>("all");
  const [level, setLevel] = useState<Level>("doc");
  const [issue, setIssue] = useState<string | null>(null);
  const v: View = { corpus, tag: corpus === "trec" ? tag : "", arm, gray, level, issue };
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];

  const pickCorpus = (c: string) => { setCorpus(c); setIssue(null); };
  const [explain, setExplain] = useState<string | null>(null);
  // The Method modal (how each experiment was run) opens from the header and foot buttons and from every hint's "Method" link, via MethodContext.
  const [method, setMethod] = useState(false);
  const openMethod = useCallback(() => setMethod(true), []);
  const closeMethod = useCallback(() => setMethod(false), []);
  const disclaimer = useDisclaimer(); // first-visit disclaimer; reopens from the footer
  const [on, setOn] = useState<Set<string>>(new Set(DEFAULT_ON));
  const [grp, setGrp] = useState("jev");
  const [off, setOff] = useState<Set<string>>(new Set());
  const corpusTitle = `${fmtInt(meta.n_docs)} documents · ${meta.n_issues} issues · ${fmtInt(meta.n_pos_docs_any)} responsive to at least one (${fmtPct(meta.n_pos_docs_any / meta.n_docs, 0)}) · gold: ${meta.gold}`;
  const [more, setMore] = useState(false);
  const nonDefault = [
    arm === "single" ? "one issue per call" : null,
    issue ? `issue: ${meta.issues[issue]}` : level === "decision" ? "every decision" : null,
    !issue && gray === "nogray" ? "gray excluded" : null,
  ].filter((x): x is string => !!x);
  const [theme, setTheme] = useState<"dark" | "light">(() => (localStorage.getItem("theme") as "dark" | "light") || "dark");
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("theme", theme); }, [theme]);
  const [pageId, setPageId] = useState<Page>(() => (location.hash === "#configurations" ? "configurations" : "compare"));
  useEffect(() => {
    const onHash = () => setPageId(location.hash === "#configurations" ? "configurations" : "compare");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const goPage = (p: Page) => { history.replaceState(null, "", p === "compare" ? "#compare" : "#configurations"); setPageId(p); window.scrollTo(0, 0); };

  const page = (
    <div className="page">
      <header className="masthead">
        <h1 className="title">LLMs v Deciders for Legal Document Review</h1>
        <nav className="tabs" aria-label="Pages">
          {PAGES.map((p) => (
            <button key={p.id} className={pageId === p.id ? "on" : ""} onClick={() => goPage(p.id)} aria-current={pageId === p.id ? "page" : undefined}>{p.label}</button>
          ))}
        </nav>
        <span className="theme"><MethodButton onClick={openMethod} /><Seg value={theme} onChange={setTheme} options={[{ id: "dark", label: "Dark" }, { id: "light", label: "Light" }]} /></span>
      </header>

      <div className="controls">
        <Control label="Corpus">
          <Seg value={corpus} onChange={pickCorpus} options={CORPORA.map((c) => ({ id: c.id, label: c.label, title: c.id === corpus ? corpusTitle : c.short }))} />
          <Hint title={meta.display} text={corpusTitle} />
        </Control>
        {pageId === "compare"
          ? <ModelPicker v={v} on={on} setOn={setOn} explain={setExplain} />
          : <VariantPicker v={v} grp={grp} setGrp={setGrp} off={off} setOff={setOff} explain={setExplain} />}
        {corpus === "trec" && (
          <Control label="Criteria">
            <Seg value={tag} onChange={setTag} options={[
              { id: "", label: "calibrated", title: "Criteria refined once on a 668-email calibration set disjoint from this evaluation set" },
              { id: "v0", label: "bare topic", title: "The NIST topic sentence as written, no iteration" },
            ]} />
          </Control>
        )}
        <span className="more-wrap">
          {!more && nonDefault.length > 0 && <span className="more-summary">{nonDefault.join(" · ")}</span>}
          <ExplainButton label={pageId === "compare" ? "how each model is asked" : "requests side by side"} onClick={() => setExplain(pageId === "compare" ? "jev@base" : `${grp}@base`)} />
          <button className={`more${more ? " on" : ""}`} onClick={() => setMore((m) => !m)} aria-expanded={more}>
            {more ? "Fewer options" : "More options"}<span className="chev" />
          </button>
        </span>
      </div>
      {more && (
      <div className="controls controls-more">
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
          <Hint title="Scope" items={[
            { k: "Document", v: <mark>A document is <b>responsive if it is positive for any issue</b>: the relevance call a review team makes.</mark> },
            { k: "Decision", v: <><b>Pools every (document, issue) judgment</b>.</> },
            { k: "Single issue", v: <><b>That issue's recall and precision on its own</b>, over all gold labels.</> },
          ]} />
        </Control>
        <Control label="Gold">
          <Seg value={issue ? "all" : gray} onChange={setGray} options={[
            { id: "all", label: "all labels" },
            { id: "nogray", label: "exclude gray", title: issue ? "Not available for a single issue" : "Drop decisions whose gold label was flagged as debatable" },
          ]} />
        </Control>
      </div>
      )}

      {pageId === "compare" ? <CompareSection v={v} on={on} explain={setExplain} /> : <AblationSection v={v} grp={grp} off={off} explain={setExplain} />}
      {explain && (
        <ExplainModal
          initialKey={explain} initialCorpus={corpus} onClose={() => setExplain(null)}
          metrics={(k, c) => metricsFor(k, c, v, (rows) => (pageId === "compare" ? rows.filter((r) => r.primary && on.has(r.model)) : rows.filter((r) => r.group === grp && !!r.variant && !isHidden(r.model) && !off.has(r.variant))))}
        />
      )}

      {method && <MethodModal onClose={closeMethod} />}
      {disclaimer.open && <DisclaimerModal onClose={disclaimer.close} />}

      <footer className="notes">
        <MethodButton onClick={openMethod} />
        <span className="notes-t">How each experiment was run: data sets, truth data, measurement.</span>
        <DisclaimerLink onClick={disclaimer.show} />
      </footer>
    </div>
  );
  return <MethodContext.Provider value={openMethod}>{page}</MethodContext.Provider>;
}
