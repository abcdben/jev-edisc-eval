import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { DATA, fmtInt, issueLabel, corpusKey, starOf } from "./data";
import { LATENCY_ITEMS, PRCard, Shell, costItems, useCompareItems, type Chart, type CompareProps } from "./App";
import { HoverProvider } from "./components/hover";
import { Hint, Seg } from "./components/ui";
import { StudioBars, StudioScatter } from "./components/StudioCharts";
import { DET_ITEMS } from "./components/Consistency";
import {
  COST_UNIT, costAxis, costCaption, costPts, costRows, fmtMoneyTick, fmtMsTick, fmtPctTick, speedAxis, speedCaption, speedRows, stabAxis, stabCaption, stabRows,
  type CostChart, type CostScale, type CostUnit, type SpeedChart, type SpeedUnit, type StabChart, type StabSetting,
} from "./opsRows";

/**
 * Variant B of the site (b.html → b.tsx → this page), for an A/B comparison with index.html. Everything is the shell App.tsx renders (masthead, control
 * bar, Compare configurations, modals, foot) except the Compare models section: instead of one recall/precision plot with the Speed, Cost and Stability
 * cards small beside it, a tab strip at the foot of the sticky control bar (Recall / precision · Cost · Speed · Stability) shows one full-width chart at a
 * time, each with its own controls in the card header. The Cost, Speed and Stability charts are the studio's full-size ones (components/StudioCharts.tsx;
 * rows and captions from opsRows.ts), with their rows clickable for the details modal like the A cards. The active tab lives in the URL hash
 * (#compare, #cost, #speed, #stability) so a link can open a tab; the corpus, models and issue controls sit above the tabs and survive a tab change.
 */

export type Tab = "pr" | "cost" | "speed" | "stability";
const TABS: { id: Tab; label: string; title: string }[] = [
  { id: "pr", label: "Recall / precision", title: "Recall against precision, as a map or ranked rows" },
  { id: "cost", label: "Cost", title: "Dollars as paid, per 1,000 or 100,000 documents or per decision" },
  { id: "speed", label: "Speed", title: "Median latency per document, or documents per hour" },
  { id: "stability", label: "Stability", title: "How often identical runs disagree" },
];
const tabHash = (t: Tab) => (t === "pr" ? "#compare" : `#${t}`);
const readTab = (): Tab => { const h = location.hash.slice(1); return h === "cost" || h === "speed" || h === "stability" ? h : "pr"; };

// The active tab reaches the section through a context rather than a prop, so the section component passed to the shell is one stable function and
// its per-tab control state (chart type, units…) survives a tab change.
const TabContext = createContext<Tab>("pr");

