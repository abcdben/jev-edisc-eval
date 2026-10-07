import { useCallback, useEffect, useState } from "react";
import { CORPORA, displayMeta, fmtInt, pick, type Rec } from "./data";
import type { View } from "./App";
import type { PRItem } from "./components/PRScatter";
import { armLabels, type TarReviewerArm } from "./components/TarReviewer";
import { RAIL_SORT_DEFAULT, type RailMetric, type SortDir } from "./components/PRRail";
import { REALISTIC_REVIEWER, applyReviewer, asReviewer, fmtRate, fmtRates, gridFor, isPublished, isTarModel, publishedRates, publishedText, type Applied, type Reviewer, type ReviewerSetting } from "./tarGrid";
import { movedName } from "./tarNames";
import { DEFAULT_THRESHOLD, asThreshold, f1Of, fmtThreshold, isDefaultThreshold, recut } from "./sweep";

/**
 * The statistical inputs behind the recall/precision figures, shared by the public site's Compare models section (App.tsx, AppB.tsx; the Statistics row,
 * components/CompareStats.tsx) and the Studio's Statistics section (StudioPage.tsx): the model threshold (sweep.ts), the TAR reviewer's error rates
 * (tarGrid.ts) and the ranked view's order (components/PRRail.tsx). `applyStats` turns the published selection into the items the charts draw under
 * a setting; at the default threshold and the `published` reviewer it returns the published figures exactly (each item gaining only its F1, findings'
 * own point, for the ranked view's third column). The reviewer starts at REALISTIC_REVIEWER (10% / 2% on every TAR arm), so a TAR row whose published
 * run assumed other rates differs from findings.json from the start and carries a ‡. The notes name what moved, for the captions under the charts.
 */

export type Sort = { by: RailMetric; dir: SortDir };
export type Stats = { threshold: number; sort: Sort; tarReviewer: ReviewerSetting };
export const STATS_DEFAULT: Stats = { threshold: DEFAULT_THRESHOLD, sort: RAIL_SORT_DEFAULT, tarReviewer: REALISTIC_REVIEWER };

/** A header click: rank by that metric best first; a second click on the one in force flips it. */
export const nextSort = (p: Sort, by: RailMetric): Sort => (p.by === by ? { by, dir: p.dir === "desc" ? "asc" : "desc" } : { by, dir: "desc" });
export const isDefaultSort = (s: Sort) => s.by === RAIL_SORT_DEFAULT.by && s.dir === RAIL_SORT_DEFAULT.dir;
/** The sort as the captions say it: "F1, best first". */
export const sortText = (s: Sort) => `${s.by === "f1" ? "F1" : s.by}, ${s.dir === "desc" ? "best first" : "worst first"}`;

export type StatsApplied = {
  /** The selected records, the TAR ones with a grid re-pointed at the reviewer's cell (tarGrid.ts applyReviewer); the published ones at the default. */
  sel: Rec[];
  /** The items the charts draw: every one with its F1; re-cut at the threshold, or re-pointed by the reviewer, where that applies. */
  items: PRItem[];
  /** Off the default threshold: the items re-cut (models with a probability) and the ones that could not be (classical TAR, † in the name). */
  movedIds: string[]; fixedIds: string[];
  applied: Applied;
  /** The selected TAR arms as the reviewer control wants them: each with its grid on this corpus, or null. */
  revArms: TarReviewerArm[];
  /** Whether the threshold is off the default (0.50, the published cut). */
  thrOn: boolean;
  /** The rates every gridded TAR row was re-pointed at, when the reviewer setting moved any; null at the published figures. */
  revSnapped: Reviewer | null;
  /** Whether any TAR row's figures differ from findings.json under the reviewer setting (tarGrid.ts Applied.offPublished; ‡ in the name). */
  revOff: boolean;
  /** Why a TAR arm without a grid is fixed, naming the corpus: "adjustable runs not yet computed for TREC 2016". */
  fixedHint: string;
};

