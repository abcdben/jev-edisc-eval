import { useMemo } from "react";
import type { CI } from "../data";
import { TipBox, useTip, type TipLine } from "./ui";

export type PRItem = {
  id: string; name: string; color: string; recall: CI; precision: CI; dashed?: boolean; subset?: string | null;
  tip: { lines: TipLine[]; notes?: string[] };
};

const W = 760, H = 520, PL = 56, PR = 20, PT = 18, PB = 48;

function niceTicks(lo: number, hi: number): number[] {
  const span = hi - lo;
  const step = span > 0.6 ? 0.2 : span > 0.3 ? 0.1 : span > 0.12 ? 0.05 : span > 0.06 ? 0.02 : 0.01;
  const out: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(Math.round(t * 1000) / 1000);
  return out;
}

/** Recall (x) against precision (y). Each item is a dot at the point estimate inside a box spanning both 95% intervals. */
export function PRScatter({ items, zoom, xLabel = "Recall", yLabel = "Precision", emptyText }: { items: PRItem[]; zoom: boolean; xLabel?: string; yLabel?: string; emptyText?: string }) {
  const { tip, show, hide, hostRef } = useTip();
  const pts = items.filter((it) => it.recall && it.precision) as (PRItem & { recall: NonNullable<CI>; precision: NonNullable<CI> })[];
  const undefinedOnes = items.filter((it) => !it.recall || !it.precision);

  const dom = useMemo(() => {
    if (!zoom || pts.length === 0) return { x: [0, 1] as [number, number], y: [0, 1] as [number, number] };
    const pad = (lo: number, hi: number): [number, number] => {
      const p = Math.max(0.02, (hi - lo) * 0.12);
      return [Math.max(0, lo - p), Math.min(1, hi + p)];
    };
    return {
      x: pad(Math.min(...pts.map((p) => p.recall[1])), Math.max(...pts.map((p) => p.recall[2]))),
      y: pad(Math.min(...pts.map((p) => p.precision[1])), Math.max(...pts.map((p) => p.precision[2]))),
    };
  }, [pts, zoom]);

  const X = (v: number) => PL + ((v - dom.x[0]) / (dom.x[1] - dom.x[0] || 1)) * (W - PL - PR);
  const Y = (v: number) => PT + (1 - (v - dom.y[0]) / (dom.y[1] - dom.y[0] || 1)) * (H - PT - PB);
  const xt = niceTicks(dom.x[0], dom.x[1]), yt = niceTicks(dom.y[0], dom.y[1]);

  // label placement: try several offsets; avoid other dots and labels; give up (hover only) when nothing fits
  const labels = useMemo(() => {
    const placed: { x: number; y: number; w: number; h: number }[] = [];
    const dots = pts.map((p) => ({ x: X(p.recall[0]), y: Y(p.precision[0]) }));
    const overlaps = (a: { x: number; y: number; w: number; h: number }) =>
      placed.some((b) => a.x < b.x + b.w + 2 && a.x + a.w + 2 > b.x && a.y < b.y + b.h + 1 && a.y + a.h + 1 > b.y) ||
      dots.some((d) => d.x > a.x - 5 && d.x < a.x + a.w + 5 && d.y > a.y - 5 && d.y < a.y + a.h + 5);
    return pts.map((p, i) => {
      const w = p.name.length * 6.3 + 4, h = 13;
      const { x, y } = dots[i];
      const cands: { x: number; y: number }[] = [
        { x: x + 9, y: y - h / 2 }, { x: x - 9 - w, y: y - h / 2 },
        { x: x - w / 2, y: y - 11 - h }, { x: x - w / 2, y: y + 11 },
        { x: x + 8, y: y - h - 4 }, { x: x + 8, y: y + 4 }, { x: x - 8 - w, y: y - h - 4 }, { x: x - 8 - w, y: y + 4 },
        { x: x + 9, y: y - h / 2 - 22 }, { x: x + 9, y: y - h / 2 + 22 }, { x: x - 9 - w, y: y - h / 2 - 22 }, { x: x - 9 - w, y: y - h / 2 + 22 },
      ];
      const c = cands.find((cc) => cc.x >= PL && cc.x + w <= W - 2 && cc.y >= 0 && !overlaps({ ...cc, w, h }));
      if (!c) return null;
      placed.push({ ...c, w, h });
      return { ...c, w, text: p.name + (p.subset ? " *" : "") };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pts, dom]);

  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: "block", overflow: "visible" }}>
        {/* grid */}
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
        <line x1={PL} x2={W - PR} y1={H - PB} y2={H - PB} stroke="var(--axis)" />
        <line x1={PL} x2={PL} y1={PT} y2={H - PB} stroke="var(--axis)" />
        <text x={(PL + W - PR) / 2} y={H - 10} fontSize={12} textAnchor="middle" fill="var(--ink-2)">{xLabel}</text>
        <text x={14} y={(PT + H - PB) / 2} fontSize={12} textAnchor="middle" fill="var(--ink-2)" transform={`rotate(-90 14 ${(PT + H - PB) / 2})`}>{yLabel}</text>

        {/* CI boxes first so dots sit on top */}
        {pts.map((p) => {
          const x0 = X(p.recall[1]), x1 = X(p.recall[2]), y0 = Y(p.precision[2]), y1 = Y(p.precision[1]);
          return (
            <g key={`b${p.id}`} onMouseMove={(e) => show(e, { title: p.name, color: p.color, ...p.tip })} onMouseLeave={hide}>
              <rect x={x0} y={y0} width={Math.max(1, x1 - x0)} height={Math.max(1, y1 - y0)} fill={p.color} style={{ fillOpacity: "var(--box-alpha)" }} rx={1} />
            </g>
          );
        })}
        {pts.map((p) => {
          const x = X(p.recall[0]), y = Y(p.precision[0]);
          return (
            <g key={`d${p.id}`} onMouseMove={(e) => show(e, { title: p.name, color: p.color, ...p.tip })} onMouseLeave={hide} style={{ cursor: "default" }}>
              <circle cx={x} cy={y} r={8} fill="transparent" />
              <circle cx={x} cy={y} r={3.2} fill={p.color} />
            </g>
          );
        })}
        {labels.map((l, i) =>
          l ? (
            <text key={`l${i}`} x={l.x} y={l.y + 10} fontSize={11} fill="var(--ink)" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 2.5, strokeLinejoin: "round", pointerEvents: "none" }}>
              {l.text}
            </text>
          ) : null,
        )}
        {labels.some((l) => !l) && <text x={W - PR} y={PT - 6} fontSize={10.5} textAnchor="end" fill="var(--ink-4)">some labels hidden where marks overlap; hover to identify</text>}
        {pts.length === 0 && <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={13} fill="var(--ink-4)">{emptyText ?? "Select at least one model."}</text>}
      </svg>
      {undefinedOnes.length > 0 && (
        <div className="legend-note">
          {undefinedOnes.map((u) => (
            <span key={u.id} className="k"><span style={{ width: 9, height: 9, borderRadius: 2, background: u.color, display: "inline-block" }} />{u.name}: flagged nothing, precision undefined</span>
          ))}
        </div>
      )}
      <TipBox tip={tip} />
    </div>
  );
}
