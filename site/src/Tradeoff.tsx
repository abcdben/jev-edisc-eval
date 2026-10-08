import { useMemo, useState } from "react";
import { DATA, PRIMARY_BY_KEY, displayMeta, fmtInt, fmtPct, issueLabel, corpusKey, isDecider, starOf, type DisplayMeta, type Kind, type Level, type Rec } from "./data";
import type { View } from "./App";
import { Control, Hint, Seg, type HintItem } from "./components/ui";
import { HoverProvider, hoverable, useHover } from "./components/hover";
import { Picker, type PickGroup } from "./components/Picker";
import { PRCurves, type CurveSeries } from "./components/PRCurves";
import { Logo } from "./logos";
import { SeriesColorControl, useSeriesColors } from "./seriesColors";
import { DEFAULT_INDEX, DEFAULT_THRESHOLD, THRESHOLDS, curveOf, curvePoint, curvePoints, fmtThreshold, indexForRecall, sweepCell, type Curve } from "./sweep";

/**
 * The Trade-off page: recall against precision, one curve per model swept over the probability threshold (results/sweep.json), with a draggable
 * operating point on each. The published figures on Compare models are each model's own label (p ≥ 0.50); every model here outputs a probability,
 * so any of them can be moved along its own recall/precision trade-off, and the fair comparison is curve against curve. The page keeps one threshold
 * per model (`idx`, a grid index; DEFAULT_INDEX is the 0.50 cut) and shows, per model, the cut, recall, precision, F1 and how much of the corpus it
 * flags at that cut (the review depth). "Match recall" puts every marker at the cheapest cut that reaches a target recall.
 */

/** The models the page offers, in picker order: the Jev configurations Compare models lists, the three OpenAI Decisions forms, Laya's fine-tune, the LLMs. Classical TAR has no probability and no curve. */
export const TRADEOFF_ROSTER = [
  "jev@base", "jev@choice", "jev@score", "jev@decompose", "jev@ensemble", "jev@gate",
  "openai-decisions@predicate", "openai-decisions@choice", "openai-decisions@decompose",
  "laya-ft",
  "claude-haiku-4.5", "claude-sonnet-5", "gpt-5.6-luna", "gpt-5.6-terra", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemma3-12b",
];
export const TRADEOFF_DEFAULT_ON = new Set(["jev@base", "jev@decompose", "openai-decisions@predicate", "claude-sonnet-5", "gpt-5.6-luna"]);

/**
 * Display metadata: the headline roster's own (data.ts), plus Decisions · Facets, a Configurations-page row that Compare models does not list. Jev · Facets
 * keeps its name but takes the Jev family's second colour here: its roster colour (--v1) is Sonnet 5's hex, and both are on by default on this page.
 */
const EXTRA_META: Record<string, DisplayMeta> = {
  "openai-decisions@decompose": { short: "Decisions · Facets", color: "var(--c-laya)", kind: "system1", note: "OpenAI Decisions API (GPT-6 Luna), Facets: each issue is asked as the facets the task file defines for it, each its own predicate; the issue probability is the maximum (logical OR). The Decisions analogue of Jev · Facets." },
};
const COLOR_OVERRIDE: Record<string, string> = { "jev@decompose": "var(--c-jev-2)" };
export const tradeoffMeta = (key: string, rec?: Rec): DisplayMeta => { const m = EXTRA_META[key] ?? displayMeta(key, rec); return COLOR_OVERRIDE[key] ? { ...m, color: COLOR_OVERRIDE[key] } : m; };
const kindOf = (r: Rec): Kind => (EXTRA_META[r.model]?.kind ?? PRIMARY_BY_KEY[r.model]?.kind ?? (r.kind as Kind));
const PICK_ORDER: Kind[] = ["system1", "system1_ft", "llm", "local_llm"];
const KIND_SHORT: Record<string, string> = { system1: "Decision models", system1_ft: "Supervised", llm: "LLM", local_llm: "Local LLM" };

/** The roster's records on the view's corpus and arm that have a sweep curve (so a marker can move), in roster order. */
export function useTradeoffRows(v: View): Rec[] {
  return useMemo(() => {
    const rows = DATA.records.filter((r) => r.corpus === v.corpus && r.tag === v.tag && r.arm === v.arm);
    return TRADEOFF_ROSTER.map((k) => rows.find((r) => r.model === k)).filter((r): r is Rec => !!r && !!sweepCell(r.corpus, r.tag, r.arm, r.model));
  }, [v.corpus, v.tag, v.arm]);
}

