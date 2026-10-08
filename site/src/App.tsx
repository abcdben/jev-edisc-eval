import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import {
  ABLATION_GROUPS, CORPORA, DATA, DEFAULT_CORPUS, SUGGESTED_ON, GPU_NAME, GPU_USD_PER_HOUR, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER, rosterOf,
  corpusKey, costPerDoc, displayMeta, fmtCI, fmtInt, fmtMs, fmtPct, fmtUSD, isDecider, isGpuRow, isHidden, issueLabel, paidPerDoc, pick, selectableRowsOf, siteCorpus, starOf, tarRowsOf, variantColor,
  type Gray, type Kind, type Level, type PRF, type Rec,
} from "./data";
import { Control, Hint, MethodContext, ROW_PULSE_MS, Seg, usePulseWindow, type HintItem, type TipLine } from "./components/ui";
import { PRScatter, type PRItem } from "./components/PRScatter";
import { PRRail, type RailMetric } from "./components/PRRail";
import { StatsRow } from "./components/CompareStats";
import { applyStats, nextSort, reviewerNotes, thresholdNotes, useSiteStats, type Sort, type Stats, type StatsApplied } from "./compareStats";
import { PUBLISHED, applyReviewer, fmtRate, type ReviewerSetting } from "./tarGrid";
import { compareName, movedName, tarName, tarOption, type TarOption } from "./tarNames";
import { PRHeat } from "./components/PRHeat";
import { OpsBars, type BarItem } from "./components/OpsBars";
import { Consistency, detFor, detLines } from "./components/Consistency";
import { TarDepthCharts } from "./components/TarDepthCharts";
import { HoverProvider, useHover } from "./components/hover";
import { ExplainModal, type MetricSection, type Metrics } from "./components/Explain";
import { Picker, type PickGroup } from "./components/Picker";
import { DisclaimerLink, DisclaimerModal, useDisclaimer } from "./components/Disclaimer";
import { Logo } from "./logos";
import { THEME_KEY, THEME_OPTIONS, readTheme, type Theme } from "./theme";
import { SeriesColorControl, useSeriesColors } from "./seriesColors";
import { TradeoffPicker, TradeoffSection } from "./Tradeoff";

/** The prompt a chart shows while nothing is selected (every page opens with nothing selected). */
export const CHOOSE_MODELS = "Choose models to compare.";

/** The recall/precision card's views. `ranked` is drawn by PRRail on Compare models (rank rail) and by PRHeat on Compare configurations (vs default), chosen by PRCard's `ranked` prop. */
export type Chart = "map" | "ranked";

/** Short group names for the one-line picker. */
/** Picker order: decision models first, then the LLMs (API and local share one group via the PRIMARY `kind` override), then classical TAR. Kinds with no roster member (`baseline`, `local_llm`) are dropped before rendering. */
const PICK_ORDER: Kind[] = ["system1", "system1_ft", "baseline", "llm", "local_llm", "tar"];
const KIND_SHORT: Record<Kind, string> = { system1: "Decision models", system1_ft: "Supervised", llm: "LLM", local_llm: "Local LLM", tar: "Classical TAR", baseline: "Floor" };


/** Recall/precision card with a map (scatter with interval boxes) or ranked (rows with whiskers) view. The chart mode is owned by the section so it can switch the dashboard layout. `explain` opens the details modal for a clicked mark or row (item ids are model keys). */
/** `pulse` (Compare models only: the Configurations page shows one family, so no decider to single out) lets the deciders' interval boxes breathe for a few cycles when the map loads or its points change. */
/** `ranked` picks the ranked view's component: `rail` (PRRail, Compare models) or `heat` (PRHeat, Compare configurations, differenced against `referenceId`, the family's base configuration). Both draw their own legend line. */
/** `sig` names what the card is showing (the corpus, and the family on Configurations): the `ranked` option's accent (ui.tsx Seg `accent`) breathes once when the card mounts and again whenever it changes, not on every model toggle. */
/** `sort` (Compare models: the Statistics row's order, compareStats.ts) turns the rail's F1 column on and its Recall / Precision / F1 headers into sort controls; `notes` are caption lines under either view (the threshold and reviewer notes). */
export function PRCard({ items, chart, onChart, defaultZoom, emptyText, logos = true, height = 380, explain, pulse = false, ranked, referenceId, sig = "card", seriesKey, sort, notes = [] }: { items: PRItem[]; chart: Chart; onChart: (c: Chart) => void; defaultZoom: boolean; emptyText?: string; logos?: boolean; height?: number; explain?: (k: string) => void; pulse?: boolean; ranked: "rail" | "heat"; referenceId?: string; sig?: string; seriesKey?: ReactNode; sort?: { value: Sort; onSort: (by: RailMetric) => void }; notes?: string[] }) {
  const setChart = onChart;
  const [zoom, setZoom] = useState(defaultZoom);
  const onSelect = explain && ((it: PRItem) => explain(it.id));
  const hover = useHover();
  const rowProps = { items, zoom, sortBy: "recall" as const, logos, onSelect, highlight: hover.id, onHover: hover.set };
  // the rail with the Statistics row's sort: the F1 column on, the headers clickable (PRRail.tsx); without one, the plain recall-ranked rail
  const railProps = sort ? { ...rowProps, f1: true, sortBy: sort.value.by, sortDir: sort.value.dir, onSort: sort.onSort } : rowProps;
  const accentPulse = usePulseWindow(sig, true, ROW_PULSE_MS);
  const options: { id: Chart; label: string; title?: string; accent?: boolean }[] = [
    { id: "map", label: "map", title: "Recall against precision, one box per model" },
    { id: "ranked", label: "ranked", title: ranked === "heat" ? "Rows sorted by recall, each value differenced against the Default configuration" : "Rows sorted by recall, whiskers for the intervals", accent: true },
  ];
  return (
    <div className={`card${chart === "map" ? " fill" : ""}`}>
      <div className="card-t">
        <h3>Recall and precision</h3>
        <span className="right">
          <Seg value={chart} onChange={setChart} options={options} pulse={accentPulse} />
          <Seg value={zoom ? "zoom" : "full"} onChange={(z) => setZoom(z === "zoom")} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }]} />
        </span>
      </div>
      {chart === "map" && <div className="chart-fill" style={{ minHeight: height }}><PRScatter items={items} zoom={zoom} emptyText={emptyText} logos={logos} fill onSelect={onSelect} highlight={hover.id} onHover={hover.set} pulse={pulse} labels={seriesKey ? "none" : "beside"} /></div>}
      {/* the ranked views draw rows only: with nothing selected the prompt stands in for them */}
      {chart === "ranked" && !items.length && <div className="tradeoff-empty">{emptyText ?? CHOOSE_MODELS}</div>}
      {chart === "ranked" && items.length > 0 && ranked === "rail" && <PRRail {...railProps} />}
      {chart === "ranked" && items.length > 0 && ranked === "heat" && <PRHeat {...rowProps} referenceId={referenceId} />}
      {seriesKey}
      {chart === "map" && (
        <div className="legend-note">
          <span>Dot: point estimate. Shaded box: 95% interval on recall (width) and precision (height).</span>
          {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
          {notes.map((t, i) => <span key={i}>{t}</span>)}
        </div>
      )}
      {chart === "ranked" && notes.length > 0 && <div className="legend-note">{notes.map((t, i) => <span key={i}>{t}</span>)}</div>}
    </div>
  );
}

