import { useId } from "react";
import { PUBLISHED, REALISTIC_REVIEWER, availableFp, fmtRate, fmtRates, isPublished, publishedText, sameReviewer, sameSetting, type RateGrid, type Reviewer, type ReviewerSetting } from "../tarGrid";

/**
 * The TAR reviewer error-rate control (tarGrid.ts): two sliders over the grid's miss rates (fn, relevant documents the reviewer codes not
 * relevant) and over-code rates (fp, non-relevant documents coded relevant), stepping through the exported grid points, a tick at each selected
 * TAR arm's published rates, a Default button to REALISTIC_REVIEWER (10% / 2%, the same on every arm) and a Published button to each arm's own
 * published rates (`value` "published", findings.json's figures). Shared by the Compare Statistics row, the Studio, the Study page and the
 * Population explorer; each decides where it sits and what it drives. Under the sliders, one line on what a setting does and one on where each
 * arm stands: its rates and whether they equal the published ones, or that it is fixed at them because no grid exists for this corpus yet.
 */
export type TarReviewerArm = {
  model: string; name: string;
  /** The arm's grid on the current corpus (fn/fp arrays and its published default), or null where none has been computed. */
  grid: RateGrid | null;
  /** The rates the arm's published run assumed, where known without a grid (data.ts Rec.tar); a grid's default takes precedence. */
  published?: Reviewer;
};

/** The default first hint line, for the pages the grid drives (the explorer re-codes per document and says so instead). */
export const GRID_HINT = "Reviewer error re-runs the TAR simulation (classifier retrained, stop rule re-applied) from a precomputed grid.";
/** The default reason an arm without a grid is fixed; the pages that know the corpus name it. */
export const FIXED_HINT = "adjustable runs not yet computed for this corpus";

/** The arms' names as the status line prints them: the part before the first " · " where that still tells them apart, else the whole name. */
export function armLabels(arms: { name: string }[]): string[] {
  const heads = arms.map((a) => a.name.split(" · ")[0]);
  return new Set(heads).size === arms.length ? heads : arms.map((a) => a.name);
}
/** An arm's published rates: its grid's default, else what the page knew. */
const publishedOf = (a: TarReviewerArm): Reviewer | undefined => a.grid?.default ?? a.published;

/** One arm's status under a setting: "TAR 1.0: 10% / 2% (published assumed a perfect reviewer)", "TAR 2.0: 10% / 2% (= published)", "TAR 1.0: as published (a perfect reviewer)", "TAR 2.0: fixed at published 10% / 2% — …". */
export function armStatus(a: TarReviewerArm, label: string, value: ReviewerSetting, fixedHint: string): string {
  const pub = publishedOf(a);
  if (!a.grid) return `${label}: fixed at published${pub ? ` ${fmtRates(pub)}` : ""} — ${fixedHint}`;
  if (isPublished(value)) return `${label}: as published (${publishedText(a.grid.default)})`;
  const same = sameReviewer(value, a.grid.default);
  return `${label}: ${fmtRates(value)} (${same ? "= published" : `published assumed ${publishedText(a.grid.default)}`})`;
}
/** The status line: every arm's status, joined. The rates are the ones the sliders snapped to (the caller passes the snapped setting where it has it). */
export const statusLine = (arms: TarReviewerArm[], value: ReviewerSetting, fixedHint: string): string => {
  const labels = armLabels(arms);
  return arms.map((a, i) => armStatus(a, labels[i], value, fixedHint)).join(" · ");
};

