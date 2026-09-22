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
  subset: string | null; ops: Ops; all: Score; nogray: Score; tar?: TarBlock;
};
/** Classical TAR rows: the simulated reviewer's effort and the spread across random seeds. */
export type TarBlock = {
  variant: string; kind: "t1" | "cal"; n_corpus: number; n_eval: number;
  docs_reviewed: number; hours: number; cost_usd: number; review_share: number;
  reviewer: { docs_per_hour: number; usd_per_hour: number; miscode_rate: number };
  seeds: number; median_seed: number; recall_range: [number, number] | null; precision_range: [number, number] | null;
  cutoff_rule: string | null; issue_models: string[] | null; train_positives_any: number | null;
  batches: number | null; batch: number | null; stop: string | null; stop_rule: string | null; curve: { reviewed: number; found: number; est_recall?: number | null }[] | null;
  pool_richness: number | null; relevant_in_pool: number | null; found_gold: number | null; downsampled: boolean;
  /** CAL only. The plotted set is the production set (what the reviewer coded relevant, control set included) on the CAL pool. */
  plotted?: string; target?: number | null; docs_queued?: number | null;
  control_set?: { n: number; relevant_coded: number; relevant_gold: number } | null;
  est_recall_at_stop?: number | null; reached_recall?: number | null; review_set_precision?: number | null;
  production?: TarPRF | null;
  classifier?: { cutoff: number; target: number; pool: TarPRF; eval: TarPRF & { n_reviewed_in_eval: number } } | null;
};
/** Point recall / precision of a set against gold, no interval (sidecar figures on the CAL pool or the evaluation set). */
export type TarPRF = { recall: number | null; precision: number | null; flagged: number; relevant: number; n: number };
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

/** Corpora offered on the site, in display order. Veridian (synthetic) stays in findings.json and examples.json but is not listed; add "veridian" here to bring it back. */
export const SITE_CORPORA = ["mnk", "cuad", "trec"];
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

export type Kind = "system1" | "system1_ft" | "llm" | "local_llm" | "tar" | "baseline";
export const KIND_LABEL: Record<Kind, string> = {
  system1: "System 1 decision models",
  system1_ft: "System 1, supervised",
  llm: "Large language models (API)",
  local_llm: "Open-weight LLM (local GPU)",
  tar: "Classical TAR",
  baseline: "Floor",
};
export const KIND_ORDER: Kind[] = ["system1", "system1_ft", "llm", "local_llm", "tar", "baseline"];
/** The decider kinds (Jev, Laya). The one rule behind every decider marker: the outlined name on rows and in the picker, the ringed mark on the map, the DECIDER tag in modals. */
export const isDecider = (kind: string | null | undefined): boolean => kind === "system1" || kind === "system1_ft";
/** Rows whose name carries no subset asterisk even though they were scored on a subset (the fact stays in the tooltip and the Method table). */
export const NO_STAR = new Set(["laya-ft"]);
export const starOf = (r: { model: string; subset: string | null }): string | null => (NO_STAR.has(r.model) ? null : r.subset);

/**
 * Model keys the site does not show anywhere (roster, picker, charts, Configurations, details modal), though their results stay in
 * findings.json and examples.json. CAL hidden for now; remove from this list to bring it back.
 */
export const HIDDEN_MODELS: string[] = ["tar@cal", "tar@cal_75", "tar@cal_perfect", "tar@cal_knee"];
export const isHidden = (key: string): boolean => HIDDEN_MODELS.includes(key);
/** The kind of a model key (headline roster or configuration), from the models map or the first record that ran it. */
export const modelKind = (key: string): string | undefined => DATA.models[key]?.kind ?? DATA.records.find((r) => r.model === key)?.kind;

