import { DATA, PRIMARY_BY_KEY, costPerDoc, fmtInt, fmtPct, isDecider, pick, starOf, type Rec } from "./data";
import { detFor } from "./components/Consistency";
import type { StudioRow, StudioScatterPt } from "./components/StudioCharts";
import type { View } from "./App";

/**
 * The Cost, Speed and Stability charts' rows and captions, built from the selected roster records (`sel`, App.tsx useCompareItems). Shared by the
 * screenshot studio (StudioPage.tsx) and the tabbed B variant of the dashboard (AppB.tsx), which draw them with components/StudioCharts.tsx.
 * Every figure here follows the dashboard's rules: costPerDoc for money, the median latency with its 95% bootstrap interval for speed, and the
 * Stability card's cell selection (components/Consistency.tsx detFor) for disagreement.
 */

export type CostChart = "bars" | "dots" | "scatter";
export type CostUnit = "1k" | "100k" | "decision";
export type CostScale = "linear" | "log";
export type SpeedChart = "bars" | "dots" | "throughput";
export type SpeedUnit = "ms" | "s";
export type StabChart = "bars" | "agree" | "dots";
export type StabSetting = "default" | "t0";

export const COST_UNIT: Record<CostUnit, { mult: (r: Rec) => number; axis: string; short: string }> = {
  "1k": { mult: () => 1e3, axis: "US dollars per 1,000 documents", short: "per 1,000 docs" },
  "100k": { mult: () => 1e5, axis: "US dollars per 100,000 documents", short: "per 100,000 docs" },
  decision: { mult: (r) => (r.ops.n_decisions ? r.ops.n_docs / r.ops.n_decisions : 1), axis: "US dollars per decision (one document × one issue)", short: "per decision" },
};
/** Money at the precision the size calls for: "$5,000", "$12.3", "$0.14", "$0.000017". */
export const fmtMoney = (v: number): string => (v === 0 ? "$0" : v >= 100 ? `$${fmtInt(Math.round(v))}` : v >= 1 ? `$${v.toFixed(v >= 10 ? 1 : 2)}` : v >= 0.01 ? `$${v.toFixed(2)}` : `$${(+v.toPrecision(2)).toString()}`);
export const fmtMoneyTick = (v: number): string => (v >= 1 ? `$${fmtInt(Math.round(v))}` : `$${(+v.toPrecision(2)).toString()}`);
export const fmtMsTick = (v: number): string => (v === 0 ? "0" : v < 1000 ? `${Math.round(v)} ms` : `${+(v / 1000).toFixed(2)} s`);
export const fmtPctTick = (v: number): string => `${+(v * 100).toFixed(2)}%`;
export const fmtLatency = (ms: number, unit: SpeedUnit) => (unit === "s" ? `${(ms / 1000).toFixed(2)} s` : `${fmtInt(Math.round(ms))} ms`);

/** The row fields every chart shares: colours and short names from the roster (so the studio's Style presets apply), the decider marker and the subset star. */
export const rowBase = (r: Rec) => ({ id: r.model, name: PRIMARY_BY_KEY[r.model].short, color: PRIMARY_BY_KEY[r.model].color, decider: isDecider(PRIMARY_BY_KEY[r.model].kind ?? r.kind), subset: starOf(r) });

export function costRows(sel: Rec[], unit: CostUnit): StudioRow[] {
  const cu = COST_UNIT[unit];
  return sel.map((r) => {
    const c = costPerDoc(r), val = c == null ? null : c * cu.mult(r);
    return { ...rowBase(r), value: val, label: val == null ? "" : fmtMoney(val) };
  });
}

export function costPts(sel: Rec[], v: View, unit: CostUnit): StudioScatterPt[] {
  const cu = COST_UNIT[unit];
  return sel.map((r) => { const c = costPerDoc(r); return { ...rowBase(r), x: c == null ? null : c * cu.mult(r), y: pick(r, v.level, v.gray, v.issue).recall }; });
}

export function speedRows(sel: Rec[], chart: SpeedChart, unit: SpeedUnit): StudioRow[] {
  return sel.map((r) => {
    const p50 = r.ops.doc_latency_p50_ms, ci = r.ops.doc_latency_p50_ci_ms ?? null;
    if (chart === "throughput") { const val = p50 == null ? null : 3.6e6 / p50; return { ...rowBase(r), value: val, label: val == null ? "" : `${fmtInt(Math.round(val))} docs/h` }; }
    // Whisker: the 95% bootstrap interval for the median (two-sided), not the p95 tail.
    return { ...rowBase(r), value: p50, lo: ci?.[0] ?? null, hi: ci?.[1] ?? null, label: p50 == null ? "" : fmtLatency(p50, unit) };
  });
}

// Stability: the card's rule. At t = 0 a decider keeps its default cell (no sampling control); an LLM without a t = 0 cell rejected the parameter.
const isLLM = (r: Rec) => r.kind === "llm" || r.kind === "local_llm";
const stabLbl = (p: number) => (p === 0 ? "0" : fmtPct(p, p < 0.001 ? 2 : 1));

/**
 * The Stability rows for `sel`. `sameRuns` is "5 runs · 2,400 decisions" when every measured row shares it (for the caption; otherwise each row
 * carries its own); `agreeDomain` is the zoomed axis of the agreement view; `hasT0` says whether any selected model has a temperature-0 cell.
 */