export function TarReviewerControl({ value, onChange, arms, note, movedHint = GRID_HINT, fixedHint = FIXED_HINT, stacked = false }: {
  value: ReviewerSetting; onChange: (r: ReviewerSetting) => void;
  /** The selected TAR arms, each with its grid on the current corpus or null. */
  arms: TarReviewerArm[];
  /** A page's own line under the status (the Study page: which measures follow the grid). */
  note?: string;
  /** The first hint line: what a setting does. The grid pages' default, or the explorer's per-document re-coding. */
  movedHint?: string;
  /** Why an arm without a grid is fixed, after its published rates ("adjustable runs not yet computed for TREC 2016"). */
  fixedHint?: string;
  /** Rows one under another (the rails) rather than one inline row (the Studio's control bar, the Compare Statistics row). */
  stacked?: boolean;
}) {
  const id = useId();
  const withGrid = arms.filter((a): a is TarReviewerArm & { grid: RateGrid } => !!a.grid);
  if (!arms.length) return null;
  if (!withGrid.length) return <span className="tar-rev-fixed">{statusLine(arms, PUBLISHED, fixedHint)}</span>;
  const g = withGrid[0].grid;
  // at `published` the sliders rest at the first gridded arm's own rates (each arm then shows its published figures; the status line says so)
  const shown: Reviewer = isPublished(value) ? g.default : value;
  const idx = (xs: number[], x: number) => xs.reduce((best, v, i) => (Math.abs(v - x) < Math.abs(xs[best] - x) ? i : best), 0);
  // over-code rates no gridded arm ran (Grid.unavailable: TREC CAL from 5%) stay as ticks, so the slider lines up with the other corpora, but
  // the thumb snaps to the highest rate every arm has a cell for
  const capped = withGrid.filter((a) => a.grid.unavailable);
  const fpAvail = capped.length ? Math.min(...capped.map((a) => availableFp(a.grid).length)) : g.fp.length;
  const fpMaxI = Math.max(0, Math.min(fpAvail, g.fp.length) - 1);
  const fnI = idx(g.fn, shown.fn), fpI = Math.min(idx(g.fp, shown.fp), fpMaxI);
  const snapped: ReviewerSetting = isPublished(value) ? value : { fn: g.fn[fnI], fp: g.fp[fpI] };
  const setFn = (i: number) => onChange({ fn: g.fn[i], fp: g.fp[fpI] });
  const setFp = (i: number) => onChange({ fn: g.fn[fnI], fp: g.fp[Math.min(i, fpMaxI)] });
  const cappedLabels = armLabels(capped);
  const cappedHint = capped.length
    ? capped.map((a, i) => `${cappedLabels[i]}: over-code ≥ ${fmtRate(a.grid.unavailable!.fp_min)} unavailable (review never stops at those rates; snapped to ${fmtRate(g.fp[fpMaxI])})`).join(" · ")
    : null;
  const marks = (which: "fn" | "fp") => [...new Set(withGrid.map((a) => idx(g[which], a.grid.default[which])))];
  const labels = armLabels(withGrid);
  const publishedTitle = withGrid.map((a, i) => `${labels[i]} ${publishedText(a.grid.default)}`).join(", ");
  const atDefault = sameSetting(value, REALISTIC_REVIEWER);
  const row = (which: "fn" | "fp", label: string, title: string, i: number, set: (i: number) => void) => {
    const unavailable = which === "fp" ? g.fp.map((_, k) => k).filter((k) => k > fpMaxI) : [];
    return (
      <label className={`tar-rev-row${unavailable.length ? " capped" : ""}`} title={unavailable.length ? `${title} Rates from ${fmtRate(g.fp[fpMaxI + 1])} were not run on this corpus: ${capped[0].grid.unavailable!.reason}` : title}>
        <span className="k">{label}</span>
        <input type="range" min={0} max={g[which].length - 1} step={1} value={i} onChange={(e) => set(Number(e.target.value))} list={`${id}-${which}`} aria-label={`TAR reviewer ${which === "fn" ? "miss" : "over-code"} rate`} />
        <datalist id={`${id}-${which}`}>
          {marks(which).map((m) => <option key={m} value={m} label={`published ${fmtRate(g[which][m])}`} />)}
          {unavailable.map((k) => <option key={`u${k}`} value={k} label={`${fmtRate(g.fp[k])} unavailable`} />)}
        </datalist>
        <span className="val">{fmtRate(g[which][i])}</span>
      </label>
    );
  };
  return (
    <span className={`tar-rev${stacked ? " stacked" : ""}`}>
      {row("fn", "misses", "False-negative rate: the share of relevant documents the simulated reviewer codes not relevant (on every issue). The grid re-ran the workflow at each rate: classifier retrained, stop rule re-applied.", fnI, setFn)}
      {row("fp", "over-codes", "False-positive rate: the share of non-relevant documents the simulated reviewer codes relevant (on one issue at random).", fpI, setFp)}
      <span className="tar-rev-btns">
        <button type="button" className="studio-btn small" disabled={atDefault} onClick={() => onChange(REALISTIC_REVIEWER)} title={`A realistic reviewer on every TAR arm: misses ${fmtRate(REALISTIC_REVIEWER.fn)} of relevant documents, over-codes ${fmtRate(REALISTIC_REVIEWER.fp)} of non-relevant ones`}>Default</button>
        <button type="button" className="studio-btn small" disabled={isPublished(value)} onClick={() => onChange(PUBLISHED)} title={`Each TAR arm at the rates its published run assumed (findings.json): ${publishedTitle}`}>Published</button>
      </span>
      <span className="tar-rev-hint">
        <span>{movedHint}</span>
        <span>{statusLine(arms, snapped, fixedHint)}</span>
        {cappedHint && <span title={capped[0].grid.unavailable!.reason}>{cappedHint}</span>}
        {note && <span>{note}</span>}
      </span>
    </span>
  );
}
