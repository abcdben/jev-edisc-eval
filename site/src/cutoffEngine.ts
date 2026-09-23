/**
 * The Cutoffs page's arithmetic (CutoffsPage.tsx): decode public/cutoffs.json (site/tools/build_cutoffs.py), score a model at any set of
 * per-issue probability cutoffs, sweep a shared cutoff into a precision–recall curve, and choose cutoffs (per-issue F1, pooled F1 by
 * coordinate ascent, a recall target). Definitions follow ediscovery_bench/export.py: a decision is one (document, issue); document level
 * calls a document responsive when any issue is, over the cells the model has; `nogray` drops debatable-gold decisions and, at document level,
 * every document that has a debatable label. Cutoff c flags a decision when p ≥ c. The published benchmark scores each model's stated label
 * instead, which the file carries as a bit per cell; that is the "benchmark default" every figure is compared against.
 */

export type IssueMeta = { id: string; title: string; short: string; n_pos: number; n_gray: number };
export type ModelData = { key: string; p: Float64Array; label: Uint8Array; nDocs: number; nCells: number; nErr: number; nDisagree: number };
export type CorpusData = {
  key: string; display: string; label: string; nDocs: number; nPosDocsAny: number; docs: string[]; issues: IssueMeta[];
  gold: Uint8Array; gray: Uint8Array; docGray: Uint8Array; models: Record<string, ModelData>;
};
export type CutoffsFile = { version: number; corpora: Record<string, CorpusData> };
export type Gray = "all" | "nogray";
export type Level = "doc" | "decision";

/** The cutoff grid: 201 steps of 0.005. Slider positions are grid indices; `gridValue(i)` is the same double the decoder produces for a u8 value i, so equality at a grid point is exact. */
export const GRID_N = 200;
export const gridValue = (i: number) => i / GRID_N;
export const DEFAULT_CUTOFF_IDX = GRID_N / 2;

const b64 = (s: string): Uint8Array => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const unpackBits = (s: string, n: number): Uint8Array => {
  const bytes = b64(s), out = new Uint8Array(n);
  for (let i = 0; i < n; i++) out[i] = (bytes[i >> 3] >> (i & 7)) & 1;
  return out;
};

type RawModel = { enc: "u8" | "u16"; p: string; label: string; n_docs: number; n_cells: number; n_err: number; n_disagree: number };
type RawCorpus = { display: string; label: string; n_docs: number; n_pos_docs_any: number; docs: string[]; issues: IssueMeta[]; gold: string; gray: string; models: Record<string, RawModel> };

/** Decode the generator's JSON: base64 bit sets to Uint8Array, quantized probabilities to Float64Array (NaN where the model has no decision). */
export function decodeCutoffs(raw: { version: number; corpora: Record<string, RawCorpus> }): CutoffsFile {
  const corpora: Record<string, CorpusData> = {};
  for (const [key, c] of Object.entries(raw.corpora)) {
    const nq = c.issues.length, n = c.n_docs * nq;
    const gold = unpackBits(c.gold, n), gray = unpackBits(c.gray, n);
    const docGray = new Uint8Array(c.n_docs);
    for (let d = 0; d < c.n_docs; d++) for (let q = 0; q < nq; q++) if (gray[d * nq + q]) docGray[d] = 1;
    const models: Record<string, ModelData> = {};
    for (const [mk, m] of Object.entries(c.models)) {
      const bytes = b64(m.p), p = new Float64Array(n);
      if (m.enc === "u8") for (let i = 0; i < n; i++) p[i] = bytes[i] === 255 ? NaN : bytes[i] / 200;
      else for (let i = 0; i < n; i++) { const v = bytes[2 * i] | (bytes[2 * i + 1] << 8); p[i] = v === 65535 ? NaN : v / 10000; }
      models[mk] = { key: mk, p, label: unpackBits(m.label, n), nDocs: m.n_docs, nCells: m.n_cells, nErr: m.n_err, nDisagree: m.n_disagree };
    }
    corpora[key] = { key, display: c.display, label: c.label, nDocs: c.n_docs, nPosDocsAny: c.n_pos_docs_any, docs: c.docs, issues: c.issues, gold, gray, docGray, models };
  }
  return { version: raw.version, corpora };
}

// ------------------------------------------------------------------------------------------------

