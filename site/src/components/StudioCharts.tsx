import { useMemo, useRef } from "react";
import type { CI } from "../data";
import { LogoGlyph, logoFor } from "../logos";
import { DECIDER_TEXT, useSize, useWidth } from "./ui";

/**
 * Screenshot-studio charts for the Cost, Speed and Stability plots (StudioPage.tsx): static SVG, no tooltips, hover or motion; every
 * figure is written on the chart. They read the same CSS variables as the dashboard cards (--ink*, --line, --grid, --axis, --bar-alpha)
 * and the item colour from the roster, so the studio's Style presets (styles.css .studio-plot[data-style]) restyle them unchanged.
 * Gridlines carry className="gl" like PRScatter's so a preset can dot them.
 */

/** One row of a StudioBars chart. `lo`/`hi` draw a whisker (an interval around `value`); `sub` is a muted secondary figure after the label; `empty` replaces "not measured". */
export type StudioRow = { id: string; name: string; color: string; value: number | null; lo?: number | null; hi?: number | null; label: string; sub?: string; empty?: string; decider?: boolean; subset?: string | null };

const ROW0 = 30, TOP0 = 8;
/** Stroke widths and mark radii read the studio's high-contrast variables (styles.css .studio-plot[data-contrast="high"]); unset, they are the defaults given here. */
const SW = (base: number) => ({ strokeWidth: `calc(${base} * var(--sw-mult, 1))` });
const R = (base: number) => ({ r: `calc(${base}px + var(--r-add, 0px))` } as React.CSSProperties);

/** `nice` step for a linear axis with about five ticks. */
function linTicks(d0: number, d1: number): number[] {
  const span = d1 - d0;
  if (!(span > 0)) return [d0];
  const raw = span / 5, mag = 10 ** Math.floor(Math.log10(raw)), r = raw / mag;
  const step = (r >= 5 ? 5 : r >= 2.5 ? 2.5 : r >= 2 ? 2 : 1) * mag;
  const out: number[] = [];
  for (let t = Math.ceil(d0 / step - 1e-9) * step; t <= d1 + 1e-9; t += step) out.push(+t.toPrecision(12));
  return out;
}
/** Powers of ten across the domain; 2× and 5× as well when there are fewer than three decades. */
function logTicks(d0: number, d1: number): number[] {
  const a = Math.floor(Math.log10(d0)), b = Math.ceil(Math.log10(d1));
  const out: number[] = [];
  for (let e = a; e <= b; e++) {
    const p = 10 ** e;
    out.push(p);
    if (b - a < 3) { if (2 * p < d1) out.push(2 * p); if (5 * p < d1) out.push(5 * p); }
  }
  return out.filter((t) => t >= d0 - 1e-12 && t <= d1 + 1e-12).sort((x, y) => x - y);
}

/**
 * Horizontal bars (`kind: "bar"`) or a dot plot (`kind: "dot"`: whisker and dot in the row's colour) on a linear or log axis, one row per item,
 * the figure written after the bar. `domain` fixes the axis (linear: bars grow from its start, the zoomed Stability view); otherwise linear runs
 * from 0 to a little past the largest value or whisker end and log from the decade below the smallest value to the decade above the largest.
 * `sort`: ascending, descending or the given order; rows without a value sink to the bottom in muted ink (or pass them filtered out).
 * The width follows the host; the height follows the rows (the studio panel's `auto` mode).
 * `textScale` (the studio's Text control) multiplies every font size and, with it, the row height, the label and value columns and the axis area.
 */
