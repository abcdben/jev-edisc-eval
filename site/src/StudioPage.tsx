import { useEffect, useMemo, useRef, useState } from "react";
import { DATA, PRIMARY_BY_KEY, corpusKey, fmtInt, issueLabel, siteCorpus, starOf, CORPORA } from "./data";
import { ModelPicker, useCompareItems, type View } from "./App";
import { INTERVAL_MODES, MARK_SHAPES, PRScatter, intervalHasArea, type PRDomain } from "./components/PRScatter";
import { FILL_MODES, isOutlined } from "./components/hatch";
import { PRRail } from "./components/PRRail";
import { StudioBars, StudioScatter } from "./components/StudioCharts";
import { COST_UNIT, STAB_T0, costAxis, costCaption, costPts, costRows, fmtMoneyTick, fmtMsTick, fmtPctTick, speedAxis, speedCaption, speedRows, stabAxis, stabCaption, stabPaired, stabRows, type StabT0 } from "./opsRows";
import { Control, Seg } from "./components/ui";
import { Section, sectionsApi, summarize } from "./components/Inspector";
import type { PlotBg } from "./components/plotBg";
import { TICK_DENSITIES } from "./components/ticks";
import { copyPng, downloadBlob, renderPanelPng, slug } from "./exportPng";
import { PALETTES, siblingHue, toHex, toVars, varOf } from "./palettes";
import type { LogosMode } from "./logos";
import { THEME_OPTIONS } from "./theme";
import { FAMILIES, FAMILY_BASIC_VAR, FAMILY_COMPOSED_VAR, FAMILY_MEMBERS, MAKERS, familyColor, familyOf, makerColor, makerName, makerOf } from "./makers";
import {
  BUILTIN_PRESETS, BUILTIN_PREFIX, JEV_SCALE, MARK_SCALE, SCHEME_MODELS, SCHEME_SLIDERS, SCHEME_SURFACE, SCHEME_VARS, TEXT_SCALE, builtinState, cleanVars, decodeHash, defaults, encodeHash,
  fromPreset, isVars, makePreset, parsePresetFile, readPresets, readStored, sameState, writeChanged,
  type Bg, type ColorMode, type PlotStyle, type StudioPreset, type StudioState, type Vars,
} from "./studioState";

/**
 * Screenshot studio (studio.html → studio.tsx → this page; unlinked from the site): one Compare models chart alone, on a plain panel whose size
 * you set, with every control above the plot and none on it. The top bar holds what is plotted (plot, corpus, models, issue) and the PNG export;
 * the Presets row under it saves, loads, imports, exports and shares the whole panel of settings (studioState.ts); the inspector under that
 * (components/Inspector.tsx) groups the rest into disclosure sections: Chart (the plot's own controls: view, axes, gridline
 * density, marks, the interval mark's shape, fill of the boxes and bars, labels, the key: by model, maker or question-form family), Canvas (size, title, frame, legend, logos, background pattern), Style (preset, colours, text, contrast), Scheme (the custom scheme
 * editor, with Style → Custom) and Export (scale, backdrop). Plots: recall/precision (the site's map and ranked views), Cost, Speed and Stability
 * (components/StudioCharts.tsx). Drag the panel's bottom-right corner or type a size; pick a size preset for LinkedIn's usual aspect ratios. Nothing pulses and nothing opens on click.
 *
 * State: every setting is one field of a single `StudioState` (studioState.ts FIELDS: defaults, validation, and the localStorage key each remembered
 * field has always had), held in one useState here; `set` / `patch` change fields, an effect writes the changed remembered fields back to their own keys,
 * so a visitor who never touches presets sees no difference. A preset is `snapshot(state)`; loading one replaces the whole state (`fromPreset`).
 */

type SizePreset = { id: string; label: string; w: number; h: number };
const PRESETS: SizePreset[] = [
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
 * A preset may carry a `profile`: the companion settings (labels, marks, background, panel frame, logos, colours, text, contrast) that reproduce its reference
 * look, applied once, when the preset is chosen (onStyle), never on reload or while it stays on, so every control still moves freely afterwards.
 */
type Profile = Partial<Pick<StudioState, "labels" | "leaders" | "mark" | "markSize" | "bg" | "frame" | "logos" | "text" | "contrast" | "colors">>;
const STYLES: { id: PlotStyle; label: string; title: string; profile?: Profile }[] = [
  { id: "site", label: "Site", title: "The site's own look; follows the Dark/Light theme" },
  { id: "journal", label: "Journal", title: "Academic figure: white, black hairline axes, serif labels, Okabe–Ito colorblind-safe palette" },
  { id: "newsroom", label: "Newsroom", title: "Editorial data graphic: warm greys, dotted grid, muted news palette" },
  { id: "linkedin", label: "LinkedIn", title: "LinkedIn brand: #0A66C2 blues for Jev, LinkedIn accent colours for the LLMs" },
  { id: "slate", label: "Slate", title: "Dark slate, Jev in one saturated accent, every LLM in a shade of grey" },
  { id: "economist", label: "Economist", title: "Financial weekly: red accent tab, thin grey rules, the Economist data palette" },
  { id: "epoch", label: "Epoch", title: "Epoch AI-style chart: white, horizontal hairline grid only, flat saturated dots, no interval boxes; pairs with Labels → legend" },
  {
    id: "typesafe", label: "TypeSafe",
    title: "TypeSafe AI's house chart: charcoal panel, white Inter labels, thin solid grid, Jev in TypeSafe magenta, OpenAI teal, Anthropic orange, Fireworks grey. Choosing it also sets Labels → legend, Marks → diamond L, Background → plain, Panel → plain, names only, Colors → style's own, Text M, normal contrast (each can be changed again after)",
    profile: { labels: "legend", leaders: false, mark: "diamond", markSize: "l", bg: "off", frame: false, logos: "none", text: "m", contrast: "normal", colors: "style" },
  },
  { id: "custom", label: "Custom", title: "Your own scheme: starts as a copy of the preset that was on, editable below, saved by name" },
];
/** Presets with a dark panel (the Colors palettes are lifted on them, palettes.ts forDark; Site follows the theme, Custom its own --panel). */
const DARK_STYLES: PlotStyle[] = ["slate", "typesafe"];
/**
 * Built-in schemes (Scheme → Saved, the "built-in" group): a preset offered as a starting point in the editor under its own name, its variables read
 * off the preset's CSS when chosen (presetVars), so the two never drift apart. Saving keeps a copy under the user's schemes; the built-in stays.
 */
const BUILTIN_SCHEMES: { name: string; style: PlotStyle }[] = [{ name: "TypeSafe", style: "typesafe" }];

/**
 * Custom scheme (Style → Custom): the panel variables every preset block defines (studioState.ts SCHEME_SURFACE, SCHEME_MODELS, SCHEME_SLIDERS), exposed
 * in the editor row, plus `--bg`, the page behind the panel (painted by the stage while Custom is on; the PNG export is the panel alone and never shows it).
 * Colours: the surface and ink set, then one per roster model through the custom property its colour is (data.ts ALL_PRIMARY `var(--…)`, palettes.ts varOf).
 * Sliders: the interval-box fill opacity and the bar fill opacity (each also sets its hatch lines' opacity in the hatched Fill modes, components/hatch.tsx FillMode)
 * and the outline width in px. `--sans` is the panel face. A colour's text field takes any CSS colour (`transparent` for no grid included); the native picker beside it shows the nearest hex.
 * The saved schemes (`studio-schemes`, a name → vars map) are a colour library apart from the state: a preset carries its scheme's vars inline instead.
 */
const isSchemes = (o: unknown): o is Record<string, Vars> => !!o && typeof o === "object" && !Array.isArray(o) && Object.values(o).every(isVars);
const readJson = <T,>(key: string, ok: (o: unknown) => o is T, dflt: T): T => { try { const o: unknown = JSON.parse(localStorage.getItem(key) || "null"); return ok(o) ? o : dflt; } catch { return dflt; } };
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

// Mark size (studioState.ts MarkSize, MARK_SCALE): the multiplier on every point mark and vendor glyph, written to the panel as --mark-user (PRScatter.tsx Mark,
// glyphScale) and passed to the scatters so their label placement keeps clear of the larger mark. High contrast's own 1.3 (--mark-scale / --r-add) multiplies on top.
// Jev mark size (JevMarkSize, JEV_SCALE): the Jev rows' own size (logos.tsx isJev; Laya and the LLMs keep the Mark size), the same steps plus 2XL, or `same`, the
// Mark size. Written to the panel as --mark-jev, an absolute factor the Jev marks and glyphs read in place of --mark-user, and passed to the scatters as `jevMarkSize`.
// Text size (TextSize, TEXT_SCALE): one factor on every font size in the panel, passed to the charts as `textScale`, which also scales their label-width estimates and margins.
// Contrast `high` (styles.css .studio-plot[data-contrast="high"]) puts every label in full ink, thickens axes and whiskers, raises the bar and box alphas and enlarges the marks.
// Key (KeyMode; makers.ts): `maker` colours every item by who makes it through that maker's model colour property, so the Style preset, palette or custom swatch
// still decides the hue; the legend then lists the makers and the points keep their name labels (shortened where the roster gives a `shortInMaker`).
// `family` splits the Jev rows into the basic question forms (Noul, Choice, Score) and the composed variants (Facets, Ensemble, Gate), one colour each through
// --fam-basic / --fam-composed (styles.css defaults off the style's Jev colours, a palette's composed default a sibling hue of its Jev · Noul; the Basic and
// Composed swatches, `famBasic` / `famComposed`, override inline), and colours every other model as by maker.
/** Logos (Canvas → Panel): every item's vendor mark, the Jev rows' alone, or none (logos.tsx LogosMode). */
const LOGOS_OPTIONS: { id: LogosMode; label: string; title: string }[] = [
  { id: "all", label: "logos", title: "Every model's vendor mark: as the point mark on the map and cost scatter, before the name in the ranked and bar charts" },
  { id: "jev", label: "Jev logos only", title: "The Jev rows keep their mark; the LLMs (and Laya) draw the plain mark shape and their name alone" },
  { id: "none", label: "names only", title: "No vendor marks; every point is the Marks shape" },
];

/**
 * Background (Canvas → Background): the pattern behind every plot's plot area (components/plotBg.tsx). `auto` is what each Style preset drew before
 * the control existed: the recall/precision charts' dot matrix in the preset's --dots (transparent in Journal, Newsroom, Economist and Epoch), nothing
 * behind the bar and scatter charts; `off` removes it everywhere; `dots` and `grid` put the pattern behind every plot, in the preset's --dots where
 * it has one and otherwise a faint ink written to the panel as --plot-dots.
 */
const BG_OPTIONS: { id: Bg; label: string; title: string }[] = [
  { id: "auto", label: "auto", title: "The style's own: the dot matrix on the recall/precision charts where the preset has a dot colour (Site, LinkedIn, Slate), nothing behind the bar charts" },
  { id: "off", label: "plain", title: "No pattern behind the plot area, in every plot and style" },
  { id: "dots", label: "dot grid", title: "A dot matrix behind the plot area of every plot; the style's dot colour, or a faint ink where the style has none" },
  { id: "grid", label: "fine grid", title: "Fine hairlines behind the plot area of every plot, in the same colour as the dot grid" },
];
const BG_SUMMARY: Record<Bg, string> = { auto: "background auto", off: "plain background", dots: "dot grid", grid: "fine grid" };
/** A computed --dots that draws nothing: unset, or transparent in either spelling. */
const noColour = (v: string) => !v || v === "transparent" || v === "rgba(0, 0, 0, 0)";

const clamp = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, Math.round(n)));

