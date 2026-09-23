import { useEffect, useMemo, useState } from "react";
import {
  ABLATION_GROUPS, CORPORA, DATA, DEFAULT_CORPUS, DEFAULT_ON, GPU_NAME, GPU_USD_PER_HOUR, PRIMARY, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER,
  corpusKey, costPerDoc, fmtCI, fmtInt, fmtMs, fmtPct, fmtUSD, isDecider, isGpuRow, isHidden, issueLabel, pick, siteCorpus, starOf, variantColor,
  type Gray, type Kind, type Level, type PRF, type Rec,
} from "./data";
import { Control, Hint, MethodContext, ROW_PULSE_MS, Seg, usePulseWindow, type HintItem, type TipLine } from "./components/ui";
import { PRScatter, type PRItem } from "./components/PRScatter";
import { PRRail } from "./components/PRRail";
import { PRHeat } from "./components/PRHeat";
import { OpsBars, type BarItem } from "./components/OpsBars";
import { Consistency, detFor, detLines } from "./components/Consistency";
import { HoverProvider, useHover } from "./components/hover";
import { ExplainModal, type MetricSection, type Metrics } from "./components/Explain";
import { Picker, type PickGroup } from "./components/Picker";
import { DisclaimerLink, DisclaimerModal, useDisclaimer } from "./components/Disclaimer";
import { Logo } from "./logos";

/** The recall/precision card's views. `ranked` is drawn by PRRail on Compare models (rank rail) and by PRHeat on Compare configurations (vs default), chosen by PRCard's `ranked` prop. */
type Chart = "map" | "ranked";

/** Short group names for the one-line picker. */
/** Picker order: decision models first, then the LLMs (API and local share one group via the PRIMARY `kind` override). Kinds with no roster member (`baseline`, `local_llm`) are dropped before rendering. */
const PICK_ORDER: Kind[] = ["system1", "system1_ft", "baseline", "llm", "local_llm"];
const KIND_SHORT: Record<Kind, string> = { system1: "Decision models", system1_ft: "Supervised", llm: "LLM", local_llm: "Local LLM", baseline: "Floor" };


/** Recall/precision card with a map (scatter with interval boxes) or ranked (rows with whiskers) view. The chart mode is owned by the section so it can switch the dashboard layout. `explain` opens the details modal for a clicked mark or row (item ids are model keys). */
/** `pulse` (Compare models only: the Configurations page shows one family, so no decider to single out) lets the deciders' interval boxes breathe for a few cycles when the map loads or its points change. */
/** `ranked` picks the ranked view's component: `rail` (PRRail, Compare models) or `heat` (PRHeat, Compare configurations, differenced against `referenceId`, the family's base configuration). Both draw their own legend line. */
/** `sig` names what the card is showing (the corpus, and the family on Configurations): the `ranked` option's accent (ui.tsx Seg `accent`) breathes once when the card mounts and again whenever it changes, not on every model toggle. */
function PRCard({ items, chart, onChart, defaultZoom, emptyText, logos = true, height = 380, explain, pulse = false, ranked, referenceId, sig = "card" }: { items: PRItem[]; chart: Chart; onChart: (c: Chart) => void; defaultZoom: boolean; emptyText?: string; logos?: boolean; height?: number; explain?: (k: string) => void; pulse?: boolean; ranked: "rail" | "heat"; referenceId?: string; sig?: string }) {
  const setChart = onChart;
  const [zoom, setZoom] = useState(defaultZoom);
  const onSelect = explain && ((it: PRItem) => explain(it.id));
  const hover = useHover();
  const rowProps = { items, zoom, sortBy: "recall" as const, logos, onSelect, highlight: hover.id, onHover: hover.set };
  const accentPulse = usePulseWindow(sig, true, ROW_PULSE_MS);
  const options: { id: Chart; label: string; title?: string; accent?: boolean }[] = [
    { id: "map", label: "map", title: "Recall against precision, one box per model" },
    { id: "ranked", label: "ranked", title: ranked === "heat" ? "Rows sorted by recall, each value differenced against the Default configuration" : "Rows sorted by recall, whiskers for the intervals", accent: true },
  ];
  return (
    <div className={`card${chart === "map" ? " fill" : ""}`}>
      <div className="card-t">
        <h3>Recall and precision</h3>
        <span className="right">
          <Seg value={chart} onChange={setChart} options={options} pulse={accentPulse} />
          <Seg value={zoom ? "zoom" : "full"} onChange={(z) => setZoom(z === "zoom")} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }]} />
        </span>
      </div>
      {chart === "map" && <div className="chart-fill" style={{ minHeight: height }}><PRScatter items={items} zoom={zoom} emptyText={emptyText} logos={logos} fill onSelect={onSelect} highlight={hover.id} onHover={hover.set} pulse={pulse} /></div>}
      {chart === "ranked" && ranked === "rail" && <PRRail {...rowProps} />}
      {chart === "ranked" && ranked === "heat" && <PRHeat {...rowProps} referenceId={referenceId} />}
      {chart === "map" && (
        <div className="legend-note">
          <span>Dot: point estimate. Shaded box: 95% interval on recall (width) and precision (height).</span>
          {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
        </div>
      )}
    </div>
  );
}

