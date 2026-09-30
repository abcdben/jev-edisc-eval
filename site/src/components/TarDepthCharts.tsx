import { useMemo, useState } from "react";
import { fmtInt, fmtPct, type Rec } from "../data";
import { linTicks } from "./ticks";
import { Seg, TipBox, useTip, useWidth } from "./ui";
import { SeriesColorControl, useSeriesColors } from "../seriesColors";

type Sampling = "random" | "diversity";
type Metric = "f1" | "recall" | "precision";
type Alignment = 60 | 70 | 80 | 90 | 100;
type Point = { id: string; depth: number; value: number; row: Rec };
type Series = { alignment: Alignment; label: string; color: string; points: Point[] };
type Domain = { maxDepth: number; y: [number, number] };

const METRICS: { id: Metric; label: string }[] = [
  { id: "f1", label: "F1" },
  { id: "recall", label: "Recall" },
  { id: "precision", label: "Precision" },
];
const metricLabel = (metric: Metric) => METRICS.find((x) => x.id === metric)!.label;
const metricValue = (row: Rec, metric: Metric) => metric === "f1" ? row.all.doc.f1 : row.all.doc[metric]?.[0] ?? null;

const ALIGNMENTS: { alignment: Alignment; label: string; color: string }[] = [
  { alignment: 60, label: "60%", color: "var(--v1)" },
  { alignment: 70, label: "70%", color: "var(--v9)" },
  { alignment: 80, label: "80%", color: "var(--v3)" },
  { alignment: 90, label: "90%", color: "var(--v14)" },
  { alignment: 100, label: "Perfect", color: "var(--v7)" },
];

const variantParts = (variant: string): { depth: number; sampling: Sampling; alignment: Alignment } | null => {
  const m = /^t1_(\d+)(?:_acc(60|70|80|90))?(_div)?$/.exec(variant);
  if (!m) return null;
  return { depth: Number(m[1]), alignment: (m[2] ? Number(m[2]) : 100) as Alignment, sampling: m[3] ? "diversity" : "random" };
};

function seriesFor(rows: Rec[], sampling: Sampling, metric: Metric): Series[] {
  const points = rows.flatMap((row): (Point & { alignment: Alignment })[] => {
    const p = variantParts(row.variant ?? "");
    const depth = row.tar?.docs_reviewed;
    const value = metricValue(row, metric);
    return p && p.sampling === sampling && depth != null && value != null
      ? [{ id: row.model, depth, value, row, alignment: p.alignment }]
      : [];
  });
  return ALIGNMENTS.map((s) => ({
    ...s,
    points: points.filter((p) => p.alignment === s.alignment).sort((a, b) => a.depth - b.depth),
  })).filter((s) => s.points.length);
}

const niceMetricTicks = (lo: number, hi: number) => {
  const span = hi - lo;
  const step = span > 0.35 ? 0.1 : span > 0.18 ? 0.05 : span > 0.08 ? 0.02 : 0.01;
  const out: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(Math.round(t * 1000) / 1000);
  return out;
};

