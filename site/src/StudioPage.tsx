import { useEffect, useRef, useState } from "react";
import { DATA, DEFAULT_CORPUS, DEFAULT_ON, PRIMARY_BY_KEY, corpusKey, costPerDoc, fmtInt, fmtPct, isDecider, issueLabel, pick, siteCorpus, starOf, CORPORA, type Rec } from "./data";
import { ModelPicker, useCompareItems, type Chart, type View } from "./App";
import { BOX_MODES, MARK_SHAPES, PRScatter, isBoxMode, type BoxMode, type LabelsMode, type MarkShape, type PRDomain } from "./components/PRScatter";
import { PRRail } from "./components/PRRail";
import { detFor } from "./components/Consistency";
import { StudioBars, StudioScatter, type StudioRow, type StudioScatterPt } from "./components/StudioCharts";
import { Control, Seg } from "./components/ui";
import { copyPng, downloadBlob, renderPanelPng, slug, type ExportBackground } from "./exportPng";
import { PALETTES, isPaletteId, toHex, toVars, varOf, type PaletteId } from "./palettes";

/**
 * Screenshot studio (studio.html → studio.tsx → this page; unlinked from the site): one Compare models chart alone, on a plain panel whose size
 * you set, with every control (corpus, models, issue, plot and chart type, units, axis range, size, theme, frame, legend, style and a custom colour scheme
 * you can save, load, export and import, model colours) in the bars above and none on the plot. Plots: recall/precision (the site's map and ranked views), Cost, Speed and Stability (components/StudioCharts.tsx).
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

/**
 * Plot style presets (styles.css `.studio-plot[data-style=…]`): every one but `site` fully specifies its own panel, ink, grid and model palette, so the masthead
 * Dark/Light theme does not reach the panel. `custom` has no CSS block: its variables are the user's (the scheme editor below), written as inline custom
 * properties on the `.studio-scheme` wrapper around the panel, so the preset CSS, the high-contrast block and the PNG export read them unchanged;
 * the slider variables alone (SCHEME_SLIDERS) go inline on the panel itself, so the high-contrast block's own alphas do not overrule the user's.
 */
type PlotStyle = "site" | "journal" | "newsroom" | "linkedin" | "slate" | "economist" | "epoch" | "custom";
const STYLES: { id: PlotStyle; label: string; title: string }[] = [
  { id: "site", label: "Site", title: "The site's own look; follows the Dark/Light theme" },
  { id: "journal", label: "Journal", title: "Academic figure: white, black hairline axes, serif labels, Okabe–Ito colorblind-safe palette" },
  { id: "newsroom", label: "Newsroom", title: "Editorial data graphic: warm greys, dotted grid, muted news palette" },
  { id: "linkedin", label: "LinkedIn", title: "LinkedIn brand: #0A66C2 blues for Jev, LinkedIn accent colours for the LLMs" },
  { id: "slate", label: "Slate", title: "Dark slate, Jev in one saturated accent, every LLM in a shade of grey" },
  { id: "economist", label: "Economist", title: "Financial weekly: red accent tab, thin grey rules, the Economist data palette" },
  { id: "epoch", label: "Epoch", title: "Epoch AI-style chart: white, horizontal hairline grid only, flat saturated dots, no interval boxes; pairs with Labels → legend" },
  { id: "custom", label: "Custom", title: "Your own scheme: starts as a copy of the preset that was on, editable below, saved by name" },
];
const isPlotStyle = (s: string | null): s is PlotStyle => STYLES.some((x) => x.id === s);

/**
 * Custom scheme (Style → Custom): the panel variables every preset block defines, exposed in the editor row, plus `--bg`, the page behind the panel
 * (painted by the stage while Custom is on; the PNG export is the panel alone and never shows it). Colours: the surface and ink set, then one
 * per roster model through the custom property its colour is (data.ts ALL_PRIMARY `var(--…)`, palettes.ts varOf). Sliders: the interval-box fill
 * opacity (which also sets the hatch lines' in the hatched Boxes modes, PRScatter.tsx BoxMode), the box outline width in px and the bar fill opacity.
 * `--sans` is the panel face. A colour's text field takes any CSS colour (`transparent` for no grid included); the native picker beside it shows the nearest hex.
 */
