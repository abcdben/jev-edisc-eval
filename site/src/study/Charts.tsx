import { TipBox, useTip, useWidth, type TipContent } from "../components/ui";
import { fmtValue, isLogUnit, unitDomain, type Unit } from "../studyData";

/** One arm's row or mark. `planned` draws it hollow with a dashed interval; `human` uses a square so reviewers read as a different species on every chart. */
export type SeriesItem = { id: string; name: string; color: string; planned: boolean; human: boolean; note?: string };
export type ValueItem = SeriesItem & { v: number | null; lo: number | null; hi: number | null; n: number | null };

const ROW = 24, LABEL_W = 172, PAD_R = 92, TICK_FS = 10.5;

/** The mark for an arm: a dot for models, a square for humans; hollow when planned. */
export function ArmMark({ x, y, item, r = 4.5 }: { x: number; y: number; item: SeriesItem; r?: number }) {
  const fill = item.planned ? "var(--panel)" : item.color;
  const stroke = item.color;
  if (item.human) return <rect x={x - r} y={y - r} width={2 * r} height={2 * r} fill={fill} stroke={stroke} strokeWidth={1.5} />;
  return <circle cx={x} cy={y} r={r} fill={fill} stroke={stroke} strokeWidth={1.5} />;
}

function scaleFor(unit: Unit, items: ValueItem[], w0: number, w1: number): { x: (v: number) => number; ticks: number[] } {
  const vals = items.flatMap((i) => [i.v, i.lo, i.hi]).filter((v): v is number => v != null && isFinite(v));
  if (isLogUnit(unit)) {
    const pos = vals.filter((v) => v > 0);
    const lo = Math.pow(10, Math.floor(Math.log10(Math.min(...pos, 1e9)))), hi = Math.pow(10, Math.ceil(Math.log10(Math.max(...pos, 1e-9))));
    const l0 = Math.log10(lo), l1 = Math.log10(Math.max(hi, lo * 10));
    const ticks: number[] = [];
    for (let e = l0; e <= l1 + 1e-9; e++) ticks.push(Math.pow(10, e));
    return { x: (v) => w0 + ((Math.log10(Math.max(v, lo)) - l0) / (l1 - l0)) * (w1 - w0), ticks };
  }
  const dom = unitDomain(unit);
  let lo = dom ? dom[0] : Math.min(0, ...vals), hi = dom ? dom[1] : Math.max(...vals, 0) * 1.1 || 1;
  if (!dom && unit === "ratio") { lo = Math.min(0.5, ...vals); hi = Math.max(1.5, ...vals) * 1.05; }
  // small rates (flip rates, elusion) get their own scale instead of a 0–100% axis with everything in the first inch; negatives extend it below 0
  if (unit === "pct") {
    const vmax = Math.max(0, ...vals), vmin = Math.min(0, ...vals);
    if (vmax <= 0.5) hi = Math.max(0.01, Math.ceil(vmax * 1.15 * 20) / 20);
    if (vmin < 0) lo = Math.floor(vmin * 1.15 * 20) / 20;
  }
  const step = (hi - lo) / 5;
  const ticks = Array.from({ length: 6 }, (_, i) => lo + i * step);
  return { x: (v) => w0 + ((v - lo) / (hi - lo || 1)) * (w1 - w0), ticks };
}

/**
 * Ranked rows, one per arm: a mark at the value, a whisker over the interval, the value written at the right. Sorted best-first by the
 * measure's direction. Log scale for latency, cost and hours so human and machine rows share an axis.
 */
