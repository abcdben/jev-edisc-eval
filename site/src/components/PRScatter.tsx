import { useMemo, type ReactNode } from "react";
import { fmtCI, type CI } from "../data";
import { Logo, LogoGlyph, logoFor } from "../logos";
import { CLICK_HINT, TipBox, fadeStyle, selectable, usePresence, usePulseWindow, useSize, useTip, useTween, type TipContent } from "./ui";
import { hoverable } from "./hover";

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

function niceTicks(lo: number, hi: number): number[] {
  const span = hi - lo;
  const step = span > 0.6 ? 0.2 : span > 0.3 ? 0.1 : span > 0.12 ? 0.05 : span > 0.06 ? 0.02 : 0.01;
  const out: number[] = [];
  for (let t = Math.ceil(lo / step) * step; t <= hi + 1e-9; t += step) out.push(Math.round(t * 1000) / 1000);
  return out;
}

/** Recall (x) against precision (y). Each item is a dot at the point estimate inside a box spanning both 95% intervals. */
/** `fill`: size to the host's box (host must be positioned, e.g. an absolutely-filled flex child) instead of a fixed height. */
/** `onSelect` makes each mark (dot, label and interval box) a button: click, Enter or Space. */
/** `highlight` (cross-chart hover, see hover.tsx) gives that item a subtle emphasis: a deeper box fill, its label forced visible and the item drawn on top; the mark itself is unchanged. `onHover` reports the mark or box under the pointer or keyboard focus. */
/** Motion (ui.tsx): marks, boxes and labels ease to their new place over 320 ms when the corpus, scope, gold or zoom changes; items fade in and out over 150 ms. */
/** How long the decider boxes breathe after the plot loads or its points change: PULSE_CYCLES cycles of the styles.css box-breathe animation (keep in step with `.pr-box.pulse`). */
const PULSE_CYCLES = 2, PULSE_CYCLE_MS = 650;

