import raw from "../../results/tar_grid.json";
import { type CI, type IssueScore, type Ops, type PRF, type Rec } from "./data";
import { f1CI, wilsonCI } from "./sweep";

/**
 * The TAR reviewer error-rate grid (results/tar_grid.json, `bench tar-grid`, ediscovery_bench/tar.py): each headline TAR workflow re-run with the
 * simulated reviewer missing a share `fn` of relevant documents and over-coding a share `fp` of non-relevant ones, at every pair of the grid's
 * rates, the classifier retrained and the stop rule re-run per cell. One cell per (fn, fp): the production set's document-level recall, precision
 * and F1 with findings' Wilson intervals, the per-issue intervals, the documents the reviewer read and the hours and dollars that cost at the run's
 * reviewer economics (export.py _tar_ops). The default cell (the run's own rates) equals findings.json, asserted at export, so the `published`
 * setting shows the published figures exactly. The pages start at REALISTIC_REVIEWER instead, the same rates on every TAR arm; a TAR arm with no
 * grid on the current corpus (its pool was not on the machine at export) stays at its published figures whatever the setting.
 */
export type GridCell = {
  doc: { recall: CI; precision: CI; f1: number | null };
  per_issue: Record<string, { recall: CI; precision: CI }>;
  docs_reviewed: number; hours: number; cost_usd: number; n_corpus: number; review_share: number;
  seeds: { recall: number; precision: number; docs_reviewed: number }[];
  recall_range: [number, number] | null; precision_range: [number, number] | null;
};
export type Grid = {
  corpus: string; variant: string; kind: "t1" | "cal"; default: Reviewer; fn: number[]; fp: number[]; seeds: number; median_rule: string;
  reviewer: { docs_per_hour: number; usd_per_hour: number }; default_check?: string; cells: Record<string, GridCell>;
  /** Over-code rates from `fp_min` up were not run (tar.py grid_unavailable: TREC CAL, where the stop rule does not converge); `fp` still lists them so the slider ticks align across corpora. */
  unavailable?: GridUnavailable;
};
export type GridUnavailable = { fp_min: number; reason: string };
/** The reviewer's two error rates: `fn` the miss rate on relevant documents, `fp` the over-code rate on non-relevant ones. */
export type Reviewer = { fn: number; fp: number };
/**
 * The site-wide default reviewer: a realistic human reviewer, missing 10% of relevant documents and over-coding 2% of non-relevant ones (the
 * rates the published CAL runs assumed; both are grid ticks). Every page's reviewer control starts here when nothing is remembered, and its
 * Default button returns here.
 */
export const REALISTIC_REVIEWER: Reviewer = { fn: 0.1, fp: 0.02 };
/** The setting's other value: each TAR arm at the rates its own published run assumed (its grid's `default` cell, which equals findings.json). */
export const PUBLISHED = "published" as const;
/** What the reviewer controls hold: one pair of rates applied to every TAR arm, or `published`, each arm at its own published rates. */
export type ReviewerSetting = Reviewer | typeof PUBLISHED;
export const isPublished = (r: ReviewerSetting): r is typeof PUBLISHED => r === PUBLISHED;

export const TAR_GRID = raw as unknown as Record<string, Record<string, Grid>>;
/** What the control steps through (components/TarReviewer.tsx): the two rate arrays and a default; a Grid is one, the explorer builds one from a TAR arm's meta. */
export type RateGrid = Pick<Grid, "fn" | "fp" | "default" | "unavailable">;
/** The over-code rates a grid has cells for: `fp` below `unavailable.fp_min` (all of them where nothing was left out). */
export const availableFp = (g: RateGrid): number[] => (g.unavailable ? g.fp.filter((v) => v < g.unavailable!.fp_min - 1e-9) : g.fp);
/** The grid's rate steps, the same for every exported grid (tar.py tar-grid): the explorer's sliders use them too. */
export const GRID_RATES: Pick<Grid, "fn" | "fp"> = (() => { const g = Object.values(TAR_GRID).flatMap((v) => Object.values(v))[0]; return g ? { fn: g.fn, fp: g.fp } : { fn: [0, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5], fp: [0, 0.01, 0.02, 0.05, 0.1, 0.15, 0.2] }; })();

/** The grid variant a TAR model key names: tar@cal → cal, tar@t1_1000_div → t1_1000_div; null for anything else. */
export const gridVariant = (model: string): string | null => (model.startsWith("tar@") ? model.slice(4) : null);
/** The grid for a TAR model on a corpus, if the export has one. */
export function gridFor(corpus: string, model: string): Grid | undefined {
  const v = gridVariant(model);
  return v ? TAR_GRID[corpus]?.[v] : undefined;
}
export const isTarModel = (model: string) => model.startsWith("tar@");

