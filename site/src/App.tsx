import { useEffect, useMemo, useState } from "react";
import {
  ABLATION_GROUPS, CORPORA, DATA, DEFAULT_ON, KIND_LABEL, KIND_ORDER, PRIMARY, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER,
  corpusKey, fmtCI, fmtHours, fmtInt, fmtMs, fmtPct, fmtUSD, pick, variantColor,
  type Gray, type Kind, type Level, type PRF, type Rec,
} from "./data";
import { Control, Hint, Seg, type TipLine } from "./components/ui";
import { PRScatter, type PRItem } from "./components/PRScatter";
import { PRRows } from "./components/PRRows";
import { OpsBars, type BarItem } from "./components/OpsBars";
import { Consistency } from "./components/Consistency";
import { ExplainButton, ExplainModal } from "./components/Explain";
import { Logo } from "./logos";

type Chart = "map" | "ranked";

/** Recall/precision card with a map (scatter with interval boxes) or ranked (rows with whiskers) view. */
function PRCard({ items, hint, defaultChart, defaultZoom, emptyText, logos = true }: { items: PRItem[]; hint: string; defaultChart: Chart; defaultZoom: boolean; emptyText?: string; logos?: boolean }) {
  const [chart, setChart] = useState<Chart>(defaultChart);
  const [zoom, setZoom] = useState(defaultZoom);
  return (
    <div className="card">
      <div className="card-t">
        <h3>Recall and precision</h3>
        <span className="right">
          <Seg value={chart} onChange={setChart} options={[{ id: "map", label: "map", title: "Recall against precision, one box per model" }, { id: "ranked", label: "ranked", title: "Rows sorted by F1, whiskers for the intervals" }]} />
          <Seg value={zoom ? "zoom" : "full"} onChange={(z) => setZoom(z === "zoom")} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }]} />
          <Hint left text={hint} />
        </span>
      </div>
      {chart === "map" ? <PRScatter items={items} zoom={zoom} emptyText={emptyText} logos={logos} /> : <PRRows items={items} zoom={zoom} sortBy="f1" logos={logos} />}
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

function opsLines(r: Rec): { lines: TipLine[]; notes: string[] } {
  const o = r.ops;
  if (r.tar) {
    const t = r.tar;
    return {
      lines: [
        ["Documents reviewed by hand", `${fmtInt(t.docs_reviewed)} of ${fmtInt(t.n_corpus)}`],
        ["Reviewer hours", fmtHours(t.hours)],
        ["Reviewer cost", fmtUSD(t.cost_usd)],
        ["Per 100k docs, scaled from this corpus", `${fmtHours(o.hours_per_100k_docs)} · ${o.cost_per_doc == null ? "—" : fmtUSD(o.cost_per_doc * 1e5)}`],
      ],
      notes: [`${t.reviewer.docs_per_hour} docs/hour at $${t.reviewer.usd_per_hour}/hour; classifier compute not charged. A fixed coded sample does not scale with corpus size, so the per-100k figure is specific to a ${fmtInt(t.n_corpus)}-document collection.`],
    };
  }
  return {
    lines: [
      ["Time per 100k docs", fmtHours(o.hours_per_100k_docs)],
      ["Cost per 100k docs", o.cost_per_doc == null ? "—" : fmtUSD(o.cost_per_doc * 1e5)],
      ["Median time per doc", fmtMs(o.doc_latency_p50_ms)],
      ["Tokens in / out per doc", o.tokens_in_per_doc == null ? "—" : `${fmtInt(Math.round(o.tokens_in_per_doc))} / ${fmtInt(Math.round(o.tokens_out_per_doc ?? 0))}`],
    ],
    notes: [],
  };
}

// ------------------------------------------------------------------------------------------------

function useRows(v: View) {
  return useMemo(() => DATA.records.filter((r) => r.corpus === v.corpus && r.tag === v.tag && r.arm === v.arm), [v.corpus, v.tag, v.arm]);
}