type View = { corpus: string; tag: string; arm: "multi" | "single"; gray: Gray; level: Level; issue: string | null };

// ------------------------------------------------------------------------------------------------
// Metrics: the full figures for a row. Shown in the details modal's Metrics block; the chart hovers carry only the plotted value and one
// secondary line (qualitySub, opsSub).

/** The one secondary line of a recall/precision hover: what the point was scored on. */
function qualitySub(r: Rec, v: View): string | undefined {
  if (r.subset) return `scored on ${r.subset}`;
  const n = pick(r, v.level, v.gray, v.issue).detail?.n;
  return n ? `${fmtInt(n)} ${v.level === "decision" && !v.issue ? "decisions" : "documents"} scored` : undefined;
}

function qualityLines(r: Rec, v: View): { lines: TipLine[]; notes: string[] } {
  const p = pick(r, v.level, v.gray, v.issue);
  const lines: TipLine[] = [["Recall", fmtCI(p.recall)], ["Precision", fmtCI(p.precision)]];
  if (p.detail && "tp" in p.detail) {
    const m = p.detail as PRF;
    lines.push(["F1", m.f1 == null ? "—" : fmtPct(m.f1)]);
  }
  if (r.subset) lines.push(["Scored on", r.subset]);
  const notes: string[] = [];
  if (r.lever && !r.primary) notes.push(r.lever);
  return { lines, notes };
}

/** The model's median per-document latency (ms) and dollars per 100k documents; null when not measured. */
function opsValues(r: Rec): { ms: number | null; usd: number | null } {
  const c = costPerDoc(r);
  return { ms: r.ops.doc_latency_p50_ms, usd: c == null ? null : c * 1e5 };
}

/** The export's `latency_source` as a short phrase for the hover; null for a source the site does not describe. */
function latencySource(s: string): string | null {
  if (s === "per-call latency from the main run") return "per-call, main run";
  if (/same forward pass/.test(s)) return "same forward pass as the zero-shot Laya recipe";
  if (/concurrency-1/.test(s)) return "dedicated single-request run";
  return null;
}

/** The one secondary line of an Inference latency or Cost hover: the p95 and how the latency was measured, or where the money went. */
function opsSub(r: Rec, kind: "latency" | "cost"): string {
  if (kind === "latency") return [`p95 ${fmtMs(r.ops.doc_latency_p95_ms)}`, latencySource(r.ops.latency_source)].filter(Boolean).join(" · ");
  return `as paid · ${isGpuRow(r) ? "GPU rental" : "API"}`;
}

