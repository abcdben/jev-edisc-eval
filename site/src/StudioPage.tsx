import { useEffect, useRef, useState } from "react";
import { DATA, DEFAULT_CORPUS, DEFAULT_ON, PRIMARY_BY_KEY, corpusKey, costPerDoc, fmtInt, fmtPct, isDecider, issueLabel, pick, siteCorpus, starOf, CORPORA, type Rec } from "./data";
import { ModelPicker, useCompareItems, type Chart, type View } from "./App";
import { PRScatter, type PRDomain } from "./components/PRScatter";
import { PRRail } from "./components/PRRail";
import { detFor } from "./components/Consistency";
import { StudioBars, StudioScatter, type StudioRow, type StudioScatterPt } from "./components/StudioCharts";
import { Control, Seg } from "./components/ui";

/**
 * Screenshot studio (studio.html → studio.tsx → this page; unlinked from the site): one Compare models chart alone, on a plain panel whose size
 * you set, with every control (corpus, models, issue, plot and chart type, units, axis range, size, theme, frame, legend, style) in the bars above
 * and none on the plot. Plots: recall/precision (the site's map and ranked views), Cost, Speed and Stability (components/StudioCharts.tsx).
 * Drag the panel's bottom-right corner or type a size; pick a preset for LinkedIn's usual aspect ratios. Nothing pulses and nothing opens on click.
 */

type Preset = { id: string; label: string; w: number; h: number };
const PRESETS: Preset[] = [
  { id: "wide", label: "1200 × 675 (16:9)", w: 1200, h: 675 },
  { id: "link", label: "1200 × 627 (link card)", w: 1200, h: 627 },
  { id: "square", label: "1080 × 1080 (1:1)", w: 1080, h: 1080 },
  { id: "tall", label: "1080 × 1350 (4:5)", w: 1080, h: 1350 },
  { id: "banner", label: "1584 × 396 (banner)", w: 1584, h: 396 },
];

/** Plot style presets (styles.css `.studio-plot[data-style=…]`): every one but `site` fully specifies its own panel, ink, grid and model palette, so the masthead Dark/Light theme does not reach the panel. */
type PlotStyle = "site" | "journal" | "newsroom" | "linkedin" | "slate" | "economist";
const STYLES: { id: PlotStyle; label: string; title: string }[] = [
  { id: "site", label: "Site", title: "The site's own look; follows the Dark/Light theme" },
  { id: "journal", label: "Journal", title: "Academic figure: white, black hairline axes, serif labels, Okabe–Ito colorblind-safe palette" },
  { id: "newsroom", label: "Newsroom", title: "Editorial data graphic: warm greys, dotted grid, muted news palette" },
  { id: "linkedin", label: "LinkedIn", title: "LinkedIn brand: #0A66C2 blues for Jev, LinkedIn accent colours for the LLMs" },
  { id: "slate", label: "Slate", title: "Dark slate, Jev in one saturated accent, every LLM in a shade of grey" },
  { id: "economist", label: "Economist", title: "Financial weekly: red accent tab, thin grey rules, the Economist data palette" },
];
const isPlotStyle = (s: string | null): s is PlotStyle => STYLES.some((x) => x.id === s);