/** Headline roster, in display order, with a stable colour each. `kind` overrides the record's kind for grouping on the Compare page. HIDDEN_MODELS are filtered out below. */
const ALL_PRIMARY: { key: string; color: string; short: string; note: string; kind?: Kind }[] = [
  { key: "jev@base", color: "var(--c-jev)", short: "Jev", note: "TypeSafe Jev 1.13, default configuration: Noul question form, prose criteria, RFP phrasing, matter context." },
  { key: "jev@state_string", color: "var(--c-jev-2)", short: "Jev w/ Iteration", note: "Jev 1.13 after one round of iteration on the Veridian dev split: the one lever that won the 12-variant ablation (flat-string state), selected before any other corpus was scored." },
  { key: "laya-ft", color: "var(--c-laya-ft)", short: "Laya", kind: "system1", note: "ConvAI Laya, fine-tuned (RLCD) on a 30% document-level dev split of the same corpus and scored on the held-out 70%; every other row is zero-shot. The labeled data it needed is not counted in the time and cost panels. Zero-shot Laya configurations are on the Configurations page." },
  { key: "claude-haiku-4.5", color: "var(--c-haiku)", short: "Haiku 4.5", note: "Anthropic Claude Haiku 4.5, structured JSON output, default effort." },
  { key: "claude-sonnet-5", color: "var(--c-sonnet)", short: "Sonnet 5", note: "Anthropic Claude Sonnet 5, structured JSON output, default effort, prompt caching on the all-issues arm." },
  { key: "gpt-5.6-luna", color: "var(--c-luna)", short: "GPT-5.6 Luna", note: "OpenAI GPT-5.6 Luna, structured output, minimal reasoning, flex pricing (50% off list)." },
  { key: "gpt-5.6-terra", color: "var(--c-terra)", short: "GPT-5.6 Terra", note: "OpenAI GPT-5.6 Terra, structured output, minimal reasoning, flex pricing (50% off list)." },
  { key: "gemini-3.5-flash-lite", color: "var(--c-flashlite)", short: "Gemini 3.5 Flash-Lite", note: "Google Gemini 3.5 Flash-Lite, structured output." },
  { key: "gemini-3.8-flash", color: "var(--c-flash)", short: "Gemini 3.8 Flash", note: "Google Gemini 3.8 Flash, structured output." },
  { key: "gemma3-12b", color: "var(--c-gemma)", short: "Gemma 3 12B", kind: "llm", note: "Local, open-weight. Google Gemma 3 12B run via Ollama on a rented A100. Scored on a 400-600 document stratified subsample; latency measured with 4 concurrent requests." },
  { key: "tar@t1_100", color: "var(--c-tar-1)", short: "TAR 1.0 · 100", note: "Simple learning. A simulated reviewer (50 docs/h, $65/h) codes 100 random documents; TF-IDF + logistic regression labels the rest with a cutoff targeting 80% recall, chosen by cross-validation on the coded sample. Median of 5 random seeds." },
  { key: "tar@t1_300", color: "var(--c-tar-2)", short: "TAR 1.0 · 300", note: "As above with 300 documents coded." },
  { key: "tar@t1_1000", color: "var(--c-tar-3)", short: "TAR 1.0 · 1,000", note: "As above with 1,000 documents coded." },
  { key: "tar@t1_5000", color: "var(--c-tar-4)", short: "TAR 1.0 · 5,000", note: "As above with 5,000 documents coded." },
  { key: "tar@cal", color: "var(--c-cal)", short: "TAR 2.0 · CAL", note: "Continuous active learning with an imperfect reviewer (misses 10% of relevant documents, over-codes 2% of non-relevant), as run in practice. The reviewer first codes a random control set (10% of the pool, capped at 500; 2,000 on TREC), then codes the classifier's top-ranked batch, it retrains, repeat; review stops once the control set estimates 80% recall for two consecutive batches. Plotted as the production set: every document the reviewer coded relevant, scored against gold on the pool CAL ran over. The tooltip has the review effort, the recall estimate at stop against the true figure, and the classifier on its own. On Mallinckrodt, whose benchmark sample is 61% rich by design, CAL runs on a 10%-rich pool." },
];
export const PRIMARY = ALL_PRIMARY.filter((p) => !isHidden(p.key));
export const PRIMARY_BY_KEY = Object.fromEntries(PRIMARY.map((p) => [p.key, p]));
export const DEFAULT_ON = new Set(["jev@base", "laya-ft", "claude-haiku-4.5", "claude-sonnet-5", "gpt-5.6-luna", "gpt-5.6-terra", "gemini-3.5-flash-lite", "gemini-3.8-flash", "gemma3-12b", "tar@t1_100", "tar@t1_300", "tar@t1_1000", "tar@t1_5000", "tar@cal"].filter((k) => !isHidden(k)));

/**
 * Human prompt/criteria development, added to every non-TAR row when the ops cards are set to "+ human time".
 * Someone has to write and iterate the criteria for an LLM or a decider model;
 * we assume that iteration reviews 500 documents at 50 docs/hour and $175/hour, i.e. 10 h and $1,750, and count it
 * once per 100k-document project since the cards are per 100k documents. TAR rows are already human time.
 */
