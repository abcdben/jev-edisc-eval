/**
 * The pattern behind a chart's plot area, under its gridlines and data: the site's dot matrix on the recall/precision charts, and the studio's
 * Canvas → Background control (StudioPage.tsx), which puts it behind every plot. `dots` is the dot matrix, `grid` a fine hairline grid, `none` nothing.
 * The colour is `--plot-dots` where the panel sets one (the studio derives a faint ink for styles whose preset has no dot colour), else the
 * theme's or preset's `--dots`. `step` is the tile in px at text scale 1 and scales with the chart's text (`s`) so the matrix keeps its density
 * against larger labels. Ids must be unique per chart (pass the component's useId): `url(#id)` resolves document-wide, and the PNG export
 * (exportPng.ts) clones the panel into the same document.
 */
export type PlotBg = "none" | "dots" | "grid";
export const PLOT_BG_FILL = "var(--plot-dots, var(--dots))";

export function PlotBgPattern({ id, kind, s = 1, step = 8, opacity }: { id: string; kind: PlotBg; s?: number; step?: number; opacity?: number }) {
  if (kind === "none") return null;
  const p = step * s;
  return (
    <pattern id={id} width={p} height={p} patternUnits="userSpaceOnUse">
      {kind === "dots" ? (
        <circle cx={1} cy={1} r={0.7 * Math.min(s, 1.3)} fill={PLOT_BG_FILL} fillOpacity={opacity} />
      ) : (
        <path d={`M0 .5H${p}M.5 0V${p}`} stroke={PLOT_BG_FILL} strokeOpacity={opacity} strokeWidth={0.6} fill="none" />
      )}
    </pattern>
  );
}