function opsLines(r: Rec): { lines: TipLine[]; notes: string[] } {
  const o = r.ops;
  const c = costPerDoc(r);
  const lines: TipLine[] = [
    ["Median latency", fmtMs(o.doc_latency_p50_ms)],
    ["p95 latency", fmtMs(o.doc_latency_p95_ms)],
    ["Cost per 100k docs", c == null ? "—" : fmtUSD(c * 1e5)],
    ["Cost per document", c == null ? "—" : c === 0 ? "$0" : `$${c.toFixed(c < 0.001 ? 5 : 4)}`],
    ["Input tokens per document", o.tokens_in_per_doc == null ? "—" : fmtInt(Math.round(o.tokens_in_per_doc))],
    ["Output tokens per document", o.tokens_out_per_doc == null ? "—" : fmtInt(Math.round(o.tokens_out_per_doc))],
  ];
  const notes: string[] = [];
  const src = latencySource(o.latency_source);
  if (src) notes.push(`Latency: ${src}.`);
  if (isGpuRow(r) && c != null) notes.push(`Cost is rented GPU time: ${GPU_NAME} at $${GPU_USD_PER_HOUR.toFixed(2)}/h for the median latency, one request at a time; serving documents concurrently would lower it.`);
  if (r.model === "laya-ft") notes.push("The labeled training data this checkpoint needed is not counted here.");
  return { lines, notes };
}

/**
 * Everything the details modal's Metrics block lists for one row on one corpus: the recall/precision, inference latency and cost, and determinism
 * facts that the chart tooltips used to carry. `shown` picks the page's selection out of the corpus rows, the referent of "vs. lowest shown".
 */
function metricsFor(key: string, corpus: string, v: View, shown: (rows: Rec[]) => Rec[]): Metrics | null {
  const tag = corpus === "trec" ? v.tag : "";
  const rows = DATA.records.filter((r) => r.corpus === corpus && r.tag === tag && r.arm === v.arm);
  const r = rows.find((x) => x.model === key);
  if (!r) return null;
  const vv: View = { ...v, corpus, tag, issue: corpus === v.corpus ? v.issue : null };
  const meta = DATA.corpora[corpusKey(corpus, tag)];
  const group = ABLATION_GROUPS.find((g) => g.id === r.group);
  const name = PRIMARY_BY_KEY[r.model]?.short ?? (r.variant ? `${group?.label ?? r.family} · ${VARIANT_LABEL[r.variant] ?? r.variant}` : r.name);
  const color = PRIMARY_BY_KEY[r.model]?.color ?? (r.variant ? variantColor(r.variant, group?.recipe ?? "") : "var(--ink)");
  const scope = vv.issue ? issueLabel(meta, vv.issue) : vv.level === "decision" ? "every decision" : "document level";
  const context = [meta.display, vv.arm === "single" ? "one issue per call" : "all issues per call", scope, !vv.issue && vv.gray === "nogray" ? "gray excluded" : null].filter(Boolean).join(" · ");
  const q = qualityLines(r, vv);
  const o = opsLines(r);
  const peers = shown(rows);
  const lowest = (f: (x: Rec) => number | null) => { const vals = peers.map(f).filter((x): x is number => x != null && x > 0); return vals.length ? Math.min(...vals) : null; };
  const ratio = (label: string, val: number | null, best: number | null): TipLine[] => {
    if (val == null || !best || val / best <= 1.05) return [];
    const k = val / best;
    return [[label, `${k >= 10 ? Math.round(k) : k.toFixed(1)}×`]];
  };
  const mine = opsValues(r);
  const sections: MetricSection[] = [
    { title: "Recall and precision", lines: q.lines, notes: q.notes },
    {
      title: "Speed and cost",
      lines: [...o.lines, ...ratio("Latency vs. fastest shown", mine.ms, lowest((x) => opsValues(x).ms)), ...ratio("Cost vs. cheapest shown", mine.usd, lowest((x) => opsValues(x).usd))],
      notes: o.notes,
    },
  ];
  const det = detFor(r, vv.arm, "default"), t0 = detFor(r, vv.arm, "t0");
  if (det) { const d = detLines(det, r, name); sections.push({ title: "Determinism", lines: d.lines, notes: d.notes }); }
  if (t0) { const d = detLines(t0, r, name); sections.push({ title: "Determinism · temperature 0", lines: d.lines, notes: d.notes }); }
  return { name, color, context, sections };
}