export default function AppB() {
  const [tab, setTabRaw] = useState<Tab>(readTab);
  useEffect(() => {
    const onHash = () => setTabRaw(readTab());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  const setTab = (t: Tab) => { history.replaceState(null, "", tabHash(t)); setTabRaw(t); };
  const tabs = (
    <div className="cmp-tabs">
      <Seg value={tab} onChange={setTab} options={TABS} />
    </div>
  );
  const mast = <a className="variant" href="./index.html" title="The A layout: one recall/precision plot with the Speed, Cost and Stability cards beside it">Variant B · view A</a>;
  return (
    <TabContext.Provider value={tab}>
      <Shell Compare={CompareTabs} mast={mast} controlsTail={tabs} compareHash={tabHash(tab)} />
    </TabContext.Provider>
  );
}

const SUBSET_NOTE = "* scored on a stratified subset";

/** The Compare models section of B: the active tab's chart alone, full width, with that chart's controls in its card header. */
function CompareTabs({ v, on, explain }: CompareProps) {
  const tab = useContext(TabContext);
  const { sel, items } = useCompareItems(v, on);
  const [chart, setChart] = useState<Chart>("map");
  const [costChart, setCostChart] = useState<CostChart>("bars");
  const [costUnit, setCostUnit] = useState<CostUnit>("100k");
  const [costScale, setCostScale] = useState<CostScale>("linear");
  const [speedChart, setSpeedChart] = useState<SpeedChart>("bars");
  const [speedUnit, setSpeedUnit] = useState<SpeedUnit>("ms");
  const [stabChart, setStabChart] = useState<StabChart>("bars");
  const [stabSetting, setStabSetting] = useState<StabSetting>("default");
  const [hideUnmeasured, setHideUnmeasured] = useState(false);
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];
  const subset = sel.some((r) => starOf(r));
  // the chart's legend line, the subset star and how to reach the details modal (the A cards say it in their hover tooltips; these charts have none)
  const caption = (lines: string[], what: "row" | "mark" = "row") => (
    <div className="legend-note">
      {lines.map((t, i) => <span key={i}>{t}</span>)}
      {subset && <span>{SUBSET_NOTE}</span>}
      <span>Click a {what} for the model's details.</span>
    </div>
  );

  let card: ReactNode;
  if (tab === "pr") {
    // taller than A's map (380), which shares its height with the side stack: alone across the page a 620 px plot keeps the interval boxes near square
    card = <PRCard items={items} chart={chart} onChart={setChart} defaultZoom={true} explain={explain} pulse ranked="rail" sig={v.corpus} height={620} />;
  } else if (tab === "cost") {
    const cu = COST_UNIT[costUnit];
    card = (
      <div className={`card${costChart === "scatter" ? " fill" : ""}`}>
        <div className="card-t">
          <h3>Cost</h3><span className="unit">{cu.short}</span>
          <span className="right">
            <Seg value={costChart} onChange={setCostChart} options={[{ id: "bars", label: "bars" }, { id: "dots", label: "dots · log" }, { id: "scatter", label: "cost vs recall" }]} />
            {costChart === "bars" && <Seg value={costScale} onChange={setCostScale} options={[{ id: "linear", label: "linear" }, { id: "log", label: "log" }]} />}
            <Seg value={costUnit} onChange={setCostUnit} options={[{ id: "1k", label: "per 1,000 docs" }, { id: "100k", label: "per 100,000 docs" }, { id: "decision", label: "per decision" }]} />
            <Hint items={costItems(sel)} more="About" />
          </span>
        </div>
        {costChart === "scatter" ? (
          <div className="chart-fill" style={{ minHeight: 520 }}>
            <StudioScatter pts={costPts(sel, v, costUnit)} xLabel={`${cu.axis} (log)`} yLabel={v.issue ? `Recall · ${issueLabel(meta, v.issue).split(" · ")[0]}` : "Recall"} fmtX={fmtMoneyTick} onSelect={explain} />
          </div>
        ) : (
          <StudioBars rows={costRows(sel, costUnit)} kind={costChart === "dots" ? "dot" : "bar"} scale={costChart === "dots" ? "log" : costScale} axis={costAxis(costChart, costUnit, costScale)} fmtTick={fmtMoneyTick} onSelect={explain} />
        )}
        {caption(costCaption(costChart, costUnit, costScale), costChart === "scatter" ? "mark" : "row")}
      </div>
    );
  } else if (tab === "speed") {
    card = (
      <div className="card">
        <div className="card-t">
          <h3>Speed</h3><span className="unit">{speedChart === "throughput" ? "sequential documents per hour" : "median latency per document"}</span>
          <span className="right">
            <Seg value={speedChart} onChange={setSpeedChart} options={[{ id: "bars", label: "bars" }, { id: "dots", label: "dots · log" }, { id: "throughput", label: "docs per hour" }]} />
            {speedChart !== "throughput" && <Seg value={speedUnit} onChange={setSpeedUnit} options={[{ id: "ms", label: "ms" }, { id: "s", label: "s" }]} />}
            <Hint items={LATENCY_ITEMS} more="About" />
          </span>
        </div>
        <StudioBars
          rows={speedRows(sel, speedChart, speedUnit)} kind={speedChart === "dots" ? "dot" : "bar"} scale={speedChart === "dots" ? "log" : "linear"} sort={speedChart === "throughput" ? "desc" : "asc"}
          axis={speedAxis(speedChart)} fmtTick={speedChart === "throughput" ? (t) => fmtInt(Math.round(t)) : fmtMsTick} onSelect={explain}
        />
        {caption(speedCaption(speedChart))}
      </div>
    );
  } else {
    const stab = stabRows(sel, v.arm, stabChart, stabSetting, hideUnmeasured);
    const det = DATA.determinism;
    const runs = det?.cells.find((c) => c.setting === "default")?.k ?? 5;
    card = (
      <div className="card">
        <div className="card-t">
          <h3>Stability</h3>
          <span className="unit">{det ? `how often ${runs} identical runs on ${fmtInt(det.sample.n_docs)} emails disagree` : "not measured"}</span>
          <span className="right">
            <Seg value={stabChart} onChange={setStabChart} options={[{ id: "bars", label: "disagreement bars" }, { id: "agree", label: "agreement · zoomed" }, { id: "dots", label: "dots" }]} />
            <Seg value={stabSetting} onChange={setStabSetting} options={[{ id: "default", label: "default", title: "Vendor default sampling" }, { id: "t0", label: "t = 0", title: stab.hasT0 ? "Temperature 0 where the API accepts it" : "No t = 0 cell among the selected models" }]} />
            <Seg value={hideUnmeasured ? "hide" : "show"} onChange={(x) => setHideUnmeasured(x === "hide")} options={[{ id: "show", label: "list unmeasured" }, { id: "hide", label: "hide unmeasured" }]} />
            <Hint items={DET_ITEMS} more="About" />
          </span>
        </div>
        <StudioBars
          rows={stab.rows} kind={stabChart === "dots" ? "dot" : "bar"} sort={stabChart === "agree" ? "desc" : "asc"} domain={stabChart === "agree" ? stab.agreeDomain : undefined}
          axis={stabAxis(stabChart, stabSetting)} fmtTick={fmtPctTick} onSelect={explain}
        />
        {caption(stabCaption(stabChart, stabSetting, stab.sameRuns))}
      </div>
    );
  }

  // `.dash.ranked` spans the one card across the full width (the ranked layout of A's dashboard, without the side stack). Keyed on the tab so a
  // tab change mounts a fresh card: the Cost, Speed and Stability cards share one shape, and React would otherwise keep the previous card's
  // Hint (ui.tsx), whose popover title is read from the card heading once, on mount.
  return (
    <section className="section cmp-full">
      <HoverProvider>
        <div className="dash ranked" key={tab}>{card}</div>
      </HoverProvider>
    </section>
  );
}