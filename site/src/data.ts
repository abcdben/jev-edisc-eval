import raw from "../../results/findings.json";

export type CI = [number, number, number] | null; // [point, lo95, hi95]
export type PRF = { tp: number; fp: number; fn: number; tn: number; precision: CI; recall: CI; f1: number | null; elusion: CI; n: number };
export type IssueScore = { recall: CI; precision: CI; n_pos: number; n: number };
export type Score = { decision: PRF; doc: PRF; per_issue?: Record<string, IssueScore> };
export type Ops = {
  n_docs: number; n_decisions: number; errors: number;
  cost_per_doc: number | null; list_cost_per_doc: number | null;
  tokens_in_per_doc: number | null; tokens_out_per_doc: number | null;
  doc_latency_p50_ms: number | null; doc_latency_p95_ms: number | null; hours_per_100k_docs: number | null;
  latency_source: string; pricing_modes: string[]; model_resolved: string[];
};
export type Rec = {
  corpus: string; tag: string; arm: "multi" | "single"; model: string; model_key: string; name: string; family: string; kind: string;
  primary: boolean; group: string | null; variant: string | null; lever: string | null;
  subset: string | null; ops: Ops; all: Score; nogray: Score;
};
export type CorpusMeta = {
  corpus: string; tag: string; display: string; gold: string; n_docs: number; n_issues: number;
  issues: Record<string, string>; n_pos_docs_any: number; n_pos_by_issue: Record<string, number>; n_gray_by_issue: Record<string, number>;
};
export type Findings = { corpora: Record<string, CorpusMeta>; models: Record<string, { name: string; family: string; kind: string }>; records: Rec[] };

export const DATA = raw as unknown as Findings;

// ------------------------------------------------------------------------------------------------

export const CORPORA: { id: string; label: string; short: string }[] = [
  { id: "veridian", label: "Veridian", short: "synthetic medical-device MDL" },
  { id: "mnk", label: "Mallinckrodt", short: "real opioid-litigation emails" },
  { id: "cuad", label: "CUAD", short: "commercial contracts, expert labels" },
  { id: "trec", label: "TREC 2016", short: "Jeb Bush emails, NIST labels" },
];

export type Kind = "system1" | "system1_ft" | "llm" | "local_llm" | "baseline";
export const KIND_LABEL: Record<Kind, string> = {
  system1: "System 1 decision models",
  system1_ft: "System 1, supervised",
  llm: "Large language models (API)",
  local_llm: "Open-weight LLM (local GPU)",
  baseline: "Floor",
};
export const KIND_ORDER: Kind[] = ["system1", "system1_ft", "llm", "local_llm", "baseline"];

/** Headline roster, in display order, with a stable colour each. */
export const PRIMARY: { key: string; color: string; short: string; note: string }[] = [
  { key: "jev@base", color: "#1f6b4a", short: "Jev", note: "TypeSafe Jev 1.13, default configuration: Noul question form, prose criteria, RFP phrasing, matter context." },
  { key: "jev@state_string", color: "#5fa37d", short: "Jev · recipe", note: "Jev 1.13 with the one lever that won the 12-variant ablation on the Veridian dev split (flat-string state). Chosen before any other corpus was scored." },
  { key: "laya@base", color: "#2f5f8f", short: "Laya", note: "ConvAI Laya, zero-shot, default configuration. 512-token context; long documents are truncated." },
  { key: "laya@recipe", color: "#6f9bc4", short: "Laya · recipe", note: "Laya zero-shot with compact criteria and a sliding window over the document (max-pooled), the two levers that fit its 512-token context." },
  { key: "laya-ft", color: "#7b5ea7", short: "Laya · fine-tuned", note: "SUPERVISED. Laya fine-tuned (RLCD) on a 30% document-level dev split of the same corpus and scored on the held-out 70%. Not on equal footing with the zero-shot rows." },
  { key: "claude-haiku-4.5", color: "#d99a6c", short: "Haiku 4.5", note: "Anthropic Claude Haiku 4.5, structured JSON output, default effort." },
  { key: "claude-sonnet-5", color: "#b5623a", short: "Sonnet 5", note: "Anthropic Claude Sonnet 5, structured JSON output, default effort, prompt caching on the all-issues arm." },
  { key: "gpt-5.6-luna", color: "#8a8780", short: "GPT-5.6 Luna", note: "OpenAI GPT-5.6 Luna, structured output, minimal reasoning, flex pricing (50% off list)." },
  { key: "gpt-5.6-terra", color: "#3a3835", short: "GPT-5.6 Terra", note: "OpenAI GPT-5.6 Terra, structured output, minimal reasoning, flex pricing (50% off list)." },
  { key: "gemini-3.5-flash-lite", color: "#dcbf5a", short: "Gemini 3.5 Flash-Lite", note: "Google Gemini 3.5 Flash-Lite, structured output." },
  { key: "gemini-3.8-flash", color: "#b5952a", short: "Gemini 3.8 Flash", note: "Google Gemini 3.8 Flash, structured output." },
  { key: "gemma3-12b", color: "#8c9a4a", short: "Gemma 3 12B", note: "Google Gemma 3 12B run locally via Ollama on an A100. Scored on a 400-600 document stratified subsample; latency measured with 4 concurrent requests." },
  { key: "lexical", color: "#b9b5ac", short: "Keyword floor", note: "Term overlap between the RFP text and the document, thresholded at 0.5. No model; shows what vocabulary alone buys." },
];
export const PRIMARY_BY_KEY = Object.fromEntries(PRIMARY.map((p) => [p.key, p]));
export const DEFAULT_ON = new Set(["jev@base", "laya@recipe", "claude-haiku-4.5", "claude-sonnet-5", "gpt-5.6-luna", "gemini-3.8-flash", "lexical"]);