/** The model multi-select for the Trade-off page, in the control bar: the roster grouped by kind, as Compare models' picker is. */
export function TradeoffPicker({ v, on, setOn, explain }: { v: View; on: Set<string>; setOn: (s: Set<string>) => void; explain?: (k: string) => void }) {
  const rows = useTradeoffRows(v);
  const { colorOf, setColor } = useSeriesColors();
  const byKind = PICK_ORDER.map((k) => ({ kind: k, recs: rows.filter((r) => kindOf(r) === k) })).filter((g) => g.recs.length);
  const groups: PickGroup[] = byKind.map((g) => ({
    id: g.kind, label: KIND_SHORT[g.kind],
    items: g.recs.map((r) => {
      const m = tradeoffMeta(r.model, r);
      return { id: r.model, label: m.short, title: m.note, mark: <span style={{ color: m.color }}><Logo model={r.model} /></span>, suffix: starOf(r) ? <span className="sub" title={`scored on ${r.subset}`}>*</span> : undefined, detail: explain ? () => explain(r.model) : undefined, accent: isDecider(kindOf(r)) ? m.color : undefined };
    }),
  }));
  const selected = rows.filter((r) => on.has(r.model));
  return <Picker label="Models" summary={`${selected.length} of ${rows.length}`} groups={groups} on={on} onChange={setOn} onReset={() => setOn(new Set(TRADEOFF_DEFAULT_ON))}
    selected={selected.length ? <><span className="pick-selected-lab">Selected</span><div className="series-selected">
      {selected.map((r) => {
        const meta = tradeoffMeta(r.model, r);
        return <div className="series-selected-row" key={r.model}><SeriesColorControl id={r.model} color={colorOf(r.model, meta.color)} onColor={setColor} label={meta.short} /><span>{meta.short}</span><button type="button" onClick={() => { const next = new Set(on); next.delete(r.model); setOn(next); }} aria-label={`Remove ${meta.short}`}>×</button></div>;
      })}
    </div></> : undefined} />;
}

