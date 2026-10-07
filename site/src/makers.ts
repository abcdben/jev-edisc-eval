import { PRIMARY_BY_KEY } from "./data";

/**
 * Model makers (the studio's Chart → Key control, StudioPage.tsx, `by maker`; `by family` below reuses them for the non-Jev models): the roster models grouped by who makes them, each group with the
 * CSS custom property it is coloured through in that mode. The property is one of the roster's own model colours (data.ts ALL_PRIMARY
 * `var(--c-…)`), so a maker's colour is whatever the Style preset, palette or custom swatch gives that model: in the TypeSafe preset TypeSafe is
 * Jev's magenta, OpenAI is Terra's teal, Anthropic is Sonnet's orange, Google is Flash's blue and ConvAI is Laya's lilac. Gemma is Google's
 * open-weight model and is grouped under Google. A key no rule matches (none on the roster today) falls to `other`, drawn in its own roster colour.
 */
export type Maker = { id: string; label: string; colorVar: string | null; title?: string };
export const MAKERS: Maker[] = [
  { id: "typesafe", label: "TypeSafe", colorVar: "--c-jev" },
  { id: "convai", label: "ConvAI", colorVar: "--c-laya-ft" },
  { id: "anthropic", label: "Anthropic", colorVar: "--c-sonnet" },
  { id: "openai", label: "OpenAI", colorVar: "--c-terra" },
  { id: "google", label: "Google", colorVar: "--c-flash" },
  { id: "tar", label: "TAR", colorVar: null },
  { id: "other", label: "Other", colorVar: null },
];
const byId = Object.fromEntries(MAKERS.map((m) => [m.id, m]));
const makerId = (key: string): string => {
  const fam = key.split("@")[0];
  if (fam === "jev") return "typesafe";
  if (fam.startsWith("laya")) return "convai";
  if (fam.startsWith("claude")) return "anthropic";
  if (fam.startsWith("gpt") || fam === "openai-decisions") return "openai";
  if (fam.startsWith("gemini") || fam.startsWith("gemma")) return "google";
  if (fam === "tar") return "tar";
  return "other";
};
/** The maker of a model key (`jev@base`, `claude-sonnet-5`, …). */
export const makerOf = (key: string): Maker => byId[makerId(key)];
/** The colour a model draws in by-maker mode: its maker's property, or its own roster colour where the maker has none (TAR, other). */
export const makerColor = (key: string, own: string): string => { const v = makerOf(key).colorVar; return v ? `var(${v})` : own; };
/** The model's name in by-maker and by-family mode: the roster's `shortInMaker` (the vendor prefix dropped, "GPT-5.6 Luna" → "Luna") where it has one, else `short`. */
export const makerName = (key: string, own: string): string => PRIMARY_BY_KEY[key]?.shortInMaker ?? own;

/**
 * Question-form families (the Key control's `by family`): the Jev rows split into the three basic question forms (Noul, Choice, Score: JEV_BASIC) and
 * the composed variants (Facets, Three-Phrasing Ensemble, Relevance Gate, and any other `jev@…` row the roster gains), each family drawn in one colour
 * through its own custom property. styles.css gives the two properties defaults off the style's own Jev colours (--fam-basic follows Noul's --c-jev,
 * --fam-composed Score's --v5, TypeSafe a cooler magenta-violet); with a Colors palette or custom swatches on, StudioPage.tsx gives the composed
 * family a sibling hue of the recoloured Noul instead (palettes.ts siblingHue), and the studio's Basic and Composed swatches write overrides
 * inline on the panel. Every other model is grouped and coloured as in by-maker mode (makerOf).
 */
export const JEV_BASIC = ["jev@base", "jev@choice", "jev@score"];
export const FAMILY_BASIC_VAR = "--fam-basic", FAMILY_COMPOSED_VAR = "--fam-composed";
const jevNames = (keys: string[]) => keys.map((k) => PRIMARY_BY_KEY[k]?.short.replace(/^Jev · /, "") ?? k).join(", ");
const JEV_COMPOSED = Object.keys(PRIMARY_BY_KEY).filter((k) => k.startsWith("jev@") && !JEV_BASIC.includes(k));
/** Each family's members by their roster names, "Jev · " dropped: "Noul, Choice, Score" / "Facets, Three-Phrasing Ensemble, Relevance Gate" (the legend entries' hover titles; the entries themselves read "Jev · basic" / "Jev · composed"). */
export const FAMILY_MEMBERS = { basic: jevNames(JEV_BASIC), composed: jevNames(JEV_COMPOSED) };
export const FAMILIES: { basic: Maker; composed: Maker } = {
  basic: { id: "jev-basic", label: "Jev · basic", colorVar: FAMILY_BASIC_VAR, title: `Jev's three basic question forms: ${FAMILY_MEMBERS.basic}` },
  composed: { id: "jev-composed", label: "Jev · composed", colorVar: FAMILY_COMPOSED_VAR, title: `Jev's composed variants: ${FAMILY_MEMBERS.composed}` },
};
/** The family of a model key: a Jev row's question-form family, any other model's maker. */
export const familyOf = (key: string): Maker => (key.split("@")[0] === "jev" ? (JEV_BASIC.includes(key) ? FAMILIES.basic : FAMILIES.composed) : makerOf(key));
/** The colour a model draws in by-family mode: its family's property, or its own roster colour where the group has none (TAR, other). */
export const familyColor = (key: string, own: string): string => { const v = familyOf(key).colorVar; return v ? `var(${v})` : own; };
