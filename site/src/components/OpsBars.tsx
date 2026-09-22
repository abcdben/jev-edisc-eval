import { useRef } from "react";
import { Logo, LogoGlyph } from "../logos";
import { CLICK_HINT, DECIDER_TEXT, ROW_PULSE_MS, RowTint, TipBox, fadeStyle, selectable, usePresence, usePulseWindow, useTip, useTween, useWidth } from "./ui";
import { hoverable } from "./hover";

/** `sub` is the one secondary line of the row's hover tooltip. `empty` replaces the "not measured" text when `value` is null for a reason other than missing data. `decider` (data.ts isDecider) washes the row's logo and name. `emphasis` (Compare models: the Jev row only) tints the row (ui.tsx RowTint). */
export type BarItem = { id: string; name: string; color: string; value: number | null; label: string; sub?: string; subset?: string | null; empty?: string; decider?: boolean; emphasis?: boolean };

const ROW = 20;

/** Horizontal bars with the number written at the end of each bar. Zero-valued items are drawn as a hairline. `unit` follows the value in the tooltip. `onSelect` makes each row a button (click, Enter, Space). `highlight` tints the row with that id (cross-chart hover, see hover.tsx); `onHover` reports the row under the pointer or keyboard focus. */
/** Motion (ui.tsx): bars grow from 0 on first paint and ease to a new length over 320 ms; rows slide to their new order (CSS transform on the keyed group) and fade in and out over 150 ms. */
export function OpsBars({ items, axis, unit, sort = true, logos = true, onSelect, highlight, onHover }: { items: BarItem[]; axis: string; unit?: string; sort?: boolean; logos?: boolean; onSelect?: (item: BarItem) => void; highlight?: string | null; onHover?: (id: string | null) => void }) {
  const { tip, show, hide, hostRef } = useTip();
  const pickRow = onSelect && ((it: BarItem) => { hide(); onSelect(it); });
  const W = useWidth(hostRef, 560);
  const LABEL_W = logos ? 168 : 150;
  const rows = sort ? [...items].sort((a, b) => (a.value ?? Infinity) - (b.value ?? Infinity)) : items;
  const max = Math.max(1e-9, ...rows.map((r) => r.value ?? 0));
  const plotW = W - LABEL_W - 80;
  const h = rows.length * ROW + 20;
  const barW = (v: number | null) => (v == null ? 0 : v === 0 ? 1.5 : Math.max(2, (v / max) * plotW));
  // where the longest bar's figure ends: a tooltip beside the pointer may only sit right of this
  const clearX = Math.max(LABEL_W, ...rows.map((r) => LABEL_W + barW(r.value) + 7 + (r.value == null ? r.empty ?? "not measured" : r.label).length * 6.6));
  // Drawn in the order rows first appeared (ui.tsx usePresence), placed by rank with a transform, so a re-sort slides rows instead of moving
  // DOM nodes; rows that just left fade out where they last stood. Bar lengths ease, from 0 when a bar first appears (useTween).
  const presence = usePresence(items, (it) => it.id);
  const lastTop = useRef(new Map<string, number>());
  rows.forEach((r, i) => lastTop.current.set(r.id, i * ROW));
  const drawn = presence.map((p) => ({ r: p.item, state: p.state }));
  const widths = useTween(Object.fromEntries(drawn.map(({ r }) => [r.id, barW(r.value)])), 320, () => 0, W);
  // An emphasised row (`emphasis: true`, Compare models' Jev row) carries a faint tint that breathes for a few cycles when the table loads or its rows change (ui.tsx usePulseWindow, RowTint).
  const sig = items.map((it) => `${it.id}:${it.value == null ? "-" : it.value.toPrecision(6)}`).join("|");
  const pulsing = usePulseWindow(sig, items.some((it) => it.emphasis), ROW_PULSE_MS);
  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
        {drawn.map(({ r, state }) => {
          // the row's group is translated to its rank (CSS transition on transform); everything inside is drawn at y = 0..ROW
          const top = lastTop.current.get(r.id) ?? 0;
          const v = r.value;
          const bw = widths[r.id] ?? barW(v), label = `${r.name}${r.subset ? " *" : ""}`;
          const content = { title: r.name, color: r.color, icon: logos ? <Logo model={r.id} size={12} /> : undefined, value: v == null ? r.empty ?? "not measured" : r.label, unit: v == null ? undefined : unit, sub: r.sub };
          return (
            <g key={r.id} className={`mv fd${highlight === r.id ? " hl" : ""}`} style={{ transform: `translate(0px, ${top}px)`, ...fadeStyle(state) }} {...hoverable(onHover, r.id)}>{/* cross-chart hover (hover.tsx) wraps the tooltip group */}
            <g onMouseMove={(e) => show(e, { kind: "row", top, height: ROW, clearX }, content)} onMouseLeave={hide} {...selectable(pickRow, r, r.name)}>
              {r.emphasis && <RowTint sig={sig} pulsing={pulsing} width={W} height={ROW} />}
              <rect className="hit" x={0} y={0} width={W} height={ROW} fill="transparent" />
              {logos ? (
                <>
                  
                  <g color="var(--ink-2)"><LogoGlyph model={r.id} cx={8} cy={ROW / 2} /></g>
                  <text x={22} y={ROW / 2 + 4} fontSize={12} fill="var(--ink-2)" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
                </>
              ) : (
                <text x={LABEL_W - 10} y={ROW / 2 + 4} textAnchor="end" fontSize={12} fill="var(--ink-2)" style={r.decider ? DECIDER_TEXT : undefined}>{label}</text>
              )}
              <rect x={LABEL_W} y={6} width={bw} height={ROW - 12} fill={r.color} rx={1.5} style={{ fillOpacity: v === 0 ? "calc(var(--bar-alpha) * 0.5)" : "var(--bar-alpha)" }} />
              <text x={LABEL_W + bw + 7} y={ROW / 2 + 4} fontSize={11.5} fill={v == null ? "var(--ink-4)" : "var(--ink)"} className="mono">{v == null ? r.empty ?? "not measured" : r.label}</text>
            </g>
            </g>
          );
        })}
        <line x1={LABEL_W} x2={LABEL_W} y1={0} y2={rows.length * ROW} stroke="var(--axis)" />
        <text x={LABEL_W} y={rows.length * ROW + 15} fontSize={10.5} fill="var(--ink-3)">{axis}</text>
        {rows.length === 0 && <text x={W / 2} y={12} textAnchor="middle" fontSize={12} fill="var(--ink-4)">—</text>}
      </svg>
      <TipBox tip={tip} hint={onSelect ? CLICK_HINT : undefined} />
    </div>
  );
}
