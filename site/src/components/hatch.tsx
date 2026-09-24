import { useId } from "react";

/**
 * How a chart's areas are drawn: the recall/precision map's 95% interval boxes (PRScatter.tsx `boxes`) and the Cost, Speed and Stability bars
 * (StudioCharts.tsx StudioBars `bars`); the studio's Fill control, `filled` on the site. The same four modes read the area's own opacity variable
 * (--box-alpha for a box, --bar-alpha for a bar):
 *   filled            a shade at that opacity;
 *   hatched           45° lines in the item's colour at 3 × that opacity, capped at 1, so the one slider carries both looks (a 1 px line every
 *                     6 px covers about a sixth of the area, so the tripled alpha keeps its weight about the same); a bar adds a hairline edge;
 *   outline           the edge alone, in the item's colour, --box-stroke-w px wide (0.75 unset) × --sw-mult;
 *   hatched-outline   the hatch inside that edge.
 * The hatch is one SVG <pattern> per item in the chart's <defs> (HatchDefs): pattern contents take their styles from the pattern's own ancestors,
 * not from the shape that paints with it, so `currentColor` cannot carry the colour and each item needs its own tile. A tile is HATCH_GAP × textScale
 * square with one line down its middle (at the edge it would be half clipped), 1 × textScale × --sw-mult wide, the tile turned 45°. Ids come from
 * useHatchIds: the component's useId and the item id, so two charts on one page never share a pattern and the PNG export (exportPng.ts, which
 * clones the panel's SVG whole) keeps every url(#…) reference resolvable.
 */
export type FillMode = "filled" | "hatched" | "outline" | "hatched-outline";
export const FILL_MODES: { id: FillMode; label: string; title: string }[] = [
  { id: "filled", label: "filled", title: "A shaded box or bar at the fill opacity (the box-fill and bar-fill sliders)" },
  { id: "hatched", label: "hatched", title: "45° hatch lines in the model's colour; their opacity follows the fill slider" },
  { id: "outline", label: "outline", title: "The box's or bar's edge alone, in the model's colour" },
  { id: "hatched-outline", label: "hatched + outline", title: "Hatch lines inside an outlined box or bar" },
];
export const isFillMode = (s: string | null): s is FillMode => FILL_MODES.some((m) => m.id === s);
export const isHatched = (m: FillMode) => m === "hatched" || m === "hatched-outline";
export const isOutlined = (m: FillMode) => m === "outline" || m === "hatched-outline";

export const HATCH_GAP = 6;
/** Hatch-line opacity for an area whose filled opacity is the variable `alphaVar` (`dflt` where the styles set none). */
export const hatchAlpha = (alphaVar: string, dflt: number) => `min(1, calc(var(${alphaVar}, ${dflt}) * 3))`;
// × 1px: a unitless calc() that comes to 0 is computed as `0%` by Chrome and dropped (the width attribute would show through); a length is honoured
/** Outline width in the outline modes: --box-stroke-w px (0.75 unset) × --sw-mult. */
export const OUTLINE_W = "calc(var(--box-stroke-w, 0.75) * var(--sw-mult, 1) * 1px)";

/** A pattern id per item id, unique to the calling component instance and safe inside url(#…). */
export function useHatchIds(): (id: string) => string {
  const uid = useId().replace(/[^A-Za-z0-9_-]/g, "");
  return (id: string) => `hatch-${uid}-${id.replace(/[^A-Za-z0-9_-]/g, "-")}`;
}

/** The hatch tiles for `items`, to go inside the chart's <defs>; `s` is the text scale. Renders nothing when `on` is false. */
export function HatchDefs({ items, s, hatchId, on = true }: { items: { id: string; color: string }[]; s: number; hatchId: (id: string) => string; on?: boolean }) {
  if (!on) return null;
  const gap = HATCH_GAP * s;
  return (
    <>
      {items.map((p) => (
        <pattern key={p.id} id={hatchId(p.id)} width={gap} height={gap} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <line x1={gap / 2} x2={gap / 2} y1={0} y2={gap} stroke={p.color} strokeWidth={s} style={{ strokeWidth: `calc(${s}px * var(--sw-mult, 1))` }} />
        </pattern>
      ))}
    </>
  );
}