export const HUMAN_DEV_DOCS = 500;
export const HUMAN_DEV_DOCS_PER_HOUR = 50;
export const HUMAN_DEV_USD_PER_HOUR = 175;
export const HUMAN_DEV_HOURS = HUMAN_DEV_DOCS / HUMAN_DEV_DOCS_PER_HOUR;
export const HUMAN_DEV_USD = HUMAN_DEV_HOURS * HUMAN_DEV_USD_PER_HOUR;

/**
 * GPU rental for the rows that ran on our own hardware rather than an API (Laya checkpoints, Gemma 3 12B).
 * Both were measured on a Lambda Cloud 1× A100 (Laya single-stream latency samples; Gemma via Ollama with 4 concurrent requests).
 * Lambda on-demand list price, lambda.ai/pricing, checked 2026-09-21: 1× A100 40 GB SXM $1.99/GPU-h; 1× H100 PCIe $3.29/GPU-h (H100 SXM $4.29).
 * Cost per document = hours_per_100k_docs × GPU_USD_PER_HOUR / 100,000, i.e. the GPU time for the single-stream review time shown.
 */
export const GPU_USD_PER_HOUR = 1.99;
export const GPU_USD_PER_HOUR_H100 = 3.29;
export const GPU_NAME = "Lambda Cloud 1× A100";
/** Rows whose cost is GPU rental rather than an API bill. */
export const isGpuRow = (r: Rec) => r.kind === "local_llm" || r.family === "Laya";
/** Cost per document under the site's accounting: API rows as paid, GPU rows as rental for their review time. */
export const costPerDoc = (r: Rec): number | null => {
  if (isGpuRow(r)) return r.ops.hours_per_100k_docs == null ? null : (r.ops.hours_per_100k_docs * GPU_USD_PER_HOUR) / 1e5;
  return r.ops.cost_per_doc;
};

/** Ablation families: a base model whose variants change one lever at a time. */
export const ABLATION_GROUPS: { id: string; label: string; recipe: string; note: string }[] = [
  { id: "jev", label: "Jev 1.13", recipe: "state_string", note: "Twelve configurations of TypeSafe Jev. Each variant changes a single lever from the default. ★ marks the configuration selected on the Veridian dev split and carried into Compare models." },
  { id: "laya", label: "Laya", recipe: "recipe", note: "ConvAI Laya, English checkpoint, zero-shot. Two levers (compact, chunk) exist only to fit its 512-token context; ★ marks the configuration that combines them, selected on the Veridian dev split." },
  { id: "laya-typed", label: "Laya · typed", recipe: "recipe", note: "Laya typed checkpoint, zero-shot." },
  { id: "laya-multilingual", label: "Laya · multilingual", recipe: "recipe", note: "Laya multilingual checkpoint, zero-shot." },
  { id: "tar", label: "Classical TAR", recipe: "", note: "A simulated reviewer (50 docs/h, $65/h) plus TF-IDF + logistic regression. TAR 1.0 rows vary the size of the coded sample, the cutoff rule (80% recall vs. F1) and reviewer accuracy. Every row is the median of the random seeds." },
];
export const VARIANT_ORDER = ["base", "choice", "score", "crit_none", "crit_struct", "literal", "no_context", "state_string", "gate", "ensemble", "decompose", "preview", "compact", "chunk", "recipe", "recipe_choice",
  "t1_100", "t1_100_f1", "t1_100_noisy", "t1_300", "t1_300_f1", "t1_300_noisy", "t1_1000", "t1_1000_f1", "t1_1000_noisy", "t1_5000", "t1_5000_f1", "t1_5000_noisy", "cal", "cal_75", "cal_perfect", "cal_knee"];