export function DotRows({ items, unit, higherBetter, axis, emptyText = "Select at least one arm.", reference }: { items: ValueItem[]; unit: Unit; higherBetter: boolean; axis: string; emptyText?: string; reference?: number | null }) {
  const { tip, show, hide, hostRef } = useTip();
  const w = useWidth(hostRef, 720);
  const rows = items.filter((i) => i.v != null).sort((a, b) => (higherBetter ? b.v! - a.v! : a.v! - b.v!));
  const h = rows.length * ROW + 46;
  const x0 = LABEL_W, x1 = Math.max(x0 + 120, w - PAD_R);
  const { x, ticks } = scaleFor(unit, rows, x0, x1);
  if (!rows.length) return <div className="study-empty">{emptyText}</div>;
  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg width={w} height={h} className="study-svg">
        <defs>
          <pattern id="study-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--ink-4)" strokeWidth="1" /></pattern>
        </defs>
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={x(t)} x2={x(t)} y1={8} y2={h - 38} stroke="var(--line)" />
            <text x={x(t)} y={h - 24} textAnchor="middle" fontSize={TICK_FS} fill="var(--ink-3)">{fmtValue(t, unit)}</text>
          </g>
        ))}
        {reference != null && <line x1={x(reference)} x2={x(reference)} y1={8} y2={h - 38} stroke="var(--ink-3)" strokeDasharray="3 3" />}
        <text x={(x0 + x1) / 2} y={h - 6} textAnchor="middle" fontSize={11.5} fill="var(--ink-2)">{axis}</text>
        {rows.map((r, i) => {
          const cy = 16 + i * ROW;
          const tipc: TipContent = { title: r.name, color: r.color, value: fmtValue(r.v, unit), lines: r.lo != null ? [["95% interval", `${fmtValue(r.lo, unit)} – ${fmtValue(r.hi, unit)}`]] : undefined, sub: [r.n ? `n = ${r.n.toLocaleString()}` : null, r.planned ? "placeholder: not yet measured" : null, r.note ?? null].filter(Boolean).join(" · ") };
          return (
            <g key={r.id} onMouseMove={(e) => show(e, { kind: "row", top: cy - ROW / 2, height: ROW, clearX: x1 + PAD_R }, tipc)} onMouseLeave={hide}>
              <rect x={0} y={cy - ROW / 2} width={w} height={ROW} fill={r.planned ? "url(#study-hatch)" : "transparent"} opacity={r.planned ? 0.18 : 1} />
              <text x={x0 - 10} y={cy + 4} textAnchor="end" fontSize={12} fill={r.human ? "var(--ink)" : "var(--ink-2)"} fontWeight={r.human ? 500 : 400} fontStyle={r.planned ? "italic" : "normal"}>{r.name}</text>
              {r.lo != null && r.hi != null && <line x1={x(r.lo)} x2={x(r.hi)} y1={cy} y2={cy} stroke={r.color} strokeWidth={1.5} strokeDasharray={r.planned ? "3 3" : undefined} />}
              <ArmMark x={x(r.v!)} y={cy} item={r} />
              <text x={x1 + 10} y={cy + 4} fontSize={11.5} fill="var(--ink-2)" style={{ fontVariantNumeric: "tabular-nums" }}>{fmtValue(r.v, unit)}</text>
            </g>
          );
        })}
      </svg>
      <TipBox tip={tip} />
    </div>
  );
}

/** "Whose side": one 100%-stacked bar per arm over the four outcomes on contested documents, κ values written at the right. */
export type SidesItem = SeriesItem & { parts: [number, number, number, number]; kappaA: number | null; kappaR: number | null; dep: number | null };
const SIDES_LABELS = ["agrees with both", "sides with authority", "sides with reviewer", "disagrees with both"];
const SIDES_SHADES = ["var(--ink-4)", null, "var(--c-tar-2)", "var(--line-2)"];