// ------------------------------------------------------------------------------------------------

/** The records the page plots for the view; keys data.ts hides (isHidden) are left out. */
function useRows(v: View) {
  return useMemo(() => DATA.records.filter((r) => r.corpus === v.corpus && r.tag === v.tag && r.arm === v.arm && !isHidden(r.model)), [v.corpus, v.tag, v.arm]);
}

/** The Speed and Cost hints: machine time and price only. */
const LATENCY_ITEMS: HintItem[] = [
  { k: "Measures", v: <><b>Median round-trip to score one document</b>, one request at a time.</> },
  { k: "Hosted", v: <>Includes network. <b>Rate limits and parallel throughput not measured.</b></> },
  { k: "Local", v: <>Laya and Gemma on <b>one A100</b>; no network.</> },
];
/** What a document is on each corpus, for the Cost hint's basis line. */
const DOC_NOUN: Record<string, string> = { trec: "email", mnk: "email" };
/**
 * The Cost hint for the rows the card shows: the per-100k basis, then the mean billed tokens per document across the shown LLM rows
 * (the corpus's average document length in each vendor's tokenizer), so the numbers follow the corpus and the selection.
 */
function costItems(recs: Rec[]): HintItem[] {
  const llm = recs.filter((r) => (r.kind === "llm" || r.kind === "local_llm") && r.ops.tokens_in_per_doc != null);
  const mean = (f: (r: Rec) => number | null) => { const v = llm.map(f).filter((x): x is number => x != null); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : null; };
  const tin = mean((r) => r.ops.tokens_in_per_doc), tout = mean((r) => r.ops.tokens_out_per_doc);
  const noun = DOC_NOUN[recs[0]?.corpus ?? ""] ?? "document";
  const tokens = tin == null ? null : `${fmtInt(Math.round(tin / 100) * 100)} in / ${fmtInt(Math.max(10, Math.round((tout ?? 0) / 10) * 10))} out`;
  return [
    { k: "Measures", v: <><b>API price as paid</b> × 100,000 documents.</> },
    { k: "Basis", v: <>This corpus's average billed tokens per {noun}{tokens ? <>: <b>≈{tokens}</b> for the LLMs</> : null}.</> },
    { k: "Pricing", v: <>OpenAI <b>flex (half of list)</b>; Anthropic prompt caching.</> },
    { k: "Local", v: <mark>Laya and Gemma: A100 rental at ${GPU_USD_PER_HOUR.toFixed(2)}/h × latency, <b>an upper bound</b>.</mark> },
  ];
}

/**
 * `decider` sets a row's name a step heavier (data.ts isDecider); Compare models passes it, the Configurations page (one family per chart) does not.
 * `emphasis` picks the rows that carry the faint --hl tint (Compare models: the decision models, Jev and Laya; the Configurations page passes nothing, its base row looks like the others).
 */
function OpsCards({ recs, colorOf, nameOf, logos = true, explain, decider, emphasis }: { recs: Rec[]; colorOf: (r: Rec) => string; nameOf: (r: Rec) => string; logos?: boolean; explain?: (k: string) => void; decider?: (r: Rec) => boolean; emphasis?: (r: Rec) => boolean }) {
  const onSelect = explain && ((it: BarItem) => explain(it.id));
  const hover = useHover();
  const latency: BarItem[] = recs.map((r) => {
    const { ms } = opsValues(r);
    return { id: r.model, name: nameOf(r), color: colorOf(r), value: ms, label: fmtMs(ms), sub: opsSub(r, "latency"), subset: starOf(r), decider: decider?.(r), emphasis: emphasis?.(r) };
  });
  const cost: BarItem[] = recs.map((r) => {
    const { usd } = opsValues(r);
    return { id: r.model, name: nameOf(r), color: colorOf(r), value: usd, label: fmtUSD(usd), sub: opsSub(r, "cost"), subset: starOf(r), decider: decider?.(r), emphasis: emphasis?.(r) };
  });
  return (
    <>
      <div className="card">
        <div className="card-t">
          <h3>Speed</h3><span className="unit">median latency per document</span>
          <span className="right"><Hint items={LATENCY_ITEMS} more="About" /></span>
        </div>
        <OpsBars items={latency} axis="milliseconds" unit="per document, median" logos={logos} onSelect={onSelect} highlight={hover.id} onHover={hover.set} />
      </div>
      <div className="card">
        <div className="card-t">
          <h3>Cost</h3><span className="unit">per 100k docs</span>
          <span className="right"><Hint items={costItems(recs)} more="About" /></span>
        </div>
        <OpsBars items={cost} axis="US dollars" unit="per 100k docs" logos={logos} onSelect={onSelect} highlight={hover.id} onHover={hover.set} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------------------------------------

/** A headline row's kind for grouping: the roster's override (Laya's fine-tuned row sits with the deciders) or the record's own. */
const kindOf = (r: Rec): Kind => PRIMARY_BY_KEY[r.model]?.kind ?? (r.kind as Kind);

/** The model multi-select for Compare models, rendered in the control bar. */
function ModelPicker({ v, on, setOn, explain }: { v: View; on: Set<string>; setOn: (s: Set<string>) => void; explain: (k: string) => void }) {
  const rows = useRows(v);
  const primary = rows.filter((r) => r.primary && PRIMARY_BY_KEY[r.model]);
  const byKind = PICK_ORDER.map((k) => ({ kind: k, recs: PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && kindOf(r) === k) })).filter((g) => g.recs.length);
  const avail = primary.filter((r) => on.has(r.model)).length;
  const groups: PickGroup[] = byKind.map((g) => ({
    id: g.kind, label: KIND_SHORT[g.kind as Kind],
    items: g.recs.map((r) => {
      const m = PRIMARY_BY_KEY[r.model];
      return { id: r.model, label: m.short, title: m.note, mark: <span style={{ color: m.color }}><Logo model={r.model} /></span>, suffix: starOf(r) ? <span className="sub" title={`scored on ${r.subset}`}>*</span> : undefined, detail: () => explain(r.model), accent: isDecider(kindOf(r)) ? m.color : undefined };
    }),
  }));
  return <Picker label="Models" summary={`${avail} of ${primary.length}`} groups={groups} on={on} onChange={setOn} onReset={() => setOn(new Set(DEFAULT_ON))} />;
}

function CompareSection({ v, on, explain }: { v: View; on: Set<string>; explain: (k: string) => void }) {
  const rows = useRows(v);
  const primary = rows.filter((r) => r.primary);
  const sel = PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && on.has(r.model));
  const [chart, setChart] = useState<Chart>("map");
  // the decider marker (data.ts isDecider: heavier name on rows) on every chart of this page, by the roster's kind (Laya's fine-tuned row is grouped with the deciders)
  const decider = (r: Rec) => isDecider(kindOf(r));
  // the emphasised rows on this page's tables (ui.tsx RowTint, the --hl tint): the decision models, Jev and Laya, by the same kind rule as `decider`
  const emphasis = (r: Rec) => isDecider(kindOf(r));

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    const meta = PRIMARY_BY_KEY[r.model];
    return { id: r.model, name: meta.short, color: meta.color, recall: p.recall, precision: p.precision, dashed: r.kind === "system1_ft", subset: starOf(r), sub: qualitySub(r, v), decider: decider(r), emphasis: emphasis(r) };
  });

  return (
    <section className="section">
      <HoverProvider>
        <div className={`dash${chart !== "map" ? " ranked" : ""}`}>
          <PRCard
            items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={explain}
            pulse ranked="rail" sig={v.corpus}
          />
          <div className="stack">
            <OpsCards recs={sel} colorOf={(r) => PRIMARY_BY_KEY[r.model].color} nameOf={(r) => PRIMARY_BY_KEY[r.model].short} explain={explain} decider={decider} emphasis={emphasis} />
            <ConsistencyCard recs={sel} colorOf={(r) => PRIMARY_BY_KEY[r.model].color} nameOf={(r) => PRIMARY_BY_KEY[r.model].short} arm={v.arm} onSelect={(r) => explain(r.model)} emphasis={emphasis} />
          </div>
        </div>
      </HoverProvider>
    </section>
  );
}

