import { useRef } from "react";
import type { CI } from "../data";
import { fmtPct, fmtRange } from "../data";
import { Logo, LogoGlyph } from "../logos";
import type { PRItem } from "./PRScatter";
import { prTip } from "./PRScatter";
import { CLICK_HINT, DECIDER_TEXT, TipBox, fadeStyle, selectable, usePresence, useTip, useTween, useWidth } from "./ui";
import { hoverable } from "./hover";

/** Row geometry shared with PRRail; VAL_W is the value cell (with its tint), RANGE_W the muted "82–91" interval column after it, DELTA_W the "vs default" column that follows when a reference row is given. HDR is the two-line header. */
const ROW = 26, VAL_W = 58, RANGE_W = 50, DELTA_W = 66, HDR = 28;

/** Signed difference in percentage points, with a true minus sign; "0.0" within rounding. */
const signed = (d: number) => (Math.abs(d) < 0.05 ? "0.0" : `${d > 0 ? "+" : "\u2212"}${Math.abs(d).toFixed(1)}`);

/**
 * Heat-annotated ranked rows (the Compare configurations `ranked` view, "vs default"): dot-whisker panels, plus, when `referenceId` names one of the items,
 * a faint diverging tint behind each printed value (--c-terra above the reference, --c-sonnet below, deeper the further away) and a muted ±pp
 * column per panel. The reference row sits on the site's --hl band and a dashed line marks its value through each panel. Without `referenceId`
 * (or when that row is not among the items) the tint, column, band and lines are simply omitted. Same hover, click, cross-chart highlight and motion contract as PRRail.
 */