/**
 * The published selection (`selPublished`, `ownItems`: App.tsx useCompareItems) under a threshold and a reviewer setting on a view. The reviewer runs
 * first: each selected TAR record whose corpus and variant have a grid is re-pointed at the cell nearest the rates (recall/precision/F1, per-issue
 * intervals, review effort, cost and hours), the rest stay published; a row re-pointed off its published rates carries a ‡ in its name. Then, off the
 * default threshold, every model with a sweep curve is re-cut at p(responsive) ≥ threshold under the same view; the rows without one (classical TAR:
 * a reviewer's coding and a cutoff chosen on a sample, not a probability) keep their point and carry a † in their name, unless the reviewer grid is
 * moving them. At the default threshold and the `published` reviewer every number is findings.json's own.
 */
export function applyStats(ownItems: PRItem[], selPublished: Rec[], v: View, threshold: number, tarReviewer: ReviewerSetting): StatsApplied {
  const applied = applyReviewer(selPublished, tarReviewer);
  const sel = applied.recs;
  const revArms: TarReviewerArm[] = selPublished.filter((r) => isTarModel(r.model)).map((r) => ({ model: r.model, name: displayMeta(r.model, r).short, grid: gridFor(r.corpus, r.model) ?? null, published: publishedRates(r) }));
  const revSnapped = !isPublished(tarReviewer) && applied.moved.size > 0 ? [...applied.moved.values()][0] : null;
  const fixedHint = `adjustable runs not yet computed for ${CORPORA.find((c) => c.id === v.corpus)?.label ?? v.corpus}`;
  const thrOn = !isDefaultThreshold(threshold);
  const recOf = (id: string) => sel.find((x) => x.model === id);
  const fixedIds: string[] = [], movedIds: string[] = [];
  const items = ownItems.map((it): PRItem => {
    const r = recOf(it.id);
    const rev = r ? applied.moved.get(it.id) : undefined;
    let out: PRItem = { ...it, f1: r ? f1Of(r, v) : null };
    if (r && rev) {
      // the grid cell's point under the view, with the effort behind it; off the published rates the row is named by the applied rates with a ‡ (tarNames.ts movedName)
      const p = pick(r, v.level, v.gray, v.issue);
      const off = applied.offPublished.includes(it.id);
      const pub = revArms.find((x) => x.model === it.id), pubRates = pub?.grid?.default ?? pub?.published;
      const sub = off
        ? `re-run at a ${fmtRate(rev.fn)} miss rate, ${fmtRate(rev.fp)} over-code rate${pubRates ? ` (published assumed ${publishedText(pubRates)})` : ""}`
        : `reviewer misses ${fmtRate(rev.fn)}, over-codes ${fmtRate(rev.fp)} (published)`;
      out = { ...out, name: off ? movedName(r, rev) : out.name, recall: p.recall, precision: p.precision, sub: `${sub}${r.tar ? ` · ${fmtInt(r.tar.docs_reviewed)} documents reviewed` : ""}` };
    }
    if (!thrOn) return out;
    const c = r ? recut(r, v, threshold) : null;
    if (!c) { if (!rev) { fixedIds.push(it.id); out = { ...out, name: `${out.name} †` }; } return out; }
    movedIds.push(it.id);
    return { ...out, recall: c.recall, precision: c.precision, f1: c.f1ci, sub: r?.subset ? `scored on ${r.subset}` : `${fmtInt(c.n)} ${v.issue ? "decisions" : "documents"} scored at p ≥ ${fmtThreshold(threshold)}` };
  });
  return { sel, items, movedIds, fixedIds, applied, revArms, thrOn, revSnapped, revOff: applied.offPublished.length > 0, fixedHint };
}

/** The caption lines for the threshold, when it is off the default: what was re-cut and at what, and the † on the rows that could not be. */
export function thresholdNotes(a: StatsApplied, threshold: number): string[] {
  if (!a.thrOn) return [];
  return [
    `Model threshold ${fmtThreshold(threshold)}: each model with a probability re-cut at p(responsive) ≥ ${fmtThreshold(threshold)}; the published figures are each model's own label (${fmtThreshold(DEFAULT_THRESHOLD)}).`,
    ...(a.fixedIds.length ? ["† fixed: a decision without a probability to re-cut (classical TAR), at its published point."] : []),
  ];
}
/**
 * The caption lines for the TAR reviewer, when its setting moves a figure off findings.json: the rates every gridded TAR row was re-run at and the ‡
 * rows with what their published runs assumed, then the rows no grid could move. At `published`, or at rates that equal every arm's own, nothing.
 */
