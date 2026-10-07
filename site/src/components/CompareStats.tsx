import { Control, Seg } from "./ui";
import { TarReviewerControl } from "./TarReviewer";
import { RAIL_METRIC_LABEL, RAIL_SORT_DEFAULT, type RailMetric } from "./PRRail";
import { isDefaultSort, thresholdHint, type Stats, type StatsApplied } from "../compareStats";
import { DEFAULT_THRESHOLD, THRESHOLD_MAX, THRESHOLD_MIN, THRESHOLD_STEP, fmtThreshold } from "../sweep";

/**
 * The Statistics row of the public site's Compare models section (App.tsx CompareSection, AppB.tsx CompareTabs): the analysis inputs, apart from the
 * formatting controls in the card headers, in the control bar's own idiom (ui.tsx Control, Seg). The model threshold slider (sweep.ts; shown where the
 * recall/precision chart is), the TAR reviewer's miss and over-code sliders (TarReviewer.tsx; while a TAR workflow is selected, on the charts the grid
 * reaches) and, in the ranked view, the sort, which the column headers also drive. The setting lives in the page shell (compareStats.ts useSiteStats)
 * so the TAR workflow picker can read it; `applied` is what applyStats made of it, for the hints.
 */
export function StatsRow({ stats, set, applied, threshold = true, reviewer = true, ranked = false }: {
  stats: Stats; set: (p: Partial<Stats>) => void; applied: StatsApplied;
  /** Whether the threshold slider applies to the chart shown (the recall/precision chart only). */
  threshold?: boolean;
  /** Whether the reviewer control applies to the chart shown (recall/precision, cost, speed). */
  reviewer?: boolean;
  /** Whether the ranked view is showing (its sort control). */
  ranked?: boolean;
}) {
  const { revArms } = applied;
  const thrOn = applied.thrOn;
  return (
    <div className="stats-row" role="group" aria-label="Statistics">
      <span className="stats-row-lab">Statistics</span>
      {threshold && (
        <Control label="Threshold">
          <label className="studio-slider" title={`Re-cut every model with a probability at p(responsive) ≥ this, live, from its saved per-document probabilities (results/sweep.json). At ${fmtThreshold(DEFAULT_THRESHOLD)} the chart shows each model at its own label. Classical TAR rows are hard decisions and keep their point (†); the TAR reviewer sliders move them instead.`}>
            <span>p ≥</span>
            <input type="range" min={THRESHOLD_MIN} max={THRESHOLD_MAX} step={THRESHOLD_STEP} value={stats.threshold} onChange={(e) => set({ threshold: Number(e.target.value) })} aria-label="model threshold" />
            <span className="val">{fmtThreshold(stats.threshold)}</span>
          </label>
          {thrOn && <button type="button" className="studio-btn small" onClick={() => set({ threshold: DEFAULT_THRESHOLD })} title={`Back to ${fmtThreshold(DEFAULT_THRESHOLD)}, the published operating point`}>reset</button>}
          <span className="studio-hint small">{thresholdHint(applied, stats.threshold)}</span>
        </Control>
      )}
      {reviewer && revArms.length > 0 && (
        <Control label="TAR reviewer" className="tar-rev-ctl">
          <TarReviewerControl value={stats.tarReviewer} onChange={(r) => set({ tarReviewer: r })} arms={revArms} fixedHint={applied.fixedHint} />
        </Control>
      )}
      {ranked && (
        <Control label="Sort">
          <Seg<RailMetric> value={stats.sort.by} onChange={(by) => set({ sort: { ...stats.sort, by } })} options={(["recall", "precision", "f1"] as RailMetric[]).map((m) => ({ id: m, label: m === "f1" ? "F1" : RAIL_METRIC_LABEL[m].toLowerCase() }))} />
          <Seg value={stats.sort.dir} onChange={(dir) => set({ sort: { ...stats.sort, dir } })} options={[{ id: "desc", label: "best first" }, { id: "asc", label: "worst first" }]} />
          {!isDefaultSort(stats.sort) && <button type="button" className="studio-btn small" onClick={() => set({ sort: RAIL_SORT_DEFAULT })} title="Back to recall, best first">reset</button>}
          <span className="studio-hint small">or click a column header</span>
        </Control>
      )}
      {!threshold && !(reviewer && revArms.length > 0) && !ranked && <span className="studio-hint small">No statistical inputs reach this chart; the figures are the published ones.</span>}
    </div>
  );
}
