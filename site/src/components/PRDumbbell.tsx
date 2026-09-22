import { useRef } from "react";
import type { CI } from "../data";
import { fmtPct } from "../data";
import { Logo, LogoGlyph } from "../logos";
import type { PRItem } from "./PRScatter";
import { prTip } from "./PRScatter";
import { CLICK_HINT, DECIDER_TEXT, TipBox, fadeStyle, selectable, usePresence, useTip, useTween, useWidth } from "./ui";
import { hoverable } from "./hover";

/** Row height shared with PRRows; COL_W is one of the three number columns (recall, precision, P − R), PAD the air between the axis and the numbers. */
const ROW = 26, COL_W = 66, PAD = 26, TOP = 20;

/** Signed difference in percentage points, with a true minus sign; "0.0" within rounding. */
const signed = (d: number) => (Math.abs(d) < 0.05 ? "0.0" : `${d > 0 ? "+" : "\u2212"}${Math.abs(d).toFixed(1)}`);

/**
 * Dumbbell rows (ranked-view candidate "dumbbell"): one shared axis for recall and precision; per row a filled dot at recall and a ring at
 * precision joined by a hairline in the row's colour, the two 95% intervals as faint translucent capsules behind the dots. Three tabular number
 * columns follow: recall, precision and P − R in muted ink with its sign. Same hover, click, cross-chart highlight and motion contract as PRRows.
 */