function TarDepthChart({ rows, sampling, metric, domain }: { rows: Rec[]; sampling: Sampling; metric: Metric; domain: Domain }) {
  const { tip, show, hide, hostRef } = useTip();
  const { colorOf, setColor } = useSeriesColors();
  const W = useWidth(hostRef, 620), H = W < 480 ? 310 : 340;
  const PL = W < 480 ? 48 : 56, PR = 18, PT = 18, PB = 50;
  const series = useMemo(() => seriesFor(rows, sampling, metric), [rows, sampling, metric]);
  const all = series.flatMap((s) => s.points);
  if (!all.length) return <div className="tar-depth-empty">No reviewer-alignment sweep is available for this corpus.</div>;

  const maxX = domain.maxDepth, [y0, y1] = domain.y;
  const X = (v: number) => PL + (v / maxX) * (W - PL - PR);
  const Y = (v: number) => PT + (1 - (v - y0) / (y1 - y0 || 1)) * (H - PT - PB);
  const xt = linTicks(0, maxX, W < 480 ? 3 : 5), yt = niceMetricTicks(y0, y1);
  const path = (pts: Point[]) => pts.map((p, i) => `${i ? "L" : "M"}${X(p.depth).toFixed(1)} ${Y(p.value).toFixed(1)}`).join("");
  const label = metricLabel(metric);

  return (
    <div ref={hostRef} data-tip-host className="tar-depth-chart">
      <div className="tar-depth-key" aria-label="Relevant-document coding accuracy legend">
        {series.map((s) => {
          const id = `tar-depth:${sampling}:${s.alignment}`, color = colorOf(id, s.color);
          return <span key={s.alignment}><SeriesColorControl id={id} color={color} onColor={setColor} label={`${s.label} relevant-document coding accuracy`} />{s.label}</span>;
        })}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} role="img" aria-label={`${sampling === "random" ? "Random" : "Diversity"} sampling: actual review depth against document-level ${label}`}>
        <title>{sampling === "random" ? "Random" : "Diversity"} sampling review depth versus {label}</title>
        {xt.map((t) => <g key={`x${t}`}><line x1={X(t)} x2={X(t)} y1={PT} y2={H - PB} stroke="var(--grid)" /><text x={X(t)} y={H - PB + 17} textAnchor="middle" fontSize={10.5} fill="var(--ink-3)" className="mono">{t >= 1000 ? `${t / 1000}k` : t}</text></g>)}
        {yt.map((t) => <g key={`y${t}`}><line x1={PL} x2={W - PR} y1={Y(t)} y2={Y(t)} stroke="var(--grid)" /><text x={PL - 8} y={Y(t) + 3.5} textAnchor="end" fontSize={10.5} fill="var(--ink-3)" className="mono">{Math.round(t * 100)}%</text></g>)}
        <g stroke="var(--axis)"><line x1={PL} x2={W - PR} y1={H - PB} y2={H - PB} /><line x1={PL} x2={PL} y1={PT} y2={H - PB} /></g>
        <text x={(PL + W - PR) / 2} y={H - 10} textAnchor="middle" fontSize={12} fill="var(--ink-2)">Actual documents reviewed</text>
        <text x={14} y={(PT + H - PB) / 2} textAnchor="middle" fontSize={12} fill="var(--ink-2)" transform={`rotate(-90 14 ${(PT + H - PB) / 2})`}>Document-level {label}</text>
        {series.map((s) => (
          <g key={s.alignment}>
            <path d={path(s.points)} fill="none" stroke={colorOf(`tar-depth:${sampling}:${s.alignment}`, s.color)} strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
            {s.points.map((p) => (
              <g key={p.id} tabIndex={0} style={{ outline: "none" }}
                onMouseMove={(e) => show(e, { kind: "mark", x: X(p.depth), y: Y(p.value), r: 6 }, {
                  title: `${s.label} relevant-document coding accuracy`, color: colorOf(p.id, colorOf(`tar-depth:${sampling}:${s.alignment}`, s.color)),
                  lines: [
                    ["Actual review depth", fmtInt(p.depth)],
                    ["Document-level recall", fmtPct(p.row.all.doc.recall?.[0])],
                    ["Document-level precision", fmtPct(p.row.all.doc.precision?.[0])],
                    ["Document-level F1", fmtPct(p.row.all.doc.f1)],
                    ["Sampling", sampling === "random" ? "Random" : "Diversity"],
                  ],
                  sub: s.alignment === 100 ? "Perfect reviewer coding." : `Non-relevant false-positive rate: ${(100 - s.alignment) / 5}% (one-fifth of the miss rate).`,
                })} onMouseLeave={hide}>
                <title>{`${s.label} relevant-document coding accuracy, ${fmtInt(p.depth)} reviewed, document-level ${label} ${fmtPct(p.value)}`}</title>
                <circle cx={X(p.depth)} cy={Y(p.value)} r={4.2} fill="var(--panel)" stroke={colorOf(p.id, colorOf(`tar-depth:${sampling}:${s.alignment}`, s.color))} strokeWidth={2} />
                <circle cx={X(p.depth)} cy={Y(p.value)} r={9} fill="transparent" />
              </g>
            ))}
          </g>
        ))}
      </svg>
      <TipBox tip={tip} />
    </div>
  );
}

export function TarDepthCharts({ rows }: { rows: Rec[] }) {
  const [metric, setMetric] = useState<Metric>("f1");
  const domain = useMemo<Domain>(() => {
    const eligible = rows.flatMap((row) => variantParts(row.variant ?? "") && row.tar?.docs_reviewed != null && metricValue(row, metric) != null ? [row] : []);
    const values = eligible.map((row) => metricValue(row, metric)!);
    const rawLo = Math.min(...values), rawHi = Math.max(...values), pad = Math.max(0.025, (rawHi - rawLo) * 0.14);
    return {
      maxDepth: Math.max(1, ...eligible.map((row) => row.tar!.docs_reviewed)),
      y: [Math.max(0, Math.floor((rawLo - pad) * 20) / 20), Math.min(1, Math.ceil((rawHi + pad) * 20) / 20)],
    };
  }, [rows, metric]);
  return (
    <div className="tar-depth-grid">
      <div className="tar-depth-head">
        <div><h2>Review depth performance</h2><span>Median-seed TAR 1.0 · document-level relevance</span></div>
        <div className="tar-depth-metric"><span>Metric</span><Seg value={metric} onChange={setMetric} options={METRICS} /></div>
      </div>
      {(["random", "diversity"] as Sampling[]).map((sampling) => (
        <div className="card tar-depth-card" key={sampling}>
          <div className="card-t"><h3>{sampling === "random" ? "Random sampling" : "Diversity sampling"}</h3><span className="unit">review depth vs {metricLabel(metric)}</span></div>
          <TarDepthChart rows={rows} sampling={sampling} metric={metric} domain={domain} />
        </div>
      ))}
      <p className="tar-depth-note">Lines are reviewer <b>relevant-document coding accuracy</b>, not overall reviewer agreement. For imperfect reviewers, the false-positive rate on non-relevant documents is one-fifth of the relevant-document miss rate. Each point is the median-seed TAR 1.0 result; x is the actual number coded.</p>
    </div>
  );
}