export const VARIANT_LABEL: Record<string, string> = {
  base: "default", choice: "Choice form", score: "Score form", crit_none: "no criteria", crit_struct: "structured criteria", literal: "literal phrasing",
  no_context: "no matter context", state_string: "flat-string state", gate: "gated", ensemble: "3-phrasing ensemble", decompose: "decomposed",
  preview: "jev-preview", compact: "compact", chunk: "chunked", recipe: "compact + chunk", recipe_choice: "compact + chunk, Choice",
  t1_100: "TAR 1.0 · 100 coded", t1_100_f1: "TAR 1.0 · 100 · F1 cutoff", t1_100_noisy: "TAR 1.0 · 100 · 90% reviewer",
  t1_300: "TAR 1.0 · 300 coded", t1_300_f1: "TAR 1.0 · 300 · F1 cutoff", t1_300_noisy: "TAR 1.0 · 300 · 90% reviewer",
  t1_1000: "TAR 1.0 · 1,000 coded", t1_1000_f1: "TAR 1.0 · 1,000 · F1 cutoff", t1_1000_noisy: "TAR 1.0 · 1,000 · 90% reviewer",
  t1_5000: "TAR 1.0 · 5,000 coded", t1_5000_f1: "TAR 1.0 · 5,000 · F1 cutoff", t1_5000_noisy: "TAR 1.0 · 5,000 · 90% reviewer",
  cal: "TAR 2.0 · CAL (80% target)", cal_75: "TAR 2.0 · CAL · 75% target", cal_perfect: "TAR 2.0 · CAL · perfect reviewer", cal_knee: "TAR 2.0 · CAL · knee stop",
};
/**
 * One-line definition of each configuration, the highlighted clause of the details modal's opening sentence
 * ("<name> is the configuration in which <definition>."). Lower-case clauses, no trailing stop. Keyed by model key
 * (family@variant); the typed and multilingual Laya checkpoints fall back to laya@<variant>. TAR 1.0 rows are templates
 * with {n} for the coded-sample size. Text follows the lever notes in ediscovery_bench/examples.py and export.py.
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
  "jev@preview": "the request is identical to the default but is sent to the jev-preview model instead of jev-1.13.0",
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
  "laya@recipe_choice": "compact + chunk with the Choice question form",
  // Laya, supervised (the Compare models row)
  "laya-ft": "Laya's compact + chunk request is sent to a checkpoint fine-tuned (RLCD) on a 30% document-level dev split of {corpus}'s own gold labels and scored on the held-out 70%; the request does not change, the weights do",
  // Generative models: one definition, the prompt is the same for every model
  "llm": "one chat completion per document (all issues at once) or per issue, with a JSON schema the vendor enforces on the reply: a label and p(responsive), no free text",
  // Classical TAR 1.0, templated on the coded-sample size
  "tar@t1": "a simulated reviewer (50 documents/hour, $65/hour) codes {n} random documents and a TF-IDF + logistic-regression classifier learns from those codes and labels the rest, with a cutoff targeting 80% recall chosen by 5-fold cross-validation on the coded sample",
  "tar@t1_f1": "the TAR 1.0 · {n} coded workflow with the classifier cutoff set to maximise F1 on the coded sample instead of targeting 80% recall",
  "tar@t1_noisy": "the TAR 1.0 · {n} coded workflow with an imperfect reviewer, who misses 10% of relevant documents and over-codes 2% of non-relevant ones",
};
/** The definition for a model key on a corpus: resolves the Laya checkpoints, the TAR templates and the {corpus} placeholder. */
export const variantDefinition = (key: string, corpusLabel: string): string | undefined => {
  const [fam, v] = key.includes("@") ? key.split("@") : [key, ""];
  let d = VARIANT_DEFINITION[key] ?? (fam.startsWith("laya") && v ? VARIANT_DEFINITION[`laya@${v}`] : undefined);
  if (!d && fam === "tar") {
    const m = /^t1_(\d+)(_f1|_noisy)?$/.exec(v);
    if (m) d = VARIANT_DEFINITION[`tar@t1${m[2] ?? ""}`]?.replace("{n}", fmtInt(Number(m[1])));
  }
  if (!d && !key.includes("@") && key !== "lexical") d = VARIANT_DEFINITION.llm;
  return d?.replace("{corpus}", corpusLabel);
};
/** TAR variants share a hue per coded-sample size so the three rows of one stage read as a family. */
const TAR_VARIANT_COLOR: Record<string, string> = {
  t1_100: "var(--c-tar-1)", t1_100_f1: "var(--c-tar-1)", t1_100_noisy: "var(--c-tar-1)",
  t1_300: "var(--c-tar-2)", t1_300_f1: "var(--c-tar-2)", t1_300_noisy: "var(--c-tar-2)",
  t1_1000: "var(--c-tar-3)", t1_1000_f1: "var(--c-tar-3)", t1_1000_noisy: "var(--c-tar-3)",
  t1_5000: "var(--c-tar-4)", t1_5000_f1: "var(--c-tar-4)", t1_5000_noisy: "var(--c-tar-4)",
  cal: "var(--c-cal)", cal_75: "var(--c-cal)", cal_perfect: "var(--c-cal)", cal_knee: "var(--c-cal)",
};
const VARIANT_PALETTE = Array.from({ length: 16 }, (_, i) => `var(--v${i})`);
export const variantColor = (v: string, recipe: string) => TAR_VARIANT_COLOR[v] ?? (v === recipe ? "var(--c-jev)" : v === "base" ? "var(--c-base)" : VARIANT_PALETTE[(VARIANT_ORDER.indexOf(v) + 1) % VARIANT_PALETTE.length]);

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