/** The Determinism card wired to the section's cross-chart hover (hover.tsx). */
function ConsistencyCard(props: Parameters<typeof Consistency>[0]) {
  const hover = useHover();
  return <Consistency {...props} highlight={hover.id} onHover={hover.set} />;
}

// ------------------------------------------------------------------------------------------------

function useVariants(v: View, grp: string) {
  const rows = useRows(v);
  return useMemo(() => {
    const recs = rows.filter((r) => r.group === grp && r.variant && !isHidden(r.model));
    return VARIANT_ORDER.map((vv) => recs.find((r) => r.variant === vv)).filter((r): r is Rec => !!r);
  }, [rows, grp]);
}

/** Model select + configuration multi-select for the Configurations page, rendered in the control bar. */
/** Compare configurations shows every configuration of the chosen family; there is no per-configuration picker (the rows' details buttons open the modal). */
function VariantPicker({ grp, setGrp }: { grp: string; setGrp: (g: string) => void }) {
  return (
    <Control label="Model">
      <span className="select">
        <select value={grp} onChange={(e) => setGrp(e.target.value)}>
          {ABLATION_GROUPS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
        </select>
      </span>
    </Control>
  );
}

function AblationSection({ v, grp, off, explain }: { v: View; grp: string; off: Set<string>; explain: (k: string) => void }) {
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useVariants(v, grp);
  const sel = variants.filter((r) => !off.has(r.variant!));
  const color = (r: Rec) => variantColor(r.variant!, G.recipe);
  const name = (r: Rec) => VARIANT_LABEL[r.variant!] ?? r.variant!;
  const [chart, setChart] = useState<Chart>("ranked");
  // The family's reference configuration, for the `heat` view's "vs default" column: the `@base` variant. Taken from the whole family, so
  // it is stable while configurations are toggled; PRHeat omits the comparison while that row is not shown.
  const referenceId = variants.map((r) => r.model).find((k) => k.endsWith("@base"));

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    return { id: r.model, name: name(r), color: color(r), recall: p.recall, precision: p.precision, subset: starOf(r), sub: qualitySub(r, v) };
  });

  // Only the Recall and precision card on this page (the Inference latency and Cost cards belong to Compare models); `.dash.ranked` lets it span the full width in both views.
  return (
    <section className="section">
      <HoverProvider>
        <div className="dash ranked">
          <PRCard
            items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={explain}
            emptyText={variants.length ? "Select at least one configuration." : "No configurations of this model were run on this corpus and arm."}
            logos={false} ranked="heat" referenceId={referenceId} sig={`${v.corpus}:${grp}`} height={460}
          />
        </div>
      </HoverProvider>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------

type Page = "compare" | "configurations";
const PAGES: { id: Page; label: string }[] = [{ id: "compare", label: "Compare models" }, { id: "configurations", label: "Compare configurations" }];

export default function App() {
  // The corpus is not persisted (hash or storage); siteCorpus still guards the state so an unlisted id (e.g. "veridian") can never render.
  const [corpus, setCorpusRaw] = useState(DEFAULT_CORPUS);
  const setCorpus = (c: string) => setCorpusRaw(siteCorpus(c));
  const tag: "" | "v0" = ""; // TREC criteria: always the calibrated set; the bare-topic (v0) rows stay exported but are not shown
  const arm: "multi" | "single" = "multi"; // prompting: always all issues per call; the one-issue-per-call rows stay exported but are not shown
  const gray: Gray = "all"; // gray gold labels always count; the exclude-gray view is not shown
  const level: Level = "doc"; // scope: document level or one issue; the pooled every-decision view is not shown
  const [issue, setIssue] = useState<string | null>(null);
  const v: View = { corpus, tag: corpus === "trec" ? tag : "", arm, gray, level, issue };
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];

  const pickCorpus = (c: string) => { setCorpus(c); setIssue(null); };
  const [explain, setExplain] = useState<string | null>(null);
  // The Method modal (how each experiment was run) opens from the header and foot buttons and from every hint's "Method" link, via MethodContext.
  const disclaimer = useDisclaimer(); // first-visit disclaimer; reopens from the footer
  // The Method modal (components/Method.tsx) is not mounted for now; hint "more" links open the About modal instead.
  const openMethod = disclaimer.show;
  const [on, setOn] = useState<Set<string>>(new Set(DEFAULT_ON));
  const [grp, setGrp] = useState("jev");
  const off = useMemo(() => new Set<string>(), []); // every configuration of the family is shown
  const corpusTitle = `${fmtInt(meta.n_docs)} documents · ${meta.n_issues} issues · ${fmtInt(meta.n_pos_docs_any)} responsive to at least one (${fmtPct(meta.n_pos_docs_any / meta.n_docs, 0)}) · gold: ${meta.gold}`;
  const [theme, setTheme] = useState<"dark" | "light">(() => (localStorage.getItem("theme") as "dark" | "light") || "light");
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("theme", theme); }, [theme]);
  const [pageId, setPageId] = useState<Page>(() => (location.hash === "#configurations" ? "configurations" : "compare"));
  useEffect(() => {
    const onHash = () => setPageId(location.hash === "#configurations" ? "configurations" : "compare");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const goPage = (p: Page) => { history.replaceState(null, "", p === "compare" ? "#compare" : "#configurations"); setPageId(p); window.scrollTo(0, 0); };

  const page = (
    <div className="page">
      <header className="masthead">
        <h1 className="title"><em>Zero-Shot Bake-Off:</em> Jev vs the Frontier LLMs</h1>
        <nav className="tabs" aria-label="Pages">
          {PAGES.map((p) => (
            <button key={p.id} className={pageId === p.id ? "on" : ""} onClick={() => goPage(p.id)} aria-current={pageId === p.id ? "page" : undefined}>{p.label}</button>
          ))}
        </nav>
        <span className="theme"><Seg value={theme} onChange={setTheme} options={[{ id: "dark", label: "Dark" }, { id: "light", label: "Light" }]} /></span>
      </header>

      <div className="controls">
        <Control label="Corpus">
          <Seg value={corpus} onChange={pickCorpus} options={CORPORA.map((c) => ({ id: c.id, label: c.label }))} />
          <Hint title={meta.display} text={corpusTitle} />
        </Control>
        {pageId === "compare"
          ? <ModelPicker v={v} on={on} setOn={setOn} explain={setExplain} />
          : <VariantPicker grp={grp} setGrp={setGrp} />}
        <Control label="Issue">
          <span className="select">
            <select value={issue ?? "__doc"} onChange={(e) => { const val = e.target.value; setIssue(val === "__doc" ? null : val); }}>
              <option value="__doc">Relevance</option>
              <optgroup label="Issues">
                {Object.keys(meta.issues).map((k) => <option key={k} value={k}>{issueLabel(meta, k)}</option>)}
              </optgroup>
            </select>
          </span>
        </Control>
      </div>

      {pageId === "compare" ? <CompareSection v={v} on={on} explain={setExplain} /> : <AblationSection v={v} grp={grp} off={off} explain={setExplain} />}
      {explain && (
        <ExplainModal
          initialKey={explain} initialCorpus={corpus} onClose={() => setExplain(null)}
          metrics={(k, c) => metricsFor(k, c, v, (rows) => (pageId === "compare" ? rows.filter((r) => r.primary && on.has(r.model)) : rows.filter((r) => r.group === grp && !!r.variant && !isHidden(r.model) && !off.has(r.variant))))}
        />
      )}

      {disclaimer.open && <DisclaimerModal onClose={disclaimer.close} />}

      <footer className="notes">
        <DisclaimerLink onClick={disclaimer.show} />
      </footer>
    </div>
  );
  return <MethodContext.Provider value={openMethod}>{page}</MethodContext.Provider>;
}
