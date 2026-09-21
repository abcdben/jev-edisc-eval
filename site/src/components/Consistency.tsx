import { DATA, fmtCI, fmtInt, fmtPct, type DetCell, type Rec } from "../data";
import { LogoGlyph } from "../logos";
import { Hint, TipBox, useTip, useWidth, type TipLine } from "./ui";

const LABEL_W = 168, ROW = 24;

/** The determinism cell for a record: matched on model key, arm follows the page. Ablation variants are not covered. */
export function detFor(r: Rec, arm: "multi" | "single", setting: "default" | "t0"): DetCell | null {
  const det = DATA.determinism;
  if (!det) return null;
  const key = r.model === "laya-ft" ? null : r.model_key;
  if (!key) return null;
  return det.cells.find((c) => c.model === key && c.arm === arm && c.setting === setting) ?? null;
}

function tipFor(c: DetCell, name: string): { lines: TipLine[]; notes: string[] } {
  const lines: TipLine[] = [
    ["Runs", String(c.k)],
    ["Decisions compared", fmtInt(c.n_decisions)],
    ["Pairwise disagreement", fmtCI(c.pairwise, 2)],
    ["Decisions that flipped", fmtCI(c.decision_flip, 2)],
  ];
  if (c.recall_range) lines.push(["Recall across runs", `${fmtPct(c.recall_range[0])} – ${fmtPct(c.recall_range[1])}`]);
  if (c.precision_range) lines.push(["Precision across runs", `${fmtPct(c.precision_range[0])} – ${fmtPct(c.precision_range[1])}`]);
  return { lines, notes: c.setting === "t0" ? [`${name} at temperature 0.`] : [] };
}

export function Consistency({ recs, colorOf, nameOf, arm }: { recs: Rec[]; colorOf: (r: Rec) => string; nameOf: (r: Rec) => string; arm: "multi" | "single" }) {
  const { tip, show, hide, hostRef } = useTip();
  const W = useWidth(hostRef, 760);
  const det = DATA.determinism;
  const rows = recs.map((r) => ({ r, d: detFor(r, arm, "default"), t0: detFor(r, arm, "t0") }));
  const measured = rows.filter((x) => x.d);
  const sorted = [...rows].sort((a, b) => (a.d?.pairwise[0] ?? Infinity) - (b.d?.pairwise[0] ?? Infinity));
  const max = Math.max(0.01, ...measured.flatMap((x) => [x.d!.pairwise[2], x.t0?.pairwise[2] ?? 0]));
  const plotW = Math.max(120, W - LABEL_W - 130);
  const X = (v: number) => LABEL_W + (v / max) * plotW;
  const h = sorted.length * ROW + 24;
  const hasT0 = sorted.some((x) => x.t0);
  return (
    <div className="card">
      <div className="card-t">
        <h3>Determinism</h3>
        <span className="unit">run-to-run disagreement · {det ? `${fmtInt(det.sample.n_docs)} Mallinckrodt emails` : "not measured"} · {measured[0]?.d?.k ?? 5} runs</span>
        <span className="right">
          <Hint left text="Measured on Mallinckrodt only and shown for every corpus, since it is a property of the model rather than the documents. Each model scored the same fixed sample of 300 Mallinckrodt emails five times under identical settings (100 emails with a debatable gold label, 100 clear positives, 100 clear negatives; the benchmark run counts as the first repeat). The bar is pairwise disagreement: the probability that two independent runs give a different label for the same (document, issue) decision. The whisker is a 95% bootstrap interval over decisions. Lighter bars are the same models at temperature 0 where the API accepts it; Anthropic rejects sampling parameters on Sonnet 5, so it has no temperature-0 bar. Jev and Laya expose no sampling controls, so their bars are intrinsic behavior. Hover for flip rates by stratum, issue and gold label, and for how much recall moved between runs." />
        </span>
      </div>
      <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
          {sorted.map((x, i) => {
            const y = i * ROW;
            const c = colorOf(x.r), nm = nameOf(x.r);
            if (!x.d) {
              return (
                <g key={x.r.model}>
                  <g color="var(--ink-4)"><LogoGlyph model={x.r.model} cx={8} cy={y + ROW / 2} opacity={0.5} /></g>
                  <text x={22} y={y + ROW / 2 + 4} fontSize={12} fill="var(--ink-4)">{nm}</text>
                  <text x={LABEL_W + 7} y={y + ROW / 2 + 4} fontSize={11} fill="var(--ink-4)">not measured</text>
                </g>
              );
            }
            const bars = [{ c: x.d, op: 1, dy: x.t0 ? -4 : 0, bh: x.t0 ? 6 : 10 }, ...(x.t0 ? [{ c: x.t0, op: 0.45, dy: 4, bh: 6 }] : [])];
            return (
              <g key={x.r.model}>
                <g color="var(--ink-2)"><LogoGlyph model={x.r.model} cx={8} cy={y + ROW / 2} /></g>
                <text x={22} y={y + ROW / 2 + 4} fontSize={12} fill="var(--ink-2)">{nm}</text>
                {bars.map((b, j) => {
                  const v = b.c.pairwise[0], lo = b.c.pairwise[1], hi = b.c.pairwise[2];
                  const cy = y + ROW / 2 + b.dy;
                  return (
                    <g key={j} onMouseMove={(e) => show(e, { title: `${nm}${b.c.setting === "t0" ? " · temperature 0" : ""}`, color: c, ...tipFor(b.c, nm) })} onMouseLeave={hide} style={{ cursor: "default" }}>
                      <rect x={LABEL_W - 4} y={cy - b.bh / 2 - 2} width={W - LABEL_W + 4} height={b.bh + 4} fill="transparent" />
                      <rect x={LABEL_W} y={cy - b.bh / 2} width={Math.max(1.5, X(v) - LABEL_W)} height={b.bh} fill={c} rx={1.5} style={{ fillOpacity: `calc(var(--bar-alpha) * ${b.op})` }} />
                      <line x1={X(lo)} x2={X(hi)} y1={cy} y2={cy} stroke="var(--ink)" strokeWidth={1} opacity={0.6} />
                      <text x={X(hi) + 7} y={cy + 4} fontSize={11} fill={b.op < 1 ? "var(--ink-3)" : "var(--ink)"} className="mono">
                        {v === 0 ? "0" : fmtPct(v, v < 0.001 ? 2 : 1)}{b.c.setting === "t0" ? "  t=0" : ""}
                      </text>
                    </g>
                  );
                })}
              </g>
            );
          })}
          <line x1={LABEL_W} x2={LABEL_W} y1={0} y2={sorted.length * ROW} stroke="var(--axis)" />
          <text x={LABEL_W} y={sorted.length * ROW + 17} fontSize={10.5} fill="var(--ink-3)">probability two runs disagree{hasT0 ? " · lighter bar: temperature 0" : ""}</text>
        </svg>
        <TipBox tip={tip} />
      </div>
    </div>
  );
}
