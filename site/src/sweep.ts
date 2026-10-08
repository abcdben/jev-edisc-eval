import raw from "../../results/sweep.json";
import { corpusKey, pick, type CI, type IssueScore, type PRF, type Rec } from "./data";
import type { View } from "./App";

/**
 * Threshold sweep curves (results/sweep.json, `bench export-sweep`, ediscovery_bench/sweep.py), read by the Studio's Model threshold slider.
 *
 * findings.json scores every model at its own label, so the site's fixed points are the models' own operating points (p ≥ 0.50 for Jev and
 * Laya; the label the LLM returned, which agrees with its p ≥ 0.50 on all but a fraction of a percent of decisions). The sweep carries, per
 * corpus, arm and model, the confusion counts of the same predictions re-cut at p(responsive) ≥ t for t = 0.01 … 0.99 (the export's `thresholds`;
 * `bench export-sweep --step`): `P` gold-positive, `N` gold-negative, `tp[i]`, `fp[i]` at THRESHOLDS[i]; one curve at document level over all gold
 * (`all`), one with gray documents excluded (`nogray`), one per issue at decision level (`issues`, all gold, as findings' all.per_issue), and every
 * decision pooled (`decisions.all`, `decisions.nogray`; findings' decision level). Recall, precision and their 95% Wilson intervals are computed here
 * with metrics.py's formula and findings' rounding, so a curve point agrees with export.py's _prf for the same counts. Models whose label is not a
 * cut on a probability (classical TAR, the keyword baseline) have no curve and stay fixed. The Trade-off page (Tradeoff.tsx) draws the whole curve.
 */
export type Curve = { P: number; N: number; tp: number[]; fp: number[] };
export type SweepCell = { all: Curve; nogray: Curve; issues: Record<string, Curve>; decisions?: { all: Curve; nogray: Curve } };
type Sweep = { thresholds: number[]; z: number; default: number; curves: Record<string, Record<string, Record<string, SweepCell>>> };

export const SWEEP = raw as unknown as Sweep;
export const THRESHOLDS = SWEEP.thresholds;
/** The published operating point: each model's own label, drawn from findings.json; the slider rests here. */
export const DEFAULT_THRESHOLD = SWEEP.default;
/** The export's grid: its first and last cut, and the step between them (0.01 now; 0.05 in the first export), read off the file so a slider follows whatever was exported. */
export const THRESHOLD_MIN = THRESHOLDS[0], THRESHOLD_MAX = THRESHOLDS[THRESHOLDS.length - 1], THRESHOLD_STEP = THRESHOLDS.length > 1 ? Math.round((THRESHOLDS[1] - THRESHOLDS[0]) * 1e4) / 1e4 : 0.05;
const near = (a: number, b: number) => Math.abs(a - b) < 1e-6;
export const isDefaultThreshold = (t: number) => near(t, DEFAULT_THRESHOLD);
/** The index of a threshold on the grid, or -1. */
export const thresholdIndex = (t: number) => THRESHOLDS.findIndex((x) => near(x, t));
/** The index of the published operating point (the 0.50 cut) on the grid. */
export const DEFAULT_INDEX = thresholdIndex(DEFAULT_THRESHOLD);
/** The slider's value as one of the exported thresholds (a stored or linked value that is none of them is dropped). */
export const asThreshold = (raw: unknown): number | undefined => {
  const n = typeof raw === "number" ? raw : typeof raw === "string" ? Number(raw) : NaN;
  return Number.isFinite(n) ? THRESHOLDS.find((t) => near(t, n)) : undefined;
};
export const fmtThreshold = (t: number) => t.toFixed(2);

/** 95% Wilson score interval (metrics.py wilson, z = 1.96). */
export function wilson(k: number, n: number, z = SWEEP.z): [number, number] {
  if (n === 0) return [0, 1];
  const p = k / n;
  const c = (p + (z * z) / (2 * n)) / (1 + (z * z) / n);
  const h = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / (1 + (z * z) / n);
  return [Math.max(0, c - h), Math.min(1, c + h)];
}
const round4 = (x: number) => Math.round(x * 1e4) / 1e4;
/** [point, lo, hi] rounded as export.py _ci does, or null where the denominator is empty. */
export const wilsonCI = (k: number, n: number): CI => (n === 0 ? null : [round4(k / n), round4(wilson(k, n)[0]), round4(wilson(k, n)[1])]);

