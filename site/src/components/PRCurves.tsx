import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type PointerEvent as ReactPointerEvent } from "react";
import { fmtInt, fmtPct } from "../data";
import { fmtThreshold, type CurvePoint } from "../sweep";
import { TipBox, textWidth, useFontMetrics, useSize, type Tip, type TipAnchor, type TipContent } from "./ui";
import { hoverable } from "./hover";
import { PlotBgPattern } from "./plotBg";
import { axisMargins } from "./PRScatter";
import { pctTicks } from "./ticks";

/**
 * One model's recall/precision curve on the Trade-off page (Tradeoff.tsx): every point of its sweep (sweep.ts curvePoints, lowest threshold
 * first), the index of its operating point (`ti`, the draggable marker) and of its published point (`pubI`, the 0.50 cut, a fixed open ring).
 * Points whose precision is undefined (nothing flagged) are not drawn.
 */
export type CurveSeries = { id: string; name: string; color: string; pts: CurvePoint[]; ti: number; pubI: number; subset?: string | null };

const PR = 20, PT = 18, TICK_FS = 10.5, TITLE_FS = 12;
/** Marker radius (the operating point), the published ring's radius, and the hit radius for dragging. */
const MARK_R = 5.5, PUB_R = 3, HIT_R = 12;
/** The iso-F1 contours drawn faintly behind the curves. */
const ISO_F1 = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9];

/** The tooltip for a point on a curve: the cut and what it buys. */
export const curveTip = (s: CurveSeries, p: CurvePoint, sub?: string): TipContent => ({
  title: s.name, color: s.color,
  lines: [["Threshold", `p ≥ ${fmtThreshold(p.t)}`], ["Recall", fmtPct(p.recall)], ["Precision", fmtPct(p.precision)], ["F1", fmtPct(p.f1)], ["Flagged", `${fmtInt(p.flagged)} of ${fmtInt(p.n)} (${fmtPct(p.share)})`]],
  sub,
});

/**
 * Recall (x) against precision (y), one curve per series swept over the threshold, in plain SVG as the site's other charts are. On each curve a
 * draggable marker is the series' operating point: dragging it (pointer capture) or, focused, the arrow keys (← / ↓ raise the threshold and move
 * it left along the curve; → / ↑ lower it; Shift steps five cuts; Home / End the grid's ends) report the nearest grid index through `onIndex`. The
 * published point (the 0.50 cut) is a small open ring on every curve. Hovering a curve shows that series' numbers at the nearest point, and names
 * the series to the section's cross-chart hover (hover.tsx), as the readout table does. `zoom` fits the axes to the curves' points; iso-F1 contours
 * (precision = F·r / (2r − F)) sit faintly behind, labelled at their right end.
 */