export default function StudioPage() {
  // ---- The one state object (studioState.ts): the remembered fields from their own localStorage keys, or the whole state from a share link's #p= hash ----
  const [fromLink] = useState(() => decodeHash(location.hash));
  const [state, setState] = useState<StudioState>(() => (fromLink ? fromPreset(fromLink.state) : readStored()));
  const stateRef = useRef(state);
  stateRef.current = state;
  // Persistence gate: a state that arrived by link is not written to localStorage until the user changes something or saves it; the first change also
  // drops the hash from the URL, since it no longer describes the page. `lastWritten` is what was last written back, null before the first write.
  const persistRef = useRef(!fromLink);
  const lastWritten = useRef<StudioState | null>(null);
  const touch = () => {
    if (persistRef.current) return;
    persistRef.current = true;
    if (location.hash) history.replaceState(null, "", location.pathname + location.search);
    writeChanged(null, stateRef.current);
    lastWritten.current = stateRef.current;
  };
  /** Set one field (a value or an updater), as a user change. */
  const set = <K extends keyof StudioState>(k: K, v: StudioState[K] | ((p: StudioState[K]) => StudioState[K])) => {
    touch();
    setState((p) => { const nv = typeof v === "function" ? (v as (p: StudioState[K]) => StudioState[K])(p[k]) : v; return Object.is(nv, p[k]) ? p : { ...p, [k]: nv }; });
  };
  const setter = <K extends keyof StudioState>(k: K) => (v: StudioState[K]) => set(k, v);
  /** Set several fields at once, as a user change. */
  const patch = (p: Partial<StudioState>) => { touch(); setState((s) => ({ ...s, ...p })); };
  // every remembered field whose stored form changed goes back to its own key, as the page always wrote it (studioState.ts FIELDS)
  useEffect(() => { if (!persistRef.current) return; writeChanged(lastWritten.current, state); lastWritten.current = state; }, [state]);
  const {
    plot, corpus, issue, on, chart, costChart, costUnit, costScale, speedChart, speedUnit, stabChart, stabT0, stabT0Tag, stabT0Key, hideUnmeasured, orient, axes, ax, swap, ticks,
    mark, markSize, jevSize, fill: fillMode, interval, labels: labelsMode, leaders, key, famBasic, famComposed, w, h, title, frame, legend, logos, bg, style, colors: colorMode, custom, text, contrast,
    scheme, schemeName, exScale, exBg, theme,
  } = state;

  // the controls' setters, one per field (the JSX below reads as it did when each was its own useState)
  const setPlot = setter("plot"), setCorpus = (c: string) => patch({ corpus: siteCorpus(c), issue: null }), setIssue = setter("issue"), setOn = setter("on");
  const setChart = setter("chart"), setCostChart = setter("costChart"), setCostUnit = setter("costUnit"), setCostScale = setter("costScale"), setSpeedChart = setter("speedChart"), setSpeedUnit = setter("speedUnit");
  const setStabChart = setter("stabChart"), setStabT0 = setter("stabT0"), setStabT0Tag = setter("stabT0Tag"), setStabT0Key = setter("stabT0Key"), setHideUnmeasured = setter("hideUnmeasured"), setOrient = setter("orient"), setAxes = setter("axes"), setSwap = setter("swap"), setTicks = setter("ticks");
  // the bar charts (StudioCharts.tsx StudioBars, in any of their modes): the plots the Orientation control applies to; `vertical` is columns
  const barPlot = (plot === "cost" && costChart !== "scatter") || plot === "speed" || plot === "stability";
  const vertical = barPlot && orient === "v";
  // Temperature 0 as drawn (opsRows.ts StabT0): paired bars on the dot chart become the lollipop, and the lollipop is a dot chart whatever Chart says
  const stabT0Draw: StabT0 = stabT0 === "paired" && stabChart === "dots" ? "dots" : stabT0;
  const stabDots = stabChart === "dots" || stabT0Draw === "dots";
  const setMark = setter("mark"), setMarkSize = setter("markSize"), setJevSize = setter("jevSize"), setFillMode = setter("fill"), setIntervalMode = setter("interval"), setLabelsMode = setter("labels"), setLeaders = setter("leaders"), setKey = setter("key");
  const setW = setter("w"), setH = setter("h"), setTitle = setter("title"), setFrame = setter("frame"), setLegend = setter("legend"), setLogos = setter("logos"), setBg = setter("bg");
  const setText = setter("text"), setContrast = setter("contrast"), setExScale = setter("exScale"), setExBg = setter("exBg"), setTheme = setter("theme");
  const v: View = { corpus, tag: "", arm: "multi", gray: "all", level: "doc", issue };
  const meta = DATA.corpora[corpusKey(v.corpus, v.tag)];
  const { sel, items } = useCompareItems(v, on);

  // Axes: the site's two modes, plus `custom`, explicit percent bounds per axis (the ranked view shares one range across both panels).
  const setBound = (k: keyof StudioState["ax"]) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const n = Number(e.target.value);
    if (Number.isFinite(n)) set("ax", (p) => ({ ...p, [k]: clamp(n, 0, 100) }));
  };
  const span = (lo: number, hi: number): [number, number] => (hi > lo ? [lo / 100, hi / 100] : [Math.min(lo, hi) / 100, Math.min(lo, hi) / 100 + 0.01]);
  // Axes orientation (PRScatter.tsx `swap`): recall on x (the site's map) or precision on x with recall up the side. The custom bounds
  // above stay per metric (xlo/xhi are recall, ylo/yhi precision) and are mapped to the plot's axes here.
  const recallSpan = span(ax.xlo, ax.xhi), precisionSpan = span(ax.ylo, ax.yhi);
  const domain: PRDomain | undefined = axes === "custom" ? (swap ? { x: precisionSpan, y: recallSpan } : { x: recallSpan, y: precisionSpan }) : undefined;
  const range: [number, number] | undefined = axes === "custom" ? span(ax.xlo, ax.xhi) : undefined;
  const zoom = axes === "zoom";
  const byMaker = key === "maker", byFamily = key === "family";
  // Key (KeyMode): the group an item falls into and the colour it draws in (makers.ts): its maker in by-maker mode, its question-form family (or maker) in
  // by-family mode; none in by-model mode. `keyed` is the one place the items and rows the charts get are recoloured and renamed (the in-maker name in both
  // grouped modes); in by-model mode it returns them as they came.
  const groupOf = byFamily ? familyOf : byMaker ? makerOf : null;
  const groupColor = byFamily ? familyColor : makerColor;
  const keyed = <T extends { id: string; name: string; color: string }>(x: T): T => (groupOf ? { ...x, color: groupColor(x.id, x.color), name: makerName(x.id, x.name) } : x);
  const keyedItems = useMemo(() => items.map(keyed), [items, key]); // eslint-disable-line react-hooks/exhaustive-deps
  // the legend groups (PRScatter.tsx LegendGroup) the scatters list in the grouped modes with Labels → legend; the point labels stay on
  const groups = groupOf ? (id: string) => { const g = groupOf(id); return { id: g.id, name: g.label, title: g.title, color: groupColor(id, PRIMARY_BY_KEY[id]?.color ?? "var(--ink-3)") }; } : undefined;
  const pointLabels = labelsMode === "beside" || !!groupOf;
  // Marks: the point shape when logos are off (the glyph stands in for it otherwise), and the size of whichever is drawn; the Jev rows' own size (`same` follows Mark size)
  const ms = MARK_SCALE[markSize];
  const jms = jevSize === "same" ? ms : JEV_SCALE[jevSize];
  // Fill (components/hatch.tsx FillMode): how the map's 95% interval boxes and the Cost, Speed and Stability bars are drawn: filled, hatched, outline
  // only, or hatched inside an outline. One setting for whichever plot is shown; stored under the key the earlier Boxes control used (`studio-boxes`).
  const boxOutlined = isOutlined(fillMode);
  // Interval (PRScatter.tsx IntervalMode): the shape of the map's 95% interval marks (box, whiskers, recall whisker, ellipse, brackets, none); the
  // ranked view maps it onto its row whiskers (PRRail.tsx). `box` is what the site and the studio always drew.
  const intervalArea = intervalHasArea(interval);
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  // Background (Bg): `presetDots` is whether the panel's own --dots (preset, theme or Custom scheme; not the --plot-dots override) draws anything.
  const [presetDots, setPresetDots] = useState(true);
  // The inspector's sections (components/Inspector.tsx; the `sections` field): Chart and Canvas open on a first visit, Scheme whenever Style → Custom is chosen.
  // Opening or closing one is not a change to the chart: it neither starts persisting a linked state nor marks a loaded preset modified.
  const sections = sectionsApi(state.sections, (f) => setState((p) => ({ ...p, sections: f(p.sections) })));

  // Custom scheme: the variables on the panel (the `scheme` field, `studio-custom`), the schemes saved by name (`studio-schemes`, a colour library
  // outside the state) and the name in the field / the saved scheme selected (`schemeName`, one value: the select shows it while it matches a saved name).
  const setScheme = (v: Vars | ((p: Vars) => Vars)) => set("scheme", v);
  const setSchemeName = setter("schemeName");
  const [schemes, setSchemes] = useState<Record<string, Vars>>(() => readJson("studio-schemes", isSchemes, {}));
  useEffect(() => { localStorage.setItem("studio-schemes", JSON.stringify(schemes)); }, [schemes]);
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
  // a saved scheme by name, or a built-in one (BUILTIN_SCHEMES; the select's `builtin:` values) read off its preset's CSS
  const loadScheme = (n: string) => {
    if (n.startsWith(BUILTIN_PREFIX)) { const b = BUILTIN_SCHEMES.find((x) => x.name === n.slice(BUILTIN_PREFIX.length)); if (b) { setScheme(presetVars(b.style)); setSchemeName(b.name); } return; }
    const s = schemes[n]; if (!s) return; setScheme({ ...s }); setSchemeName(n);
  };
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
  const ts = TEXT_SCALE[text];

  // Model colours: a palette over the Style preset, or per-model swatches. Dark panels (Slate, or Site in Dark) get the palette lifted (palettes.ts forDark).
  const setCustom = (v: Record<string, string> | ((p: Record<string, string>) => Record<string, string>)) => set("custom", v);
  const customPanelHex = style === "custom" ? toHex(scheme["--panel"] ?? "") : null;
  const darkPanel = customPanelHex ? luminance(customPanelHex) < 0.4 : DARK_STYLES.includes(style) || (style === "site" && theme === "dark");
  const colorVars: Record<string, string> = colorMode === "style" ? {} : colorMode === "custom" ? toVars(custom, false) : toVars(PALETTES.find((p) => p.id === colorMode)!.colors, darkPanel);
  // The family swatches (famBasic / famComposed): a hex goes inline on the panel over the style's default (styles.css --fam-basic / --fam-composed);
  // "" leaves the default, except that with a Colors palette or custom swatches on, the composed family's default is a sibling hue of the recoloured
  // Jev · Noul (palettes.ts siblingHue) rather than a preset's fixed hue or its Score row: every palette keeps the Jev rows in one hue family, so
  // following any of them would draw the two families alike. Without a Noul swatch to turn (custom mode, none set), it follows the Score row.
  const paletteBasic = colorMode !== "style" ? colorVars[varOf("jev@base")!] : undefined;
  const famVars: Record<string, string> = {
    ...(famBasic ? { [FAMILY_BASIC_VAR]: famBasic } : {}),
    ...(famComposed ? { [FAMILY_COMPOSED_VAR]: famComposed } : colorMode !== "style" ? { [FAMILY_COMPOSED_VAR]: paletteBasic ? siblingHue(paletteBasic) : "var(--v5)" } : {}),
  };
  // what the two families draw in right now, read off the panel for the swatches' pickers (the default is a var() chain the picker cannot show)
  const [famShown, setFamShown] = useState({ basic: "#888888", composed: "#888888" });
  useEffect(() => {
    const el = plotRef.current; if (!el || !byFamily) return;
    const cs = getComputedStyle(el), read = (v: string, dflt: string) => toHex(cs.getPropertyValue(v)) ?? dflt;
    const basic = read(FAMILY_BASIC_VAR, famBasic || "#888888"), composed = read(FAMILY_COMPOSED_VAR, famComposed || "#888888");
    setFamShown((p) => (p.basic === basic && p.composed === composed ? p : { basic, composed }));
  }, [byFamily, style, scheme, colorMode, custom, theme, famBasic, famComposed]);
  const resetFamily = () => patch({ famBasic: "", famComposed: "" });
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
  // A style's profile (STYLES): the companion settings it declares, set once as it is chosen; the controls are the user's again from then on.
  // Entering Custom copies the preset that was on, so the editor starts from real values; a reload into Custom with nothing stored copies Site.
  const onStyle = (s: PlotStyle) => {
    const entering = s === "custom" && style !== "custom";
    if (entering) sections.set("scheme", true);
    const profile = s !== style ? STYLES.find((x) => x.id === s)?.profile : undefined;
    patch({ ...profile, style: s, ...(entering ? { scheme: presetVars(style) } : {}) });
  };
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
    patch(m === "custom" && colorMode !== "custom" ? { colors: m, custom: currentColors() } : { colors: m });
  };
  const resetCustom = () => patch({ custom: {}, colors: "style" });

  // ---- Presets (studioState.ts): the whole state saved by name (`studio-presets`), the one loaded (`studio-preset-current`; shown in the select, with a
  // • once the settings differ from it), the built-ins (BUILTIN_PRESETS, copy-on-save), a JSON file in or out, a share link carrying the state in its hash. ----
  const [presets, setPresets] = useState<Record<string, StudioPreset>>(readPresets);
  useEffect(() => { localStorage.setItem("studio-presets", JSON.stringify(presets)); }, [presets]);
  const [current, setCurrentRaw] = useState(() => (fromLink ? "" : localStorage.getItem("studio-preset-current") ?? ""));
  const setCurrent = (n: string) => { setCurrentRaw(n); localStorage.setItem("studio-preset-current", n); };
  const [presetName, setPresetName] = useState(() => fromLink?.name ?? current.replace(BUILTIN_PREFIX, ""));
  const builtinOf = (n: string) => BUILTIN_PRESETS.find((b) => BUILTIN_PREFIX + b.name === n);
  const cur = current in presets || builtinOf(current) ? current : "";
  const curLabel = cur.replace(BUILTIN_PREFIX, "");
  const curBuiltin = builtinOf(cur);
  const curState = cur ? (curBuiltin ? builtinState(curBuiltin) : fromPreset(presets[cur].state)) : null;
  const modified = !!curState && !sameState(curState, state);
  const [psMsg, setPsMsg] = useState<string | null>(null);
  const psTimer = useRef(0);
  const note = (msg: string) => { setPsMsg(msg); window.clearTimeout(psTimer.current); psTimer.current = window.setTimeout(() => setPsMsg(null), 2200); };
  const savePreset = (name: string) => {
    const n = name.trim().slice(0, 80);
    if (!n) { note("Name the preset first."); return; }
    if (n in presets && n !== cur && !confirm(`Overwrite the saved preset “${n}”?`)) return;
    touch();
    setPresets((p) => ({ ...p, [n]: makePreset(n, state) }));
    setCurrent(n); setPresetName(n);
    note(n in presets ? `Updated “${n}”` : `Saved “${n}”`);
  };
  // the loaded (saved, not built-in) preset takes the name in the field; shown while the field holds a different, non-empty name
  const renameName = cur && !curBuiltin ? presetName.trim().slice(0, 80) : "";
  const canRename = !!renameName && renameName !== cur;
  const renamePreset = () => {
    if (!canRename) return;
    if (renameName in presets && !confirm(`Overwrite the saved preset “${renameName}”?`)) return;
    setPresets((p) => { const q = { ...p }; q[renameName] = { ...q[cur], name: renameName }; delete q[cur]; return q; });
    setCurrent(renameName); setPresetName(renameName); note(`Renamed to “${renameName}”`);
  };
  const onSaveAs = () => { const n = prompt("Save the current settings as", presetName.trim() || "My preset"); if (n != null) savePreset(n); };
  const applyPreset = (st: StudioState, name: string, field: string) => { touch(); setState(st); setCurrent(name); setPresetName(field); };
  const loadPreset = (n: string) => {
    if (!n) return;
    const b = builtinOf(n);
    if (b) applyPreset(builtinState(b), n, b.name);
    else if (presets[n]) applyPreset(fromPreset(presets[n].state), n, n);
  };
  const deletePreset = () => {
    if (!cur || curBuiltin || !confirm(`Delete the saved preset “${cur}”?`)) return;
    setPresets((p) => { const q = { ...p }; delete q[cur]; return q; });
    setCurrent(""); note(`Deleted “${cur}”`);
  };
  const exportPreset = () => {
    const n = presetName.trim() || curLabel || "preset";
    downloadBlob(new Blob([JSON.stringify(makePreset(n, state), null, 2)], { type: "application/json" }), `${slug(n) || "preset"}.studio.json`);
  };
  const importPresets = async (file: File | undefined) => {
    if (!file) return;
    const got = parsePresetFile(await file.text());
    const names = got ? Object.keys(got) : [];
    if (!got || !names.length) { note("Not a preset file."); return; }
    setPresets((p) => ({ ...p, ...got }));
    applyPreset(fromPreset(got[names[0]].state), names[0], names[0]);
    note(names.length === 1 ? `Imported “${names[0]}”` : `Imported ${names.length} presets`);
  };
  const resetAll = () => { if (!confirm("Reset every setting to its default?")) return; applyPreset(defaults(), "", ""); note("Reset to defaults"); };
  // the share link: this page's URL with the whole state, as a preset, base64url-encoded in the hash (studioState.ts encodeHash); read back on load (fromLink)
  const copyLink = async () => {
    const url = `${location.origin}${location.pathname}#${encodeHash(makePreset(presetName.trim() || curLabel || "shared", state))}`;
    try { await navigator.clipboard.writeText(url); note(`Link copied (${(url.length / 1024).toFixed(1)} KB)`); } catch { prompt("Copy this link", url); }
  };

  // PNG export (exportPng.ts): the panel as shown, minus frame, corner radius and resize grip, at 1–3× on the panel colour or transparent.
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
  // A bar chart in columns (Orientation → vertical) fills the panel too: the columns take the height, the names run along the bottom.
  const fills = (plot === "pr" && chart === "map") || (plot === "cost" && costChart === "scatter") || vertical;
  // Which plots draw bars (StudioBars kind "bar"), and so take the Fill control with the map; the dot and scatter views have no area to fill.
  const hasBars = (plot === "cost" && costChart === "bars") || (plot === "speed" && speedChart !== "dots") || (plot === "stability" && !stabDots);
  // the map's Fill applies to the Interval modes with an area (box, ellipse); whiskers, brackets and none have nothing to fill
  const showFill = (plot === "pr" && chart === "map" && intervalArea) || hasBars;

  // Panel size in CSS pixels. The panel is also CSS-resizable by its corner; a ResizeObserver writes the dragged size back into the fields.
  // In the row-based charts the height follows the rows, so only the width is synced and the chosen height is kept for when a filling chart returns.
  // The observer's write-back is quiet (setState, not `set`): it fires on mount and after a preset loads, which are not the user's changes.
  const plotRef = useRef<HTMLDivElement>(null);
  const fillsRef = useRef(fills);
  fillsRef.current = fills;
  useEffect(() => {
    const el = plotRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      const bw = el.offsetWidth, bh = el.offsetHeight;
      setState((p) => { const nw = bw || p.w, nh = bh && fillsRef.current ? bh : p.h; return nw === p.w && nh === p.h ? p : { ...p, w: nw, h: nh }; });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const preset = PRESETS.find((p) => p.w === w && p.h === h)?.id ?? "custom";

  // ---- rows for the studio's own charts, from the selected roster records (opsRows.ts: colours and short names from the roster, so Style presets apply) ----
  const cu = COST_UNIT[costUnit];
  const stab = stabRows(sel, v.arm, stabChart, stabT0Draw, hideUnmeasured);
  const stabRowsKeyed = stab.rows.map(keyed);
  // whether the chart draws a t = 0 element for some selected model (the paired modes engage only where a t = 0 cell exists)
  const stabT0Drawn = stabPaired(stabT0Draw) && stab.rows.some((r) => r.value != null && r.t0);

  const emptyText = "Select at least one model.";
  // What the panel actually draws for the 95% interval, read off its computed variables after each style-affecting change (preset, Custom sliders,
  // Fill mode and Contrast all folded in): the map's boxes (--box-alpha, or the outline: --box-stroke in the filled modes, --box-stroke-w in the outline
  // modes) and the whisker charts' whiskers (--op-whisker). The legend note names only what is drawn.
  const [marks, setMarks] = useState({ boxes: true, whiskers: true });
  useEffect(() => {
    const el = plotRef.current; if (!el) return;
    const cs = getComputedStyle(el), num = (v: string, dflt: number) => { const n = parseFloat(cs.getPropertyValue(v)); return Number.isFinite(n) ? n : dflt; };
    const outline = boxOutlined ? num("--box-stroke-w", 0.75) > 0 : num("--box-stroke", 0) > 0;
    const drawn = (fillMode !== "outline" && num("--box-alpha", 0.14) > 0) || outline, whiskers = num("--op-whisker", 0.75) > 0;
    setMarks((p) => (p.boxes === drawn && p.whiskers === whiskers ? p : { boxes: drawn, whiskers }));
    setPresetDots(!noColour(cs.getPropertyValue("--dots").trim()));
  }, [style, scheme, contrast, theme, fillMode, boxOutlined]);
  // The Background control on the panel: the pattern each chart draws (auto keeps each chart's own default) and, where the style has no dot colour,
  // a faint ink for it: lighter on a dark panel, stronger in high contrast, and lighter again for the fine grid, whose lines cover more of the area than dots.
  const plotBg = (dflt: PlotBg): PlotBg => (bg === "auto" ? dflt : bg === "off" ? "none" : bg);
  const inkPct = (darkPanel ? 13 : contrast === "high" ? 30 : 20) * (bg === "grid" ? 0.6 : 1);
  const bgVars: Record<string, string> = bg !== "auto" && bg !== "off" && !presetDots ? { "--plot-dots": `color-mix(in srgb, var(--ink) ${inkPct}%, transparent)` } : {};
  const legendText = (): string[] => {
    // the note names the mark drawn at the point (Marks control); with every logo on it keeps the site's wording
    const what = logos === "all" || mark === "dot" ? "Dot" : mark === "x" ? "Cross" : mark[0].toUpperCase() + mark.slice(1);
    if (plot === "pr") {
      if (chart !== "map") return [];
      // the interval mark (Interval control), named only where the panel draws it: an area mode when its fill or outline is visible (marks.boxes), a line mode when --op-whisker is
      const fillWord = fillMode === "filled" ? "Shaded" : fillMode === "hatched" ? "Hatched" : fillMode === "outline" ? "Outlined" : "Hatched, outlined";
      // the directions follow the Axes orientation: recall is the width / horizontal on the site's map, the height / vertical when swapped
      const [rDim, pDim] = swap ? ["height", "width"] : ["width", "height"], [rDir, pDir] = swap ? ["vertical", "horizontal"] : ["horizontal", "vertical"];
      const ci =
        interval === "box" && marks.boxes ? `${fillWord} box: 95% interval on recall (${rDim}) and precision (${pDim}).`
        : interval === "ellipse" && marks.boxes ? `${fillWord} ellipse: spans the 95% intervals on recall (${rDim}) and precision (${pDim}).`
        : interval === "whiskers" && marks.whiskers ? `Whiskers: 95% interval on recall (${rDir}) and precision (${pDir}).`
        : interval === "band" && marks.whiskers ? "Whisker: 95% interval on recall."
        : interval === "bracket" && marks.whiskers ? `Brackets: corners of the 95% interval on recall (${rDim}) and precision (${pDim}).`
        : null;
      return [ci ? `${what}: point estimate. ${ci}` : `${what}: point estimate.`];
    }
    if (plot === "cost") return barNote(costCaption(costChart, costUnit, costScale, marks.whiskers));
    if (plot === "speed") return barNote(speedCaption(speedChart, marks.whiskers));
    // the lollipop (Temperature 0 → dots) draws no whiskers: the segment between the two dots takes the row
    return barNote(stabCaption(stabChart, stabT0Draw, stab.sameRuns, marks.whiskers && !(stabT0Draw === "dots" && stabT0Drawn), stab.runsNotes));
  };
  // A bar chart's caption (opsRows.ts, written for a filled bar) names the Fill mode: its leading "Bar:" becomes "Hatched bar:" and the like; a caption
  // that does not open on the bar (Cost, throughput) is prefixed with it instead. Filled bars, and the dot and scatter views, keep the caption as written.
  const barWord = fillMode === "hatched" ? "Hatched bar" : fillMode === "outline" ? "Outlined bar" : "Hatched, outlined bar";
  const barNote = (lines: string[]): string[] => columnNote(!hasBars || fillMode === "filled" || !lines.length ? lines : [lines[0].startsWith("Bar:") ? barWord + lines[0].slice(3) : `${barWord}: ${lines[0][0].toLowerCase()}${lines[0].slice(1)}`, ...lines.slice(1)]);
  // In columns (Orientation → vertical) the caption's bar is a column: "Bar:" / "Hatched bar:" become "Column:" / "Hatched column:", a dot chart's "Dot:" says one column
  // per model, and a caption that opens on neither (filled Cost bars, throughput) gets the columns named at its end.
  const columnNote = (lines: string[]): string[] => {
    if (!vertical || !lines.length) return lines;
    const [first, ...rest] = lines;
    const m = /^((?:Hatched, outlined|Hatched|Outlined) bar|Bar):/.exec(first);
    if (m) return [`${m[1].replace(/bar$/i, m[1] === "Bar" ? "Column" : "column")}:${first.slice(m[0].length)}`, ...rest];
    if (first.startsWith("Dot:")) return [`Dot, one column per model:${first.slice(4)}`, ...rest];
    return [`${first} One column per model.`, ...rest];
  };
  const legendLines = legendText();
  /** A bar chart's host: the filling canvas in columns (the chart sizes to its box), the chart alone in rows (it sizes to them). */
  const barHost = (chart: React.ReactNode) => (vertical ? <div className="studio-canvas">{chart}</div> : chart);
  const showIssue = plot === "pr" || (plot === "cost" && costChart === "scatter");
  /** e.g. jev-recall-precision-map-trec-linkedin-1200x675@2x.png; the size is the panel's rendered CSS size (the PNG is that × scale). */
  const exportName = (el: HTMLElement) => {
    const chartId = plot === "pr" ? chart : plot === "cost" ? costChart : plot === "speed" ? speedChart : stabChart;
    const styleId = style === "custom" && schemeName.trim() ? `custom-${schemeName.trim()}` : style;
    const t0Id = plot === "stability" && stabT0Draw !== "off" ? `t0-${stabT0Draw}` : "";
    return `${slug(["jev", plot === "pr" ? "recall-precision" : plot, chartId, t0Id, vertical ? "vertical" : "", plot === "pr" && chart === "map" && swap ? "precision-x" : "", corpus, styleId, colorMode === "style" ? "" : colorMode, byMaker ? "by-maker" : byFamily ? "by-family" : ""].join("-"))}-${el.offsetWidth}x${el.offsetHeight}@${exScale}x.png`;
  };
  const exportSize = `${w * Number(exScale)} × ${fills ? h * Number(exScale) : "auto"} px`;

  // The sections' one-line summaries while closed (Inspector.tsx summarize): the values a closed section holds, in the order its controls come.
  const markText = `${fills && logos === "all" ? "logos" : MARK_SHAPES.find((m) => m.id === mark)?.label} ${markSize.toUpperCase()}${jevSize === "same" ? "" : ` · Jev ${jevSize === "xxl" ? "2XL" : jevSize.toUpperCase()}`}`;
  const chartSummary = summarize(
    plot === "pr" && chart, plot === "pr" && (axes === "full" ? "0–100%" : axes === "zoom" ? "fit to data" : `${ax.xlo}–${ax.xhi}%${chart === "map" ? ` × ${ax.ylo}–${ax.yhi}%` : ""}`), plot === "pr" && chart === "map" && swap && "precision on x",
    plot === "cost" && (costChart === "scatter" ? "cost vs recall" : costChart === "dots" ? "dots · log" : `bars · ${costScale}`), plot === "cost" && COST_UNIT[costUnit].axis,
    plot === "speed" && (speedChart === "throughput" ? "docs per hour" : `${speedChart === "dots" ? "dots · log" : "bars"} · ${speedUnit} per document`),
    plot === "stability" && (stabChart === "agree" ? "agreement · zoomed" : stabChart === "dots" ? "dots" : "disagreement bars"),
    plot === "stability" && (stabT0 === "off" ? "default sampling" : stabT0 === "t0" ? "t = 0 only" : `t = 0 ${STAB_T0.find((o) => o.id === stabT0)?.label}${stabT0Tag ? "" : " · no tag"}${stabT0Key ? "" : " · no key"}`),
    plot === "stability" && hideUnmeasured && "unmeasured hidden", vertical && "vertical",
    ticks !== "normal" && (ticks === "none" ? "no gridlines" : `${ticks} gridlines`), markText,
    // the interval mark: "filled boxes" / "hatched ellipses" in the area modes (the Fill folded in), the mode's own name otherwise; the bar charts name their Fill alone
    plot === "pr" && (showFill ? `${FILL_MODES.find((m) => m.id === fillMode)?.label} ${interval === "ellipse" ? "ellipses" : "boxes"}` : INTERVAL_MODES.find((m) => m.id === interval)?.label),
    hasBars && `${FILL_MODES.find((m) => m.id === fillMode)?.label} bars`, fills && `labels ${labelsMode}`, fills && pointLabels && leaders && "leaders", byMaker ? "key by maker" : byFamily && "key by family",
  );
  const canvasSummary = summarize(`${w} × ${fills ? h : "auto"} px`, title.trim() && `“${title.trim()}”`, frame ? "framed" : "plain", legend ? "legend" : "no legend", LOGOS_OPTIONS.find((o) => o.id === logos)?.label, BG_SUMMARY[bg]);
  const styleSummary = summarize(
    STYLES.find((s) => s.id === style)?.label, style === "custom" && schemeName.trim(),
    colorMode === "style" ? null : colorMode === "custom" ? "custom colours" : PALETTES.find((p) => p.id === colorMode)?.label, `Text ${text.toUpperCase()}`, `${contrast} contrast`,
  );
  const schemeSummary = summarize(savedName ? `${savedName} (saved)` : schemeName.trim() ? `${schemeName.trim()} (unsaved)` : "unnamed", `${Object.keys(schemes).length} saved`, (scheme["--sans"] ?? "").split(",")[0].replace(/["']/g, "").trim());
  const exportSummary = summarize(`${exScale}×`, exportSize, exBg === "panel" ? "panel colour" : "transparent");

  return (
    <div className="page studio">
      <header className="masthead">
        <h1 className="title"><em>Studio ·</em> Jev vs Frontier LLMs</h1>
        <span className="studio-hint">Set the chart up here, then screenshot the panel below. Controls never draw on the panel.</span>
        <span className="theme"><Seg value={theme} onChange={setTheme} options={THEME_OPTIONS} /></span>
      </header>

      {/* Top bar: what is plotted, and the PNG export at the right (the export's scale and backdrop are in the Export section below). */}
      <div className="controls studio-bar">
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
        <span className="studio-bar-r">
          {exStatus && <span className={`studio-status${exStatus.err ? " err" : ""}`} role="status">{exStatus.msg}</span>}
          <span className="studio-hint small" title="The PNG's pixel size: the panel × the Export scale">{exportSize}</span>
          <button type="button" className="studio-btn primary" onClick={onDownload} disabled={exStatus?.busy} title="Save the chart area as a PNG file">Download PNG</button>
          <button type="button" className="studio-btn" onClick={onCopy} disabled={exStatus?.busy} title="Copy the chart area as a PNG image">Copy PNG</button>
        </span>
      </div>

      {/* Presets row: the whole panel of settings (every control on this page, studioState.ts) saved by name in this browser, as a JSON file, or as a link. */}
      <div className="controls studio-bar studio-presets">
        <Control label="Preset">
          <span className="select">
            <select value={cur} onChange={(e) => loadPreset(e.target.value)} aria-label="Saved presets" title="Load a saved preset: every setting on this page, the models and size included">
              <option value="">{Object.keys(presets).length ? "—" : "none saved yet"}</option>
              {Object.keys(presets).sort().map((n) => <option key={n} value={n}>{n}</option>)}
              <optgroup label="Built-in">
                {BUILTIN_PRESETS.map((b) => <option key={b.name} value={BUILTIN_PREFIX + b.name} title={b.title}>{b.name}</option>)}
              </optgroup>
            </select>
          </span>
          {cur && (
            <span className={`studio-preset-cur${modified ? " mod" : ""}`} title={modified ? `The settings differ from “${curLabel}” as ${curBuiltin ? "built in" : "saved"}${curBuiltin ? "; Save keeps your copy" : "; Update saves them over it"}` : `“${curLabel}” as ${curBuiltin ? "built in" : "saved"}`}>
              {curLabel}{modified && <span className="dot"> •</span>}
            </span>
          )}
          {cur && modified && !curBuiltin && <button type="button" className="studio-btn small" onClick={() => savePreset(cur)} title={`Save the current settings over “${curLabel}”`}>Update</button>}
          <button type="button" className="studio-btn small" onClick={deletePreset} disabled={!cur || !!curBuiltin} title={curBuiltin ? "Built-in presets stay" : "Remove the selected preset from this browser"}>Delete</button>
        </Control>
        <Control label="Save">
          <span className="studio-size">
            <input type="text" className="name" value={presetName} onChange={(e) => setPresetName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") savePreset(presetName); }} placeholder="name" spellCheck={false} aria-label="preset name" />
          </span>
          <button type="button" className="studio-btn small" onClick={() => savePreset(presetName)} title="Store every current setting under this name in this browser (asks before overwriting another preset)">Save</button>
          <button type="button" className="studio-btn small" onClick={onSaveAs} title="Store every current setting under a new name">Save as…</button>
          {canRename && <button type="button" className="studio-btn small" onClick={renamePreset} title={`Rename “${curLabel}” to “${renameName}” (its settings stay as saved)`}>Rename</button>}
        </Control>
        <Control label="File">
          <button type="button" className="studio-btn small" onClick={exportPreset} title="Download every current setting as <name>.studio.json, for another browser">Export JSON</button>
          <label className="studio-btn small" title="Load a preset file written by Export JSON (one preset, or an array or map of them); the first is applied, all are saved">
            Import JSON
            <input type="file" accept=".json,application/json" hidden onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; void importPresets(f); }} />
          </label>
        </Control>
        <span className="studio-bar-r">
          {psMsg && <span className="studio-status" role="status">{psMsg}</span>}
          <button type="button" className="studio-btn small" onClick={copyLink} title="Copy this page's address with every setting in it (#p=…), to open elsewhere or send">Copy link</button>
          <button type="button" className="studio-btn small" onClick={resetAll} title="Every setting back to its default, the models and size included">Reset to defaults</button>
        </span>
      </div>

      {/* Inspector (components/Inspector.tsx): every other control, grouped in disclosure sections that summarise their values while closed. */}
      <div className="studio-ins">
        <Section id="chart" title="Chart" open={!!sections.open.chart} onToggle={() => sections.toggle("chart")} summary={chartSummary}>
          {plot === "pr" && (
            <>
              <Control label="View">
                <Seg value={chart} onChange={setChart} options={[{ id: "map", label: "map" }, { id: "ranked", label: "ranked" }]} />
              </Control>
              <Control label="Axes">
                <Seg value={axes} onChange={setAxes} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }, { id: "custom", label: "custom" }]} />
                {axes === "custom" && (
                  <span className="studio-axes">
                    {/* the bounds are per metric; the bracketed axis letter follows the Axes orientation control */}
                    <span className="studio-size">
                      <span className="unit">{chart === "map" ? `recall (${swap ? "y" : "x"})` : "both panels"}</span>
                      <input type="number" min={0} max={100} step={5} value={ax.xlo} onChange={setBound("xlo")} aria-label="recall axis minimum, percent" />
                      <span className="x">–</span>
                      <input type="number" min={0} max={100} step={5} value={ax.xhi} onChange={setBound("xhi")} aria-label="recall axis maximum, percent" />
                      <span className="unit">%</span>
                    </span>
                    {chart === "map" && (
                      <span className="studio-size">
                        <span className="unit">precision ({swap ? "x" : "y"})</span>
                        <input type="number" min={0} max={100} step={5} value={ax.ylo} onChange={setBound("ylo")} aria-label="precision axis minimum, percent" />
                        <span className="x">–</span>
                        <input type="number" min={0} max={100} step={5} value={ax.yhi} onChange={setBound("yhi")} aria-label="precision axis maximum, percent" />
                        <span className="unit">%</span>
                      </span>
                    )}
                  </span>
                )}
              </Control>
              {/* Axes orientation (PRScatter.tsx `swap`): which metric runs along the bottom; the ranked view is not an x/y plot */}
              {chart === "map" && (
                <Control label="Orientation">
                  <Seg value={swap ? "precision" : "recall"} onChange={(x) => setSwap(x === "precision")} options={[{ id: "recall", label: "recall → x", title: "Recall along the bottom, precision up the side (the site's map)" }, { id: "precision", label: "precision → x", title: "Precision along the bottom, recall up the side" }]} />
                </Control>
              )}
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
              {/* Temperature 0 (opsRows.ts StabT0): the default cell alone, both cells per model as paired bars or a lollipop, or the t = 0 cell alone */}
              <Control label="Temperature 0">
                <Seg value={stabT0} onChange={setStabT0} options={STAB_T0.map((o) => ({ id: o.id, label: o.label, title: o.id === "off" ? o.title : stab.hasT0 ? o.title : "No t = 0 cell among the selected models" }))} />
                {stabT0 === "paired" && stabChart === "dots" && <span className="studio-hint small">on the dot chart, paired bars draw as the dots</span>}
                {stabT0 !== "off" && !stab.hasT0 && <span className="studio-hint small">no selected model has a t = 0 cell</span>}
              </Control>
              {stabPaired(stabT0) && (
                <Control label="t = 0 marks">
                  <Seg value={stabT0Tag ? "on" : "off"} onChange={(x) => setStabT0Tag(x === "on")} options={[{ id: "on", label: "t = 0 label", title: "A small grey “t = 0” tag after the temperature-0 value" }, { id: "off", label: "no label", title: "The temperature-0 value alone" }]} />
                  <Seg value={stabT0Key ? "on" : "off"} onChange={(x) => setStabT0Key(x === "on")} options={[{ id: "on", label: "key", title: legend ? "A two-entry key (default sampling / temperature 0) above the rows" : "Shown when Canvas → Legend is on" }, { id: "off", label: "no key", title: "No key on the chart; the caption still names the reruns" }]} />
                  {!legend && stabT0Key && <span className="studio-hint small">Canvas → Legend is off, so the key is hidden</span>}
                </Control>
              )}
              <Control label="Unmeasured">
                <Seg value={hideUnmeasured ? "hide" : "show"} onChange={(x) => setHideUnmeasured(x === "hide")} options={[{ id: "show", label: "list unmeasured" }, { id: "hide", label: "hide unmeasured" }]} />
              </Control>
            </>
          )}
          {/* Orientation (StudioCharts.tsx Orient): the bar charts as rows (names down the left) or columns (names along the bottom, values up the axis) */}
          {barPlot && (
            <Control label="Orientation">
              <Seg value={orient} onChange={setOrient} options={[{ id: "h", label: "horizontal", title: "Rows: model names down the left, the value axis along the bottom (the site's layout)" }, { id: "v", label: "vertical", title: "Columns rising from a baseline: model names along the bottom, values up the left axis; the chart fills the panel's height" }]} />
            </Control>
          )}
          {/* one Gridlines setting for every plot's axes (ticks.ts): after Axes on the recall/precision plot, after the chart's own controls on the others */}
          <Control label="Gridlines">
            <Seg value={ticks} onChange={setTicks} options={TICK_DENSITIES} />
          </Control>
          {/* the shape control steps aside where every point's mark is its vendor glyph (a scatter with all logos on); the size controls scale either */}
          {!(fills && logos === "all") && (
            <Control label="Marks">
              <Seg value={mark} onChange={setMark} options={MARK_SHAPES.map((m) => ({ id: m.id, label: m.label }))} />
              {fills && logos === "jev" && <span className="studio-hint small">the LLMs' mark; the Jev logos stay</span>}
            </Control>
          )}
          <Control label="Mark size">
            <Seg value={markSize} onChange={setMarkSize} options={[{ id: "s", label: "S", title: "0.75× the site's mark" }, { id: "m", label: "M", title: "The site's mark size" }, { id: "l", label: "L", title: "1.5×" }, { id: "xl", label: "XL", title: "2.2×, for logos inside wide interval boxes" }]} />
            {fills && logos === "all" && <span className="studio-hint small" title="Switch Canvas → Panel to Jev logos only or names only to choose a mark shape">logos are the marks</span>}
          </Control>
          {/* the Jev rows' own size (JevMarkSize): their logo or mark alone, the LLMs' and Laya's untouched; `= marks` follows Mark size */}
          <Control label="Jev mark size">
            <Seg
              value={jevSize} onChange={setJevSize}
              options={[
                { id: "same", label: "= marks", title: "The Jev rows' marks at the Mark size, like every other" },
                { id: "s", label: "S", title: "Jev marks and logos at 0.75× the site's mark, whatever Mark size is" }, { id: "m", label: "M", title: "Jev marks at the site's size" },
                { id: "l", label: "L", title: "1.5×" }, { id: "xl", label: "XL", title: "2.2×" }, { id: "xxl", label: "2XL", title: "3×, for a Jev logo that dominates its interval box" },
              ]}
            />
          </Control>
          {/* the interval mark's shape (PRScatter.tsx IntervalMode) on the map; the ranked view takes what applies to its row whiskers (PRRail.tsx) */}
          {plot === "pr" && (
            <Control label="Interval">
              <Seg value={interval} onChange={setIntervalMode} options={INTERVAL_MODES.map((m) => ({ id: m.id, label: m.label, title: m.title }))} />
              {chart === "ranked" && <span className="studio-hint small">{interval === "none" ? "row whiskers off" : intervalArea ? "plain row whiskers" : "row whiskers with end caps"}</span>}
            </Control>
          )}
          {/* one Fill setting for the map's interval boxes or ellipses and the bar charts' bars; hidden on the views with neither (whiskers, brackets, ranked, dots, scatter) */}
          {showFill && (
            <Control label="Fill">
              <Seg value={fillMode} onChange={setFillMode} options={FILL_MODES.map((m) => ({ id: m.id, label: m.label, title: m.title }))} />
            </Control>
          )}
          {fills && (
            <Control label="Labels">
              <Seg value={labelsMode} onChange={setLabelsMode} options={[{ id: "beside", label: "beside", title: "Each model's name next to its mark" }, { id: "legend", label: "legend", title: "A legend row at the top of the panel (square swatches and names); no names on the plot" }]} />
            </Control>
          )}
          {fills && pointLabels && (
            <Control label="Leaders">
              <Seg value={leaders ? "on" : "off"} onChange={(x) => setLeaders(x === "on")} options={[{ id: "off", label: "off" }, { id: "on", label: "on", title: "A hairline in the model's colour from a label the layout pushed away from its mark back to the mark; labels beside their mark get none" }]} />
            </Control>
          )}
          {/* the key (KeyMode): every plot recolours by maker or by question-form family; the scatters' legend (Labels → legend) lists the groups and keeps the point names */}
          <Control label="Key">
            <Seg
              value={key} onChange={setKey}
              options={[
                { id: "model", label: "by model", title: "Every model in its own colour; a legend (Labels → legend) lists the models" },
                { id: "maker", label: "by maker", title: `One colour per maker (${MAKERS.filter((m) => m.colorVar).map((m) => m.label).join(", ")}), taken from the style's colour for that maker's model (Jev, Laya, Sonnet, Terra, Flash); a legend lists the makers and every point keeps its own name label` },
                { id: "family", label: "by family", title: `Jev's three basic question forms (${FAMILY_MEMBERS.basic}) in one colour and its composed variants (${FAMILY_MEMBERS.composed}) in a second, set by the Basic and Composed swatches (the style's own Jev colours until changed); every other model by maker; a legend lists the families and makers and every point keeps its own name label` },
              ]}
            />
            {/* the two family swatches (famBasic / famComposed): the picker shows what the family draws in now (famShown); a pick writes it over the style's colour */}
            {byFamily && (
              <>
                <span className="studio-fam">
                  <label className="studio-swatch" title={`${FAMILIES.basic.title}. ${famBasic ? `Set to ${famBasic}` : "The style's Jev · Noul colour"}; the picker overrides it`}>
                    <input type="color" value={famShown.basic} onChange={(e) => set("famBasic", e.target.value)} aria-label="Jev basic forms colour" />
                    <span>Basic</span>
                  </label>
                  <label className="studio-swatch" title={`${FAMILIES.composed.title}. ${famComposed ? `Set to ${famComposed}` : colorMode === "style" ? "The style's own (its Jev · Score colour, or a companion hue)" : "A sibling hue of the Jev · Noul colour"}; the picker overrides it`}>
                    <input type="color" value={famShown.composed} onChange={(e) => set("famComposed", e.target.value)} aria-label="Jev composed variants colour" />
                    <span>Composed</span>
                  </label>
                </span>
                {(famBasic || famComposed) && <button type="button" className="studio-btn small" onClick={resetFamily} title="Drop both family swatches and go back to the style's own colours">reset</button>}
              </>
            )}
            {groupOf && fills && labelsMode === "legend" && <span className="studio-hint small">{byFamily ? "families and makers" : "makers"} in the legend, model names on the points</span>}
          </Control>
        </Section>

        <Section id="canvas" title="Canvas" open={!!sections.open.canvas} onToggle={() => sections.toggle("canvas")} summary={canvasSummary}>
          <Control label="Size">
            <span className="select">
              <select value={preset} onChange={(e) => { const p = PRESETS.find((x) => x.id === e.target.value); if (p) { setW(p.w); setH(p.h); } }} aria-label="size preset">
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
          <Control label="Title">
            <span className="studio-size">
              <input type="text" className="ttl" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="none" spellCheck={false} aria-label="chart title" title="A bold title at the panel's top-left, above the chart; leave empty for none. Part of the PNG export." />
            </span>
          </Control>
          <Control label="Panel">
            <Seg value={frame ? "card" : "plain"} onChange={(x) => setFrame(x === "card")} options={[{ id: "card", label: "framed" }, { id: "plain", label: "plain" }]} />
            <Seg value={legend ? "on" : "off"} onChange={(x) => setLegend(x === "on")} options={[{ id: "on", label: "legend" }, { id: "off", label: "no legend" }]} />
            <Seg value={logos} onChange={setLogos} options={LOGOS_OPTIONS} />
          </Control>
          <Control label="Background">
            <Seg value={bg} onChange={setBg} options={BG_OPTIONS} />
          </Control>
        </Section>

        <Section id="style" title="Style" open={!!sections.open.style} onToggle={() => sections.toggle("style")} summary={styleSummary}>
          <Control label="Style" className="wide">
            <Seg value={style} onChange={onStyle} options={STYLES.map((s) => ({ id: s.id, label: s.label, title: s.title }))} />
          </Control>
          <Control label="Colors" className="wide">
            <Seg
              value={colorMode} onChange={onColorMode}
              options={[
                { id: "style" as ColorMode, label: "style's own", title: "The model colours the Style preset defines" },
                ...PALETTES.map((p) => ({ id: p.id as ColorMode, label: p.label, title: p.title })),
                { id: "custom" as ColorMode, label: "custom", title: "Pick each model's colour; starts from the colours on screen" },
              ]}
            />
            {colorMode === "custom" && (
              <>
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
                </span>
                <button type="button" className="studio-btn small" onClick={resetCustom} title="Drop the swatches and go back to the style's own colours">reset</button>
                {byMaker && <span className="studio-hint small">Key is by maker: each maker takes one model's swatch (TypeSafe → Jev · Noul, ConvAI → Laya, Anthropic → Sonnet 5, OpenAI → GPT-5.6 Terra, Google → Gemini 3.8 Flash)</span>}
                {byFamily && <span className="studio-hint small">Key is by family: the basic forms take the Jev · Noul swatch and the composed variants a sibling hue of it, unless the Basic and Composed swatches under Chart → Key are set; each maker takes one model's swatch (ConvAI → Laya, Anthropic → Sonnet 5, OpenAI → GPT-5.6 Terra, Google → Gemini 3.8 Flash)</span>}
              </>
            )}
          </Control>
          <Control label="Text">
            <Seg value={text} onChange={setText} options={[{ id: "s", label: "S", title: "90% of the site's text size" }, { id: "m", label: "M", title: "The site's text size" }, { id: "l", label: "L", title: "120%" }, { id: "xl", label: "XL", title: "145%, for phone-sized viewing" }]} />
          </Control>
          <Control label="Contrast">
            <Seg value={contrast} onChange={setContrast} options={[{ id: "normal", label: "normal" }, { id: "high", label: "high", title: "Full-ink labels, darker and thicker axes and whiskers, stronger fills, larger marks" }]} />
          </Control>
        </Section>

        {style === "custom" && (
          <Section id="scheme" title="Scheme" open={!!sections.open.scheme} onToggle={() => sections.toggle("scheme")} summary={schemeSummary}>
            <Control label="Name">
              <span className="studio-size">
                <input type="text" className="name" value={schemeName} onChange={(e) => setSchemeName(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") saveScheme(); }} placeholder="name" spellCheck={false} aria-label="scheme name" />
              </span>
              <button type="button" className="studio-btn small" onClick={saveScheme} title="Store these values under this name in this browser; an existing name is overwritten">Save</button>
              <button type="button" className="studio-btn small" onClick={exportScheme} title="Download these values as <name>.json, for another browser">Export JSON</button>
              {scMsg && <span className="studio-status" role="status">{scMsg}</span>}
            </Control>
            <Control label="Saved">
              <span className="select">
                <select value={savedName} onChange={(e) => loadScheme(e.target.value)} aria-label="Saved schemes">
                  <option value="">{Object.keys(schemes).length ? "—" : "none saved yet"}</option>
                  {Object.keys(schemes).sort().map((n) => <option key={n} value={n}>{n}</option>)}
                  <optgroup label="Built-in">
                    {BUILTIN_SCHEMES.map((b) => <option key={b.name} value={BUILTIN_PREFIX + b.name} title={`The ${b.name} preset's own values, as a starting point; Save keeps your copy`}>{b.name}</option>)}
                  </optgroup>
                </select>
              </span>
              <button type="button" className="studio-btn small" onClick={deleteScheme} disabled={!savedName} title="Remove the selected saved scheme from this browser">Delete</button>
              <label className="studio-btn small" title="Load a scheme file written by Export JSON (or a bare variable map)">
                Import JSON
                <input type="file" accept=".json,application/json" hidden onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; void importScheme(f); }} />
              </label>
            </Control>
            <Control label="Surface" className="wide">
              <span className="studio-swatches">
                {SCHEME_SURFACE.map((x) => <SchemeColor key={x.v} v={x.v} label={x.label} value={scheme[x.v] ?? ""} onChange={(val) => setVar(x.v, val)} />)}
              </span>
            </Control>
            <Control label="Alpha" className="wide">
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
            <Control label="Font" className="wide">
              <span className="studio-size">
                <input type="text" className="font" value={scheme["--sans"] ?? ""} onChange={(e) => setVar("--sans", e.target.value)} spellCheck={false} aria-label="panel font family, CSS" title="The panel's font-family list, as CSS" />
              </span>
            </Control>
            <Control label="Models" className="wide">
              <button type="button" className="studio-btn small" onClick={() => setShowModels((s) => !s)} aria-expanded={showModels}>{showModels ? "hide" : "show"} {SCHEME_MODELS.length} colours</button>
              {showModels && colorMode !== "style" && <span className="studio-hint small">Colors is on “{colorMode === "custom" ? "custom" : PALETTES.find((p) => p.id === colorMode)?.label}”, which paints over these; set it to style's own to see them.</span>}
              {showModels && (
                <span className="studio-swatches">
                  {SCHEME_MODELS.map((x) => <SchemeColor key={x.v} v={x.v} label={x.label} value={scheme[x.v] ?? ""} onChange={(val) => setVar(x.v, val)} />)}
                </span>
              )}
            </Control>
          </Section>
        )}

        <Section id="export" title="Export" open={!!sections.open.export} onToggle={() => sections.toggle("export")} summary={exportSummary}>
          <Control label="Scale">
            <Seg value={exScale} onChange={setExScale} options={[{ id: "1", label: "1×", title: "PNG at the panel's size" }, { id: "2", label: "2×", title: "Twice the panel's size (retina)" }, { id: "3", label: "3×", title: "Three times the panel's size" }]} />
            <span className="studio-hint small">{exportSize}, no frame</span>
          </Control>
          <Control label="Backdrop">
            <Seg value={exBg} onChange={setExBg} options={[{ id: "panel", label: "panel", title: "Filled with the style's panel colour" }, { id: "transparent", label: "transparent", title: "Alpha where the panel would be" }]} />
          </Control>
        </Section>
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
            style={{ ...colorVars, ...sliderVars, ...bgVars, ...famVars, width: w, height: fills ? h : undefined, "--fs-legend": `${12 * ts}px`, "--mark-user": ms, "--mark-jev": jms } as React.CSSProperties}
          >
            {title.trim() ? <div className="studio-title">{title.trim()}</div> : null}
            {plot === "pr" && chart === "map" && (
              <div className="studio-canvas">
                <PRScatter items={keyedItems} zoom={zoom} domain={domain} swap={swap} emptyText={emptyText} logos={logos} fill textScale={ts} leaders={leaders} labels={labelsMode} mark={mark} markSize={ms} jevMarkSize={jms} boxes={fillMode} interval={interval} bg={plotBg("dots")} groups={groups} ticks={ticks} />
              </div>
            )}
            {plot === "pr" && chart === "ranked" && <PRRail items={keyedItems} zoom={zoom} range={range} sortBy="recall" logos={logos} textScale={ts} mark={mark} bg={plotBg("dots")} interval={interval} ticks={ticks} />}
            {plot === "cost" && costChart === "scatter" && (
              <div className="studio-canvas">
                <StudioScatter pts={costPts(sel, v, costUnit).map(keyed)} xLabel={`${cu.axis} (log)`} yLabel={v.issue ? `Recall · ${issueLabel(meta, v.issue).split(" · ")[0]}` : "Recall"} fmtX={fmtMoneyTick} logos={logos} emptyText={emptyText} textScale={ts} leaders={leaders} labels={labelsMode} mark={mark} markSize={ms} jevMarkSize={jms} bg={plotBg("none")} groups={groups} ticks={ticks} />
              </div>
            )}
            {/* the bar charts: in columns (vertical) inside the filling canvas, as the scatters; as rows they size themselves */}
            {plot === "cost" && costChart !== "scatter" && barHost(
              <StudioBars rows={costRows(sel, costUnit).map(keyed)} kind={costChart === "dots" ? "dot" : "bar"} scale={costChart === "dots" ? "log" : costScale} axis={costAxis(costChart, costUnit, costScale)} fmtTick={fmtMoneyTick} logos={logos} textScale={ts} mark={mark} bg={plotBg("none")} bars={fillMode} ticks={ticks} orient={orient} />,
            )}
            {plot === "speed" && barHost(
              <StudioBars
                rows={speedRows(sel, speedChart, speedUnit).map(keyed)} kind={speedChart === "dots" ? "dot" : "bar"} scale={speedChart === "dots" ? "log" : "linear"} sort={speedChart === "throughput" ? "desc" : "asc"}
                axis={speedAxis(speedChart)}
                fmtTick={speedChart === "throughput" ? (t) => fmtInt(Math.round(t)) : fmtMsTick} logos={logos} textScale={ts} mark={mark} bg={plotBg("none")} bars={fillMode} ticks={ticks} orient={orient}
              />,
            )}
            {plot === "stability" && barHost(
              <StudioBars
                rows={stabRowsKeyed} kind={stabDots ? "dot" : "bar"} sort={stabChart === "agree" ? "desc" : "asc"} domain={stabChart === "agree" ? stab.agreeDomain : undefined}
                axis={stabAxis(stabChart, stabT0Draw)}
                fmtTick={fmtPctTick} logos={logos} textScale={ts} mark={mark} bg={plotBg("none")} bars={fillMode} ticks={ticks}
                t0={stabT0Draw === "paired" ? "paired" : stabT0Draw === "dots" ? "dots" : "none"} t0Tag={stabT0Tag} t0Key={legend && stabT0Key} orient={orient}
              />,
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
      <p className="studio-foot">Drag the panel's bottom-right corner to resize, or type a size under Canvas. {w} × {fills ? h : "auto"} px.</p>
    </div>
  );
}
