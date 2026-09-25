/**
 * Tick density (the studio's Gridlines control, StudioPage.tsx, `studio-ticks`; every chart on the site draws `normal`): how many ticks, and so
 * gridlines, an axis carries. `normal` is each chart's own rule, unchanged from before the control. `sparse`, `dense` and `fine` aim at about
 * 4, 11 and 21 ticks across the axis (TARGET intervals) and are then kept in order (sparse coarser than normal, dense finer, fine finer than dense),
 * so every setting differs from its neighbours on every domain. `none` keeps the normal ticks' labels and draws no gridline (a preset can do the
 * same through `--grid: transparent`, as Journal does in high contrast; the two compose). Ticks and gridlines always share a step; where labels
 * would touch, every n-th tick is labelled and every tick keeps its line (labelEvery, labelledAt; PRRail did this first).
 *
 * Percent axes (the recall/precision map, PRScatter.tsx; the ranked view, PRRail.tsx): pctStep picks from PCT_STEPS. Linear axes (StudioCharts.tsx
 * StudioBars: Cost linear, Speed, Stability; StudioScatter's y): linTicks with linTarget intervals. Log axes (the dot plots, Cost log, the cost
 * scatter's x): logTicks, decades plus what the density adds inside each.
 */
export type TickDensity = "none" | "sparse" | "normal" | "dense" | "fine";
export const TICK_DENSITIES: { id: TickDensity; label: string; title: string }[] = [
  { id: "none", label: "none", title: "No gridlines; the axes keep their normal tick labels" },
  { id: "sparse", label: "sparse", title: "About 4 ticks across the axis, one nice step coarser than normal (25% on 0–100%, 10% on a fitted map); log axes: decades only" },
  { id: "normal", label: "normal", title: "The site's own ticks: about 6 across the axis (20% on 0–100%, 5% on a fitted map); log axes: decades, with 2× and 5× when there are fewer than three" },
  { id: "dense", label: "dense", title: "About 11 ticks, one step finer than normal (10% on 0–100%, 2% on a fitted map); log axes: 1, 2 and 5 in every decade" },
  { id: "fine", label: "fine", title: "About 21 ticks, two steps finer (5% on 0–100%, 1% on a fitted map), labelled every other one where they would touch; log axes: every integer in each decade, 1, 2 and 5 labelled" },
];
export const isTickDensity = (s: string | null): s is TickDensity => TICK_DENSITIES.some((d) => d.id === s);
/** Whether gridlines are drawn at all: `none` drops the lines and keeps the labels. */
export const gridOn = (d: TickDensity) => d !== "none";
/** The step rule a density uses: `none` ticks like `normal`. */
const rule = (d: TickDensity): Exclude<TickDensity, "none"> => (d === "none" ? "normal" : d);

/** Target number of intervals across an axis; `normal` is each chart's own rule (5 on the linear axes, the span thresholds on the percent ones). */
const TARGET = { sparse: 3, normal: 5, dense: 10, fine: 20 } as const;
/** Nice percent steps. 25 is the ranked view's own full-range step, 50 only ever `sparse` above it. */
const PCT_STEPS = [1, 2, 5, 10, 20, 25, 50];

/**
 * The percent step of a 0–1 axis `span` wide: `normal` (and `none`) is the chart's own `normalStep` (PRScatter and PRRail differ); the others pick
 * the PCT_STEPS entry whose interval count is nearest the density's target (in ratio), then hold their order: sparse strictly coarser than normal,
 * dense strictly finer, fine strictly finer than dense (down to 1%), so no two settings coincide on a domain where the targets would.
 */
export function pctStep(d: TickDensity, span: number, normalStep: number): number {
  const r = rule(d);
  if (r === "normal") return normalStep;
  const n = span * 100;
  const nearest = (target: number) => PCT_STEPS.reduce((best, st) => (Math.abs(Math.log(n / st / target)) < Math.abs(Math.log(n / best / target)) ? st : best));
  const coarser = (st: number) => PCT_STEPS.find((x) => x > st) ?? st;
  const finer = (st: number) => PCT_STEPS.filter((x) => x < st).pop() ?? st;
  if (r === "sparse") { const st = nearest(TARGET.sparse); return st > normalStep ? st : coarser(normalStep); }
  const dense = (() => { const st = nearest(TARGET.dense); return st < normalStep ? st : finer(normalStep); })();
  if (r === "dense") return dense;
  const st = nearest(TARGET.fine);
  return st < dense ? st : finer(dense);
}
/** Ticks every `step` percent from `lo` to `hi` (0–1 fractions), counted in whole steps so a bound on a step (65% at 5%) always gets its tick. */
export function pctTicks(lo: number, hi: number, step: number): number[] {
  const out: number[] = [];
  for (let k = Math.ceil((lo * 100) / step - 1e-6); k * step <= hi * 100 + 1e-6; k++) out.push((k * step) / 100);
  return out;
}

