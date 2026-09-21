import type { CI } from "../data";
import { fmtPct } from "../data";
import type { PRItem } from "./PRScatter";
import { LogoGlyph } from "../logos";
import { CLICK_HINT, TipBox, selectable, useTip, useWidth } from "./ui";

const ROW = 26, NUM_W = 54;

/** Ranked rows: recall and precision side by side, dot at the point estimate, whisker across the 95% interval. `onSelect` makes each row a button (click, Enter, Space). */
export function PRRows({ items, zoom, sortBy, logos = true, onSelect }: { items: PRItem[]; zoom: boolean; sortBy: "recall" | "precision" | "f1"; logos?: boolean; onSelect?: (item: PRItem) => void }) {
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
        {rows.map((r, i) => {
          const y = 20 + i * ROW + ROW / 2;
          return (
            <g key={r.id} onMouseMove={(e) => show(e, { title: r.name, color: r.color, ...r.tip })} onMouseLeave={hide} {...selectable(pickRow, r, r.name)}>
              <rect className="hit" x={0} y={y - ROW / 2} width={W} height={ROW} fill="transparent" />
              {logos ? (
                <>
                  <g color="var(--ink-2)"><LogoGlyph model={r.id} cx={8} cy={y} /></g>
                  <text x={22} y={y + 4} fontSize={12} fill="var(--ink-2)">{r.name}{r.subset ? " *" : ""}</text>
                </>
              ) : (
                <text x={LABEL_W - 12} y={y + 4} textAnchor="end" fontSize={12} fill="var(--ink-2)">{r.name}{r.subset ? " *" : ""}</text>
              )}
              {([r.recall, r.precision] as CI[]).map((ci, col) =>
                ci ? (
                  <g key={col}>
                    <line x1={sx(col, ci[1])} x2={sx(col, ci[2])} y1={y} y2={y} stroke={r.color} strokeWidth={1.5} strokeLinecap="butt" />
                    <circle cx={sx(col, ci[0])} cy={y} r={3.2} fill={r.color} />
                    <text x={x0[col] + colW + 8} y={y + 4} fontSize={11.5} fill="var(--ink)" className="mono">{fmtPct(ci[0])}</text>
                  </g>
                ) : (
                  <text key={col} x={x0[col] + colW + 8} y={y + 4} fontSize={11.5} fill="var(--ink-4)" className="mono">—</text>
                ),
              )}
            </g>
          );
        })}
        {rows.length === 0 && <text x={W / 2} y={40} textAnchor="middle" fontSize={13} fill="var(--ink-4)">Select at least one model.</text>}
      </svg>
      <TipBox tip={tip} hint={onSelect ? CLICK_HINT : undefined} />
    </div>
  );
}
