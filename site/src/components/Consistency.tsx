import { DATA, fmtCI, fmtInt, fmtPct, type DetCell, type Rec } from "../data";
import { Hint, TipBox, useTip, useWidth, type TipLine } from "./ui";

const LABEL_W = 170, ROW = 24;
const ISSUE_SHORT: Record<string, string> = {
  som_broad: "SOM broad", som_narrow: "SOM narrow", mktg_broad: "Marketing broad", mktg_narrow: "Marketing narrow",
  data_broad: "Data broad", data_narrow: "Data narrow", dea_broad: "DEA broad", dea_narrow: "DEA narrow",
};

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
    ["Runs", `${c.k} (${c.runs.join(", ")})`],
    ["Decisions compared", `${fmtInt(c.n_decisions)} on ${fmtInt(c.n_docs)} docs`],
    ["Pairwise disagreement", fmtCI(c.pairwise, 2)],
    ["Decisions that flipped in any run", fmtCI(c.decision_flip, 2)],
    ["  reweighted to corpus mix", fmtPct(c.decision_flip_weighted, 2)],
  ];
  if (c.doc_flip) lines.push(["Documents whose any-issue call flipped", fmtCI(c.doc_flip, 2)]);
  lines.push(["Confident flips (p swung past 0.3 and 0.7)", fmtCI(c.confident_flip, 2)]);
  lines.push(["Probability byte-identical across runs", fmtCI(c.identical_prob, 1)]);
  lines.push(["Probability spread, median / p95", `${c.prob_spread_median.toFixed(3)} / ${c.prob_spread_p95.toFixed(3)}`]);
  if (c.recall_range) lines.push(["Recall across runs", `${fmtPct(c.recall_range[0])} – ${fmtPct(c.recall_range[1])}`]);
  if (c.precision_range) lines.push(["Precision across runs", `${fmtPct(c.precision_range[0])} – ${fmtPct(c.precision_range[1])}`]);
  if (c.majority.recall != null) lines.push(["Majority vote of runs, recall / precision", `${fmtPct(c.majority.recall)} / ${fmtPct(c.majority.precision)}`]);
  const strat = Object.entries(c.by_stratum).filter(([, s]) => s.n > 0).map(([k, s]) => `${k} ${fmtPct(s.flip?.[0] ?? null, 1)}`).join(" · ");
  const gold = Object.entries(c.by_gold).filter(([, s]) => s.n > 0).map(([k, s]) => `${k} ${fmtPct(s.flip?.[0] ?? null, 1)}`).join(" · ");
  const issues = Object.entries(c.by_issue).map(([k, s]) => `${ISSUE_SHORT[k] ?? k} ${fmtPct(s.flip?.[0] ?? null, 1)}`).join(" · ");
  return {
    lines,
    notes: [
      `Flip rate by document stratum: ${strat}.`,
      `By gold label of the decision: ${gold}.`,
      `By issue: ${issues}.`,
      c.setting === "t0" ? `${name} at temperature 0.` : `${name} at the settings the benchmark ran under.`,
    ],
  };
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
  const h = sorted.length * ROW + 26;
  const hasT0 = sorted.some((x) => x.t0);
  const anyT0Refused = sorted.some((x) => x.d && !x.t0 && x.r.kind === "llm");
  return (
    <div className="card" style={{ marginTop: 20 }}>
      <div className="card-t">
        <h3>Consistency</h3>
        <span className="unit">
          run-to-run disagreement on the same documents · {det ? `${fmtInt(det.sample.n_docs)} Mallinckrodt emails` : "not measured"}{arm === "single" ? ", two narrow issues, one issue per call" : ", all eight issues per call"}
        </span>
        <span className="right">
          <Hint left text="Each model scored the same fixed sample of 300 Mallinckrodt emails five times under identical settings (100 emails with a debatable gold label, 100 clear positives, 100 clear negatives; the benchmark run counts as the first repeat). The bar is pairwise disagreement: the probability that two independent runs give a different label for the same (document, issue) decision. The whisker is a 95% bootstrap interval over decisions. Lighter bars are the same models at temperature 0 where the API accepts it; Anthropic rejects sampling parameters on Sonnet 5, so it has no zero arm. Jev and Laya expose no sampling controls, so their bars are intrinsic behavior. Hover for flip rates by stratum, issue and gold label, and for how much recall moved between runs." />
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
                  <text x={LABEL_W - 10} y={y + ROW / 2 + 4} textAnchor="end" fontSize={12} fill="var(--ink-4)">{nm}</text>
                  <text x={LABEL_W + 7} y={y + ROW / 2 + 4} fontSize={11} fill="var(--ink-4)">not measured</text>
                </g>
              );
            }
            const bars = [{ c: x.d, op: 1, dy: x.t0 ? -4.5 : 0, bh: x.t0 ? 7 : 12 }, ...(x.t0 ? [{ c: x.t0, op: 0.45, dy: 4.5, bh: 7 }] : [])];
            return (
              <g key={x.r.model}>
                <text x={LABEL_W - 10} y={y + ROW / 2 + 4} textAnchor="end" fontSize={12} fill="var(--ink-2)">{nm}</text>
                {bars.map((b, j) => {
                  const v = b.c.pairwise[0], lo = b.c.pairwise[1], hi = b.c.pairwise[2];
                  const cy = y + ROW / 2 + b.dy;
                  return (
                    <g key={j} onMouseMove={(e) => show(e, { title: `${nm}${b.c.setting === "t0" ? " · temperature 0" : ""}`, color: c, ...tipFor(b.c, nm) })} onMouseLeave={hide} style={{ cursor: "default" }}>
                      <rect x={LABEL_W - 4} y={cy - b.bh / 2 - 2} width={W - LABEL_W + 4} height={b.bh + 4} fill="transparent" />
                      <rect x={LABEL_W} y={cy - b.bh / 2} width={Math.max(1.5, X(v) - LABEL_W)} height={b.bh} fill={c} opacity={b.op} rx={2} />
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
          <text x={LABEL_W} y={sorted.length * ROW + 17} fontSize={10.5} fill="var(--ink-3)">probability two runs disagree on a decision · {measured[0]?.d?.k ?? 5} runs each</text>
        </svg>
        <TipBox tip={tip} />
      </div>
      <div className="legend-note">
        {hasT0 && <span>lighter bar: temperature 0</span>}
        {anyT0Refused && <span>Sonnet 5: the API rejects sampling parameters, no zero arm</span>}
        <span>measured on Mallinckrodt only; shown for every corpus since it is a property of the model, not the documents</span>
      </div>
    </div>
  );
}
