import { useId, useRef } from "react";
import type { CI } from "../data";
import { fmtPct, fmtRange } from "../data";
import { Logo, LogoGlyph } from "../logos";
import type { MarkShape, PRItem } from "./PRScatter";
import { Mark, NAME_CLS, prTip } from "./PRScatter";
import { CLICK_HINT, DECIDER_TEXT, ROW_PULSE_MS, RowTint, TipBox, fadeStyle, selectable, usePresence, usePulseWindow, useTip, useTween, useWidth } from "./ui";
import { hoverable } from "./hover";
import { useTextMeasure } from "./measure";
import { PlotBgPattern, type PlotBg } from "./plotBg";

/** Row geometry (row height, value column) shared with PRHeat so the two ranked views keep rows in place; RAIL is the rank rail at the left edge, RANK_W the `01`–`12` numerals, RANGE_W the muted "82–91" interval column after each value. */
const ROW0 = 26, NUM_W0 = 54, RANGE_W0 = 52, RAIL = 3, RANK_W0 = 26, TOP0 = 20;

/**
 * Ranked rows on a rank rail (the Compare models `ranked` view): recall and precision side by side, dot at the point estimate, whisker
 * across the 95% interval, on a dot-matrix. A thin uniform rail at the left edge, with muted `01`–`12` numerals; hairline
 * separators and faint alternate banding. After each value the interval's ends are printed in muted ink. Every row is drawn the same.
 * Hover tooltip, click-to-details, cross-card highlight (hover.tsx), presence fades and the emphasis tint (ui.tsx RowTint)
 * follow the same contract as OpsBars and Consistency.
 */
