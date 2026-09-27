import { useId, useMemo, useRef, type CSSProperties } from "react";
import type { CI } from "../data";
import { LogoGlyph, isJev, logoFor, logoShown, logosMode, type LogosMode } from "../logos";
import { LEADER_STYLE, LEGEND_CLS, LEGEND_GAP, Legend, Mark, NAME_CLS, axisMargins, glyphScale, leaderFor, legendGroups, legendLayout, legendSwatch, userScale, type LabelsMode, type LegendGroup, type MarkShape } from "./PRScatter";
import { useTextMeasure } from "./measure";
import { DECIDER_TEXT, selectable, useSize, useWidth } from "./ui";
import { PlotBgPattern, type PlotBg } from "./plotBg";
import { HatchDefs, OUTLINE_W, hatchAlpha, isHatched, isOutlined, useHatchIds, type FillMode } from "./hatch";
import { gridOn, labelEvery, labelledAt, linTarget, linTicks, logTicks, thinLogLabels, type TickDensity } from "./ticks";

/** A url(#…)-safe id from useId, for this chart's background pattern (plotBg.tsx). */
const useBgId = () => `bg-${useId().replace(/[^A-Za-z0-9_-]/g, "")}`;

/**
 * Screenshot-studio charts for the Cost, Speed and Stability plots (StudioPage.tsx): static SVG, no tooltips, hover or motion; every
 * figure is written on the chart. They read the same CSS variables as the dashboard cards (--ink*, --line, --grid, --axis, --bar-alpha)
 * and the item colour from the roster, so the studio's Style presets (styles.css .studio-plot[data-style]) restyle them unchanged.
 * Gridlines carry className="gl" like PRScatter's so a preset can dot them.
 */

/** A second figure a row may carry (the Stability chart's temperature-0 rerun): drawn as a lighter bar or a hollow dot when the chart's `t0` mode is on. */
export type StudioRowT0 = { value: number; lo?: number | null; hi?: number | null; label: string };
/** One row of a StudioBars chart. `lo`/`hi` draw a whisker (an interval around `value`); `sub` is a muted secondary figure after the label; `empty` replaces "not measured"; `t0` is the row's temperature-0 figure (StudioRowT0). */
export type StudioRow = { id: string; name: string; color: string; value: number | null; lo?: number | null; hi?: number | null; label: string; sub?: string; empty?: string; decider?: boolean; subset?: string | null; t0?: StudioRowT0 };

/**
 * How a row's temperature-0 figure (StudioRow.t0) is drawn (the studio's Stability → Temperature 0 control, opsRows.ts StabT0): `none` ignores it;
 * `paired` adds a second bar under the row's bar, in a lighter tint of its colour (T0_TINT); `dots` makes the chart a lollipop: a faint stem from the
 * axis, a filled mark at the row's value and a hollow dot at the t = 0 value, the two joined by a segment in the row's colour. Rows without a `t0`
 * keep their one element. Rows are taller in either mode so the second figure's label fits.
 */
export type T0Mode = "none" | "paired" | "dots";
/** The t = 0 tint: the row's colour mixed half-and-half with the panel, so the second bar reads as the same hue, lighter, under any Fill mode. */
const T0_TINT = (color: string) => `color-mix(in srgb, ${color} 50%, var(--panel))`;
const T0_TAG = "t = 0";
/** The lollipop's segment and hollow-dot stroke: 1.75 px × the high-contrast multiplier (the dot itself follows the Mark size, --mark-user). */
const T0_STROKE_W = "calc(1.75px * var(--sw-mult, 1))";

const ROW0 = 30, TOP0 = 8;
/** Row heights in the t = 0 modes: two bars with a label each; a dot with its label above and the hollow dot's below. */
const ROW_PAIRED = 40, ROW_LOLLI = 44;
/** The t = 0 key (two entries, drawn above the rows when `t0Key` is on): its row height and the gap to the first row, at text scale 1. */
const KEY_ROW = 16;
/** Stroke widths and mark radii read the studio's high-contrast variables (styles.css .studio-plot[data-contrast="high"]); unset, they are the defaults given here. */
const SW = (base: number) => ({ strokeWidth: `calc(${base} * var(--sw-mult, 1))` });
/** Hatch-line opacity for a bar whose filled opacity is --bar-alpha (hatch.tsx). */
const BAR_HATCH_ALPHA = hatchAlpha("--bar-alpha", 0.55);
/** The hairline edge a hatched bar gets (no outline mode on), so its extent reads where the lines thin out: 0.5 px × --sw-mult. */
const HATCHED_EDGE_W = "calc(0.5px * var(--sw-mult, 1))";
/**
 * The ticks of a value axis `plotPx` long at a density (ticks.ts; the tick routines themselves live there): linear, nice numbers at the density's target
 * count; log, decades and what the density adds inside them. Each carries whether it is labelled: labels thin to every n-th tick where the widest one
 * (`labelPx`, measured) would touch its neighbour; every tick keeps its gridline.
 */
