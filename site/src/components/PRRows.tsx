import { useRef } from "react";
import type { CI } from "../data";
import { fmtPct } from "../data";
import type { PRItem } from "./PRScatter";
import { Logo, LogoGlyph } from "../logos";
import { CLICK_HINT, DECIDER_TEXT, TipBox, fadeStyle, selectable, usePresence, useTip, useTween, useWidth } from "./ui";
import { prTip } from "./PRScatter";
import { hoverable } from "./hover";

const ROW = 26, NUM_W = 54;

/** Ranked rows: recall and precision side by side, dot at the point estimate, whisker across the 95% interval. `onSelect` makes each row a button (click, Enter, Space). `highlight` tints the row with that id (cross-chart hover, see hover.tsx); `onHover` reports the row under the pointer or keyboard focus. */
/** Motion (ui.tsx): rows slide to their new rank over 320 ms (a CSS transform on the keyed group), whiskers and dots ease along the axis; rows fade in and out over 150 ms. */
export function PRRows({ items, zoom, sortBy, logos = true, onSelect, highlight, onHover }: { items: PRItem[]; zoom: boolean; sortBy: "recall" | "precision" | "f1"; logos?: boolean; onSelect?: (item: PRItem) => void; highlight?: string | null; onHover?: (id: string | null) => void }) {
  const { tip, show, hide, hostRef } = useTip();
  const pickRow = onSelect && ((it: PRItem) => { hide(); onSelect(it); });
  const W = useWidth(hostRef, 760);
  // In the full-width ranked layout (~1100px) the label column and the gap between the panels grow with the width, so long names keep clear of the whiskers.
  const wide = Math.max(0, W - 760) / 340;
  const LABEL_W = Math.round((logos ? 196 : 170) + Math.min(1, wide) * 44);
  const GAP = Math.round(26 + Math.min(1, wide) * 22);
  const f1 = (it: PRItem) => (it.recall && it.precision ? (2 * it.recall[0] * it.precision[0]) / (it.recall[0] + it.precision[0] || 1) : -1);
  const rows = [...items].sort((a, b) => {
    const va = sortBy === "f1" ? f1(a) : (a[sortBy]?.[0] ?? -1), vb = sortBy === "f1" ? f1(b) : (b[sortBy]?.[0] ?? -1);
    return vb - va;
  });
  const colW = (W - LABEL_W - GAP - 2 * NUM_W) / 2;
  const x0 = [LABEL_W, LABEL_W + colW + NUM_W + GAP];
  const all = rows.flatMap((r) => [r.recall, r.precision]).filter((c): c is NonNullable<CI> => !!c);
  let lo = 0, hi = 1;
  if (zoom && all.length) {
    lo = Math.max(0, Math.min(...all.map((c) => c[1])) - 0.02);
    hi = Math.min(1, Math.max(...all.map((c) => c[2])) + 0.02);
  }
  const sx = (col: number, v: number) => x0[col] + ((v - lo) / (hi - lo || 1)) * colW;
  const span = hi - lo;
  const step = span > 0.6 ? 0.25 : span > 0.3 ? 0.1 : span > 0.12 ? 0.05 : 0.02;
  const ticks: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) ticks.push(Math.round(t * 1000) / 1000);
  const h = rows.length * ROW + 44;
  // Drawn in the order rows first appeared (ui.tsx usePresence), placed by rank with a transform, so a re-sort slides rows instead of moving
  // DOM nodes; rows that just left fade out where they last stood. The whisker ends and dots ease along the axis (useTween).
  const presence = usePresence(items, (it) => it.id);
  const lastTop = useRef(new Map<string, number>());
  rows.forEach((r, i) => lastTop.current.set(r.id, 20 + i * ROW));
  const drawn = presence.map((p) => ({ r: p.item, state: p.state }));
  const target: Record<string, number> = {};
  for (const { r } of drawn) ([r.recall, r.precision] as CI[]).forEach((ci, col) => { if (ci) { target[`${r.id}:${col}:lo`] = sx(col, ci[1]); target[`${r.id}:${col}:hi`] = sx(col, ci[2]); target[`${r.id}:${col}:v`] = sx(col, ci[0]); } });
  const geo = useTween(target, undefined, undefined, W);
  const g = (k: string) => geo[k] ?? target[k];
  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
        {[0, 1].map((col) => (
          <g key={col}>
            <text x={x0[col]} y={12} fontSize={12} fontWeight={500} fill="var(--ink)">{col === 0 ? "Recall" : "Precision"}</text>
            {ticks.map((t) => (
              <g key={t}>
                <line x1={sx(col, t)} x2={sx(col, t)} y1={20} y2={20 + rows.length * ROW} stroke="var(--grid)" />
                <text x={sx(col, t)} y={20 + rows.length * ROW + 14} fontSize={10} textAnchor="middle" fill="var(--ink-3)" className="mono">{Math.round(t * 100)}%</text>
              </g>
            ))}
          </g>
        ))}
        {drawn.map(({ r, state }) => {
          // the row's group is translated to its rank (CSS transition on transform); everything inside is drawn at y = 0..ROW
          const top = lastTop.current.get(r.id) ?? 20, y = ROW / 2, label = `${r.name}${r.subset ? " *" : ""}`;
          return (
            <g key={r.id} className={`mv fd${highlight === r.id ? " hl" : ""}`} style={{ transform: `translate(0px, ${top}px)`, ...fadeStyle(state) }} {...hoverable(onHover, r.id)}>{/* cross-chart hover (hover.tsx) wraps the tooltip group */}
            <g onMouseMove={(e) => show(e, { kind: "row", top, height: ROW, clearX: W }, prTip(r, logos ? <Logo model={r.id} size={12} /> : undefined))} onMouseLeave={hide} {...selectable(pickRow, r, r.name)}>
              <rect className="hit" x={0} y={0} width={W} height={ROW} fill="transparent" />
              {logos ? (
                <>
                  
                  <g color="var(--ink-2)"><LogoGlyph model={r.id} cx={8} cy={y} /></g>
                  <text x={22} y={y + 4} fontSize={12} fill="var(--ink-2)" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
                </>
              ) : (
                <text x={LABEL_W - 12} y={y + 4} textAnchor="end" fontSize={12} fill="var(--ink-2)" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
              )}
              {([r.recall, r.precision] as CI[]).map((ci, col) =>
                ci ? (
                  <g key={col}>
                    <line x1={g(`${r.id}:${col}:lo`)} x2={g(`${r.id}:${col}:hi`)} y1={y} y2={y} stroke={r.color} strokeWidth={1.5} strokeLinecap="butt" />
                    <circle cx={g(`${r.id}:${col}:v`)} cy={y} r={3.2} fill={r.color} />
                    <text x={x0[col] + colW + 8} y={y + 4} fontSize={11.5} fill="var(--ink)" className="mono">{fmtPct(ci[0])}</text>
                  </g>
                ) : (
                  <text key={col} x={x0[col] + colW + 8} y={y + 4} fontSize={11.5} fill="var(--ink-4)" className="mono">—</text>
                ),
              )}
            </g>
            </g>
          );
        })}
        {rows.length === 0 && <text x={W / 2} y={40} textAnchor="middle" fontSize={13} fill="var(--ink-4)">Select at least one model.</text>}
      </svg>
      <TipBox tip={tip} hint={onSelect ? CLICK_HINT : undefined} />
    </div>
  );
}
