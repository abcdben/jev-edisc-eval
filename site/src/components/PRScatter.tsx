import { useMemo, type ReactNode } from "react";
import { fmtCI, type CI } from "../data";
import { Logo, LogoGlyph, logoFor } from "../logos";
import { CLICK_HINT, TipBox, fadeStyle, selectable, usePresence, usePulseWindow, useSize, useTip, useTween, type TipContent } from "./ui";
import { hoverable } from "./hover";

/** `sub` is the one secondary line of the hover tooltip (what the point was scored on); the full figures live in the details modal. `decider` sets the row's name heavier in the tables; on the map it only selects which interval boxes breathe when `pulse` is on (the mark and label are drawn like every other). `emphasis` (Compare models: the decision-model rows, Jev and Laya) tints the row in the ranked table (ui.tsx RowTint); the map ignores it. */
export type PRItem = { id: string; name: string; color: string; recall: CI; precision: CI; dashed?: boolean; subset?: string | null; sub?: string; decider?: boolean; emphasis?: boolean };

/** The compact hover tooltip of a recall/precision mark or row: both intervals and the scoring line. */
export const prTip = (p: PRItem, icon?: ReactNode): TipContent => ({ title: p.name, color: p.color, icon, lines: [["Recall", fmtCI(p.recall)], ["Precision", fmtCI(p.precision)]], sub: p.sub });