type SchemeVar = { v: string; label: string };
const SCHEME_SURFACE: SchemeVar[] = [
  { v: "--bg", label: "page" }, { v: "--panel", label: "panel" }, { v: "--ink", label: "ink" }, { v: "--ink-2", label: "ink 2" }, { v: "--ink-3", label: "ink 3" }, { v: "--ink-4", label: "ink 4" },
  { v: "--line", label: "line" }, { v: "--line-2", label: "line 2" }, { v: "--grid", label: "grid" }, { v: "--dots", label: "dots" }, { v: "--axis", label: "axis" }, { v: "--hl", label: "highlight" },
];
const SCHEME_MODELS: SchemeVar[] = Object.entries(PRIMARY_BY_KEY).flatMap(([k, m]) => { const v = varOf(k); return v ? [{ v, label: m.short }] : []; });
/** `dflt` is shown, and drawn, while the scheme has no value for the variable (the charts' own fallback). */
const SCHEME_SLIDERS: (SchemeVar & { min: number; max: number; step: number; dflt: number; title: string })[] = [
  { v: "--box-alpha", label: "box fill", min: 0, max: 0.6, step: 0.01, dflt: 0.14, title: "Opacity of the 95% interval boxes on the recall/precision map: the shade of a filled box, or the lines of a hatched one (Boxes control)" },
  { v: "--box-stroke-w", label: "outline px", min: 0, max: 3, step: 0.25, dflt: 0.75, title: "Width of the interval boxes' outline, in px (Boxes → outline or hatched + outline; also a preset's own hairline, as Journal's)" },
  { v: "--bar-alpha", label: "bar fill", min: 0.1, max: 1, step: 0.01, dflt: 0.55, title: "Fill opacity of the bars (Cost, Speed and Stability bar charts)" },
];
// --grid-x and --axis-y (vertical gridlines, y-axis line; unset they follow --grid / --axis) and --box-stroke (a preset's outline opacity in the filled and hatched
// Boxes modes; Journal's hairline) have no control but are copied, saved and imported, so a Custom made from Epoch keeps its horizontal-only grid
const SCHEME_VARS = new Set([...SCHEME_SURFACE, ...SCHEME_MODELS, ...SCHEME_SLIDERS].map((x) => x.v).concat("--sans", "--grid-x", "--axis-y", "--box-stroke"));
type Vars = Record<string, string>;
const isVars = (o: unknown): o is Vars => !!o && typeof o === "object" && !Array.isArray(o) && Object.values(o).every((x) => typeof x === "string");
const isSchemes = (o: unknown): o is Record<string, Vars> => !!o && typeof o === "object" && !Array.isArray(o) && Object.values(o).every(isVars);
const readJson = <T,>(key: string, ok: (o: unknown) => o is T, dflt: T): T => { try { const o: unknown = JSON.parse(localStorage.getItem(key) || "null"); return ok(o) ? o : dflt; } catch { return dflt; } };
/** Only the editor's variables, as short strings: what a saved or imported scheme may set on the panel. */
const cleanVars = (o: Vars): Vars => Object.fromEntries(Object.entries(o).filter(([k, v]) => SCHEME_VARS.has(k) && v.length <= 200));
/** A scheme file as Export JSON writes it (`{ name, vars }`), a bare variable map, or a `{ [name]: vars }` map (the localStorage form); null if none of those. */
const parseSchemeFile = (text: string): Record<string, Vars> | null => {
  let o: unknown; try { o = JSON.parse(text); } catch { return null; }
  if (!o || typeof o !== "object") return null;
  const r = o as Record<string, unknown>;
  if (isVars(r.vars)) return { [typeof r.name === "string" && r.name.trim() ? r.name.trim() : "imported"]: cleanVars(r.vars) };
  if (isVars(r)) return { imported: cleanVars(r) };
  if (isSchemes(r)) return Object.fromEntries(Object.entries(r).map(([k, v]) => [k, cleanVars(v)]));
  return null;
};
/** Relative luminance of a hex colour, 0–1. */
const luminance = (hex: string): number => { const c = (i: number) => parseInt(hex.slice(i, i + 2), 16) / 255; return 0.2126 * c(1) + 0.7152 * c(3) + 0.0722 * c(5); };

/** One scheme colour: the native picker (nearest hex) beside a text field that takes any CSS colour and commits once the browser accepts it. */
function SchemeColor({ v, label, value, onChange }: { v: string; label: string; value: string; onChange: (val: string) => void }) {
  const [txt, setTxt] = useState(value);
  useEffect(() => setTxt(value), [value]);
  const type = (t: string) => { setTxt(t); const c = t.trim(); if (c && CSS.supports("color", c)) onChange(c); };
  return (
    <span className="studio-swatch" title={`${v}: ${value}`}>
      <input type="color" value={toHex(value) ?? "#000000"} onChange={(e) => onChange(e.target.value)} aria-label={`${label} colour`} />
      <input type="text" className="hex" value={txt} onChange={(e) => type(e.target.value)} onBlur={() => setTxt(value)} spellCheck={false} aria-label={`${label} colour as CSS`} />
      <span>{label}</span>
    </span>
  );
}

/** Mark sizes (Mark size control): the multiplier on every point mark and vendor glyph, written to the panel as --mark-user (PRScatter.tsx Mark, GLYPH_SCALE) and passed to the scatters so their label placement keeps clear of the larger mark. High contrast's own 1.3 (--mark-scale / --r-add) multiplies on top. */
type MarkSize = "s" | "m" | "l" | "xl";
const MARK_SCALE: Record<MarkSize, number> = { s: 0.75, m: 1, l: 1.5, xl: 2.2 };
const isMarkSize = (s: string | null): s is MarkSize => s != null && s in MARK_SCALE;
const isMarkShape = (s: string | null): s is MarkShape => MARK_SHAPES.some((m) => m.id === s);