export const sweepCell = (corpus: string, tag: string, arm: string, model: string): SweepCell | undefined => SWEEP.curves[corpusKey(corpus, tag)]?.[arm]?.[model];
/** Whether a record can be re-cut by the slider at all (it has a curve); false for the fixed rows (TAR, baselines). */
export const hasSweep = (r: Rec): boolean => !!sweepCell(r.corpus, r.tag, r.arm, r.model);

/**
 * 95% interval for F1 = 2tp / (2tp + fp + fn) from the confusion counts, by the delta method over the multinomial (tp, fp, fn, tn) counts
 * (Takahashi, Yamamoto, Kuchiba & Koyama 2022, "Confidence interval for micro-averaged F1 and macro-averaged F1 scores", Appl. Intell.):
 * the documents (or decisions) are the sample, each falling in one of the four cells. findings.json carries F1 as a point alone (export.py
 * _prf), so this is the one interval the site draws for it; it needs the counts, not an export, and reproduces the point exactly. The
 * interval is clipped to [0, 1]; null where F1 is undefined (no positive call and no positive gold). `z` is the Wilson intervals' 1.96.
 */
export function f1CI(tp: number, fp: number, fn: number, tn: number, z = SWEEP.z): CI {
  const n = tp + fp + fn + tn, d = 2 * tp + fp + fn;
  if (n === 0 || d === 0) return null;
  const f = (2 * tp) / d;
  // gradient of F1 in the cell proportions (tp/n, fp/n, fn/n, tn/n): tn does not enter F1
  const g = [(2 * (fp + fn)) / (d * d), (-2 * tp) / (d * d), (-2 * tp) / (d * d), 0].map((x) => x * n);
  const p = [tp / n, fp / n, fn / n, tn / n];
  // multinomial covariance of the proportions: Var = p_i (1 - p_i) / n, Cov = -p_i p_j / n
  let v = 0;
  for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) v += g[i] * g[j] * (i === j ? (p[i] * (1 - p[i])) / n : (-p[i] * p[j]) / n);
  const h = z * Math.sqrt(Math.max(0, v));
  return [round4(f), round4(Math.max(0, f - h)), round4(Math.min(1, f + h))];
}

/**
 * The confusion counts behind a record's recall/precision under the view, for f1CI: read off a document-level PRF (findings carries tp/fp/fn/tn),
 * or rebuilt from an issue's recall, precision and n_pos (findings' per_issue has no counts; the 4-decimal rates recover them exactly while
 * n_pos and the positive calls stay under ~5,000, which every site corpus does).
 */
export function countsOf(detail: PRF | IssueScore | null): { tp: number; fp: number; fn: number; tn: number } | null {
  if (!detail) return null;
  if ("tp" in detail) return { tp: detail.tp, fp: detail.fp, fn: detail.fn, tn: detail.tn };
  if (!detail.recall || !detail.precision) return null;
  const tp = Math.round(detail.recall[0] * detail.n_pos), fp = Math.max(0, Math.round(tp / detail.precision[0]) - tp);
  return { tp, fp, fn: detail.n_pos - tp, tn: Math.max(0, detail.n - detail.n_pos - fp) };
}
/** A record's F1 with its interval under the view at the published operating point: findings' own f1 where it has one (doc level), else from the recall and precision points, the interval from the counts (countsOf). */
export function f1Of(r: Rec, v: View): CI {
  const p = pick(r, v.level, v.gray, v.issue);
  const c = countsOf(p.detail);
  if (!c) return null;
  const ci = f1CI(c.tp, c.fp, c.fn, c.tn);
  if (!ci) return null;
  // the point as published: findings' rounded f1 (export.py _prf, from the rounded recall and precision) over the counts' own ratio
  const own = p.detail && "f1" in p.detail ? p.detail.f1 : p.recall && p.precision && p.recall[0] + p.precision[0] > 0 ? round4((2 * p.recall[0] * p.precision[0]) / (p.recall[0] + p.precision[0])) : null;
  return [own ?? ci[0], ci[1], ci[2]];
}

