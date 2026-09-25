import { DATA, DEFAULT_CORPUS, DEFAULT_ON, PRIMARY_BY_KEY, siteCorpus } from "./data";
import type { Chart } from "./App";
import { INTERVAL_MODES, MARK_SHAPES, type IntervalMode, type LabelsMode, type MarkShape } from "./components/PRScatter";
import { FILL_MODES, type FillMode } from "./components/hatch";
import { TICK_DENSITIES, type TickDensity } from "./components/ticks";
import type { CostChart, CostScale, CostUnit, SpeedChart, SpeedUnit, StabChart, StabSetting } from "./opsRows";
import type { ExportBackground } from "./exportPng";
import { PALETTES, varOf, type PaletteId } from "./palettes";
import type { LogosMode } from "./logos";

/**
 * The studio's settings as one object (StudioPage.tsx holds one `StudioState` in state), and the registry that knows, for each field, its default,
 * how to validate a value that came from outside (localStorage, a preset file, a share link) and, where the field was always remembered, the
 * localStorage key and string form it has had, so a reload reads exactly what the page wrote before this module existed. Fields without a key
 * (what is plotted, the models, the panel size) start from their default on every visit, as they always did, and are still captured in presets.
 *
 * Presets (StudioPage.tsx Presets row): `StudioPreset` is `{ v: 1, name, saved, state }`, `state` being `snapshot()` of a StudioState, JSON-safe
 * (the models set as an array). `fromPreset` rebuilds a StudioState from one: unknown keys are ignored, bad or missing values fall back to the
 * default, enums are checked against their option lists, the issue against the corpus. The same object, base64url-encoded, is the share link's
 * `#p=` payload (encodeHash / decodeHash). Built-in presets (BUILTIN_PRESETS) are partial states over the defaults.
 */

export const PLOTS = ["pr", "cost", "speed", "stability"] as const;
/** The four plots. `pr` is the site's recall/precision chart (map or ranked); the others are the studio's own bar, dot and scatter charts (opsRows.ts). */
export type Plot = (typeof PLOTS)[number];
export const PLOT_STYLES = ["site", "journal", "newsroom", "linkedin", "slate", "economist", "epoch", "typesafe", "custom"] as const;
export type PlotStyle = (typeof PLOT_STYLES)[number];
export const isPlotStyle = (s: string | null): s is PlotStyle => (PLOT_STYLES as readonly string[]).includes(s ?? "");
/** Mark sizes (Mark size control): the multiplier on every point mark and vendor glyph (--mark-user). */
export type MarkSize = "s" | "m" | "l" | "xl";
export const MARK_SCALE: Record<MarkSize, number> = { s: 0.75, m: 1, l: 1.5, xl: 2.2 };
/** Jev mark size: the Jev rows' own factor, or `same`, the Mark size. */
export type JevMarkSize = "same" | MarkSize | "xxl";
export const JEV_SCALE: Record<Exclude<JevMarkSize, "same">, number> = { ...MARK_SCALE, xxl: 3 };
/** Text sizes: one factor on every font size in the panel. M is the site's own size. */
export type TextSize = "s" | "m" | "l" | "xl";
export const TEXT_SCALE: Record<TextSize, number> = { s: 0.9, m: 1, l: 1.2, xl: 1.45 };
export type Contrast = "normal" | "high";
/** Colors (palettes.ts): `style` leaves the Style preset's own model colours; a palette id writes that palette over them; `custom` the user's swatches. */
export type ColorMode = "style" | PaletteId | "custom";
export type KeyMode = "model" | "maker";
export type ExportScale = "1" | "2" | "3";
export type Bg = "auto" | "off" | "dots" | "grid";
export type Axes = "full" | "zoom" | "custom";
export type Theme = "dark" | "light";
export type AxBounds = { xlo: number; xhi: number; ylo: number; yhi: number };
export type Vars = Record<string, string>;

