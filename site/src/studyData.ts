import raw from "../../results/study.json";
import { fmtInt, fmtMs, fmtPct, fmtUSD, type CI } from "./data";
import { fmtRate, gridCell, gridFor, isPublished, publishedText, reviewerEffort, sameReviewer, type ReviewerSetting } from "./tarGrid";

/** results/study.json, written by `bench export-study` (ediscovery_bench/study.py). */
export type ArmKind = "system1" | "system1_ft" | "llm" | "local_llm" | "tar" | "baseline" | "human";
export type Status = "measured" | "planned" | "na";
export type Unit = "pct" | "ms" | "usd" | "hours" | "ratio" | "kappa" | "auc";
export type ChartKind = "pr" | "bars" | "grid" | "roc" | "frontier";

export type Dataset = { id: string; label: string; short: string; status: "measured" | "planned"; n_docs?: number; n_issues?: number; gold?: string; human_signals: string[] };
export type Arm = { id: string; name: string; short: string; kind: ArmKind; maker: string; color: string; status: "measured" | "planned"; note?: string };
export type Measure = { id: string; label: string; unit: Unit; higher_better: boolean };
export type Experiment = { id: string; group: string; title: string; question: string; chart: ChartKind; measures: Measure[]; datasets: string[]; humans: string[]; na?: string; status: Record<string, Status> };
export type Cell = { v: number | null; lo: number | null; hi: number | null; n: number | null; planned: boolean; note?: string };
export type Study = { generated: string; datasets: Dataset[]; arms: Arm[]; experiments: Experiment[]; values: Record<string, Record<string, Record<string, Record<string, Cell>>>> };

export const STUDY = raw as unknown as Study;
export const ARM_BY_ID: Record<string, Arm> = Object.fromEntries(STUDY.arms.map((a) => [a.id, a]));
export const DS_BY_ID: Record<string, Dataset> = Object.fromEntries(STUDY.datasets.map((d) => [d.id, d]));
export const EX_BY_ID: Record<string, Experiment> = Object.fromEntries(STUDY.experiments.map((e) => [e.id, e]));

export const KIND_ORDER: ArmKind[] = ["system1", "system1_ft", "llm", "local_llm", "tar", "human", "baseline"];
export const KIND_LABEL: Record<ArmKind, string> = {
  system1: "Decision models", system1_ft: "Decision models, supervised", llm: "Large language models", local_llm: "Open-weight LLM (local)",
  tar: "Classical TAR", human: "Humans", baseline: "Floor",
};
export const isHuman = (a: Arm) => a.kind === "human";

/** Experiments in group order, the groups themselves in first-appearance order. */
export const GROUPS: { group: string; items: Experiment[] }[] = (() => {
  const out: { group: string; items: Experiment[] }[] = [];
  for (const e of STUDY.experiments) {
    const g = out.find((x) => x.group === e.group);
    if (g) g.items.push(e); else out.push({ group: e.group, items: [e] });
  }
  return out;
})();

export const cell = (ds: string, ex: string, arm: string, m: string): Cell | null => STUDY.values[ds]?.[ex]?.[arm]?.[m] ?? null;

/** The measures the TAR reviewer grid can re-point (tarGrid.ts), by experiment; every other cell (elusion, the human-side measures) stays as study.json has it. */
export const REVIEWER_MEASURES: Record<string, string[]> = {
  accuracy: ["recall", "precision", "f1"],
  workflow: ["recall", "human_share", "hours_per_100k", "usd_per_100k"],
  speed_cost: ["latency_p50_ms", "usd_per_100k", "hours_per_100k"],
};
/**
 * A cell under a reviewer setting: for a TAR arm whose dataset has a grid, the grid cell's value for the measures above (results/study.json is not
 * changed; the arithmetic is export.py _tar_ops', tarGrid.ts tarOps), carrying a `note` naming the rates where they are not the arm's published
 * ones (the default cell equals study.json's, so it is left unmarked); otherwise, and at `published`, the published cell. The dataset ids are the
 * corpus keys of results/tar_grid.json and the arm ids the TAR model keys, so the lookup is direct.
 */