export function StudioBars({ rows, kind = "bar", scale = "linear", domain, sort = "asc", axis, fmtTick, logos = true, labelW, textScale = 1 }: { rows: StudioRow[]; kind?: "bar" | "dot"; scale?: "linear" | "log"; domain?: [number, number]; sort?: "asc" | "desc" | "none"; axis: string; fmtTick: (v: number) => string; logos?: boolean; labelW?: number; textScale?: number }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const W = useWidth(hostRef, 900);
  const s = textScale, ROW = ROW0 * s, TOP = TOP0 * s;
  const LABEL_W = labelW ?? Math.min(260 * s, Math.max(170 * s, ...rows.map((r) => (r.name.length * 6.6 + (logos ? 44 : 24)) * s)));
  // the value column after the longest bar: the figure, then the muted secondary figure when a row carries one
  const VALUE_W = Math.max(90, ...rows.map((r) => (r.value == null ? (r.empty ?? "not measured").length * 6.3 : r.label.length * 7.6 + (r.sub ? r.sub.length * 6.2 + 10 : 0)) + 14)) * s;
  const sorted = sort === "none" ? rows : [...rows].sort((a, b) => {
    const va = a.value ?? (sort === "asc" ? Infinity : -Infinity), vb = b.value ?? (sort === "asc" ? Infinity : -Infinity);
    return sort === "asc" ? va - vb : vb - va;
  });
  const measured = sorted.filter((r) => r.value != null);
  const x0 = LABEL_W, plotW = Math.max(120, W - LABEL_W - VALUE_W);
  const ends = measured.flatMap((r) => [r.value!, r.hi ?? r.value!, r.lo ?? r.value!]);
  const dom = useMemo<[number, number]>(() => {
    if (domain) return domain;
    if (scale === "log") {
      const pos = ends.filter((v) => v > 0);
      if (!pos.length) return [0.01, 1];
      const mn = Math.min(...pos), mx = Math.max(...pos);
      return [10 ** Math.floor(Math.log10(mn)), 10 ** Math.ceil(Math.log10(mx) - 1e-9)];
    }
    const mx = Math.max(1e-9, ...ends);
    return [0, mx * 1.06];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain, scale, ends.join("|")]);
  const X = (v: number) => {
    if (scale === "log") {
      const l0 = Math.log10(dom[0]), l1 = Math.log10(dom[1]);
      if (v <= 0) return x0;
      return x0 + Math.min(1, Math.max(0, (Math.log10(v) - l0) / (l1 - l0 || 1))) * plotW;
    }
    return x0 + Math.min(1, Math.max(0, (v - dom[0]) / (dom[1] - dom[0] || 1))) * plotW;
  };
  const ticks = scale === "log" ? logTicks(dom[0], dom[1]) : linTicks(dom[0], dom[1]);
  const n = sorted.length, bottom = TOP + n * ROW, h = bottom + 46 * s;
  return (
    <div ref={hostRef} style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
        {ticks.map((t) => (
          <g key={t}>
            <line className="gl" x1={X(t)} x2={X(t)} y1={TOP} y2={bottom} stroke="var(--grid)" />
            <text x={X(t)} y={bottom + 16 * s} fontSize={11 * s} textAnchor="middle" fill="var(--ink-3)" className="mono">{fmtTick(t)}</text>
          </g>
        ))}
        {sorted.map((r, i) => {
          const cy = TOP + i * ROW + ROW / 2;
          const nameX = logos ? 30 * s : LABEL_W - 14 * s;
          const label = `${r.name}${r.subset ? " *" : ""}`;
          if (r.value == null) {
            return (
              <g key={r.id}>
                {logos && <g color="var(--ink-4)"><LogoGlyph model={r.id} cx={12 * s} cy={cy} size={14 * s} opacity={0.6} /></g>}
                <text x={nameX} y={cy + 4.5 * s} fontSize={12.5 * s} textAnchor={logos ? "start" : "end"} fill="var(--ink-4)" className="nm">{label}</text>
                <text x={x0 + 8 * s} y={cy + 4.5 * s} fontSize={11.5 * s} fill="var(--ink-4)">{r.empty ?? "not measured"}</text>
              </g>
            );
          }
          const v = r.value, xv = X(v);
          const lo = r.lo ?? null, hi = r.hi ?? null;
          const xlo = lo == null ? xv : X(lo), xhi = hi == null ? xv : X(hi);
          const end = Math.max(xv, xhi) + 9 * s;
          return (
            <g key={r.id}>
              {logos && <g color="var(--ink-2)"><LogoGlyph model={r.id} cx={12 * s} cy={cy} size={14 * s} /></g>}
              <text x={nameX} y={cy + 4.5 * s} fontSize={12.5 * s} textAnchor={logos ? "start" : "end"} fill="var(--ink-2)" className="nm" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
              {kind === "bar" ? (
                <>
                  <rect x={x0} y={cy - 6 * s} width={Math.max(1.5, xv - x0)} height={12 * s} fill={r.color} rx={1.5} style={{ fillOpacity: v === 0 ? "calc(var(--bar-alpha) * 0.5)" : "var(--bar-alpha)" }} />
                  {(lo != null || hi != null) && xhi - xlo > 0.5 && (
                    <g stroke="var(--ink)" strokeWidth={1} style={{ ...SW(1), opacity: "var(--op-whisker, 0.65)" }}>
                      <line x1={xlo} x2={xhi} y1={cy} y2={cy} />
                      <line x1={xlo} x2={xlo} y1={cy - 4 * s} y2={cy + 4 * s} />
                      <line x1={xhi} x2={xhi} y1={cy - 4 * s} y2={cy + 4 * s} />
                    </g>
                  )}
                </>
              ) : (
                <>
                  {xhi - xlo > 0.5 && <line x1={xlo} x2={xhi} y1={cy} y2={cy} stroke={r.color} strokeWidth={1.75} style={SW(1.75)} />}
                  <circle cx={xv} cy={cy} r={4.5} fill={r.color} style={R(4.5)} />
                </>
              )}
              <text x={end} y={cy + 4.5 * s} fontSize={12 * s} fill="var(--ink)" className="mono">{r.label}</text>
              {r.sub && <text x={end + (r.label.length * 7.6 + 10) * s} y={cy + 4.5 * s} fontSize={10.5 * s} fill="var(--ink-3)" className="mono">{r.sub}</text>}
            </g>
          );
        })}
        <g stroke="var(--axis)" style={SW(1)}>
          <line x1={x0} x2={x0} y1={TOP} y2={bottom} />
          <line x1={x0} x2={x0 + plotW} y1={bottom} y2={bottom} />
        </g>
        <text x={x0} y={bottom + 36 * s} fontSize={11.5 * s} fill="var(--ink-3)" className="ax">{axis}</text>
        {n === 0 && <text x={W / 2} y={30} textAnchor="middle" fontSize={13 * s} fill="var(--ink-4)">Select at least one model.</text>}
      </svg>
    </div>
  );
}