export type Counts = { tp: number; fp: number; fn: number; tn: number };
export type Metrics = Counts & { n: number; flagged: number; nPos: number; recall: number | null; precision: number | null; f1: number | null; elusion: number | null; reviewShare: number | null };

export function metrics(c: Counts): Metrics {
  const n = c.tp + c.fp + c.fn + c.tn, flagged = c.tp + c.fp, nPos = c.tp + c.fn;
  const recall = nPos ? c.tp / nPos : null, precision = flagged ? c.tp / flagged : null;
  const f1 = recall == null || precision == null || recall + precision === 0 ? null : (2 * recall * precision) / (recall + precision);
  return { ...c, n, flagged, nPos, recall, precision, f1, elusion: n - flagged ? c.fn / (n - flagged) : null, reviewShare: n ? flagged / n : null };
}
/** F1 for optimisation: undefined F1 (nothing flagged, or no positives) scores 0. */
const f1Of = (tp: number, fp: number, fn: number) => (2 * tp + fp + fn === 0 ? 0 : (2 * tp) / (2 * tp + fp + fn));

/**
 * One issue's decisions sorted by p descending, with running counts, so "flagged at cutoff c" is a binary search and every metric at any
 * cutoff is O(log n). Built over an optional document mask (the split-half check). `ng` arrays are the same counts over the non-gray decisions.
 */
export type IssueStats = { p: Float64Array; cumTP: Int32Array; cumNG: Int32Array; cumTPNG: Int32Array; n: number; nPos: number; nNG: number; nPosNG: number };

export function buildIssueStats(c: CorpusData, m: ModelData, q: number, mask?: Uint8Array | null): IssueStats {
  const nq = c.issues.length;
  const idx: number[] = [];
  for (let d = 0; d < c.nDocs; d++) {
    if (mask && !mask[d]) continue;
    const i = d * nq + q;
    if (!Number.isNaN(m.p[i])) idx.push(i);
  }
  idx.sort((a, b) => m.p[b] - m.p[a]);
  const n = idx.length, p = new Float64Array(n), cumTP = new Int32Array(n + 1), cumNG = new Int32Array(n + 1), cumTPNG = new Int32Array(n + 1);
  for (let k = 0; k < n; k++) {
    const i = idx[k], g = c.gold[i], ng = c.gray[i] ? 0 : 1;
    p[k] = m.p[i];
    cumTP[k + 1] = cumTP[k] + g; cumNG[k + 1] = cumNG[k] + ng; cumTPNG[k + 1] = cumTPNG[k] + (g & ng);
  }
  return { p, cumTP, cumNG, cumTPNG, n, nPos: cumTP[n], nNG: cumNG[n], nPosNG: cumTPNG[n] };
}

/** Number of decisions with p ≥ cutoff (the first index whose p is below it). */
export function flaggedAt(s: IssueStats, cutoff: number): number {
  let lo = 0, hi = s.n;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (s.p[mid] >= cutoff) lo = mid + 1; else hi = mid; }
  return lo;
}

export function issueCounts(s: IssueStats, cutoff: number, gray: Gray): Counts {
  const k = flaggedAt(s, cutoff);
  if (gray === "all") { const tp = s.cumTP[k]; return { tp, fp: k - tp, fn: s.nPos - tp, tn: s.n - k - (s.nPos - tp) }; }
  const flagged = s.cumNG[k], tp = s.cumTPNG[k];
  return { tp, fp: flagged - tp, fn: s.nPosNG - tp, tn: s.nNG - flagged - (s.nPosNG - tp) };
}
export const issueMetrics = (s: IssueStats, cutoff: number, gray: Gray) => metrics(issueCounts(s, cutoff, gray));

/** The issue's counts under the published labels (the benchmark default), over the same cells. */
export function issueCountsLabel(c: CorpusData, m: ModelData, q: number, gray: Gray, mask?: Uint8Array | null): Counts {
  const nq = c.issues.length, out = { tp: 0, fp: 0, fn: 0, tn: 0 };
  for (let d = 0; d < c.nDocs; d++) {
    if (mask && !mask[d]) continue;
    const i = d * nq + q;
    if (Number.isNaN(m.p[i]) || (gray === "nogray" && c.gray[i])) continue;
    tally(out, m.label[i] === 1, c.gold[i] === 1);
  }
  return out;
}

function tally(o: Counts, pred: boolean, gold: boolean) {
  if (pred) { if (gold) o.tp++; else o.fp++; } else if (gold) o.fn++; else o.tn++;
}

