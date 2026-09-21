import { useEffect, useMemo, useState } from "react";
import {
  ABLATION_GROUPS, CORPORA, DATA, DEFAULT_ON, GPU_NAME, GPU_USD_PER_HOUR, HUMAN_DEV_DOCS, HUMAN_DEV_DOCS_PER_HOUR, HUMAN_DEV_HOURS, HUMAN_DEV_USD, HUMAN_DEV_USD_PER_HOUR, PRIMARY, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER,
  corpusKey, costPerDoc, fmtCI, fmtHours, fmtInt, fmtMs, fmtPct, fmtUSD, isGpuRow, pick, variantColor,
  type Gray, type Kind, type Level, type PRF, type Rec,
} from "./data";
import { Control, Hint, NOTES_ID, Seg, type HintItem, type TipLine } from "./components/ui";
import { PRScatter, type PRItem } from "./components/PRScatter";
import { PRRows } from "./components/PRRows";
import { OpsBars, type BarItem } from "./components/OpsBars";
import { Consistency } from "./components/Consistency";
import { ExplainButton, ExplainModal } from "./components/Explain";
import { Picker, type PickGroup } from "./components/Picker";
import { Logo } from "./logos";

type Chart = "map" | "ranked";

/** Short group names for the one-line picker. */
/** Picker order: deciders first, then the LLMs (API and local share one group via the PRIMARY `kind` override), then TAR. Kinds with no roster member (`baseline`, `local_llm`) are dropped before rendering. */
const PICK_ORDER: Kind[] = ["system1", "system1_ft", "baseline", "llm", "local_llm", "tar"];
const KIND_SHORT: Record<Kind, string> = { system1: "Deciders", system1_ft: "Supervised", llm: "LLM", local_llm: "Local LLM", tar: "Classical TAR", baseline: "Floor" };

/** Recall/precision card with a map (scatter with interval boxes) or ranked (rows with whiskers) view. The chart mode is owned by the section so it can switch the dashboard layout. `explain` opens the details modal for a clicked mark or row (item ids are model keys). */
function PRCard({ items, hint, chart, onChart, defaultZoom, emptyText, logos = true, height = 380, explain }: { items: PRItem[]; hint: HintItem[]; chart: Chart; onChart: (c: Chart) => void; defaultZoom: boolean; emptyText?: string; logos?: boolean; height?: number; explain?: (k: string) => void }) {
  const setChart = onChart;
  const [zoom, setZoom] = useState(defaultZoom);
  const onSelect = explain && ((it: PRItem) => explain(it.id));
  return (
    <div className={`card${chart === "map" ? " fill" : ""}`}>
      <div className="card-t">
        <h3>Recall and precision</h3>
        <span className="right">
          <Seg value={chart} onChange={setChart} options={[{ id: "map", label: "map", title: "Recall against precision, one box per model" }, { id: "ranked", label: "ranked", title: "Rows sorted by F1, whiskers for the intervals" }]} />
          <Seg value={zoom ? "zoom" : "full"} onChange={(z) => setZoom(z === "zoom")} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }]} />
          <Hint items={hint} more="Notes on method" />
        </span>
      </div>
      {chart === "map" ? <div className="chart-fill" style={{ minHeight: height }}><PRScatter items={items} zoom={zoom} emptyText={emptyText} logos={logos} fill onSelect={onSelect} /></div> : <PRRows items={items} zoom={zoom} sortBy="f1" logos={logos} onSelect={onSelect} />}
      <div className="legend-note">
        {chart === "map" ? <span>Dot: point estimate. Shaded box: 95% interval on recall (width) and precision (height).</span> : <span>Sorted by F1. Dot: point estimate. Whisker: 95% interval.</span>}
        {items.some((i) => i.subset) && <span>* scored on a stratified subset (hover for the count)</span>}
      </div>
    </div>
  );
}

type View = { corpus: string; tag: string; arm: "multi" | "single"; gray: Gray; level: Level; issue: string | null };