/** A point of the cost-against-recall scatter: cost on a log x axis, recall with its 95% interval as a vertical whisker. */
export type StudioScatterPt = { id: string; name: string; color: string; x: number | null; y: CI; decider?: boolean; subset?: string | null };

const PR = 24, PT = 18;

/** Cost (log x) against recall (y, 95% whisker). Sized to the host's box like PRScatter's `fill` mode (host must be positioned). */
export function StudioScatter({ pts, xLabel, yLabel = "Recall", fmtX, logos = true, emptyText = "Select at least one model.", textScale = 1 }: { pts: StudioScatterPt[]; xLabel: string; yLabel?: string; fmtX: (v: number) => string; logos?: boolean; emptyText?: string; textScale?: number }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const sz = useSize(hostRef, { w: 900, h: 520 });
  const W = sz.w, H = Math.max(300, sz.h);
  // the left and bottom margins hold the tick labels, so they grow with the text scale (60 and 50 at scale 1)
  const s = textScale, PL = Math.round(44 + 16 * s), PB = Math.round(26 + 24 * s);
  const drawn = pts.filter((p): p is StudioScatterPt & { x: number; y: NonNullable<CI> } => p.x != null && p.x > 0 && !!p.y);
  const xs = drawn.map((p) => p.x);
  const xd: [number, number] = xs.length ? [10 ** Math.floor(Math.log10(Math.min(...xs))), 10 ** Math.ceil(Math.log10(Math.max(...xs)) - 1e-9)] : [0.01, 100];
  const ylo = Math.min(1, ...drawn.map((p) => p.y[1])), yhi = Math.max(0, ...drawn.map((p) => p.y[2]));
  const pad = Math.max(0.02, (yhi - ylo) * 0.12);
  const yd: [number, number] = drawn.length ? [Math.max(0, ylo - pad), Math.min(1, yhi + pad)] : [0, 1];
  const X = (v: number) => PL + ((Math.log10(v) - Math.log10(xd[0])) / (Math.log10(xd[1]) - Math.log10(xd[0]) || 1)) * (W - PL - PR);
  const Y = (v: number) => PT + (1 - (v - yd[0]) / (yd[1] - yd[0] || 1)) * (H - PT - PB);
  const xt = logTicks(xd[0], xd[1]), yt = linTicks(yd[0], yd[1]);
  // labels: right of the mark, else left, above, below; skipped when nothing fits
  const placed: { x: number; y: number; w: number; h: number }[] = [];
  const dots = drawn.map((p) => ({ x: X(p.x), y: Y(p.y[0]) }));
  const clash = (a: { x: number; y: number; w: number; h: number }) => placed.some((b) => a.x < b.x + b.w + 2 && a.x + a.w + 2 > b.x && a.y < b.y + b.h + 1 && a.y + a.h + 1 > b.y) || dots.some((d) => d.x > a.x - 6 && d.x < a.x + a.w + 6 && d.y > a.y - 6 && d.y < a.y + a.h + 6);
  const labels = drawn.map((p, i) => {
    const text = `${p.name}${p.subset ? " *" : ""}`, w = text.length * 6.6 * s + 4, h = 14 * s, o = 11 * s, { x, y } = dots[i];
    const cands = [{ x: x + o, y: y - h / 2 }, { x: x - o - w, y: y - h / 2 }, { x: x - w / 2, y: y - 14 * s - h }, { x: x - w / 2, y: y + 14 * s }];
    const c = cands.find((cc) => cc.x >= PL && cc.x + w <= W - 2 && cc.y >= 0 && !clash({ ...cc, w, h }));
    if (c) placed.push({ ...c, w, h });
    return c ? { ...c, text } : null;
  });
  return (
    <div ref={hostRef} style={{ position: "absolute", inset: 0 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ display: "block", overflow: "visible" }}>
        {xt.map((t) => (
          <g key={`x${t}`}>
            <line className="gl" x1={X(t)} x2={X(t)} y1={PT} y2={H - PB} stroke="var(--grid)" />
            <text x={X(t)} y={H - PB + 16 * s} fontSize={10.5 * s} textAnchor="middle" fill="var(--ink-3)" className="mono">{fmtX(t)}</text>
          </g>
        ))}
        {yt.map((t) => (
          <g key={`y${t}`}>
            <line className="gl" x1={PL} x2={W - PR} y1={Y(t)} y2={Y(t)} stroke="var(--grid)" />
            <text x={PL - 8} y={Y(t) + 3.5 * s} fontSize={10.5 * s} textAnchor="end" fill="var(--ink-3)" className="mono">{`${+(t * 100).toFixed(1)}%`}</text>
          </g>
        ))}
        <g stroke="var(--axis)" style={SW(1)}>
          <line x1={PL} x2={W - PR} y1={H - PB} y2={H - PB} />
          <line x1={PL} x2={PL} y1={PT} y2={H - PB} />
        </g>
        <text x={(PL + W - PR) / 2} y={H - 10 * s} fontSize={12 * s} textAnchor="middle" fill="var(--ink-2)" className="ax">{xLabel}</text>
        <text x={14 * s} y={(PT + H - PB) / 2} fontSize={12 * s} textAnchor="middle" fill="var(--ink-2)" className="ax" transform={`rotate(-90 ${14 * s} ${(PT + H - PB) / 2})`}>{yLabel}</text>
        {drawn.map((p, i) => {
          const x = X(p.x), y = Y(p.y[0]), y1 = Y(p.y[2]), y2 = Y(p.y[1]);
          const l = labels[i];
          return (
            <g key={p.id}>
              <g stroke={p.color} strokeWidth={1.5} style={{ ...SW(1.5), opacity: "var(--op-whisker, 0.75)" }}>
                <line x1={x} x2={x} y1={y1} y2={y2} />
                <line x1={x - 4} x2={x + 4} y1={y1} y2={y1} />
                <line x1={x - 4} x2={x + 4} y1={y2} y2={y2} />
              </g>
              {logos && logoFor(p.id) ? <g color={p.color} style={{ transform: "scale(var(--mark-scale, 1))", transformOrigin: `${x}px ${y}px` }}><LogoGlyph model={p.id} cx={x} cy={y} size={13} /></g> : <circle cx={x} cy={y} r={4} fill={p.color} style={R(4)} />}
              {l && <text x={l.x} y={l.y + 10.5 * s} fontSize={11.5 * s} fill="var(--ink)" className="nm" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 2.5, strokeLinejoin: "round" }}>{l.text}</text>}
            </g>
          );
        })}
        {drawn.length === 0 && <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={13 * s} fill="var(--ink-4)">{emptyText}</text>}
      </svg>
    </div>
  );
}
