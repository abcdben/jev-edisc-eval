import { PRIMARY_BY_KEY } from "./data";

/**
 * Studio model colours (StudioPage.tsx Colors control). Every chart colours a model through the CSS custom property named in its roster
 * entry (data.ts ALL_PRIMARY `color`, e.g. `var(--c-jev)`), and the Style presets (styles.css `.studio-plot[data-style=…]`) redefine those
 * properties inside the panel. A palette here is one more layer on top: a model key → hex map that the page writes onto the panel as inline
 * custom properties, which beat the preset's. "Style's own" writes nothing; "custom" writes whatever the user picked.
 *
 * The named palettes give the Jev rows one warm, saturated family and the LLMs a cooler or greyer one, so the deciders read first on a
 * white, off-white or dark panel. Colours are chosen for a light panel; `forPanel` lifts them for a dark one.
 */

export type PaletteId = "ember" | "crimson" | "emerald" | "spectrum" | "plum";
export type Palette = { id: PaletteId; label: string; title: string; colors: Record<string, string> };

const JEV = ["jev@base", "jev@choice", "jev@score", "jev@decompose", "jev@ensemble", "jev@gate"] as const;
const LLM = ["claude-haiku-4.5", "claude-sonnet-5", "gpt-5.6-luna", "gpt-5.6-terra", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemma3-12b"] as const;
const map = (jev: string[], laya: string, llm: string[]): Record<string, string> => {
  const out: Record<string, string> = { "laya-ft": laya };
  JEV.forEach((k, i) => { out[k] = jev[i]; });
  LLM.forEach((k, i) => { out[k] = llm[i]; });
  return out;
};

export const PALETTES: Palette[] = [
  {
    id: "ember", label: "Ember", title: "Jev in vermilion, orange and gold; the LLMs in cool steel blues and blue-greys",
    colors: map(["#e4572e", "#f28e2b", "#d4a72c", "#b23a48", "#f4a582", "#8c2d19"], "#8e6bbf", ["#6fa3d8", "#2f6db5", "#4fb3a9", "#1e8a7e", "#9aabbe", "#6b7c90", "#b0b8c2"]),
  },
  {
    id: "crimson", label: "Crimson", title: "Jev in crimson, rose and wine; the LLMs in slate and warm greys",
    colors: map(["#c8102e", "#e0457b", "#9b1b5a", "#7a0c1e", "#f07a9a", "#5c0a2a"], "#7f5aa6", ["#6b7a8f", "#3f5470", "#8f9bab", "#55708c", "#b3bcc6", "#7f8a96", "#a2aab3"]),
  },
  {
    id: "emerald", label: "Emerald", title: "Jev in emerald, jade and forest green; the LLMs in graphite and warm greys",
    colors: map(["#1b9e77", "#5fc4a1", "#0b6e4f", "#3fa34d", "#a6d96a", "#005f3c"], "#8e6bbf", ["#8d8d8d", "#4f4f4f", "#aaa49e", "#6e6e6e", "#c4bdb5", "#8a847d", "#b1aba4"]),
  },
  {
    id: "spectrum", label: "Spectrum", title: "Every model its own hue: Jev in reds, oranges and yellow; the LLMs in blues, greens and teals",
    colors: map(["#e15759", "#f28e2b", "#e0b93b", "#b07aa1", "#ff9da7", "#9c755f"], "#af7aa1", ["#4e79a7", "#2c5985", "#59a14f", "#2a7f62", "#76b7b2", "#499894", "#bab0ac"]),
  },
  {
    id: "plum", label: "Plum", title: "Jev in plum, violet and lilac; the LLMs in sand, olive and khaki",
    colors: map(["#6a3d9a", "#9e6bd1", "#c497e3", "#4b2a70", "#b58fd6", "#8a56c8"], "#d95f02", ["#c9a66b", "#8b6f3a", "#a3a86b", "#6f7a3c", "#d9c6a5", "#a89b7f", "#bfb3a0"]),
  },
];
export const isPaletteId = (s: string | null): s is PaletteId => PALETTES.some((p) => p.id === s);

/** The CSS custom property a roster model is coloured through: `var(--c-jev)` → `--c-jev`. */
export const varOf = (key: string): string | null => PRIMARY_BY_KEY[key]?.color.match(/^var\((--[\w-]+)\)$/)?.[1] ?? null;

/** A model → hex map as the inline custom properties to set on the panel. */
export function toVars(colors: Record<string, string>, dark: boolean): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [k, hex] of Object.entries(colors)) {
    const v = varOf(k);
    if (v && hex) out[v] = dark ? forDark(hex) : hex;
  }
  return out;
}

// ---- colour arithmetic ----

/** "#rgb", "#rrggbb" or "rgb(r, g, b)" → "#rrggbb"; null if unparseable. */
export function toHex(s: string): string | null {
  const t = s.trim().toLowerCase();
  let m = t.match(/^#([0-9a-f]{3})$/);
  if (m) return "#" + m[1].split("").map((c) => c + c).join("");
  m = t.match(/^#([0-9a-f]{6})([0-9a-f]{2})?$/);
  if (m) return "#" + m[1];
  m = t.match(/^rgba?\(\s*(\d+)[\s,]+(\d+)[\s,]+(\d+)/);
  if (m) return "#" + [m[1], m[2], m[3]].map((n) => Math.min(255, Number(n)).toString(16).padStart(2, "0")).join("");
  return null;
}

function hexToHsl(hex: string): [number, number, number] {
  const r = parseInt(hex.slice(1, 3), 16) / 255, g = parseInt(hex.slice(3, 5), 16) / 255, b = parseInt(hex.slice(5, 7), 16) / 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2;
  if (max === min) return [0, 0, l];
  const d = max - min, s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
  const h = max === r ? ((g - b) / d + (g < b ? 6 : 0)) / 6 : max === g ? ((b - r) / d + 2) / 6 : ((r - g) / d + 4) / 6;
  return [h, s, l];
}
function hslToHex(h: number, s: number, l: number): string {
  const f = (n: number) => { const k = (n + h * 12) % 12, a = s * Math.min(l, 1 - l); return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))).toString(16).padStart(2, "0"); };
  return `#${f(0)}${f(8)}${f(4)}`;
}
/** Lift a colour meant for a white panel so it reads on a dark one: lightness to at least 0.58 (a little more for mid-tones), hue and saturation kept. */
export function forDark(hex: string): string {
  const h = toHex(hex); if (!h) return hex;
  const [hue, s, l] = hexToHsl(h);
  if (l >= 0.58) return h;
  return hslToHex(hue, s, Math.max(0.58, Math.min(l + 0.12, 0.7)));
}