export function PRHeat({ items, zoom, sortBy = "recall", logos = false, onSelect, highlight, onHover, referenceId }: { items: PRItem[]; zoom: boolean; sortBy?: "recall" | "precision" | "f1"; logos?: boolean; onSelect?: (item: PRItem) => void; highlight?: string | null; onHover?: (id: string | null) => void; referenceId?: string }) {
  const { tip, show, hide, hostRef } = useTip();
  const pickRow = onSelect && ((it: PRItem) => { hide(); onSelect(it); });
  const W = useWidth(hostRef, 760);
  const wide = Math.min(1, Math.max(0, W - 760) / 340);
  const LABEL_W = Math.round((logos ? 196 : 190) + wide * 44);
  const GAP = Math.round(26 + wide * 22);
  const ref = referenceId != null ? items.find((it) => it.id === referenceId) ?? null : null;
  const NUMS = VAL_W + RANGE_W + (ref ? DELTA_W : 0);
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
  if (zoom && all.length) {
    lo = Math.max(0, Math.min(...all.map((c) => c[1])) - 0.02);
    hi = Math.min(1, Math.max(...all.map((c) => c[2])) + 0.02);
  }
  const sx = (col: number, v: number) => x0[col] + ((v - lo) / (hi - lo || 1)) * colW;
  const span = hi - lo;
  const step = span > 0.6 ? 0.25 : span > 0.3 ? 0.1 : span > 0.12 ? 0.05 : 0.02;
  const ticks: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) ticks.push(Math.round(t * 1000) / 1000);
  const h = n * ROW + HDR + 24;
  // the reference value per panel and the largest distance from it, which sets the deepest tint
  const refV = [ref?.recall?.[0] ?? null, ref?.precision?.[0] ?? null];
  const maxD = [0, 1].map((col) => { const rv = refV[col]; return rv == null ? 0 : Math.max(1e-9, ...rows.map((r) => { const c = col === 0 ? r.recall : r.precision; return c ? Math.abs(c[0] - rv) : 0; })); });
  const presence = usePresence(items, (it) => it.id);
  const lastTop = useRef(new Map<string, number>());
  rows.forEach((r, i) => lastTop.current.set(r.id, HDR + i * ROW));
  const drawn = presence.map((p) => ({ r: p.item, state: p.state }));
  const target: Record<string, number> = {};
  for (const { r } of drawn) ([r.recall, r.precision] as CI[]).forEach((ci, col) => { if (ci) { target[`${r.id}:${col}:lo`] = sx(col, ci[1]); target[`${r.id}:${col}:hi`] = sx(col, ci[2]); target[`${r.id}:${col}:v`] = sx(col, ci[0]); } });
  const geo = useTween(target, undefined, undefined, W);
  const g = (k: string) => geo[k] ?? target[k];
  const sortLabel = sortBy === "f1" ? "F1" : sortBy;
  const refName = ref?.name ?? "default";
  const deltaHead = "VS DEFAULT";
  return (
    <>
      <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
          {[0, 1].map((col) => (
            <g key={col}>
              <text x={x0[col]} y={10} fontSize={10} fontWeight={500} letterSpacing=".07em" fill="var(--ink)">{col === 0 ? "RECALL" : "PRECISION"}</text>
              <text x={x0[col]} y={22} fontSize={10} fill="var(--ink-4)">{col === 0 ? "share of relevant documents found" : "share of flagged documents that are relevant"}</text>
              <text x={x0[col] + colW + 8} y={10} fontSize={10} fontWeight={500} letterSpacing=".07em" fill="var(--ink-3)">VALUE</text>
              <text x={x0[col] + colW + 8 + VAL_W} y={10} fontSize={10} fontWeight={500} letterSpacing=".05em" fill="var(--ink-3)">95% CI</text>
              {ref && (
                <>
                  <text x={x0[col] + colW + 8 + VAL_W + RANGE_W} y={10} fontSize={10} fontWeight={500} letterSpacing=".05em" fill="var(--ink-3)">{deltaHead}</text>
                  <text x={x0[col] + colW + 8 + VAL_W + RANGE_W} y={22} fontSize={10} fill="var(--ink-4)">pp</text>
                </>
              )}
              {ticks.map((t) => (
                <g key={t}>
                  <line x1={sx(col, t)} x2={sx(col, t)} y1={HDR} y2={HDR + n * ROW} stroke="var(--grid)" />
                  <text x={sx(col, t)} y={HDR + n * ROW + 14} fontSize={10} textAnchor="middle" fill="var(--ink-3)" className="mono">{Math.round(t * 100)}%</text>
                </g>
              ))}
            </g>
          ))}
          {drawn.map(({ r, state }) => {
            const top = lastTop.current.get(r.id) ?? HDR, y = ROW / 2, label = `${r.name}${r.subset ? " *" : ""}`, isRef = !!ref && r.id === ref.id;
            return (
              <g key={r.id} className={`mv fd${highlight === r.id ? " hl" : ""}`} style={{ transform: `translate(0px, ${top}px)`, ...fadeStyle(state) }} {...hoverable(onHover, r.id)}>
                <g onMouseMove={(e) => show(e, { kind: "row", top, height: ROW, clearX: W }, prTip(r, logos ? <Logo model={r.id} size={12} /> : undefined))} onMouseLeave={hide} {...selectable(pickRow, r, r.name)}>
                  {isRef && <rect className="row-ref" x={0} y={0} width={W} height={ROW} rx={2} />}
                  <rect className="hit" x={0} y={0} width={W} height={ROW} fill="transparent" />
                  {logos ? (
                    <>
                      <g color="var(--ink-2)"><LogoGlyph model={r.id} cx={8} cy={y} /></g>
                      <text x={22} y={y + 4} fontSize={12} fill="var(--ink-2)" style={isRef ? { fill: "var(--ink)", fontWeight: 500 } : r.decider ? DECIDER_TEXT : undefined}>{label}</text>
                    </>
                  ) : (
                    <text x={LABEL_W - 12} y={y + 4} textAnchor="end" fontSize={12} fill="var(--ink-2)" style={isRef ? { fill: "var(--ink)", fontWeight: 500 } : r.decider ? DECIDER_TEXT : undefined}>{label}</text>
                  )}
                  {([r.recall, r.precision] as CI[]).map((ci, col) => {
                    if (!ci) return <text key={col} x={x0[col] + colW + 8} y={y + 4} fontSize={11.5} fill="var(--ink-4)" className="mono">—</text>;
                    const rv = refV[col];
                    const d = ref && rv != null ? (ci[0] - rv) * 100 : null;
                    const tint = d == null || isRef || Math.abs(d) < 0.05 ? null : { fill: d > 0 ? "var(--c-terra)" : "var(--c-sonnet)", alpha: 0.06 + (Math.abs(d) / 100 / maxD[col]) * 0.22 };
                    return (
                      <g key={col}>
                        {tint && <rect x={x0[col] + colW + 4} y={y - 10} width={VAL_W - 6} height={20} rx={3} fill={tint.fill} fillOpacity={tint.alpha.toFixed(3)} />}
                        <line x1={g(`${r.id}:${col}:lo`)} x2={g(`${r.id}:${col}:hi`)} y1={y} y2={y} stroke={r.color} strokeWidth={1.5} strokeLinecap="butt" />
                        <circle cx={g(`${r.id}:${col}:v`)} cy={y} r={3.2} fill={r.color} />
                        <text x={x0[col] + colW + 8} y={y + 4} fontSize={11.5} fill={isRef ? "var(--ink-3)" : "var(--ink)"} className="mono">{fmtPct(ci[0])}</text>
                        <text x={x0[col] + colW + 8 + VAL_W} y={y + 4} fontSize={10.5} fill="var(--ink-4)" className="mono">{fmtRange(ci)}</text>
                        {ref && (isRef ? (
                          <text x={x0[col] + colW + 8 + VAL_W + RANGE_W} y={y + 4} fontSize={11} fill="var(--ink-4)" className="mono">ref</text>
                        ) : (
                          <text x={x0[col] + colW + 8 + VAL_W + RANGE_W} y={y + 4} fontSize={11} fill={d == null ? "var(--ink-4)" : "var(--ink-3)"} className="mono">{d == null ? "—" : signed(d)}</text>
                        ))}
                      </g>
                    );
                  })}
                </g>
              </g>
            );
          })}
          {/* the reference's value through each panel, drawn over the rows so it reads across the whiskers */}
          {ref && [0, 1].map((col) => { const rv = refV[col]; return rv == null ? null : <line key={col} x1={sx(col, rv)} x2={sx(col, rv)} y1={HDR - 2} y2={HDR + n * ROW + 2} stroke="var(--ink-3)" strokeDasharray="2 3" pointerEvents="none" />; })}
          {n === 0 && <text x={W / 2} y={HDR + 20} textAnchor="middle" fontSize={13} fill="var(--ink-4)">Select at least one model.</text>}
        </svg>
        <TipBox tip={tip} hint={onSelect ? CLICK_HINT : undefined} />
      </div>
      <div className="legend-note">
        <span>Sorted by {sortLabel}. Dot: point estimate. Whisker and range: 95% interval.{ref ? ` Cell tint: distance from the ${refName} row, green above, umber below. Dashed line: the ${refName} row's value.` : ""}</span>
        {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
      </div>
    </>
  );
}