/** Custom scheme (Style → Custom) variables: the surface and ink set, one colour per roster model, the sliders, and the copied-only extras. */
export type SchemeVar = { v: string; label: string };
export const SCHEME_SURFACE: SchemeVar[] = [
  { v: "--bg", label: "page" }, { v: "--panel", label: "panel" }, { v: "--ink", label: "ink" }, { v: "--ink-2", label: "ink 2" }, { v: "--ink-3", label: "ink 3" }, { v: "--ink-4", label: "ink 4" },
  { v: "--line", label: "line" }, { v: "--line-2", label: "line 2" }, { v: "--grid", label: "grid" }, { v: "--dots", label: "dots" }, { v: "--axis", label: "axis" }, { v: "--hl", label: "highlight" },
];
export const SCHEME_MODELS: SchemeVar[] = Object.entries(PRIMARY_BY_KEY).flatMap(([k, m]) => { const v = varOf(k); return v ? [{ v, label: m.short }] : []; });
/** `dflt` is shown, and drawn, while the scheme has no value for the variable (the charts' own fallback). */
export const SCHEME_SLIDERS: (SchemeVar & { min: number; max: number; step: number; dflt: number; title: string })[] = [
  { v: "--box-alpha", label: "box fill", min: 0, max: 0.6, step: 0.01, dflt: 0.14, title: "Opacity of the 95% interval boxes on the recall/precision map: the shade of a filled box, or the lines of a hatched one (Fill control)" },
  { v: "--box-stroke-w", label: "outline px", min: 0, max: 3, step: 0.25, dflt: 0.75, title: "Width of the interval boxes' and bars' outline, in px (Fill → outline or hatched + outline; also a preset's own box hairline, as Journal's)" },
  { v: "--bar-alpha", label: "bar fill", min: 0.1, max: 1, step: 0.01, dflt: 0.55, title: "Opacity of the bars (Cost, Speed and Stability bar charts): the shade of a filled bar, or the lines of a hatched one (Fill control)" },
];
// --grid-x and --axis-y (vertical gridlines, y-axis line; unset they follow --grid / --axis) and --box-stroke (a preset's box outline opacity in the filled and hatched
// Fill modes; Journal's hairline) have no control but are copied, saved and imported, so a Custom made from Epoch keeps its horizontal-only grid
export const SCHEME_VARS = new Set([...SCHEME_SURFACE, ...SCHEME_MODELS, ...SCHEME_SLIDERS].map((x) => x.v).concat("--sans", "--grid-x", "--axis-y", "--box-stroke"));
export const isVars = (o: unknown): o is Vars => !!o && typeof o === "object" && !Array.isArray(o) && Object.values(o).every((x) => typeof x === "string");
/** Only the editor's variables, as short strings: what a saved or imported scheme may set on the panel. */
export const cleanVars = (o: Vars): Vars => Object.fromEntries(Object.entries(o).filter(([k, v]) => SCHEME_VARS.has(k) && v.length <= 200));

/** Every setting the studio holds; one preset captures all of them. */
export type StudioState = {
  plot: Plot; corpus: string; issue: string | null; on: Set<string>;
  chart: Chart; costChart: CostChart; costUnit: CostUnit; costScale: CostScale; speedChart: SpeedChart; speedUnit: SpeedUnit; stabChart: StabChart; stabSetting: StabSetting; hideUnmeasured: boolean;
  axes: Axes; ax: AxBounds; swap: boolean; ticks: TickDensity;
  mark: MarkShape; markSize: MarkSize; jevSize: JevMarkSize; fill: FillMode; interval: IntervalMode; labels: LabelsMode; leaders: boolean; key: KeyMode;
  w: number; h: number; title: string; frame: boolean; legend: boolean; logos: LogosMode; bg: Bg;
  style: PlotStyle; colors: ColorMode; custom: Record<string, string>; text: TextSize; contrast: Contrast;
  scheme: Vars; schemeName: string;
  exScale: ExportScale; exBg: ExportBackground;
  sections: Record<string, boolean>; theme: Theme;
};