/** Text sizes: one factor on every font size in the panel (axis titles, ticks, names, values, point labels, legend note), passed to the charts as `textScale`, which also scales their label-width estimates and margins. M is the site's own size. */
type TextSize = "s" | "m" | "l" | "xl";
const TEXT_SCALE: Record<TextSize, number> = { s: 0.9, m: 1, l: 1.2, xl: 1.45 };
const isTextSize = (s: string | null): s is TextSize => s != null && s in TEXT_SCALE;
/** Contrast: `high` (styles.css .studio-plot[data-contrast="high"]) puts every label in full ink, thickens axes and whiskers, raises the bar and box alphas and enlarges the marks, on top of whichever Style preset is on. */
type Contrast = "normal" | "high";
/** Colors (palettes.ts): `style` leaves the Style preset's own model colours; a palette id writes that palette over them; `custom` writes the user's swatches, seeded from whatever was showing when they switched. */
type ColorMode = "style" | PaletteId | "custom";
const isColorMode = (s: string | null): s is ColorMode => s === "style" || s === "custom" || isPaletteId(s);
const readCustom = (): Record<string, string> => { try { const o = JSON.parse(localStorage.getItem("studio-colors-custom") || "{}"); return o && typeof o === "object" ? o : {}; } catch { return {}; } };