/** `range` (the screenshot studio) fixes both panels' axis to an explicit 0–1 range, overriding `zoom`. */
/** `textScale` (the studio's Text control; 1 on the site) multiplies every font size and the row geometry (row height, label and value columns) with it. Whisker width and dot radius read --sw-mult / --r-add (styles.css, the studio's high-contrast block); `mark` (the studio's Marks control; `dot` on the site) is the point shape (PRScatter.tsx Mark). */
/** `bg` (the studio's Background control; the site's dot matrix, `dots`) is the pattern behind each panel's rows (plotBg.tsx). */
export function PRRail({ items, zoom, range, sortBy = "recall", logos = false, onSelect, highlight, onHover, textScale = 1, mark = "dot", bg = "dots" }: { items: PRItem[]; zoom: boolean; range?: [number, number]; sortBy?: "recall" | "precision" | "f1"; logos?: boolean; onSelect?: (item: PRItem) => void; highlight?: string | null; onHover?: (id: string | null) => void; textScale?: number; mark?: MarkShape; bg?: PlotBg }) {
  const { tip, show, hide, hostRef } = useTip();
  const bgId = `bg-${useId().replace(/[^A-Za-z0-9_-]/g, "")}`;
  const pickRow = onSelect && ((it: PRItem) => { hide(); onSelect(it); });
  const W = useWidth(hostRef, 760);
  const s = textScale, ROW = ROW0 * s, NUM_W = NUM_W0 * s, RANGE_W = RANGE_W0 * s, RANK_W = RANK_W0 * s, TOP = TOP0 * s;
  const wide = Math.min(1, Math.max(0, W - 760) / 340);
  // text widths as drawn (measure.tsx): the name column grows past its default when a name (with the glyph, or right-aligned after the rank numeral) would not fit it
  const { measure, probes } = useTextMeasure([NAME_CLS, { key: "dec", className: NAME_CLS, style: DECIDER_TEXT }, "mono"]);
  const labelOf = (it: PRItem) => `${it.name}${it.subset ? " *" : ""}`;
  const nameW = Math.max(0, ...items.map((it) => measure(labelOf(it), 12 * s, it.decider ? "dec" : NAME_CLS)));
  const LABEL_W = Math.max(Math.round(((logos ? 196 : 190) + wide * 44) * s) + RANK_W, Math.ceil(RANK_W + nameW + (logos ? 38 : 22) * s));
  const GAP = Math.round(26 + wide * 22);
  const NUMS = NUM_W + RANGE_W;
  const f1 = (it: PRItem) => (it.recall && it.precision ? (2 * it.recall[0] * it.precision[0]) / (it.recall[0] + it.precision[0] || 1) : -1);
  const rows = [...items].sort((a, b) => {
    const va = sortBy === "f1" ? f1(a) : (a[sortBy]?.[0] ?? -1), vb = sortBy === "f1" ? f1(b) : (b[sortBy]?.[0] ?? -1);
    return vb - va;
  });
  const n = rows.length;
  const colW = (W - LABEL_W - GAP - 2 * NUMS) / 2;
  const x0 = [LABEL_W, LABEL_W + colW + NUMS + GAP];
  const all = rows.flatMap((r) => [r.recall, r.precision]).filter((c): c is NonNullable<CI> => !!c);
  let lo = 0, hi = 1;
  if (range) [lo, hi] = range;
  else if (zoom && all.length) {
    lo = Math.max(0, Math.min(...all.map((c) => c[1])) - 0.02);
    hi = Math.min(1, Math.max(...all.map((c) => c[2])) + 0.02);
  }
  const sx = (col: number, v: number) => x0[col] + ((v - lo) / (hi - lo || 1)) * colW;
  const span = hi - lo;
  const step = span > 0.6 ? 0.25 : span > 0.3 ? 0.1 : span > 0.12 ? 0.05 : 0.02;
  const ticks: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) ticks.push(Math.round(t * 1000) / 1000);
  // every tick keeps its gridline; labels ("100%" at its measured width, 8 s apart) go on every n-th tick when adjacent ones would touch (large text in a narrow panel)
  const tickW = measure("100%", 10 * s, "mono") + 8 * s;
  const labelEvery = Math.max(1, Math.ceil(tickW / ((colW * step) / (span || 1))));
  const h = n * ROW + 44 * s;
  // rows drawn in first-appearance order and placed by rank with a transform (ui.tsx usePresence), so a re-sort slides them
  const presence = usePresence(items, (it) => it.id);
  const lastTop = useRef(new Map<string, number>());
  rows.forEach((r, i) => lastTop.current.set(r.id, TOP + i * ROW));
  const drawn = presence.map((p) => ({ r: p.item, state: p.state }));
  const target: Record<string, number> = {};
  for (const { r } of drawn) ([r.recall, r.precision] as CI[]).forEach((ci, col) => { if (ci) { target[`${r.id}:${col}:lo`] = sx(col, ci[1]); target[`${r.id}:${col}:hi`] = sx(col, ci[2]); target[`${r.id}:${col}:v`] = sx(col, ci[0]); } });
  const geo = useTween(target, undefined, undefined, W);
  const g = (k: string) => geo[k] ?? target[k];
  // An emphasised row (`emphasis: true`, the decision-model rows on Compare models) carries a faint tint that breathes for a few cycles when the table loads or its rows change (ui.tsx usePulseWindow, RowTint).
  const sig = items.map((it) => `${it.id}:${it.recall?.[0].toFixed(4) ?? "-"}:${it.precision?.[0].toFixed(4) ?? "-"}`).join("|");
  const pulsing = usePulseWindow(sig, items.some((it) => it.emphasis), ROW_PULSE_MS);
  return (
    <>
      <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
          <defs>
            <PlotBgPattern id={bgId} kind={bg} s={s} step={10} opacity={0.8} />
          </defs>
          {/* rank-indexed furniture: banding, separators, rail and numerals stay put while the rows slide between ranks */}
          {rows.map((_, i) => (
            <g key={i}>
              {i % 2 === 1 && <rect x={RAIL + 4} y={TOP + i * ROW} width={Math.max(0, W - RAIL - 4)} height={ROW} fill="var(--ink)" fillOpacity={0.018} />}
              <line x1={RAIL + 4} x2={W} y1={TOP + (i + 1) * ROW} y2={TOP + (i + 1) * ROW} stroke="var(--line)" />
              <rect x={0} y={TOP + i * ROW + 1} width={RAIL} height={ROW - 2} rx={1.5} fill="var(--ink)" fillOpacity={0.45} />
              <text x={RAIL + 10 * s} y={TOP + i * ROW + ROW / 2 + 4 * s} fontSize={10.5 * s} fill="var(--ink-4)" className="mono">{String(i + 1).padStart(2, "0")}</text>
            </g>
          ))}
          {n > 0 && <line x1={RAIL + 4} x2={W} y1={TOP} y2={TOP} stroke="var(--line-2)" />}
          {[0, 1].map((col) => (
            <g key={col}>
              {bg !== "none" && <rect x={x0[col]} y={TOP} width={Math.max(0, colW)} height={n * ROW} fill={`url(#${bgId})`} />}
              <text x={x0[col]} y={12 * s} fontSize={12 * s} fontWeight={500} fill="var(--ink)" className="ax">{col === 0 ? "Recall" : "Precision"}</text>
              <text x={x0[col] + colW + NUMS - 2} y={12 * s} textAnchor="end" fontSize={10 * s} fontWeight={500} letterSpacing=".06em" fill="var(--ink-3)">95% CI</text>
              {ticks.map((t, i) => (
                <g key={t}>
                  <line className="gl" x1={sx(col, t)} x2={sx(col, t)} y1={TOP} y2={TOP + n * ROW} stroke="var(--line)" />
                  {i % labelEvery === 0 && <text x={sx(col, t)} y={TOP + n * ROW + 14 * s} fontSize={10 * s} textAnchor="middle" fill="var(--ink-3)" className="mono">{Math.round(t * 100)}%</text>}
                </g>
              ))}
            </g>
          ))}
          {drawn.map(({ r, state }) => {
            const top = lastTop.current.get(r.id) ?? TOP, y = ROW / 2, label = labelOf(r);
            return (
              <g key={r.id} className={`mv fd${highlight === r.id ? " hl" : ""}`} transform={`translate(0 ${top})`} style={fadeStyle(state)} {...hoverable(onHover, r.id)}>
                <g onMouseMove={(e) => show(e, { kind: "row", top, height: ROW, clearX: W }, prTip(r, logos ? <Logo model={r.id} size={12} /> : undefined))} onMouseLeave={hide} {...selectable(pickRow, r, r.name)}>
                  {r.emphasis && <RowTint sig={sig} pulsing={pulsing} width={W} height={ROW} />}
                  <rect className="hit" x={0} y={0} width={W} height={ROW} fill="transparent" />
                  {logos ? (
                    <>
                      <g color="var(--ink-2)"><LogoGlyph model={r.id} cx={RANK_W + 12 * s} cy={y} size={13 * s} /></g>
                      <text x={RANK_W + 26 * s} y={y + 4 * s} fontSize={12 * s} fill="var(--ink-2)" className="nm" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
                    </>
                  ) : (
                    <text x={LABEL_W - 12 * s} y={y + 4 * s} textAnchor="end" fontSize={12 * s} fill="var(--ink-2)" className="nm" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
                  )}
                  {([r.recall, r.precision] as CI[]).map((ci, col) =>
                    ci ? (
                      <g key={col}>
                        <line x1={g(`${r.id}:${col}:lo`)} x2={g(`${r.id}:${col}:hi`)} y1={y} y2={y} stroke={r.color} strokeWidth={1.5} style={{ strokeWidth: "calc(1.5 * var(--sw-mult, 1))" }} />
                        <Mark shape={mark} cx={g(`${r.id}:${col}:v`)} cy={y} r={3.2} color={r.color} />
                        <text x={x0[col] + colW + NUM_W} y={y + 4 * s} textAnchor="end" fontSize={11.5 * s} fill="var(--ink)" className="mono">{fmtPct(ci[0])}</text>
                        <text x={x0[col] + colW + NUMS - 2} y={y + 4 * s} textAnchor="end" fontSize={10.5 * s} fill="var(--ink-4)" className="mono">{fmtRange(ci)}</text>
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
      <div className="legend-note">
        <span>Dot: point estimate. Whisker and range: 95% interval.</span>
        {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
      </div>
    </>
  );
}