/** Recall and precision card, Compare models. */
const PR_ITEMS: HintItem[] = [
  { k: "Recall", v: "Gold-responsive items the model flagged, over all gold-responsive items." },
  { k: "Precision", v: "Flagged items that were gold-responsive, over all flagged." },
  { k: "Intervals", v: "95% Wilson score; recall over the gold-positive set, precision over the flagged set, since every document carries a gold label." },
  { k: "Label", v: "The model's own label, not a tuned threshold." },
  { k: "Scope", v: "Document level: responsive if positive for any issue. Decision level: every (document, issue) judgment pooled." },
  { k: "Gray", v: "'Exclude gray' drops decisions whose gold label was flagged as debatable." },
  { k: "*", v: "Scored on a stratified subset; hover a row for the count. Intervals widen to match." },
];
/** Recall and precision card, Configurations page. */
const CONFIG_PR_ITEMS: HintItem[] = [
  { k: "Measures", v: "The same recall and precision as on Compare models, for configurations of one model." },
  { k: "Default view", v: "Ranked rows with axes fitted to the data, since configurations differ less than model families; switch to map and 0–100% for the Compare scale." },
  { k: "Intervals", v: "95% Wilson score; * marks a stratified subset." },
  { k: "Levers", v: "Hover a configuration for what its lever changes." },
  { k: "★", v: "The optimized configuration, selected on the Veridian dev split." },
];

// ------------------------------------------------------------------------------------------------
// tooltip content

function qualityLines(r: Rec, v: View): { lines: TipLine[]; notes: string[] } {
  const p = pick(r, v.level, v.gray, v.issue);
  const lines: TipLine[] = [["Recall", fmtCI(p.recall)], ["Precision", fmtCI(p.precision)]];
  if (p.detail && "tp" in p.detail) {
    const m = p.detail as PRF;
    lines.push(["F1", m.f1 == null ? "—" : fmtPct(m.f1)]);
  }
  if (r.subset) lines.push(["Scored on", r.subset]);
  const notes: string[] = [];
  if (r.tar) {
    const t = r.tar;
    lines.push([t.kind === "cal" ? "Reviewed by hand" : "Coded for training", `${fmtInt(t.docs_reviewed)} of ${fmtInt(t.n_corpus)} (${fmtPct(t.review_share, 0)})`]);
    if (t.kind === "cal" && t.production) lines.push(["Produced set (hand-coded)", `recall ${fmtPct(t.production.recall?.[0] ?? null)} · precision ${fmtPct(t.production.precision?.[0] ?? null)}`]);
    if (t.recall_range) lines.push([`Recall across ${t.seeds} seeds`, `${fmtPct(t.recall_range[0])} – ${fmtPct(t.recall_range[1])}`]);
    if (t.kind === "cal") {
      notes.push("Plotted: the review set the classifier queued for the reviewer (recall = relevant documents reached, precision = share of reviewed documents that were relevant), the analogue of a model's flagged set.");
      if (t.downsampled) notes.push(`Run on a ${fmtPct(t.pool_richness ?? 0, 0)}-rich pool of ${fmtInt(t.n_corpus)} documents (all gold-negatives plus a random draw of positives); the benchmark sample itself is 61% rich by design.`);
    }
  }
  if (r.lever && !r.primary) notes.push(r.lever);
  return { lines, notes };
}

/** "machine": the model's own time and bill. "human": adds the prompt/criteria development a person does for every non-TAR row. */
type OpsMode = "machine" | "human";

/** Hours and dollars per 100k documents for a record under the toggle; null when not measured or, for TAR in machine mode, not applicable. */
function opsValues(r: Rec, mode: OpsMode): { hours: number | null; usd: number | null } {
  const c = costPerDoc(r);
  if (r.tar) return mode === "machine" ? { hours: null, usd: null } : { hours: r.ops.hours_per_100k_docs, usd: c == null ? null : c * 1e5 };
  const add = mode === "human";
  return {
    hours: r.ops.hours_per_100k_docs == null ? null : r.ops.hours_per_100k_docs + (add ? HUMAN_DEV_HOURS : 0),
    usd: c == null ? null : c * 1e5 + (add ? HUMAN_DEV_USD : 0),
  };
}

