import { useId, useRef } from "react";
import type { CI } from "../data";
import { fmtPct, fmtRange } from "../data";
import { Logo, LogoGlyph, isJev, logoShown, logosMode, type LogosMode } from "../logos";
import type { IntervalMode, MarkShape, PRItem } from "./PRScatter";
import { AXIS_TICK, Mark, NAME_CLS, prTip } from "./PRScatter";
import { CLICK_HINT, DECIDER_TEXT, ROW_PULSE_MS, RowTint, TipBox, fadeStyle, selectable, usePresence, usePulseWindow, useTip, useTween, useWidth } from "./ui";
import { hoverable } from "./hover";
import { useTextMeasure } from "./measure";
import { PlotBgPattern, type PlotBg } from "./plotBg";
import { gridOn, labelEvery, labelledAt, pctStep, pctTicks, type TickDensity } from "./ticks";

/** Row geometry (row height, value column) shared with PRHeat so the two ranked views keep rows in place; RAIL is the rank rail at the left edge, RANK_W the `01`–`12` numerals, RANGE_W the muted "82–91" interval column after each value. */
const ROW0 = 26, NUM_W0 = 54, RANGE_W0 = 52, RAIL = 3, RANK_W0 = 26, TOP0 = 20;
/** The forest plot's figure column: "100.0 [100.0, 100.0]" at 11 px tabular figures, with a gap to the error bars. */
const FOREST_W0 = 132;

/**
 * Ranked rows on a rank rail (the Compare models `ranked` view): recall and precision side by side, dot at the point estimate, whisker
 * across the 95% interval, on a dot-matrix. A thin uniform rail at the left edge, with muted `01`–`12` numerals; hairline
 * separators and faint alternate banding. After each value the interval's ends are printed in muted ink. Every row is drawn the same.
 * Hover tooltip, click-to-details, cross-card highlight (hover.tsx), presence fades and the emphasis tint (ui.tsx RowTint)
 * follow the same contract as OpsBars and Consistency.
 */
