import { useId, useMemo, type ReactNode } from "react";
import { fmtCI, type CI } from "../data";
import { Logo, LogoGlyph, isJev, logoFor, logoShown, logosMode, type LogosMode } from "../logos";
import { CLICK_HINT, TipBox, fadeStyle, selectable, usePresence, usePulseWindow, useSize, useTip, useTween, type TipContent } from "./ui";
import { hoverable } from "./hover";
import { useTextMeasure, type Measure } from "./measure";
import { PlotBgPattern, type PlotBg } from "./plotBg";
import { HatchDefs, OUTLINE_W, hatchAlpha, isHatched, isOutlined, useHatchIds, type FillMode } from "./hatch";
import { gridOn, labelEvery, labelledAt, pctStep, pctTicks, type TickDensity } from "./ticks";

/** `sub` is the one secondary line of the hover tooltip (what the point was scored on); the full figures live in the details modal. `decider` sets the row's name heavier in the tables; on the map it only selects which interval boxes breathe when `pulse` is on (the mark and label are drawn like every other). `emphasis` (Compare models: the decision-model rows, Jev and Laya) tints the row in the ranked table (ui.tsx RowTint); the map ignores it. */
export type PRItem = { id: string; name: string; color: string; recall: CI; precision: CI; dashed?: boolean; subset?: string | null; sub?: string; decider?: boolean; emphasis?: boolean };

/** The compact hover tooltip of a recall/precision mark or row: both intervals and the scoring line. */
export const prTip = (p: PRItem, icon?: ReactNode): TipContent => ({ title: p.name, color: p.color, icon, lines: [["Recall", fmtCI(p.recall)], ["Precision", fmtCI(p.precision)]], sub: p.sub });

const PR = 20, PT = 18;
/** Tick and axis-title font sizes at text scale 1 (the studio's Text control multiplies them). */
const TICK_FS = 10.5, TITLE_FS = 12;

/**
 * Axis margins, derived from what they hold rather than fixed, so the axis title never lands on a tick label at any text scale or face
 * (styles.css --sans; the export PNG, exportPng.ts, uses the same layout). Tick text is estimated at 0.78 em per character, on the wide side for
 * every face the studio offers (Inter's tabular digits and % are the widest, at about 0.76). Left, from the edge: pad, the rotated y title (its
 * baseline at `titleX`, its box one em to the left and a quarter em to the right of that), a gap, the widest tick label, then 8 px to the axis.
 * Bottom, from the axis: 16 s to the tick baseline, its descent, a gap of 8 px, the x title's box, then a pad; the title's baseline sits 10 s
 * above the bottom edge. At scale 1 with two-digit ticks this gives the site's 56 and 48.
 */
export const tickTextW = (labels: string[], s: number) => Math.max(0, ...labels.map((l) => l.length)) * 0.78 * TICK_FS * s;
export function axisMargins(yTickLabels: string[], s: number) {
  const titleX = 2 + TITLE_FS * s;
  const PL = Math.round(titleX + 0.25 * TITLE_FS * s + Math.max(6, 5 * s) + tickTextW(yTickLabels, s) + 8);
  const PB = Math.round(16 * s + 3 * s + 8 + TITLE_FS * s + 9 * s);
  return { PL, PB, titleX };
}

/**
 * Leader line (the studio's Leaders control, `leaders` on PRScatter and StudioScatter) from a label the placement pushed away from its mark back to
 * the mark. Everything is relative to the mark's centre: `l` is the label's box, `r` the mark's radius (dot, or half the vendor glyph), `o` the
 * chart's beside-the-mark offset (the gap its default slot leaves between the centre and the label's near edge; 9 × text scale on PRScatter,
 * about 6 px clear of a 3.2 px dot). The label is *adjacent*, and gets no line, when its nearest point is within `o + 1` of the centre: the
 * default slot on either side and the diagonal slots (whose near corner is closer still). The centred above/below slots (11 s) and the far slots
 * (22 s up or down the side) are displaced. The line runs from the midpoint of the label's edge facing the mark and stops `r + 1` short of the
 * centre so it never enters the mark.
 */
export function leaderFor(l: { x: number; y: number; w: number; h: number }, r: number, o: number): { x1: number; y1: number; x2: number; y2: number } | null {
  let ex: number, ey: number;
  if (l.x > 0) { ex = l.x; ey = l.y + l.h / 2; }
  else if (l.x + l.w < 0) { ex = l.x + l.w; ey = l.y + l.h / 2; }
  else if (l.y > 0) { ex = l.x + l.w / 2; ey = l.y; }
  else if (l.y + l.h < 0) { ex = l.x + l.w / 2; ey = l.y + l.h; }
  else return null; // the mark is inside the label's box
  const nx = Math.min(Math.max(0, l.x), l.x + l.w), ny = Math.min(Math.max(0, l.y), l.y + l.h); // nearest point of the box to the centre
  if (Math.hypot(nx, ny) <= o + 1) return null;
  const d = Math.hypot(ex, ey);
  if (d <= r + 1) return null;
  const k = (r + 1) / d;
  return { x1: ex, y1: ey, x2: ex * k, y2: ey * k };
}
/** The leader's stroke: a 0.75 px hairline that the high-contrast block multiplies (--sw-mult); its opacity is the `stroke-opacity` attribute, so CSS (`.pr-leader`) can raise it. */
export const LEADER_STYLE = { strokeWidth: "calc(0.75 * var(--sw-mult, 1))" } as const;