function opsLines(r: Rec, mode: OpsMode): { lines: TipLine[]; notes: string[] } {
  const o = r.ops;
  const c = costPerDoc(r);
  const usd100k = c == null ? "—" : fmtUSD(c * 1e5);
  if (r.tar) {
    const t = r.tar;
    return {
      lines: [
        ["Documents reviewed by hand", `${fmtInt(t.docs_reviewed)} of ${fmtInt(t.n_corpus)}`],
        ["Reviewer hours", fmtHours(t.hours)],
        ["Reviewer cost", fmtUSD(t.cost_usd)],
        ["Per 100k docs, scaled from this corpus", `${fmtHours(o.hours_per_100k_docs)} · ${usd100k}`],
      ],
      notes: [`${t.reviewer.docs_per_hour} docs/hour at $${t.reviewer.usd_per_hour}/hour; classifier compute not charged. A fixed coded sample does not scale with corpus size, so the per-100k figure is specific to a ${fmtInt(t.n_corpus)}-document collection.`],
    };
  }
  const lines: TipLine[] = [
    ["Time per 100k docs", fmtHours(o.hours_per_100k_docs)],
    ["Cost per 100k docs", usd100k],
  ];
  const notes: string[] = [];
  if (isGpuRow(r) && o.hours_per_100k_docs != null) {
    lines.push(["GPU rental", `${GPU_NAME} at $${GPU_USD_PER_HOUR.toFixed(2)}/h × ${fmtHours(o.hours_per_100k_docs)} = ${usd100k} per 100k`]);
    notes.push("Cost is the rented GPU time for the single-stream review time shown; serving many documents concurrently would lower it.");
  }
  if (mode === "human") {
    const tot = opsValues(r, mode);
    lines.push(
      ["Prompt development", `${fmtHours(HUMAN_DEV_HOURS)} · ${fmtUSD(HUMAN_DEV_USD)} (${HUMAN_DEV_DOCS} docs at ${HUMAN_DEV_DOCS_PER_HOUR}/h, $${HUMAN_DEV_USD_PER_HOUR}/h; counted once per 100k-document project)`],
      ["Shown, machine + human", `${fmtHours(tot.hours)} · ${fmtUSD(tot.usd)}`],
    );
    if (r.model === "laya-ft") notes.push("The labeled training data this checkpoint needed is not counted here, only the same 500-document iteration every row gets.");
  }
  lines.push(
    ["Median time per doc", fmtMs(o.doc_latency_p50_ms)],
    ["Tokens in / out per doc", o.tokens_in_per_doc == null ? "—" : `${fmtInt(Math.round(o.tokens_in_per_doc))} / ${fmtInt(Math.round(o.tokens_out_per_doc ?? 0))}`],
  );
  return { lines, notes };
}

// ------------------------------------------------------------------------------------------------

function useRows(v: View) {
  return useMemo(() => DATA.records.filter((r) => r.corpus === v.corpus && r.tag === v.tag && r.arm === v.arm), [v.corpus, v.tag, v.arm]);
}