export function stabRows(sel: Rec[], arm: "multi" | "single", chart: StabChart, setting: StabSetting, hideUnmeasured: boolean): { rows: StudioRow[]; sameRuns: string | null; agreeDomain: [number, number]; hasT0: boolean } {
  const cells = sel.map((r) => { const d = detFor(r, arm, "default"), t0 = detFor(r, arm, "t0"); return { r, d, c: setting === "t0" ? (t0 ?? (isLLM(r) ? null : d)) : d }; });
  // "5 runs · 2,400 decisions" goes in the legend when every measured row shares it, on each row otherwise
  const runsOf = new Set(cells.filter((x) => x.c).map((x) => `${x.c!.cell.k} runs · ${fmtInt(x.c!.cell.n_decisions)} decisions`));
  const sameRuns = runsOf.size === 1 ? [...runsOf][0] : null;
  const all: StudioRow[] = cells.map(({ r, d, c }) => {
    if (!c) return { ...rowBase(r), value: null, label: "", empty: setting === "t0" && d ? "API rejects temperature" : "not measured" };
    const [p, lo, hi] = c.pairwise, runs = `${c.cell.k} runs · ${fmtInt(c.cell.n_decisions)} decisions`;
    if (chart === "agree") return { ...rowBase(r), value: 1 - p, lo: 1 - hi, hi: 1 - lo, label: p === 0 ? "100%" : fmtPct(1 - p, p < 0.001 ? 2 : 1), sub: `disagree ${stabLbl(p)}` };
    return { ...rowBase(r), value: p, lo, hi, label: stabLbl(p), sub: sameRuns ? undefined : runs };
  });
  const rows = hideUnmeasured ? all.filter((x) => x.value != null) : all;
  const agreeLo = Math.min(1, ...rows.map((x) => (x.value == null ? 1 : (x.lo ?? x.value))));
  const agreeDomain: [number, number] = [Math.max(0, Math.floor((agreeLo - 0.003) * 200) / 200), 1];
  const hasT0 = sel.some((r) => detFor(r, arm, "t0"));
  return { rows, sameRuns, agreeDomain, hasT0 };
}

/** Where the Stability cells were measured, for the caption. */
export const MEASURED_ON = DATA.determinism ? `${fmtInt(DATA.determinism.sample.n_docs)} Mallinckrodt emails` : "a fixed sample";

// ---- captions (the legend line under each chart). `whiskers` says whether the chart draws its whiskers (the studio's presets can hide them). ----

export function costCaption(chart: CostChart, unit: CostUnit, scale: CostScale, whiskers = true): string[] {
  const cu = COST_UNIT[unit];
  const basis = "Cost at standard list price for every API model (no flex, batch or caching discounts); GPU rows as A100 rental for the measured time";
  if (chart === "scatter") return [`${basis}, ${cu.short} on a log axis, against recall${whiskers ? " with its 95% interval (whisker)" : ""}.`];
  return [`${basis}, ${cu.short}${chart === "dots" || scale === "log" ? ", log axis" : ""}.`];
}

/** Where the Speed figures come from, for the caption's second line. */
export const SPEED_SOURCE = "TREC all-issues Jev, Claude and GPT rows: a dedicated single-request sample of 200 emails (GPT-5.6 Luna on OpenAI's standard tier, Terra on flex); every other cell: per-request timings recorded during the benchmark run, 8–12 requests in flight.";

export function speedCaption(chart: SpeedChart, whiskers = true): string[] {
  if (chart === "throughput") return ["Sequential documents per hour: 3,600,000 ÷ median wall-clock milliseconds per request to score one document. Every service accepts parallel requests, so compare ratios, not absolutes.", SPEED_SOURCE];
  return [`${chart === "bars" ? "Bar" : "Dot"}: median wall-clock per request to score one document${chart === "dots" ? ", on a log axis" : ""}${whiskers ? "; whisker: 95% bootstrap interval for the median" : ""}.`, SPEED_SOURCE];
}

export function stabCaption(chart: StabChart, setting: StabSetting, sameRuns: string | null, whiskers = true): string[] {
  const t0 = setting === "t0" ? " Temperature 0 where the API accepts it; deciders expose no sampling control." : "";
  const where = `Measured on ${MEASURED_ON}${sameRuns ? ` (${sameRuns} per model)` : " scored 5 times"}; the same cells are shown for every corpus.`;
  if (chart === "agree") return [`Bar: agreement, the probability two identical runs give the same decision (1 − pairwise disagreement)${whiskers ? "; whisker: 95% bootstrap interval" : ""}. Axis zoomed to the measured range.${t0}`, where];
  return [`${chart === "bars" ? "Bar" : "Dot"}: probability two identical runs disagree on a decision (pairwise)${whiskers ? "; whisker: 95% bootstrap interval over decisions" : ""}.${t0}`, where];
}

/** Axis titles, as the studio writes them. */
export const costAxis = (chart: CostChart, unit: CostUnit, scale: CostScale) => COST_UNIT[unit].axis + (chart === "dots" || scale === "log" ? " (log)" : "");
export const speedAxis = (chart: SpeedChart) => (chart === "throughput" ? "sequential documents per hour (3,600,000 ÷ median ms per document)" : `median latency per document${chart === "dots" ? " (log)" : ""}`);
export const stabAxis = (chart: StabChart, setting: StabSetting) => (chart === "agree" ? `agreement: probability two identical runs give the same decision${setting === "t0" ? " · temperature 0" : ""}` : `probability two identical runs disagree${setting === "t0" ? " · temperature 0" : ""}`);