function axisTicks(scale: "linear" | "log", dom: [number, number], density: TickDensity, plotPx: number, labelPx: (t: number) => number): { t: number; label: boolean }[] {
  if (scale === "log") {
    const raw = logTicks(dom[0], dom[1], density);
    const widest = Math.max(0, ...raw.filter((x) => x.label).map((x) => labelPx(x.t)));
    return thinLogLabels(raw, widest, plotPx / (Math.log10(dom[1]) - Math.log10(dom[0]) || 1));
  }
  const ts = linTicks(dom[0], dom[1], linTarget(density));
  const step = ts.length > 1 ? ts[1] - ts[0] : dom[1] - dom[0] || 1;
  const every = labelEvery(Math.max(0, ...ts.map(labelPx)), (plotPx * step) / (dom[1] - dom[0] || 1));
  return ts.map((t) => ({ t, label: labelledAt(t, step, every) }));
}

/**
 * Horizontal bars (`kind: "bar"`) or a dot plot (`kind: "dot"`: whisker and dot in the row's colour) on a linear or log axis, one row per item,
 * the figure written after the bar. `domain` fixes the axis (linear: bars grow from its start, the zoomed Stability view); otherwise linear runs
 * from 0 to a little past the largest value or whisker end and log from the decade below the smallest value to the decade above the largest.
 * `sort`: ascending, descending or the given order; rows without a value sink to the bottom in muted ink (or pass them filtered out).
 * The width follows the host; the height follows the rows (the studio panel's `auto` mode).
 * `textScale` (the studio's Text control) multiplies every font size and, with it, the row height, the label and value columns and the axis area.
 * `mark` (the studio's Marks control) is the dot plot's point shape (PRScatter.tsx Mark; a Jev row's reads the Jev mark size, --mark-jev).
 * `logos` (logos.tsx LogosMode, or the boolean it was): which rows carry their vendor glyph before the name; in `jev` the name column keeps the glyph
 * layout (names left-aligned after the glyph slot) and only the Jev rows fill the slot, so the LLM rows read as name-only rows in the same table.
 * `onSelect` (the dashboard's B variant, AppB.tsx; the studio passes none) makes each row a button that opens the details modal for its id: a transparent
 * full-width hit rect behind the row tints on hover (styles.css `.sel .hit`), Enter and Space work (ui.tsx selectable). Without it the rows are inert, as in the studio.
 * `bg` (the studio's Background control; none by default) is a pattern behind the bar area, under the gridlines (plotBg.tsx).
 * `bars` (the studio's Fill control; `filled` by default) is how a bar is drawn (hatch.tsx FillMode): a shade at --bar-alpha; 45° hatch lines in the
 * row's colour at 3 × --bar-alpha (capped at 1) inside a hairline edge; the edge alone, --box-stroke-w px wide; or the hatch inside that edge. The
 * whisker gets a panel-colour halo over a hatched bar so its ink line stays legible across the hatch lines; the figures sit clear of the bar either way.
 * `ticks` (the studio's Gridlines control; `normal` by default) is the axis's tick and gridline density (ticks.ts TickDensity, axisTicks above).
 * `t0` (T0Mode; `none` by default) draws each row's temperature-0 figure (StudioRow.t0) as a second, lighter bar or as the hollow dot of a lollipop;
 * `t0Tag` (on by default) puts a small grey "t = 0" after that figure's label; `t0Key` (off by default) draws a two-entry key (default sampling /
 * temperature 0) above the rows. The `dots` mode draws the chart as dots whatever `kind` says. Nothing changes while no row carries a `t0`.
 */