/** How a remembered field has always been written to localStorage: the raw string, "on"/"off" for a boolean, or JSON. */
type Store = "string" | "onoff" | "json";
type Field<T> = {
  dflt: T;
  /** localStorage key, for the fields the page remembered before presets existed; absent, the field starts from `dflt` on every visit. */
  key?: string;
  store?: Store;
  /** A value from outside (storage, file, link) as a valid T, or undefined for the default. */
  coerce: (raw: unknown) => T | undefined;
  /** The JSON form for presets where T is not JSON already (the models set). */
  toJson?: (v: T) => unknown;
};
type Fields = { [K in keyof StudioState]: Field<StudioState[K]> };

const oneOf = <T extends string>(ids: readonly T[]) => (raw: unknown): T | undefined => (typeof raw === "string" && (ids as readonly string[]).includes(raw) ? (raw as T) : undefined);
const bool = (raw: unknown): boolean | undefined => (typeof raw === "boolean" ? raw : raw === "on" ? true : raw === "off" ? false : undefined);
const str = (max: number) => (raw: unknown): string | undefined => (typeof raw === "string" && raw.length <= max ? raw : undefined);
const clampInt = (n: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, Math.round(n)));
const int = (lo: number, hi: number) => (raw: unknown): number | undefined => (typeof raw === "number" && Number.isFinite(raw) ? clampInt(raw, lo, hi) : undefined);
const isRecord = (o: unknown): o is Record<string, unknown> => !!o && typeof o === "object" && !Array.isArray(o);
const isOpenMap = (o: unknown): o is Record<string, boolean> => isRecord(o) && Object.values(o).every((v) => typeof v === "boolean");
const ids = <T extends string>(xs: readonly { id: T }[]) => xs.map((x) => x.id);

export const DEFAULT_SECTIONS: Record<string, boolean> = { chart: true, canvas: true, style: false, scheme: true, export: false };
export const DEFAULT_SIZE = { w: 1200, h: 675 };