/**
 * Point marks (the studio's Marks control; `dot` on the site). Every chart that draws a point at a value uses `Mark`, so a chosen shape
 * is the same on the map, the cost scatter, the dot plots and the ranked rail. Sizes are relative to the chart's dot radius `r`:
 *   dot      filled circle, radius r (+ the high-contrast --r-add);
 *   plus, x  two thin strokes crossing at the centre, arm 1.6 r, 1.25 px × --sw-mult, round caps (x is the plus turned 45°);
 *   ring     circle of radius r, no fill, 1.5 px × --sw-mult stroke;
 *   square   filled, side 1.8 r, axis-aligned; diamond is the square turned 45°.
 * Two size multipliers compose on the mark as CSS transforms: --mark-user, the studio's Mark size control (set inline on the panel; 1 on the site),
 * and --mark-scale, the high-contrast block's 1.3 (the dot takes high contrast as --r-add instead, as it always has, so it is not counted twice).
 * A Jev item's mark (`jev`, logos.tsx isJev) reads --mark-jev in place of --mark-user: the studio's Jev mark size control (an absolute factor, set
 * inline on the panel; unset it falls back to --mark-user, so the site and the control's "= marks" setting draw every mark alike).
 * The vendor glyph (logos on) is scaled by the same product where it is drawn (glyphScale). `fixed` draws at the base size, for legend swatches.
 * A sized mark given a position is drawn at the origin of a group translated to (cx, cy), so the scale's origin is the SVG default (0 0) and never a
 * `transform-origin: cx cy` in px: WebKit resolves those lengths with the page zoom folded in, so on a zoomed page (Safari at anything but 100%)
 * the mark scaled about a point off to the side and drifted across the chart, the ranked view's marks landing on its value columns.
 */
export type MarkShape = "dot" | "plus" | "x" | "ring" | "square" | "diamond";
export const MARK_SHAPES: { id: MarkShape; label: string }[] = [{ id: "dot", label: "dot" }, { id: "plus", label: "plus" }, { id: "x", label: "×" }, { id: "ring", label: "ring" }, { id: "square", label: "square" }, { id: "diamond", label: "diamond" }];
/** The user's size factor on a mark: the Jev mark size where the item is a Jev row and the control is set, else the Mark size. */
const userScale = (jev: boolean) => (jev ? "var(--mark-jev, var(--mark-user, 1))" : "var(--mark-user, 1)");
/** The CSS transform that sizes a vendor glyph: the studio's Mark size (or Jev mark size, for a Jev row) × the high-contrast enlargement. */
export const glyphScale = (jev: boolean) => `scale(calc(var(--mark-scale, 1) * ${userScale(jev)}))`;
export function Mark({ shape = "dot", cx = 0, cy = 0, r, color, fixed = false, jev = false, className }: { shape?: MarkShape; cx?: number; cy?: number; r: number; color: string; fixed?: boolean; jev?: boolean; className?: string }) {
  if (!fixed && (cx || cy)) return <g transform={`translate(${cx} ${cy})`}><Mark shape={shape} r={r} color={color} jev={jev} className={className} /></g>;
  const scale = fixed ? undefined : shape === "dot" ? `scale(${userScale(jev)})` : glyphScale(jev);
  const st = scale ? ({ transform: scale, transformOrigin: "0px 0px" } as React.CSSProperties) : undefined;
  if (shape === "dot") return <circle className={className} cx={cx} cy={cy} r={r} fill={color} style={{ ...st, r: fixed ? undefined : `calc(${r}px + var(--r-add, 0px))` } as React.CSSProperties} />;
  if (shape === "ring") return <circle className={className} cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={1.5} style={{ ...st, strokeWidth: "calc(1.5 * var(--sw-mult, 1))" }} />;
  // the size transform goes on an outer group (a CSS transform would replace an element's own transform attribute), the turn on the inner one
  if (shape === "plus" || shape === "x") {
    const a = 1.6 * r;
    return (
      <g className={className} style={st}>
        <g stroke={color} strokeWidth={1.25} strokeLinecap="round" style={{ strokeWidth: "calc(1.25 * var(--sw-mult, 1))" }} transform={shape === "x" ? `rotate(45 ${cx} ${cy})` : undefined}>
          <line x1={cx - a} x2={cx + a} y1={cy} y2={cy} />
          <line x1={cx} x2={cx} y1={cy - a} y2={cy + a} />
        </g>
      </g>
    );
  }
  const side = 1.8 * r;
  return (
    <g className={className} style={st}>
      <rect x={cx - side / 2} y={cy - side / 2} width={side} height={side} fill={color} transform={shape === "diamond" ? `rotate(45 ${cx} ${cy})` : undefined} />
    </g>
  );
}

/**
 * Where a scatter names its points (the studio's Labels control; `beside` on the site): `beside` places a label next to each mark (and draws
 * no legend); `legend` draws no point labels and instead a legend row at the top of the SVG, one square swatch and name per item, in
 * display order, wrapped when the panel is too narrow, with the plot area moved down under it (legendLayout, Legend).
 */
export type LabelsMode = "beside" | "legend";
/**
 * A legend group (the studio's Key → by maker mode, `groups` on PRScatter and StudioScatter): the legend lists one swatch and name per group the
 * drawn items fall into (in order of first appearance; makers.ts), instead of one per item, and the items keep their beside labels, so the
 * names read on the plot and the key reads at the top. Without `groups`, Labels → legend lists the items and draws no point labels.
 * `title`, where given, is the legend entry's hover tooltip (an SVG <title>; the by-family groups list their members in it).
 */
