import raw from "../../results/examples.json";
import { SITE_CORPORA, isHidden } from "./data";

export type ExOutput = {
  arm: "single" | "multi";
  label: string | null;
  p_positive: number | null;
  confidence: number | null;
  latency_ms: number | null;
  input_tokens: number | null;
  output_tokens: number | null;
  cost_usd: number | null;
  model_resolved: string | null;
  raw: Record<string, unknown>;
  gold: string | null;
  error: string | null;
} | null;

export type ExConfig = {
  group: string;
  variant: string;
  settings: Record<string, unknown>;
  examples: { request: unknown; output: ExOutput }[];
};

export type ExCorpus = {
  context: string;
  question: { id: string; title: string; rfp_text: string };
  documents: { id: string; text: string; gold: string }[];
  configs: Record<string, ExConfig>;
};

export type Examples = {
  corpora: Record<string, ExCorpus>;
  notes: { jev: Record<string, string>; laya: Record<string, string>; "openai-decisions"?: Record<string, string>; llm: string };
  score_levels: string[];
};

export const EX = raw as unknown as Examples;

/**
 * Families the modal can page through. `members` is resolved per corpus from the config keys.
 * `hidden` families are not offered in the FAMILY menu (only the Laya method charted on Compare models is a family there); the modal still
 * resolves their keys when the Configurations page opens one, and lists that family while it is the current one.
 */
export const EX_GROUPS: { id: string; label: string; match: (k: string) => boolean; intro: string; hidden?: boolean }[] = [
  {
    id: "jev", label: "Jev", match: (k) => k.startsWith("jev@"),
    intro: "Jev is a decision model: it does not write text. Each call sends a state (the document, and usually the matter background) plus one or more typed questions; the answer to each is a **probability**, an option with probabilities, or a level on an ordinal scale. Every configuration is zero-shot: the criteria as written, no examples. Switch configurations to see exactly what changes in the request, and what the model returned for the same document.",
  },
  {
    // the fine-tuned checkpoint (the Laya row on Compare models, key `laya-ft`) and the zero-shot English-checkpoint configurations it was built from
    id: "laya", label: "Laya", match: (k) => k === "laya-ft" || k.startsWith("laya@"),
    intro: "Laya is a local decision model with the same three question types (Noul / Choice / Score). It reads at most **512 tokens**: the question head takes up to 192, the rest is the document, truncated from the right. Two of its configurations (Compact Question, Chunked Document) exist only to work around that limit. The **fine-tuned** configuration is the Laya row on Compare models and the one supervised row in this zero-shot comparison: the Compact + Chunked request sent to a checkpoint fine-tuned (RLCD) on a 30% document-level dev split of the corpus and scored on the held-out 70%; every other configuration here is zero-shot, and the labeled data the fine-tuning needed is not counted in the time and cost panels.",
  },
  {
    id: "openai-decisions", label: "OpenAI Decisions", match: (k) => k.startsWith("openai-decisions@"),
    intro: "OpenAI's Decisions API (GPT-6 Luna, `POST /v1/decisions`, public beta since 2026-10-06) is a decision model in the same sense as Jev: it does not write text. Each call sends one flat text **input** and a list of typed questions (`predicate`, `choice`, `score`); the answer to each is a probability, an option with probabilities and a confidence, or a weighted level. Two of the configurations here are the forms that map onto Jev's Noul and Choice, with the same RFP instruction and the same positive/negative descriptions; the third, Facets, is Jev's Facets lever on the predicate form: one predicate per facet, max-combined. Billed on input tokens only.",
  },
  { id: "laya-typed", label: "Laya · typed", hidden: true, match: (k) => k.startsWith("laya-typed@"), intro: "The typed Laya checkpoint, zero-shot, same request shapes as Laya." },
  { id: "laya-multilingual", label: "Laya · multilingual", hidden: true, match: (k) => k.startsWith("laya-multilingual@"), intro: "The multilingual Laya checkpoint, zero-shot, same request shapes as Laya." },
  {
    id: "llm", label: "Language models", match: (k) => !k.includes("@") && k !== "lexical" && k !== "laya-ft",
    intro: "Every generative model received the **same zero-shot prompt**, described below, with no examples and no per-model tuning; the reply is a label and a probability, nothing else. Switch models to see the settings that differ; the prompt does not.",
  },
];

export const groupOf = (key: string) => EX_GROUPS.find((g) => g.match(key))?.id ?? "jev";
/** The family's configurations with examples on this corpus, less the keys the site hides (data.ts HIDDEN_MODELS). */
export const membersOf = (corpus: string, group: string): string[] => {
  const g = EX_GROUPS.find((x) => x.id === group)!;
  const c = EX.corpora[corpus];
  if (!c) return [];
  return Object.keys(c.configs).filter((k) => g.match(k) && !isHidden(k));
};

/** Corpus key used by the site view -> corpus key in examples.json; only site corpora are eligible, first one with examples as fallback. */
export const exCorpus = (viewCorpus: string) => (SITE_CORPORA.includes(viewCorpus) && EX.corpora[viewCorpus] ? viewCorpus : SITE_CORPORA.find((c) => EX.corpora[c]) ?? viewCorpus);