export const FIELDS: Fields = {
  plot: { dflt: "pr", coerce: oneOf(PLOTS) },
  corpus: { dflt: DEFAULT_CORPUS, coerce: (r) => (typeof r === "string" ? siteCorpus(r) : undefined) },
  issue: { dflt: null, coerce: (r) => (r === null ? null : typeof r === "string" && r.length <= 80 ? r : undefined) },
  on: {
    dflt: new Set(DEFAULT_ON),
    coerce: (r) => (Array.isArray(r) ? new Set(r.filter((k): k is string => typeof k === "string" && k in PRIMARY_BY_KEY)) : undefined),
    toJson: (s) => [...s].sort(), // sorted, so the set compares by membership whatever order the picker added in
  },
  chart: { dflt: "map", coerce: oneOf(["map", "ranked"] as const) },
  costChart: { dflt: "bars", coerce: oneOf(["bars", "dots", "scatter"] as const) },
  costUnit: { dflt: "1k", coerce: oneOf(["1k", "100k", "decision"] as const) },
  costScale: { dflt: "linear", coerce: oneOf(["linear", "log"] as const) },
  speedChart: { dflt: "bars", coerce: oneOf(["bars", "dots", "throughput"] as const) },
  speedUnit: { dflt: "ms", coerce: oneOf(["ms", "s"] as const) },
  stabChart: { dflt: "bars", coerce: oneOf(["bars", "agree", "dots"] as const) },
  stabSetting: { dflt: "default", coerce: oneOf(["default", "t0"] as const) },
  hideUnmeasured: { dflt: false, coerce: bool },
  axes: { dflt: "zoom", coerce: oneOf(["full", "zoom", "custom"] as const) },
  ax: {
    dflt: { xlo: 50, xhi: 100, ylo: 50, yhi: 100 },
    coerce: (r) => {
      if (!isRecord(r)) return undefined;
      const pct = int(0, 100), xlo = pct(r.xlo), xhi = pct(r.xhi), ylo = pct(r.ylo), yhi = pct(r.yhi);
      return xlo != null && xhi != null && ylo != null && yhi != null ? { xlo, xhi, ylo, yhi } : undefined;
    },
  },
  swap: { dflt: false, key: "studio-swap", store: "onoff", coerce: bool },
  ticks: { dflt: "normal", key: "studio-ticks", store: "string", coerce: oneOf(ids(TICK_DENSITIES)) },
  mark: { dflt: "dot", key: "studio-mark", store: "string", coerce: oneOf(ids(MARK_SHAPES)) },
  markSize: { dflt: "m", key: "studio-mark-scale", store: "string", coerce: oneOf(["s", "m", "l", "xl"] as const) },
  jevSize: { dflt: "same", key: "studio-jev-mark", store: "string", coerce: oneOf(["same", "s", "m", "l", "xl", "xxl"] as const) },
  fill: { dflt: "filled", key: "studio-boxes", store: "string", coerce: oneOf(ids(FILL_MODES)) },
  interval: { dflt: "box", key: "studio-ci", store: "string", coerce: oneOf(ids(INTERVAL_MODES)) },
  labels: { dflt: "beside", key: "studio-labels", store: "string", coerce: oneOf(["beside", "legend"] as const) },
  leaders: { dflt: false, key: "studio-leaders", store: "onoff", coerce: bool },
  key: { dflt: "model", key: "studio-key", store: "string", coerce: oneOf(["model", "maker"] as const) },
  w: { dflt: DEFAULT_SIZE.w, coerce: int(320, 4000) },
  h: { dflt: DEFAULT_SIZE.h, coerce: int(240, 4000) },
  title: { dflt: "", key: "studio-title", store: "string", coerce: str(300) },
  frame: { dflt: true, coerce: bool },
  legend: { dflt: true, coerce: bool },
  logos: { dflt: "all", key: "studio-logos", store: "string", coerce: oneOf(["all", "jev", "none"] as const) },
  bg: { dflt: "auto", key: "studio-bg", store: "string", coerce: oneOf(["auto", "off", "dots", "grid"] as const) },
  style: { dflt: "site", key: "studio-style", store: "string", coerce: oneOf(PLOT_STYLES) },
  colors: { dflt: "style", key: "studio-colors", store: "string", coerce: oneOf(["style", "custom", ...ids(PALETTES)] as const) },
  custom: {
    dflt: {}, key: "studio-colors-custom", store: "json",
    coerce: (r) => (isRecord(r) ? Object.fromEntries(Object.entries(r).filter((e): e is [string, string] => typeof e[1] === "string" && e[1].length <= 40)) : undefined),
  },
  text: { dflt: "m", key: "studio-text", store: "string", coerce: oneOf(["s", "m", "l", "xl"] as const) },
  contrast: { dflt: "normal", key: "studio-contrast", store: "string", coerce: oneOf(["normal", "high"] as const) },
  scheme: { dflt: {}, key: "studio-custom", store: "json", coerce: (r) => (isVars(r) ? cleanVars(r) : undefined) },
  schemeName: { dflt: "", key: "studio-scheme", store: "string", coerce: str(80) },
  exScale: { dflt: "2", key: "studio-export-scale", store: "string", coerce: oneOf(["1", "2", "3"] as const) },
  exBg: { dflt: "panel", key: "studio-export-bg", store: "string", coerce: oneOf(["panel", "transparent"] as const) },
  sections: { dflt: DEFAULT_SECTIONS, key: "studio-sections", store: "json", coerce: (r) => (isOpenMap(r) ? { ...DEFAULT_SECTIONS, ...r } : undefined) },
  theme: { dflt: "light", key: "theme", store: "string", coerce: oneOf(["dark", "light"] as const) },
};
export const STATE_KEYS = Object.keys(FIELDS) as (keyof StudioState)[];
/** Fields left out of the "modified since loaded" comparison: opening or closing an inspector section is not a change to the chart. */
const VOLATILE: (keyof StudioState)[] = ["sections"];