export type View = { corpus: string; tag: string; arm: "multi" | "single"; gray: Gray; level: Level; issue: string | null };

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
  if (r.lever && !r.primary) notes.push(r.lever);
  return { lines, notes };
}

/** The model's median per-document latency (ms) and dollars per 100k documents; null when not measured. */
function opsValues(r: Rec): { ms: number | null; usd: number | null } {
  const c = costPerDoc(r);
  return { ms: r.ops.doc_latency_p50_ms, usd: c == null ? null : c * 1e5 };
}

/** The export's `latency_source` as a short phrase for the hover; null for a source the site does not describe. */
function latencySource(s: string): string | null {
  if (s === "per-call latency from the main run") return "per-request timing from the benchmark run, 8–12 requests in flight";
  if (/same forward pass/.test(s)) return "same forward pass as the zero-shot Laya recipe";
  const m = /^dedicated concurrency-1 sample of (\d+) documents(.*)$/.exec(s);
  if (m) {
    const tier = /on the standard tier/.test(m[2]) ? " · OpenAI standard tier (the run used flex, which was slower)" : /on the flex tier/.test(m[2]) ? " · OpenAI flex tier, as run (standard was no faster)" : "";
    return `dedicated single-request sample of ${fmtInt(Number(m[1]))} documents${tier}`;
  }
  if (/concurrency-1/.test(s)) return "dedicated single-request sample";
  return null;
}

/** The one secondary line of an Inference latency or Cost hover: the p95 and how the latency was measured, or the cost basis (list price; what the run paid when a discount applied). */
function opsSub(r: Rec, kind: "latency" | "cost"): string {
  if (kind === "latency") return [`p95 ${fmtMs(r.ops.doc_latency_p95_ms)}`, latencySource(r.ops.latency_source)].filter(Boolean).join(" · ");
  if (isGpuRow(r)) return "A100 rental for the measured time";
  const paid = paidPerDoc(r);
  return paid ? `standard list price · as paid ${fmtUSD(paid.usd * 1e5)} (${paid.mode})` : "standard list price · API";
}

function opsLines(r: Rec): { lines: TipLine[]; notes: string[] } {
  const o = r.ops;
  const c = costPerDoc(r);
  const lines: TipLine[] = [
    ["Median latency", fmtMs(o.doc_latency_p50_ms)],
    ["p95 latency", fmtMs(o.doc_latency_p95_ms)],
    ["Cost per 100k docs", c == null ? "—" : fmtUSD(c * 1e5)],
    ["Cost per document", c == null ? "—" : c === 0 ? "$0" : `$${c.toFixed(c < 0.001 ? 5 : 4)}`],
    ["Input tokens per document", o.tokens_in_per_doc == null ? "—" : fmtInt(Math.round(o.tokens_in_per_doc))],
    ["Output tokens per document", o.tokens_out_per_doc == null ? "—" : fmtInt(Math.round(o.tokens_out_per_doc))],
  ];
  const paid = paidPerDoc(r);
  if (paid) lines.push(["As paid per 100k docs", `${fmtUSD(paid.usd * 1e5)} (${paid.mode})`]);
  const notes: string[] = [];
  const src = latencySource(o.latency_source);
  if (src) notes.push(`Latency: ${src}.`);
  if (!isGpuRow(r) && c != null) notes.push(`Cost is the standard list price of the tokens used, no flex, batch or caching discount${paid ? `; the run itself paid ${fmtUSD(paid.usd * 1e5)} per 100k docs on ${paid.mode}` : ""}.`);
  if (isGpuRow(r) && c != null) notes.push(`Cost is rented GPU time: ${GPU_NAME} at $${GPU_USD_PER_HOUR.toFixed(2)}/h for the median latency, one request at a time; serving documents concurrently would lower it.`);
  if (r.model === "laya-ft") notes.push("The labeled training data this checkpoint needed is not counted here.");
  return { lines, notes };
}

/**
 * Everything the details modal's Metrics block lists for one row on one corpus: the recall/precision, inference latency and cost, and determinism
 * facts that the chart tooltips used to carry. `shown` picks the page's selection out of the corpus rows, the referent of "vs. lowest shown".
 */