/** Pooled counts over every decision (the sum of the per-issue confusions). */
export function decisionCounts(stats: IssueStats[], cutoffs: number[], gray: Gray): Counts {
  const out = { tp: 0, fp: 0, fn: 0, tn: 0 };
  stats.forEach((s, q) => { const c = issueCounts(s, cutoffs[q], gray); out.tp += c.tp; out.fp += c.fp; out.fn += c.fn; out.tn += c.tn; });
  return out;
}

/**
 * Document-level counts: a document is predicted responsive when any of its issues is flagged, gold-responsive when any of its (present) issues
 * is gold-positive. `useLabel` scores the published labels instead of the cutoffs. Under `nogray` documents with any debatable label are skipped.
 */
export function docCounts(c: CorpusData, m: ModelData, cutoffs: number[], gray: Gray, mask?: Uint8Array | null, useLabel = false): Counts {
  const nq = c.issues.length, out = { tp: 0, fp: 0, fn: 0, tn: 0 };
  for (let d = 0; d < c.nDocs; d++) {
    if (mask && !mask[d]) continue;
    if (gray === "nogray" && c.docGray[d]) continue;
    let pred = false, gold = false, any = false;
    const base = d * nq;
    for (let q = 0; q < nq; q++) {
      const i = base + q, p = m.p[i];
      if (Number.isNaN(p)) continue;
      any = true;
      if (c.gold[i]) gold = true;
      if (useLabel ? m.label[i] === 1 : p >= cutoffs[q]) pred = true;
    }
    if (any) tally(out, pred, gold);
  }
  return out;
}

export function pooledCounts(level: Level, c: CorpusData, m: ModelData, stats: IssueStats[], cutoffs: number[], gray: Gray, mask?: Uint8Array | null): Counts {
  return level === "doc" ? docCounts(c, m, cutoffs, gray, mask) : decisionCounts(stats, cutoffs, gray);
}
/** The benchmark default at the pooled level: the published labels. */
export function pooledCountsLabel(level: Level, c: CorpusData, m: ModelData, gray: Gray, mask?: Uint8Array | null): Counts {
  if (level === "doc") return docCounts(c, m, [], gray, mask, true);
  const out = { tp: 0, fp: 0, fn: 0, tn: 0 };
  for (let q = 0; q < c.issues.length; q++) { const x = issueCountsLabel(c, m, q, gray, mask); out.tp += x.tp; out.fp += x.fp; out.fn += x.fn; out.tn += x.tn; }
  return out;
}

/** The pooled precision–recall curve traced by one shared cutoff over the grid; index i is cutoff i/200. */
export function sweepCurve(level: Level, c: CorpusData, m: ModelData, stats: IssueStats[], gray: Gray): Metrics[] {
  const out: Metrics[] = [];
  const cutoffs = new Array<number>(c.issues.length);
  for (let i = 0; i <= GRID_N; i++) {
    cutoffs.fill(gridValue(i));
    out.push(metrics(pooledCounts(level, c, m, stats, cutoffs, gray)));
  }
  return out;
}

/** One issue's precision–recall curve over the grid (for the row sparkline). */
export function issueCurve(s: IssueStats, gray: Gray): Metrics[] {
  const out: Metrics[] = [];
  for (let i = 0; i <= GRID_N; i++) out.push(issueMetrics(s, gridValue(i), gray));
  return out;
}

/** Score histogram for one issue: 20 bins of 0.05, gold-negative and gold-positive counts; p = 1 falls in the last bin. */
export function issueHistogram(c: CorpusData, m: ModelData, q: number, gray: Gray, bins = 20): { neg: number[]; pos: number[] } {
  const nq = c.issues.length, neg = new Array(bins).fill(0), pos = new Array(bins).fill(0);
  for (let d = 0; d < c.nDocs; d++) {
    const i = d * nq + q, p = m.p[i];
    if (Number.isNaN(p) || (gray === "nogray" && c.gray[i])) continue;
    const b = Math.min(bins - 1, Math.floor(p * bins + 1e-9));
    if (c.gold[i]) pos[b]++; else neg[b]++;
  }
  return { neg, pos };
}

// ------------------------------------------------------------------------------------------------
// Choosing cutoffs. Every optimiser works on grid indices and breaks ties toward 0.5 (index 100): F1 is a step function of the cutoff, so a
// whole run of grid points usually shares the maximum, and the one nearest the benchmark default is the least surprising to report.

