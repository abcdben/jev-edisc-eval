/**
 * Page theme (styles.css `:root` light palette, `[data-theme="dark"]`, `[data-theme="white"]`), shared by the main site (App.tsx)
 * and the Studio (studioState.ts `theme` field): one localStorage key, `theme`, so a choice on one page carries to the others.
 * `light` is the warm off-white console look; `white` is the same palette on a pure white page with white panels behind hairline borders.
 */
export const THEMES = ["dark", "light", "white"] as const;
export type Theme = (typeof THEMES)[number];
export const THEME_KEY = "theme";
export const THEME_OPTIONS: { id: Theme; label: string; title: string }[] = [
  { id: "dark", label: "Dark", title: "Dark page and panels" },
  { id: "light", label: "Light", title: "Warm off-white page, lighter panels" },
  { id: "white", label: "White", title: "Pure white page and panels, hairline borders" },
];
export const isTheme = (v: unknown): v is Theme => typeof v === "string" && (THEMES as readonly string[]).includes(v);
/** The remembered theme, or `light` when none is stored or the stored value is not one of THEMES (storage denied counts as none). */
export const readTheme = (): Theme => { try { const v = localStorage.getItem(THEME_KEY); return isTheme(v) ? v : "light"; } catch { return "light"; } };