const OPS_MODE_KEY = "opsMode";
const OPS_MODE_OPTIONS = [
  { id: "machine" as const, label: "machine only", title: "The model's own time and bill" },
  { id: "human" as const, label: "+ human time", title: `Adds ${fmtHours(HUMAN_DEV_HOURS)} and ${fmtUSD(HUMAN_DEV_USD)} of prompt development to every non-TAR row` },
];
/** The two rows shared by the Review time and Cost hints: what the '+ human time' toggle adds, and why TAR rows disappear without it. */
const HUMAN_ITEMS: HintItem[] = [
  { k: "+ human time", v: `Adds prompt or criteria development: ${HUMAN_DEV_DOCS} documents at ${HUMAN_DEV_DOCS_PER_HOUR}/h and $${HUMAN_DEV_USD_PER_HOUR}/h, ${fmtHours(HUMAN_DEV_HOURS)} and ${fmtUSD(HUMAN_DEV_USD)}, once per 100k-document project.` },
  { k: "TAR rows", v: "Already human time, so they are hidden in machine-only." },
];
const TIME_ITEMS: HintItem[] = [
  { k: "Measures", v: "Median wall-clock time per document for the model's own calls, one request at a time, scaled to 100,000 documents." },
  { k: "Arms", v: "All issues per call: one call per document. One issue per call: the sum over issues." },
  { k: "Parallelism", v: "Every service accepts parallel requests, so hours shrink for all models alike; compare the ratios, not the absolutes." },
  { k: "GPU rows", v: "Laya and Gemma ran on one rented A100." },
  ...HUMAN_ITEMS,
];
const COST_ITEMS: HintItem[] = [
  { k: "Measures", v: "What was actually paid to the vendor, summed over the model's decisions and scaled to 100,000 documents." },
  { k: "Pricing", v: "OpenAI on flex pricing (half of list); Anthropic with prompt caching on the all-issues arm." },
  { k: "GPU rows", v: `Laya and Gemma: a rented ${GPU_NAME} at $${GPU_USD_PER_HOUR.toFixed(2)}/h times the single-stream review time, so an upper bound.` },
  ...HUMAN_ITEMS,
];