const field = <K extends keyof StudioState>(k: K): Field<StudioState[K]> => FIELDS[k];
const copy = <T,>(v: T): T => (v instanceof Set ? (new Set(v) as T) : v && typeof v === "object" ? (Array.isArray(v) ? ([...v] as T) : ({ ...v } as T)) : v);

export function defaults(): StudioState {
  const s = {} as StudioState;
  for (const k of STATE_KEYS) (s as Record<string, unknown>)[k] = copy(field(k).dflt);
  return s;
}

/** The stored string of a remembered field, in the form the page has always written. */
const encode = <K extends keyof StudioState>(k: K, v: StudioState[K]): string => {
  const f = field(k);
  return f.store === "onoff" ? (v ? "on" : "off") : f.store === "json" ? JSON.stringify(f.toJson ? f.toJson(v) : v) : String(v);
};
const decode = (store: Store | undefined, s: string): unknown => { if (store !== "json") return s; try { return JSON.parse(s); } catch { return undefined; } };

/** Every remembered field from localStorage (its own key, as before), the rest at their defaults. */
export function readStored(): StudioState {
  const s = defaults();
  for (const k of STATE_KEYS) {
    const f = field(k); if (!f.key) continue;
    const raw = localStorage.getItem(f.key); if (raw == null) continue;
    const v = f.coerce(decode(f.store, raw));
    if (v !== undefined) (s as Record<string, unknown>)[k] = v;
  }
  return s;
}

/** Write each remembered field whose stored form differs from `prev` (every one when `prev` is null). */
export function writeChanged(prev: StudioState | null, next: StudioState) {
  for (const k of STATE_KEYS) {
    const f = field(k); if (!f.key) continue;
    const s = encode(k, next[k]);
    if (prev && encode(k, prev[k]) === s) continue;
    try { localStorage.setItem(f.key, s); } catch { /* storage full or denied: the page still works for the session */ }
  }
}

// ---- presets ----

export type PresetState = Record<string, unknown>;
export type StudioPreset = { v: 1; name: string; saved: string; state: PresetState };

/** The state as JSON-safe values in registry order. */
export function snapshot(s: StudioState): PresetState {
  const out: PresetState = {};
  for (const k of STATE_KEYS) { const f = field(k); out[k] = f.toJson ? (f.toJson as (v: unknown) => unknown)(s[k]) : s[k]; }
  return out;
}
/** A StudioState from a preset's `state` (or any object): unknown keys ignored, bad values and missing keys at their defaults, the issue checked against the corpus. */
export function fromPreset(raw: unknown): StudioState {
  const s = defaults();
  if (!isRecord(raw)) return s;
  for (const k of STATE_KEYS) {
    if (!(k in raw)) continue;
    const v = field(k).coerce(raw[k]);
    if (v !== undefined) (s as Record<string, unknown>)[k] = v;
  }
  if (s.issue && !(s.issue in (DATA.corpora[s.corpus]?.issues ?? {}))) s.issue = null;
  return s;
}
export const makePreset = (name: string, s: StudioState): StudioPreset => ({ v: 1, name, saved: new Date().toISOString(), state: snapshot(s) });
export const isPreset = (o: unknown): o is StudioPreset => isRecord(o) && o.v === 1 && typeof o.name === "string" && isRecord(o.state);
const isPresetMap = (o: unknown): o is Record<string, StudioPreset> => isRecord(o) && Object.values(o).every(isPreset);
/** Two states draw the same chart (VOLATILE fields aside); both are normalised through the registry so key order and unknowns never matter. */
export const sameState = (a: StudioState, b: StudioState): boolean => STATE_KEYS.every((k) => VOLATILE.includes(k) || encode(k, a[k]) === encode(k, b[k]));