export function StudioBars({ rows, kind: kindIn = "bar", scale = "linear", domain, sort = "asc", axis, fmtTick, logos: logosIn, labelW, textScale = 1, mark: markIn = "dot", onSelect, bg = "none", bars: barMode = "filled", ticks: density = "normal", t0: t0Mode = "none", t0Tag = true, t0Key = false }: { rows: StudioRow[]; kind?: "bar" | "dot"; scale?: "linear" | "log"; domain?: [number, number]; sort?: "asc" | "desc" | "none"; axis: string; fmtTick: (v: number) => string; logos?: boolean | LogosMode; labelW?: number; textScale?: number; mark?: MarkShape; onSelect?: (id: string) => void; bg?: PlotBg; bars?: FillMode; ticks?: TickDensity; t0?: T0Mode; t0Tag?: boolean; t0Key?: boolean }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const logosOn = logosMode(logosIn, true), logos = logosOn !== "none";
  const glyphOf = (r: StudioRow) => logoShown(logosOn, r.id);
  const bgId = useBgId();
  // the t = 0 modes: `dots` turns the chart into a lollipop (kind dot); `paired` a second bar. Either engages only where a row carries a t = 0 figure.
  const kind = t0Mode === "dots" ? "dot" : kindIn;
  const t0Of = (r: StudioRow) => (t0Mode === "none" ? undefined : r.t0);
  const anyT0 = rows.some((r) => r.value != null && t0Of(r));
  const paired = anyT0 && kind === "bar", lolli = anyT0 && kind === "dot";
  // the lollipop's filled mark is the Marks control's shape; a ring there would read as the hollow t = 0 dot, so it falls back to the dot
  const mark: MarkShape = lolli && markIn === "ring" ? "dot" : markIn;
  const hatched = kind === "bar" && isHatched(barMode), outlined = kind === "bar" && isOutlined(barMode);
  const hatchId = useHatchIds();
  const t0HatchId = (id: string) => hatchId(`${id}~t0`);
  const W = useWidth(hostRef, 900);
  const s = textScale, ROW = (paired ? ROW_PAIRED : lolli ? ROW_LOLLI : ROW0) * s;
  const keyOn = t0Key && anyT0, keyH = keyOn ? (KEY_ROW + 8) * s : 0, TOP = TOP0 * s + keyH;
  // text widths as drawn (measure.tsx): names (.nm, the decider rows heavier), figures (.mono), the plain "not measured" and the key's names (.lg)
  const { measure, probes } = useTextMeasure([NAME_CLS, { key: "dec", className: NAME_CLS, style: DECIDER_TEXT }, "mono", "", LEGEND_CLS]);
  const labelOf = (r: StudioRow) => `${r.name}${r.subset ? " *" : ""}`;
  const nameW = (r: StudioRow) => measure(labelOf(r), 12.5 * s, r.decider ? "dec" : NAME_CLS);
  // the name column: the glyph (30 s to the name's start) or a 10 s pad, the widest name, 14 s to the axis; at least 170 s, at most 260 s
  const LABEL_W = labelW ?? Math.min(260 * s, Math.max(170 * s, ...rows.map((r) => nameW(r) + (logos ? 44 : 24) * s)));
  // the value labels' sizes: a paired row's two figures are a touch smaller (11.5 s) so both fit the row; the tag is 10 s
  const FS_VAL = paired ? 11.5 * s : 12 * s, FS_TAG = 10 * s, TAG_GAP = 5 * s;
  const tagW = t0Tag ? TAG_GAP + measure(T0_TAG, FS_TAG) : 0;
  const t0LabelW = (r: StudioRow) => { const t = t0Of(r); return t ? measure(t.label, FS_VAL, "mono") + tagW : 0; };
  // the value column after the longest bar: the figure, then the muted secondary figure when a row carries one, and 14 s of air; a paired row's t = 0 label
  // (with its tag) counts too; in the lollipop the labels are centred on their dots, so the overhang is half a label (plus the tag after the t = 0 one)
  const VALUE_W = Math.max(90 * s, ...rows.map((r) => {
    if (r.value == null) return measure(r.empty ?? "not measured", 11.5 * s) + 14 * s;
    const main = measure(r.label, FS_VAL, "mono") + (r.sub ? measure(r.sub, 10.5 * s, "mono") + 10 * s : 0);
    if (lolli && t0Of(r)) return Math.max(main / 2, measure(t0Of(r)!.label, FS_VAL, "mono") / 2 + tagW) + 14 * s;
    return Math.max(main, t0LabelW(r)) + 14 * s;
  }));
  const sorted = sort === "none" ? rows : [...rows].sort((a, b) => {
    const va = a.value ?? (sort === "asc" ? Infinity : -Infinity), vb = b.value ?? (sort === "asc" ? Infinity : -Infinity);
    return sort === "asc" ? va - vb : vb - va;
  });
  const measured = sorted.filter((r) => r.value != null);
  const x0 = LABEL_W, plotW = Math.max(120, W - LABEL_W - VALUE_W);
  const ends = measured.flatMap((r) => { const t = t0Of(r); return [r.value!, r.hi ?? r.value!, r.lo ?? r.value!, ...(t ? [t.value, t.hi ?? t.value, t.lo ?? t.value] : [])]; });
  const dom = useMemo<[number, number]>(() => {
    if (domain) return domain;
    if (scale === "log") {
      const pos = ends.filter((v) => v > 0);
      if (!pos.length) return [0.01, 1];
      const mn = Math.min(...pos), mx = Math.max(...pos);
      return [10 ** Math.floor(Math.log10(mn)), 10 ** Math.ceil(Math.log10(mx) - 1e-9)];
    }
    const mx = Math.max(1e-9, ...ends);
    return [0, mx * 1.06];
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [domain, scale, ends.join("|")]);
  const X = (v: number) => {
    if (scale === "log") {
      const l0 = Math.log10(dom[0]), l1 = Math.log10(dom[1]);
      if (v <= 0) return x0;
      return x0 + Math.min(1, Math.max(0, (Math.log10(v) - l0) / (l1 - l0 || 1))) * plotW;
    }
    return x0 + Math.min(1, Math.max(0, (v - dom[0]) / (dom[1] - dom[0] || 1))) * plotW;
  };
  const ticks = axisTicks(scale, dom, density, plotW, (t) => measure(fmtTick(t), 11 * s, "mono") + 8 * s), grid = gridOn(density);
  const n = sorted.length, bottom = TOP + n * ROW, h = bottom + 46 * s;
  // the hatch tiles: one per measured row and, with paired bars, one per t = 0 figure in the tint
  const hatchItems = paired ? [...measured, ...measured.filter((r) => t0Of(r)).map((r) => ({ id: `${r.id}~t0`, color: T0_TINT(r.color) }))] : measured;
  // the "t = 0" tag after a t = 0 figure's label: small, muted, plain face
  const tag = (x: number, y: number) => (t0Tag ? <text x={x} y={y} fontSize={FS_TAG} fill="var(--ink-3)">{T0_TAG}</text> : null);
  // the two-entry key above the rows: the chart's own elements in ink (a bar and its lighter twin, or a filled and a hollow dot), the names in --ink-2
  const key = keyOn && (() => {
    const fs = 11 * s, sw = 10 * s, gap = 6 * s, item = 18 * s, ky = TOP0 * s, cy = ky + (KEY_ROW * s) / 2;
    const names = ["default sampling", "temperature 0"];
    const x1 = x0 + sw + gap + measure(names[0], fs, LEGEND_CLS) + item;
    return (
      <g className="pr-legend">
        {kind === "bar" ? (
          <>
            <rect x={x0} y={cy - 4 * s} width={sw} height={8 * s} rx={1.5} fill="var(--ink-2)" style={{ fillOpacity: "var(--bar-alpha)" }} />
            <rect x={x1} y={cy - 4 * s} width={sw} height={8 * s} rx={1.5} style={{ fill: T0_TINT("var(--ink-2)"), fillOpacity: "var(--bar-alpha)" }} />
          </>
        ) : (
          <>
            <circle cx={x0 + sw / 2} cy={cy} r={3.75 * s} fill="var(--ink-2)" />
            <circle cx={x1 + sw / 2} cy={cy} r={3.75 * s} fill="var(--panel)" stroke="var(--ink-2)" strokeWidth={1.5} style={{ strokeWidth: "calc(1.5px * var(--sw-mult, 1))" }} />
          </>
        )}
        <text x={x0 + sw + gap} y={cy + 4 * s} fontSize={fs} fill="var(--ink-2)" className={LEGEND_CLS}>{names[0]}</text>
        <text x={x1 + sw + gap} y={cy + 4 * s} fontSize={fs} fill="var(--ink-2)" className={LEGEND_CLS}>{names[1]}</text>
      </g>
    );
  })();
  return (
    <div ref={hostRef} style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
        <defs>
          <PlotBgPattern id={bgId} kind={bg} s={s} />
          <HatchDefs items={hatchItems} s={s} hatchId={hatchId} on={hatched} />
        </defs>
        {key}
        {bg !== "none" && n > 0 && <rect x={x0} y={TOP} width={plotW} height={bottom - TOP} fill={`url(#${bgId})`} />}
        {ticks.map(({ t, label }) => (
          <g key={t}>
            {grid && <line className="gl" x1={X(t)} x2={X(t)} y1={TOP} y2={bottom} stroke="var(--grid)" />}
            {label && <text x={X(t)} y={bottom + 16 * s} fontSize={11 * s} textAnchor="middle" fill="var(--ink-3)" className="mono">{fmtTick(t)}</text>}
          </g>
        ))}
        {sorted.map((r, i) => {
          const cy = TOP + i * ROW + ROW / 2;
          const nameX = logos ? 30 * s : LABEL_W - 14 * s;
          const label = labelOf(r);
          // clickable rows (onSelect): the row group becomes a button with a full-width hit rect behind it; without onSelect nothing is added
          const sel = onSelect ? selectable(onSelect, r.id, label) : {};
          const hit = onSelect ? <rect className="hit" x={0} y={cy - ROW / 2} width={W} height={ROW} fill="transparent" /> : null;
          if (r.value == null) {
            return (
              <g key={r.id} {...sel}>
                {hit}
                {glyphOf(r) && <g color="var(--ink-4)"><LogoGlyph model={r.id} cx={12 * s} cy={cy} size={14 * s} opacity={0.6} /></g>}
                <text x={nameX} y={cy + 4.5 * s} fontSize={12.5 * s} textAnchor={logos ? "start" : "end"} fill="var(--ink-4)" className="nm">{label}</text>
                <text x={x0 + 8 * s} y={cy + 4.5 * s} fontSize={11.5 * s} fill="var(--ink-4)">{r.empty ?? "not measured"}</text>
              </g>
            );
          }
          const v = r.value, xv = X(v);
          const lo = r.lo ?? null, hi = r.hi ?? null;
          const xlo = lo == null ? xv : X(lo), xhi = hi == null ? xv : X(hi);
          const end = Math.max(xv, xhi) + 9 * s;
          // the row's t = 0 figure, where the mode draws it: its x, whisker ends and label end
          const t = t0Of(r), xt = t ? X(t.value) : xv;
          const xtlo = t?.lo != null ? X(t.lo) : xt, xthi = t?.hi != null ? X(t.hi) : xt, tEnd = Math.max(xt, xthi) + 9 * s;
          // the bar's paint (FillMode): a zero-value bar is a 1.5 px stub at half the opacity; the edge is the outline modes' --box-stroke-w, or a hatched bar's hairline at the hatch opacity
          const alpha = hatched ? BAR_HATCH_ALPHA : "var(--bar-alpha)";
          const barFill = barMode === "outline" ? "none" : hatched ? `url(#${hatchId(r.id)})` : r.color;
          const barStyle: CSSProperties = { fillOpacity: barMode === "outline" ? undefined : v === 0 ? `calc(${alpha} * 0.5)` : alpha };
          if (outlined) barStyle.strokeWidth = OUTLINE_W;
          else if (hatched) { barStyle.strokeWidth = HATCHED_EDGE_W; barStyle.strokeOpacity = alpha; }
          // the t = 0 bar: the same Fill mode in the tint (its own hatch tile, its edge and outline in the tint too)
          const tint = T0_TINT(r.color);
          const t0Style: CSSProperties = { ...barStyle, fillOpacity: barMode === "outline" ? undefined : t?.value === 0 ? `calc(${alpha} * 0.5)` : alpha };
          if (!hatched && barMode !== "outline") t0Style.fill = tint;
          const t0Fill = barMode === "outline" ? "none" : hatched ? `url(#${t0HatchId(r.id)})` : undefined;
          // paired rows: two bars of 9 s, 1 s either side of the centre line; a row without a t = 0 figure keeps its one 12 s bar on the centre line
          const two = paired && !!t, barH = two ? 9 * s : 12 * s, yA = two ? cy - 10 * s : cy - 6 * s, yB = cy + 1 * s;
          const cA = two ? cy - 5.5 * s : cy, cB = cy + 5.5 * s;
          const whisker = (a: number, b: number, y: number) => (
            <>
              {/* over a hatched bar the whisker sits on a panel-colour halo, so its ink line is not lost among the hatch lines */}
              {hatched && (
                <g stroke="var(--panel)" strokeWidth={3} strokeLinecap="round" style={SW(3)}>
                  <line x1={a} x2={b} y1={y} y2={y} />
                  <line x1={a} x2={a} y1={y - 4 * s} y2={y + 4 * s} />
                  <line x1={b} x2={b} y1={y - 4 * s} y2={y + 4 * s} />
                </g>
              )}
              <g stroke="var(--ink)" strokeWidth={1} style={{ ...SW(1), opacity: "var(--op-whisker, 0.65)" }}>
                <line x1={a} x2={b} y1={y} y2={y} />
                <line x1={a} x2={a} y1={y - 4 * s} y2={y + 4 * s} />
                <line x1={b} x2={b} y1={y - 4 * s} y2={y + 4 * s} />
              </g>
            </>
          );
          // the lollipop: the labels sit above the filled dot and below the hollow one, centred, kept clear of the axis
          const centred = (x: number, w: number) => Math.max(x, x0 + w / 2 + 2 * s);
          const lw = measure(r.label, FS_VAL, "mono"), tlw = t ? measure(t.label, FS_VAL, "mono") : 0;
          const lx = centred(xv, lw), tlx = centred(xt, tlw);
          return (
            <g key={r.id} {...sel}>
              {hit}
              {glyphOf(r) && <g color="var(--ink-2)"><LogoGlyph model={r.id} cx={12 * s} cy={cy} size={14 * s} /></g>}
              <text x={nameX} y={cy + 4.5 * s} fontSize={12.5 * s} textAnchor={logos ? "start" : "end"} fill="var(--ink-2)" className="nm" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
              {kind === "bar" ? (
                <>
                  <rect x={x0} y={yA} width={Math.max(1.5, xv - x0)} height={barH} fill={barFill} rx={1.5} stroke={outlined || hatched ? r.color : undefined} style={barStyle} />
                  {(lo != null || hi != null) && xhi - xlo > 0.5 && whisker(xlo, xhi, cA)}
                  {two && (
                    <>
                      <rect x={x0} y={yB} width={Math.max(1.5, xt - x0)} height={barH} fill={t0Fill} rx={1.5} stroke={outlined || hatched ? tint : undefined} style={t0Style} />
                      {(t!.lo != null || t!.hi != null) && xthi - xtlo > 0.5 && whisker(xtlo, xthi, cB)}
                    </>
                  )}
                  <text x={end} y={cA + 4 * s} fontSize={FS_VAL} fill="var(--ink)" className="mono">{r.label}</text>
                  {r.sub && <text x={end + lw + 10 * s} y={cA + 4 * s} fontSize={10.5 * s} fill="var(--ink-3)" className="mono">{r.sub}</text>}
                  {two && (
                    <>
                      <text x={tEnd} y={cB + 4 * s} fontSize={FS_VAL} fill="var(--ink)" className="mono">{t!.label}</text>
                      {tag(tEnd + tlw + TAG_GAP, cB + 4 * s)}
                    </>
                  )}
                </>
              ) : lolli ? (
                <>
                  {/* the stem: a faint line from the axis to the farther dot; then the segment between the two, the filled mark and the hollow dot */}
                  <line x1={x0} x2={Math.max(xv, xt)} y1={cy} y2={cy} stroke="var(--ink-4)" strokeWidth={1} strokeOpacity={0.4} style={SW(1)} />
                  {t && Math.abs(xt - xv) > 0.5 && <line x1={xv} x2={xt} y1={cy} y2={cy} stroke={r.color} strokeWidth={1.75} strokeLinecap="round" style={{ strokeWidth: T0_STROKE_W }} />}
                  <Mark shape={mark} cx={xv} cy={cy} r={4.5} color={r.color} jev={isJev(r.id)} />
                  {t && (
                    <g transform={`translate(${xt} ${cy})`}>
                      <circle r={4.5} fill="var(--panel)" stroke={r.color} strokeWidth={1.75} style={{ transform: `scale(${userScale(isJev(r.id))})`, transformOrigin: "0px 0px", r: "calc(4.5px + var(--r-add, 0px))", strokeWidth: T0_STROKE_W } as CSSProperties} />
                    </g>
                  )}
                  {t ? (
                    <>
                      <text x={lx} y={cy - 9 * s} fontSize={FS_VAL} textAnchor="middle" fill="var(--ink)" className="mono">{r.label}</text>
                      {r.sub && <text x={lx + lw / 2 + 8 * s} y={cy - 9 * s} fontSize={10.5 * s} fill="var(--ink-3)" className="mono">{r.sub}</text>}
                      <text x={tlx} y={cy + 17 * s} fontSize={FS_VAL} textAnchor="middle" fill="var(--ink)" className="mono">{t.label}</text>
                      {tag(tlx + tlw / 2 + TAG_GAP, cy + 17 * s)}
                    </>
                  ) : (
                    <>
                      <text x={xv + 9 * s} y={cy + 4.5 * s} fontSize={FS_VAL} fill="var(--ink)" className="mono">{r.label}</text>
                      {r.sub && <text x={xv + 9 * s + lw + 10 * s} y={cy + 4.5 * s} fontSize={10.5 * s} fill="var(--ink-3)" className="mono">{r.sub}</text>}
                    </>
                  )}
                </>
              ) : (
                <>
                  {xhi - xlo > 0.5 && <line x1={xlo} x2={xhi} y1={cy} y2={cy} stroke={r.color} strokeWidth={1.75} style={SW(1.75)} />}
                  <Mark shape={mark} cx={xv} cy={cy} r={4.5} color={r.color} jev={isJev(r.id)} />
                  <text x={end} y={cy + 4.5 * s} fontSize={FS_VAL} fill="var(--ink)" className="mono">{r.label}</text>
                  {r.sub && <text x={end + lw + 10 * s} y={cy + 4.5 * s} fontSize={10.5 * s} fill="var(--ink-3)" className="mono">{r.sub}</text>}
                </>
              )}
            </g>
          );
        })}
        <g stroke="var(--axis)" style={SW(1)}>
          <line x1={x0} x2={x0} y1={TOP} y2={bottom} />
          <line x1={x0} x2={x0 + plotW} y1={bottom} y2={bottom} />
        </g>
        <text x={x0} y={bottom + 36 * s} fontSize={11.5 * s} fill="var(--ink-3)" className="ax">{axis}</text>
        {n === 0 && <text x={W / 2} y={30} textAnchor="middle" fontSize={13 * s} fill="var(--ink-4)">Select at least one model.</text>}
        {probes}
      </svg>
    </div>
  );
}

/** A point of the cost-against-recall scatter: cost on a log x axis, recall with its 95% interval as a vertical whisker. */
export type StudioScatterPt = { id: string; name: string; color: string; x: number | null; y: CI; decider?: boolean; subset?: string | null };

const PR = 24, PT = 18;

/** Cost (log x) against recall (y, 95% whisker). Sized to the host's box like PRScatter's `fill` mode (host must be positioned). `logos`, `leaders`, `labels`, `mark`, `markSize`, `jevMarkSize` and `groups` as on PRScatter: which items get their vendor glyph as the mark; a hairline from a displaced label to its mark; a legend row at the top instead of point labels; the point shape, and the Mark size and Jev mark size multipliers the label placement allows for; the groups the legend lists (the points then keep their labels). `onSelect` (AppB.tsx) makes each mark a button opening the details modal for its id; the studio passes none. `ticks` (the studio's Gridlines control) is the tick density of both axes (axisTicks: x log, y linear). */
export function StudioScatter({ pts, xLabel, yLabel = "Recall", fmtX, logos: logosIn, emptyText = "Select at least one model.", textScale = 1, leaders = false, labels: labelsMode = "beside", mark = "dot", markSize = 1, jevMarkSize = markSize, onSelect, bg = "none", groups, ticks: density = "normal" }: { pts: StudioScatterPt[]; xLabel: string; yLabel?: string; fmtX: (v: number) => string; logos?: boolean | LogosMode; emptyText?: string; textScale?: number; leaders?: boolean; labels?: LabelsMode; mark?: MarkShape; markSize?: number; jevMarkSize?: number; onSelect?: (id: string) => void; bg?: PlotBg; groups?: (id: string) => LegendGroup; ticks?: TickDensity }) {
  const hostRef = useRef<HTMLDivElement>(null);
  const logos = logosMode(logosIn, true);
  const hasLogo = (p: StudioScatterPt) => logoShown(logos, p.id) && !!logoFor(p.id);
  const bgId = useBgId();
  const sz = useSize(hostRef, { w: 900, h: 520 });
  const W = sz.w, H = Math.max(300, sz.h);
  const s = textScale;
  const { measure, probes } = useTextMeasure([LEGEND_CLS, NAME_CLS, "mono"]);
  const drawn = pts.filter((p): p is StudioScatterPt & { x: number; y: NonNullable<CI> } => p.x != null && p.x > 0 && !!p.y);
  const xs = drawn.map((p) => p.x);
  const xd: [number, number] = xs.length ? [10 ** Math.floor(Math.log10(Math.min(...xs))), 10 ** Math.ceil(Math.log10(Math.max(...xs)) - 1e-9)] : [0.01, 100];
  const ylo = Math.min(1, ...drawn.map((p) => p.y[1])), yhi = Math.max(0, ...drawn.map((p) => p.y[2]));
  const pad = Math.max(0.02, (yhi - ylo) * 0.12);
  const yd: [number, number] = drawn.length ? [Math.max(0, ylo - pad), Math.min(1, yhi + pad)] : [0, 1];
  const yTickLabel = (t: number) => `${+(t * 100).toFixed(1)}%`;
  // the left and bottom margins hold the y tick labels and the axis titles, sized from them and the text scale (PRScatter.tsx axisMargins)
  const { PL, PB, titleX } = axisMargins(linTicks(yd[0], yd[1], linTarget(density)).map(yTickLabel), s);
  // the legend lists the items, or the groups they fall into (`groups`; PRScatter.tsx LegendGroup), in which case the points keep their labels
  const grouped = labelsMode === "legend" && groups ? legendGroups(drawn.map((p) => p.id), groups) : null;
  const legendItems = grouped ?? drawn.map((p) => ({ id: p.id, name: `${p.name}${p.subset ? " *" : ""}`, color: p.color, sample: p.id }));
  const pointLabels = labelsMode === "beside" || !!grouped;
  const LEGEND_Y = 4, legendH = labelsMode === "legend" ? legendLayout(legendItems.map((i) => i.name), s, PL, W - PR, measure).height : 0;
  const top = labelsMode === "legend" ? Math.max(PT, LEGEND_Y + legendH + LEGEND_GAP * s) : PT;
  // ticks at the density (axisTicks): x log across the plot width, y linear down its height (a label there is a line high)
  const xt = axisTicks("log", xd, density, W - PL - PR, (t) => measure(fmtX(t), 10.5 * s, "mono") + 8 * s), yt = axisTicks("linear", yd, density, H - top - PB, () => 10.5 * s * 1.4);
  const grid = gridOn(density);
  const X = (v: number) => PL + ((Math.log10(v) - Math.log10(xd[0])) / (Math.log10(xd[1]) - Math.log10(xd[0]) || 1)) * (W - PL - PR);
  const Y = (v: number) => top + (1 - (v - yd[0]) / (yd[1] - yd[0] || 1)) * (H - top - PB);
  // per item: its size factor (the Jev mark size for a Jev row, else the Mark size), the mark radius as drawn (glyph half-size or dot radius × that) and the
  // beside-the-mark label offset, grown with the mark (PRScatter does the same); the placement keeps clear of each dot by its own grown pad
  const sizeOf = (p: StudioScatterPt) => (isJev(p.id) ? jevMarkSize : markSize);
  const markR = (p: StudioScatterPt) => (hasLogo(p) ? 6.5 : 4) * sizeOf(p);
  const growOf = (p: StudioScatterPt) => Math.max(0, 6.5 * sizeOf(p) - 6.5), O = (p: StudioScatterPt) => 11 * s + growOf(p);
  // labels: right of the mark, else left, above, below; skipped when nothing fits
  const placed: { x: number; y: number; w: number; h: number }[] = [];
  const dots = drawn.map((p) => ({ x: X(p.x), y: Y(p.y[0]), avoid: 6 + growOf(p) }));
  const clash = (a: { x: number; y: number; w: number; h: number }) => placed.some((b) => a.x < b.x + b.w + 2 && a.x + a.w + 2 > b.x && a.y < b.y + b.h + 1 && a.y + a.h + 1 > b.y) || dots.some((d) => d.x > a.x - d.avoid && d.x < a.x + a.w + d.avoid && d.y > a.y - d.avoid && d.y < a.y + a.h + d.avoid);
  const labels = drawn.map((p, i) => {
    if (!pointLabels) return null;
    const text = `${p.name}${p.subset ? " *" : ""}`, w = measure(text, 11.5 * s, NAME_CLS) + 4, h = 14 * s, o = O(p), { x, y } = dots[i];
    const cands = [{ x: x + o, y: y - h / 2 }, { x: x - o - w, y: y - h / 2 }, { x: x - w / 2, y: y - 14 * s - h }, { x: x - w / 2, y: y + 14 * s }];
    const c = cands.find((cc) => cc.x >= PL && cc.x + w <= W - 2 && cc.y >= 0 && !clash({ ...cc, w, h }));
    if (c) placed.push({ ...c, w, h });
    return c ? { ...c, w, h, text } : null;
  });
  return (
    <div ref={hostRef} style={{ position: "absolute", inset: 0 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ display: "block", overflow: "visible" }}>
        <defs><PlotBgPattern id={bgId} kind={bg} s={s} /></defs>
        {bg !== "none" && <rect x={PL} y={top} width={W - PR - PL} height={H - PB - top} fill={`url(#${bgId})`} />}
        {xt.map(({ t, label }) => (
          <g key={`x${t}`}>
            {grid && <line className="gl" x1={X(t)} x2={X(t)} y1={top} y2={H - PB} stroke="var(--grid-x, var(--grid))" />}
            {label && <text x={X(t)} y={H - PB + 16 * s} fontSize={10.5 * s} textAnchor="middle" fill="var(--ink-3)" className="mono">{fmtX(t)}</text>}
          </g>
        ))}
        {yt.map(({ t, label }) => (
          <g key={`y${t}`}>
            {grid && <line className="gl" x1={PL} x2={W - PR} y1={Y(t)} y2={Y(t)} stroke="var(--grid)" />}
            {label && <text x={PL - 8} y={Y(t) + 3.5 * s} fontSize={10.5 * s} textAnchor="end" fill="var(--ink-3)" className="mono">{yTickLabel(t)}</text>}
          </g>
        ))}
        <g stroke="var(--axis)" style={SW(1)}>
          <line x1={PL} x2={W - PR} y1={H - PB} y2={H - PB} />
          <line x1={PL} x2={PL} y1={top} y2={H - PB} stroke="var(--axis-y, var(--axis))" />
        </g>
        <text x={(PL + W - PR) / 2} y={H - 10 * s} fontSize={12 * s} textAnchor="middle" fill="var(--ink-2)" className="ax">{xLabel}</text>
        <text x={titleX} y={(top + H - PB) / 2} fontSize={12 * s} textAnchor="middle" fill="var(--ink-2)" className="ax" transform={`rotate(-90 ${titleX} ${(top + H - PB) / 2})`}>{yLabel}</text>
        {labelsMode === "legend" && <Legend items={legendItems} s={s} x0={PL} x1={W - PR} y={LEGEND_Y} mark={(id) => legendSwatch(logos, mark)(legendItems.find((i) => i.id === id)?.sample ?? id)} measure={measure} />}
        {probes}
        {/* leader lines: before every whisker, mark and label, so none crosses them */}
        {leaders && pointLabels && drawn.map((p, i) => {
          const l = labels[i];
          if (!l) return null;
          const { x, y } = dots[i];
          const ld = leaderFor({ x: l.x - x, y: l.y - y, w: l.w, h: l.h }, markR(p), O(p));
          return ld && <line key={`l${p.id}`} className="pr-leader" x1={x + ld.x1} y1={y + ld.y1} x2={x + ld.x2} y2={y + ld.y2} stroke={p.color} strokeOpacity={0.7} style={LEADER_STYLE} />;
        })}
        {drawn.map((p, i) => {
          const x = X(p.x), y = Y(p.y[0]), y1 = Y(p.y[2]), y2 = Y(p.y[1]);
          const l = labels[i];
          return (
            <g key={p.id} {...(onSelect ? selectable(onSelect, p.id, `${p.name}${p.subset ? " *" : ""}`) : {})}>
              <g stroke={p.color} strokeWidth={1.5} style={{ ...SW(1.5), opacity: "var(--op-whisker, 0.75)" }}>
                <line x1={x} x2={x} y1={y1} y2={y2} />
                <line x1={x - 4} x2={x + 4} y1={y1} y2={y1} />
                <line x1={x - 4} x2={x + 4} y1={y2} y2={y2} />
              </g>
              {/* the glyph is drawn at the origin of a group translated to the point and scaled about 0 0 (PRScatter.tsx Mark): a `transform-origin: x y` in px drifts on a zoomed WebKit page */}
              {hasLogo(p) ? <g transform={`translate(${x} ${y})`}><g color={p.color} style={{ transform: glyphScale(isJev(p.id)) }}><LogoGlyph model={p.id} cx={0} cy={0} size={13} /></g></g> : <Mark shape={mark} cx={x} cy={y} r={4} color={p.color} jev={isJev(p.id)} />}
              {l && <text x={l.x} y={l.y + 10.5 * s} fontSize={11.5 * s} fill="var(--ink)" className="nm" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 2.5, strokeLinejoin: "round" }}>{l.text}</text>}
            </g>
          );
        })}
        {drawn.length === 0 && <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={13 * s} fill="var(--ink-4)">{emptyText}</text>}
      </svg>
    </div>
  );
}
