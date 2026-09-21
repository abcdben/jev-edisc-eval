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
  notes: { jev: Record<string, string>; laya: Record<string, string>; llm: string };
  score_levels: string[];
};

export const EX = raw as unknown as Examples;

/** Families the modal can page through. `members` is resolved per corpus from the config keys. */
export const EX_GROUPS: { id: string; label: string; match: (k: string) => boolean; intro: string }[] = [
  {
    id: "jev", label: "Jev", match: (k) => k.startsWith("jev@"),
    intro: "Jev is a decider model: it does not write text. Each call sends a state (the document, and usually the matter background) plus one or more typed questions; the answer to each is a **probability**, an option with probabilities, or a level on an ordinal scale. Switch configurations to see exactly what changes in the request, and what the model returned for the same document.",
  },
  {
    id: "laya", label: "Laya", match: (k) => k.startsWith("laya@"),
    intro: "Laya is a local decider model with the same three question types (Noul / Choice / Score). It reads at most **512 tokens**: the question head takes up to 192, the rest is the document, truncated from the right. Two of its configurations (compact, chunked) exist only to work around that limit.",
  },
  { id: "laya-typed", label: "Laya · typed", match: (k) => k.startsWith("laya-typed@"), intro: "The typed Laya checkpoint, same request shapes as Laya." },
  { id: "laya-multilingual", label: "Laya · multilingual", match: (k) => k.startsWith("laya-multilingual@"), intro: "The multilingual Laya checkpoint, same request shapes as Laya." },
  {
    id: "laya-ft", label: "Laya · fine-tuned", match: (k) => k === "laya-ft",
    intro: "Laya is a local decider model; its zero-shot configurations are under the Laya family. Here only the **weights** differ, and the labeled data the fine-tuning needed is not counted in the time and cost panels.",
  },
  {
    id: "llm", label: "Language models", match: (k) => !k.includes("@") && k !== "lexical" && k !== "laya-ft",
    intro: "Every generative model received the **same prompt**, described below; the reply is a label and a probability, nothing else. Switch models to see the settings that differ; the prompt does not.",
  },
  {
    id: "tar", label: "Classical TAR", match: (k) => k.startsWith("tar@"),
    intro: "**No model reads the request.** A simulated reviewer codes documents by hand from the gold labels and a TF-IDF + logistic-regression classifier learns from those codes. The request shown is the workflow and the coded sample; the output is the median seed's call on this document. Switch rows to compare sample sizes, cutoff rules and reviewer accuracy.",
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