const ABOUT: HintItem[] = [
  { k: "Curve", v: <>Each model's saved per-decision probabilities re-cut at <b>p(responsive) ≥ t</b> for t = {fmtThreshold(THRESHOLDS[0])} … {fmtThreshold(THRESHOLDS[THRESHOLDS.length - 1])} in steps of {fmtThreshold(THRESHOLDS[1] - THRESHOLDS[0])} (results/sweep.json). Document level: a document is flagged when any issue clears t, and is relevant when any issue is.</> },
  { k: "Published", v: <>The open ring is the {fmtThreshold(DEFAULT_THRESHOLD)} cut. For Jev, Decisions and Laya that is the figure on Compare models (their label is p ≥ {fmtThreshold(DEFAULT_THRESHOLD)}); an LLM's returned label can disagree with its own probability on a small share of decisions, so its ring can sit a little off its Compare models point. The filled marker is the operating point you set.</> },
  { k: "Flagged", v: <>How many documents (or decisions) the cut sends to review, and the share of the corpus: the depth of the ranked list a reviewer would read.</> },
  { k: "Iso-F1", v: <>The dashed lines join points of equal F1; moving along a curve towards one is a gain in F1 whatever it costs in recall or precision.</> },
];

/** The signed change in percentage points, "+12.6" / "−6.2"; "0.0" within rounding. */
const signedPts = (d: number) => (Math.abs(d) < 0.0005 ? "0.0" : `${d > 0 ? "+" : "\u2212"}${(Math.abs(d) * 100).toFixed(1)}`);

export function TradeoffSection({ v, on, explain }: { v: View; on: Set<string>; explain: (k: string) => void }) {
  const rows = useTradeoffRows(v);
  const { colors, colorOf, setColor } = useSeriesColors();
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];
  // the page's own scope: documents (the main page's level) or every decision pooled; an issue chosen in the control bar is its decision-level curve
  const [level, setLevel] = useState<Level>("doc");
  const unit = v.issue || level === "decision" ? "decisions" : "documents";
  const [zoom, setZoom] = useState(true);
  // one operating point per model, as a grid index; absent means the published cut
  const [idx, setIdx] = useState<Record<string, number>>({});
  const setOne = (id: string, i: number) => setIdx((p) => (p[id] === i ? p : { ...p, [id]: i }));
  const [target, setTarget] = useState("90");
  const [matched, setMatched] = useState<{ target: number; n: number; short: string[] } | null>(null);

  const curves = useMemo(() => rows.filter((r) => on.has(r.model)).map((r) => { const cell = sweepCell(r.corpus, r.tag, r.arm, r.model); return { r, curve: cell ? curveOf(cell, { level, gray: v.gray, issue: v.issue }) : undefined }; }).filter((x): x is { r: Rec; curve: Curve } => !!x.curve), [rows, on, v.gray, v.issue, level]);
  const series: CurveSeries[] = useMemo(() => curves.map(({ r, curve }) => {
    const m = tradeoffMeta(r.model, r);
    return { id: r.model, name: m.short, color: colors[r.model] ?? m.color, pts: curvePoints(curve), ti: idx[r.model] ?? DEFAULT_INDEX, pubI: DEFAULT_INDEX, subset: starOf(r) };
  }), [curves, colors, idx]);
  const moved = series.filter((s) => s.ti !== s.pubI).length;

  const reset = () => { setIdx({}); setMatched(null); };
  const match = () => {
    const t = Number(target) / 100;
    if (!Number.isFinite(t) || t <= 0 || t > 1) return;
    const next: Record<string, number> = { ...idx }, short: string[] = [];
    for (const { r, curve } of curves) { const m = indexForRecall(curve, t); next[r.model] = m.i; if (!m.reached) short.push(tradeoffMeta(r.model, r).short); }
    setIdx(next);
    setMatched({ target: t, n: curves.length - short.length, short });
  };

  const scope = v.issue ? issueLabel(meta, v.issue) : level === "doc" ? "document level" : "every decision";
  const lede = `Every model here outputs a probability; the operating point is a choice. The published figures (Compare models) are each model's own label, p ≥ ${fmtThreshold(DEFAULT_THRESHOLD)}, the open ring on each curve. Drag a marker along its curve, or set a recall to match, to re-cut that model.`;

  return (
    <section className="section">
      <div className="stats-row" role="group" aria-label="Operating points">
        <span className="stats-row-lab">Operating point</span>
        <Control label="Scope">
          {v.issue
            ? <span className="studio-hint small">{issueLabel(meta, v.issue)}: decisions on that issue (choose Relevance in the Issue control for document level)</span>
            : <Seg<Level> value={level} onChange={setLevel} options={[{ id: "doc", label: "documents", title: "A document is flagged when any issue clears the threshold; relevant when any issue is relevant" }, { id: "decision", label: "decisions", title: "Every document × issue decision pooled" }]} />}
        </Control>
        <Control label="Match recall">
          <label className="studio-slider" title="Move every marker to the highest threshold whose recall still reaches this target: the cheapest cut that gets there">
            <input type="number" min={1} max={100} step={1} value={target} onChange={(e) => setTarget(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") match(); }} aria-label="target recall, percent" className="tradeoff-target" />
            <span>%</span>
          </label>
          <button type="button" className="studio-btn small" onClick={match} disabled={!series.length}>match</button>
          <span className="studio-hint small">
            {matched ? `${matched.n} of ${matched.n + matched.short.length} reach ${fmtPct(matched.target, 0)}${matched.short.length ? `; ${matched.short.join(", ")} cannot at any cut` : ""}` : "every marker to the cut that reaches this recall"}
          </span>
        </Control>
        <Control label="Reset">
          <button type="button" className="studio-btn small" onClick={reset} disabled={!moved} title={`Every marker back to ${fmtThreshold(DEFAULT_THRESHOLD)}, the published operating point`}>all to {fmtThreshold(DEFAULT_THRESHOLD)}</button>
          <span className="studio-hint small">{moved ? `${moved} of ${series.length} moved off ${fmtThreshold(DEFAULT_THRESHOLD)}` : `all at ${fmtThreshold(DEFAULT_THRESHOLD)}, the published figures`}</span>
        </Control>
      </div>
      <HoverProvider>
        <div className="dash ranked">
          <CurveCard series={series} setOne={setOne} zoom={zoom} setZoom={setZoom} unit={unit} lede={lede} scope={scope} />
          <ReadoutCard series={series} curves={curves} setOne={setOne} unit={unit} explain={explain} colorOf={colorOf} setColor={setColor} />
        </div>
      </HoverProvider>
    </section>
  );
}

function CurveCard({ series, setOne, zoom, setZoom, unit, lede, scope }: { series: CurveSeries[]; setOne: (id: string, i: number) => void; zoom: boolean; setZoom: (z: boolean) => void; unit: string; lede: string; scope: string }) {
  const hover = useHover();
  return (
    <div className="card fill">
      <div className="card-t">
        <h3>Recall against precision, swept over the threshold</h3><span className="unit">{scope}</span>
        <span className="right">
          <Seg value={zoom ? "zoom" : "full"} onChange={(z) => setZoom(z === "zoom")} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }]} />
          <Hint items={ABOUT} title="Trade-off" />
        </span>
      </div>
      <p className="tradeoff-lede">{lede}</p>
      <div className="chart-fill" style={{ minHeight: 460 }}>
        <PRCurves series={series} onIndex={setOne} zoom={zoom} fill highlight={hover.id} onHover={hover.set} unit={unit} emptyText="Select at least one model." />
      </div>
      <div className="legend-note">
        <span>Filled marker: the operating point (drag it, or focus it and use the arrow keys). Open ring: the published point, p ≥ {fmtThreshold(DEFAULT_THRESHOLD)}. Dashed: equal F1.</span>
        {series.some((s) => s.subset) && <span>* scored on a stratified subset</span>}
      </div>
    </div>
  );
}

