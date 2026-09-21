import { useEffect, useMemo, useState } from "react";
import {
  ABLATION_GROUPS, CORPORA, DATA, DEFAULT_ON, GPU_NAME, GPU_USD_PER_HOUR, HUMAN_DEV_DOCS, HUMAN_DEV_DOCS_PER_HOUR, HUMAN_DEV_HOURS, HUMAN_DEV_USD, HUMAN_DEV_USD_PER_HOUR, PRIMARY, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER,
  corpusKey, costPerDoc, fmtCI, fmtHours, fmtInt, fmtMs, fmtPct, fmtUSD, isGpuRow, pick, variantColor,
  type Gray, type Kind, type Level, type PRF, type Rec,
} from "./data";
import { Control, Hint, Seg, type TipLine } from "./components/ui";
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
function PRCard({ items, hint, chart, onChart, defaultZoom, emptyText, logos = true, height = 380, explain }: { items: PRItem[]; hint: string; chart: Chart; onChart: (c: Chart) => void; defaultZoom: boolean; emptyText?: string; logos?: boolean; height?: number; explain?: (k: string) => void }) {
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
          <Hint left text={hint} />
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
    if (t.recall_range) lines.push([`Recall across ${t.seeds} seeds`, `${fmtPct(t.recall_range[0])} – ${fmtPct(t.recall_range[1])}`]);
    if (t.kind === "cal") notes.push("Precision is of the produced set, which the reviewer coded by hand; the review effort is in the time and cost panels.");
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
const HUMAN_SENTENCE = `The '+ human time' view adds the prompt or criteria development a person does for every non-TAR row: ${HUMAN_DEV_DOCS} documents reviewed at ${HUMAN_DEV_DOCS_PER_HOUR}/hour and $${HUMAN_DEV_USD_PER_HOUR}/hour, ${fmtHours(HUMAN_DEV_HOURS)} and ${fmtUSD(HUMAN_DEV_USD)}, counted once per 100k-document project; TAR rows are already human time, so in 'machine only' they show none.`;

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
          <span className="right">{seg}<Hint left text={`Median wall-clock time of the model's own calls per document, one request at a time, scaled to 100,000 documents. In the 'all issues per call' arm that is one call per document; in 'one issue per call' it is the sum over issues. Every service accepts parallel requests, so absolute hours shrink with concurrency for all models alike; the ratios are the comparison. Laya and Gemma ran on one A100. ${HUMAN_SENTENCE}`} /></span>
        </div>
        <OpsBars items={time} axis="hours" logos={logos} onSelect={onSelect} />
      </div>
      <div className="card">
        <div className="card-t">
          <h3>Cost</h3><span className="unit">per 100k documents, as paid</span>
          <span className="right">{seg}<Hint left text={`What was actually paid to the vendor, summed over the model's decisions and scaled to 100,000 documents. OpenAI ran on flex pricing (half of list); Anthropic used prompt caching on the all-issues arm. Laya and Gemma ran on a rented ${GPU_NAME} ($${GPU_USD_PER_HOUR.toFixed(2)}/hour), so their cost is that GPU time for the single-stream review time shown; serving many documents concurrently would lower it. ${HUMAN_SENTENCE}`} /></span>
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
          hint="Recall: gold-responsive items the model flagged, over all gold-responsive items. Precision: flagged items that were gold-responsive, over all flagged. Intervals are 95% Wilson score intervals. Because every document in each test set carries a gold label, the recall interval is computed over the gold-positive set and the precision interval over the model's flagged set, rather than from a review sample. All metrics use the model's own label, not a tuned threshold."
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
          hint="Same measurement as on Compare models. Differences between configurations are usually smaller than between model families, so this card defaults to ranked rows with the axes fitted to the data; switch to map and 0–100% to see the same points on the scale used there. Hover a configuration for what the lever changes. ★ marks the optimized configuration, the one selected on the Veridian dev split."
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
          <Hint text={`${meta.display}. ${corpusTitle}.`} />
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
          <Hint text="Document level: a document counts as responsive if it is positive for any issue, which is the relevance call a review team makes. Decision level pools every (document, issue) judgment. A single issue shows that issue's recall and precision on its own (all gold labels)." />
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

      <details className="notes">
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
          <p>Each model re-scored the same 300 Mallinckrodt emails five times (all eight issues per call, and the two narrow issues one per call). Bars are the probability that two runs disagree on a decision; the benchmark run is repeat one. Temperature 0 was run where the API accepts it.</p>
        </div>
        <div>
          <h4>Classical TAR</h4>
          <p>A simulated reviewer (gold labels; 50 documents/hour at $65/hour) plus TF‑IDF and logistic regression, one model per issue and one for any‑issue relevance. TAR 1.0 codes a random sample and picks its cutoff by cross‑validation on that sample alone; TAR 2.0 is continuous active learning stopped after two consecutive batches under 5% relevant. Rows are the median of five random seeds (three for TREC). TREC rows are trained and reviewed over the full 286k collection and scored on the same evaluation set as the other models. The 90%‑reviewer variants miscode 10% of documents at random; with that reviewer the CAL stopping rule can never fire (every batch comes back at least ~9% "relevant"), so those rows reviewed the whole collection on Mallinckrodt and CUAD and were not run on TREC.</p>
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
