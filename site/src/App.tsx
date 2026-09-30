import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import {
  ABLATION_GROUPS, CORPORA, DATA, DEFAULT_CORPUS, DEFAULT_ON, GPU_NAME, GPU_USD_PER_HOUR, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER, rosterOf,
  corpusKey, costPerDoc, displayMeta, fmtCI, fmtInt, fmtMs, fmtPct, fmtUSD, isDecider, isGpuRow, isHidden, issueLabel, paidPerDoc, pick, selectableRowsOf, siteCorpus, starOf, tarRowsOf, variantColor,
  type Gray, type Kind, type Level, type PRF, type Rec,
} from "./data";
import { Control, Hint, MethodContext, ROW_PULSE_MS, Seg, usePulseWindow, type HintItem, type TipLine } from "./components/ui";
import { PRScatter, type PRItem } from "./components/PRScatter";
import { PRRail } from "./components/PRRail";
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
export function PRCard({ items, chart, onChart, defaultZoom, emptyText, logos = true, height = 380, explain, pulse = false, ranked, referenceId, sig = "card", seriesKey }: { items: PRItem[]; chart: Chart; onChart: (c: Chart) => void; defaultZoom: boolean; emptyText?: string; logos?: boolean; height?: number; explain?: (k: string) => void; pulse?: boolean; ranked: "rail" | "heat"; referenceId?: string; sig?: string; seriesKey?: ReactNode }) {
  const setChart = onChart;
  const [zoom, setZoom] = useState(defaultZoom);
  const onSelect = explain && ((it: PRItem) => explain(it.id));
  const hover = useHover();
  const rowProps = { items, zoom, sortBy: "recall" as const, logos, onSelect, highlight: hover.id, onHover: hover.set };
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
      {chart === "ranked" && ranked === "rail" && <PRRail {...rowProps} />}
      {chart === "ranked" && ranked === "heat" && <PRHeat {...rowProps} referenceId={referenceId} />}
      {seriesKey}
      {chart === "map" && (
        <div className="legend-note">
          <span>Dot: point estimate. Shaded box: 95% interval on recall (width) and precision (height).</span>
          {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
        </div>
      )}
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
  { k: "Source", v: <><b>TREC, all issues per call, Jev / Claude / GPT rows</b>: a dedicated single-request sample of 200 emails. Every other cell: per-request timings recorded during the benchmark run, <b>8–12 requests in flight</b>. Each row's details say which.</> },
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
        <OpsBars items={latency} axis="milliseconds" unit="per document, median" logos={logos} onSelect={onSelect} highlight={hover.id} onHover={hover.set} />
      </div>
      <div className="card">
        <div className="card-t">
          <h3>Cost</h3><span className="unit">per 100k docs</span>
          <span className="right"><Hint items={costItems(recs)} more="About" /></span>
        </div>
        <OpsBars items={cost} axis="US dollars" unit="per 100k docs" logos={logos} onSelect={onSelect} highlight={hover.id} onHover={hover.set} />
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
  const reset = () => {
    const next = new Set([...on].filter((k) => k.startsWith("tar@")));
    DEFAULT_ON.forEach((k) => { if (!k.startsWith("tar@")) next.add(k); });
    setOn(next);
  };
  const selected = primary.filter((r) => on.has(r.model));
  return <Picker label="Models" summary={`${avail} of ${primary.length}`} groups={groups} on={on} onChange={setOn} onReset={reset}
    selected={selected.length ? <><span className="pick-selected-lab">Selected</span><div className="series-selected">
      {selected.map((r) => {
        const meta = displayMeta(r.model, r);
        return <div className="series-selected-row" key={r.model}><SeriesColorControl id={r.model} color={colorOf(r.model, meta.color)} onColor={setColor} label={meta.short} /><span>{meta.short}</span><button type="button" onClick={() => { const next = new Set(on); next.delete(r.model); setOn(next); }} aria-label={`Remove ${meta.short}`}>×</button></div>;
      })}
    </div></> : undefined} />;
}

type TarOption = { row: Rec; n: number | null; sampling: "Random" | "Diversity" | null; reviewer: string; order: number };
function tarOption(row: Rec): TarOption {
  const v = row.model.replace(/^tar@/, "");
  if (v.startsWith("cal")) {
    const reviewer = v === "cal" ? "80% recall target · 90% relevant-document coding accuracy" : v === "cal_75" ? "75% recall target · 90% relevant-document coding accuracy" : v === "cal_perfect" ? "80% recall target · perfect coding" : v === "cal_knee" ? "Knee stop · 90% relevant-document coding accuracy" : row.name.replace(/^TAR 2\.0\s*·?\s*/, "");
    return { row, n: null, sampling: null, reviewer, order: { cal: 0, cal_75: 1, cal_perfect: 2, cal_knee: 3 }[v] ?? 9 };
  }
  const m = /^t1_(\d+)(.*)$/.exec(v);
  const n = m ? Number(m[1]) : 0, suffix = m?.[2] ?? "";
  const sampling = suffix.endsWith("_div") ? "Diversity" : "Random";
  const acc = /_acc(\d+)/.exec(suffix)?.[1];
  const reviewer = acc ? `${acc}% relevant-document coding accuracy${acc === "90" ? " · sweep" : ""}` : suffix.includes("_noisy") ? "90% relevant-document coding accuracy · baseline" : suffix.includes("_f1") ? "Perfect coding · F1 cutoff" : "Perfect coding · 80% recall cutoff";
  return { row, n, sampling, reviewer, order: (sampling === "Random" ? 0 : 10) + (acc ? Number(acc) / 10 : suffix.includes("_noisy") ? 9 : suffix.includes("_f1") ? 8 : 0) };
}

const tarName = (x: TarOption) => x.n == null
  ? `TAR 2.0 · CAL · ${x.reviewer}`
  : `TAR 1.0 · ${fmtInt(x.n)} reviewed · ${x.sampling?.toLowerCase()} · ${x.reviewer}`;
const compareName = (r: Rec) => r.model.startsWith("tar@") ? tarName(tarOption(r)) : displayMeta(r.model, r).short;

type TarWorkflow = "t1" | "cal";
type TarSampling = "random" | "diversity";
type TarAccuracy = "60" | "70" | "80" | "90" | "perfect";
type CalStop = "target80" | "target75" | "knee";
const ACCURACY_OPTIONS: { id: TarAccuracy; label: string }[] = [
  { id: "60", label: "60%" }, { id: "70", label: "70%" }, { id: "80", label: "80%" }, { id: "90", label: "90%" }, { id: "perfect", label: "Perfect" },
];

/** TAR workflow builder: independent variables resolve to an existing result key; selected combinations remain a multi-select comparison. */
export function TarPicker({ v, on, setOn }: { v: View; on: Set<string>; setOn: (s: Set<string>) => void }) {
  const rows = useRows(v);
  const { colorOf, setColor } = useSeriesColors();
  const options = tarRowsOf(rows).map(tarOption);
  if (!options.length) return null;
  const sizes = [...new Set(options.flatMap((x) => x.n == null ? [] : [x.n]))].sort((a, b) => a - b);
  const ids = new Set(options.map((x) => x.row.model));
  const defaults = new Set([...DEFAULT_ON].filter((k) => ids.has(k)));
  const selectedOptions = options.filter((x) => on.has(x.row.model));
  const isDefault = selectedOptions.length === defaults.size && selectedOptions.every((x) => defaults.has(x.row.model));
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
  const reset = () => {
    const next = new Set([...on].filter((k) => !k.startsWith("tar@")));
    DEFAULT_ON.forEach((k) => { if (ids.has(k)) next.add(k); });
    setOn(next);
  };
  const remove = (id: string) => { const next = new Set(on); next.delete(id); setOn(next); };
  return (
    <span ref={wrapRef} className={`pick-wrap tar-build${open ? " open" : ""}`}>
      <button ref={buttonRef} className="pick-btn" onClick={() => setOpen((x) => !x)} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined}>
        <span className="pick-lab">TAR workflows</span>
        <span className="pick-sum">{selectedOptions.length ? `${selectedOptions.length} selected${isDefault ? " · defaults" : ""}` : "None selected"}</span>
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
                  const name = tarName(x), fallback = displayMeta(x.row.model, x.row).color;
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
            <button type="button" onClick={reset}>Restore defaults</button>
            <button type="button" onClick={() => { const next = new Set([...on].filter((k) => !k.startsWith("tar@"))); setOn(next); }}>Clear TAR</button>
            <span className="pick-foot-r"><span className="pick-note">Percentages are relevant-document coding accuracy, not overall agreement. The non-relevant false-positive rate is one-fifth of the miss rate.</span></span>
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

/** What the page shell hands its Compare models section: the view, the model selection and the details-modal opener. */
export type CompareProps = { v: View; on: Set<string>; explain: (k: string) => void; setOn?: (s: Set<string>) => void };

function CompareSection({ v, on, explain, setOn }: CompareProps) {
  const rows = useRows(v);
  const { sel, items } = useCompareItems(v, on);
  const { colorOf } = useSeriesColors();
  const [chart, setChart] = useState<Chart>("map");
  const manyTar = items.filter((x) => x.id.startsWith("tar@")).length >= 12;
  const wasManyTar = useRef(manyTar);
  useEffect(() => {
    if (manyTar && !wasManyTar.current) setChart("ranked");
    wasManyTar.current = manyTar;
  }, [manyTar]);

  return (
    <section className="section">
      {manyTar && <div className="tar-chart-note" role="status"><b>Dense TAR comparison.</b> Ranked view keeps workflow names and confidence intervals readable; you can still switch back to the map.</div>}
      <HoverProvider>
        <div className={`dash${chart !== "map" ? " ranked" : ""}`}>
          <PRCard
            items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={(k) => { if (!k.startsWith("tar@")) explain(k); }}
            pulse ranked="rail" sig={v.corpus}
            seriesKey={setOn ? <ComparisonKey items={items} on={on} setOn={setOn} /> : undefined}
          />
          <div className="stack">
            <OpsCards recs={sel} colorOf={(r) => colorOf(r.model, displayMeta(r.model, r).color)} nameOf={compareName} explain={(k) => { if (!k.startsWith("tar@")) explain(k); }} decider={decider} emphasis={emphasis} />
            <ConsistencyCard recs={sel} colorOf={(r) => colorOf(r.model, displayMeta(r.model, r).color)} nameOf={compareName} arm={v.arm} onSelect={(r) => { if (!r.model.startsWith("tar@")) explain(r.model); }} emphasis={emphasis} />
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

/** Model select + configuration multi-select for the Configurations page, rendered in the control bar. */
/** Compare configurations shows every configuration of the chosen family; there is no per-configuration picker (the rows' details buttons open the modal). */
function VariantPicker({ grp, setGrp }: { grp: string; setGrp: (g: string) => void }) {
  return (
    <Control label="Model">
      <span className="select">
        <select value={grp} onChange={(e) => setGrp(e.target.value)}>
          {ABLATION_GROUPS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
        </select>
      </span>
    </Control>
  );
}

function AblationSection({ v, grp, off, explain }: { v: View; grp: string; off: Set<string>; explain: (k: string) => void }) {
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useVariants(v, grp);
  const sel = variants.filter((r) => !off.has(r.variant!));
  const color = (r: Rec) => variantColor(r.variant!, G.recipe);
  const name = (r: Rec) => VARIANT_LABEL[r.variant!] ?? r.variant!;
  const [chart, setChart] = useState<Chart>("ranked");
  // The family's reference configuration, for the `heat` view's "vs default" column: the `@base` variant. Taken from the whole family, so
  // it is stable while configurations are toggled; PRHeat omits the comparison while that row is not shown.
  const referenceId = variants.map((r) => r.model).find((k) => k.endsWith("@base"));

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
            emptyText={variants.length ? "Select at least one configuration." : "No configurations of this model were run on this corpus and arm."}
            logos={false} ranked="heat" referenceId={referenceId} sig={`${v.corpus}:${grp}`} height={460}
          />
        </div>
      </HoverProvider>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------

type Page = "compare" | "configurations";
const PAGES: { id: Page; label: string }[] = [{ id: "compare", label: "Compare models" }, { id: "configurations", label: "Compare configurations" }];

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
  const [on, setOn] = useState<Set<string>>(new Set(DEFAULT_ON));
  const [grp, setGrp] = useState("jev");
  const off = useMemo(() => new Set<string>(), []); // every configuration of the family is shown
  const corpusTitle = `${fmtInt(meta.n_docs)} documents · ${meta.n_issues} issues · ${fmtInt(meta.n_pos_docs_any)} responsive to at least one (${fmtPct(meta.n_pos_docs_any / meta.n_docs, 0)}) · gold: ${meta.gold}`;
  const [theme, setTheme] = useState<Theme>(readTheme);
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem(THEME_KEY, theme); } catch { /* storage denied: the choice lasts the session */ } }, [theme]);
  const [pageId, setPageId] = useState<Page>(() => (location.hash === "#configurations" ? "configurations" : "compare"));
  useEffect(() => {
    const onHash = () => setPageId(location.hash === "#configurations" ? "configurations" : "compare");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const goPage = (p: Page) => { history.replaceState(null, "", p === "compare" ? compareHash : "#configurations"); setPageId(p); window.scrollTo(0, 0); };

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
        <span className="theme"><Seg value={theme} onChange={setTheme} options={THEME_OPTIONS} /></span>
      </header>

      <div className="controls">
        <Control label="Corpus">
          <Seg value={corpus} onChange={pickCorpus} options={CORPORA.map((c) => ({ id: c.id, label: c.label }))} />
          <Hint title={meta.display} text={corpusTitle} />
        </Control>
        {pageId === "compare"
          ? <><ModelPicker v={v} on={on} setOn={setOn} explain={setExplain} /><TarPicker v={v} on={on} setOn={setOn} /></>
          : <VariantPicker grp={grp} setGrp={setGrp} />}
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

      {pageId === "compare" ? <Compare v={v} on={on} setOn={setOn} explain={setExplain} /> : <AblationSection v={v} grp={grp} off={off} explain={setExplain} />}
      {explain && (
        <ExplainModal
          initialKey={explain} initialCorpus={corpus} onClose={() => setExplain(null)}
          metrics={(k, c) => metricsFor(k, c, v, (rows) => (pageId === "compare" ? rosterOf(rows).filter((r) => on.has(r.model)) : rows.filter((r) => r.group === grp && !!r.variant && !isHidden(r.model) && !off.has(r.variant))))}
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

/** The site (index.html): the shell with its own Compare models section. */
export default function App() {
  return <Shell />;
}