/** PNG export scale: device pixels per CSS pixel of the panel (a 1200 × 675 panel at 2× is a 2400 × 1350 PNG). */
type ExportScale = "1" | "2" | "3";
const isExportScale = (s: string | null): s is ExportScale => s === "1" || s === "2" || s === "3";

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
  // Leader lines (PRScatter.tsx / StudioCharts.tsx `leaders`): a hairline from a label the placement pushed away from its mark back to the mark.
  const [leaders, setLeaders] = useState(() => localStorage.getItem("studio-leaders") === "on");
  useEffect(() => { localStorage.setItem("studio-leaders", leaders ? "on" : "off"); }, [leaders]);
  // Labels (PRScatter.tsx LabelsMode): names beside the marks, or a legend row at the top of the panel and no point labels.
  const [labelsMode, setLabelsMode] = useState<LabelsMode>(() => (localStorage.getItem("studio-labels") === "legend" ? "legend" : "beside"));
  useEffect(() => { localStorage.setItem("studio-labels", labelsMode); }, [labelsMode]);
  // Marks: the point shape when logos are off (the glyph stands in for it otherwise), and the size of whichever is drawn.
  const [mark, setMark] = useState<MarkShape>(() => { const s = localStorage.getItem("studio-mark"); return isMarkShape(s) ? s : "dot"; });
  useEffect(() => { localStorage.setItem("studio-mark", mark); }, [mark]);
  const [markSize, setMarkSize] = useState<MarkSize>(() => { const s = localStorage.getItem("studio-mark-scale"); return isMarkSize(s) ? s : "m"; });
  useEffect(() => { localStorage.setItem("studio-mark-scale", markSize); }, [markSize]);
  const ms = MARK_SCALE[markSize];
  // Boxes (PRScatter.tsx BoxMode): how the map draws the 95% interval boxes: filled, hatched, outline only, or hatched inside an outline.
  const [boxes, setBoxes] = useState<BoxMode>(() => { const s = localStorage.getItem("studio-boxes"); return isBoxMode(s) ? s : "filled"; });
  useEffect(() => { localStorage.setItem("studio-boxes", boxes); }, [boxes]);
  const boxOutlined = boxes === "outline" || boxes === "hatched-outline";
  const [theme, setTheme] = useState<"dark" | "light">(() => (localStorage.getItem("theme") as "dark" | "light") || "light");
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("theme", theme); }, [theme]);
  const [style, setStyle] = useState<PlotStyle>(() => { const s = localStorage.getItem("studio-style"); return isPlotStyle(s) ? s : "site"; });
  useEffect(() => { localStorage.setItem("studio-style", style); }, [style]);

  // Custom scheme: the variables on the panel (`studio-custom`), the schemes saved by name (`studio-schemes`) and the name in the field / the
  // saved scheme selected (`studio-scheme`, one value: the select shows it while it matches a saved name).
  const [scheme, setScheme] = useState<Vars>(() => readJson("studio-custom", isVars, {}));
  useEffect(() => { localStorage.setItem("studio-custom", JSON.stringify(scheme)); }, [scheme]);
  const [schemes, setSchemes] = useState<Record<string, Vars>>(() => readJson("studio-schemes", isSchemes, {}));
  useEffect(() => { localStorage.setItem("studio-schemes", JSON.stringify(schemes)); }, [schemes]);
  const [schemeName, setSchemeName] = useState(() => localStorage.getItem("studio-scheme") ?? "");
  useEffect(() => { localStorage.setItem("studio-scheme", schemeName); }, [schemeName]);
  const [showModels, setShowModels] = useState(false);
  const [scMsg, setScMsg] = useState<string | null>(null);
  const scTimer = useRef(0);
  const say = (msg: string) => { setScMsg(msg); window.clearTimeout(scTimer.current); scTimer.current = window.setTimeout(() => setScMsg(null), 1800); };
  const setVar = (v: string, val: string) => setScheme((p) => ({ ...p, [v]: val }));
  const savedName = schemeName.trim() in schemes ? schemeName.trim() : "";
  const saveScheme = () => {
    const n = schemeName.trim();
    if (!n) { say("Name the scheme first."); return; }
    setSchemes((p) => ({ ...p, [n]: { ...scheme } }));
    setSchemeName(n);
    say(n in schemes ? `Overwrote “${n}”` : `Saved “${n}”`);
  };
  const loadScheme = (n: string) => { const s = schemes[n]; if (!s) return; setScheme({ ...s }); setSchemeName(n); };
  const deleteScheme = () => { if (!savedName) return; setSchemes((p) => { const q = { ...p }; delete q[savedName]; return q; }); say(`Deleted “${savedName}”`); };
  const exportScheme = () => {
    const n = schemeName.trim() || "scheme";
    downloadBlob(new Blob([JSON.stringify({ name: n, vars: scheme }, null, 2)], { type: "application/json" }), `${slug(n) || "scheme"}.json`);
  };
  const importScheme = async (file: File | undefined) => {
    if (!file) return;
    const got = parseSchemeFile(await file.text());
    const names = got ? Object.keys(got) : [];
    if (!got || !names.length) { say("Not a scheme file."); return; }
    setSchemes((p) => ({ ...p, ...got }));
    setScheme({ ...got[names[0]] });
    setSchemeName(names[0]);
    say(names.length === 1 ? `Imported “${names[0]}”` : `Imported ${names.length} schemes`);
  };
  const [text, setText] = useState<TextSize>(() => { const s = localStorage.getItem("studio-text"); return isTextSize(s) ? s : "m"; });
  useEffect(() => { localStorage.setItem("studio-text", text); }, [text]);
  const ts = TEXT_SCALE[text];
  const [contrast, setContrast] = useState<Contrast>(() => (localStorage.getItem("studio-contrast") === "high" ? "high" : "normal"));
  useEffect(() => { localStorage.setItem("studio-contrast", contrast); }, [contrast]);

  // Model colours: a palette over the Style preset, or per-model swatches. Dark panels (Slate, or Site in Dark) get the palette lifted (palettes.ts forDark).
  const [colorMode, setColorMode] = useState<ColorMode>(() => { const s = localStorage.getItem("studio-colors"); return isColorMode(s) ? s : "style"; });
  useEffect(() => { localStorage.setItem("studio-colors", colorMode); }, [colorMode]);
  const [custom, setCustom] = useState<Record<string, string>>(readCustom);
  useEffect(() => { localStorage.setItem("studio-colors-custom", JSON.stringify(custom)); }, [custom]);
  const customPanelHex = style === "custom" ? toHex(scheme["--panel"] ?? "") : null;
  const darkPanel = customPanelHex ? luminance(customPanelHex) < 0.4 : style === "slate" || (style === "site" && theme === "dark");
  const colorVars: Record<string, string> = colorMode === "style" ? {} : colorMode === "custom" ? toVars(custom, false) : toVars(PALETTES.find((p) => p.id === colorMode)!.colors, darkPanel);
  // The scheme's slider values, written inline on the panel itself (the rest of the scheme sits on the wrapper): the panel's own [data-contrast="high"]
  // block sets --box-alpha and --bar-alpha, and would otherwise silence the sliders whenever Contrast is high.
  const sliderVars: Record<string, string> = style === "custom" ? Object.fromEntries(SCHEME_SLIDERS.flatMap((x) => (scheme[x.v] ? [[x.v, scheme[x.v]]] : []))) : {};
  /**
   * Every scheme variable as a `.studio-plot` in `forStyle` resolves it, with the Colors layer on and no contrast override: read off a hidden probe
   * panel, not the live one, because in high contrast the live panel's --ink-2, --grid… are color-mix() expressions that the editor cannot show.
   */
  const presetVars = (forStyle: PlotStyle): Vars => {
    const probe = document.createElement("div");
    probe.className = "studio-plot";
    probe.dataset.style = forStyle;
    Object.assign(probe.style, { position: "fixed", left: "-9999px", top: "0", width: "10px", height: "10px" } as Partial<CSSStyleDeclaration>);
    for (const [k, val] of Object.entries(colorVars)) probe.style.setProperty(k, val);
    document.body.appendChild(probe);
    const cs = getComputedStyle(probe), out: Vars = {};
    for (const v of SCHEME_VARS) { const val = cs.getPropertyValue(v).trim(); if (val) out[v] = val; }
    probe.remove();
    return out;
  };
  // Entering Custom copies the preset that was on, so the editor starts from real values; a reload into Custom with nothing stored copies Site.
  const onStyle = (s: PlotStyle) => { if (s === "custom" && style !== "custom") setScheme(presetVars(style)); setStyle(s); };
  useEffect(() => { if (style === "custom" && !Object.keys(scheme).length) setScheme(presetVars("site")); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  /** Every roster model's colour as the panel currently resolves it (the preset's, or the palette or swatch over it). */
  const currentColors = (): Record<string, string> => {
    const el = plotRef.current, out: Record<string, string> = {};
    if (!el) return out;
    const cs = getComputedStyle(el);
    for (const k of Object.keys(PRIMARY_BY_KEY)) { const v = varOf(k); const hex = v ? toHex(cs.getPropertyValue(v)) : null; if (hex) out[k] = hex; }
    return out;
  };
  const onColorMode = (m: ColorMode) => {
    // Entering custom starts from the colours on screen, so "pick a palette, then tweak" works.
    if (m === "custom" && colorMode !== "custom") setCustom(currentColors());
    setColorMode(m);
  };
  const resetCustom = () => { setCustom({}); setColorMode("style"); };

  // PNG export (exportPng.ts): the panel as shown, minus frame, corner radius and resize grip, at 1–3× on the panel colour or transparent.
  const [exScale, setExScale] = useState<ExportScale>(() => { const s = localStorage.getItem("studio-export-scale"); return isExportScale(s) ? s : "2"; });
  useEffect(() => { localStorage.setItem("studio-export-scale", exScale); }, [exScale]);
  const [exBg, setExBg] = useState<ExportBackground>(() => (localStorage.getItem("studio-export-bg") === "transparent" ? "transparent" : "panel"));
  useEffect(() => { localStorage.setItem("studio-export-bg", exBg); }, [exBg]);
  const [exStatus, setExStatus] = useState<{ msg: string; busy?: boolean; err?: boolean } | null>(null);
  const exTimer = useRef(0);
  const flash = (msg: string, err = false) => { setExStatus({ msg, err }); window.clearTimeout(exTimer.current); exTimer.current = window.setTimeout(() => setExStatus(null), err ? 6000 : 1500); };
  const errText = (e: unknown) => (e instanceof Error && e.message ? e.message : "Export failed.");
  const renderPng = () => renderPanelPng(plotRef.current!, Number(exScale), exBg, style === "custom" ? scheme : undefined);
  const onDownload = async () => {
    const el = plotRef.current; if (!el) return;
    setExStatus({ msg: "Rendering…", busy: true });
    try { const blob = await renderPng(); downloadBlob(blob, exportName(el)); flash("Downloaded"); } catch (e) { flash(errText(e), true); }
  };
  // The blob promise, not the blob, goes to the clipboard so the write stays inside the click's user-gesture window (Safari); Chrome accepts either.
  const onCopy = async () => {
    if (!plotRef.current) return;
    setExStatus({ msg: "Rendering…", busy: true });
    try { await copyPng(renderPng()); flash("Copied"); } catch (e) { flash(errText(e), true); }
  };

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
    const p50 = r.ops.doc_latency_p50_ms, ci = r.ops.doc_latency_p50_ci_ms ?? null;
    if (speedChart === "throughput") { const val = p50 == null ? null : 3.6e6 / p50; return { ...base(r), value: val, label: val == null ? "" : `${fmtInt(Math.round(val))} docs/h` }; }
    // Whisker: the 95% bootstrap interval for the median (two-sided), not the p95 tail.
    return { ...base(r), value: p50, lo: ci?.[0] ?? null, hi: ci?.[1] ?? null, label: p50 == null ? "" : fmtLatency(p50, speedUnit) };
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
  // What the panel actually draws for the 95% interval, read off its computed variables after each style-affecting change (preset, Custom sliders,
  // Boxes mode and Contrast all folded in): the map's boxes (--box-alpha, or the outline: --box-stroke in the filled modes, --box-stroke-w in the outline
  // modes) and the whisker charts' whiskers (--op-whisker). The legend note names only what is drawn.
  const [marks, setMarks] = useState({ boxes: true, whiskers: true });
  useEffect(() => {
    const el = plotRef.current; if (!el) return;
    const cs = getComputedStyle(el), num = (v: string, dflt: number) => { const n = parseFloat(cs.getPropertyValue(v)); return Number.isFinite(n) ? n : dflt; };
    const outline = boxOutlined ? num("--box-stroke-w", 0.75) > 0 : num("--box-stroke", 0) > 0;
    const drawn = (boxes !== "outline" && num("--box-alpha", 0.14) > 0) || outline, whiskers = num("--op-whisker", 0.75) > 0;
    setMarks((p) => (p.boxes === drawn && p.whiskers === whiskers ? p : { boxes: drawn, whiskers }));
  }, [style, scheme, contrast, theme, boxes, boxOutlined]);
  const legendText = (): string[] => {
    // the note names the mark drawn at the point (Marks control); with logos on it keeps the site's wording
    const what = logos || mark === "dot" ? "Dot" : mark === "x" ? "Cross" : mark[0].toUpperCase() + mark.slice(1);
    const box = boxes === "filled" ? "Shaded box" : boxes === "hatched" ? "Hatched box" : boxes === "outline" ? "Outlined box" : "Hatched, outlined box";
    if (plot === "pr") return chart === "map" ? [marks.boxes ? `${what}: point estimate. ${box}: 95% interval on recall (width) and precision (height).` : `${what}: point estimate.`] : [];
    const whisk = (clause: string) => (marks.whiskers ? clause : "");
    if (plot === "cost") {
      const basis = "Cost as paid for the benchmark run (OpenAI flex pricing, Anthropic prompt caching, Google and TypeSafe at list; GPU rows as A100 rental for their median latency)";
      if (costChart === "scatter") return [`${basis}, ${cu.short} on a log axis, against recall${whisk(" with its 95% interval (whisker)")}.`];
      return [`${basis}, ${cu.short}${costChart === "dots" || costScale === "log" ? ", log axis" : ""}.`];
    }
    if (plot === "speed") {
      if (speedChart === "throughput") return ["Sequential documents per hour: 3,600,000 ÷ median wall-clock milliseconds per document, one request at a time. Every service accepts parallel requests, so compare ratios, not absolutes."];
      return [`${speedChart === "bars" ? "Bar" : "Dot"}: median latency per document, one request at a time${speedChart === "dots" ? ", on a log axis" : ""}${whisk("; whisker: 95% bootstrap interval for the median")}.`];
    }
    const t0 = stabSetting === "t0" ? " Temperature 0 where the API accepts it; deciders expose no sampling control." : "";
    const where = `Measured on ${measuredOn}${sameRuns ? ` (${sameRuns} per model)` : " scored 5 times"}; the same cells are shown for every corpus.`;
    if (stabChart === "agree") return [`Bar: agreement, the probability two identical runs give the same decision (1 − pairwise disagreement)${whisk("; whisker: 95% bootstrap interval")}. Axis zoomed to the measured range.${t0}`, where];
    return [`${stabChart === "bars" ? "Bar" : "Dot"}: probability two identical runs disagree on a decision (pairwise)${whisk("; whisker: 95% bootstrap interval over decisions")}.${t0}`, where];
  };
  const legendLines = legendText();
  const showIssue = plot === "pr" || (plot === "cost" && costChart === "scatter");
  /** e.g. jev-recall-precision-map-trec-linkedin-1200x675@2x.png; the size is the panel's rendered CSS size (the PNG is that × scale). */
  const exportName = (el: HTMLElement) => {
    const chartId = plot === "pr" ? chart : plot === "cost" ? costChart : plot === "speed" ? speedChart : stabChart;
    const styleId = style === "custom" && schemeName.trim() ? `custom-${schemeName.trim()}` : style;
    return `${slug(["jev", plot === "pr" ? "recall-precision" : plot, chartId, corpus, styleId, colorMode === "style" ? "" : colorMode].join("-"))}-${el.offsetWidth}x${el.offsetHeight}@${exScale}x.png`;
  };

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
        {/* the shape control steps aside where the vendor glyph is the mark (a scatter with logos on); the size control scales either */}
        {!(fills && logos) && (
          <Control label="Marks">
            <Seg value={mark} onChange={setMark} options={MARK_SHAPES.map((m) => ({ id: m.id, label: m.label }))} />
          </Control>
        )}
        <Control label="Mark size">
          <Seg value={markSize} onChange={setMarkSize} options={[{ id: "s", label: "S", title: "0.75× the site's mark" }, { id: "m", label: "M", title: "The site's mark size" }, { id: "l", label: "L", title: "1.5×" }, { id: "xl", label: "XL", title: "2.2×, for logos inside wide interval boxes" }]} />
          {fills && logos && <span className="studio-hint small" title="Switch Panel to names only to choose a mark shape">logos are the marks</span>}
        </Control>
        {plot === "pr" && chart === "map" && (
          <Control label="Boxes">
            <Seg value={boxes} onChange={setBoxes} options={BOX_MODES.map((m) => ({ id: m.id, label: m.label, title: m.title }))} />
          </Control>
        )}
        {fills && (
          <Control label="Labels">
            <Seg value={labelsMode} onChange={setLabelsMode} options={[{ id: "beside", label: "beside", title: "Each model's name next to its mark" }, { id: "legend", label: "legend", title: "A legend row at the top of the panel (square swatches and names); no names on the plot" }]} />
          </Control>
        )}
        {fills && labelsMode === "beside" && (
          <Control label="Leaders">
            <Seg value={leaders ? "on" : "off"} onChange={(x) => setLeaders(x === "on")} options={[{ id: "off", label: "off" }, { id: "on", label: "on", title: "A hairline in the model's colour from a label the layout pushed away from its mark back to the mark; labels beside their mark get none" }]} />
          </Control>
        )}
        <Control label="Style">
          <Seg value={style} onChange={onStyle} options={STYLES.map((s) => ({ id: s.id, label: s.label, title: s.title }))} />
        </Control>
        {style === "custom" && (
          <Control label="Saved">
            <span className="select">
              <select value={savedName} onChange={(e) => loadScheme(e.target.value)} aria-label="Saved schemes">
                <option value="">{Object.keys(schemes).length ? "—" : "none yet"}</option>
                {Object.keys(schemes).sort().map((n) => <option key={n} value={n}>{n}</option>)}
              </select>
            </span>
            <button type="button" className="studio-btn small" onClick={deleteScheme} disabled={!savedName} title="Remove the selected saved scheme from this browser">Delete</button>
            <label className="studio-btn small" title="Load a scheme file written by Export JSON (or a bare variable map)">
              Import JSON
              <input type="file" accept=".json,application/json" hidden onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; void importScheme(f); }} />
            </label>
          </Control>
        )}
        <Control label="Colors">
          <Seg
            value={colorMode} onChange={onColorMode}
            options={[
              { id: "style" as ColorMode, label: "style's own", title: "The model colours the Style preset defines" },
              ...PALETTES.map((p) => ({ id: p.id as ColorMode, label: p.label, title: p.title })),
              { id: "custom" as ColorMode, label: "custom", title: "Pick each model's colour; starts from the colours on screen" },
            ]}
          />
          {colorMode === "custom" && (
            <span className="studio-swatches">
              {sel.map((r) => {
                const m = PRIMARY_BY_KEY[r.model], hex = custom[r.model] ?? "#888888";
                return (
                  <label key={r.model} className="studio-swatch" title={`${m.short}: ${hex}`}>
                    <input type="color" value={hex} onChange={(e) => { const c = e.target.value; setCustom((p) => ({ ...p, [r.model]: c })); }} aria-label={`${m.short} colour`} />
                    <span>{m.short}</span>
                  </label>
                );
              })}
              <button type="button" className="studio-btn small" onClick={resetCustom} title="Drop the swatches and go back to the style's own colours">reset</button>
            </span>
          )}
        </Control>
        <Control label="Text">
          <Seg value={text} onChange={setText} options={[{ id: "s", label: "S", title: "90% of the site's text size" }, { id: "m", label: "M", title: "The site's text size" }, { id: "l", label: "L", title: "120%" }, { id: "xl", label: "XL", title: "145%, for phone-sized viewing" }]} />
        </Control>
        <Control label="Contrast">
          <Seg value={contrast} onChange={setContrast} options={[{ id: "normal", label: "normal" }, { id: "high", label: "high", title: "Full-ink labels, darker and thicker axes and whiskers, stronger fills, larger marks" }]} />
        </Control>
      </div>

      {style === "custom" && (
        <div className="controls studio-row2 studio-scheme-row">
          <Control label="Scheme">
            <span className="studio-size">
              <input type="text" className="name" value={schemeName} onChange={(e) => setSchemeName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") saveScheme(); }} placeholder="name" spellCheck={false} aria-label="scheme name" />
            </span>
            <button type="button" className="studio-btn small" onClick={saveScheme} title="Store these values under this name in this browser; an existing name is overwritten">Save</button>
            <button type="button" className="studio-btn small" onClick={exportScheme} title="Download these values as <name>.json, for another browser">Export JSON</button>
            {scMsg && <span className="studio-status" role="status">{scMsg}</span>}
          </Control>
          <Control label="Surface">
            <span className="studio-swatches">
              {SCHEME_SURFACE.map((x) => <SchemeColor key={x.v} v={x.v} label={x.label} value={scheme[x.v] ?? ""} onChange={(val) => setVar(x.v, val)} />)}
            </span>
          </Control>
          <Control label="Boxes & bars">
            {SCHEME_SLIDERS.map((x) => {
              const n = parseFloat(scheme[x.v] ?? ""); const val = Number.isFinite(n) ? n : x.dflt;
              return (
                <label key={x.v} className="studio-slider" title={x.title}>
                  <span>{x.label}</span>
                  <input type="range" min={x.min} max={x.max} step={x.step} value={val} onChange={(e) => setVar(x.v, e.target.value)} aria-label={x.label} />
                  <span className="val">{val.toFixed(2)}</span>
                </label>
              );
            })}
          </Control>
          <Control label="Font">
            <span className="studio-size">
              <input type="text" className="font" value={scheme["--sans"] ?? ""} onChange={(e) => setVar("--sans", e.target.value)} spellCheck={false} aria-label="panel font family, CSS" title="The panel's font-family list, as CSS" />
            </span>
          </Control>
          <Control label="Models">
            <button type="button" className="studio-btn small" onClick={() => setShowModels((s) => !s)} aria-expanded={showModels}>{showModels ? "hide" : "show"} {SCHEME_MODELS.length} colours</button>
            {showModels && (
              <span className="studio-swatches">
                {SCHEME_MODELS.map((x) => <SchemeColor key={x.v} v={x.v} label={x.label} value={scheme[x.v] ?? ""} onChange={(val) => setVar(x.v, val)} />)}
              </span>
            )}
            {showModels && colorMode !== "style" && <span className="studio-hint small">Colors is on “{colorMode === "custom" ? "custom" : PALETTES.find((p) => p.id === colorMode)?.label}”, which paints over these; set it to style's own to see them.</span>}
          </Control>
        </div>
      )}

      <div className="controls studio-row2 studio-export">
        <Control label="Export">
          <button type="button" className="studio-btn" onClick={onDownload} disabled={exStatus?.busy} title="Save the chart area as a PNG file">Download PNG</button>
          <button type="button" className="studio-btn" onClick={onCopy} disabled={exStatus?.busy} title="Copy the chart area as a PNG image">Copy PNG</button>
          {exStatus && <span className={`studio-status${exStatus.err ? " err" : ""}`} role="status">{exStatus.msg}</span>}
        </Control>
        <Control label="Scale">
          <Seg value={exScale} onChange={setExScale} options={[{ id: "1", label: "1×", title: "PNG at the panel's size" }, { id: "2", label: "2×", title: "Twice the panel's size (retina)" }, { id: "3", label: "3×", title: "Three times the panel's size" }]} />
          <span className="studio-hint small">{w * Number(exScale)} × {fills ? h * Number(exScale) : "auto"} px, no frame</span>
        </Control>
        <Control label="Background">
          <Seg value={exBg} onChange={setExBg} options={[{ id: "panel", label: "panel", title: "Filled with the style's panel colour" }, { id: "transparent", label: "transparent", title: "Alpha where the panel would be" }]} />
        </Control>
      </div>

      {/* With Custom on, the stage paints the scheme's --bg behind the panel (styles.css .studio-stage.custom); body keeps the theme's. */}
      <section className={`section studio-stage${style === "custom" ? " custom" : ""}`} style={style === "custom" && scheme["--bg"] ? ({ "--bg": scheme["--bg"] } as React.CSSProperties) : undefined}>
        {/* The custom scheme's colours sit on this wrapper, not the panel: inline on the panel they would beat .studio-plot[data-contrast="high"], which must still recolour
            relative to --ink and --panel. The sliders' variables do go inline on the panel (sliderVars), so that block's own --box-alpha / --bar-alpha never overrule them. */}
        <div className="studio-scheme" style={style === "custom" ? (scheme as React.CSSProperties) : undefined}>
          <div
            ref={plotRef}
            className={`studio-plot${frame ? " framed" : ""}${fills ? "" : " auto"}`}
            data-style={style}
            data-contrast={contrast}
            style={{ ...colorVars, ...sliderVars, width: w, height: fills ? h : undefined, "--fs-legend": `${12 * ts}px`, "--mark-user": ms } as React.CSSProperties}
          >
            {plot === "pr" && chart === "map" && (
              <div className="studio-canvas">
                <PRScatter items={items} zoom={zoom} domain={domain} emptyText={emptyText} logos={logos} fill textScale={ts} leaders={leaders} labels={labelsMode} mark={mark} markSize={ms} boxes={boxes} />
              </div>
            )}
            {plot === "pr" && chart === "ranked" && <PRRail items={items} zoom={zoom} range={range} sortBy="recall" logos={logos} textScale={ts} mark={mark} />}
            {plot === "cost" && costChart === "scatter" && (
              <div className="studio-canvas">
                <StudioScatter pts={costPts} xLabel={`${cu.axis} (log)`} yLabel={v.issue ? `Recall · ${issueLabel(meta, v.issue).split(" · ")[0]}` : "Recall"} fmtX={fmtMoneyTick} logos={logos} emptyText={emptyText} textScale={ts} leaders={leaders} labels={labelsMode} mark={mark} markSize={ms} />
              </div>
            )}
            {plot === "cost" && costChart !== "scatter" && (
              <StudioBars rows={costRows} kind={costChart === "dots" ? "dot" : "bar"} scale={costChart === "dots" ? "log" : costScale} axis={cu.axis + (costChart === "dots" || costScale === "log" ? " (log)" : "")} fmtTick={fmtMoneyTick} logos={logos} textScale={ts} mark={mark} />
            )}
            {plot === "speed" && (
              <StudioBars
                rows={speedRows} kind={speedChart === "dots" ? "dot" : "bar"} scale={speedChart === "dots" ? "log" : "linear"} sort={speedChart === "throughput" ? "desc" : "asc"}
                axis={speedChart === "throughput" ? "sequential documents per hour (3,600,000 ÷ median ms per document)" : `median latency per document${speedChart === "dots" ? " (log)" : ""}`}
                fmtTick={speedChart === "throughput" ? (t) => fmtInt(Math.round(t)) : fmtMsTick} logos={logos} textScale={ts} mark={mark}
              />
            )}
            {plot === "stability" && (
              <StudioBars
                rows={stabRows} kind={stabChart === "dots" ? "dot" : "bar"} sort={stabChart === "agree" ? "desc" : "asc"} domain={stabChart === "agree" ? agreeDomain : undefined}
                axis={stabChart === "agree" ? `agreement: probability two identical runs give the same decision${stabSetting === "t0" ? " · temperature 0" : ""}` : `probability two identical runs disagree${stabSetting === "t0" ? " · temperature 0" : ""}`}
                fmtTick={fmtPctTick} logos={logos} textScale={ts} mark={mark}
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
        </div>
      </section>
      {/* outside the stage, so it reads the theme's ink rather than sitting on a Custom scheme's page colour */}
      <p className="studio-foot">Drag the panel's bottom-right corner to resize, or type a size above. {w} × {fills ? h : "auto"} px.</p>
    </div>
  );
}