/** Ablation families: a base model whose variants change one lever at a time. */
export const ABLATION_GROUPS: { id: string; label: string; recipe: string; note: string }[] = [
  { id: "jev", label: "Jev 1.13", recipe: "state_string", note: "Twelve configurations of TypeSafe Jev. Each changes one lever from the default; the recipe is the lever that won on the Veridian dev split." },
  { id: "laya", label: "Laya", recipe: "recipe", note: "ConvAI Laya, English checkpoint, zero-shot. Two levers (compact, chunk) exist only to fit its 512-token context; the recipe combines them." },
  { id: "laya-typed", label: "Laya · typed", recipe: "recipe", note: "Laya typed checkpoint, zero-shot." },
  { id: "laya-multilingual", label: "Laya · multilingual", recipe: "recipe", note: "Laya multilingual checkpoint, zero-shot." },
];
export const VARIANT_ORDER = ["base", "choice", "score", "crit_none", "crit_struct", "literal", "no_context", "state_string", "gate", "ensemble", "decompose", "preview", "compact", "chunk", "recipe", "recipe_choice"];
export const VARIANT_LABEL: Record<string, string> = {
  base: "default", choice: "Choice form", score: "Score form", crit_none: "no criteria", crit_struct: "structured criteria", literal: "literal phrasing",
  no_context: "no matter context", state_string: "flat-string state", gate: "gated", ensemble: "3-phrasing ensemble", decompose: "decomposed",
  preview: "jev-preview", compact: "compact", chunk: "chunked", recipe: "compact + chunk", recipe_choice: "compact + chunk, Choice",
};
const VARIANT_PALETTE = ["#171614", "#b5623a", "#d99a6c", "#2f5f8f", "#6f9bc4", "#7b5ea7", "#b08ad0", "#1f6b4a", "#5fa37d", "#b5952a", "#dcbf5a", "#8c9a4a", "#8a8780", "#c4c0b8", "#d16a8a", "#e6a5b8"];
export const variantColor = (v: string, recipe: string) => (v === recipe ? "#1f6b4a" : v === "base" ? "#171614" : VARIANT_PALETTE[(VARIANT_ORDER.indexOf(v) + 1) % VARIANT_PALETTE.length]);

// ------------------------------------------------------------------------------------------------

export const fmtPct = (v: number | null | undefined, d = 1) => (v == null ? "—" : `${(v * 100).toFixed(d)}%`);
export const fmtCI = (ci: CI, d = 1) => (ci ? `${fmtPct(ci[0], d)}  [${fmtPct(ci[1], d)}, ${fmtPct(ci[2], d)}]` : "—");
export const fmtInt = (v: number) => v.toLocaleString("en-US");
export const fmtHours = (h: number | null) => {
  if (h == null) return "—";
  if (h < 0.05) return "< 0.1 h";
  if (h < 10) return `${h.toFixed(1)} h`;
  return `${fmtInt(Math.round(h))} h`;
};
export const fmtUSD = (v: number | null) => {
  if (v == null) return "—";
  if (v === 0) return "$0";
  if (v < 1) return `$${v.toFixed(2)}`;
  if (v < 100) return `$${v.toFixed(1)}`;
  return `$${fmtInt(Math.round(v))}`;
};
export const fmtMs = (v: number | null) => (v == null ? "—" : v < 1000 ? `${Math.round(v)} ms` : `${(v / 1000).toFixed(1)} s`);

export type Level = "doc" | "decision";
export type Gray = "all" | "nogray";

/** Recall/precision for a record under the current view. `issue` narrows to one issue (all gold labels). */
export function pick(r: Rec, level: Level, gray: Gray, issue: string | null): { recall: CI; precision: CI; detail: PRF | IssueScore | null } {
  if (issue) {
    const s = r.all.per_issue?.[issue] ?? null;
    return { recall: s?.recall ?? null, precision: s?.precision ?? null, detail: s };
  }
  const s = (gray === "all" ? r.all : r.nogray)[level];
  return { recall: s.recall, precision: s.precision, detail: s };
}

export const corpusKey = (corpus: string, tag: string) => (tag ? `${corpus}#${tag}` : corpus);