export type LegendGroup = { id: string; name: string; color: string; title?: string };
/** The groups among `ids`, each with the first item that fell into it (`sample`, for the swatch: its logo where drawn, else the mark). */
export function legendGroups(ids: string[], groupOf: (id: string) => LegendGroup): (LegendGroup & { sample: string })[] {
  const out: (LegendGroup & { sample: string })[] = [];
  for (const id of ids) { const g = groupOf(id); if (!out.some((o) => o.id === g.id)) out.push({ ...g, sample: id }); }
  return out;
}
/** The legend text's class (styles.css has no rule for it; the presets' and high contrast's `svg text` rules reach it) and the point labels' (`.nm`), which the measurer's probes carry too. */
export const LEGEND_CLS = "lg", NAME_CLS = "nm";
/** Legend metrics at text scale `s`: a 10 px swatch, 6 px to the name, 18 px between items, 16 px rows; names at their measured width (measure.tsx) in the legend's 11 px × s face. */
export function legendLayout(names: string[], s: number, x0: number, x1: number, measure: Measure): { pos: { x: number; y: number }[]; height: number; sw: number; gap: number; row: number; fs: number } {
  const sw = 10 * s, gap = 6 * s, item = 18 * s, row = 16 * s, fs = 11 * s;
  const pos: { x: number; y: number }[] = [];
  let x = x0, r = 0;
  for (const n of names) {
    const w = sw + gap + measure(n, fs, LEGEND_CLS);
    if (x > x0 && x + w > x1) { x = x0; r++; }
    pos.push({ x, y: r * row });
    x += w + item;
  }
  return { pos, height: names.length ? (r + 1) * row : 0, sw, gap, row, fs };
}
/** How far below a legend's rows the plot area starts. */
export const LEGEND_GAP = 10;
/** The legend row(s) (LabelsMode `legend`): a swatch in the item colour and the name in --ink-2, from (x0, y) rightward, wrapping before x1. The swatch is the chart's mark shape (`mark`) at a fixed size, or a rounded square where the chart draws the item's vendor logo (never the logo itself): `mark` is one for every item, or a function of the item id (legendSwatch, for the Jev-only logos mode). */
export type LegendSwatch = MarkShape | "square-swatch";
/** The legend swatch for an item under a logos mode: a square where its logo is drawn, else the chart's mark shape. */
export const legendSwatch = (logos: LogosMode, mark: MarkShape) => (id: string): LegendSwatch => (logoShown(logos, id) ? "square-swatch" : mark);
export function Legend({ items, s, x0, x1, y, mark, measure }: { items: { id: string; name: string; color: string; title?: string }[]; s: number; x0: number; x1: number; y: number; mark?: LegendSwatch | ((id: string) => LegendSwatch); measure: Measure }) {
  const L = legendLayout(items.map((i) => i.name), s, x0, x1, measure);
  return (
    <g className="pr-legend">
      {items.map((it, i) => {
        const m = typeof mark === "function" ? mark(it.id) : mark;
        return (
        <g key={it.id} transform={`translate(${L.pos[i].x} ${y + L.pos[i].y})`}>
          {it.title && <title>{it.title}</title>}
          {m && m !== "square-swatch"
            ? <Mark shape={m} cx={L.sw / 2} cy={L.row / 2} r={m === "dot" ? 0.45 * L.sw : 0.36 * L.sw} color={it.color} fixed />
            : <rect y={(L.row - L.sw) / 2} width={L.sw} height={L.sw} rx={1.5} fill={it.color} />}
          <text x={L.sw + L.gap} y={L.row / 2 + 4 * s} fontSize={L.fs} fill="var(--ink-2)" className={LEGEND_CLS}>{it.name}</text>
        </g>
        );
      })}
    </g>
  );
}

/**
 * How the 95% interval boxes are drawn (the studio's Fill control, hatch.tsx FillMode; `filled` on the site). The box variables the styles set are read as:
 *   --box-alpha     fill opacity of a filled box; a hatched box draws its lines at 3 × this, capped at 1 (hatch.tsx hatchAlpha);
 *   --box-stroke    outline opacity in `filled` and `hatched` (0 on the site; Journal's hairline is 0.9); the outline modes draw the outline at 1;
 *   --box-stroke-w  outline width in px (0.75 unset), × --sw-mult (hatch.tsx OUTLINE_W).
 * The hatch tiles come from hatch.tsx HatchDefs, one per item in `<defs>`, so the map's boxes and the studio's bars (StudioCharts.tsx) hatch alike.
 */
/** Hatch-line opacity for a box whose fill opacity is --box-alpha. */
const HATCH_ALPHA = hatchAlpha("--box-alpha", 0.14);

/**
 * How the map draws each item's 95% intervals (the studio's Interval control, `interval` on PRScatter; `box` on the site). Every mode covers the
 * same footprint, the rectangle spanning the recall interval (width) and the precision interval (height), so the label placement is unchanged:
 *   box       the rectangle, drawn per the Fill control (FillMode above);
 *   whiskers  crosshair error bars through the point: a horizontal line across the recall interval and a vertical one across the precision
 *             interval, each with WHISKER_CAP × textScale end caps; the item's colour at --op-whisker (0.75 unset), 1 px × --sw-mult;
 *   band      the recall whisker alone (recall is the review figure);
 *   ellipse   the ellipse inscribed in the rectangle (semi-axes the intervals' half-widths), drawn per the Fill control like the box. It spans
 *             the two intervals; it is not a confidence ellipse (there is no covariance behind it) and the legend says so;
 *   bracket   the rectangle's four corners as L-shaped ticks, arms BRACKET_FRAC of each side (at least BRACKET_MIN px), no fill; whisker stroke;
 *   none      no interval mark, the point alone.
 * Whiskers, bands and brackets are drawn under the marks and labels, where the boxes go.
 */