/** The four plots. `pr` is the site's recall/precision chart (map or ranked); the others are the studio's own bar, dot and scatter charts. */
type Plot = "pr" | "cost" | "speed" | "stability";
type CostChart = "bars" | "dots" | "scatter";
type CostUnit = "1k" | "100k" | "decision";
type SpeedChart = "bars" | "dots" | "throughput";
type SpeedUnit = "ms" | "s";
type StabChart = "bars" | "agree" | "dots";

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, Math.round(n)));
const COST_UNIT: Record<CostUnit, { mult: (r: Rec) => number; axis: string; short: string }> = {
  "1k": { mult: () => 1e3, axis: "US dollars per 1,000 documents", short: "per 1,000 docs" },
  "100k": { mult: () => 1e5, axis: "US dollars per 100,000 documents", short: "per 100,000 docs" },
  decision: { mult: (r) => (r.ops.n_decisions ? r.ops.n_docs / r.ops.n_decisions : 1), axis: "US dollars per decision (one document × one issue)", short: "per decision" },
};
/** Money at the precision the size calls for: "$5,000", "$12.3", "$0.14", "$0.000017". */
const fmtMoney = (v: number): string => (v === 0 ? "$0" : v >= 100 ? `$${fmtInt(Math.round(v))}` : v >= 1 ? `$${v.toFixed(v >= 10 ? 1 : 2)}` : v >= 0.01 ? `$${v.toFixed(2)}` : `$${(+v.toPrecision(2)).toString()}`);
const fmtMoneyTick = (v: number): string => (v >= 1 ? `$${fmtInt(Math.round(v))}` : `$${(+v.toPrecision(2)).toString()}`);
const fmtMsTick = (v: number): string => (v === 0 ? "0" : v < 1000 ? `${Math.round(v)} ms` : `${+(v / 1000).toFixed(2)} s`);
const fmtPctTick = (v: number): string => `${+(v * 100).toFixed(2)}%`;
const fmtLatency = (ms: number, unit: SpeedUnit) => (unit === "s" ? `${(ms / 1000).toFixed(2)} s` : `${fmtInt(Math.round(ms))} ms`);