export function SidesBars({ items, emptyText = "Select at least one arm." }: { items: SidesItem[]; emptyText?: string }) {
  const { tip, show, hide, hostRef } = useTip();
  const w = useWidth(hostRef, 720);
  const rows = items.slice().sort((a, b) => b.parts[1] - a.parts[1]);
  if (!rows.length) return <div className="study-empty">{emptyText}</div>;
  const x0 = LABEL_W, x1 = Math.max(x0 + 160, w - 190);
  const h = rows.length * (ROW + 6) + 44;
  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg width={w} height={h} className="study-svg">
        <defs><pattern id="study-hatch2" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--panel)" strokeWidth="2" /></pattern></defs>
        {[0, 0.25, 0.5, 0.75, 1].map((t) => <text key={t} x={x0 + t * (x1 - x0)} y={h - 22} textAnchor="middle" fontSize={TICK_FS} fill="var(--ink-3)">{Math.round(t * 100)}%</text>)}
        <text x={x1 + 12} y={12} fontSize={10.5} fill="var(--ink-3)">κ auth · κ rev · dep.</text>
        {rows.map((r, i) => {
          const cy = 24 + i * (ROW + 6);
          let acc = 0;
          const lines = r.parts.map((p, k) => [SIDES_LABELS[k], fmtValue(p, "pct")] as [string, string]);
          const tipc: TipContent = { title: r.name, color: r.color, lines: [...lines, ["κ vs. authority", r.kappaA == null ? "—" : r.kappaA.toFixed(2)], ["κ vs. reviewer", r.kappaR == null ? "—" : r.kappaR.toFixed(2)], ["Error dependence", r.dep == null ? "—" : `${r.dep.toFixed(2)}×`]], sub: r.planned ? "placeholder: not yet measured" : undefined };
          return (
            <g key={r.id} onMouseMove={(e) => show(e, { kind: "row", top: cy - ROW / 2, height: ROW, clearX: w }, tipc)} onMouseLeave={hide}>
              <text x={x0 - 10} y={cy + 4} textAnchor="end" fontSize={12} fill="var(--ink-2)" fontStyle={r.planned ? "italic" : "normal"}>{r.name}</text>
              {r.parts.map((p, k) => {
                const xa = x0 + acc * (x1 - x0); acc += p;
                const wseg = p * (x1 - x0);
                const fill = SIDES_SHADES[k] ?? r.color;
                return (
                  <g key={k}>
                    <rect x={xa} y={cy - 9} width={wseg} height={18} fill={fill} opacity={k === 1 ? 1 : 0.9} />
                    {r.planned && <rect x={xa} y={cy - 9} width={wseg} height={18} fill="url(#study-hatch2)" opacity={0.5} />}
                    {wseg > 34 && <text x={xa + wseg / 2} y={cy + 3.5} textAnchor="middle" fontSize={10} fill={k === 1 ? "var(--bg)" : "var(--ink)"}>{Math.round(p * 100)}%</text>}
                  </g>
                );
              })}
              <text x={x1 + 12} y={cy + 4} fontSize={11.5} fill="var(--ink-2)" style={{ fontVariantNumeric: "tabular-nums" }}>
                {r.kappaA == null ? "—" : r.kappaA.toFixed(2)} · {r.kappaR == null ? "—" : r.kappaR.toFixed(2)} · {r.dep == null ? "—" : `${r.dep.toFixed(2)}×`}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="legend-note study-legend">
        {SIDES_LABELS.map((l, k) => <span key={l}><i className="sw" style={{ background: SIDES_SHADES[k] ?? "var(--c-jev)" }} />{l}</span>)}
        <span>dep. = P(model wrong | reviewer wrong) ÷ P(model wrong); 1.0 means the model's errors are independent of the reviewer's.</span>
      </div>
      <TipBox tip={tip} />
    </div>
  );
}

/** Workflow frontier: recall against the share of documents a human reads; mark area scales with cost per 100k. */
export type FrontierItem = SeriesItem & { recall: number; share: number; hours: number | null; usd: number | null };

export function Frontier({ items, emptyText = "Select at least one arm." }: { items: FrontierItem[]; emptyText?: string }) {
  const { tip, show, hide, hostRef } = useTip();
  const w = useWidth(hostRef, 720);
  if (!items.length) return <div className="study-empty">{emptyText}</div>;
  const h = 420, PL = 56, PR = 24, PT = 18, PB = 48;
  const x = (s: number) => PL + s * (w - PL - PR), y = (r: number) => PT + (1 - r) * (h - PT - PB);
  const maxUsd = Math.max(1, ...items.map((i) => i.usd ?? 0));
  const rad = (u: number | null) => 4 + Math.sqrt((u ?? 0) / maxUsd) * 14;
  // labels sit right of their mark; where two marks are close the lower label is pushed down so the names stay legible
  const labelY = new Map<string, number>();
  items.slice().sort((a, b) => y(a.recall) - y(b.recall)).forEach((it) => {
    let ly = y(it.recall) + 4;
    for (const [oid, oy] of labelY) {
      const o = items.find((i) => i.id === oid)!;
      if (Math.abs(x(o.share) - x(it.share)) < 110 && ly - oy < 13) ly = oy + 13;
    }
    labelY.set(it.id, ly);
  });
  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg width={w} height={h} className="study-svg">
        {[0, 0.25, 0.5, 0.75, 1].map((t) => (
          <g key={t}>
            <line x1={x(t)} x2={x(t)} y1={PT} y2={h - PB} stroke="var(--line)" />
            <line x1={PL} x2={w - PR} y1={y(t)} y2={y(t)} stroke="var(--line)" />
            <text x={x(t)} y={h - PB + 16} textAnchor="middle" fontSize={TICK_FS} fill="var(--ink-3)">{Math.round(t * 100)}%</text>
            <text x={PL - 8} y={y(t) + 3.5} textAnchor="end" fontSize={TICK_FS} fill="var(--ink-3)">{Math.round(t * 100)}%</text>
          </g>
        ))}
        <text x={(PL + w - PR) / 2} y={h - 8} textAnchor="middle" fontSize={11.5} fill="var(--ink-2)">Documents read by a human</text>
        <text transform={`translate(14 ${(PT + h - PB) / 2}) rotate(-90)`} textAnchor="middle" fontSize={11.5} fill="var(--ink-2)">Recall</text>
        {items.map((it) => {
          const tipc: TipContent = { title: it.name, color: it.color, lines: [["Recall", fmtValue(it.recall, "pct")], ["Human share", fmtValue(it.share, "pct")], ["Human hours / 100k", fmtValue(it.hours, "hours")], ["Cost / 100k", fmtValue(it.usd, "usd")]], sub: it.planned ? "placeholder: not yet measured" : undefined };
          const cx = x(it.share), cy = y(it.recall), r = rad(it.usd);
          return (
            <g key={it.id} onMouseMove={(e) => show(e, { kind: "mark", x: cx, y: cy, r }, tipc)} onMouseLeave={hide}>
              {it.human
                ? <rect x={cx - r} y={cy - r} width={2 * r} height={2 * r} fill={it.planned ? "var(--panel)" : it.color} fillOpacity={0.35} stroke={it.color} strokeWidth={1.5} strokeDasharray={it.planned ? "3 3" : undefined} />
                : <circle cx={cx} cy={cy} r={r} fill={it.color} fillOpacity={it.planned ? 0.12 : 0.35} stroke={it.color} strokeWidth={1.5} strokeDasharray={it.planned ? "3 3" : undefined} />}
              {cx + r + 5 + it.name.length * 6.2 > w - PR
                ? <text x={cx - r - 5} y={labelY.get(it.id) ?? cy + 4} textAnchor="end" fontSize={11} fill="var(--ink-2)" fontStyle={it.planned ? "italic" : "normal"}>{it.name}</text>
                : <text x={cx + r + 5} y={labelY.get(it.id) ?? cy + 4} fontSize={11} fill="var(--ink-2)" fontStyle={it.planned ? "italic" : "normal"}>{it.name}</text>}
            </g>
          );
        })}
      </svg>
      <div className="legend-note study-legend"><span>Mark area: cost per 100,000 documents. Squares: human arms. Dashed: placeholder.</span></div>
      <TipBox tip={tip} />
    </div>
  );
}