/** `range` (the screenshot studio) fixes both panels' axis to an explicit 0–1 range, overriding `zoom`. */
/** `textScale` (the studio's Text control; 1 on the site) multiplies every font size and the row geometry (row height, label and value columns) with it. Whisker width and dot radius read --sw-mult / --r-add (styles.css, the studio's high-contrast block); `mark` (the studio's Marks control; `dot` on the site) is the point shape (PRScatter.tsx Mark). */
/** `logos` (logos.tsx LogosMode, or the boolean it was; off on the site): which rows carry their vendor glyph before the name; in `jev` the name column keeps the glyph layout and only the Jev rows fill the slot. A Jev row's point marks read the studio's Jev mark size (--mark-jev). */
/** `bg` (the studio's Background control; the site's dot matrix, `dots`) is the pattern behind each panel's rows (plotBg.tsx). */
/** `interval` (the studio's Interval control, PRScatter.tsx IntervalMode; `box` on the site) maps onto the row's one horizontal interval mark: `box` and `ellipse` keep the plain line the site draws; `whiskers`, `band` and `bracket` add end caps to it; `none` drops it (the point and the printed range stay). */
/** `ticks` (the studio's Gridlines control; `normal` on the site) is the tick and gridline density of the shared percent range (ticks.ts TickDensity). */
/** The ranked view's metrics: the two columns the site draws, and F1 (the studio, `f1` on). */
export type RailMetric = "recall" | "precision" | "f1";
export type SortDir = "desc" | "asc";
export const RAIL_METRIC_LABEL: Record<RailMetric, string> = { recall: "Recall", precision: "Precision", f1: "F1" };
/** The order the rows have always had: recall, best first. */
export const RAIL_SORT_DEFAULT: { by: RailMetric; dir: SortDir } = { by: "recall", dir: "desc" };
/** `f1` adds a third column, F1 with its interval (PRItem.f1; sweep.ts f1CI), after Precision. `sortBy` / `sortDir` order the rows (RAIL_SORT_DEFAULT: recall, best first); with `onSort` the column headers are sort controls: click one to rank by it, click it again to flip the direction, the arrow marks the one in force. */
/** `forest` (the studio's Journal (academic) style) draws the rows as a forest plot: no rank rail, numerals or banding; each column a bare axis line with outward ticks; the point with a capped error bar; one right-hand figure column, "estimate [lo, hi]" in percent to one decimal. `shapeOf` gives each row its own mark shape (PRScatter.tsx); `note` false drops the legend note under the rows (the studio's figure caption replaces it). */
export function PRRail({ items, zoom, range, sortBy = RAIL_SORT_DEFAULT.by, sortDir = RAIL_SORT_DEFAULT.dir, onSort, f1: f1On = false, logos: logosIn, onSelect, highlight, onHover, textScale = 1, mark = "dot", bg = "dots", interval = "box", ticks: density = "normal", forest = false, shapeOf, note = true }: { items: PRItem[]; zoom: boolean; range?: [number, number]; sortBy?: RailMetric; sortDir?: SortDir; onSort?: (by: RailMetric) => void; f1?: boolean; logos?: boolean | LogosMode; onSelect?: (item: PRItem) => void; highlight?: string | null; onHover?: (id: string | null) => void; textScale?: number; mark?: MarkShape; bg?: PlotBg; interval?: IntervalMode; ticks?: TickDensity; forest?: boolean; shapeOf?: (id: string) => MarkShape; note?: boolean }) {
  const { tip, show, hide, hostRef } = useTip();
  const whisker = interval !== "none", caps = forest || interval === "whiskers" || interval === "band" || interval === "bracket";
  const logosOn = logosMode(logosIn, false), logos = logosOn !== "none";
  const glyphOf = (r: PRItem) => logoShown(logosOn, r.id);
  const bgId = `bg-${useId().replace(/[^A-Za-z0-9_-]/g, "")}`;
  const pickRow = onSelect && ((it: PRItem) => { hide(); onSelect(it); });
  const W = useWidth(hostRef, 760);
  // the forest plot's one figure column ("86.3 [77.0, 92.2]") replaces the value and range columns, and there is no rank numeral
  const s = textScale, ROW = ROW0 * s, NUM_W = (forest ? 0 : NUM_W0) * s, RANGE_W = (forest ? FOREST_W0 : RANGE_W0) * s, RANK_W = (forest ? 6 : RANK_W0) * s, TOP = TOP0 * s;
  const tk = forest ? AXIS_TICK * s : 0;
  /** A forest-plot figure: percent to one decimal, no sign. */
  const pct1 = (v: number) => (v * 100).toFixed(1);
  const forestCell = (ci: NonNullable<CI>, point: boolean) => (point ? `${pct1(ci[0])} [—]` : `${pct1(ci[0])} [${pct1(ci[1])}, ${pct1(ci[2])}]`);
  const wide = Math.min(1, Math.max(0, W - 760) / 340);
  // text widths as drawn (measure.tsx): the name column grows past its default when a name (with the glyph, or right-aligned after the rank numeral) would not fit it
  const { measure, probes } = useTextMeasure([NAME_CLS, { key: "dec", className: NAME_CLS, style: DECIDER_TEXT }, "mono"]);
  const labelOf = (it: PRItem) => `${it.name}${it.subset ? " *" : ""}`;
  const nameW = Math.max(0, ...items.map((it) => measure(labelOf(it), 12 * s, it.decider ? "dec" : NAME_CLS)));
  const LABEL_W = Math.max(Math.round(((logos ? 196 : 190) + wide * 44) * s) + RANK_W, Math.ceil(RANK_W + nameW + (logos ? 38 : 22) * s));
  const GAP = Math.round(26 + wide * 22);
  const NUMS = NUM_W + RANGE_W;
  // the columns drawn, and an item's interval in each: F1 is the item's own (sweep.ts f1Of / recut) where the chart carries it, else the point from its recall and precision (the sort key the view always had)
  const cols: RailMetric[] = f1On ? ["recall", "precision", "f1"] : ["recall", "precision"];
  const f1Point = (it: PRItem): CI => (it.recall && it.precision && it.recall[0] + it.precision[0] > 0 ? [(2 * it.recall[0] * it.precision[0]) / (it.recall[0] + it.precision[0]), NaN, NaN] : null);
  const valueOf = (it: PRItem, m: RailMetric): CI => (m === "f1" ? it.f1 ?? f1Point(it) : it[m]);
  const key = (it: PRItem) => valueOf(it, sortBy)?.[0] ?? -1;
  const rows = [...items].sort((a, b) => (sortDir === "desc" ? key(b) - key(a) : key(a) - key(b)));
  const n = rows.length, k = cols.length;
  const colW = (W - LABEL_W - (k - 1) * GAP - k * NUMS) / k;
  const x0 = cols.map((_, i) => LABEL_W + i * (colW + NUMS + GAP));
  const cells = (r: PRItem): CI[] => cols.map((m) => { const c = valueOf(r, m); return c && Number.isFinite(c[1]) ? c : c ? [c[0], c[0], c[0]] : null; });
  const all = rows.flatMap(cells).filter((c): c is NonNullable<CI> => !!c);
  let lo = 0, hi = 1;
  if (range) [lo, hi] = range;
  else if (zoom && all.length) {
    lo = Math.max(0, Math.min(...all.map((c) => c[1])) - 0.02);
    hi = Math.min(1, Math.max(...all.map((c) => c[2])) + 0.02);
  }
  const sx = (col: number, v: number) => x0[col] + ((v - lo) / (hi - lo || 1)) * colW;
  const span = hi - lo;
  // the tick step in percent (ticks.ts): the rail's own at `normal` (25% across the full range, 5% on a fitted one), the density's around it
  const step = pctStep(density, span, span > 0.6 ? 25 : span > 0.3 ? 10 : span > 0.12 ? 5 : 2);
  const ticks = pctTicks(lo, hi, step), grid = gridOn(density);
  // a tick label's centre, kept so its box (measured) stays inside the column: the edge labels ("100%" at the right, "0%" at the left) would
  // otherwise straddle the column's edge, the right one reaching under the value column's figures; `shift` is how far that moves a label
  const halfW = (t: number) => measure(`${Math.round(t * 100)}%`, 10 * s, "mono") / 2;
  const tickLabelX = (col: number, t: number) => Math.min(Math.max(sx(col, t), x0[col] + halfW(t)), x0[col] + colW - halfW(t));
  const shift = ticks.length ? Math.max(0, ...[ticks[0], ticks[ticks.length - 1]].map((t) => Math.abs(tickLabelX(0, t) - sx(0, t)))) : 0;
  // every tick keeps its gridline; labels ("100%" at its measured width, 8 s apart, plus what the edge clamp moves one by) go on every n-th tick when
  // adjacent ones would touch (large text in a narrow panel, or a fine density)
  const tickW = measure("100%", 10 * s, "mono") + 8 * s + shift;
  const every = labelEvery(tickW, (colW * step) / 100 / (span || 1));
  const h = n * ROW + 44 * s + tk;
  // rows drawn in first-appearance order and placed by rank with a transform (ui.tsx usePresence), so a re-sort slides them
  const presence = usePresence(items, (it) => it.id);
  const lastTop = useRef(new Map<string, number>());
  rows.forEach((r, i) => lastTop.current.set(r.id, TOP + i * ROW));
  const drawn = presence.map((p) => ({ r: p.item, state: p.state }));
  const target: Record<string, number> = {};
  for (const { r } of drawn) cells(r).forEach((ci, col) => { if (ci) { target[`${r.id}:${col}:lo`] = sx(col, ci[1]); target[`${r.id}:${col}:hi`] = sx(col, ci[2]); target[`${r.id}:${col}:v`] = sx(col, ci[0]); } });
  const geo = useTween(target, undefined, undefined, W);
  const g = (k: string) => geo[k] ?? target[k];
  // An emphasised row (`emphasis: true`, the decision-model rows on Compare models) carries a faint tint that breathes for a few cycles when the table loads or its rows change (ui.tsx usePulseWindow, RowTint).
  const sig = items.map((it) => `${it.id}:${it.recall?.[0].toFixed(4) ?? "-"}:${it.precision?.[0].toFixed(4) ?? "-"}`).join("|");
  const pulsing = usePulseWindow(sig, items.some((it) => it.emphasis), ROW_PULSE_MS);
  // a column whose F1 is a point alone (no counts behind it): the range column prints "—" and the whisker is not drawn
  const pointOnly = (r: PRItem, col: number) => cols[col] === "f1" && !(r.f1 && Number.isFinite(r.f1[1]));
  const anyF1CI = f1On && rows.some((r) => r.f1 && Number.isFinite(r.f1[1])), anyPointOnly = f1On && rows.some((r) => pointOnly(r, cols.indexOf("f1")));
  const sortNonDefault = sortBy !== RAIL_SORT_DEFAULT.by || sortDir !== RAIL_SORT_DEFAULT.dir;
  const arrow = sortDir === "desc" ? "▼" : "▲";
  return (
    <>
      <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
          <defs>
            <PlotBgPattern id={bgId} kind={bg} s={s} step={10} opacity={0.8} />
          </defs>
          {/* rank-indexed furniture: banding, separators, rail and numerals stay put while the rows slide between ranks */}
          {/* the forest plot has none of this furniture: bare rows over each column's axis line */}
          {!forest && rows.map((_, i) => (
            <g key={i}>
              {i % 2 === 1 && <rect x={RAIL + 4} y={TOP + i * ROW} width={Math.max(0, W - RAIL - 4)} height={ROW} fill="var(--ink)" fillOpacity={0.018} />}
              <line x1={RAIL + 4} x2={W} y1={TOP + (i + 1) * ROW} y2={TOP + (i + 1) * ROW} stroke="var(--line)" />
              <rect x={0} y={TOP + i * ROW + 1} width={RAIL} height={ROW - 2} rx={1.5} fill="var(--ink)" fillOpacity={0.45} />
              <text x={RAIL + 10 * s} y={TOP + i * ROW + ROW / 2 + 4 * s} fontSize={10.5 * s} fill="var(--ink-4)" className="mono">{String(i + 1).padStart(2, "0")}</text>
            </g>
          ))}
          {n > 0 && !forest && <line x1={RAIL + 4} x2={W} y1={TOP} y2={TOP} stroke="var(--line-2)" />}
          {cols.map((m, col) => (
            <g key={m}>
              {bg !== "none" && <rect x={x0[col]} y={TOP} width={Math.max(0, colW)} height={n * ROW} fill={`url(#${bgId})`} />}
              {/* the column header; with onSort a sort control (click: rank by it; again: flip), the arrow on the one in force */}
              <g
                onClick={onSort ? () => onSort(m) : undefined} style={onSort ? { cursor: "pointer" } : undefined} role={onSort ? "button" : undefined} tabIndex={onSort ? 0 : undefined}
                onKeyDown={onSort ? (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSort(m); } } : undefined}
                aria-label={onSort ? `sort by ${RAIL_METRIC_LABEL[m]}${sortBy === m ? ` (${sortDir === "desc" ? "best first" : "worst first"}; click to flip)` : ""}` : undefined}
              >
                {onSort && <rect x={x0[col] - 4 * s} y={0} width={Math.max(0, colW + NUMS + 4 * s)} height={18 * s} fill="transparent" />}
                <text x={x0[col]} y={12 * s} fontSize={12 * s} fontWeight={500} fill="var(--ink)" className="ax">{RAIL_METRIC_LABEL[m]}{sortBy === m ? <tspan fontSize={9 * s} fill="var(--ink-3)" dx={4 * s}>{arrow}</tspan> : null}</text>
                <text x={x0[col] + colW + NUMS - 2} y={12 * s} textAnchor="end" fontSize={10 * s} fontWeight={500} letterSpacing={forest ? undefined : ".06em"} fill="var(--ink-3)">{forest ? "% [95% CI]" : "95% CI"}</text>
              </g>
              {/* the forest plot's axis: a line under the rows with outward ticks, the labels past them */}
              {forest && n > 0 && <line x1={x0[col]} x2={x0[col] + colW} y1={TOP + n * ROW} y2={TOP + n * ROW} stroke="var(--axis)" style={{ strokeWidth: "var(--sw-mult, 1)" }} />}
              {ticks.map((t) => (
                <g key={t}>
                  {grid && <line className="gl" x1={sx(col, t)} x2={sx(col, t)} y1={TOP} y2={TOP + n * ROW} stroke="var(--line)" />}
                  {forest && n > 0 && <line x1={sx(col, t)} x2={sx(col, t)} y1={TOP + n * ROW} y2={TOP + n * ROW + tk} stroke="var(--axis)" style={{ strokeWidth: "var(--sw-mult, 1)" }} />}
                  {labelledAt(t * 100, step, every) && <text x={tickLabelX(col, t)} y={TOP + n * ROW + tk + 14 * s} fontSize={10 * s} textAnchor="middle" fill="var(--ink-3)" className="mono">{Math.round(t * 100)}%</text>}
                </g>
              ))}
            </g>
          ))}
          {drawn.map(({ r, state }) => {
            const top = lastTop.current.get(r.id) ?? TOP, y = ROW / 2, label = labelOf(r);
            return (
              <g key={r.id} className={`mv fd${highlight === r.id ? " hl" : ""}`} transform={`translate(0 ${top})`} style={fadeStyle(state)} {...hoverable(onHover, r.id)}>
                <g onMouseMove={(e) => show(e, { kind: "row", top, height: ROW, clearX: W }, prTip(r, glyphOf(r) ? <Logo model={r.id} size={12} /> : undefined))} onMouseLeave={hide} {...selectable(pickRow, r, r.name)}>
                  {r.emphasis && <RowTint sig={sig} pulsing={pulsing} width={W} height={ROW} />}
                  <rect className="hit" x={0} y={0} width={W} height={ROW} fill="transparent" />
                  {logos ? (
                    <>
                      {glyphOf(r) && <g color="var(--ink-2)"><LogoGlyph model={r.id} cx={RANK_W + 12 * s} cy={y} size={13 * s} /></g>}
                      <text x={RANK_W + 26 * s} y={y + 4 * s} fontSize={12 * s} fill="var(--ink-2)" className="nm" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
                    </>
                  ) : (
                    <text x={LABEL_W - 12 * s} y={y + 4 * s} textAnchor="end" fontSize={12 * s} fill="var(--ink-2)" className="nm" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
                  )}
                  {cells(r).map((ci, col) =>
                    ci ? (
                      <g key={col}>
                        {whisker && !pointOnly(r, col) && (
                          <g stroke={r.color} strokeWidth={1.5} style={{ strokeWidth: "calc(1.5 * var(--sw-mult, 1))" }}>
                            <line x1={g(`${r.id}:${col}:lo`)} x2={g(`${r.id}:${col}:hi`)} y1={y} y2={y} />
                            {caps && <line x1={g(`${r.id}:${col}:lo`)} x2={g(`${r.id}:${col}:lo`)} y1={y - 3.5 * s} y2={y + 3.5 * s} />}
                            {caps && <line x1={g(`${r.id}:${col}:hi`)} x2={g(`${r.id}:${col}:hi`)} y1={y - 3.5 * s} y2={y + 3.5 * s} />}
                          </g>
                        )}
                        <Mark shape={shapeOf ? shapeOf(r.id) : mark} cx={g(`${r.id}:${col}:v`)} cy={y} r={3.2} color={r.color} jev={isJev(r.id)} />
                        {forest ? (
                          <text x={x0[col] + colW + NUMS - 2} y={y + 4 * s} textAnchor="end" fontSize={11 * s} fill="var(--ink)" className="mono">{forestCell(ci, pointOnly(r, col))}</text>
                        ) : (
                          <>
                            <text x={x0[col] + colW + NUM_W} y={y + 4 * s} textAnchor="end" fontSize={11.5 * s} fill="var(--ink)" className="mono">{fmtPct(ci[0])}</text>
                            <text x={x0[col] + colW + NUMS - 2} y={y + 4 * s} textAnchor="end" fontSize={10.5 * s} fill="var(--ink-4)" className="mono">{pointOnly(r, col) ? "—" : fmtRange(ci)}</text>
                          </>
                        )}
                      </g>
                    ) : (
                      <text key={col} x={x0[col] + colW + NUM_W} y={y + 4 * s} textAnchor="end" fontSize={11.5 * s} fill="var(--ink-4)" className="mono">—</text>
                    ),
                  )}
                </g>
              </g>
            );
          })}
          {n === 0 && <text x={W / 2} y={40} textAnchor="middle" fontSize={13 * s} fill="var(--ink-4)">Select at least one model.</text>}
          {probes}
        </svg>
        <TipBox tip={tip} hint={onSelect ? CLICK_HINT : undefined} />
      </div>
      {note && (
        <div className="legend-note">
          <span>{whisker ? "Dot: point estimate. Whisker and range: 95% interval." : "Dot: point estimate. Range: 95% interval."}</span>
          {f1On && <span>{anyF1CI ? `F1 interval: delta method over the confusion counts (Takahashi et al. 2022).${anyPointOnly ? " Rows without counts: point alone." : ""}` : "F1: point only, no interval available."}</span>}
          {sortNonDefault && <span>Sorted by {sortBy === "f1" ? "F1" : RAIL_METRIC_LABEL[sortBy].toLowerCase()}, {sortDir === "desc" ? "best first" : "worst first"}.</span>}
          {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
        </div>
      )}
    </>
  );
}