export type IntervalMode = "box" | "whiskers" | "band" | "ellipse" | "bracket" | "none";
export const INTERVAL_MODES: { id: IntervalMode; label: string; title: string }[] = [
  { id: "box", label: "box", title: "A box spanning the 95% interval on recall (width) and precision (height); the Fill control draws it" },
  { id: "whiskers", label: "whiskers", title: "Error bars through the point: horizontal across the recall interval, vertical across the precision interval, with end caps" },
  { id: "band", label: "recall whisker", title: "The recall whisker alone (horizontal); the precision interval is not drawn" },
  { id: "ellipse", label: "ellipse", title: "An ellipse spanning the two intervals (inscribed in the box); the Fill control draws it. Not a confidence ellipse" },
  { id: "bracket", label: "brackets", title: "The box's four corners as short L-shaped ticks; no fill" },
  { id: "none", label: "none", title: "The point alone; no interval mark" },
];
export const isIntervalMode = (s: string | null): s is IntervalMode => INTERVAL_MODES.some((m) => m.id === s);
/** Whether the mode draws an area the Fill control applies to. */
export const intervalHasArea = (m: IntervalMode) => m === "box" || m === "ellipse";
/** Whisker end cap half-length at text scale 1, px; bracket arms as a fraction of the side, and their minimum, px. */
const WHISKER_CAP = 4, BRACKET_FRAC = 0.1, BRACKET_MIN = 4;
/** The whisker and bracket stroke: the item's colour, 1 px × --sw-mult, at --op-whisker (styles.css; the high-contrast block raises both). */
const WHISKER_STYLE = { strokeWidth: "calc(1px * var(--sw-mult, 1))", opacity: "var(--op-whisker, 0.75)" } as const;

/** The map's own tick step, in percent, for an axis `span` (0–1) wide: 20% across the full range, 5% on a fitted one (the `normal` density; ticks.ts pctStep picks the others around it). */
const mapStep = (span: number) => (span > 0.6 ? 20 : span > 0.3 ? 10 : span > 0.12 ? 5 : span > 0.06 ? 2 : 1);

/** Recall (x) against precision (y), or precision against recall under `swap`. Each item is a dot at the point estimate inside a box spanning both 95% intervals. */
/** `fill`: size to the host's box (host must be positioned, e.g. an absolutely-filled flex child) instead of a fixed height. */
/** `onSelect` makes each mark (dot, label and interval box) a button: click, Enter or Space. */
/** `highlight` (cross-chart hover, see hover.tsx) gives that item a subtle emphasis: a deeper box fill, its label forced visible and the item drawn on top; the mark itself is unchanged. `onHover` reports the mark or box under the pointer or keyboard focus. */
/** Motion (ui.tsx): marks, boxes and labels ease to their new place over 320 ms when the corpus, scope, gold or zoom changes; items fade in and out over 150 ms. */
/** How long the decider boxes breathe after the plot loads or its points change: PULSE_CYCLES cycles of the styles.css box-breathe animation (keep in step with `.pr-box.pulse`). */
const PULSE_CYCLES = 2, PULSE_CYCLE_MS = 650;

