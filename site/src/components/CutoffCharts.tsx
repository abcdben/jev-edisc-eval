import { useMemo } from "react";
import { fmtPct } from "../data";
import { GRID_N, gridValue, type Metrics } from "../cutoffEngine";
import { TipBox, useTip, useWidth } from "./ui";

/** A labelled point on the precision–recall plane. */
export type PRPoint = { id: string; name: string; color: string; recall: number | null; precision: number | null; f1?: number | null };
/** A comparison model on the chart: its shared-cutoff frontier (dashed), its benchmark default, its figures at the primary's cutoffs and, when shown, at its own per-issue optimum. */
export type GhostCurve = { id: string; name: string; color: string; curve: Metrics[]; def: PRPoint; cur: PRPoint | null; own?: PRPoint | null };

const PL = 56, PR = 20, PT = 18, PB = 48;

function niceTicks(lo: number, hi: number): number[] {
  const span = hi - lo;
  const step = span > 0.6 ? 0.2 : span > 0.3 ? 0.1 : span > 0.12 ? 0.05 : span > 0.06 ? 0.02 : 0.01;
  const out: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(Math.round(t * 1000) / 1000);
  return out;
}
const has = (p: PRPoint): p is PRPoint & { recall: number; precision: number } => p.recall != null && p.precision != null;

/**
 * Recall (x) against precision (y), the Cutoffs page's headline chart. `curve` is the model's pooled frontier traced by one shared cutoff
 * (index i is cutoff i/200); `def` the benchmark default (0.5, the published labels), `cur` the figures at the current per-issue cutoffs.
 * `ghosts` are the comparison models (dashed curves in their roster colours, defaults hollow, figures at the primary's cutoffs filled) and
 * `roster` the other models' published points, faint. `own` marks (small squares) are each model's figures at its own per-issue optimum.
 * Iso-F1 contours sit behind everything. Hovering a curve reports the model and the shared cutoff at that point. Past six curves the strokes thin.
 */