/** `pulse` lets the interval boxes of decider items (`decider: true`) breathe for a few cycles whenever the plot loads or its set of points changes: a fill-opacity cycle (styles.css .pr-box.pulse) on the shaded box only, never the mark or label; a highlighted box keeps its steady deeper fill instead. Off by default and under prefers-reduced-motion. */
/** `domain` (the screenshot studio) fixes both axes to explicit 0–1 ranges, overriding `zoom`. */
/** `textScale` (the studio's Text control; 1 on the site) multiplies every font size, the label-placement estimates and the margins that hold tick labels. Axis stroke width, dot radius and the vendor-glyph size read the --sw-mult / --r-add / --mark-scale CSS variables (styles.css, the studio's high-contrast block; unset on the site). */
/** `leaders` (the studio's Leaders control; off on the site) draws a hairline from each displaced label back to its mark (leaderFor), under every mark and label. */
export type PRDomain = { x: [number, number]; y: [number, number] };
export function PRScatter({ items, zoom, domain, xLabel = "Recall", yLabel = "Precision", emptyText, logos = false, height = 520, fill = false, onSelect, highlight, onHover, pulse = false, textScale = 1, leaders = false }: { items: PRItem[]; zoom: boolean; domain?: PRDomain; xLabel?: string; yLabel?: string; emptyText?: string; logos?: boolean; height?: number; fill?: boolean; onSelect?: (item: PRItem) => void; highlight?: string | null; onHover?: (id: string | null) => void; pulse?: boolean; textScale?: number; leaders?: boolean }) {
  const { tip, show, hide, hostRef } = useTip();
  const pickMark = onSelect && ((it: PRItem) => { hide(); onSelect(it); });
  const sz = useSize(hostRef, { w: 760, h: height });
  const W = sz.w, H = fill ? Math.max(300, sz.h) : height;
  const s = textScale;
  type Pt = PRItem & { recall: NonNullable<CI>; precision: NonNullable<CI> };
  const hasPt = (it: PRItem): it is Pt => !!it.recall && !!it.precision;
  const pts = items.filter(hasPt);
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
      x: pad(Math.min(...pts.map((p) => p.recall[1])), Math.max(...pts.map((p) => p.recall[2]))),
      y: pad(Math.min(...pts.map((p) => p.precision[1])), Math.max(...pts.map((p) => p.precision[2]))),
    };
  }, [pts, zoom, domain]);

  const xt = niceTicks(dom.x[0], dom.x[1]), yt = niceTicks(dom.y[0], dom.y[1]);
  const tickLabel = (t: number) => `${Math.round(t * 100)}%`;
  const { PL, PB, titleX } = axisMargins(yt.map(tickLabel), s);
  const X = (v: number) => PL + ((v - dom.x[0]) / (dom.x[1] - dom.x[0] || 1)) * (W - PL - PR);
  const Y = (v: number) => PT + (1 - (v - dom.y[0]) / (dom.y[1] - dom.y[0] || 1)) * (H - PT - PB);

  // label placement: try several offsets; avoid other dots and labels; give up (hover only) when nothing fits
  const labels = useMemo(() => {
    const placed: { x: number; y: number; w: number; h: number }[] = [];
    const dots = pts.map((p) => ({ x: X(p.recall[0]), y: Y(p.precision[0]) }));
    const overlaps = (a: { x: number; y: number; w: number; h: number }) =>
      placed.some((b) => a.x < b.x + b.w + 2 && a.x + a.w + 2 > b.x && a.y < b.y + b.h + 1 && a.y + a.h + 1 > b.y) ||
      dots.some((d) => d.x > a.x - 5 && d.x < a.x + a.w + 5 && d.y > a.y - 5 && d.y < a.y + a.h + 5);
    return pts.map((p, i) => {
      const w = p.name.length * 6.3 * s + 4, h = 13 * s, o = 9 * s, d = 22 * s;
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
      return { ...c, w, h, text: p.name + (p.subset ? " *" : "") };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pts, dom, W, H, s]);

  // Where everything is heading, keyed by item so a move is continuous across re-sorts; `geo` is where it is drawn this frame.
  const target: Record<string, number> = {};
  for (const p of drawn) {
    const x0 = X(p.recall[1]), x1 = X(p.recall[2]), y0 = Y(p.precision[2]), y1 = Y(p.precision[1]);
    target[`${p.id}:x`] = X(p.recall[0]); target[`${p.id}:y`] = Y(p.precision[0]);
    target[`${p.id}:x0`] = x0; target[`${p.id}:y0`] = y0; target[`${p.id}:w`] = Math.max(1, x1 - x0); target[`${p.id}:h`] = Math.max(1, y1 - y0);
  }
  const geo = useTween(target, undefined, undefined, `${W}x${H}`);
  const g = (id: string, k: string) => geo[`${id}:${k}`] ?? target[`${id}:${k}`];

  // Mark sizes are uniform.
  const glyph = (_p: PRItem) => 12;

  return (
    <div ref={hostRef} data-tip-host style={fill ? { position: "absolute", inset: 0 } : { position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width={W} height={H} style={{ display: "block", overflow: "visible" }}>
        {/* dot-matrix plot background, then the tick grid on top */}
        <defs>
          <pattern id="dotgrid" width={8} height={8} patternUnits="userSpaceOnUse">
            <circle cx={1} cy={1} r={0.7} fill="var(--dots)" />
          </pattern>
        </defs>
        <rect x={PL} y={PT} width={W - PR - PL} height={H - PB - PT} fill="url(#dotgrid)" />
        {xt.map((t) => (
          <g key={`x${t}`}>
            <line className="gl" x1={X(t)} x2={X(t)} y1={PT} y2={H - PB} stroke="var(--grid)" />
            <text x={X(t)} y={H - PB + 16 * s} fontSize={TICK_FS * s} textAnchor="middle" fill="var(--ink-3)" className="mono">{tickLabel(t)}</text>
          </g>
        ))}
        {yt.map((t) => (
          <g key={`y${t}`}>
            <line className="gl" x1={PL} x2={W - PR} y1={Y(t)} y2={Y(t)} stroke="var(--grid)" />
            <text x={PL - 8} y={Y(t) + 3.5 * s} fontSize={TICK_FS * s} textAnchor="end" fill="var(--ink-3)" className="mono">{tickLabel(t)}</text>
          </g>
        ))}
        <g stroke="var(--axis)" style={{ strokeWidth: "var(--sw-mult, 1)" }}>
          <line x1={PL} x2={W - PR} y1={H - PB} y2={H - PB} />
          <line x1={PL} x2={PL} y1={PT} y2={H - PB} />
        </g>
        <text x={(PL + W - PR) / 2} y={H - 10 * s} fontSize={TITLE_FS * s} textAnchor="middle" fill="var(--ink-2)" className="ax">{xLabel}</text>
        <text x={titleX} y={(PT + H - PB) / 2} fontSize={TITLE_FS * s} textAnchor="middle" fill="var(--ink-2)" className="ax" transform={`rotate(-90 ${titleX} ${(PT + H - PB) / 2})`}>{yLabel}</text>

        {/* CI boxes first so dots sit on top; every box is the same stroke-less shade, the highlighted one a little deeper */}
        {drawn.map((p) => {
          const mark = { kind: "mark" as const, x: X(p.recall[0]), y: Y(p.precision[0]), r: 9 };
          return (
            <g key={`b${p.id}`} className="fd" style={fadeStyle(stateOf[p.id] ?? "exit")}>{/* fade in / out (ui.tsx usePresence) */}
            <g {...hoverable(onHover, p.id)}>{/* cross-chart hover (hover.tsx) wraps the tooltip group */}
            <g onMouseMove={(e) => show(e, mark, prTip(p, logos ? <Logo model={p.id} size={12} /> : undefined))} onMouseLeave={hide} {...selectable(pickMark, p, p.name)} tabIndex={-1}>
              {/* the pulse class is dropped while this box is highlighted, so the deeper hover fill is steady and wins */}
              {/* `--box-stroke` (0 on the site) lets a studio style preset draw the box as a hairline outline in the item's colour */}
              <rect key={`${p.id}:${sig}`} className={pulsing && p.decider && hl !== p.id ? "pr-box pulse" : "pr-box"} x={g(p.id, "x0")} y={g(p.id, "y0")} width={g(p.id, "w")} height={g(p.id, "h")} fill={p.color} stroke={p.color} strokeWidth={0.75} style={{ fillOpacity: hl === p.id ? 0.35 : "var(--box-alpha)", strokeOpacity: "var(--box-stroke, 0)", transition: "fill-opacity 120ms" }} rx={1} />
            </g>
            </g>
            </g>
          );
        })}
        {/* leader lines (studio): drawn after every box and before every mark and label, so none crosses a mark or a label */}
        {leaders && drawn.map((p) => {
          const li = pts.indexOf(p), l0 = li >= 0 ? labels[li] : null;
          if (!l0) return null;
          const tx = X(p.recall[0]), ty = Y(p.precision[0]);
          const ld = leaderFor({ x: l0.x - tx, y: l0.y - ty, w: l0.w, h: l0.h }, logos && logoFor(p.id) ? glyph(p) / 2 : 3.2, 9 * s);
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
          const tx = X(p.recall[0]), ty = Y(p.precision[0]), x = g(p.id, "x"), y = g(p.id, "y");
          const li = pts.indexOf(p), l0 = li >= 0 ? labels[li] : null;
          const l = l0 ? { x: l0.x - tx, y: l0.y - ty, text: l0.text } : hl === p.id ? { x: 9 * s, y: -6.5 * s, text: p.name + (p.subset ? " *" : "") } : null;
          const hasLogo = logos && logoFor(p.id);
          return (
            <g key={`d${p.id}`} className="fd" style={fadeStyle(stateOf[p.id] ?? "exit")}>{/* fade in / out (ui.tsx usePresence) */}
            <g {...hoverable(onHover, p.id)}>{/* cross-chart hover (hover.tsx) wraps the tooltip group */}
            <g transform={`translate(${x} ${y})`} onMouseMove={(e) => show(e, { kind: "mark", x: tx, y: ty, r: 9 }, prTip(p, logos ? <Logo model={p.id} size={12} /> : undefined))} onMouseLeave={hide} {...selectable(pickMark, p, p.name)}>
              <circle className="hit" r={9} fill="transparent" />
              {hasLogo ? (
                <g color={p.color} style={{ transform: "scale(var(--mark-scale, 1))" }}><LogoGlyph model={p.id} cx={0} cy={0} size={glyph(p)} /></g>
              ) : (
                <circle r={3.2} fill={p.color} style={{ r: "calc(3.2px + var(--r-add, 0px))" } as React.CSSProperties} />
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
        {labels.some((l) => !l) && <text x={W - PR} y={PT - 6} fontSize={10.5 * s} textAnchor="end" fill="var(--ink-4)">some labels hidden where marks overlap; hover to identify</text>}
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