/** `pulse` lets the interval boxes of decider items (`decider: true`) breathe for a few cycles whenever the plot loads or its set of points changes: a fill-opacity cycle (styles.css .pr-box.pulse) on the shaded box only, never the mark or label; a highlighted box keeps its steady deeper fill instead. Off by default and under prefers-reduced-motion. */
/** `domain` (the screenshot studio) fixes both axes to explicit 0–1 ranges, overriding `zoom`. */
/** `textScale` (the studio's Text control; 1 on the site) multiplies every font size, the label placement's box heights and offsets (its widths are measured, measure.tsx) and the margins that hold tick labels. Axis stroke width, dot radius and the vendor-glyph size read the --sw-mult / --r-add / --mark-scale CSS variables (styles.css, the studio's high-contrast block; unset on the site). */
/** `leaders` (the studio's Leaders control; off on the site) draws a hairline from each displaced label back to its mark (leaderFor), under every mark and label. */
/** `labels` (the studio's Labels control; `beside` on the site): `legend` drops the point labels (and leaders) for a legend row at the top (Legend), the plot moved down under it. */
/** `groups` (the studio's Key → by maker; none on the site): the legend lists the groups the items fall into (LegendGroup) and the point labels stay, whichever Labels mode is on. */
/** `logos` (logos.tsx LogosMode, or the boolean it was): which items get their vendor glyph as the mark (`all`, the Jev rows alone, or none, when every item gets `mark`). */
/** `mark` (the studio's Marks control; `dot` on the site) is the point shape where an item draws no logo; `markSize` is the studio's Mark size multiplier (the --mark-user the panel sets) and `jevMarkSize` the Jev rows' own (--mark-jev; `markSize` when unset): the label placement needs them as numbers to keep labels and leaders clear of a larger mark. */
/** `boxes` (the studio's Fill control; `filled` on the site) is how the interval boxes (or ellipses) are drawn (hatch.tsx FillMode). */
/** `interval` (the studio's Interval control; `box` on the site) is the shape of the interval mark (IntervalMode above). */
/** `bg` (the studio's Background control; the site's dot matrix, `dots`) is the pattern behind the plot area (plotBg.tsx). */
/** `swap` (the studio's Axes orientation control; off on the site) puts precision on x and recall on y. Every item's (recall, precision) is read through `xCI` / `yCI` once, so the marks, intervals (the box's width becomes the precision interval, the recall whisker vertical), fit-to-data domain, ticks, titles, labels and leaders all follow. `domain` is always in plot x/y (the caller maps its metric bounds). */
/** `ticks` (the studio's Gridlines control; `normal` on the site) is the tick and gridline density on both axes (ticks.ts TickDensity): gridlines and tick labels share the step; labels thin to every n-th tick where they would touch. */
export type PRDomain = { x: [number, number]; y: [number, number] };
export function PRScatter({ items, zoom, domain, swap = false, xLabel = swap ? "Precision" : "Recall", yLabel = swap ? "Recall" : "Precision", emptyText, logos: logosIn, height = 520, fill = false, onSelect, highlight, onHover, pulse = false, textScale = 1, leaders = false, labels: labelsMode = "beside", mark = "dot", markSize = 1, jevMarkSize = markSize, boxes: boxMode = "filled", interval = "box", bg = "dots", groups, ticks = "normal" }: { items: PRItem[]; zoom: boolean; domain?: PRDomain; swap?: boolean; xLabel?: string; yLabel?: string; emptyText?: string; logos?: boolean | LogosMode; height?: number; fill?: boolean; onSelect?: (item: PRItem) => void; highlight?: string | null; onHover?: (id: string | null) => void; pulse?: boolean; textScale?: number; leaders?: boolean; labels?: LabelsMode; mark?: MarkShape; markSize?: number; jevMarkSize?: number; boxes?: FillMode; interval?: IntervalMode; bg?: PlotBg; groups?: (id: string) => LegendGroup; ticks?: TickDensity }) {
  const { tip, show, hide, hostRef } = useTip();
  const logos = logosMode(logosIn, false);
  const hasLogo = (p: PRItem) => logoShown(logos, p.id) && !!logoFor(p.id);
  const tipIcon = (p: PRItem) => (hasLogo(p) ? <Logo model={p.id} size={12} /> : undefined);
  // text widths as drawn (measure.tsx): the legend rows and the point labels are laid out from them; the tick labels (.mono) for the thinning
  const { measure, probes } = useTextMeasure([LEGEND_CLS, NAME_CLS, "mono"]);
  const area = intervalHasArea(interval);
  const hatched = area && isHatched(boxMode), outlined = isOutlined(boxMode);
  // pattern ids (url(#…)-safe, unique to this instance): the hatch tiles (hatch.tsx) and the background
  const hatchId = useHatchIds();
  const bgId = `bg-${useId().replace(/[^A-Za-z0-9_-]/g, "")}`;
  const pickMark = onSelect && ((it: PRItem) => { hide(); onSelect(it); });
  const sz = useSize(hostRef, { w: 760, h: height });
  const W = sz.w, H = fill ? Math.max(300, sz.h) : height;
  const s = textScale;
  type Pt = PRItem & { recall: NonNullable<CI>; precision: NonNullable<CI> };
  const hasPt = (it: PRItem): it is Pt => !!it.recall && !!it.precision;
  const pts = items.filter(hasPt);
  // the one place an item's metrics become plot axes: recall on x and precision on y, or the other way round under `swap`
  const xCI = (p: Pt): NonNullable<CI> => (swap ? p.precision : p.recall), yCI = (p: Pt): NonNullable<CI> => (swap ? p.recall : p.precision);
  const undefinedOnes = items.filter((it) => !it.recall || !it.precision);
  // Items that just left stay for their fade-out; the axes, label placement and highlight consider only the present ones.
  const presence = usePresence(items, (it) => it.id);
  const stateOf = Object.fromEntries(presence.map((p) => [p.key, p.state]));
  const shownPts = presence.map((p) => p.item).filter(hasPt);
  // Cross-chart highlight: only when the highlighted id is plotted here. It is drawn last (on top); the other items are left as they are.
  const hl = highlight != null && pts.some((p) => p.id === highlight) ? highlight : null;
  const drawn = hl == null ? shownPts : [...shownPts.filter((p) => p.id !== hl), ...shownPts.filter((p) => p.id === hl)];

  // The pulse runs for a bounded window after the plotted set changes (ids and point estimates); outside the window the boxes are still (ui.tsx usePulseWindow).
  const sig = pts.map((p) => `${p.id}:${p.recall[0].toFixed(4)}:${p.precision[0].toFixed(4)}`).join("|");
  const pulsing = usePulseWindow(sig, pulse, PULSE_CYCLES * PULSE_CYCLE_MS);

  const dom = useMemo(() => {
    if (domain) return domain;
    if (!zoom || pts.length === 0) return { x: [0, 1] as [number, number], y: [0, 1] as [number, number] };
    const pad = (lo: number, hi: number): [number, number] => {
      const p = Math.max(0.02, (hi - lo) * 0.12);
      return [Math.max(0, lo - p), Math.min(1, hi + p)];
    };
    return {
      x: pad(Math.min(...pts.map((p) => xCI(p)[1])), Math.max(...pts.map((p) => xCI(p)[2]))),
      y: pad(Math.min(...pts.map((p) => yCI(p)[1])), Math.max(...pts.map((p) => yCI(p)[2]))),
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pts, zoom, domain, swap]);

  // tick step per axis (percent; ticks.ts): the map's own at `normal`, the density's around it; every tick draws a gridline (unless `none`)
  const xSpan = dom.x[1] - dom.x[0], ySpan = dom.y[1] - dom.y[0];
  const xStep = pctStep(ticks, xSpan, mapStep(xSpan)), yStep = pctStep(ticks, ySpan, mapStep(ySpan));
  const xt = pctTicks(dom.x[0], dom.x[1], xStep), yt = pctTicks(dom.y[0], dom.y[1], yStep);
  const grid = gridOn(ticks);
  const tickLabel = (t: number) => `${Math.round(t * 100)}%`;
  const { PL, PB, titleX } = axisMargins(yt.map(tickLabel), s);
  // legend mode: the legend rows sit at the top (from LEGEND_Y), and the plot area starts LEGEND_GAP below them instead of at PT; the rows list the
  // items, or the groups they fall into (`groups`), in which case the points keep their labels (pointLabels) as in beside mode
  const LEGEND_Y = 4;
  const grouped = labelsMode === "legend" && groups ? legendGroups(pts.map((p) => p.id), groups) : null;
  const legendItems = grouped ?? pts.map((p) => ({ id: p.id, name: p.name + (p.subset ? " *" : ""), color: p.color, sample: p.id }));
  const pointLabels = labelsMode === "beside" || !!grouped;
  const legendH = labelsMode === "legend" ? legendLayout(legendItems.map((i) => i.name), s, PL, W - PR, measure).height : 0;
  const top = labelsMode === "legend" ? Math.max(PT, LEGEND_Y + legendH + LEGEND_GAP * s) : PT;
  const X = (v: number) => PL + ((v - dom.x[0]) / (dom.x[1] - dom.x[0] || 1)) * (W - PL - PR);
  const Y = (v: number) => top + (1 - (v - dom.y[0]) / (dom.y[1] - dom.y[0] || 1)) * (H - top - PB);
  // labels on every n-th tick where adjacent ones would touch ("100%" at its measured width plus 8 s along x; a line's height along y); every tick keeps its gridline
  const xEvery = labelEvery(measure("100%", TICK_FS * s, "mono") + 8 * s, ((W - PL - PR) * xStep) / 100 / (xSpan || 1));
  const yEvery = labelEvery(TICK_FS * s * 1.4, ((H - top - PB) * yStep) / 100 / (ySpan || 1));

  // Per item: its size factor (the Jev mark size for a Jev row, else the Mark size), the mark radius as drawn (the glyph's half-size or the dot's radius, × that),
  // and the beside-the-mark label offset: 9 s at size 1, grown so the gap to a larger mark stays. `grow` is what a larger mark adds; the placement pads each dot by its own.
  const sizeOf = (p: PRItem) => (isJev(p.id) ? jevMarkSize : markSize);
  const markR = (p: PRItem) => (hasLogo(p) ? 6 : 3.2) * sizeOf(p);
  const growOf = (p: PRItem) => Math.max(0, 6 * sizeOf(p) - 6);
  const O = (p: PRItem) => 9 * s + growOf(p);
  // label placement: try several offsets; avoid other dots and labels; give up (hover only) when nothing fits
  const labels = useMemo(() => {
    const placed: { x: number; y: number; w: number; h: number }[] = [];
    const dots = pts.map((p) => ({ x: X(xCI(p)[0]), y: Y(yCI(p)[0]), pad: 5 + growOf(p) }));
    const overlaps = (a: { x: number; y: number; w: number; h: number }) =>
      placed.some((b) => a.x < b.x + b.w + 2 && a.x + a.w + 2 > b.x && a.y < b.y + b.h + 1 && a.y + a.h + 1 > b.y) ||
      dots.some((d) => d.x > a.x - d.pad && d.x < a.x + a.w + d.pad && d.y > a.y - d.pad && d.y < a.y + a.h + d.pad);
    return pts.map((p, i) => {
      const text = p.name + (p.subset ? " *" : "");
      const grow = growOf(p);
      const w = measure(text, 11 * s, NAME_CLS) + 4, h = 13 * s, o = O(p), d = 22 * s + grow;
      const { x, y } = dots[i];
      const cands: { x: number; y: number }[] = [
        { x: x + o, y: y - h / 2 }, { x: x - o - w, y: y - h / 2 },
        { x: x - w / 2, y: y - 11 * s - h }, { x: x - w / 2, y: y + 11 * s },
        { x: x + o - s, y: y - h - 4 }, { x: x + o - s, y: y + 4 }, { x: x - o + s - w, y: y - h - 4 }, { x: x - o + s - w, y: y + 4 },
        { x: x + o, y: y - h / 2 - d }, { x: x + o, y: y - h / 2 + d }, { x: x - o - w, y: y - h / 2 - d }, { x: x - o - w, y: y - h / 2 + d },
      ];
      const c = cands.find((cc) => cc.x >= PL && cc.x + w <= W - 2 && cc.y >= 0 && !overlaps({ ...cc, w, h }));
      if (!c) return null;
      placed.push({ ...c, w, h });
      return { ...c, w, h, text };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pts, dom, W, H, s, top, markSize, jevMarkSize, logos, measure, swap]);

  // Where everything is heading, keyed by item so a move is continuous across re-sorts; `geo` is where it is drawn this frame.
  const target: Record<string, number> = {};
  for (const p of drawn) {
    const xc = xCI(p), yc = yCI(p);
    const x0 = X(xc[1]), x1 = X(xc[2]), y0 = Y(yc[2]), y1 = Y(yc[1]);
    target[`${p.id}:x`] = X(xc[0]); target[`${p.id}:y`] = Y(yc[0]);
    target[`${p.id}:x0`] = x0; target[`${p.id}:y0`] = y0; target[`${p.id}:w`] = Math.max(1, x1 - x0); target[`${p.id}:h`] = Math.max(1, y1 - y0);
  }
  const geo = useTween(target, undefined, undefined, `${W}x${H}`);
  const g = (id: string, k: string) => geo[`${id}:${k}`] ?? target[`${id}:${k}`];

  // Mark sizes are uniform.
  const glyph = (_p: PRItem) => 12;

  return (
    <div ref={hostRef} data-tip-host style={fill ? { position: "absolute", inset: 0 } : { position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ display: "block", overflow: "visible" }}>
        {/* plot-area background (plotBg.tsx: the dot matrix, or the studio's choice), then the tick grid on top */}
        <defs>
          <PlotBgPattern id={bgId} kind={bg} s={s} />
          {/* hatch tiles (hatch.tsx), one per item, in the hatched modes */}
          <HatchDefs items={drawn} s={s} hatchId={hatchId} on={hatched} />
        </defs>
        {bg !== "none" && <rect x={PL} y={top} width={W - PR - PL} height={H - PB - top} fill={`url(#${bgId})`} />}
        {/* vertical gridlines read --grid-x (falls back to --grid), so a preset can keep horizontal rules only (Epoch); the y-axis line likewise --axis-y */}
        {xt.map((t) => (
          <g key={`x${t}`}>
            {grid && <line className="gl" x1={X(t)} x2={X(t)} y1={top} y2={H - PB} stroke="var(--grid-x, var(--grid))" />}
            {labelledAt(t * 100, xStep, xEvery) && <text x={X(t)} y={H - PB + 16 * s} fontSize={TICK_FS * s} textAnchor="middle" fill="var(--ink-3)" className="mono">{tickLabel(t)}</text>}
          </g>
        ))}
        {yt.map((t) => (
          <g key={`y${t}`}>
            {grid && <line className="gl" x1={PL} x2={W - PR} y1={Y(t)} y2={Y(t)} stroke="var(--grid)" />}
            {labelledAt(t * 100, yStep, yEvery) && <text x={PL - 8} y={Y(t) + 3.5 * s} fontSize={TICK_FS * s} textAnchor="end" fill="var(--ink-3)" className="mono">{tickLabel(t)}</text>}
          </g>
        ))}
        <g stroke="var(--axis)" style={{ strokeWidth: "var(--sw-mult, 1)" }}>
          <line x1={PL} x2={W - PR} y1={H - PB} y2={H - PB} />
          <line x1={PL} x2={PL} y1={top} y2={H - PB} stroke="var(--axis-y, var(--axis))" />
        </g>
        <text x={(PL + W - PR) / 2} y={H - 10 * s} fontSize={TITLE_FS * s} textAnchor="middle" fill="var(--ink-2)" className="ax">{xLabel}</text>
        <text x={titleX} y={(top + H - PB) / 2} fontSize={TITLE_FS * s} textAnchor="middle" fill="var(--ink-2)" className="ax" transform={`rotate(-90 ${titleX} ${(top + H - PB) / 2})`}>{yLabel}</text>
        {labelsMode === "legend" && <Legend items={legendItems} s={s} x0={PL} x1={W - PR} y={LEGEND_Y} mark={(id) => legendSwatch(logos, mark)(legendItems.find((i) => i.id === id)?.sample ?? id)} measure={measure} />}
        {probes}

        {/* CI marks (IntervalMode) first so dots sit on top; every box or ellipse is drawn the same way (FillMode), the highlighted one a little deeper */}
        {interval !== "none" && drawn.map((p) => {
          const mark = { kind: "mark" as const, x: X(xCI(p)[0]), y: Y(yCI(p)[0]), r: 9 };
          const boxFill = boxMode === "outline" ? "none" : hatched ? `url(#${hatchId(p.id)})` : p.color;
          const boxFillOpacity = boxMode === "outline" ? undefined : hl === p.id ? (hatched ? 1 : 0.35) : hatched ? HATCH_ALPHA : "var(--box-alpha)";
          // the footprint this frame: the box, and the point through which the whiskers run
          const x0 = g(p.id, "x0"), y0 = g(p.id, "y0"), w = g(p.id, "w"), h = g(p.id, "h"), x1 = x0 + w, y1 = y0 + h, cx = g(p.id, "x"), cy = g(p.id, "y");
          const areaStyle = { fillOpacity: boxFillOpacity, strokeOpacity: outlined ? 1 : "var(--box-stroke, 0)", strokeWidth: OUTLINE_W, transition: "fill-opacity 120ms" } as const;
          // the pulse class is dropped while this box is highlighted, so the deeper hover fill is steady and wins
          const areaCls = pulsing && p.decider && hl !== p.id ? "pr-box pulse" : "pr-box";
          const cap = WHISKER_CAP * s, ax = Math.max(BRACKET_MIN, BRACKET_FRAC * w), ay = Math.max(BRACKET_MIN, BRACKET_FRAC * h);
          return (
            <g key={`b${p.id}`} className="fd" style={fadeStyle(stateOf[p.id] ?? "exit")}>{/* fade in / out (ui.tsx usePresence) */}
            <g {...hoverable(onHover, p.id)}>{/* cross-chart hover (hover.tsx) wraps the tooltip group */}
            <g onMouseMove={(e) => show(e, mark, prTip(p, tipIcon(p)))} onMouseLeave={hide} {...selectable(pickMark, p, p.name)} tabIndex={-1}>
              {/* `--box-stroke` (0 on the site) lets a studio style preset draw the box as a hairline outline in the item's colour; the outline modes draw it regardless */}
              {interval === "box" && <rect key={`${p.id}:${sig}`} className={areaCls} x={x0} y={y0} width={w} height={h} fill={boxFill} stroke={p.color} strokeWidth={0.75} style={areaStyle} rx={1} />}
              {interval === "ellipse" && <ellipse key={`${p.id}:${sig}`} className={areaCls} cx={x0 + w / 2} cy={y0 + h / 2} rx={w / 2} ry={h / 2} fill={boxFill} stroke={p.color} strokeWidth={0.75} style={areaStyle} />}
              {(interval === "whiskers" || interval === "band") && (
                <g className="pr-whisker" stroke={p.color} strokeWidth={1} fill="none" style={WHISKER_STYLE}>
                  {/* the horizontal whisker is the recall interval, or the precision one under `swap`; `band` keeps the recall whisker alone, whichever way it runs */}
                  {(interval === "whiskers" || !swap) && (
                    <>
                      <line x1={x0} x2={x1} y1={cy} y2={cy} />
                      <line x1={x0} x2={x0} y1={cy - cap} y2={cy + cap} />
                      <line x1={x1} x2={x1} y1={cy - cap} y2={cy + cap} />
                    </>
                  )}
                  {(interval === "whiskers" || swap) && (
                    <>
                      <line x1={cx} x2={cx} y1={y0} y2={y1} />
                      <line x1={cx - cap} x2={cx + cap} y1={y0} y2={y0} />
                      <line x1={cx - cap} x2={cx + cap} y1={y1} y2={y1} />
                    </>
                  )}
                </g>
              )}
              {interval === "bracket" && (
                <path
                  className="pr-whisker" stroke={p.color} strokeWidth={1} fill="none" style={WHISKER_STYLE}
                  d={`M${x0} ${y0 + ay}V${y0}H${x0 + ax} M${x1 - ax} ${y0}H${x1}V${y0 + ay} M${x1} ${y1 - ay}V${y1}H${x1 - ax} M${x0 + ax} ${y1}H${x0}V${y1 - ay}`}
                />
              )}
            </g>
            </g>
            </g>
          );
        })}
        {/* leader lines (studio): drawn after every box and before every mark and label, so none crosses a mark or a label */}
        {leaders && pointLabels && drawn.map((p) => {
          const li = pts.indexOf(p), l0 = li >= 0 ? labels[li] : null;
          if (!l0) return null;
          const tx = X(xCI(p)[0]), ty = Y(yCI(p)[0]);
          const ld = leaderFor({ x: l0.x - tx, y: l0.y - ty, w: l0.w, h: l0.h }, markR(p), O(p));
          if (!ld) return null;
          return (
            <g key={`l${p.id}`} className="fd" style={fadeStyle(stateOf[p.id] ?? "exit")} transform={`translate(${g(p.id, "x")} ${g(p.id, "y")})`}>
              <line className="pr-leader" x1={ld.x1} y1={ld.y1} x2={ld.x2} y2={ld.y2} stroke={p.color} strokeOpacity={0.7} style={LEADER_STYLE} />
            </g>
          );
        })}
        {/* the mark and its label share one group so both hover, click and focus as a unit; labels have a panel-coloured halo so they read over the boxes */}
        {drawn.map((p) => {
          // a highlighted mark whose label found no room gets one anyway, at the first candidate position
          const tx = X(xCI(p)[0]), ty = Y(yCI(p)[0]), x = g(p.id, "x"), y = g(p.id, "y");
          const li = pts.indexOf(p), l0 = li >= 0 ? labels[li] : null;
          const l = !pointLabels ? null : l0 ? { x: l0.x - tx, y: l0.y - ty, text: l0.text } : hl === p.id ? { x: O(p), y: -6.5 * s, text: p.name + (p.subset ? " *" : "") } : null;
          const hitR = Math.max(9, markR(p) + 3);
          return (
            <g key={`d${p.id}`} className="fd" style={fadeStyle(stateOf[p.id] ?? "exit")}>{/* fade in / out (ui.tsx usePresence) */}
            <g {...hoverable(onHover, p.id)}>{/* cross-chart hover (hover.tsx) wraps the tooltip group */}
            <g transform={`translate(${x} ${y})`} onMouseMove={(e) => show(e, { kind: "mark", x: tx, y: ty, r: hitR }, prTip(p, tipIcon(p)))} onMouseLeave={hide} {...selectable(pickMark, p, p.name)}>
              <circle className="hit" r={hitR} fill="transparent" />
              {hasLogo(p) ? (
                <g color={p.color} style={{ transform: glyphScale(isJev(p.id)) }}><LogoGlyph model={p.id} cx={0} cy={0} size={glyph(p)} /></g>
              ) : (
                <Mark shape={mark} r={3.2} color={p.color} jev={isJev(p.id)} />
              )}
              {l && (
                <text x={l.x} y={l.y + 10 * s} fontSize={11 * s} fill="var(--ink)" className="nm" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 2.5, strokeLinejoin: "round", pointerEvents: onSelect ? "auto" : "none" }}>
                  {l.text}
                </text>
              )}
            </g>
            </g>
            </g>
          );
        })}
        {pts.length === 0 && <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={13 * s} fill="var(--ink-4)">{emptyText ?? "Select at least one model."}</text>}
      </svg>
      {undefinedOnes.length > 0 && (
        <div className="legend-note">
          {undefinedOnes.map((u) => (
            <span key={u.id} className="k"><span style={{ width: 9, height: 9, borderRadius: 2, background: u.color, display: "inline-block" }} />{u.name}: flagged nothing, precision undefined</span>
          ))}
        </div>
      )}
      <TipBox tip={tip} hint={onSelect ? CLICK_HINT : undefined} />
    </div>
  );
}