export function PRCurveChart({ curve, def, cur, own, color, ghosts, roster, zoom, height = 340, xLabel = "Recall", yLabel = "Precision" }: {
  curve: Metrics[]; def: PRPoint; cur: PRPoint; own?: PRPoint | null; color: string; ghosts?: GhostCurve[]; roster?: PRPoint[]; zoom: boolean; height?: number; xLabel?: string; yLabel?: string;
}) {
  const { tip, show, hide, hostRef } = useTip();
  const W = useWidth(hostRef, 720), H = height;
  const gs = ghosts ?? [];
  const thin = gs.length > 6;
  // the frame fits the primary and every model's default and own optimum; a comparison model's point at the primary's cutoffs may sit far off
  // (one model's cutoffs applied to another's probability scale) and is left out of the fit rather than stretching the frame, 0–100% shows it
  const pts = [def, cur, ...(own ? [own] : []), ...gs.flatMap((g) => [g.def, g.own].filter((p): p is PRPoint => !!p)), ...(roster ?? [])].filter(has);
  const dom = useMemo(() => {
    if (!zoom) return { x: [0, 1] as [number, number], y: [0, 1] as [number, number] };
    const xs = pts.map((p) => p.recall), ys = pts.map((p) => p.precision);
    // the frontier's middle (shared cutoffs 0.2–0.8) sets the frame; its tails run to recall 0 and to precision = prevalence
    const cx = curve.slice(GRID_N * 0.2, GRID_N * 0.8 + 1).filter((m) => m.recall != null && m.precision != null);
    xs.push(...cx.map((m) => m.recall!)); ys.push(...cx.map((m) => m.precision!));
    const fin = (v: number[]) => v.filter(Number.isFinite);
    const fx = fin(xs), fy = fin(ys);
    if (!fx.length || !fy.length) return { x: [0, 1] as [number, number], y: [0, 1] as [number, number] };
    const pad = (lo: number, hi: number): [number, number] => { const p = Math.max(0.03, (hi - lo) * 0.12); return [Math.max(0, lo - p), Math.min(1, hi + p)]; };
    return { x: pad(Math.min(...fx), Math.max(...fx)), y: pad(Math.min(...fy), Math.max(...fy)) };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoom, pts.map((p) => `${p.recall},${p.precision}`).join("|"), curve]);
  const X = (v: number) => PL + ((v - dom.x[0]) / (dom.x[1] - dom.x[0] || 1)) * (W - PL - PR);
  const Y = (v: number) => PT + (1 - (v - dom.y[0]) / (dom.y[1] - dom.y[0] || 1)) * (H - PT - PB);
  const xt = niceTicks(dom.x[0], dom.x[1]), yt = niceTicks(dom.y[0], dom.y[1]);
  const inside = (r: number, p: number) => r >= dom.x[0] - 1e-9 && r <= dom.x[1] + 1e-9 && p >= dom.y[0] - 1e-9 && p <= dom.y[1] + 1e-9;

  const path = (c: Metrics[]) => {
    let d = "", pen = false;
    for (const m of c) {
      if (m.recall == null || m.precision == null || !inside(m.recall, m.precision)) { pen = false; continue; }
      d += `${pen ? "L" : "M"}${X(m.recall).toFixed(1)} ${Y(m.precision).toFixed(1)}`; pen = true;
    }
    return d;
  };
  // iso-F1: precision = f·recall / (2·recall − f)
  const isoPath = (f: number) => {
    let d = "", pen = false;
    for (let i = 0; i <= 100; i++) {
      const r = dom.x[0] + (i / 100) * (dom.x[1] - dom.x[0]);
      const den = 2 * r - f;
      if (den <= 1e-6) { pen = false; continue; }
      const p = (f * r) / den;
      if (!inside(r, p)) { pen = false; continue; }
      d += `${pen ? "L" : "M"}${X(r).toFixed(1)} ${Y(p).toFixed(1)}`; pen = true;
    }
    return d;
  };
  const isoLabel = (f: number) => {
    // where the contour meets the top or right edge of the plot
    const r = dom.x[1] - 0.004, den = 2 * r - f;
    if (den > 1e-6) { const p = (f * r) / den; if (inside(r, p)) return { x: X(r) - 3, y: Y(p) - 4, anchor: "end" as const }; }
    const p = dom.y[1] - 0.004, den2 = 2 * p - f;
    if (den2 > 1e-6) { const rr = (f * p) / den2; if (inside(rr, p)) return { x: X(rr) + 3, y: Y(p) + 10, anchor: "start" as const }; }
    return null;
  };

  const onCurveMove = (e: React.MouseEvent, c: Metrics[], name: string, col: string) => {
    const host = hostRef.current?.getBoundingClientRect();
    if (!host) return;
    const mx = e.clientX - host.left, my = e.clientY - host.top;
    let best = -1, bd = Infinity;
    c.forEach((m, i) => {
      if (m.recall == null || m.precision == null) return;
      const dx = X(m.recall) - mx, dy = Y(m.precision) - my, d2 = dx * dx + dy * dy;
      if (d2 < bd) { bd = d2; best = i; }
    });
    if (best < 0) return;
    const m = c[best];
    show(e, { kind: "mark", x: X(m.recall!), y: Y(m.precision!), r: 5 }, {
      title: `${name} · shared cutoff ${gridValue(best).toFixed(3)}`, color: col,
      lines: [["Recall", fmtPct(m.recall)], ["Precision", fmtPct(m.precision)], ["F1", fmtPct(m.f1)], ["Flagged", `${m.flagged.toLocaleString("en-US")} · ${fmtPct(m.reviewShare)}`]],
    });
  };
  const ptTip = (p: PRPoint, what: string) => ({ title: `${p.name} · ${what}`, color: p.color, lines: [["Recall", fmtPct(p.recall)], ["Precision", fmtPct(p.precision)], ["F1", fmtPct(p.f1)]] as [string, string][] });

  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ display: "block", overflow: "visible" }}>
        <defs>
          <pattern id="dotgrid-cut" width={8} height={8} patternUnits="userSpaceOnUse"><circle cx={1} cy={1} r={0.7} fill="var(--dots)" /></pattern>
          <clipPath id="cut-clip"><rect x={PL} y={PT} width={Math.max(0, W - PL - PR)} height={Math.max(0, H - PT - PB)} /></clipPath>
        </defs>
        <rect x={PL} y={PT} width={Math.max(0, W - PR - PL)} height={Math.max(0, H - PB - PT)} fill="url(#dotgrid-cut)" />
        {xt.map((t) => (
          <g key={`x${t}`}>
            <line x1={X(t)} x2={X(t)} y1={PT} y2={H - PB} stroke="var(--grid)" />
            <text x={X(t)} y={H - PB + 16} fontSize={10.5} textAnchor="middle" fill="var(--ink-3)" className="mono">{Math.round(t * 100)}%</text>
          </g>
        ))}
        {yt.map((t) => (
          <g key={`y${t}`}>
            <line x1={PL} x2={W - PR} y1={Y(t)} y2={Y(t)} stroke="var(--grid)" />
            <text x={PL - 8} y={Y(t) + 3.5} fontSize={10.5} textAnchor="end" fill="var(--ink-3)" className="mono">{Math.round(t * 100)}%</text>
          </g>
        ))}
        <g stroke="var(--axis)"><line x1={PL} x2={W - PR} y1={H - PB} y2={H - PB} /><line x1={PL} x2={PL} y1={PT} y2={H - PB} /></g>
        <text x={(PL + W - PR) / 2} y={H - 10} fontSize={12} textAnchor="middle" fill="var(--ink-2)" className="ax">{xLabel}</text>
        <text x={14} y={(PT + H - PB) / 2} fontSize={12} textAnchor="middle" fill="var(--ink-2)" className="ax" transform={`rotate(-90 14 ${(PT + H - PB) / 2})`}>{yLabel}</text>
        {/* iso-F1 contours */}
        <g clipPath="url(#cut-clip)">
          {[0.5, 0.6, 0.7, 0.8, 0.9].map((f) => <path key={f} d={isoPath(f)} fill="none" stroke="var(--line-2)" strokeWidth={0.8} strokeDasharray="2 4" opacity={0.7} />)}
        </g>
        {[0.5, 0.6, 0.7, 0.8, 0.9].map((f) => { const l = isoLabel(f); return l ? <text key={f} x={l.x} y={l.y} fontSize={9.5} textAnchor={l.anchor} fill="var(--ink-4)" className="mono">F1 {Math.round(f * 100)}</text> : null; })}
        {/* other models' published points */}
        {roster?.filter(has).filter((p) => inside(p.recall, p.precision)).map((p) => (
          <g key={p.id} onMouseMove={(e) => show(e, { kind: "mark", x: X(p.recall), y: Y(p.precision), r: 5 }, ptTip(p, "benchmark default"))} onMouseLeave={hide} style={{ cursor: "default" }}>
            <circle cx={X(p.recall)} cy={Y(p.precision)} r={3} fill={p.color} fillOpacity={0.35} />
            <text x={X(p.recall) + 6} y={Y(p.precision) + 3.5} fontSize={9.5} fill="var(--ink-4)" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 2.5, strokeLinejoin: "round" }}>{p.name}</text>
          </g>
        ))}
        {/* comparison models: dashed frontiers, defaults hollow, figures at the primary's cutoffs filled, own optimum as a square */}
        {gs.map((g) => (
          <g key={g.id}>
            <path d={path(g.curve)} fill="none" stroke={g.color} strokeWidth={thin ? 1 : 1.4} strokeDasharray={thin ? "3 3" : "4 3"} opacity={thin ? 0.5 : 0.6} onMouseMove={(e) => onCurveMove(e, g.curve, g.name, g.color)} onMouseLeave={hide} style={{ pointerEvents: "stroke" }} />
            <path d={path(g.curve)} fill="none" stroke="transparent" strokeWidth={8} onMouseMove={(e) => onCurveMove(e, g.curve, g.name, g.color)} onMouseLeave={hide} style={{ pointerEvents: "stroke" }} />
            {has(g.def) && inside(g.def.recall, g.def.precision) && (
              <circle cx={X(g.def.recall)} cy={Y(g.def.precision)} r={thin ? 3.2 : 4} fill="var(--panel)" stroke={g.color} strokeWidth={1.4} opacity={0.85} onMouseMove={(e) => show(e, { kind: "mark", x: X(g.def.recall!), y: Y(g.def.precision!), r: 5 }, ptTip(g.def, "benchmark default · 0.5"))} onMouseLeave={hide} />
            )}
            {g.cur && has(g.cur) && inside(g.cur.recall, g.cur.precision) && (
              <circle cx={X(g.cur.recall)} cy={Y(g.cur.precision)} r={thin ? 3 : 3.6} fill={g.color} opacity={0.7} onMouseMove={(e) => show(e, { kind: "mark", x: X(g.cur!.recall!), y: Y(g.cur!.precision!), r: 5 }, ptTip(g.cur!, "at these cutoffs"))} onMouseLeave={hide} />
            )}
            {g.own && has(g.own) && inside(g.own.recall, g.own.precision) && (
              <rect x={X(g.own.recall) - 3} y={Y(g.own.precision) - 3} width={6} height={6} fill={g.color} stroke="var(--panel)" strokeWidth={1} opacity={0.9} onMouseMove={(e) => show(e, { kind: "mark", x: X(g.own!.recall!), y: Y(g.own!.precision!), r: 5 }, ptTip(g.own!, "own per-issue optimum"))} onMouseLeave={hide} />
            )}
          </g>
        ))}
        {/* the model: frontier, default, current */}
        <path d={path(curve)} fill="none" stroke={color} strokeWidth={thin ? 1.6 : 1.8} opacity={0.9} onMouseMove={(e) => onCurveMove(e, curve, cur.name, color)} onMouseLeave={hide} style={{ pointerEvents: "stroke" }} />
        <path d={path(curve)} fill="none" stroke="transparent" strokeWidth={10} onMouseMove={(e) => onCurveMove(e, curve, cur.name, color)} onMouseLeave={hide} style={{ pointerEvents: "stroke" }} />
        {own && has(own) && inside(own.recall, own.precision) && (
          <rect x={X(own.recall) - 3.5} y={Y(own.precision) - 3.5} width={7} height={7} fill={color} stroke="var(--panel)" strokeWidth={1} onMouseMove={(e) => show(e, { kind: "mark", x: X(own.recall!), y: Y(own.precision!), r: 6 }, ptTip(own, "own per-issue optimum"))} onMouseLeave={hide} />
        )}
        {has(def) && has(cur) && inside(def.recall, def.precision) && inside(cur.recall, cur.precision) && (
          <line x1={X(def.recall)} y1={Y(def.precision)} x2={X(cur.recall)} y2={Y(cur.precision)} stroke={color} strokeWidth={1} strokeDasharray="2 2" opacity={0.6} />
        )}
        {has(def) && inside(def.recall, def.precision) && (
          <g onMouseMove={(e) => show(e, { kind: "mark", x: X(def.recall), y: Y(def.precision), r: 6 }, ptTip(def, "benchmark default · 0.5"))} onMouseLeave={hide}>
            <circle cx={X(def.recall)} cy={Y(def.precision)} r={5} fill="var(--panel)" stroke={color} strokeWidth={1.6} />
            <text x={X(def.recall) + 8} y={Y(def.precision) - 6} fontSize={10.5} fill="var(--ink-3)" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 2.5, strokeLinejoin: "round" }}>0.5 default</text>
          </g>
        )}
        {has(cur) && inside(cur.recall, cur.precision) && (
          <g onMouseMove={(e) => show(e, { kind: "mark", x: X(cur.recall), y: Y(cur.precision), r: 6 }, ptTip(cur, "current cutoffs"))} onMouseLeave={hide}>
            <circle cx={X(cur.recall)} cy={Y(cur.precision)} r={5.5} fill={color} className="cut-cur" />
            <text x={X(cur.recall) + 8} y={Y(cur.precision) + 13} fontSize={10.5} fontWeight={500} fill="var(--ink)" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 2.5, strokeLinejoin: "round" }}>{cur.name}</text>
          </g>
        )}
      </svg>
      <TipBox tip={tip} />
    </div>
  );
}