export function PRDumbbell({ items, zoom, sortBy = "recall", logos = false, onSelect, highlight, onHover }: { items: PRItem[]; zoom: boolean; sortBy?: "recall" | "precision" | "f1"; logos?: boolean; onSelect?: (item: PRItem) => void; highlight?: string | null; onHover?: (id: string | null) => void }) {
  const { tip, show, hide, hostRef } = useTip();
  const pickRow = onSelect && ((it: PRItem) => { hide(); onSelect(it); });
  const W = useWidth(hostRef, 760);
  const wide = Math.min(1, Math.max(0, W - 760) / 340);
  const LABEL_W = Math.round((logos ? 196 : 170) + wide * 44);
  const f1 = (it: PRItem) => (it.recall && it.precision ? (2 * it.recall[0] * it.precision[0]) / (it.recall[0] + it.precision[0] || 1) : -1);
  const rows = [...items].sort((a, b) => {
    const va = sortBy === "f1" ? f1(a) : (a[sortBy]?.[0] ?? -1), vb = sortBy === "f1" ? f1(b) : (b[sortBy]?.[0] ?? -1);
    return vb - va;
  });
  const n = rows.length;
  const NUMS = 3 * COL_W;
  const pw = Math.max(0, W - LABEL_W - NUMS - PAD);
  const nx = LABEL_W + pw + PAD;
  const all = rows.flatMap((r) => [r.recall, r.precision]).filter((c): c is NonNullable<CI> => !!c);
  let lo = 0, hi = 1;
  if (zoom && all.length) {
    lo = Math.max(0, Math.min(...all.map((c) => c[1])) - 0.02);
    hi = Math.min(1, Math.max(...all.map((c) => c[2])) + 0.02);
  }
  const sx = (v: number) => LABEL_W + ((v - lo) / (hi - lo || 1)) * pw;
  const span = hi - lo;
  const step = span > 0.6 ? 0.25 : span > 0.3 ? 0.1 : span > 0.12 ? 0.05 : 0.02;
  // labelled ticks at `step`, a dotted minor line halfway between
  const ticks: { v: number; major: boolean }[] = [];
  for (let t = Math.ceil(lo / (step / 2)) * (step / 2); t <= hi + 1e-9; t += step / 2) {
    const v = Math.round(t * 1000) / 1000;
    ticks.push({ v, major: Math.abs(v / step - Math.round(v / step)) < 1e-6 });
  }
  const h = n * ROW + 44;
  const presence = usePresence(items, (it) => it.id);
  const lastTop = useRef(new Map<string, number>());
  rows.forEach((r, i) => lastTop.current.set(r.id, TOP + i * ROW));
  const drawn = presence.map((p) => ({ r: p.item, state: p.state }));
  const target: Record<string, number> = {};
  for (const { r } of drawn) {
    if (r.recall) { target[`${r.id}:r`] = sx(r.recall[0]); target[`${r.id}:rlo`] = sx(r.recall[1]); target[`${r.id}:rhi`] = sx(r.recall[2]); }
    if (r.precision) { target[`${r.id}:p`] = sx(r.precision[0]); target[`${r.id}:plo`] = sx(r.precision[1]); target[`${r.id}:phi`] = sx(r.precision[2]); }
  }
  const geo = useTween(target, undefined, undefined, W);
  const g = (k: string) => geo[k] ?? target[k];
  const sortLabel = sortBy === "f1" ? "F1" : sortBy;
  return (
    <>
      <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
          <text x={LABEL_W} y={12} fontSize={12} fontWeight={500} fill="var(--ink)">Recall and precision, one axis</text>
          <text x={nx} y={12} fontSize={10} fontWeight={500} letterSpacing=".06em" fill="var(--ink-3)">RECALL</text>
          <text x={nx + COL_W} y={12} fontSize={10} fontWeight={500} letterSpacing=".06em" fill="var(--ink-3)">PRECISION</text>
          <text x={nx + 2 * COL_W} y={12} fontSize={10} fontWeight={500} letterSpacing=".06em" fill="var(--ink-3)">P − R</text>
          {/* rank-indexed banding stays put while rows slide between ranks */}
          {rows.map((_, i) => i % 2 === 1 && <rect key={i} x={0} y={TOP + i * ROW} width={W} height={ROW} fill="var(--ink)" fillOpacity={0.02} />)}
          {ticks.map((t) => (
            <g key={t.v}>
              <line x1={sx(t.v)} x2={sx(t.v)} y1={TOP} y2={TOP + n * ROW} stroke="var(--grid)" strokeDasharray={t.major ? undefined : "1 3"} />
              {t.major && <text x={sx(t.v)} y={TOP + n * ROW + 14} fontSize={10} textAnchor="middle" fill="var(--ink-3)" className="mono">{Math.round(t.v * 100)}%</text>}
            </g>
          ))}
          {drawn.map(({ r, state }) => {
            const top = lastTop.current.get(r.id) ?? TOP, y = ROW / 2, label = `${r.name}${r.subset ? " *" : ""}`;
            const d = r.recall && r.precision ? (r.precision[0] - r.recall[0]) * 100 : null;
            return (
              <g key={r.id} className={`mv fd${highlight === r.id ? " hl" : ""}`} style={{ transform: `translate(0px, ${top}px)`, ...fadeStyle(state) }} {...hoverable(onHover, r.id)}>
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
                  {/* interval capsules first, then the joining line, then the two marks on top */}
                  {r.recall && <rect x={g(`${r.id}:rlo`)} y={y - 5} width={Math.max(0, g(`${r.id}:rhi`) - g(`${r.id}:rlo`))} height={10} rx={5} fill={r.color} style={{ fillOpacity: "var(--box-alpha)" }} />}
                  {r.precision && <rect x={g(`${r.id}:plo`)} y={y - 5} width={Math.max(0, g(`${r.id}:phi`) - g(`${r.id}:plo`))} height={10} rx={5} fill={r.color} style={{ fillOpacity: "var(--box-alpha)" }} />}
                  {r.recall && r.precision && <line x1={g(`${r.id}:r`)} x2={g(`${r.id}:p`)} y1={y} y2={y} stroke={r.color} strokeWidth={1.5} strokeOpacity={0.75} />}
                  {r.recall && <circle cx={g(`${r.id}:r`)} cy={y} r={3.4} fill={r.color} />}
                  {r.precision && <circle cx={g(`${r.id}:p`)} cy={y} r={3.4} fill="var(--panel)" stroke={r.color} strokeWidth={1.6} />}
                  <text x={nx} y={y + 4} fontSize={11.5} fill={r.recall ? "var(--ink)" : "var(--ink-4)"} className="mono">{r.recall ? fmtPct(r.recall[0]) : "—"}</text>
                  <text x={nx + COL_W} y={y + 4} fontSize={11.5} fill={r.precision ? "var(--ink)" : "var(--ink-4)"} className="mono">{r.precision ? fmtPct(r.precision[0]) : "—"}</text>
                  <text x={nx + 2 * COL_W} y={y + 4} fontSize={11} fill={d == null ? "var(--ink-4)" : "var(--ink-3)"} className="mono">{d == null ? "—" : signed(d)}</text>
                </g>
              </g>
            );
          })}
          {n === 0 && <text x={W / 2} y={40} textAnchor="middle" fontSize={13} fill="var(--ink-4)">Select at least one model.</text>}
        </svg>
        <TipBox tip={tip} hint={onSelect ? CLICK_HINT : undefined} />
      </div>
      <div className="legend-note">
        <span className="k"><svg width={10} height={10} aria-hidden><circle cx={5} cy={5} r={3.4} fill="var(--ink-2)" /></svg>recall</span>
        <span className="k"><svg width={10} height={10} aria-hidden><circle cx={5} cy={5} r={3.2} fill="none" stroke="var(--ink-2)" strokeWidth={1.6} /></svg>precision</span>
        <span>band: 95% interval</span>
        <span>Sorted by {sortLabel}. The line joins a configuration's two estimates; P − R is precision minus recall, in points.</span>
        {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
      </div>
    </>
  );
}