export function reviewerCell(ds: string, ex: string, arm: string, m: string, r: ReviewerSetting): Cell | null {
  const c = cell(ds, ex, arm, m);
  if (!c || isPublished(r) || !REVIEWER_MEASURES[ex]?.includes(m)) return c;
  const g = gridFor(ds, arm), hit = g && gridCell(g, r);
  if (!g || !hit || sameReviewer(hit, g.default)) return c;
  const { cell: gc, fn, fp } = hit, n = gc.n_corpus, { hours, cost_usd } = reviewerEffort(g, gc.docs_reviewed);
  const ci = (x: CI): Pick<Cell, "v" | "lo" | "hi"> => (x ? { v: x[0], lo: x[1], hi: x[2] } : { v: null, lo: null, hi: null });
  const pt = (v: number | null): Pick<Cell, "v" | "lo" | "hi"> => ({ v, lo: null, hi: null });
  const val =
    m === "recall" ? ci(gc.doc.recall) : m === "precision" ? ci(gc.doc.precision) : m === "f1" ? pt(gc.doc.f1)
    : m === "human_share" ? pt(gc.review_share) : m === "hours_per_100k" ? pt((hours * 1e5) / n) : m === "usd_per_100k" ? pt((cost_usd / n) * 1e5)
    : m === "latency_p50_ms" ? pt((hours * 3.6e6) / n) : null;
  return val ? { ...c, ...val, note: `${ARM_BY_ID[arm]?.short ?? arm}: reviewer misses ${fmtRate(fn)} / over-codes ${fmtRate(fp)}; published assumed ${publishedText(g.default)}` } : c;
}
/** Whether any selected TAR arm has a grid on a dataset, and the arms' grids for the control (components/TarReviewer.tsx). */
export const reviewerArms = (ds: string, arms: Arm[]) => arms.filter((a) => a.kind === "tar").map((a) => ({ model: a.id, name: a.short, grid: gridFor(ds, a.id) ?? null }));
/** Every arm with at least one value for the dataset × experiment. */
export const armsWithData = (ds: string, ex: string): string[] => Object.keys(STUDY.values[ds]?.[ex] ?? {});

export const DEFAULT_ARMS = ["jev@base", "openai-decisions@predicate", "claude-sonnet-5", "gpt-5.6-luna", "gemini-3.8-flash", "tar@cal", "human@firstpass", "human@literature"];
export const DEFAULT_DATASETS = ["trec", "legal09", "legal10"];

/** A value in its unit; `ci` adds the interval when present. */
export function fmtValue(v: number | null | undefined, unit: Unit): string {
  if (v == null) return "—";
  switch (unit) {
    case "pct": return fmtPct(v);
    case "ms": return fmtMs(v);
    case "usd": return fmtUSD(v);
    case "hours": return v < 10 ? `${v.toFixed(1)} h` : `${fmtInt(Math.round(v))} h`;
    case "ratio": return `${v.toFixed(2)}×`;
    case "kappa": return v.toFixed(2);
    case "auc": return v.toFixed(3);
  }
}
export const fmtCell = (c: Cell | null, unit: Unit): string => {
  if (!c || c.v == null) return "—";
  const s = fmtValue(c.v, unit);
  return c.lo != null && c.hi != null ? `${s}  [${fmtValue(c.lo, unit)}, ${fmtValue(c.hi, unit)}]` : s;
};
/** Log axes for the units that span orders of magnitude between humans and models. */
export const isLogUnit = (u: Unit) => u === "ms" || u === "usd" || u === "hours";
export const unitDomain = (u: Unit): [number, number] | null => (u === "pct" ? [0, 1] : u === "auc" ? [0.5, 1] : u === "kappa" ? [-0.2, 1] : null);
