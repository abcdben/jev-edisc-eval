import raw from "../../results/findings.json";

export type CI = [number, number, number] | null; // [point, lo95, hi95]
export type PRF = { tp: number; fp: number; fn: number; tn: number; precision: CI; recall: CI; f1: number | null; elusion: CI; n: number };
export type IssueScore = { recall: CI; precision: CI; n_pos: number; n: number };
export type Score = { decision: PRF; doc: PRF; per_issue?: Record<string, IssueScore> };
export type Ops = {
  n_docs: number; n_decisions: number; errors: number;
  cost_per_doc: number | null; list_cost_per_doc: number | null;
  tokens_in_per_doc: number | null; tokens_out_per_doc: number | null;
  doc_latency_p50_ms: number | null; doc_latency_p95_ms: number | null; hours_per_100k_docs: number | null; // hours_per_100k_docs is p50 × 100k, in the export only; the site reads the latencies
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
export type DetSub = { n: number; flip: CI; pairwise: number | null };
export type DetCell = {
  arm: "multi" | "single"; setting: "default" | "t0"; model: string; k: number; runs: string[];
  n_decisions: number; n_docs: number;
  decision_flip: CI; decision_flip_weighted: number; pairwise: [number, number, number];
  identical_prob: CI; prob_spread_median: number; prob_spread_p95: number;
  confident_flip: CI; confident_share_of_flips: number | null;
  by_issue: Record<string, DetSub>; by_stratum: Record<string, DetSub>; by_gold: Record<string, DetSub>;
  recall_range: [number, number] | null; precision_range: [number, number] | null;
  majority: { recall: number | null; precision: number | null };
  doc_flip?: CI; doc_pairwise?: number;
};
export type Determinism = {
  sample: { n_docs: number; strata: Record<string, number>; corpus_strata: Record<string, number>; focus_issues: string[] };
  cells: DetCell[];
} | null;
export type Findings = {
  corpora: Record<string, CorpusMeta>; models: Record<string, { name: string; family: string; kind: string }>; records: Rec[]; determinism: Determinism;
};

export const DATA = raw as unknown as Findings;

// ------------------------------------------------------------------------------------------------

/** Corpora offered on the site, in display order. Veridian (synthetic) and CUAD stay in findings.json and examples.json but are not listed; add "veridian" or "cuad" here to bring them back. */
export const SITE_CORPORA = ["trec", "mnk"];
const ALL_CORPORA: { id: string; label: string; short: string }[] = [
  { id: "veridian", label: "Veridian", short: "synthetic medical-device MDL" },
  { id: "mnk", label: "Mallinckrodt", short: "real opioid-litigation emails" },
  { id: "cuad", label: "CUAD", short: "commercial contracts, expert labels" },
  { id: "trec", label: "TREC 2016", short: "Jeb Bush emails, NIST labels" },
];
export const CORPORA = SITE_CORPORA.map((id) => ALL_CORPORA.find((c) => c.id === id)!);
export const DEFAULT_CORPUS = CORPORA[0].id;
/** Coerce a corpus id (state, hash, storage) to one the site offers, falling back to the first. */
export const siteCorpus = (id: string | null | undefined) => (id && SITE_CORPORA.includes(id) ? id : DEFAULT_CORPUS);

export type Kind = "system1" | "system1_ft" | "llm" | "local_llm" | "baseline";
export const KIND_LABEL: Record<Kind, string> = {
  system1: "Decision models",
  system1_ft: "Decision models, supervised",
  llm: "Large language models (API)",
  local_llm: "Open-weight LLM (local GPU)",
  baseline: "Floor",
};
export const KIND_ORDER: Kind[] = ["system1", "system1_ft", "llm", "local_llm", "baseline"];
/** The decision-model kinds (Jev, Laya). The one rule behind every decision-model marker: the outlined name on rows and in the picker, the ringed mark on the map, the DECISION MODEL tag in modals. */
export const isDecider = (kind: string | null | undefined): boolean => kind === "system1" || kind === "system1_ft";
/** Rows whose name carries no subset asterisk even though they were scored on a subset (the fact stays in the tooltip and the Method table). */
export const NO_STAR = new Set(["laya-ft"]);
export const starOf = (r: { model: string; subset: string | null }): string | null => (NO_STAR.has(r.model) ? null : r.subset);

/**
 * Model keys the site does not show anywhere (roster, picker, charts, Configurations, details modal), though their results stay in
 * findings.json and examples.json. HIDDEN_FAMILIES hides a whole key family (`<family>@<variant>`): the `tar` family is exported but
 * not shown; remove it from the set to bring it back.
 */
export const HIDDEN_MODELS: string[] = [];
export const HIDDEN_FAMILIES = new Set(["tar"]);
export const isHidden = (key: string): boolean => HIDDEN_MODELS.includes(key) || HIDDEN_FAMILIES.has(key.split("@")[0]);
/** The kind of a model key (headline roster or configuration), from the models map or the first record that ran it. */
export const modelKind = (key: string): string | undefined => DATA.models[key]?.kind ?? DATA.records.find((r) => r.model === key)?.kind;

/** Headline roster, in display order, with a stable colour each. `kind` overrides the record's kind for grouping on the Compare page. HIDDEN_MODELS are filtered out below.
 * Compare models lists a curated set of Jev configurations. The three question forms (Noul, Choice, Score) start checked; the others are off. Flat-Text State and No Criteria stay on the Configurations page. */
const ALL_PRIMARY: { key: string; color: string; short: string; note: string; kind?: Kind }[] = [
  { key: "jev@base", color: "var(--c-jev)", short: "Jev · Noul", note: "TypeSafe Jev 1.13, Noul: one yes/no Noul per issue, prose criteria, RFP phrasing, matter context as a structured object. On by default." },
  { key: "jev@choice", color: "var(--v3)", short: "Jev · Choice", note: "TypeSafe Jev 1.13, Choice: the same instruction and criteria, asked as a Choice between the two labels rather than a yes/no Noul. On by default." },
  { key: "jev@score", color: "var(--v5)", short: "Jev · Score", note: "TypeSafe Jev 1.13, Score: the issue is asked as a five-point Score from 'clearly not responsive' to 'clearly responsive'; the scored probability is the level divided by four. On by default." },
  { key: "jev@decompose", color: "var(--v1)", short: "Jev · Decomposed Sub-Questions", note: "TypeSafe Jev 1.13, Decomposed Sub-Questions: each issue is split into the atomic sub-questions in the task file; each is asked as its own Noul and the issue probability is the maximum (logical OR). Strongest Jev row on TREC 2016." },
  { key: "jev@ensemble", color: "var(--v9)", short: "Jev · Three-Phrasing Ensemble", note: "TypeSafe Jev 1.13, Three-Phrasing Ensemble: the same issue is asked three ways (RFP text, literal, title + positive description) and the probabilities are averaged." },
  { key: "jev@gate", color: "var(--v14)", short: "Jev · Relevance Gate", note: "TypeSafe Jev 1.13, Relevance Gate: an extra Noul first asks whether the document has anything to do with the matter; each issue probability is multiplied by that gate. Trades recall for precision." },
  { key: "laya-ft", color: "var(--c-laya-ft)", short: "Laya", kind: "system1", note: "ConvAI Laya, fine-tuned: the one supervised row in this zero-shot comparison. Fine-tuned (RLCD) on a 30% document-level dev split of the same corpus and scored on the held-out 70%; every other row is zero-shot. The labeled data it needed is not counted in the time and cost panels. Zero-shot Laya configurations are on the Configurations page." },
  { key: "claude-haiku-4.5", color: "var(--c-haiku)", short: "Haiku 4.5", note: "Anthropic Claude Haiku 4.5, structured JSON output, default effort." },
  { key: "claude-sonnet-5", color: "var(--c-sonnet)", short: "Sonnet 5", note: "Anthropic Claude Sonnet 5, structured JSON output, default effort, prompt caching on the all-issues arm." },
  { key: "gpt-5.6-luna", color: "var(--c-luna)", short: "GPT-5.6 Luna", note: "OpenAI GPT-5.6 Luna, structured output, minimal reasoning, flex pricing (50% off list)." },
  { key: "gpt-5.6-terra", color: "var(--c-terra)", short: "GPT-5.6 Terra", note: "OpenAI GPT-5.6 Terra, structured output, minimal reasoning, flex pricing (50% off list)." },
  { key: "gemini-3.5-flash-lite", color: "var(--c-flashlite)", short: "Gemini 3.5 Flash-Lite", note: "Google Gemini 3.5 Flash-Lite, structured output." },
  { key: "gemini-3.8-flash", color: "var(--c-flash)", short: "Gemini 3.8 Flash", note: "Google Gemini 3.8 Flash, structured output." },
  { key: "gemma3-12b", color: "var(--c-gemma)", short: "Gemma 3 12B", kind: "llm", note: "Local, open-weight. Google Gemma 3 12B run via Ollama on a rented A100. Scored on a 400-600 document stratified subsample; latency measured with 4 concurrent requests." },
];
export const PRIMARY = ALL_PRIMARY.filter((p) => !isHidden(p.key));
export const PRIMARY_BY_KEY = Object.fromEntries(PRIMARY.map((p) => [p.key, p]));
export const DEFAULT_ON = new Set(["jev@base", "jev@choice", "jev@score", "claude-haiku-4.5", "claude-sonnet-5", "gpt-5.6-luna", "gpt-5.6-terra", "gemini-3.5-flash-lite", "gemini-3.8-flash"].filter((k) => !isHidden(k)));
/** Compare-models rows for a corpus, in roster order. Membership is the roster, not the export's `primary` flag: Choice, Score and the other listed Jev configurations are on the picker even though the export only flags some of them as primary. */
export const rosterOf = (rows: Rec[]) => PRIMARY.map((p) => rows.find((r) => r.model === p.key)).filter((r): r is Rec => !!r);

/**
 * GPU rental for the rows that ran on our own hardware rather than an API (Laya checkpoints, Gemma 3 12B).
 * Both were measured on a Lambda Cloud 1× A100 (Laya single-request latency samples; Gemma via Ollama with 4 concurrent requests).
 * Lambda on-demand list price, lambda.ai/pricing, checked 2026-09-21: 1× A100 40 GB SXM $1.99/GPU-h; 1× H100 PCIe $3.29/GPU-h (H100 SXM $4.29).
 * Cost per document = median latency (h) × GPU_USD_PER_HOUR, i.e. the GPU time for the one-request-at-a-time latency shown.
 */
export const GPU_USD_PER_HOUR = 1.99;
export const GPU_USD_PER_HOUR_H100 = 3.29;
export const GPU_NAME = "Lambda Cloud 1× A100";
/** Rows whose cost is GPU rental rather than an API bill. */
export const isGpuRow = (r: Rec) => r.kind === "local_llm" || r.family === "Laya";
/** Cost per document under the site's accounting: API rows as paid, GPU rows as rental for their median latency. */
export const costPerDoc = (r: Rec): number | null => {
  if (isGpuRow(r)) return r.ops.doc_latency_p50_ms == null ? null : (r.ops.doc_latency_p50_ms / 3.6e6) * GPU_USD_PER_HOUR;
  return r.ops.cost_per_doc;
};

/** Ablation families: a base model whose variants change one lever at a time. */
export const ABLATION_GROUPS: { id: string; label: string; recipe: string; note: string }[] = [
  { id: "jev", label: "Jev 1.13", recipe: "state_string", note: "Twelve configurations of TypeSafe Jev. Each variant changes a single lever from the default. ★ marks the configuration selected on the Veridian dev split." },
  { id: "laya", label: "Laya", recipe: "recipe", note: "ConvAI Laya, English checkpoint, zero-shot. Two levers (Compact Question, Chunked Document) exist only to fit its 512-token context; ★ marks the configuration that combines them (Compact + Chunked), selected on the Veridian dev split." },
  // The typed and multilingual Laya checkpoints (groups laya-typed, laya-multilingual) stay in findings.json but are not offered: only the English family, whose request the charted fine-tune uses, is shown.
];
export const VARIANT_ORDER = ["base", "choice", "score", "crit_none", "crit_struct", "literal", "no_context", "state_string", "gate", "ensemble", "decompose", "preview", "compact", "chunk", "recipe", "recipe_choice"];
export const VARIANT_LABEL: Record<string, string> = {
  base: "Noul Question", choice: "Choice Question", score: "Five-Point Score", crit_none: "No Criteria", crit_struct: "Structured Criteria", literal: "Plain-Language Phrasing",
  no_context: "No Matter Context", state_string: "Flat-Text State", gate: "Relevance Gate", ensemble: "Three-Phrasing Ensemble", decompose: "Decomposed Sub-Questions",
  preview: "Jev Preview Model", compact: "Compact Question", chunk: "Chunked Document", recipe: "Compact + Chunked", recipe_choice: "Compact + Chunked, Choice",
};
/**
 * One-line definition of each configuration, the highlighted clause of the details modal's opening sentence
 * ("<name> is the configuration in which <definition>."). Lower-case clauses, no trailing stop. Keyed by model key
 * (family@variant); the typed and multilingual Laya checkpoints fall back to laya@<variant>.
 * Text follows the lever notes in ediscovery_bench/examples.py and export.py.
 */
export const VARIANT_DEFINITION: Record<string, string> = {
  // Jev 1.13
  "jev@base": "one Noul (yes/no) question per issue whose answer is a probability; the RFP text is the instruction, the task file's positive and negative descriptions are the true/false criteria, and the state is a structured object with the matter background and the document",
  "jev@choice": "the same instruction and criteria are asked as a Choice between the two labels rather than a yes/no Noul; the model returns a probability for each label and p(responsive) is what is scored",
  "jev@score": "the question is asked as a Score on a five-point ordinal scale from 'clearly not responsive' to 'clearly responsive', with the criteria folded into the instruction; the scored probability is the level divided by four",
  "jev@crit_none": "the Noul question is sent with no criteria at all, only the instruction, to test how much the true/false descriptions are doing",
  "jev@crit_struct": "the criteria are supplied as the task file's structured object (what / includes / excludes / examples) instead of prose, falling back to prose where a question has no structured block",
  "jev@literal": "the instruction is the task file's plain-language 'literal' phrasing (a reviewer's one-line version) instead of the verbatim RFP text",
  "jev@no_context": "the matter background is dropped from the state, so the model sees only the document",
  "jev@state_string": "the state is a single flat string ('MATTER BACKGROUND: … DOCUMENT: …') instead of a structured object with named fields",
  "jev@gate": "an extra Noul first asks whether the document has anything to do with the matter at all, and each issue probability is multiplied by that gate probability",
  "jev@ensemble": "three phrasings of the same question (RFP text, literal, title + positive description) are asked as three Nouls and their probabilities averaged",
  "jev@decompose": "each issue is split into the atomic sub-questions the task file defines for it; each is asked as its own Noul and the issue probability is the maximum across them (logical OR)",
  "jev@preview": "the request is identical to the Noul Question configuration but is sent to the jev-preview model instead of jev-1.13.0",
  // Laya, zero-shot (also the typed and multilingual checkpoints)
  "laya@base": "the same request as Jev's default, run through the local Laya encoder, which packs the question head into at most 192 tokens and the whole input into 512, so the instruction and criteria are truncated and most documents are cut from the right",
  "laya@choice": "the question is asked as a Choice over the two labels instead of a Noul",
  "laya@score": "the question is asked as a five-level Score with the criteria folded into the instruction",
  "laya@literal": "the instruction is the shorter literal phrasing, which fits more of the question into the 192-token head",
  "laya@gate": "an extra matter-relevance Noul gates each issue probability",
  "laya@ensemble": "three phrasings are asked and their probabilities averaged, each truncated the same way",
  "laya@decompose": "sub-questions are asked separately and OR'd: the issue probability is the maximum across them",
  "laya@compact": "a one-line instruction ('Is this document responsive to the request for production about: <title>?') and one-sentence criteria are sized to fit Laya's 192-token head, so nothing in the question is truncated",
  "laya@chunk": "the document is split into overlapping windows sized to Laya's remaining context (about 300 tokens), each window is scored, and the per-question probability is the maximum over windows (up to 16)",
  "laya@recipe": "the compact question and the chunked document are combined: the two levers that address Laya's 512-token context, changing how much of the request Laya can read rather than what is asked",
  "laya@recipe_choice": "the Compact + Chunked request is asked with the Choice question form",
  // Laya, supervised (the Compare models row)
  "laya-ft": "Laya's Compact + Chunked request is sent to a checkpoint fine-tuned (RLCD) on a 30% document-level dev split of {corpus}'s own gold labels and scored on the held-out 70%; the request does not change, the weights do",
  // Generative models: one definition, the prompt is the same for every model
  "llm": "one zero-shot chat completion per document (all issues at once) or per issue, with a JSON schema the vendor enforces on the reply: a label and p(responsive), no free text",
};
/** The definition for a model key on a corpus: resolves the Laya checkpoints and the {corpus} placeholder. */
export const variantDefinition = (key: string, corpusLabel: string): string | undefined => {
  const [fam, v] = key.includes("@") ? key.split("@") : [key, ""];
  let d = VARIANT_DEFINITION[key] ?? (fam.startsWith("laya") && v ? VARIANT_DEFINITION[`laya@${v}`] : undefined);
  if (!d && !key.includes("@") && key !== "lexical") d = VARIANT_DEFINITION.llm;
  return d?.replace("{corpus}", corpusLabel);
};
const VARIANT_PALETTE = Array.from({ length: 16 }, (_, i) => `var(--v${i})`);
export const variantColor = (v: string, recipe: string) => (v === recipe ? "var(--c-jev)" : v === "base" ? "var(--c-base)" : VARIANT_PALETTE[(VARIANT_ORDER.indexOf(v) + 1) % VARIANT_PALETTE.length]);

// ------------------------------------------------------------------------------------------------

export const fmtPct = (v: number | null | undefined, d = 1) => (v == null ? "—" : `${(v * 100).toFixed(d)}%`);
export const fmtCI = (ci: CI, d = 1) => (ci ? `${fmtPct(ci[0], d)}  [${fmtPct(ci[1], d)}, ${fmtPct(ci[2], d)}]` : "—");
/** The interval alone, as whole points for the ranked rows' range column: "82–91". */
export const fmtRange = (ci: CI) => (ci ? `${Math.round(ci[1] * 100)}–${Math.round(ci[2] * 100)}` : "—");
export const fmtInt = (v: number) => v.toLocaleString("en-US");
export const fmtUSD = (v: number | null) => {
  if (v == null) return "—";
  if (v === 0) return "$0";
  if (v < 1) return `$${v.toFixed(2)}`;
  if (v < 100) return `$${v.toFixed(1)}`;
  return `$${fmtInt(Math.round(v))}`;
};
export const fmtMs = (v: number | null) => (v == null ? "—" : v < 1000 ? `${Math.round(v)} ms` : `${(v / 1000).toFixed(1)} s`);

/** An issue's display label, wherever `meta.issues` is rendered: the name without its " (broad)" / " (narrow)" suffix, then its measured prevalence ("Suspicious order monitoring · 19%"). */
export const issueLabel = (meta: CorpusMeta, k: string): string => {
  const name = (meta.issues[k] ?? k).replace(/\s*\((broad|narrow)\)\s*$/, "");
  const n = meta.n_pos_by_issue[k];
  return n == null ? name : `${name} · ${fmtPct(n / meta.n_docs, 0)}`;
};

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