function metricsFor(key: string, corpus: string, v: View, shown: (rows: Rec[]) => Rec[]): Metrics | null {
  const tag = corpus === "trec" ? v.tag : "";
  const rows = DATA.records.filter((r) => r.corpus === corpus && r.tag === tag && r.arm === v.arm);
  const r = rows.find((x) => x.model === key);
  if (!r) return null;
  const vv: View = { ...v, corpus, tag, issue: corpus === v.corpus ? v.issue : null };
  const meta = DATA.corpora[corpusKey(corpus, tag)];
  const group = ABLATION_GROUPS.find((g) => g.id === r.group);
  const name = PRIMARY_BY_KEY[r.model]?.short ?? (r.variant ? `${group?.label ?? r.family} · ${VARIANT_LABEL[r.variant] ?? r.variant}` : r.name);
  const color = PRIMARY_BY_KEY[r.model]?.color ?? (r.variant ? variantColor(r.variant, group?.recipe ?? "") : "var(--ink)");
  const scope = vv.issue ? issueLabel(meta, vv.issue) : vv.level === "decision" ? "every decision" : "document level";
  const context = [meta.display, vv.arm === "single" ? "one issue per call" : "all issues per call", scope, !vv.issue && vv.gray === "nogray" ? "gray excluded" : null].filter(Boolean).join(" · ");
  const q = qualityLines(r, vv);
  const o = opsLines(r);
  const peers = shown(rows);
  const lowest = (f: (x: Rec) => number | null) => { const vals = peers.map(f).filter((x): x is number => x != null && x > 0); return vals.length ? Math.min(...vals) : null; };
  const ratio = (label: string, val: number | null, best: number | null): TipLine[] => {
    if (val == null || !best || val / best <= 1.05) return [];
    const k = val / best;
    return [[label, `${k >= 10 ? Math.round(k) : k.toFixed(1)}×`]];
  };
  const mine = opsValues(r);
  const sections: MetricSection[] = [
    { title: "Recall and precision", lines: q.lines, notes: q.notes },
    {
      title: "Speed and cost",
      lines: [...o.lines, ...ratio("Latency vs. fastest shown", mine.ms, lowest((x) => opsValues(x).ms)), ...ratio("Cost vs. cheapest shown", mine.usd, lowest((x) => opsValues(x).usd))],
      notes: o.notes,
    },
  ];
  const det = detFor(r, vv.arm, "default"), t0 = detFor(r, vv.arm, "t0");
  if (det) { const d = detLines(det, r, name); sections.push({ title: "Stability", lines: d.lines, notes: d.notes }); }
  if (t0) { const d = detLines(t0, r, name); sections.push({ title: "Stability · temperature 0", lines: d.lines, notes: d.notes }); }
  return { name, color, context, sections };
}

// ------------------------------------------------------------------------------------------------

/** The records the page plots for the view; keys data.ts hides (isHidden) are left out. */
function useRows(v: View) {
  return useMemo(() => DATA.records.filter((r) => r.corpus === v.corpus && r.tag === v.tag && r.arm === v.arm && (!isHidden(r.model) || r.model.startsWith("tar@"))), [v.corpus, v.tag, v.arm]);
}

