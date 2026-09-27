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
/** The dashboard's Stability setting switch (AppB.tsx): the default-sampling cell, or the t = 0 cell where one exists. */
export type StabSetting = "default" | "t0";
/**
 * The studio's Temperature 0 control: `off` draws the default-sampling cell alone (the site's chart); `paired` adds a second, lighter-tinted bar
 * per model at its t = 0 rate; `dots` is a lollipop (filled dot at the default rate, hollow dot at t = 0, joined in the model's colour); `t0` draws
 * the t = 0 cell alone where one exists, the default cell otherwise (the dashboard's t = 0 setting). Models without a t = 0 cell keep one element.
 */
export type StabT0 = "off" | "paired" | "dots" | "t0";
export const STAB_T0: { id: StabT0; label: string; title: string }[] = [
  { id: "off", label: "off", title: "Vendor default sampling only" },
  { id: "paired", label: "paired bars", title: "A second, lighter bar per model at its temperature-0 rate; models without a t = 0 cell keep one bar" },
  { id: "dots", label: "dots", title: "Lollipop: filled dot at the default rate, hollow dot at temperature 0, joined in the model's colour" },
  { id: "t0", label: "t = 0 only", title: "Temperature 0 where the API accepts it, the default cell otherwise; deciders expose no sampling control" },
];
/** The dashboard's two-way setting as a studio mode. */
export const stabT0Of = (s: StabSetting): StabT0 => (s === "t0" ? "t0" : "off");
/** Whether a mode draws both cells per model (a second element for the t = 0 rate). */
export const stabPaired = (t0: StabT0) => t0 === "paired" || t0 === "dots";

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

type Det = NonNullable<ReturnType<typeof detFor>>;
const runsLbl = (c: Det) => `${c.cell.k} runs · ${fmtInt(c.cell.n_decisions)} decisions`;

/**
 * The Stability rows for `sel`. The rows carry the plotted figure alone (no secondary text beside the name): `sameRuns` is the runs the drawn cells
 * share, "5 runs · 2,400 decisions" (the most common where they differ), and `runsNotes` names each model whose cell departs from it ("Gemma 3 12B:
 * 4 runs"), both for the caption; `agreeDomain` is the zoomed axis of the agreement view; `hasT0` says whether any selected model has a
 * temperature-0 cell. In the paired modes (stabPaired) a row whose model has a t = 0 cell carries it as `t0`, in the chart's figure (disagreement
 * or agreement), for the second bar or the hollow dot; the row's own value stays the default cell.
 */