/** A preset's file (`{ v, name, saved, state }`), an array of them, or the `{ [name]: preset }` map (the localStorage form); null if none of those. */
export function parsePresetFile(text: string): Record<string, StudioPreset> | null {
  let o: unknown; try { o = JSON.parse(text); } catch { return null; }
  const clean = (p: StudioPreset): StudioPreset => ({ v: 1, name: p.name.trim().slice(0, 80) || "imported", saved: typeof p.saved === "string" ? p.saved : new Date().toISOString(), state: snapshot(fromPreset(p.state)) });
  if (isPreset(o)) { const p = clean(o); return { [p.name]: p }; }
  if (Array.isArray(o) && o.length && o.every(isPreset)) return Object.fromEntries(o.map((p) => { const c = clean(p); return [c.name, c]; }));
  if (isPresetMap(o) && Object.keys(o).length) return Object.fromEntries(Object.entries(o).map(([n, p]) => { const c = clean({ ...p, name: p.name || n }); return [n.trim() || c.name, c]; }));
  return null;
}
export const readPresets = (): Record<string, StudioPreset> => { try { const o: unknown = JSON.parse(localStorage.getItem("studio-presets") || "null"); return isPresetMap(o) ? o : {}; } catch { return {}; } };

// ---- share link: studio.html#p=<base64url of the preset JSON> ----

const b64url = (s: string): string => {
  const bytes = new TextEncoder().encode(s); let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
};
const unb64url = (s: string): string | null => {
  try { const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/")); return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0))); } catch { return null; }
};
/** The `#p=…` hash for a preset (no leading `#`). */
export const encodeHash = (p: StudioPreset): string => `p=${b64url(JSON.stringify(p))}`;
/** The preset in a page hash (`#p=…`), if it holds one. */
export function decodeHash(hash: string): StudioPreset | null {
  const p = new URLSearchParams(hash.replace(/^#/, "")).get("p"); if (!p) return null;
  const text = unb64url(p); if (text == null) return null;
  let o: unknown; try { o = JSON.parse(text); } catch { return null; }
  return isPreset(o) ? { v: 1, name: o.name.trim().slice(0, 80), saved: typeof o.saved === "string" ? o.saved : "", state: o.state } : null;
}

// ---- built-in presets: partial states over the defaults; StudioPage.tsx lists them in the select's "Built-in" group, copy-on-save ----

export const BUILTIN_PRESETS: { name: string; title: string; state: Partial<StudioState> }[] = [
  {
    name: "TypeSafe house", title: "The TypeSafe style with its profile: legend labels, diamond marks at L, plain background and panel, names only, Text M; 1200 × 675",
    // the TypeSafe style's own profile (StudioPage.tsx STYLES), so the two agree
    state: { style: "typesafe", labels: "legend", leaders: false, mark: "diamond", markSize: "l", bg: "off", frame: false, logos: "none", text: "m", contrast: "normal", colors: "style", w: 1200, h: 675 },
  },
  {
    name: "Journal figure", title: "An academic figure: the Journal style (white, serif, Okabe–Ito), Text L, filled interval boxes, no frame, plain marks without vendor logos; 1200 × 675",
    state: { style: "journal", text: "l", fill: "filled", interval: "box", frame: false, logos: "none", mark: "dot", markSize: "m", labels: "beside", bg: "auto", colors: "style", contrast: "normal", w: 1200, h: 675 },
  },
  {
    name: "Slate dark", title: "The Slate style in high contrast with Text XL, on the page's dark theme; 1200 × 675",
    state: { style: "slate", contrast: "high", text: "xl", theme: "dark", colors: "style", frame: true, bg: "auto", w: 1200, h: 675 },
  },
];
export const BUILTIN_PREFIX = "builtin:";
/** A built-in preset's full state: its values over the defaults. */
export const builtinState = (b: (typeof BUILTIN_PRESETS)[number]): StudioState => ({ ...defaults(), ...b.state });
