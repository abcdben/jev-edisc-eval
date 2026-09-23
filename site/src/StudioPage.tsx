import { useEffect, useRef, useState } from "react";
import { DATA, DEFAULT_CORPUS, DEFAULT_ON, corpusKey, issueLabel, siteCorpus, CORPORA } from "./data";
import { ModelPicker, useCompareItems, type Chart, type View } from "./App";
import { PRScatter } from "./components/PRScatter";
import { PRRail } from "./components/PRRail";
import { Control, Seg } from "./components/ui";

/**
 * Screenshot studio (studio.html → studio.tsx → this page; unlinked from the site): the Compare models recall/precision chart alone, on a plain
 * panel whose size you set, with every control (corpus, models, issue, map/ranked, axis range, size, theme, frame, legend) in the bars above and
 * none on the plot. Drag the panel's bottom-right corner or type a size; pick a preset for LinkedIn's usual aspect ratios. Nothing pulses and
 * nothing opens on click.
 */

type Preset = { id: string; label: string; w: number; h: number };
const PRESETS: Preset[] = [
  { id: "wide", label: "1200 × 675 (16:9)", w: 1200, h: 675 },
  { id: "link", label: "1200 × 627 (link card)", w: 1200, h: 627 },
  { id: "square", label: "1080 × 1080 (1:1)", w: 1080, h: 1080 },
  { id: "tall", label: "1080 × 1350 (4:5)", w: 1080, h: 1350 },
  { id: "banner", label: "1584 × 396 (banner)", w: 1584, h: 396 },
];

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, Math.round(n)));

export default function StudioPage() {
  const [corpus, setCorpusRaw] = useState(DEFAULT_CORPUS);
  const setCorpus = (c: string) => { setCorpusRaw(siteCorpus(c)); setIssue(null); };
  const [issue, setIssue] = useState<string | null>(null);
  const v: View = { corpus, tag: "", arm: "multi", gray: "all", level: "doc", issue };
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];
  const [on, setOn] = useState<Set<string>>(new Set(DEFAULT_ON));
  const { items } = useCompareItems(v, on);

  const [chart, setChart] = useState<Chart>("map");
  const [zoom, setZoom] = useState(true);
  const [logos, setLogos] = useState(true);
  const [legend, setLegend] = useState(true);
  const [frame, setFrame] = useState(true);
  const [theme, setTheme] = useState<"dark" | "light">(() => (localStorage.getItem("theme") as "dark" | "light") || "light");
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("theme", theme); }, [theme]);

  // Panel size in CSS pixels. The panel is also CSS-resizable by its corner; a ResizeObserver writes the dragged size back into the fields.
  // In the ranked view the height follows the rows, so only the width is synced and the chosen map height is kept for when the map returns.
  const [w, setW] = useState(PRESETS[0].w);
  const [h, setH] = useState(PRESETS[0].h);
  const plotRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef(chart);
  chartRef.current = chart;
  useEffect(() => {
    const el = plotRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const bw = el.offsetWidth, bh = el.offsetHeight;
      if (bw) setW((p) => (p === bw ? p : bw));
      if (bh && chartRef.current === "map") setH((p) => (p === bh ? p : bh));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const preset = PRESETS.find((p) => p.w === w && p.h === h)?.id ?? "custom";

  const emptyText = "Select at least one model.";
  return (
    <div className="page studio">
      <header className="masthead">
        <h1 className="title"><em>Studio ·</em> Jev vs Frontier LLMs</h1>
        <span className="studio-hint">Set the chart up here, then screenshot the panel below. Controls never draw on the panel.</span>
        <span className="theme"><Seg value={theme} onChange={setTheme} options={[{ id: "dark", label: "Dark" }, { id: "light", label: "Light" }]} /></span>
      </header>

      <div className="controls">
        <Control label="Corpus">
          <Seg value={corpus} onChange={setCorpus} options={CORPORA.map((c) => ({ id: c.id, label: c.label }))} />
        </Control>
        <ModelPicker v={v} on={on} setOn={setOn} />
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

      <div className="controls studio-row2">
        <Control label="View">
          <Seg value={chart} onChange={setChart} options={[{ id: "map", label: "map" }, { id: "ranked", label: "ranked" }]} />
        </Control>
        <Control label="Axes">
          <Seg value={zoom ? "zoom" : "full"} onChange={(z) => setZoom(z === "zoom")} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }]} />
        </Control>
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
            <input type="number" min={240} max={4000} step={10} value={h} onChange={(e) => setH(clamp(Number(e.target.value) || h, 240, 4000))} aria-label="height in pixels" disabled={chart === "ranked"} />
            <span className="unit">px{chart === "ranked" ? " · height follows the rows" : ""}</span>
          </span>
        </Control>
        <Control label="Panel">
          <Seg value={frame ? "card" : "plain"} onChange={(x) => setFrame(x === "card")} options={[{ id: "card", label: "framed" }, { id: "plain", label: "plain" }]} />
          <Seg value={legend ? "on" : "off"} onChange={(x) => setLegend(x === "on")} options={[{ id: "on", label: "legend" }, { id: "off", label: "no legend" }]} />
          <Seg value={logos ? "on" : "off"} onChange={(x) => setLogos(x === "on")} options={[{ id: "on", label: "logos" }, { id: "off", label: "names only" }]} />
        </Control>
      </div>

      <section className="section studio-stage">
        <div
          ref={plotRef}
          className={`studio-plot${frame ? " framed" : ""}${chart === "ranked" ? " auto" : ""}`}
          style={{ width: w, height: chart === "map" ? h : undefined }}
        >
          {chart === "map" && (
            <div className="studio-canvas">
              <PRScatter items={items} zoom={zoom} emptyText={emptyText} logos={logos} fill />
            </div>
          )}
          {chart === "ranked" && <PRRail items={items} zoom={zoom} sortBy="recall" logos={logos} />}
          {legend && chart === "map" && (
            <div className="legend-note">
              <span>Dot: point estimate. Shaded box: 95% interval on recall (width) and precision (height).</span>
              {items.some((i) => i.subset) && <span>* scored on a stratified subset</span>}
            </div>
          )}
        </div>
        <p className="studio-foot">Drag the panel's bottom-right corner to resize, or type a size above. {w} × {chart === "map" ? h : "auto"} px.</p>
      </section>
    </div>
  );
}