export function stabRows(sel: Rec[], arm: "multi" | "single", chart: StabChart, t0: StabT0, hideUnmeasured: boolean): { rows: StudioRow[]; sameRuns: string | null; runsNotes: string[]; agreeDomain: [number, number]; hasT0: boolean } {
  const both = stabPaired(t0);
  const cells = sel.map((r) => { const d = detFor(r, arm, "default"), t = detFor(r, arm, "t0"); return { r, d, t: both ? t : null, c: t0 === "t0" ? (t ?? (isLLM(r) ? null : d)) : d }; });
  const shown = hideUnmeasured ? cells.filter((x) => x.c) : cells;
  // the runs of the drawn cells (default and any t = 0 rerun): the most common goes in the caption, the models that depart from it are named after it
  const counts = new Map<string, number>();
  for (const x of shown) for (const c of [x.c, x.t]) if (c) counts.set(runsLbl(c), (counts.get(runsLbl(c)) ?? 0) + 1);
  const sameRuns = counts.size ? [...counts.entries()].sort((a, b) => b[1] - a[1])[0][0] : null;
  const runsNotes = shown.flatMap((x) => {
    const own = [...new Set([x.c, x.t].filter((c): c is Det => !!c && runsLbl(c) !== sameRuns).map((c) => c.cell))];
    if (!own.length) return [];
    // "4 runs" where only the run count differs from the caption's figure, the whole "4 runs · 1,600 decisions" where the decisions do too
    const sameN = !!sameRuns && own.every((c) => sameRuns.endsWith(`${fmtInt(c.n_decisions)} decisions`));
    return [`${PRIMARY_BY_KEY[x.r.model].short}: ${own.map((c) => (sameN ? `${c.k} runs` : `${c.k} runs · ${fmtInt(c.n_decisions)} decisions`)).join(", ")}`];
  });
  // a cell as the chart's figure: pairwise disagreement, or agreement (1 − it) with the interval turned round
  const fig = (c: Det) => {
    const [p, lo, hi] = c.pairwise;
    return chart === "agree" ? { value: 1 - p, lo: 1 - hi, hi: 1 - lo, label: p === 0 ? "100%" : fmtPct(1 - p, p < 0.001 ? 2 : 1) } : { value: p, lo, hi, label: stabLbl(p) };
  };
  const all: StudioRow[] = cells.map(({ r, d, c, t }) => {
    if (!c) return { ...rowBase(r), value: null, label: "", empty: t0 === "t0" && d ? "API rejects temperature" : "not measured" };
    return { ...rowBase(r), ...fig(c), ...(t ? { t0: fig(t) } : {}) };
  });
  const rows = hideUnmeasured ? all.filter((x) => x.value != null) : all;
  const agreeLo = Math.min(1, ...rows.flatMap((x) => (x.value == null ? [1] : [x.lo ?? x.value, ...(x.t0 ? [x.t0.lo ?? x.t0.value] : [])])));
  const agreeDomain: [number, number] = [Math.max(0, Math.floor((agreeLo - 0.003) * 200) / 200), 1];
  const hasT0 = sel.some((r) => detFor(r, arm, "t0"));
  return { rows, sameRuns, runsNotes, agreeDomain, hasT0 };
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

/**
 * The Stability caption. `t0` is the mode as drawn: in `t0` the first line says where temperature 0 applies; in the paired modes the measured-where
 * line gains "; temperature-0 reruns shown as lighter bars" / "hollow dots". The `dots` mode is a dot chart whatever `chart` says (the studio draws it so).
 */
export function stabCaption(chart: StabChart, t0: StabT0, sameRuns: string | null, whiskers = true, runsNotes: string[] = []): string[] {
  const only = t0 === "t0" ? " Temperature 0 where the API accepts it; deciders expose no sampling control." : "";
  const reruns = t0 === "paired" ? "; temperature-0 reruns shown as lighter bars" : t0 === "dots" ? "; temperature-0 reruns shown as hollow dots" : "";
  // the runs per model, with the models that depart from them named ("5 runs · 2,400 decisions per model; Gemma 3 12B: 4 runs")
  const runs = sameRuns ? ` (${sameRuns} per model${runsNotes.length ? `; ${runsNotes.join("; ")}` : ""})` : " scored 5 times";
  const where = `Measured on ${MEASURED_ON}${runs}; the same cells are shown for every corpus${reruns}.`;
  const mark = chart === "dots" || t0 === "dots" ? "Dot" : "Bar";
  if (chart === "agree") return [`${mark}: agreement, the probability two identical runs give the same decision (1 − pairwise disagreement)${whiskers ? "; whisker: 95% bootstrap interval" : ""}. Axis zoomed to the measured range.${only}`, where];
  return [`${mark}: probability two identical runs disagree on a decision (pairwise)${whiskers ? "; whisker: 95% bootstrap interval over decisions" : ""}.${only}`, where];
}

/** Axis titles, as the studio writes them. */
export const costAxis = (chart: CostChart, unit: CostUnit, scale: CostScale) => COST_UNIT[unit].axis + (chart === "dots" || scale === "log" ? " (log)" : "");
export const speedAxis = (chart: SpeedChart) => (chart === "throughput" ? "sequential documents per hour (3,600,000 ÷ median ms per document)" : `median latency per document${chart === "dots" ? " (log)" : ""}`);
export const stabAxis = (chart: StabChart, t0: StabT0) => (chart === "agree" ? `agreement: probability two identical runs give the same decision${t0 === "t0" ? " · temperature 0" : ""}` : `probability two identical runs disagree${t0 === "t0" ? " · temperature 0" : ""}`);