export function reviewerNotes(a: StatsApplied, tarReviewer: ReviewerSetting): string[] {
  if (isPublished(tarReviewer)) return [];
  const labels = armLabels(a.revArms), labelOf = (m: string) => labels[a.revArms.findIndex((x) => x.model === m)] ?? m;
  const off = a.revArms.filter((x) => a.applied.offPublished.includes(x.model));
  const pubOf = (x: TarReviewerArm) => (x.grid?.default ?? x.published);
  return [
    ...(a.revSnapped && off.length ? [
      `TAR reviewer: misses ${fmtRate(a.revSnapped.fn)} of relevant, over-codes ${fmtRate(a.revSnapped.fp)} of non-relevant documents; the simulation re-run from the precomputed grid (classifier retrained, stop rule re-applied).`,
      `‡ differs from the published figure: ${off.map((x) => `${labelOf(x.model)} assumed ${publishedText(pubOf(x)!)}`).join(", ")}.`,
    ] : []),
    ...(a.applied.fixed.length ? [`${a.applied.fixed.map((m) => { const x = a.revArms.find((y) => y.model === m); const p = x && pubOf(x); return `${labelOf(m)} fixed at published${p ? ` ${fmtRates(p)}` : ""}`; }).join(", ")} — ${a.fixedHint}.`] : []),
  ];
}
/** The threshold's one-line hint beside its slider: the published figures at the default, else how many rows were re-cut and how many are fixed. */
export const thresholdHint = (a: StatsApplied, threshold: number) =>
  !a.thrOn ? `${fmtThreshold(DEFAULT_THRESHOLD)} = published figures (each model's own label)` : `${a.movedIds.length} re-cut at p ≥ ${fmtThreshold(threshold)}${a.fixedIds.length ? ` · ${a.fixedIds.length} fixed †` : ""}`;

// ---- the public site's remembered setting (the Studio keeps its own under studio-* keys: studioState.ts) ----

/** The site's localStorage key for the Compare models Statistics row (one JSON object; the Studio's fields live under their own `studio-*` keys). */
export const SITE_STATS_KEY = "site-compare-stats-v1";
const SORTS: RailMetric[] = ["recall", "precision", "f1"], DIRS: SortDir[] = ["desc", "asc"];
/** A stored object as a setting: each field coerced on its own, the rest at their defaults. */
export function asStats(raw: unknown): Stats {
  if (!raw || typeof raw !== "object") return STATS_DEFAULT;
  const o = raw as Record<string, unknown>;
  const threshold = asThreshold(o.threshold) ?? STATS_DEFAULT.threshold;
  const s = o.sort as Record<string, unknown> | undefined;
  const sort: Sort = s && SORTS.includes(s.by as RailMetric) && DIRS.includes(s.dir as SortDir) ? { by: s.by as RailMetric, dir: s.dir as SortDir } : STATS_DEFAULT.sort;
  return { threshold, sort, tarReviewer: asReviewer(o.tarReviewer) ?? STATS_DEFAULT.tarReviewer };
}
/** The site's Statistics setting, remembered in localStorage (SITE_STATS_KEY); the defaults when storage is empty, denied or unreadable. */
export function useSiteStats(): [Stats, (p: Partial<Stats>) => void] {
  const [stats, setStats] = useState<Stats>(() => { try { const s = localStorage.getItem(SITE_STATS_KEY); return s ? asStats(JSON.parse(s)) : STATS_DEFAULT; } catch { return STATS_DEFAULT; } });
  useEffect(() => { try { localStorage.setItem(SITE_STATS_KEY, JSON.stringify(stats)); } catch { /* storage denied: the setting lasts the session */ } }, [stats]);
  const patch = useCallback((p: Partial<Stats>) => setStats((s) => ({ ...s, ...p })), []);
  return [stats, patch];
}