const closerToDefault = (i: number, best: number) => Math.abs(i - DEFAULT_CUTOFF_IDX) < Math.abs(best - DEFAULT_CUTOFF_IDX);

/** Per issue, the grid cutoff with the highest F1 for that issue alone. */
export function optimizePerIssueF1(stats: IssueStats[], gray: Gray): number[] {
  return stats.map((s) => {
    let best = DEFAULT_CUTOFF_IDX, bestF = -1;
    for (let i = 0; i <= GRID_N; i++) {
      const c = issueCounts(s, gridValue(i), gray), f = f1Of(c.tp, c.fp, c.fn);
      if (f > bestF + 1e-12 || (Math.abs(f - bestF) <= 1e-12 && closerToDefault(i, best))) { bestF = f; best = i; }
    }
    return best;
  });
}

/**
 * Coordinate ascent on the pooled F1: one issue at a time, every other cutoff fixed, the issue's whole grid is scanned exactly (at document
 * level the documents another issue already flags are constant, the rest flip one by one as the cutoff descends), for up to `passes` passes
 * or until a pass changes nothing.
 */
export function optimizePooledF1(level: Level, c: CorpusData, m: ModelData, stats: IssueStats[], gray: Gray, start: number[], passes = 4): number[] {
  const nq = c.issues.length, cur = start.slice();
  for (let pass = 0; pass < passes; pass++) {
    let changed = false;
    for (let q = 0; q < nq; q++) {
      let best = cur[q], bestF = -1;
      const consider = (i: number, f: number) => { if (f > bestF + 1e-12 || (Math.abs(f - bestF) <= 1e-12 && closerToDefault(i, best))) { bestF = f; best = i; } };
      if (level === "decision") {
        let tpO = 0, fpO = 0, fnO = 0;
        stats.forEach((s, j) => { if (j !== q) { const x = issueCounts(s, gridValue(cur[j]), gray); tpO += x.tp; fpO += x.fp; fnO += x.fn; } });
        for (let i = 0; i <= GRID_N; i++) { const x = issueCounts(stats[q], gridValue(i), gray); consider(i, f1Of(tpO + x.tp, fpO + x.fp, fnO + x.fn)); }
      } else {
        // documents flagged by another issue (or with no decision on this one) are fixed; the rest are candidates sorted by this issue's p
        let tp0 = 0, fp0 = 0, fn0 = 0;
        const cand: { p: number; g: number }[] = [];
        for (let d = 0; d < c.nDocs; d++) {
          if (gray === "nogray" && c.docGray[d]) continue;
          const base = d * nq;
          let other = false, gold = false, any = false;
          for (let j = 0; j < nq; j++) {
            const i = base + j, p = m.p[i];
            if (Number.isNaN(p)) continue;
            any = true;
            if (c.gold[i]) gold = true;
            if (j !== q && p >= gridValue(cur[j])) other = true;
          }
          if (!any) continue;
          const pq = m.p[base + q];
          if (other) { if (gold) tp0++; else fp0++; }
          else if (Number.isNaN(pq)) { if (gold) fn0++; }
          else cand.push({ p: pq, g: gold ? 1 : 0 });
        }
        cand.sort((a, b) => b.p - a.p);
        const cumG = new Int32Array(cand.length + 1);
        for (let k = 0; k < cand.length; k++) cumG[k + 1] = cumG[k] + cand[k].g;
        const candPos = cumG[cand.length];
        let k = 0;
        for (let i = GRID_N; i >= 0; i--) {
          const cut = gridValue(i);
          while (k < cand.length && cand[k].p >= cut) k++;
          const tpC = cumG[k], fpC = k - tpC, fnC = candPos - tpC;
          consider(i, f1Of(tp0 + tpC, fp0 + fpC, fn0 + fnC));
        }
      }
      if (best !== cur[q]) { cur[q] = best; changed = true; }
    }
    if (!changed) break;
  }
  return cur;
}

/** Per issue, the highest grid cutoff whose recall still reaches `target`; `reached` is false when only cutoff 0 (review everything) does, or the issue has no positives. */
export function targetRecall(stats: IssueStats[], gray: Gray, target: number): { idx: number; reached: boolean }[] {
  return stats.map((s) => {
    const nPos = gray === "all" ? s.nPos : s.nPosNG;
    if (!nPos) return { idx: DEFAULT_CUTOFF_IDX, reached: false };
    for (let i = GRID_N; i >= 0; i--) {
      const x = issueCounts(s, gridValue(i), gray);
      if (x.tp / nPos >= target - 1e-12) return { idx: i, reached: i > 0 };
    }
    return { idx: 0, reached: false };
  });
}