function OpsCards({ recs, colorOf, nameOf, logos = true, explain }: { recs: Rec[]; colorOf: (r: Rec) => string; nameOf: (r: Rec) => string; logos?: boolean; explain?: (k: string) => void }) {
  const [mode, setMode] = useState<OpsMode>(() => (localStorage.getItem(OPS_MODE_KEY) === "human" ? "human" : "machine"));
  const onSelect = explain && ((it: BarItem) => explain(it.id));
  useEffect(() => { localStorage.setItem(OPS_MODE_KEY, mode); }, [mode]);
  const empty = (r: Rec) => (r.tar && mode === "machine" ? "human only" : undefined);
  const time: BarItem[] = recs.map((r) => {
    const { hours } = opsValues(r, mode);
    return { id: r.model, name: nameOf(r), color: colorOf(r), value: hours, label: fmtHours(hours), tip: opsLines(r, mode), subset: r.subset, empty: empty(r) };
  });
  const cost: BarItem[] = recs.map((r) => {
    const { usd } = opsValues(r, mode);
    return { id: r.model, name: nameOf(r), color: colorOf(r), value: usd, label: fmtUSD(usd), tip: opsLines(r, mode), subset: r.subset, empty: empty(r) };
  });
  const seg = <Seg value={mode} onChange={setMode} options={OPS_MODE_OPTIONS} />;
  return (
    <>
      <div className="card">
        <div className="card-t">
          <h3>Review time</h3><span className="unit">per 100k documents, single stream</span>
          <span className="right">{seg}<Hint items={TIME_ITEMS} more="Notes on method" /></span>
        </div>
        <OpsBars items={time} axis="hours" logos={logos} onSelect={onSelect} />
      </div>
      <div className="card">
        <div className="card-t">
          <h3>Cost</h3><span className="unit">per 100k documents, as paid</span>
          <span className="right">{seg}<Hint items={COST_ITEMS} more="Notes on method" /></span>
        </div>
        <OpsBars items={cost} axis="US dollars" logos={logos} onSelect={onSelect} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------------------------------------

/** The model multi-select for Compare models, rendered in the control bar. */
function ModelPicker({ v, on, setOn, explain }: { v: View; on: Set<string>; setOn: (s: Set<string>) => void; explain: (k: string) => void }) {
  const rows = useRows(v);
  const primary = rows.filter((r) => r.primary && PRIMARY_BY_KEY[r.model]);
  const kindOf = (r: Rec) => PRIMARY_BY_KEY[r.model].kind ?? r.kind;
  const byKind = PICK_ORDER.map((k) => ({ kind: k, recs: PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && kindOf(r) === k) })).filter((g) => g.recs.length);
  const avail = primary.filter((r) => on.has(r.model)).length;
  const groups: PickGroup[] = byKind.map((g) => ({
    id: g.kind, label: KIND_SHORT[g.kind as Kind],
    items: g.recs.map((r) => {
      const m = PRIMARY_BY_KEY[r.model];
      return { id: r.model, label: m.short, title: m.note, mark: <span style={{ color: m.color }}><Logo model={r.model} /></span>, suffix: r.subset ? <span className="sub" title={`scored on ${r.subset}`}>*</span> : undefined, detail: () => explain(r.model) };
    }),
  }));
  return <Picker label="Models" summary={`${avail} of ${primary.length}`} groups={groups} on={on} onChange={setOn} onReset={() => setOn(new Set(DEFAULT_ON))} />;
}

function CompareSection({ v, on, explain }: { v: View; on: Set<string>; explain: (k: string) => void }) {
  const rows = useRows(v);
  const primary = rows.filter((r) => r.primary);
  const sel = PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && on.has(r.model));
  const [chart, setChart] = useState<Chart>("map");

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    const meta = PRIMARY_BY_KEY[r.model];
    return { id: r.model, name: meta.short, color: meta.color, recall: p.recall, precision: p.precision, dashed: r.kind === "system1_ft", subset: r.subset, tip: qualityLines(r, v) };
  });

  return (
    <section className="section">
      <div className={`dash${chart === "ranked" ? " ranked" : ""}`}>
        <PRCard
          items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={explain}
          hint={PR_ITEMS}
        />
        <div className="stack">
          <OpsCards recs={sel} colorOf={(r) => PRIMARY_BY_KEY[r.model].color} nameOf={(r) => PRIMARY_BY_KEY[r.model].short} explain={explain} />
          <Consistency recs={sel} colorOf={(r) => PRIMARY_BY_KEY[r.model].color} nameOf={(r) => PRIMARY_BY_KEY[r.model].short} arm={v.arm} onSelect={(r) => explain(r.model)} />
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------

function useVariants(v: View, grp: string) {
  const rows = useRows(v);
  return useMemo(() => {
    const recs = rows.filter((r) => r.group === grp && r.variant);
    return VARIANT_ORDER.map((vv) => recs.find((r) => r.variant === vv)).filter((r): r is Rec => !!r);
  }, [rows, grp]);
}

/** Model select + configuration multi-select for the Configurations page, rendered in the control bar. */
function VariantPicker({ v, grp, setGrp, off, setOff, explain }: { v: View; grp: string; setGrp: (g: string) => void; off: Set<string>; setOff: (s: Set<string>) => void; explain: (k: string) => void }) {
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useVariants(v, grp);
  const on = new Set(variants.filter((r) => !off.has(r.variant!)).map((r) => r.variant!));
  const groups: PickGroup[] = [{
    id: grp, label: G.label,
    items: variants.map((r) => ({
      id: r.variant!, label: VARIANT_LABEL[r.variant!] ?? r.variant!, title: r.lever ?? undefined,
      mark: <span className="sw" style={{ background: variantColor(r.variant!, G.recipe) }} />,
      suffix: <>{r.variant === G.recipe && <span className="star" title="optimized configuration: selected on the Veridian dev split">★</span>}{r.subset && <span className="sub" title={`scored on ${r.subset}`}>*</span>}</>,
      detail: () => explain(r.model),
    })),
  }];
  return (
    <>
      <Control label="Model">
        <span className="select">
          <select value={grp} onChange={(e) => { setGrp(e.target.value); setOff(new Set()); }}>
            {ABLATION_GROUPS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
          </select>
        </span>
      </Control>
      <Picker
        label="Configurations" summary={`${on.size} of ${variants.length}`} groups={groups} on={on}
        onChange={(next) => setOff(new Set(variants.map((r) => r.variant!).filter((vv) => !next.has(vv))))}
        onReset={() => setOff(new Set())}
        footer={<span className="pick-note">{G.note}</span>}
      />
    </>
  );
}

function AblationSection({ v, grp, off, explain }: { v: View; grp: string; off: Set<string>; explain: (k: string) => void }) {
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useVariants(v, grp);
  const sel = variants.filter((r) => !off.has(r.variant!));
  const color = (r: Rec) => variantColor(r.variant!, G.recipe);
  const name = (r: Rec) => VARIANT_LABEL[r.variant!] ?? r.variant!;
  const [chart, setChart] = useState<Chart>("ranked");

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    return { id: r.model, name: name(r), color: color(r), recall: p.recall, precision: p.precision, subset: r.subset, tip: qualityLines(r, v) };
  });

  return (
    <section className="section">
      <div className={`dash${chart === "ranked" ? " ranked" : ""}`}>
        <PRCard
          items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={explain}
          emptyText={variants.length ? "Select at least one configuration." : "No configurations of this model were run on this corpus and arm."}
          logos={false}
          hint={CONFIG_PR_ITEMS}
        />
        <div className="stack"><OpsCards recs={sel} colorOf={color} nameOf={name} logos={false} explain={explain} /></div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------

type Page = "compare" | "configurations";
const PAGES: { id: Page; label: string }[] = [{ id: "compare", label: "Compare models" }, { id: "configurations", label: "Configurations of one model" }];

export default function App() {
  const [corpus, setCorpus] = useState("mnk");
  const [tag, setTag] = useState<"" | "v0">("");
  const [arm, setArm] = useState<"multi" | "single">("multi");
  const [gray, setGray] = useState<Gray>("all");
  const [level, setLevel] = useState<Level>("doc");
  const [issue, setIssue] = useState<string | null>(null);
  const v: View = { corpus, tag: corpus === "trec" ? tag : "", arm, gray, level, issue };
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];

  const pickCorpus = (c: string) => { setCorpus(c); setIssue(null); };
  const [explain, setExplain] = useState<string | null>(null);
  const [on, setOn] = useState<Set<string>>(new Set(DEFAULT_ON));
  const [grp, setGrp] = useState("jev");
  const [off, setOff] = useState<Set<string>>(new Set());
  const corpusTitle = `${fmtInt(meta.n_docs)} documents · ${meta.n_issues} issues · ${fmtInt(meta.n_pos_docs_any)} responsive to at least one (${fmtPct(meta.n_pos_docs_any / meta.n_docs, 0)}) · gold: ${meta.gold}`;
  const [more, setMore] = useState(false);
  const nonDefault = [
    arm === "single" ? "one issue per call" : null,
    issue ? `issue: ${meta.issues[issue]}` : level === "decision" ? "every decision" : null,
    !issue && gray === "nogray" ? "gray excluded" : null,
  ].filter((x): x is string => !!x);
  const [theme, setTheme] = useState<"dark" | "light">(() => (localStorage.getItem("theme") as "dark" | "light") || "dark");
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("theme", theme); }, [theme]);
  const [pageId, setPageId] = useState<Page>(() => (location.hash === "#configurations" ? "configurations" : "compare"));
  useEffect(() => {
    const onHash = () => setPageId(location.hash === "#configurations" ? "configurations" : "compare");
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const goPage = (p: Page) => { history.replaceState(null, "", p === "compare" ? "#compare" : "#configurations"); setPageId(p); window.scrollTo(0, 0); };

  return (
    <div className="page">
      <header className="masthead">
        <h1 className="title">Decider Model v LLM Bakeoff</h1>
        <nav className="tabs" aria-label="Pages">
          {PAGES.map((p) => (
            <button key={p.id} className={pageId === p.id ? "on" : ""} onClick={() => goPage(p.id)} aria-current={pageId === p.id ? "page" : undefined}>{p.label}</button>
          ))}
        </nav>
        <span className="theme"><Seg value={theme} onChange={setTheme} options={[{ id: "dark", label: "Dark" }, { id: "light", label: "Light" }]} /></span>
      </header>

      <div className="controls">
        <Control label="Corpus">
          <Seg value={corpus} onChange={pickCorpus} options={CORPORA.map((c) => ({ id: c.id, label: c.label, title: c.id === corpus ? corpusTitle : c.short }))} />
          <Hint title={meta.display} text={corpusTitle} />
        </Control>
        {pageId === "compare"
          ? <ModelPicker v={v} on={on} setOn={setOn} explain={setExplain} />
          : <VariantPicker v={v} grp={grp} setGrp={setGrp} off={off} setOff={setOff} explain={setExplain} />}
        {corpus === "trec" && (
          <Control label="Criteria">
            <Seg value={tag} onChange={setTag} options={[
              { id: "", label: "calibrated", title: "Criteria refined once on a 668-email calibration set disjoint from this evaluation set" },
              { id: "v0", label: "bare topic", title: "The NIST topic sentence as written, no iteration" },
            ]} />
          </Control>
        )}
        <span className="more-wrap">
          {!more && nonDefault.length > 0 && <span className="more-summary">{nonDefault.join(" · ")}</span>}
          <ExplainButton label={pageId === "compare" ? "how each model is asked" : "requests side by side"} onClick={() => setExplain(pageId === "compare" ? "jev@base" : `${grp}@base`)} />
          <button className={`more${more ? " on" : ""}`} onClick={() => setMore((m) => !m)} aria-expanded={more}>
            {more ? "Fewer options" : "More options"}<span className="chev" />
          </button>
        </span>
      </div>
      {more && (
      <div className="controls controls-more">
        <Control label="Prompting">
          <Seg value={arm} onChange={setArm} options={[
            { id: "multi", label: "all issues per call", title: "One call per document answers every issue" },
            { id: "single", label: "one issue per call", title: "One call per (document, issue) pair" },
          ]} />
        </Control>
        <Control label="Scope">
          <span className="select">
            <select value={issue ?? (level === "doc" ? "__doc" : "__dec")} onChange={(e) => { const val = e.target.value; if (val === "__doc") { setIssue(null); setLevel("doc"); } else if (val === "__dec") { setIssue(null); setLevel("decision"); } else setIssue(val); }}>
              <option value="__doc">Any issue (document level)</option>
              <option value="__dec">Every decision (document × issue)</option>
              <optgroup label="Single issue">
                {Object.entries(meta.issues).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
              </optgroup>
            </select>
          </span>
          <Hint title="Scope" items={[
            { k: "Document", v: "A document is responsive if it is positive for any issue: the relevance call a review team makes." },
            { k: "Decision", v: "Pools every (document, issue) judgment." },
            { k: "Single issue", v: "That issue's recall and precision on its own, over all gold labels." },
          ]} />
        </Control>
        <Control label="Gold">
          <Seg value={issue ? "all" : gray} onChange={setGray} options={[
            { id: "all", label: "all labels" },
            { id: "nogray", label: "exclude gray", title: issue ? "Not available for a single issue" : "Drop decisions whose gold label was flagged as debatable" },
          ]} />
        </Control>
      </div>
      )}

      {pageId === "compare" ? <CompareSection v={v} on={on} explain={setExplain} /> : <AblationSection v={v} grp={grp} off={off} explain={setExplain} />}
      {explain && <ExplainModal initialKey={explain} initialCorpus={corpus} onClose={() => setExplain(null)} />}

      <details className="notes" id={NOTES_ID}>
        <summary>Notes on method<span className="chev" /></summary>
        <footer className="foot">
        <div>
          <h4>What every model saw</h4>
          <p>The same document text, the same issue criteria and matter context, and returned a label plus a probability. Metrics use the model's own label. Jev rows are the default configuration unless marked optimized.</p>
        </div>
        <div>
          <h4>Laya</h4>
          <p>The Laya row on Compare models is a checkpoint fine-tuned (RLCD) on a 30% document-level dev split of the same corpus and scored on the held-out 70%; every other row is zero-shot, so it is not on equal footing, and the labeled data it needed is not counted in the time and cost panels. The zero-shot Laya configurations are on the Configurations page.</p>
        </div>
        <div>
          <h4>GPU cost</h4>
          <p>Laya and Gemma 3 12B ran on a rented {GPU_NAME} rather than an API. Their cost is that GPU's on-demand rate (${GPU_USD_PER_HOUR.toFixed(2)}/hour, Lambda list price as of September 2026) times the single-stream review time shown, so it is an upper bound: serving many documents concurrently would lower it.</p>
        </div>
        <div>
          <h4>Human time</h4>
          <p>The '+ human time' toggle on the time and cost cards adds the prompt or criteria development a person does for every non-TAR row: {HUMAN_DEV_DOCS} documents reviewed at {HUMAN_DEV_DOCS_PER_HOUR}/hour and ${HUMAN_DEV_USD_PER_HOUR}/hour, {fmtHours(HUMAN_DEV_HOURS)} and {fmtUSD(HUMAN_DEV_USD)}, counted once per 100k-document project. TAR rows are already human time and are unchanged; in 'machine only' they show none.</p>
        </div>
        <div>
          <h4>Intervals</h4>
          <p>95% Wilson score intervals. Recall is measured over the gold-positive set, precision over the flagged set. Where a model is scored on a stratified subset (marked *), intervals widen to match.</p>
        </div>
        <div>
          <h4>TREC criteria</h4>
          <p>Issue criteria were refined once on a 668-email calibration set that is disjoint from the evaluation set shown. The bare-topic toggle shows the NIST topic sentence with no iteration.</p>
        </div>
        <div>
          <h4>Determinism</h4>
          <p>Measured on Mallinckrodt only and shown for every corpus, since it is a property of the model rather than the documents. Each model re-scored the same 300 Mallinckrodt emails (100 with a debatable gold label, 100 clear positives, 100 clear negatives) five times (all eight issues per call, and the two narrow issues one per call). Bars are the probability that two runs disagree on a decision, with a 95% bootstrap interval over decisions; the benchmark run is repeat one. Temperature 0 was run where the API accepts it; Anthropic rejects sampling parameters on Sonnet 5. Jev and Laya expose no sampling controls. Classical TAR rows are 0 by construction; their spread across random training samples is the seed range in the row tooltips.</p>
        </div>
        <div>
          <h4>Classical TAR</h4>
          <p>A simulated reviewer (gold labels; 50 documents/hour at $65/hour) plus TF‑IDF and logistic regression, one model per issue and one for any‑issue relevance. TAR 1.0 codes a random sample and picks its cutoff by cross‑validation on that sample alone. TAR 2.0 is continuous active learning stopped by the knee method (Cormack & Grossman 2016: pre‑knee slope at least 6× post‑knee, after 10% of the collection); it is plotted as the review set the classifier queued, since the hand‑coded production set has the reviewer's precision rather than the classifier's. Mallinckrodt's benchmark sample is 61% rich by design, so CAL there runs on a 10%‑rich pool (all gold‑negative emails plus a random draw of positives per seed). Rows are the median of five random seeds (three for TREC). TREC rows are trained and reviewed over the full 286k collection and scored on the same evaluation set as the other models. The imperfect‑reviewer variants miss 10% of relevant documents and over‑code 2% of non‑relevant ones.</p>
        </div>
        <div>
          <h4>Absent cells</h4>
          <p>A few one-issue-per-call Laya configurations stalled and are omitted from that view. The fine-tuned Laya checkpoint on CUAD collapsed to a constant negative and is shown as such.</p>
        </div>
        </footer>
      </details>
    </div>
  );
}
