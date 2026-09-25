import { PRIMARY_BY_KEY } from "./data";

/**
 * Model makers (the studio's Chart → Key control, StudioPage.tsx, `by maker`): the roster models grouped by who makes them, each group with the
 * CSS custom property it is coloured through in that mode. The property is one of the roster's own model colours (data.ts ALL_PRIMARY
 * `var(--c-…)`), so a maker's colour is whatever the Style preset, palette or custom swatch gives that model: in the TypeSafe preset TypeSafe is
 * Jev's magenta, OpenAI is Terra's teal, Anthropic is Sonnet's orange, Google is Flash's blue and ConvAI is Laya's lilac. Gemma is Google's
 * open-weight model and is grouped under Google. A key no rule matches (none on the roster today) falls to `other`, drawn in its own roster colour.
 */
export type Maker = { id: string; label: string; colorVar: string | null };
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
  if (fam.startsWith("gpt")) return "openai";
  if (fam.startsWith("gemini") || fam.startsWith("gemma")) return "google";
  if (fam === "tar") return "tar";
  return "other";
};
/** The maker of a model key (`jev@base`, `claude-sonnet-5`, …). */
export const makerOf = (key: string): Maker => byId[makerId(key)];
/** The colour a model draws in by-maker mode: its maker's property, or its own roster colour where the maker has none (TAR, other). */
export const makerColor = (key: string, own: string): string => { const v = makerOf(key).colorVar; return v ? `var(${v})` : own; };
/** The model's name in by-maker mode: the roster's `shortInMaker` (the vendor prefix dropped, "GPT-5.6 Luna" → "Luna") where it has one, else `short`. */
export const makerName = (key: string, own: string): string => PRIMARY_BY_KEY[key]?.shortInMaker ?? own;