export function PRCurves({ series, onIndex, highlight, onHover, zoom, height = 440, fill = false, emptyText, unit = "documents" }: {
  series: CurveSeries[]; onIndex: (id: string, i: number) => void; highlight?: string | null; onHover?: (id: string | null) => void; zoom: boolean; height?: number; fill?: boolean; emptyText?: string; unit?: string;
}) {
  // the tooltip follows the pointer along a curve and the marker while it is dragged, so it is set directly (no rest delay: ui.tsx useTip keeps one
  // box per title, which would hold the numbers of the point it opened on)
  const hostRef = useRef<HTMLDivElement>(null);
  // marker drag in progress: pointer capture on the marker; each move snaps the operating point to the nearest grid cut
  const drag = useRef<{ id: string; pointer: number } | null>(null);
  const [tip, setTip] = useState<Tip>(null);
  const show = (e: { clientX: number; clientY: number }, anchor: TipAnchor, t: TipContent) => { const r = hostRef.current?.getBoundingClientRect(); setTip({ x: e.clientX - (r?.left ?? 0), y: e.clientY - (r?.top ?? 0), anchor, ...t }); };
  const hide = () => setTip(null);
  // a marker can be released outside the host (a drag that ran off the card): while a tip is open, pointer movement outside the host closes it
  useEffect(() => {
    if (!tip) return;
    const onMoveDoc = (e: MouseEvent) => { if (!drag.current && !hostRef.current?.contains(e.target as Node)) setTip(null); };
    document.addEventListener("mousemove", onMoveDoc);
    return () => document.removeEventListener("mousemove", onMoveDoc);
  }, [tip]);
  useFontMetrics();
  const svgRef = useRef<SVGSVGElement>(null);
  const bgId = `bg-${useId().replace(/[^A-Za-z0-9_-]/g, "")}`;
  const sz = useSize(hostRef, { w: 760, h: height });
  const W = sz.w, H = fill ? Math.max(300, sz.h) : height;
  const drawable = (p: CurvePoint): p is CurvePoint & { precision: number } => p.precision != null;

  const dom = useMemo(() => {
    const all = series.flatMap((s) => s.pts.filter(drawable));
    if (!zoom || !all.length) return { x: [0, 1] as [number, number], y: [0, 1] as [number, number] };
    const pad = (lo: number, hi: number): [number, number] => { const p = Math.max(0.02, (hi - lo) * 0.08); return [Math.max(0, lo - p), Math.min(1, hi + p)]; };
    return { x: pad(Math.min(...all.map((p) => p.recall)), Math.max(...all.map((p) => p.recall))), y: pad(Math.min(...all.map((p) => p.precision)), Math.max(...all.map((p) => p.precision))) };
  }, [series, zoom]);
  const step = (span: number) => (span > 0.6 ? 20 : span > 0.3 ? 10 : span > 0.12 ? 5 : span > 0.06 ? 2 : 1);
  const xt = pctTicks(dom.x[0], dom.x[1], step(dom.x[1] - dom.x[0])), yt = pctTicks(dom.y[0], dom.y[1], step(dom.y[1] - dom.y[0]));
  const tickLabel = (t: number) => `${Math.round(t * 100)}%`;
  const { PL, PB, titleX } = axisMargins(yt.map(tickLabel), 1);
  const AX = H - PB, top = PT;
  const X = (v: number) => PL + ((v - dom.x[0]) / (dom.x[1] - dom.x[0] || 1)) * (W - PL - PR);
  const Y = (v: number) => top + (1 - (v - dom.y[0]) / (dom.y[1] - dom.y[0] || 1)) * (AX - top);
  const inPlot = (x: number, y: number) => x >= PL - 0.5 && x <= W - PR + 0.5 && y >= top - 0.5 && y <= AX + 0.5;

  // iso-F1 contours: precision = F r / (2r − F), for r from where precision would be 1 (r = F / (2 − F)) to the right edge, clipped to the domain
  const iso = useMemo(() => ISO_F1.map((F) => {
    const r0 = Math.max(dom.x[0], F / (2 - F) + 1e-6), r1 = dom.x[1];
    if (r0 >= r1) return null;
    const pts: [number, number][] = [];
    for (let k = 0; k <= 80; k++) {
      const r = r0 + ((r1 - r0) * k) / 80, p = (F * r) / (2 * r - F);
      if (p >= dom.y[0] && p <= dom.y[1]) pts.push([X(r), Y(p)]);
    }
    if (pts.length < 2) return null;
    const end = pts[pts.length - 1];
    return { F, d: pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(""), end };
  }).filter((c): c is { F: number; d: string; end: [number, number] } => !!c), [dom, W, H]); // eslint-disable-line react-hooks/exhaustive-deps

  // the highlighted series is drawn last (on top); the rest keep their order
  const hl = highlight != null && series.some((s) => s.id === highlight) ? highlight : null;
  const drawn = hl == null ? series : [...series.filter((s) => s.id !== hl), ...series.filter((s) => s.id === hl)];

  const pathOf = (s: CurveSeries) => {
    let d = "", open = false;
    for (const p of s.pts) {
      if (!drawable(p)) { open = false; continue; }
      d += `${open ? "L" : "M"}${X(p.recall).toFixed(1)} ${Y(p.precision).toFixed(1)}`;
      open = true;
    }
    return d;
  };
  const at = (s: CurveSeries, i: number) => { const p = s.pts[i]; return drawable(p) ? { x: X(p.recall), y: Y(p.precision), p } : null; };

  // the plot-pixel position of a pointer event (the SVG is drawn at native scale: viewBox = width × height)
  const toPlot = (e: { clientX: number; clientY: number }) => { const r = svgRef.current?.getBoundingClientRect(); return r ? { x: e.clientX - r.left, y: e.clientY - r.top } : { x: 0, y: 0 }; };
  /** The index of the series' drawable point nearest a plot position. */
  const nearest = (s: CurveSeries, x: number, y: number): number => {
    let best = -1, bd = Infinity;
    s.pts.forEach((p, i) => { if (!drawable(p)) return; const d = (X(p.recall) - x) ** 2 + (Y(p.precision) - y) ** 2; if (d < bd) { bd = d; best = i; } });
    return best;
  };

  // the drag follows the pointer on the window (so it survives leaving the marker, the card or the SVG) until it is released; pointer capture where the browser grants it
  const onDown = (s: CurveSeries) => (e: ReactPointerEvent<SVGGElement>) => {
    if (e.button !== 0 && e.pointerType === "mouse") return;
    e.preventDefault(); e.stopPropagation();
    const el = e.currentTarget;
    try { el.setPointerCapture(e.pointerId); } catch { /* synthetic or already-released pointer: the window listeners carry the drag */ }
    drag.current = { id: s.id, pointer: e.pointerId };
    el.focus?.();
    const move = (ev: PointerEvent) => {
      if (drag.current?.id !== s.id) return;
      const { x, y } = toPlot(ev);
      const i = nearest(s, x, y);
      const q = i >= 0 ? at(s, i) : null;
      if (q) show(ev, { kind: "mark", x: q.x, y: q.y, r: HIT_R }, curveTip(s, q.p, `${unit}; release to set`));
      if (i >= 0) onIndex(s.id, i);
    };
    const up = () => {
      drag.current = null;
      try { el.releasePointerCapture(e.pointerId); } catch { /* not captured */ }
      window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); window.removeEventListener("pointercancel", up);
    };
    window.addEventListener("pointermove", move); window.addEventListener("pointerup", up); window.addEventListener("pointercancel", up);
  };
  // keyboard on a focused marker: the arrows walk the grid; a step is one cut, five with Shift
  const onKey = (s: CurveSeries) => (e: ReactKeyboardEvent<SVGGElement>) => {
    const n = s.pts.length, big = e.shiftKey ? 5 : 1;
    let i = s.ti;
    if (e.key === "ArrowLeft" || e.key === "ArrowDown") i = Math.min(n - 1, s.ti + big);
    else if (e.key === "ArrowRight" || e.key === "ArrowUp") i = Math.max(0, s.ti - big);
    else if (e.key === "Home") i = 0;
    else if (e.key === "End") i = n - 1;
    else if (e.key === "PageDown") i = Math.min(n - 1, s.ti + 10);
    else if (e.key === "PageUp") i = Math.max(0, s.ti - 10);
    else return;
    e.preventDefault();
    hide(); // a tooltip left open by the pointer would show the numbers of the cut just left
    // skip cuts with nothing flagged (no point to stand on)
    while (i >= 0 && i < n && !drawable(s.pts[i])) i += i > s.ti ? 1 : -1;
    if (i >= 0 && i < n && i !== s.ti) onIndex(s.id, i);
  };

  // marker labels: beside the marker, right of it where that fits, else left, above or below; avoiding other markers and placed labels
  const labels = useMemo(() => {
    const placed: { x: number; y: number; w: number; h: number }[] = [];
    const marks = series.map((s) => at(s, s.ti));
    const hit = (a: { x: number; y: number; w: number; h: number }) =>
      placed.some((b) => a.x < b.x + b.w + 2 && a.x + a.w + 2 > b.x && a.y < b.y + b.h + 1 && a.y + a.h + 1 > b.y) ||
      marks.some((m) => m && m.x > a.x - 7 && m.x < a.x + a.w + 7 && m.y > a.y - 7 && m.y < a.y + a.h + 7);
    return series.map((s, k) => {
      const m = marks[k];
      if (!m) return null;
      const text = s.name + (s.subset ? " *" : ""), w = textWidth(text, 11) + 4, h = 13, o = 10;
      const cands = [
        { x: m.x + o, y: m.y - h / 2 }, { x: m.x - o - w, y: m.y - h / 2 }, { x: m.x - w / 2, y: m.y - o - h }, { x: m.x - w / 2, y: m.y + o },
        { x: m.x + o, y: m.y - h - 4 }, { x: m.x + o, y: m.y + 4 }, { x: m.x - o - w, y: m.y - h - 4 }, { x: m.x - o - w, y: m.y + 4 },
      ];
      const c = cands.find((cc) => cc.x >= PL && cc.x + w <= W - 2 && cc.y >= 0 && cc.y + h <= H && !hit({ ...cc, w, h }));
      if (!c) return null;
      placed.push({ ...c, w, h });
      return { ...c, w, h, text };
    });
  }, [series, dom, W, H]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div ref={hostRef} data-tip-host style={fill ? { position: "absolute", inset: 0 } : { position: "relative" }}>
      <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ display: "block", overflow: "visible" }} className="pr-curves">
        <defs><PlotBgPattern id={bgId} kind="dots" /></defs>
        <rect x={PL} y={top} width={W - PR - PL} height={AX - top} fill={`url(#${bgId})`} />
        {xt.map((t) => (
          <g key={`x${t}`}>
            <line className="gl" x1={X(t)} x2={X(t)} y1={top} y2={AX} stroke="var(--grid-x, var(--grid))" />
            <text x={X(t)} y={AX + 16} fontSize={TICK_FS} textAnchor="middle" fill="var(--ink-3)" className="mono">{tickLabel(t)}</text>
          </g>
        ))}
        {yt.map((t) => (
          <g key={`y${t}`}>
            <line className="gl" x1={PL} x2={W - PR} y1={Y(t)} y2={Y(t)} stroke="var(--grid)" />
            <text x={PL - 8} y={Y(t) + 3.5} fontSize={TICK_FS} textAnchor="end" fill="var(--ink-3)" className="mono">{tickLabel(t)}</text>
          </g>
        ))}
        {/* iso-F1 contours, faint, labelled at the right end */}
        <g className="iso-f1" fill="none" stroke="var(--line-2)" strokeWidth={0.75} strokeDasharray="2 3">
          {iso.map((c) => <path key={c.F} d={c.d} />)}
        </g>
        {iso.map((c) => (
          <text key={`l${c.F}`} x={Math.min(c.end[0], W - PR) - 3} y={c.end[1] - 3} fontSize={9.5} textAnchor="end" fill="var(--ink-4)" className="mono">F1 {c.F.toFixed(1)}</text>
        ))}
        <g stroke="var(--axis)" style={{ strokeWidth: "var(--sw-mult, 1)" }}>
          <line x1={PL} x2={W - PR} y1={AX} y2={AX} />
          <line x1={PL} x2={PL} y1={top} y2={AX} stroke="var(--axis-y, var(--axis))" />
        </g>
        <text x={(PL + W - PR) / 2} y={AX + PB - 10} fontSize={TITLE_FS} textAnchor="middle" fill="var(--ink-2)" className="ax">Recall</text>
        <text x={titleX} y={(top + AX) / 2} fontSize={TITLE_FS} textAnchor="middle" fill="var(--ink-2)" className="ax" transform={`rotate(-90 ${titleX} ${(top + AX) / 2})`}>Precision</text>

        {/* the curves: a wide transparent stroke for hovering under a visible one; the highlighted series heavier, the others a little lighter while one is */}
        {drawn.map((s) => {
          const d = pathOf(s);
          const dim = hl != null && hl !== s.id;
          return (
            <g key={`c${s.id}`} {...hoverable(onHover, s.id)} className="pr-curve">
              <path d={d} fill="none" stroke={s.color} strokeWidth={hl === s.id ? 2.5 : 1.6} strokeLinejoin="round" strokeLinecap="round" opacity={dim ? 0.45 : 1} style={{ transition: "opacity 120ms, stroke-width 120ms" }} />
              <path
                d={d} fill="none" stroke="transparent" strokeWidth={14} style={{ pointerEvents: "stroke", cursor: "crosshair" }}
                onMouseMove={(e) => { if (drag.current) return; const { x, y } = toPlot(e); const i = nearest(s, x, y); const q = i >= 0 ? at(s, i) : null; if (q) show(e, { kind: "mark", x: q.x, y: q.y, r: 6 }, curveTip(s, q.p, `${unit}; click to move the marker here`)); }}
                onMouseLeave={hide}
                onClick={(e) => { const { x, y } = toPlot(e); const i = nearest(s, x, y); if (i >= 0) onIndex(s.id, i); }}
              />
            </g>
          );
        })}
        {/* the published point (the 0.50 cut): a small open ring, fixed */}
        {drawn.map((s) => { const q = at(s, s.pubI); return q && inPlot(q.x, q.y) ? <circle key={`p${s.id}`} cx={q.x} cy={q.y} r={PUB_R} fill="var(--panel)" stroke={s.color} strokeWidth={1.25} style={{ pointerEvents: "none" }} /> : null; })}
        {/* the operating markers, draggable and focusable, with their labels */}
        {drawn.map((s) => {
          const q = at(s, s.ti);
          if (!q) return null;
          const k = series.indexOf(s), l = labels[k];
          const moved = s.ti !== s.pubI;
          return (
            <g key={`m${s.id}`} {...hoverable(onHover, s.id)} className="pr-mark">
              <g
                transform={`translate(${q.x} ${q.y})`} tabIndex={0} role="slider" aria-label={`${s.name} threshold`} aria-valuemin={s.pts[0].t} aria-valuemax={s.pts[s.pts.length - 1].t} aria-valuenow={q.p.t}
                aria-valuetext={`p ≥ ${fmtThreshold(q.p.t)}: recall ${fmtPct(q.p.recall)}, precision ${fmtPct(q.p.precision)}`}
                style={{ cursor: "grab", outline: "none", touchAction: "none" }}
                onPointerDown={onDown(s)} onKeyDown={onKey(s)}
                onMouseMove={(e) => { if (drag.current) return; show(e, { kind: "mark", x: q.x, y: q.y, r: HIT_R }, curveTip(s, q.p, `${unit}; drag, or use the arrow keys`)); }} onMouseLeave={hide}
              >
                <circle className="hit" r={HIT_R} fill="transparent" />
                <circle className="pr-mark-ring" r={MARK_R + 3} fill="none" stroke={s.color} strokeWidth={1} opacity={0} />
                <circle r={MARK_R} fill={s.color} stroke="var(--panel)" strokeWidth={1.5} />
                {moved && <circle r={1.6} fill="var(--panel)" />}
              </g>
              {l && (
                <text x={l.x} y={l.y + 10} fontSize={11} fill="var(--ink)" className="nm" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 2.5, strokeLinejoin: "round", pointerEvents: "none" }}>{l.text}</text>
              )}
            </g>
          );
        })}
        {series.length === 0 && <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={13} fill="var(--ink-4)">{emptyText ?? "Select at least one model."}</text>}
      </svg>
      <TipBox tip={tip} />
    </div>
  );
}