/**
 * Row sparkline, 120 × 48. `hist`: the issue's score histogram, gold-negative decisions above the midline and gold-positive below, each class
 * scaled to its own peak, the cutoff as a vertical rule with the flagged side tinted. `curve`: the issue's precision–recall curve with the
 * current point filled and the 0.5 point hollow; `marks` are the comparison models' points at the same cutoff, small, in their colours.
 */
export function IssueSpark({ kind, hist, curve, cutoffIdx, color, marks, w = 120, h = 48 }: {
  kind: "hist" | "pr"; hist: { neg: number[]; pos: number[] }; curve: Metrics[]; cutoffIdx: number; color: string; marks?: { id: string; name: string; color: string; recall: number | null; precision: number | null }[]; w?: number; h?: number;
}) {
  if (kind === "hist") {
    const bins = hist.neg.length, bw = w / bins, mid = h / 2 - 1;
    const maxN = Math.max(1, ...hist.neg), maxP = Math.max(1, ...hist.pos);
    const cx = (cutoffIdx / GRID_N) * w;
    return (
      <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="cut-spark" aria-hidden>
        <rect x={cx} y={0} width={Math.max(0, w - cx)} height={h} fill={color} opacity={0.07} />
        {hist.neg.map((n, i) => { const bh = (n / maxN) * (mid - 2); return <rect key={`n${i}`} x={i * bw + 0.5} y={mid - bh} width={Math.max(0.5, bw - 1)} height={bh} fill="var(--ink-4)" opacity={0.7} />; })}
        {hist.pos.map((n, i) => { const bh = (n / maxP) * (mid - 2); return <rect key={`p${i}`} x={i * bw + 0.5} y={mid + 2} width={Math.max(0.5, bw - 1)} height={bh} fill={color} opacity={0.85} />; })}
        <line x1={0} x2={w} y1={mid + 1} y2={mid + 1} stroke="var(--line-2)" />
        <line x1={cx} x2={cx} y1={0} y2={h} stroke="var(--ink)" strokeWidth={1.2} className="cut-rule" />
      </svg>
    );
  }
  const X = (r: number) => 2 + r * (w - 4), Y = (p: number) => h - 2 - p * (h - 4);
  let d = "", pen = false;
  for (const m of curve) { if (m.recall == null || m.precision == null) { pen = false; continue; } d += `${pen ? "L" : "M"}${X(m.recall).toFixed(1)} ${Y(m.precision).toFixed(1)}`; pen = true; }
  const c = curve[cutoffIdx], d5 = curve[GRID_N / 2];
  return (
    <svg width={w} height={h} viewBox={`0 0 ${w} ${h}`} className="cut-spark" aria-hidden>
      <rect x={0.5} y={0.5} width={w - 1} height={h - 1} fill="none" stroke="var(--line)" />
      <path d={d} fill="none" stroke={color} strokeWidth={1.2} opacity={0.8} />
      {marks?.map((k) => (k.recall != null && k.precision != null ? <circle key={k.id} cx={X(k.recall)} cy={Y(k.precision)} r={2.2} fill={k.color} opacity={0.75}><title>{k.name} at this cutoff</title></circle> : null))}
      {d5?.recall != null && d5.precision != null && <circle cx={X(d5.recall)} cy={Y(d5.precision)} r={2.6} fill="var(--panel)" stroke={color} strokeWidth={1.1} />}
      {c?.recall != null && c.precision != null && <circle cx={X(c.recall)} cy={Y(c.precision)} r={3} fill={color} className="cut-cur" />}
    </svg>
  );
}