const PL = 56, PR = 20, PT = 18, PB = 48;

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
export type PRDomain = { x: [number, number]; y: [number, number] };
export function PRScatter({ items, zoom, domain, xLabel = "Recall", yLabel = "Precision", emptyText, logos = false, height = 520, fill = false, onSelect, highlight, onHover, pulse = false }: { items: PRItem[]; zoom: boolean; domain?: PRDomain; xLabel?: string; yLabel?: string; emptyText?: string; logos?: boolean; height?: number; fill?: boolean; onSelect?: (item: PRItem) => void; highlight?: string | null; onHover?: (id: string | null) => void; pulse?: boolean }) {
  const { tip, show, hide, hostRef } = useTip();
  const pickMark = onSelect && ((it: PRItem) => { hide(); onSelect(it); });
  const sz = useSize(hostRef, { w: 760, h: height });
  const W = sz.w, H = fill ? Math.max(300, sz.h) : height;
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

  const X = (v: number) => PL + ((v - dom.x[0]) / (dom.x[1] - dom.x[0] || 1)) * (W - PL - PR);
  const Y = (v: number) => PT + (1 - (v - dom.y[0]) / (dom.y[1] - dom.y[0] || 1)) * (H - PT - PB);
  const xt = niceTicks(dom.x[0], dom.x[1]), yt = niceTicks(dom.y[0], dom.y[1]);

  // label placement: try several offsets; avoid other dots and labels; give up (hover only) when nothing fits
  const labels = useMemo(() => {
    const placed: { x: number; y: number; w: number; h: number }[] = [];
    const dots = pts.map((p) => ({ x: X(p.recall[0]), y: Y(p.precision[0]) }));
    const overlaps = (a: { x: number; y: number; w: number; h: number }) =>
      placed.some((b) => a.x < b.x + b.w + 2 && a.x + a.w + 2 > b.x && a.y < b.y + b.h + 1 && a.y + a.h + 1 > b.y) ||
      dots.some((d) => d.x > a.x - 5 && d.x < a.x + a.w + 5 && d.y > a.y - 5 && d.y < a.y + a.h + 5);
    return pts.map((p, i) => {
      const w = p.name.length * 6.3 + 4, h = 13;
      const { x, y } = dots[i];
      const cands: { x: number; y: number }[] = [
        { x: x + 9, y: y - h / 2 }, { x: x - 9 - w, y: y - h / 2 },
        { x: x - w / 2, y: y - 11 - h }, { x: x - w / 2, y: y + 11 },
        { x: x + 8, y: y - h - 4 }, { x: x + 8, y: y + 4 }, { x: x - 8 - w, y: y - h - 4 }, { x: x - 8 - w, y: y + 4 },
        { x: x + 9, y: y - h / 2 - 22 }, { x: x + 9, y: y - h / 2 + 22 }, { x: x - 9 - w, y: y - h / 2 - 22 }, { x: x - 9 - w, y: y - h / 2 + 22 },
      ];
      const c = cands.find((cc) => cc.x >= PL && cc.x + w <= W - 2 && cc.y >= 0 && !overlaps({ ...cc, w, h }));
      if (!c) return null;
      placed.push({ ...c, w, h });
      return { ...c, w, text: p.name + (p.subset ? " *" : "") };
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pts, dom, W]);

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
            <line x1={X(t)} x2={X(t)} y1={PT} y2={H - PB} stroke="var(--grid)" />
            <text x={X(t)} y={H - PB + 16} fontSize={10.5} textAnchor="middle" fill="var(--ink-3)" className="mono">{Math.round(t * 100)}%</text>
          </g>
        ))}
        {yt.map((t) => (
          <g key={`y${t}`}>
            <line x1={PL} x2={W - PR} y1={Y(t)} y2={Y(t)} stroke="var(--grid)" />
            <text x={PL - 8} y={Y(t) + 3.5} fontSize={10.5} textAnchor="end" fill="var(--ink-3)" className="mono">{Math.round(t * 100)}%</text>
          </g>
        ))}
        <line x1={PL} x2={W - PR} y1={H - PB} y2={H - PB} stroke="var(--axis)" />
        <line x1={PL} x2={PL} y1={PT} y2={H - PB} stroke="var(--axis)" />
        <text x={(PL + W - PR) / 2} y={H - 10} fontSize={12} textAnchor="middle" fill="var(--ink-2)">{xLabel}</text>
        <text x={14} y={(PT + H - PB) / 2} fontSize={12} textAnchor="middle" fill="var(--ink-2)" transform={`rotate(-90 14 ${(PT + H - PB) / 2})`}>{yLabel}</text>

        {/* CI boxes first so dots sit on top; every box is the same stroke-less shade, the highlighted one a little deeper */}
        {drawn.map((p) => {
          const mark = { kind: "mark" as const, x: X(p.recall[0]), y: Y(p.precision[0]), r: 9 };
          return (
            <g key={`b${p.id}`} className="fd" style={fadeStyle(stateOf[p.id] ?? "exit")}>{/* fade in / out (ui.tsx usePresence) */}
            <g {...hoverable(onHover, p.id)}>{/* cross-chart hover (hover.tsx) wraps the tooltip group */}
            <g onMouseMove={(e) => show(e, mark, prTip(p, logos ? <Logo model={p.id} size={12} /> : undefined))} onMouseLeave={hide} {...selectable(pickMark, p, p.name)} tabIndex={-1}>
              {/* the pulse class is dropped while this box is highlighted, so the deeper hover fill is steady and wins */}
              <rect key={`${p.id}:${sig}`} className={pulsing && p.decider && hl !== p.id ? "pr-box pulse" : "pr-box"} x={g(p.id, "x0")} y={g(p.id, "y0")} width={g(p.id, "w")} height={g(p.id, "h")} fill={p.color} style={{ fillOpacity: hl === p.id ? 0.35 : "var(--box-alpha)", transition: "fill-opacity 120ms" }} rx={1} />
            </g>
            </g>
            </g>
          );
        })}
        {/* the mark and its label share one group so both hover, click and focus as a unit; labels have a panel-coloured halo so they read over the boxes */}
        {drawn.map((p) => {
          // a highlighted mark whose label found no room gets one anyway, at the first candidate position
          const tx = X(p.recall[0]), ty = Y(p.precision[0]), x = g(p.id, "x"), y = g(p.id, "y");
          const li = pts.indexOf(p), l0 = li >= 0 ? labels[li] : null;
          const l = l0 ? { x: l0.x - tx, y: l0.y - ty, text: l0.text } : hl === p.id ? { x: 9, y: -6.5, text: p.name + (p.subset ? " *" : "") } : null;
          const hasLogo = logos && logoFor(p.id);
          return (
            <g key={`d${p.id}`} className="fd" style={fadeStyle(stateOf[p.id] ?? "exit")}>{/* fade in / out (ui.tsx usePresence) */}
            <g {...hoverable(onHover, p.id)}>{/* cross-chart hover (hover.tsx) wraps the tooltip group */}
            <g transform={`translate(${x} ${y})`} onMouseMove={(e) => show(e, { kind: "mark", x: tx, y: ty, r: 9 }, prTip(p, logos ? <Logo model={p.id} size={12} /> : undefined))} onMouseLeave={hide} {...selectable(pickMark, p, p.name)}>
              <circle className="hit" r={9} fill="transparent" />
              {hasLogo ? (
                <g color={p.color}><LogoGlyph model={p.id} cx={0} cy={0} size={glyph(p)} /></g>
              ) : (
                <circle r={3.2} fill={p.color} />
              )}
              {l && (
                <text x={l.x} y={l.y + 10} fontSize={11} fill="var(--ink)" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 2.5, strokeLinejoin: "round", pointerEvents: onSelect ? "auto" : "none" }}>
                  {l.text}
                </text>
              )}
            </g>
            </g>
            </g>
          );
        })}
        {labels.some((l) => !l) && <text x={W - PR} y={PT - 6} fontSize={10.5} textAnchor="end" fill="var(--ink-4)">some labels hidden where marks overlap; hover to identify</text>}
        {pts.length === 0 && <text x={W / 2} y={H / 2} textAnchor="middle" fontSize={13} fill="var(--ink-4)">{emptyText ?? "Select at least one model."}</text>}
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