const near = (a: number, b: number) => Math.abs(a - b) < 1e-6;
/** The grid value nearest to `x` (the sliders only ever produce grid values; a stored one off the grid snaps). */
export const nearestOf = (xs: number[], x: number): number => xs.reduce((best, v) => (Math.abs(v - x) < Math.abs(best - x) ? v : best), xs[0]);
/** A cell's key as the export writes it: "%g,%g" of the two rates. */
const cellKey = (fn: number, fp: number) => `${Number(fn.toPrecision(6))},${Number(fp.toPrecision(6))}`;
/** The cell at the grid point nearest the rates, with the rates it snapped to (an over-code rate the grid did not run snaps to the highest it did). */
export function gridCell(g: Grid, r: Reviewer): { cell: GridCell; fn: number; fp: number } | null {
  const fn = nearestOf(g.fn, r.fn), fp = nearestOf(availableFp(g), r.fp);
  const cell = g.cells[cellKey(fn, fp)];
  return cell ? { cell, fn, fp } : null;
}
export const sameReviewer = (a: Reviewer, b: Reviewer): boolean => near(a.fn, b.fn) && near(a.fp, b.fp);
export const sameSetting = (a: ReviewerSetting, b: ReviewerSetting): boolean => (isPublished(a) || isPublished(b) ? a === b : sameReviewer(a, b));
/**
 * A stored or linked value as a reviewer setting: "published", or a pair with both rates finite in [0, 1]; anything else (including the null that
 * stood for the published figures before the realistic default existed) is undefined, and the page starts at REALISTIC_REVIEWER.
 */
export const asReviewer = (raw: unknown): ReviewerSetting | undefined => {
  if (raw === PUBLISHED) return PUBLISHED;
  if (!raw || typeof raw !== "object") return undefined;
  const o = raw as Record<string, unknown>, fn = Number(o.fn), fp = Number(o.fp);
  return Number.isFinite(fn) && Number.isFinite(fp) && fn >= 0 && fn <= 1 && fp >= 0 && fp <= 1 ? { fn, fp } : undefined;
};
/** A rate as the controls print it: "10%", "2%", "0%". */
export const fmtRate = (x: number) => `${Math.round(x * 1000) / 10}%`;
/** A pair as the hints print it: "10% / 2%" (misses / over-codes). */
export const fmtRates = (r: Reviewer) => `${fmtRate(r.fn)} / ${fmtRate(r.fp)}`;
/** A published pair as the hints describe it: "a perfect reviewer" at 0 / 0, else the rates. */
export const publishedText = (p: Reviewer) => (near(p.fn, 0) && near(p.fp, 0) ? "a perfect reviewer" : fmtRates(p));
/** The rates a TAR record's published run assumed: its grid's default where one exists, else the sidecar's reviewer rates (data.ts Rec.tar). */
export function publishedRates(rec: Rec): Reviewer | undefined {
  const g = gridFor(rec.corpus, rec.model);
  if (g) return g.default;
  const rv = rec.tar?.reviewer;
  return rv ? { fn: rv.miscode_rate, fp: rv.fp_rate ?? rv.miscode_rate / 5 } : undefined;
}
/** The PNG-filename token of a setting: rev-fn20-fp05. */
export const reviewerToken = (r: Reviewer) => `rev-fn${String(Math.round(r.fn * 100)).padStart(2, "0")}-fp${String(Math.round(r.fp * 100)).padStart(2, "0")}`;

/** Hours and dollars from documents reviewed at the grid's reviewer economics (tar.py: docs_per_hour, usd_per_hour); the cells carry the same numbers. */
export const reviewerEffort = (g: Grid, docsReviewed: number) => {
  const hours = docsReviewed / g.reviewer.docs_per_hour;
  return { hours, cost_usd: hours * g.reviewer.usd_per_hour };
};
/** The ops block of a TAR record for an effort, as export.py _tar_ops derives it: human review is the whole cost, amortised over the corpus the workflow ran on. */
export function tarOps(ops: Ops, g: Grid, docsReviewed: number, nCorpus: number): Ops {
  const { hours, cost_usd } = reviewerEffort(g, docsReviewed);
  const n = nCorpus;
  return {
    ...ops, cost_basis: "human review",
    cost_per_doc: cost_usd / n, list_cost_per_doc: cost_usd / n, paid_cost_per_doc: cost_usd / n, cost_usd_total: cost_usd, cost_usd_paid_total: cost_usd,
    doc_latency_p50_ms: (hours * 3.6e6) / n, doc_latency_p95_ms: null, doc_latency_p50_ci_ms: null, hours_per_100k_docs: (hours * 1e5) / n,
    latency_source: `simulated reviewer at ${g.reviewer.docs_per_hour.toFixed(0)} docs/hour, $${g.reviewer.usd_per_hour.toFixed(0)}/hour: ${docsReviewed.toLocaleString("en-US")} of ${n.toLocaleString("en-US")} documents reviewed (${hours.toFixed(1)} h); compute not charged`,
  };
}