/** The Speed and Cost hints: machine time and price only. */
export const LATENCY_ITEMS: HintItem[] = [
  { k: "Measures", v: <><b>Median wall-clock per request to score one document</b>: one call in the all-issues arm, the sum over issues in the one-issue arm.</> },
  { k: "Source", v: <><b>TREC, all issues per call, Jev / OpenAI Decisions / Claude / GPT rows</b>: a dedicated single-request sample of 200 emails. Every other cell: per-request timings recorded during the benchmark run, <b>8–12 requests in flight</b>. Each row's details say which.</> },
  { k: "Hosted", v: <>Includes network. <b>Rate limits and parallel throughput not measured.</b> GPT-5.6 Luna is timed on OpenAI's standard tier (2.2× faster than the flex tier the run used, same sample); Terra on flex (standard was no faster). Cost is at list either way.</> },
  { k: "Local", v: <>Laya and Gemma on <b>one A100</b>; no network.</> },
];
/** What a document is on each corpus, for the Cost hint's basis line. */
const DOC_NOUN: Record<string, string> = { trec: "email", mnk: "email" };
/**
 * The Cost hint for the rows the card shows: the per-100k basis, then the mean billed tokens per document across the shown LLM rows
 * (the corpus's average document length in each vendor's tokenizer), so the numbers follow the corpus and the selection.
 */
export function costItems(recs: Rec[]): HintItem[] {
  const llm = recs.filter((r) => (r.kind === "llm" || r.kind === "local_llm") && r.ops.tokens_in_per_doc != null);
  const mean = (f: (r: Rec) => number | null) => { const v = llm.map(f).filter((x): x is number => x != null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  const tin = mean((r) => r.ops.tokens_in_per_doc), tout = mean((r) => r.ops.tokens_out_per_doc);
  const noun = DOC_NOUN[recs[0]?.corpus ?? ""] ?? "document";
  const tokens = tin == null ? null : `${fmtInt(Math.round(tin / 100) * 100)} in / ${fmtInt(Math.max(10, Math.round((tout ?? 0) / 10) * 10))} out`;
  return [
    { k: "Measures", v: <><b>Standard list price</b> of the tokens used × 100,000 documents.</> },
    { k: "Basis", v: <>This corpus's average billed tokens per {noun}{tokens ? <>: <b>≈{tokens}</b> for the LLMs</> : null}.</> },
    { k: "Pricing", v: <>Every API model at list: <b>no flex, batch or caching discounts</b>. Hover a bar for what the run paid.</> },
    { k: "Local", v: <mark>Laya and Gemma: A100 rental at ${GPU_USD_PER_HOUR.toFixed(2)}/h × measured time, <b>an upper bound</b>.</mark> },
  ];
}

/**
 * `decider` sets a row's name a step heavier (data.ts isDecider); Compare models passes it, the Configurations page (one family per chart) does not.
 * `emphasis` picks the rows that carry the faint --hl tint (Compare models: the decision models, Jev and Laya; the Configurations page passes nothing, its base row looks like the others).
 */
function OpsCards({ recs, colorOf, nameOf, logos = true, explain, decider, emphasis }: { recs: Rec[]; colorOf: (r: Rec) => string; nameOf: (r: Rec) => string; logos?: boolean; explain?: (k: string) => void; decider?: (r: Rec) => boolean; emphasis?: (r: Rec) => boolean }) {
  const onSelect = explain && ((it: BarItem) => explain(it.id));
  const hover = useHover();
  const latency: BarItem[] = recs.map((r) => {
    const { ms } = opsValues(r);
    return { id: r.model, name: nameOf(r), color: colorOf(r), value: ms, label: fmtMs(ms), sub: opsSub(r, "latency"), subset: starOf(r), decider: decider?.(r), emphasis: emphasis?.(r) };
  });
  const cost: BarItem[] = recs.map((r) => {
    const { usd } = opsValues(r);
    return { id: r.model, name: nameOf(r), color: colorOf(r), value: usd, label: fmtUSD(usd), sub: opsSub(r, "cost"), subset: starOf(r), decider: decider?.(r), emphasis: emphasis?.(r) };
  });
  return (
    <>
      <div className="card">
        <div className="card-t">
          <h3>Speed</h3><span className="unit">median latency per document</span>
          <span className="right"><Hint items={LATENCY_ITEMS} more="About" /></span>
        </div>
        <OpsBars items={latency} axis="milliseconds" unit="per document, median" logos={logos} onSelect={onSelect} highlight={hover.id} onHover={hover.set} emptyText={CHOOSE_MODELS} />
      </div>
      <div className="card">
        <div className="card-t">
          <h3>Cost</h3><span className="unit">per 100k docs</span>
          <span className="right"><Hint items={costItems(recs)} more="About" /></span>
        </div>
        <OpsBars items={cost} axis="US dollars" unit="per 100k docs" logos={logos} onSelect={onSelect} highlight={hover.id} onHover={hover.set} emptyText={CHOOSE_MODELS} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------------------------------------

/** A headline row's kind for grouping: the roster's override (Laya's fine-tuned row sits with the deciders) or the record's own. */
const kindOf = (r: Rec): Kind => PRIMARY_BY_KEY[r.model]?.kind ?? (r.kind as Kind);

/** The model multi-select for Compare models, rendered in the control bar (also used by the screenshot studio, Studio.tsx). */
export function ModelPicker({ v, on, setOn, explain }: { v: View; on: Set<string>; setOn: (s: Set<string>) => void; explain?: (k: string) => void }) {
  const rows = useRows(v);
  const { colorOf, setColor } = useSeriesColors();
  const primary = rosterOf(rows).filter((r) => !r.model.startsWith("tar@"));
  const byKind = PICK_ORDER.map((k) => ({ kind: k, recs: primary.filter((r) => kindOf(r) === k) })).filter((g) => g.recs.length);
  const avail = primary.filter((r) => on.has(r.model)).length;
  const groups: PickGroup[] = byKind.map((g) => ({
    id: g.kind, label: KIND_SHORT[g.kind as Kind],
    items: g.recs.map((r) => {
      const m = PRIMARY_BY_KEY[r.model];
      return { id: r.model, label: m.short, title: m.note, mark: <span style={{ color: m.color }}><Logo model={r.model} /></span>, suffix: starOf(r) ? <span className="sub" title={`scored on ${r.subset}`}>*</span> : undefined, detail: explain ? () => explain(r.model) : undefined, accent: isDecider(kindOf(r)) ? m.color : undefined };
    }),
  }));
  // the curated set (data.ts SUGGESTED_ON), the picker's "Suggested set" button; the page itself opens with nothing selected
  const suggest = () => {
    const next = new Set([...on].filter((k) => k.startsWith("tar@")));
    SUGGESTED_ON.forEach((k) => { if (!k.startsWith("tar@")) next.add(k); });
    setOn(next);
  };
  const selected = primary.filter((r) => on.has(r.model));
  return <Picker label="Models" summary={avail ? `${avail} of ${primary.length}` : "None selected"} groups={groups} on={on} onChange={setOn} onReset={suggest}
    selected={selected.length ? <><span className="pick-selected-lab">Selected</span><div className="series-selected">
      {selected.map((r) => {
        const meta = displayMeta(r.model, r);
        return <div className="series-selected-row" key={r.model}><SeriesColorControl id={r.model} color={colorOf(r.model, meta.color)} onColor={setColor} label={meta.short} /><span>{meta.short}</span><button type="button" onClick={() => { const next = new Set(on); next.delete(r.model); setOn(next); }} aria-label={`Remove ${meta.short}`}>×</button></div>;
      })}
    </div></> : undefined} />;
}

type TarWorkflow = "t1" | "cal";
type TarSampling = "random" | "diversity";
type TarAccuracy = "60" | "70" | "80" | "90" | "perfect";
type CalStop = "target80" | "target75" | "knee";
const ACCURACY_OPTIONS: { id: TarAccuracy; label: string }[] = [
  { id: "60", label: "60%" }, { id: "70", label: "70%" }, { id: "80", label: "80%" }, { id: "90", label: "90%" }, { id: "perfect", label: "Perfect" },
];

/** TAR workflow builder: independent variables resolve to an existing result key; selected combinations remain a multi-select comparison. */
/** `reviewer` is the Statistics row's TAR reviewer setting (compareStats.ts): off `published`, the foot note states the rates the selected gridded workflows are re-run at instead of the published runs' rule. */
export function TarPicker({ v, on, setOn, reviewer = PUBLISHED }: { v: View; on: Set<string>; setOn: (s: Set<string>) => void; reviewer?: ReviewerSetting }) {
  const rows = useRows(v);
  const { colorOf, setColor } = useSeriesColors();
  const options = tarRowsOf(rows).map((r) => tarOption(r));
  // the rates the Statistics row's reviewer sliders put the selected gridded workflows at (tarGrid.ts applyReviewer snaps to the grid), the selected ones no grid can move,
  // and each selected workflow's name under them (tarNames.ts movedName: the applied rates and a ‡ where they are not the published run's)
  const rev = useMemo(() => {
    const selected = options.filter((x) => on.has(x.row.model)).map((x) => x.row);
    const a = applyReviewer(selected, reviewer);
    const snapped = a.moved.size ? [...a.moved.values()][0] : null;
    const nameOf = (x: TarOption) => { const m = a.moved.get(x.row.model); return m && a.offPublished.includes(x.row.model) ? movedName(x.row, m) : tarName(x); };
    return { snapped, nameOf, fixed: a.fixed.map((m) => { const o = options.find((x) => x.row.model === m); return o ? tarName(o) : m; }) };
  }, [options, on, reviewer]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!options.length) return null;
  const sizes = [...new Set(options.flatMap((x) => x.n == null ? [] : [x.n]))].sort((a, b) => a - b);
  const ids = new Set(options.map((x) => x.row.model));
  const suggested = new Set([...SUGGESTED_ON].filter((k) => ids.has(k)));
  const selectedOptions = options.filter((x) => on.has(x.row.model));
  const isSuggested = selectedOptions.length === suggested.size && selectedOptions.every((x) => suggested.has(x.row.model));
  const [open, setOpen] = useState(false);
  const [workflow, setWorkflow] = useState<TarWorkflow>("t1");
  const [depth, setDepth] = useState(() => sizes.includes(1000) ? 1000 : sizes[0]);
  const [sampling, setSampling] = useState<TarSampling>(() => ids.has("tar@t1_1000_div") ? "diversity" : "random");
  const [accuracy, setAccuracy] = useState<TarAccuracy>("perfect");
  const [calStop, setCalStop] = useState<CalStop>("target80");
  const [calAccuracy, setCalAccuracy] = useState<"90" | "perfect">("90");
  const wrapRef = useRef<HTMLSpanElement>(null), buttonRef = useRef<HTMLButtonElement>(null), id = useId();

  useEffect(() => {
    if (sizes.includes(depth)) return;
    setDepth(sizes.includes(1000) ? 1000 : sizes[0]);
  }, [sizes.join(","), depth]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (!open) return;
    const outside = (e: PointerEvent) => { if (!wrapRef.current?.contains(e.target as Node)) setOpen(false); };
    const key = (e: KeyboardEvent) => { if (e.key === "Escape") { setOpen(false); buttonRef.current?.focus(); } };
    document.addEventListener("pointerdown", outside); document.addEventListener("keydown", key);
    return () => { document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", key); };
  }, [open]);

  const t1Key = (n: number, sample: TarSampling, acc: TarAccuracy) =>
    `tar@t1_${n}${acc === "perfect" ? "" : `_acc${acc}`}${sample === "diversity" ? "_div" : ""}`;
  const calKey = (stop: CalStop, acc: "90" | "perfect") =>
    stop === "knee" ? "tar@cal_knee" : stop === "target75" ? "tar@cal_75" : acc === "perfect" ? "tar@cal_perfect" : "tar@cal";
  const candidate = workflow === "t1" ? t1Key(depth, sampling, accuracy) : calKey(calStop, calAccuracy);
  const candidateExists = ids.has(candidate);
  const candidateSelected = on.has(candidate);
  const add = () => { if (!candidateExists || candidateSelected) return; const next = new Set(on); next.add(candidate); setOn(next); };
  // the curated TAR pair (data.ts SUGGESTED_ON), the "Suggested set" button; the page opens with no TAR workflow selected
  const suggest = () => {
    const next = new Set([...on].filter((k) => !k.startsWith("tar@")));
    SUGGESTED_ON.forEach((k) => { if (ids.has(k)) next.add(k); });
    setOn(next);
  };
  const remove = (id: string) => { const next = new Set(on); next.delete(id); setOn(next); };
  return (
    <span ref={wrapRef} className={`pick-wrap tar-build${open ? " open" : ""}`}>
      <button ref={buttonRef} className="pick-btn" onClick={() => setOpen((x) => !x)} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined}>
        <span className="pick-lab">TAR workflows</span>
        <span className="pick-sum">{selectedOptions.length ? `${selectedOptions.length} selected${isSuggested ? " · suggested set" : ""}` : "None selected"}</span>
        <span className="chev" />
      </button>
      {open && (
        <div id={id} className="pick-pop tar-build-pop" role="dialog" aria-label="Build TAR workflow">
          <div className="pick-head">
            <div className="pick-head-copy"><strong>Build a TAR workflow</strong><span>Choose each variable independently, then add the matching completed run to the comparison.</span></div>
            <button type="button" className="pick-close" onClick={() => { setOpen(false); buttonRef.current?.focus(); }} aria-label="Close TAR workflow builder">×</button>
            <div className="pick-selected" aria-live="polite">
              <span className="pick-selected-lab">Selected</span>
              {selectedOptions.length ? <div className="series-selected">
                {selectedOptions.map((x) => {
                  const name = rev.nameOf(x), fallback = displayMeta(x.row.model, x.row).color;
                  return <div className="series-selected-row" key={x.row.model}><SeriesColorControl id={x.row.model} color={colorOf(x.row.model, fallback)} onColor={setColor} label={name} /><span>{name}</span><button type="button" onClick={() => remove(x.row.model)} aria-label={`Remove ${name}`}>×</button></div>;
                })}
              </div> : <span className="pick-empty">No TAR workflow is currently shown.</span>}
            </div>
          </div>
          <div className="tar-build-body">
            <div className="tar-build-field"><span>Workflow</span><Seg value={workflow} onChange={setWorkflow} options={[{ id: "t1", label: "TAR 1.0" }, { id: "cal", label: "CAL / TAR 2.0" }]} /></div>
            {workflow === "t1" ? (
              <>
                <label className="tar-build-field"><span>Review depth</span><span className="select"><select value={depth} onChange={(e) => setDepth(Number(e.target.value))}>{sizes.map((n) => <option value={n} key={n}>{fmtInt(n)} documents</option>)}</select></span></label>
                <div className="tar-build-field"><span>Sampling</span><Seg value={sampling} onChange={setSampling} options={[{ id: "random", label: "Random" }, { id: "diversity", label: "Diversity" }]} /></div>
                <div className="tar-build-field wide"><span>Relevant-document coding accuracy</span><Seg value={accuracy} onChange={setAccuracy} options={ACCURACY_OPTIONS} /></div>
              </>
            ) : (
              <>
                <div className="tar-build-field"><span>Target / stop rule</span><Seg value={calStop} onChange={(x) => { setCalStop(x); if (x !== "target80") setCalAccuracy("90"); }} options={[{ id: "target80", label: "80% target" }, { id: "target75", label: "75% target" }, { id: "knee", label: "Knee stop" }]} /></div>
                <div className="tar-build-field"><span>Relevant-document coding accuracy</span><Seg value={calAccuracy} onChange={setCalAccuracy} options={calStop === "target80" ? [{ id: "90", label: "90%" }, { id: "perfect", label: "Perfect" }] : [{ id: "90", label: "90%" }]} /></div>
              </>
            )}
            <div className="tar-build-add">
              <div><b>{candidateExists ? tarName(options.find((x) => x.row.model === candidate)!) : "No completed run"}</b><span>{candidateExists ? "Existing benchmark result" : "This combination was not simulated."}</span></div>
              <button type="button" onClick={add} disabled={!candidateExists || candidateSelected}>{candidateSelected ? "Selected" : candidateExists ? "Add to comparison" : "Unavailable"}</button>
            </div>
          </div>
          <div className="pick-foot">
            <button type="button" onClick={suggest}>Suggested set</button>
            <button type="button" onClick={() => { const next = new Set([...on].filter((k) => !k.startsWith("tar@"))); setOn(next); }}>Clear TAR</button>
            <span className="pick-foot-r"><span className="pick-note">
              {rev.snapped
                ? `Percentages are the published runs' relevant-document coding accuracy, not overall agreement. The Statistics row's reviewer sliders currently re-run the selected workflows at a ${fmtRate(rev.snapped.fn)} miss rate and a ${fmtRate(rev.snapped.fp)} non-relevant false-positive rate${rev.fixed.length ? ` (${rev.fixed.join(", ")}: no grid for this corpus, fixed at the published run)` : ""}.`
                : "Percentages are relevant-document coding accuracy, not overall agreement. The non-relevant false-positive rate is one-fifth of the miss rate."}
            </span></span>
          </div>
        </div>
      )}
    </span>
  );
}

// the decider marker (data.ts isDecider: heavier name on rows) on every chart of Compare models, by the roster's kind (Laya's fine-tuned row is grouped with the deciders)
const decider = (r: Rec) => isDecider(kindOf(r));
// the emphasised rows on Compare models' tables (ui.tsx RowTint, the --hl tint): the decision models, Jev and Laya, by the same kind rule as `decider`
const emphasis = (r: Rec) => isDecider(kindOf(r));

/** The Compare models selection on a view: the roster rows that are switched on, and the recall/precision items drawn for them (shared with Studio.tsx). */
export function useCompareItems(v: View, on: Set<string>): { sel: Rec[]; items: PRItem[] } {
  const rows = useRows(v);
  const { colors } = useSeriesColors();
  return useMemo(() => {
    const sel = selectableRowsOf(rows).filter((r) => on.has(r.model));
    const items: PRItem[] = sel.map((r) => {
      const p = pick(r, v.level, v.gray, v.issue);
      const meta = displayMeta(r.model, r);
      return { id: r.model, name: compareName(r), color: colors[r.model] ?? meta.color, recall: p.recall, precision: p.precision, dashed: r.kind === "system1_ft", subset: starOf(r), sub: qualitySub(r, v), decider: decider(r), emphasis: emphasis(r) };
    });
    return { sel, items };
  }, [rows, on, v, colors]);
}

function ComparisonKey({ items, on, setOn }: { items: PRItem[]; on: Set<string>; setOn: (s: Set<string>) => void }) {
  const { setColor } = useSeriesColors();
  if (!items.length) return null;
  return <div className="comparison-key" aria-label="Comparison series key"><span className="comparison-key-title">Series key</span>
    <div>{items.map((item) => <div className="comparison-key-row" key={item.id}>
      <SeriesColorControl id={item.id} color={item.color} onColor={setColor} label={item.name} />
      <span title={item.name}>{item.name}</span>
      <button type="button" onClick={() => { const next = new Set(on); next.delete(item.id); setOn(next); }} aria-label={`Remove ${item.name}`}>×</button>
    </div>)}</div>
  </div>;
}

/** What the page shell hands its Compare models section: the view, the model selection, the details-modal opener and the Statistics setting (compareStats.ts) with its updater. */
export type CompareProps = { v: View; on: Set<string>; explain: (k: string) => void; setOn?: (s: Set<string>) => void; stats: Stats; setStats: (p: Partial<Stats>) => void };

/**
 * The Compare models selection under the Statistics row's setting (compareStats.ts applyStats): the published items re-cut at the threshold and the
 * TAR rows re-pointed by the reviewer, every item with its F1; at the defaults the published figures exactly. With the caption lines that name what
 * moved, and the header-click sort handler. Shared by both Compare sections (App.tsx CompareSection, AppB.tsx CompareTabs).
 */
export function useStatsItems(v: View, on: Set<string>, stats: Stats, setStats: (p: Partial<Stats>) => void): StatsApplied & { selPublished: Rec[]; notes: string[]; onSort: (by: RailMetric) => void } {
  const { sel: selPublished, items: ownItems } = useCompareItems(v, on);
  const applied = useMemo(() => applyStats(ownItems, selPublished, v, stats.threshold, stats.tarReviewer), [ownItems, selPublished, v, stats.threshold, stats.tarReviewer]);
  const notes = useMemo(() => [...thresholdNotes(applied, stats.threshold), ...reviewerNotes(applied, stats.tarReviewer)], [applied, stats.threshold, stats.tarReviewer]);
  const onSort = (by: RailMetric) => setStats({ sort: nextSort(stats.sort, by) });
  return { ...applied, selPublished, notes, onSort };
}

function CompareSection({ v, on, explain, setOn, stats, setStats }: CompareProps) {
  const rows = useRows(v);
  const st = useStatsItems(v, on, stats, setStats);
  const { sel, items } = st;
  const { colorOf } = useSeriesColors();
  // the Stability card keeps the published run's name (the grid does not reach it); on the cards the grid does reach (Cost, Speed) a row off its published
  // rates is named by the applied cell's rates with a ‡ (tarNames.ts movedName), as the recall/precision items are (compareStats.ts applyStats)
  const publishedName = (r: Rec) => compareName(st.selPublished.find((x) => x.model === r.model) ?? r);
  const gridName = (r: Rec) => { const m = st.applied.moved.get(r.model); return m && st.applied.offPublished.includes(r.model) ? movedName(r, m) : publishedName(r); };
  const [chart, setChart] = useState<Chart>("map");
  const manyTar = items.filter((x) => x.id.startsWith("tar@")).length >= 12;
  const wasManyTar = useRef(manyTar);
  useEffect(() => {
    if (manyTar && !wasManyTar.current) setChart("ranked");
    wasManyTar.current = manyTar;
  }, [manyTar]);

  return (
    <section className="section">
      {/* the Statistics row (components/CompareStats.tsx): the threshold, the TAR reviewer and the ranked view's sort, above the charts they move */}
      <StatsRow stats={stats} set={setStats} applied={st} ranked={chart === "ranked"} />
      {manyTar && <div className="tar-chart-note" role="status"><b>Dense TAR comparison.</b> Ranked view keeps workflow names and confidence intervals readable; you can still switch back to the map.</div>}
      <HoverProvider>
        <div className={`dash${chart !== "map" ? " ranked" : ""}`}>
          <PRCard
            items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={(k) => { if (!k.startsWith("tar@")) explain(k); }} emptyText={CHOOSE_MODELS}
            pulse ranked="rail" sig={v.corpus} sort={{ value: stats.sort, onSort: st.onSort }} notes={st.notes}
            seriesKey={setOn ? <ComparisonKey items={items} on={on} setOn={setOn} /> : undefined}
          />
          <div className="stack">
            <OpsCards recs={sel} colorOf={(r) => colorOf(r.model, displayMeta(r.model, r).color)} nameOf={gridName} explain={(k) => { if (!k.startsWith("tar@")) explain(k); }} decider={decider} emphasis={emphasis} />
            <ConsistencyCard recs={sel} colorOf={(r) => colorOf(r.model, displayMeta(r.model, r).color)} nameOf={publishedName} arm={v.arm} onSelect={(r) => { if (!r.model.startsWith("tar@")) explain(r.model); }} emphasis={emphasis} emptyText={CHOOSE_MODELS} />
          </div>
        </div>
        <TarDepthCharts rows={rows} />
      </HoverProvider>
    </section>
  );
}

/** The Stability card wired to the section's cross-chart hover (hover.tsx). */
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

/** The prompt the Configurations page shows while nothing is selected. */
const CHOOSE_CONFIGS = "Choose configurations to compare.";

/**
 * Model select + configuration multi-select for the Configurations page, rendered in the control bar. The family's configurations are listed in the
 * same dropdown idiom as Compare models' picker (components/Picker.tsx), each with its colour; `on` holds the configurations shown, by model key, and
 * starts empty: the page opens with nothing selected. Changing the family clears it (the shell's setGrp), so every family starts from scratch too.
 */
function VariantPicker({ v, grp, setGrp, on, setOn, explain }: { v: View; grp: string; setGrp: (g: string) => void; on: Set<string>; setOn: (s: Set<string>) => void; explain?: (k: string) => void }) {
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useVariants(v, grp);
  const groups: PickGroup[] = [{
    id: grp, label: G.label,
    items: variants.map((r) => ({
      id: r.model, label: VARIANT_LABEL[r.variant!] ?? r.variant!, title: r.lever ?? undefined,
      mark: <span className="sw" style={{ background: variantColor(r.variant!, G.recipe) }} aria-hidden="true" />,
      suffix: starOf(r) ? <span className="sub" title={`scored on ${r.subset}`}>*</span> : undefined,
      detail: explain ? () => explain(r.model) : undefined,
    })),
  }];
  const n = variants.filter((r) => on.has(r.model)).length;
  return (
    <>
      <Control label="Model">
        <span className="select">
          <select value={grp} onChange={(e) => setGrp(e.target.value)}>
            {ABLATION_GROUPS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
          </select>
        </span>
      </Control>
      <Picker label="Configurations" summary={n ? `${n} of ${variants.length}` : "None selected"} groups={groups} on={on} onChange={setOn} />
    </>
  );
}

function AblationSection({ v, grp, on, explain }: { v: View; grp: string; on: Set<string>; explain: (k: string) => void }) {
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useVariants(v, grp);
  const sel = variants.filter((r) => on.has(r.model));
  const color = (r: Rec) => variantColor(r.variant!, G.recipe);
  const name = (r: Rec) => VARIANT_LABEL[r.variant!] ?? r.variant!;
  const [chart, setChart] = useState<Chart>("ranked");
  // The family's reference configuration, for the `heat` view's "vs default" column: the `@base` variant. Taken from the whole family, so
  // it is stable while configurations are toggled; PRHeat omits the comparison while that row is not shown. OpenAI Decisions has no `@base`:
  // its `predicate` form (the Noul analogue) is the reference.
  const referenceId = variants.map((r) => r.model).find((k) => k.endsWith("@base") || k.endsWith("@predicate"));

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    return { id: r.model, name: name(r), color: color(r), recall: p.recall, precision: p.precision, subset: starOf(r), sub: qualitySub(r, v) };
  });

  // Only the Recall and precision card on this page (the Inference latency and Cost cards belong to Compare models); `.dash.ranked` lets it span the full width in both views.
  return (
    <section className="section">
      <HoverProvider>
        <div className="dash ranked">
          <PRCard
            items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={explain}
            emptyText={variants.length ? CHOOSE_CONFIGS : "No configurations of this model were run on this corpus and arm."}
            logos={false} ranked="heat" referenceId={referenceId} sig={`${v.corpus}:${grp}`} height={460}
          />
        </div>
      </HoverProvider>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------

type Page = "compare" | "configurations" | "tradeoff";
const PAGES: { id: Page; label: string }[] = [{ id: "compare", label: "Compare models" }, { id: "configurations", label: "Compare configurations" }, { id: "tradeoff", label: "Trade-off" }];
/** The page a location hash names; Compare models for anything else (the B variant keeps its tab in the hash). */
const pageOf = (hash: string): Page => (hash === "#configurations" ? "configurations" : hash === "#tradeoff" ? "tradeoff" : "compare");

/**
 * The page: masthead, sticky control bar, the Compare models or Compare configurations section, the details and disclaimer modals and the foot.
 * `Compare` is the Compare models section (this file's CompareSection: one recall/precision card with the Speed, Cost and Stability cards beside it);
 * the B variant (AppB.tsx, b.html) passes its tabbed section and keeps everything else identical. `mast` goes in the masthead after the page nav
 * (B's "view A" link), `controlsTail` at the end of the control bar on Compare models (B's tab strip), and `compareHash` is the hash the page nav writes
 * for Compare models (B keeps the active tab in it).
 */
export function Shell({ Compare = CompareSection, mast, controlsTail, compareHash = "#compare" }: { Compare?: (p: CompareProps) => ReactNode; mast?: ReactNode; controlsTail?: ReactNode; compareHash?: string }) {
  // The corpus is not persisted (hash or storage); siteCorpus still guards the state so an unlisted id (e.g. "veridian") can never render.
  const [corpus, setCorpusRaw] = useState(DEFAULT_CORPUS);
  const setCorpus = (c: string) => setCorpusRaw(siteCorpus(c));
  const tag: "" | "v0" = ""; // TREC criteria: always the calibrated set; the bare-topic (v0) rows stay exported but are not shown
  const arm: "multi" | "single" = "multi"; // prompting: always all issues per call; the one-issue-per-call rows stay exported but are not shown
  const gray: Gray = "all"; // gray gold labels always count; the exclude-gray view is not shown
  const level: Level = "doc"; // scope: document level or one issue; the pooled every-decision view is not shown
  const [issue, setIssue] = useState<string | null>(null);
  const v: View = { corpus, tag: corpus === "trec" ? tag : "", arm, gray, level, issue };
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];

  const pickCorpus = (c: string) => { setCorpus(c); setIssue(null); };
  const [explain, setExplain] = useState<string | null>(null);
  // The Method modal (how each experiment was run) opens from the header and foot buttons and from every hint's "Method" link, via MethodContext.
  const disclaimer = useDisclaimer(); // first-visit disclaimer; reopens from the footer
  // The Method modal (components/Method.tsx) is not mounted for now; hint "more" links open the About modal instead.
  const openMethod = disclaimer.show;
  // the Compare models selection: nothing to start with (every page opens from scratch; the picker's "Suggested set" button selects the curated roster)
  const [on, setOn] = useState<Set<string>>(() => new Set());
  // the Compare models Statistics row's setting (compareStats.ts: threshold, reviewer, sort), remembered under the site's own key; the TAR picker reads the reviewer for its note
  const [stats, setStats] = useSiteStats();
  // Compare configurations: the family, and the configurations of it that are shown (by model key); none to start with, and none again when the family changes
  const [grp, setGrpRaw] = useState("jev");
  const [cfgOn, setCfgOn] = useState<Set<string>>(() => new Set());
  const setGrp = (g: string) => { setGrpRaw(g); setCfgOn(new Set()); };
  const corpusTitle = `${fmtInt(meta.n_docs)} documents · ${meta.n_issues} issues · ${fmtInt(meta.n_pos_docs_any)} responsive to at least one (${fmtPct(meta.n_pos_docs_any / meta.n_docs, 0)}) · gold: ${meta.gold}`;
  const [theme, setTheme] = useState<Theme>(readTheme);
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem(THEME_KEY, theme); } catch { /* storage denied: the choice lasts the session */ } }, [theme]);
  const [pageId, setPageId] = useState<Page>(() => pageOf(location.hash));
  useEffect(() => {
    const onHash = () => setPageId(pageOf(location.hash));
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const goPage = (p: Page) => { history.replaceState(null, "", p === "compare" ? compareHash : `#${p}`); setPageId(p); window.scrollTo(0, 0); };
  // the Trade-off page's own model selection (Tradeoff.tsx): nothing to start with, as on Compare models; no TAR rows
  const [tradeOn, setTradeOn] = useState<Set<string>>(() => new Set());

  const page = (
    <div className="page">
      <header className="masthead">
        <h1 className="title">Jev vs Frontier LLMs: A Zero-Shot Bakeoff</h1>
        <nav className="tabs" aria-label="Pages">
          {PAGES.map((p) => (
            <button key={p.id} className={pageId === p.id ? "on" : ""} onClick={() => goPage(p.id)} aria-current={pageId === p.id ? "page" : undefined}>{p.label}</button>
          ))}
        </nav>
        {mast}
        <span className="theme"><a className="home-link" href="./" title="The landing page: every page of the site">Home</a><Seg value={theme} onChange={setTheme} options={THEME_OPTIONS} /></span>
      </header>

      <div className="controls">
        <Control label="Corpus">
          <Seg value={corpus} onChange={pickCorpus} options={CORPORA.map((c) => ({ id: c.id, label: c.label }))} />
          <Hint title={meta.display} text={corpusTitle} />
        </Control>
        {pageId === "compare"
          ? <><ModelPicker v={v} on={on} setOn={setOn} explain={setExplain} /><TarPicker v={v} on={on} setOn={setOn} reviewer={stats.tarReviewer} /></>
          : pageId === "tradeoff"
            ? <TradeoffPicker v={v} on={tradeOn} setOn={setTradeOn} explain={setExplain} />
            : <VariantPicker v={v} grp={grp} setGrp={setGrp} on={cfgOn} setOn={setCfgOn} explain={setExplain} />}
        <Control label="Issue">
          <span className="select">
            <select value={issue ?? "__doc"} onChange={(e) => { const val = e.target.value; setIssue(val === "__doc" ? null : val); }}>
              <option value="__doc">Relevance</option>
              <optgroup label="Issues">
                {Object.keys(meta.issues).map((k) => <option key={k} value={k}>{issueLabel(meta, k)}</option>)}
              </optgroup>
            </select>
          </span>
        </Control>
        {pageId === "compare" && controlsTail}
      </div>

      {pageId === "compare"
        ? <Compare v={v} on={on} setOn={setOn} explain={setExplain} stats={stats} setStats={setStats} />
        : pageId === "tradeoff"
          ? <TradeoffSection key={corpus} v={v} on={tradeOn} explain={setExplain} /> /* keyed on the corpus: operating points chosen against one corpus's curves start over on another */
          : <AblationSection v={v} grp={grp} on={cfgOn} explain={setExplain} />}
      {explain && (
        <ExplainModal
          initialKey={explain} initialCorpus={corpus} onClose={() => setExplain(null)}
          metrics={(k, c) => metricsFor(k, c, v, (rows) => (pageId === "compare" ? rosterOf(rows).filter((r) => on.has(r.model)) : pageId === "tradeoff" ? rows.filter((r) => tradeOn.has(r.model)) : rows.filter((r) => r.group === grp && !!r.variant && !isHidden(r.model) && cfgOn.has(r.model))))}
        />
      )}

      {disclaimer.open && <DisclaimerModal onClose={disclaimer.close} />}

      <footer className="notes">
        <DisclaimerLink onClick={disclaimer.show} />
      </footer>
    </div>
  );
  return <MethodContext.Provider value={openMethod}>{page}</MethodContext.Provider>;
}

/** The comparison app (compare.html; the root, index.html, is the landing page): the shell with its own Compare models section. */
export default function App() {
  return <Shell />;
}