export type Recut = { recall: CI; precision: CI; f1: number | null; f1ci: CI; tp: number; fp: number; fn: number; tn: number; n: number };
/**
 * A record's recall/precision under the view, re-cut at threshold `t`: the document-level curve (all gold, or gray excluded) or the issue's
 * decision-level curve, as data.ts pick chooses between them. Null where the model has no curve, the view has none for it (decision level
 * over every issue is not exported), or `t` is not an exported threshold.
 */
export function recut(r: Rec, v: View, t: number): Recut | null {
  const cell = sweepCell(r.corpus, r.tag, r.arm, r.model);
  if (!cell) return null;
  const curve = curveOf(cell, v);
  const i = thresholdIndex(t);
  if (!curve || i < 0) return null;
  const tp = curve.tp[i], fp = curve.fp[i], fn = curve.P - tp, tn = curve.N - fp;
  const precision = wilsonCI(tp, tp + fp), recall = wilsonCI(tp, tp + fn);
  const f1 = precision == null || recall == null || precision[0] + recall[0] === 0 ? null : round4((2 * precision[0] * recall[0]) / (precision[0] + recall[0]));
  const ci = f1CI(tp, fp, fn, tn);
  return { recall, precision, f1, f1ci: ci && f1 != null ? [f1, ci[1], ci[2]] : ci, tp, fp, fn, tn, n: curve.P + curve.N };
}

/**
 * The curve a view reads in a cell, as data.ts pick chooses between findings' scores: the issue's decision-level curve, the document-level curve (all
 * gold, or gray excluded), or every decision pooled (`decisions`, absent from exports before the 0.01 grid). Undefined where the cell has none.
 */
export function curveOf(cell: SweepCell, v: Pick<View, "level" | "gray" | "issue">): Curve | undefined {
  if (v.issue) return cell.issues[v.issue];
  if (v.level === "doc") return v.gray === "all" ? cell.all : cell.nogray;
  return cell.decisions?.[v.gray];
}

/** One point of a curve: the counts at THRESHOLDS[i] and the rates behind the Trade-off page's readout (point estimates; the intervals come from wilsonCI / f1CI on the counts). */
export type CurvePoint = { i: number; t: number; tp: number; fp: number; fn: number; tn: number; n: number; recall: number; precision: number | null; f1: number | null; flagged: number; share: number };
export function curvePoint(curve: Curve, i: number): CurvePoint {
  const tp = curve.tp[i], fp = curve.fp[i], fn = curve.P - tp, tn = curve.N - fp, n = curve.P + curve.N, flagged = tp + fp;
  const recall = curve.P ? tp / curve.P : 0, precision = flagged ? tp / flagged : null;
  const f1 = precision == null || precision + recall === 0 ? null : (2 * precision * recall) / (precision + recall);
  return { i, t: THRESHOLDS[i], tp, fp, fn, tn, n, recall, precision, f1, flagged, share: n ? flagged / n : 0 };
}
/** Every point of a curve, lowest threshold first (so recall descends along the array). */
export const curvePoints = (curve: Curve): CurvePoint[] => THRESHOLDS.map((_, i) => curvePoint(curve, i));
/**
 * The highest threshold whose recall still reaches `target` (the Trade-off page's "match recall": the cheapest cut that gets there), or the lowest cut
 * on the grid when none does (`reached: false`). Recall is monotone in the threshold, so this is one pass.
 */
export function indexForRecall(curve: Curve, target: number): { i: number; reached: boolean } {
  for (let i = THRESHOLDS.length - 1; i >= 0; i--) if (curve.P && curve.tp[i] / curve.P >= target - 1e-9) return { i, reached: true };
  return { i: 0, reached: false };
}