/** About `target` intervals (StudioBars' own rule at 5): the span over the target, rounded to 1, 2, 2.5 or 5 × a power of ten. */
export const linTarget = (d: TickDensity) => TARGET[rule(d)];
export function linTicks(d0: number, d1: number, target = 5): number[] {
  const span = d1 - d0;
  if (!(span > 0)) return [d0];
  const raw = span / target, mag = 10 ** Math.floor(Math.log10(raw)), r = raw / mag;
  const step = (r >= 5 ? 5 : r >= 2.5 ? 2.5 : r >= 2 ? 2 : 1) * mag;
  const out: number[] = [];
  for (let t = Math.ceil(d0 / step - 1e-9) * step; t <= d1 + 1e-9; t += step) out.push(+t.toPrecision(12));
  return out;
}

/** A log-axis tick: its value, mantissa (1–9) and exponent, and whether it carries a label. */
export type LogTick = { t: number; m: number; e: number; label: boolean };
/**
 * Log-axis ticks from the decade at or below `d0` to the one at or above `d1`: `normal` (and `none`) is the charts' own rule, decades with 2× and 5×
 * added when there are fewer than three decades; `sparse` decades only; `dense` 1, 2 and 5 in every decade; `fine` every integer mantissa, with labels
 * on 1, 2 and 5 only (the rest are gridlines).
 */
export function logTicks(d0: number, d1: number, d: TickDensity = "normal"): LogTick[] {
  const r = rule(d);
  const a = Math.floor(Math.log10(d0)), b = Math.ceil(Math.log10(d1));
  const mant = r === "sparse" ? [1] : r === "dense" ? [1, 2, 5] : r === "fine" ? [1, 2, 3, 4, 5, 6, 7, 8, 9] : b - a < 3 ? [1, 2, 5] : [1];
  const out: LogTick[] = [];
  for (let e = a; e <= b; e++) {
    for (const m of mant) {
      const t = +(m * 10 ** e).toPrecision(12);
      // the normal rule keeps 2× and 5× strictly inside the top of the domain, as it always has
      const inside = r === "normal" && m !== 1 ? t < d1 : t <= d1 + 1e-12;
      if (t >= d0 - 1e-12 && inside) out.push({ t, m, e, label: m === 1 || m === 2 || m === 5 });
    }
  }
  return out.sort((x, y) => x.t - y.t);
}
/**
 * Thins a log axis's labels to what fits, given the widest label's length along the axis and a decade's length in px: 2 and 5 lose their labels when
 * 1→2 (0.3 of a decade, the shortest labelled gap) is shorter than a label, and the decades then go every n-th (labelEvery). Every tick keeps its line.
 */
export function thinLogLabels(ticks: LogTick[], labelPx: number, decadePx: number): LogTick[] {
  const keep25 = labelPx <= Math.log10(2) * decadePx, every = labelEvery(labelPx, decadePx);
  return ticks.map((x) => ({ ...x, label: x.label && (x.m === 1 ? labelledAt(x.e, 1, every) : keep25) }));
}

/** Labels go on every n-th tick when a label `labelPx` long along the axis would touch its neighbour `pxPerTick` away; 1 while they all fit. */
export const labelEvery = (labelPx: number, pxPerTick: number) => Math.max(1, Math.ceil(labelPx / Math.max(1e-6, pxPerTick)));
/** Whether the tick at value `t` (a multiple of `step`) is labelled: every `every`-th step counted from zero, so 5% ticks labelled every other land on the tens. */
export const labelledAt = (t: number, step: number, every: number) => every <= 1 || Math.round(t / step) % every === 0;