/** Confusion counts behind a recall/precision pair over `nPos` gold positives among `n` documents (the 4-decimal rates recover them exactly at the site's corpus sizes; sweep.ts countsOf). */
const countsFrom = (recall: CI, precision: CI, nPos: number, n: number) => {
  if (!recall || !precision) return null;
  const tp = Math.round(recall[0] * nPos), fp = precision[0] > 0 ? Math.max(0, Math.round(tp / precision[0]) - tp) : 0;
  return { tp, fp, fn: nPos - tp, tn: Math.max(0, n - nPos - fp) };
};
/** A document-level PRF re-pointed at a cell: the cell's intervals, counts rebuilt over the record's own gold (the eval set does not change between cells), the cell's F1. */
function patchPRF(p: PRF, doc: GridCell["doc"]): PRF {
  const c = countsFrom(doc.recall, doc.precision, p.tp + p.fn, p.n);
  if (!c) return { ...p, recall: doc.recall, precision: doc.precision, f1: doc.f1 };
  // elusion = fn / (fn + tn) with its Wilson interval, as export.py _prf
  return { ...p, ...c, recall: doc.recall, precision: doc.precision, f1: doc.f1, elusion: wilsonCI(c.fn, c.fn + c.tn) };
}
/** The F1 interval of a cell over the record's gold, by the delta method over the rebuilt counts (sweep.ts f1CI); the point is the cell's own. */
export function cellF1(doc: GridCell["doc"], nPos: number, n: number): CI {
  const c = countsFrom(doc.recall, doc.precision, nPos, n);
  if (!c) return null;
  const ci = f1CI(c.tp, c.fp, c.fn, c.tn);
  return ci ? [doc.f1 ?? ci[0], ci[1], ci[2]] : null;
}

export type Applied = {
  /** The records, the TAR ones with a grid re-pointed at the chosen cell (the rest as given). */
  recs: Rec[];
  /** TAR model keys moved by the grid, with the rates they snapped to. */
  moved: Map<string, Reviewer>;
  /** TAR model keys with no grid on this corpus: fixed at their published point. */
  fixed: string[];
  /** The moved keys whose cell is not their grid's default: their figures differ from findings.json (the pages footnote these with ‡). */
  offPublished: string[];
};
/**
 * The records under a reviewer setting. `published` leaves every record as findings.json has it. Otherwise each TAR record whose corpus and variant
 * have a grid is re-pointed at the cell nearest the rates: `all.doc` (recall, precision, F1, the counts and elusion rebuilt over its gold),
 * `all.per_issue` (recall and precision; n_pos and n stay), the `tar` sidecar's effort and rates, and `ops` cost and hours (tarOps). `nogray.doc`
 * follows `all.doc` where the record had no gray documents (the two were equal); the decision-level scores, which the grid does not carry, are
 * left. Every other record is returned as is.
 */
export function applyReviewer(recs: Rec[], r: ReviewerSetting): Applied {
  const moved = new Map<string, Reviewer>(), fixed: string[] = [], offPublished: string[] = [];
  if (isPublished(r)) return { recs, moved, fixed, offPublished };
  const out = recs.map((rec) => {
    if (!isTarModel(rec.model)) return rec;
    const g = gridFor(rec.corpus, rec.model);
    const hit = g && gridCell(g, r);
    if (!g || !hit) { fixed.push(rec.model); return rec; }
    moved.set(rec.model, { fn: hit.fn, fp: hit.fp });
    if (!sameReviewer(hit, g.default)) offPublished.push(rec.model);
    const { cell } = hit;
    const doc = patchPRF(rec.all.doc, cell.doc);
    const per_issue = rec.all.per_issue && Object.fromEntries(Object.entries(rec.all.per_issue).map(([k, s]) => {
      const c = cell.per_issue[k];
      return [k, c ? { ...s, recall: c.recall, precision: c.precision } satisfies IssueScore : s];
    }));
    const sameNogray = rec.nogray.doc.n === rec.all.doc.n && rec.nogray.doc.tp === rec.all.doc.tp && rec.nogray.doc.fp === rec.all.doc.fp;
    const { hours, cost_usd } = reviewerEffort(g, cell.docs_reviewed);
    const n = rec.tar?.n_corpus ?? cell.n_corpus;
    return {
      ...rec,
      all: { ...rec.all, doc, per_issue },
      nogray: sameNogray ? { ...rec.nogray, doc } : rec.nogray,
      ops: tarOps(rec.ops, g, cell.docs_reviewed, n),
      tar: rec.tar && { ...rec.tar, docs_reviewed: cell.docs_reviewed, review_share: cell.docs_reviewed / n, hours, cost_usd, recall_range: cell.recall_range, precision_range: cell.precision_range, reviewer: { ...rec.tar.reviewer, miscode_rate: hit.fn, fp_rate: hit.fp } },
    };
  });
  return { recs: out, moved, fixed, offPublished };
}

/** What the selected TAR arms offer the control: the grids they have on this corpus (fn/fp arrays, defaults) and the arms with none. */
export function gridsOf(corpus: string, models: string[]): { grids: { model: string; grid: Grid }[]; missing: string[] } {
  const grids: { model: string; grid: Grid }[] = [], missing: string[] = [];
  for (const m of models) {
    if (!isTarModel(m)) continue;
    const g = gridFor(corpus, m);
    if (g) grids.push({ model: m, grid: g }); else missing.push(m);
  }
  return { grids, missing };
}