// ------------------------------------------------------------------------------------------------
// Split-half check: tune on a random half of the documents, score the other half.

/** mulberry32: a small seeded generator, so a split can be re-rolled and quoted. */
export function rng(seed: number): () => number {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** A random half of the documents the model scored (train mask) and the rest (test mask). */
export function splitHalf(c: CorpusData, m: ModelData, seed: number): { train: Uint8Array; test: Uint8Array } {
  const nq = c.issues.length, ids: number[] = [];
  for (let d = 0; d < c.nDocs; d++) for (let q = 0; q < nq; q++) if (!Number.isNaN(m.p[d * nq + q])) { ids.push(d); break; }
  const r = rng(seed);
  for (let i = ids.length - 1; i > 0; i--) { const j = Math.floor(r() * (i + 1)); [ids[i], ids[j]] = [ids[j], ids[i]]; }
  const train = new Uint8Array(c.nDocs), test = new Uint8Array(c.nDocs);
  ids.forEach((d, k) => { if (k < ids.length / 2) train[d] = 1; else test[d] = 1; });
  return { train, test };
}

export type SplitResult = {
  seed: number; nTrain: number; nTest: number; cutoffs: number[];
  train: { base: Metrics; tuned: Metrics }; test: { base: Metrics; tuned: Metrics };
};

/** Tune cutoffs (per-issue F1 or pooled F1) on the train half; report pooled metrics at the tuned cutoffs and at the benchmark default on both halves. */
export function splitHalfCheck(level: Level, c: CorpusData, m: ModelData, gray: Gray, seed: number, how: "issue" | "pooled"): SplitResult {
  const { train, test } = splitHalf(c, m, seed);
  const trainStats = c.issues.map((_, q) => buildIssueStats(c, m, q, train));
  const testStats = c.issues.map((_, q) => buildIssueStats(c, m, q, test));
  const start = new Array(c.issues.length).fill(DEFAULT_CUTOFF_IDX) as number[];
  const idx = how === "issue" ? optimizePerIssueF1(trainStats, gray) : optimizePooledF1(level, c, maskModel(c, m, train), trainStats, gray, start);
  const cutoffs = idx.map(gridValue);
  const at = (stats: IssueStats[], mask: Uint8Array) => ({
    base: metrics(pooledCountsLabel(level, c, m, gray, mask)),
    tuned: metrics(pooledCounts(level, c, m, stats, cutoffs, gray, mask)),
  });
  let nTrain = 0, nTest = 0;
  for (let d = 0; d < c.nDocs; d++) { nTrain += train[d]; nTest += test[d]; }
  return { seed, nTrain, nTest, cutoffs: idx, train: at(trainStats, train), test: at(testStats, test) };
}

/** A copy of the model with every decision outside `mask` removed, so the pooled optimiser (which has no mask parameter) sees only the train half. */
function maskModel(c: CorpusData, m: ModelData, mask: Uint8Array): ModelData {
  const nq = c.issues.length, p = new Float64Array(m.p);
  for (let d = 0; d < c.nDocs; d++) if (!mask[d]) for (let q = 0; q < nq; q++) p[d * nq + q] = NaN;
  return { ...m, p };
}

/** Mean F1 gain on the held-out half over `k` seeds (a steadier figure than one roll). */
export function splitHalfRepeat(level: Level, c: CorpusData, m: ModelData, gray: Gray, how: "issue" | "pooled", k: number, seed0: number): { meanTestGain: number; meanTrainGain: number; positiveShare: number } {
  let st = 0, str = 0, pos = 0;
  for (let i = 0; i < k; i++) {
    const r = splitHalfCheck(level, c, m, gray, seed0 + i * 7919, how);
    const gt = (r.test.tuned.f1 ?? 0) - (r.test.base.f1 ?? 0), gtr = (r.train.tuned.f1 ?? 0) - (r.train.base.f1 ?? 0);
    st += gt; str += gtr; if (gt > 0) pos++;
  }
  return { meanTestGain: st / k, meanTrainGain: str / k, positiveShare: pos / k };
}