function OpsCards({ recs, colorOf, nameOf, logos = true }: { recs: Rec[]; colorOf: (r: Rec) => string; nameOf: (r: Rec) => string; logos?: boolean }) {
  const time: BarItem[] = recs.map((r) => ({
    id: r.model, name: nameOf(r), color: colorOf(r), value: r.ops.hours_per_100k_docs, label: fmtHours(r.ops.hours_per_100k_docs), tip: opsLines(r), subset: r.subset,
  }));
  const cost: BarItem[] = recs.map((r) => ({
    id: r.model, name: nameOf(r), color: colorOf(r), value: r.ops.cost_per_doc == null ? null : r.ops.cost_per_doc * 1e5,
    label: r.ops.cost_per_doc == null ? "—" : fmtUSD(r.ops.cost_per_doc * 1e5), tip: opsLines(r), subset: r.subset,
  }));
  return (
    <>
      <div className="card">
        <div className="card-t">
          <h3>Review time</h3><span className="unit">per 100k documents, single stream</span>
          <span className="right"><Hint left text="Median wall-clock time of the model's own calls per document, one request at a time, scaled to 100,000 documents. In the 'all issues per call' arm that is one call per document; in 'one issue per call' it is the sum over issues. Every service accepts parallel requests, so absolute hours shrink with concurrency for all models alike; the ratios are the comparison. Laya and Gemma ran on one A100." /></span>
        </div>
        <OpsBars items={time} axis="hours" logos={logos} />
      </div>
      <div className="card">
        <div className="card-t">
          <h3>Cost</h3><span className="unit">per 100k documents, as paid</span>
          <span className="right"><Hint left text="What was actually paid to the vendor, summed over the model's decisions and scaled to 100,000 documents. OpenAI ran on flex pricing (half of list); Anthropic used prompt caching on the all-issues arm. Laya, Gemma and the keyword floor ran on rented hardware (about $2 per A100-hour) and show $0 here; their cost is the review-time panel." /></span>
        </div>
        <OpsBars items={cost} axis="US dollars" logos={logos} />
      </div>
    </>
  );
}

// ------------------------------------------------------------------------------------------------