export default function StudioPage() {
  const [corpus, setCorpusRaw] = useState(DEFAULT_CORPUS);
  const setCorpus = (c: string) => { setCorpusRaw(siteCorpus(c)); setIssue(null); };
  const [issue, setIssue] = useState<string | null>(null);
  const v: View = { corpus, tag: "", arm: "multi", gray: "all", level: "doc", issue };
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];
  const [on, setOn] = useState<Set<string>>(new Set(DEFAULT_ON));
  const { sel, items } = useCompareItems(v, on);

  const [plot, setPlot] = useState<Plot>("pr");
  const [chart, setChart] = useState<Chart>("map");
  const [costChart, setCostChart] = useState<CostChart>("bars");
  const [costUnit, setCostUnit] = useState<CostUnit>("1k");
  const [costScale, setCostScale] = useState<"linear" | "log">("linear");
  const [speedChart, setSpeedChart] = useState<SpeedChart>("bars");
  const [speedUnit, setSpeedUnit] = useState<SpeedUnit>("ms");
  const [stabChart, setStabChart] = useState<StabChart>("bars");
  const [stabSetting, setStabSetting] = useState<"default" | "t0">("default");
  const [hideUnmeasured, setHideUnmeasured] = useState(false);
  // Axes: the site's two modes, plus `custom`, explicit percent bounds per axis (the ranked view shares one range across both panels).
  const [axes, setAxes] = useState<"full" | "zoom" | "custom">("zoom");
  const [ax, setAx] = useState({ xlo: 50, xhi: 100, ylo: 50, yhi: 100 });
  const setBound = (k: keyof typeof ax) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const n = Number(e.target.value);
    if (Number.isFinite(n)) setAx((p) => ({ ...p, [k]: clamp(n, 0, 100) }));
  };
  const span = (lo: number, hi: number): [number, number] => (hi > lo ? [lo / 100, hi / 100] : [Math.min(lo, hi) / 100, Math.min(lo, hi) / 100 + 0.01]);
  const domain: PRDomain | undefined = axes === "custom" ? { x: span(ax.xlo, ax.xhi), y: span(ax.ylo, ax.yhi) } : undefined;
  const range: [number, number] | undefined = axes === "custom" ? span(ax.xlo, ax.xhi) : undefined;
  const zoom = axes === "zoom";
  const [logos, setLogos] = useState(true);
  const [legend, setLegend] = useState(true);
  const [frame, setFrame] = useState(true);
  const [theme, setTheme] = useState<"dark" | "light">(() => (localStorage.getItem("theme") as "dark" | "light") || "light");
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("theme", theme); }, [theme]);
  const [style, setStyle] = useState<PlotStyle>(() => { const s = localStorage.getItem("studio-style"); return isPlotStyle(s) ? s : "site"; });
  useEffect(() => { localStorage.setItem("studio-style", style); }, [style]);

  // Which charts fill the panel's height (the map-like ones); the row-based ones take their height from the rows (the panel's `auto` mode).
  const fills = (plot === "pr" && chart === "map") || (plot === "cost" && costChart === "scatter");

  // Panel size in CSS pixels. The panel is also CSS-resizable by its corner; a ResizeObserver writes the dragged size back into the fields.
  // In the row-based charts the height follows the rows, so only the width is synced and the chosen height is kept for when a filling chart returns.
  const [w, setW] = useState(PRESETS[0].w);
  const [h, setH] = useState(PRESETS[0].h);
  const plotRef = useRef<HTMLDivElement>(null);
  const fillsRef = useRef(fills);
  fillsRef.current = fills;
  useEffect(() => {
    const el = plotRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const bw = el.offsetWidth, bh = el.offsetHeight;
      if (bw) setW((p) => (p === bw ? p : bw));
      if (bh && fillsRef.current) setH((p) => (p === bh ? p : bh));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const preset = PRESETS.find((p) => p.w === w && p.h === h)?.id ?? "custom";

  // ---- rows for the studio's own charts, from the selected roster records (colours and short names from the roster, so Style presets apply) ----
  const base = (r: Rec) => ({ id: r.model, name: PRIMARY_BY_KEY[r.model].short, color: PRIMARY_BY_KEY[r.model].color, decider: isDecider(PRIMARY_BY_KEY[r.model].kind ?? r.kind), subset: starOf(r) });
  const cu = COST_UNIT[costUnit];
  const costRows: StudioRow[] = sel.map((r) => {
    const c = costPerDoc(r), val = c == null ? null : c * cu.mult(r);
    return { ...base(r), value: val, label: val == null ? "" : fmtMoney(val) };
  });
  const costPts: StudioScatterPt[] = sel.map((r) => { const c = costPerDoc(r); return { ...base(r), x: c == null ? null : c * cu.mult(r), y: pick(r, v.level, v.gray, v.issue).recall }; });
  const speedRows: StudioRow[] = sel.map((r) => {
    const p50 = r.ops.doc_latency_p50_ms;
    if (speedChart === "throughput") { const val = p50 == null ? null : 3.6e6 / p50; return { ...base(r), value: val, label: val == null ? "" : `${fmtInt(Math.round(val))} docs/h` }; }
    // Median only: the p95 tail whisker was dropped as noise for a headline chart.
    return { ...base(r), value: p50, label: p50 == null ? "" : fmtLatency(p50, speedUnit) };
  });
  // Stability: the card's rule. At t = 0 a decider keeps its default cell (no sampling control); an LLM without a t = 0 cell rejected the parameter.
  const isLLM = (r: Rec) => r.kind === "llm" || r.kind === "local_llm";
  const stabLbl = (p: number) => (p === 0 ? "0" : fmtPct(p, p < 0.001 ? 2 : 1));
  const stabCells = sel.map((r) => { const d = detFor(r, v.arm, "default"), t0 = detFor(r, v.arm, "t0"); return { r, d, c: stabSetting === "t0" ? (t0 ?? (isLLM(r) ? null : d)) : d }; });
  // "5 runs · 2,400 decisions" goes in the legend when every measured row shares it, on each row otherwise
  const runsOf = new Set(stabCells.filter((x) => x.c).map((x) => `${x.c!.cell.k} runs · ${fmtInt(x.c!.cell.n_decisions)} decisions`));
  const sameRuns = runsOf.size === 1 ? [...runsOf][0] : null;
  const stabAll: StudioRow[] = stabCells.map(({ r, d, c }) => {
    if (!c) return { ...base(r), value: null, label: "", empty: stabSetting === "t0" && d ? "API rejects temperature" : "not measured" };
    const [p, lo, hi] = c.pairwise, runs = `${c.cell.k} runs · ${fmtInt(c.cell.n_decisions)} decisions`;
    if (stabChart === "agree") return { ...base(r), value: 1 - p, lo: 1 - hi, hi: 1 - lo, label: p === 0 ? "100%" : fmtPct(1 - p, p < 0.001 ? 2 : 1), sub: `disagree ${stabLbl(p)}` };
    return { ...base(r), value: p, lo, hi, label: stabLbl(p), sub: sameRuns ? undefined : runs };
  });
  const stabRows = hideUnmeasured ? stabAll.filter((x) => x.value != null) : stabAll;
  const agreeLo = Math.min(1, ...stabRows.map((x) => (x.value == null ? 1 : (x.lo ?? x.value))));
  const agreeDomain: [number, number] = [Math.max(0, Math.floor((agreeLo - 0.003) * 200) / 200), 1];
  const stabHasT0 = sel.some((r) => detFor(r, v.arm, "t0"));

  const emptyText = "Select at least one model.";
  const measuredOn = DATA.determinism ? `${fmtInt(DATA.determinism.sample.n_docs)} Mallinckrodt emails` : "a fixed sample";
  const legendText = (): string[] => {
    if (plot === "pr") return chart === "map" ? ["Dot: point estimate. Shaded box: 95% interval on recall (width) and precision (height)."] : [];
    if (plot === "cost") {
      const basis = "Cost as paid for the benchmark run (OpenAI flex pricing, Anthropic prompt caching, Google and TypeSafe at list; GPU rows as A100 rental for their median latency)";
      if (costChart === "scatter") return [`${basis}, ${cu.short} on a log axis, against recall with its 95% interval (whisker).`];
      return [`${basis}, ${cu.short}${costChart === "dots" || costScale === "log" ? ", log axis" : ""}.`];
    }
    if (plot === "speed") {
      if (speedChart === "throughput") return ["Sequential documents per hour: 3,600,000 ÷ median wall-clock milliseconds per document, one request at a time. Every service accepts parallel requests, so compare ratios, not absolutes."];
      return [speedChart === "bars" ? "Bar: median latency per document, one request at a time." : "Dot: median latency per document, one request at a time, on a log axis."];
    }
    const t0 = stabSetting === "t0" ? " Temperature 0 where the API accepts it; deciders expose no sampling control." : "";
    const where = `Measured on ${measuredOn}${sameRuns ? ` (${sameRuns} per model)` : " scored 5 times"}; the same cells are shown for every corpus.`;
    if (stabChart === "agree") return [`Bar: agreement, the probability two identical runs give the same decision (1 − pairwise disagreement); whisker: 95% bootstrap interval. Axis zoomed to the measured range.${t0}`, where];
    return [`${stabChart === "bars" ? "Bar" : "Dot"}: probability two identical runs disagree on a decision (pairwise); whisker: 95% bootstrap interval over decisions.${t0}`, where];
  };
  const legendLines = legendText();
  const showIssue = plot === "pr" || (plot === "cost" && costChart === "scatter");

  return (
    <div className="page studio">
      <header className="masthead">
        <h1 className="title"><em>Studio ·</em> Jev vs Frontier LLMs</h1>
        <span className="studio-hint">Set the chart up here, then screenshot the panel below. Controls never draw on the panel.</span>
        <span className="theme"><Seg value={theme} onChange={setTheme} options={[{ id: "dark", label: "Dark" }, { id: "light", label: "Light" }]} /></span>
      </header>

      <div className="controls">
        <Control label="Plot">
          <Seg value={plot} onChange={setPlot} options={[{ id: "pr", label: "Recall / precision" }, { id: "cost", label: "Cost" }, { id: "speed", label: "Speed" }, { id: "stability", label: "Stability" }]} />
        </Control>
        <Control label="Corpus">
          <Seg value={corpus} onChange={setCorpus} options={CORPORA.map((c) => ({ id: c.id, label: c.label }))} />
        </Control>
        <ModelPicker v={v} on={on} setOn={setOn} />
        {showIssue && (
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
        )}
      </div>

      <div className="controls studio-row2">
        {plot === "pr" && (
          <>
            <Control label="View">
              <Seg value={chart} onChange={setChart} options={[{ id: "map", label: "map" }, { id: "ranked", label: "ranked" }]} />
            </Control>
            <Control label="Axes">
              <Seg value={axes} onChange={setAxes} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }, { id: "custom", label: "custom" }]} />
              {axes === "custom" && (
                <span className="studio-axes">
                  <span className="studio-size">
                    <span className="unit">{chart === "map" ? "recall" : "both panels"}</span>
                    <input type="number" min={0} max={100} step={5} value={ax.xlo} onChange={setBound("xlo")} aria-label="recall axis minimum, percent" />
                    <span className="x">–</span>
                    <input type="number" min={0} max={100} step={5} value={ax.xhi} onChange={setBound("xhi")} aria-label="recall axis maximum, percent" />
                    <span className="unit">%</span>
                  </span>
                  {chart === "map" && (
                    <span className="studio-size">
                      <span className="unit">precision</span>
                      <input type="number" min={0} max={100} step={5} value={ax.ylo} onChange={setBound("ylo")} aria-label="precision axis minimum, percent" />
                      <span className="x">–</span>
                      <input type="number" min={0} max={100} step={5} value={ax.yhi} onChange={setBound("yhi")} aria-label="precision axis maximum, percent" />
                      <span className="unit">%</span>
                    </span>
                  )}
                </span>
              )}
            </Control>
          </>
        )}
        {plot === "cost" && (
          <>
            <Control label="Chart">
              <Seg value={costChart} onChange={setCostChart} options={[{ id: "bars", label: "bars" }, { id: "dots", label: "dots · log" }, { id: "scatter", label: "cost vs recall" }]} />
              {costChart === "bars" && <Seg value={costScale} onChange={setCostScale} options={[{ id: "linear", label: "linear" }, { id: "log", label: "log" }]} />}
            </Control>
            <Control label="Units">
              <Seg value={costUnit} onChange={setCostUnit} options={[{ id: "1k", label: "$ per 1,000 docs" }, { id: "100k", label: "$ per 100,000 docs" }, { id: "decision", label: "$ per decision" }]} />
            </Control>
          </>
        )}
        {plot === "speed" && (
          <>
            <Control label="Chart">
              <Seg value={speedChart} onChange={setSpeedChart} options={[{ id: "bars", label: "bars" }, { id: "dots", label: "dots · log" }, { id: "throughput", label: "docs per hour" }]} />
            </Control>
            {speedChart !== "throughput" && (
              <Control label="Units">
                <Seg value={speedUnit} onChange={setSpeedUnit} options={[{ id: "ms", label: "ms per document" }, { id: "s", label: "s per document" }]} />
              </Control>
            )}
          </>
        )}
        {plot === "stability" && (
          <>
            <Control label="Chart">
              <Seg value={stabChart} onChange={setStabChart} options={[{ id: "bars", label: "disagreement bars" }, { id: "agree", label: "agreement · zoomed" }, { id: "dots", label: "dots" }]} />
            </Control>
            <Control label="Setting">
              <Seg value={stabSetting} onChange={setStabSetting} options={[{ id: "default", label: "default", title: "Vendor default sampling" }, { id: "t0", label: "t = 0", title: stabHasT0 ? "Temperature 0 where the API accepts it" : "No t = 0 cell among the selected models" }]} />
              <Seg value={hideUnmeasured ? "hide" : "show"} onChange={(x) => setHideUnmeasured(x === "hide")} options={[{ id: "show", label: "list unmeasured" }, { id: "hide", label: "hide unmeasured" }]} />
            </Control>
          </>
        )}
        <Control label="Size">
          <span className="select">
            <select value={preset} onChange={(e) => { const p = PRESETS.find((x) => x.id === e.target.value); if (p) { setW(p.w); setH(p.h); } }}>
              {PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              <option value="custom" disabled>custom</option>
            </select>
          </span>
          <span className="studio-size">
            <input type="number" min={320} max={4000} step={10} value={w} onChange={(e) => setW(clamp(Number(e.target.value) || w, 320, 4000))} aria-label="width in pixels" />
            <span className="x">×</span>
            <input type="number" min={240} max={4000} step={10} value={h} onChange={(e) => setH(clamp(Number(e.target.value) || h, 240, 4000))} aria-label="height in pixels" disabled={!fills} />
            <span className="unit">px{fills ? "" : " · height follows the rows"}</span>
          </span>
        </Control>
        <Control label="Panel">
          <Seg value={frame ? "card" : "plain"} onChange={(x) => setFrame(x === "card")} options={[{ id: "card", label: "framed" }, { id: "plain", label: "plain" }]} />
          <Seg value={legend ? "on" : "off"} onChange={(x) => setLegend(x === "on")} options={[{ id: "on", label: "legend" }, { id: "off", label: "no legend" }]} />
          <Seg value={logos ? "on" : "off"} onChange={(x) => setLogos(x === "on")} options={[{ id: "on", label: "logos" }, { id: "off", label: "names only" }]} />
        </Control>
        <Control label="Style">
          <Seg value={style} onChange={setStyle} options={STYLES.map((s) => ({ id: s.id, label: s.label, title: s.title }))} />
          {style !== "site" && <span className="studio-hint small">{STYLES.find((s) => s.id === style)?.title}; ignores Dark/Light.</span>}
        </Control>
      </div>

      <section className="section studio-stage">
        <div
          ref={plotRef}
          className={`studio-plot${frame ? " framed" : ""}${fills ? "" : " auto"}`}
          data-style={style}
          style={{ width: w, height: fills ? h : undefined }}
        >
          {plot === "pr" && chart === "map" && (
            <div className="studio-canvas">
              <PRScatter items={items} zoom={zoom} domain={domain} emptyText={emptyText} logos={logos} fill />
            </div>
          )}
          {plot === "pr" && chart === "ranked" && <PRRail items={items} zoom={zoom} range={range} sortBy="recall" logos={logos} />}
          {plot === "cost" && costChart === "scatter" && (
            <div className="studio-canvas">
              <StudioScatter pts={costPts} xLabel={`${cu.axis} (log)`} yLabel={v.issue ? `Recall · ${issueLabel(meta, v.issue).split(" · ")[0]}` : "Recall"} fmtX={fmtMoneyTick} logos={logos} emptyText={emptyText} />
            </div>
          )}
          {plot === "cost" && costChart !== "scatter" && (
            <StudioBars rows={costRows} kind={costChart === "dots" ? "dot" : "bar"} scale={costChart === "dots" ? "log" : costScale} axis={cu.axis + (costChart === "dots" || costScale === "log" ? " (log)" : "")} fmtTick={fmtMoneyTick} logos={logos} />
          )}
          {plot === "speed" && (
            <StudioBars
              rows={speedRows} kind={speedChart === "dots" ? "dot" : "bar"} scale={speedChart === "dots" ? "log" : "linear"} sort={speedChart === "throughput" ? "desc" : "asc"}
              axis={speedChart === "throughput" ? "sequential documents per hour (3,600,000 ÷ median ms per document)" : `median latency per document${speedChart === "dots" ? " (log)" : ""}`}
              fmtTick={speedChart === "throughput" ? (t) => fmtInt(Math.round(t)) : fmtMsTick} logos={logos}
            />
          )}
          {plot === "stability" && (
            <StudioBars
              rows={stabRows} kind={stabChart === "dots" ? "dot" : "bar"} sort={stabChart === "agree" ? "desc" : "asc"} domain={stabChart === "agree" ? agreeDomain : undefined}
              axis={stabChart === "agree" ? `agreement: probability two identical runs give the same decision${stabSetting === "t0" ? " · temperature 0" : ""}` : `probability two identical runs disagree${stabSetting === "t0" ? " · temperature 0" : ""}`}
              fmtTick={fmtPctTick} logos={logos}
            />
          )}
          {legend && legendLines.length > 0 && (
            <div className="legend-note">
              {legendLines.map((t, i) => <span key={i}>{t}</span>)}
              {plot === "pr" && chart === "map" && items.some((i) => i.subset) && <span>* scored on a stratified subset</span>}
              {plot !== "pr" && sel.some((r) => starOf(r)) && <span>* scored on a stratified subset</span>}
            </div>
          )}
        </div>
        <p className="studio-foot">Drag the panel's bottom-right corner to resize, or type a size above. {w} × {fills ? h : "auto"} px.</p>
      </section>
    </div>
  );
}