/** The readout: one row per model at its operating point, with a slider for the cut and the change against the published point. */
function ReadoutCard({ series, curves, setOne, unit, explain, colorOf, setColor }: { series: CurveSeries[]; curves: { r: Rec; curve: Curve }[]; setOne: (id: string, i: number) => void; unit: string; explain: (k: string) => void; colorOf: (id: string, fallback: string) => string; setColor: (id: string, c: string) => void }) {
  const hover = useHover();
  const n = THRESHOLDS.length;
  return (
    <div className="card">
      <div className="card-t">
        <h3>At the operating point</h3><span className="unit">per model: the cut, what it finds, and how much it sends to review</span>
      </div>
      {series.length === 0 ? <div className="tradeoff-empty">Select at least one model.</div> : (
        <div className="tradeoff-wrap"><table className="tradeoff-table">
          <thead>
            <tr><th>Model</th><th>Threshold</th><th className="num">Recall</th><th className="num">Precision</th><th className="num">F1</th><th className="num">Flagged</th><th className="num">Review share</th><th className="num" title="Change against the published point, in percentage points: recall / precision">vs published</th></tr>
          </thead>
          <tbody>
            {series.map((s) => {
              const curve = curves.find((c) => c.r.model === s.id)!.curve;
              const p = curvePoint(curve, s.ti), pub = curvePoint(curve, s.pubI);
              const movedRow = s.ti !== s.pubI;
              const cls = `${hover.id === s.id ? "hl" : ""}${movedRow ? " moved" : ""}`;
              return (
                <tr key={s.id} className={cls} {...hoverable(hover.set, s.id)}>
                  <th scope="row">
                    <span className="tradeoff-name">
                      <SeriesColorControl id={s.id} color={colorOf(s.id, s.color)} onColor={setColor} label={s.name} />
                      <button type="button" className="tradeoff-link" onClick={() => explain(s.id)} title="Details">{s.name}{s.subset ? " *" : ""}</button>
                    </span>
                  </th>
                  <td>
                    <label className="studio-slider">
                      <span>p ≥</span>
                      {/* the slider runs the grid backwards so right is more recall, as on the chart */}
                      <input type="range" min={0} max={n - 1} step={1} value={n - 1 - s.ti} onChange={(e) => setOne(s.id, n - 1 - Number(e.target.value))} aria-label={`${s.name} threshold`} />
                      <span className="val">{fmtThreshold(p.t)}</span>
                    </label>
                  </td>
                  <td className="num">{fmtPct(p.recall)}</td>
                  <td className="num">{p.precision == null ? "—" : fmtPct(p.precision)}</td>
                  <td className="num">{p.f1 == null ? "—" : fmtPct(p.f1)}</td>
                  <td className="num">{fmtInt(p.flagged)} <span className="dim">of {fmtInt(p.n)}</span></td>
                  <td className="num">{fmtPct(p.share)}</td>
                  <td className="num delta">{movedRow ? <><span>{signedPts(p.recall - pub.recall)}</span> / <span>{p.precision == null || pub.precision == null ? "—" : signedPts(p.precision - pub.precision)}</span> <span className="dim">pts</span></> : <span className="dim">published</span>}</td>
                </tr>
              );
            })}
          </tbody>
        </table></div>
      )}
      <div className="legend-note"><span>Flagged: {unit} with p ≥ the cut; review share is that as a fraction of all {unit} scored. vs published: recall / precision change in points against the {fmtThreshold(DEFAULT_THRESHOLD)} cut.</span></div>
    </div>
  );
}