function CompareSection({ v, explain }: { v: View; explain: (k: string) => void }) {
  const rows = useRows(v);
  const [on, setOn] = useState<Set<string>>(new Set(DEFAULT_ON));
  const primary = rows.filter((r) => r.primary);
  const byKind = KIND_ORDER.map((k) => ({ kind: k, recs: PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && r.kind === k) })).filter((g) => g.recs.length);
  const sel = PRIMARY.map((p) => primary.find((r) => r.model === p.key)).filter((r): r is Rec => !!r && on.has(r.model));
  const toggle = (k: string) => setOn((s) => { const n = new Set(s); n.has(k) ? n.delete(k) : n.add(k); return n; });
  const setGroup = (recs: Rec[], val: boolean) => setOn((s) => { const n = new Set(s); recs.forEach((r) => (val ? n.add(r.model) : n.delete(r.model))); return n; });

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    const meta = PRIMARY_BY_KEY[r.model];
    return { id: r.model, name: meta.short, color: meta.color, recall: p.recall, precision: p.precision, dashed: r.kind === "system1_ft", subset: r.subset, tip: qualityLines(r, v) };
  });

  return (
    <section className="section">
      <div className="sec-head">
        <span className="sub">Each dot is a model's recall and precision; the box around it is the 95% interval on both.</span>
        <ExplainButton label="how each model is asked" onClick={() => explain("jev@base")} />
      </div>
      <div className="pbar">
        {byKind.map((g) => (
          <div className="prow" key={g.kind}>
            <span className="plabel">
              <span>{KIND_LABEL[g.kind as Kind]}</span>
              <span className="an"><button onClick={() => setGroup(g.recs, true)}>all</button> · <button onClick={() => setGroup(g.recs, false)}>none</button></span>
            </span>
            {g.recs.map((r) => {
              const m = PRIMARY_BY_KEY[r.model];
              return (
                <button key={r.model} className={`chip${on.has(r.model) ? "" : " off"}`} onClick={() => toggle(r.model)} title={m.note} aria-pressed={on.has(r.model)}>
                  <span className="mark" style={{ color: m.color }}><Logo model={r.model} /></span>
                  <span className="nm" title={r.subset ? `scored on ${r.subset}` : undefined}>{m.short}{r.subset ? " *" : ""}</span>
                  <ExplainButton compact onClick={() => explain(r.model)} />
                </button>
              );
            })}
          </div>
        ))}
      </div>
      <div className="dash">
        <PRCard
          items={items} defaultChart="map" defaultZoom={true}
          hint="Recall: gold-responsive items the model flagged, over all gold-responsive items. Precision: flagged items that were gold-responsive, over all flagged. Intervals are 95% Wilson score intervals. Because every document in each test set carries a gold label, the recall interval is computed over the gold-positive set and the precision interval over the model's flagged set, rather than from a review sample. All metrics use the model's own label, not a tuned threshold."
        />
        <div className="stack">
          <OpsCards recs={sel} colorOf={(r) => PRIMARY_BY_KEY[r.model].color} nameOf={(r) => PRIMARY_BY_KEY[r.model].short} />
          <Consistency recs={sel} colorOf={(r) => PRIMARY_BY_KEY[r.model].color} nameOf={(r) => PRIMARY_BY_KEY[r.model].short} arm={v.arm} />
        </div>
      </div>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------

function AblationSection({ v, explain }: { v: View; explain: (k: string) => void }) {
  const rows = useRows(v);
  const [grp, setGrp] = useState("jev");
  const [off, setOff] = useState<Set<string>>(new Set());
  const G = ABLATION_GROUPS.find((g) => g.id === grp)!;
  const variants = useMemo(() => {
    const recs = rows.filter((r) => r.group === grp && r.variant);
    return VARIANT_ORDER.map((vv) => recs.find((r) => r.variant === vv)).filter((r): r is Rec => !!r);
  }, [rows, grp]);
  const sel = variants.filter((r) => !off.has(r.variant!));
  const color = (r: Rec) => variantColor(r.variant!, G.recipe);
  const name = (r: Rec) => VARIANT_LABEL[r.variant!] ?? r.variant!;
  const toggle = (vv: string) => setOff((s) => { const n = new Set(s); n.has(vv) ? n.delete(vv) : n.add(vv); return n; });

  const items: PRItem[] = sel.map((r) => {
    const p = pick(r, v.level, v.gray, v.issue);
    return { id: r.model, name: name(r), color: color(r), recall: p.recall, precision: p.precision, subset: r.subset, tip: qualityLines(r, v) };
  });

  return (
    <section className="section">
      <div className="sec-head">
        <span className="sub">Each variant changes a single lever from the default. The recipe is the configuration carried into Compare models.</span>
        <ExplainButton label="see the requests side by side" onClick={() => explain(`${grp}@base`)} />
      </div>
      <div className="pbar">
        <div className="prow">
          <span className="plabel"><span>Model</span></span>
          <span className="select">
            <select value={grp} onChange={(e) => { setGrp(e.target.value); setOff(new Set()); }}>
              {ABLATION_GROUPS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}
            </select>
          </span>
          <span className="pnote">{G.note}</span>
        </div>
        <div className="prow">
          <span className="plabel">
            <span>Configurations</span>
            <span className="an"><button onClick={() => setOff(new Set())}>all</button> · <button onClick={() => setOff(new Set(variants.map((r) => r.variant!)))}>none</button></span>
          </span>
          {variants.map((r) => (
            <button key={r.model} className={`chip${off.has(r.variant!) ? " off" : ""}`} onClick={() => toggle(r.variant!)} title={r.lever ?? undefined} aria-pressed={!off.has(r.variant!)}>
              <span className="sw" style={{ background: color(r) }} />
              <span className="nm" title={r.subset ? `scored on ${r.subset}` : undefined}>{name(r)}{r.subset ? " *" : ""}</span>
              {r.variant === G.recipe && <span className="star" title="recipe">★</span>}
              <ExplainButton compact onClick={() => explain(r.model)} />
            </button>
          ))}
          {variants.length === 0 && <span className="empty">No configurations of this model were run on this corpus and arm.</span>}
        </div>
      </div>
      <div className="dash">
        <PRCard
          items={items} defaultChart="ranked" defaultZoom={true}
          emptyText={variants.length ? "Select at least one configuration." : "No configurations available for this view."}
          logos={false}
          hint="Same measurement as on Compare models. Differences between configurations are usually smaller than between model families, so this card defaults to ranked rows with the axes fitted to the data; switch to map and 0–100% to see the same points on the scale used there. Hover a configuration for what the lever changes."
        />
        <div className="stack"><OpsCards recs={sel} colorOf={color} nameOf={name} logos={false} /></div>
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
          <Seg value={corpus} onChange={pickCorpus} options={CORPORA.map((c) => ({ id: c.id, label: c.label, title: c.short }))} />
        </Control>
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

      <div style={{ marginTop: 18, color: "var(--ink-2)", fontSize: 13, display: "flex", gap: 8, alignItems: "baseline", flexWrap: "wrap" }}>
        <span style={{ fontSize: 16, fontWeight: 500, color: "var(--ink)" }}>{meta.display}</span>
        <span style={{ color: "var(--ink-3)" }}>
          {fmtInt(meta.n_docs)} documents · {meta.n_issues} issues · {fmtInt(meta.n_pos_docs_any)} responsive to at least one ({fmtPct(meta.n_pos_docs_any / meta.n_docs, 0)}) · gold: {meta.gold}
        </span>
      </div>

      {pageId === "compare" ? <CompareSection v={v} explain={setExplain} /> : <AblationSection v={v} explain={setExplain} />}
      {explain && <ExplainModal initialKey={explain} initialCorpus={corpus} onClose={() => setExplain(null)} />}

      <details className="notes">
        <summary>Notes on method<span className="chev" /></summary>
        <footer className="foot">
        <div>
          <h4>What every model saw</h4>
          <p>The same document text, the same issue criteria and matter context, and returned a label plus a probability. Metrics use the model's own label. Jev and Laya rows are the default configuration unless marked recipe.</p>
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
          <p>A simulated reviewer (gold labels; 50 documents/hour at $65/hour) plus TF‑IDF and logistic regression, one model per issue and one for any‑issue relevance. TAR 1.0 codes a random sample and picks its cutoff by cross‑validation on that sample alone; TAR 2.0 is continuous active learning stopped after two consecutive batches under 5% relevant. Rows are the median of five random seeds (three for TREC). TREC rows are trained and reviewed over the full 286k collection and scored on the same evaluation set as the other models. The 90%‑reviewer variants miscode 10% of documents at random.</p>
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
