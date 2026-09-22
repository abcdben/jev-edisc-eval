import { DATA, fmtCI, fmtInt, fmtPct, isDecider, type DetCell, type Rec } from "../data";
import { Logo, LogoGlyph } from "../logos";
import { useRef, useState } from "react";
import { CLICK_HINT, DECIDER_TEXT, Hint, ROW_PULSE_MS, RowTint, Seg, TipBox, fadeStyle, selectable, usePresence, usePulseWindow, useTip, useTween, useWidth, type HintItem, type TipLine } from "./ui";
import { hoverable } from "./hover";

/** The Determinism card's "i" popover. */
const DET_ITEMS: HintItem[] = [
  { k: "What", v: <mark><b>Whether a model gives the same answer when asked the same question again.</b></mark> },
  { k: "Why", v: <>A review has to be <b>repeatable to be defensible</b>: a document coded responsive today should be coded responsive tomorrow. A model that flips answers adds noise a team cannot audit away.</> },
  { k: "How", v: <>Each model coded a fixed panel of <b>300 documents five times</b> under identical settings: 100 with a debatable gold label, 100 clear positives, 100 clear negatives. The bar is the probability that two runs disagree on a decision, with a 95% bootstrap whisker. The same panel is shown for every corpus.</> },
  { k: "t = 0", v: <><b>Temperature 0</b> asks an LLM for its most likely answer instead of sampling; the toggle re-runs the test that way where the API accepts it. Decision models have no sampling to turn off.</> },
];

const LABEL_W = 168, ROW = 20;

/**
 * What the card plots for one record. `cell` is the measured cell (its `model` names the configuration it was measured on, which differs
 * from the record's key when a row borrows a sibling's cell).
 */
export type DetEntry = { pairwise: [number, number, number]; setting: "default" | "t0"; cell: DetCell };

/** The determinism entry for a record: matched on model key, arm follows the page. Ablation variants are not covered. */
export function detFor(r: Rec, arm: "multi" | "single", setting: "default" | "t0"): DetEntry | null {
  const det = DATA.determinism;
  if (!det) return null;
  const find = (key: string) => det.cells.find((c) => c.model === key && c.arm === arm && c.setting === setting) ?? null;
  // The fine-tuned Laya checkpoint was not repeated. Laya has no sampling controls, so the zero-shot recipe (or base) cell stands in for it.
  const cell = r.model === "laya-ft" ? find("laya@recipe") ?? find("laya@base") : find(r.model_key);
  return cell ? { pairwise: cell.pairwise, setting: cell.setting, cell } : null;
}

/** The full determinism facts for a record (shown in the details modal's Metrics block; the hover carries only the bar's figure). */
export function detLines(x: DetEntry, r: Rec, name: string): { lines: TipLine[]; notes: string[] } {
  const c = x.cell;
  const lines: TipLine[] = [
    ["Runs", String(c.k)],
    ["Decisions compared", fmtInt(c.n_decisions)],
    ["Pairwise disagreement", fmtCI(c.pairwise, 2)],
    ["Decisions that flipped", fmtCI(c.decision_flip, 2)],
  ];
  const borrowed = c.model !== r.model_key;
  // A borrowed cell's flip rates carry over; its recall and precision levels belong to the configuration it was measured on, so they are left out.
  if (c.recall_range && !borrowed) lines.push(["Recall across runs", `${fmtPct(c.recall_range[0])} – ${fmtPct(c.recall_range[1])}`]);
  if (c.precision_range && !borrowed) lines.push(["Precision across runs", `${fmtPct(c.precision_range[0])} – ${fmtPct(c.precision_range[1])}`]);
  const notes: string[] = [];
  if (borrowed) notes.push(`Not repeated for the fine-tuned checkpoint; these are the zero-shot ${DATA.models[c.model]?.name ?? c.model} cell's numbers. Laya has no sampling controls, so the checkpoint behaves the same.`);
  if (c.setting === "t0") notes.push(`${name} at temperature 0.`);
  return { lines, notes };
}

/** `onSelect` makes each row a button (click, Enter, Space), including the rows without a measurement. `highlight` tints the row of that model (cross-chart hover, see hover.tsx); `onHover` reports the row under the pointer or keyboard focus. `emphasis` (Compare models: the Jev row only) picks the row that carries the faint tint (ui.tsx RowTint). */
export function Consistency({ recs, colorOf, nameOf, arm, onSelect, highlight, onHover, emphasis }: { recs: Rec[]; colorOf: (r: Rec) => string; nameOf: (r: Rec) => string; arm: "multi" | "single"; onSelect?: (r: Rec) => void; highlight?: string | null; onHover?: (id: string | null) => void; emphasis?: (r: Rec) => boolean }) {
  const { tip, show, hide, hostRef } = useTip();
  const pickRow = onSelect && ((r: Rec) => { hide(); onSelect(r); });
  const W = useWidth(hostRef, 760);
  const det = DATA.determinism;
  const [setting, setSetting] = useState<"default" | "t0">("default");
  const rows = recs.map((r) => ({ r, d: detFor(r, arm, "default"), t0: detFor(r, arm, "t0") }));
  const hasT0 = rows.some((x) => x.t0);
  // At temperature 0, deciders and the floor expose no sampling control, so their default cell is their behaviour in both views; an LLM without a t=0 cell (Sonnet 5) rejected the parameter.
  const isLLM = (r: Rec) => r.kind === "llm" || r.kind === "local_llm";
  const shown = rows.map((x) => ({ r: x.r, c: setting === "t0" ? (x.t0 ?? (isLLM(x.r) ? null : x.d)) : x.d }));
  const measured = shown.filter((x) => x.c);
  // Ascending by point estimate; rows without an entry sink to the bottom (stable sort keeps picker order among ties).
  const sorted = [...shown].sort((a, b) => (a.c?.pairwise[0] ?? Infinity) - (b.c?.pairwise[0] ?? Infinity));
  const max = Math.max(0.01, ...measured.map((x) => x.c!.pairwise[2]));
  const plotW = Math.max(120, W - LABEL_W - 90);
  const X = (v: number) => LABEL_W + (v / max) * plotW;
  const h = sorted.length * ROW + 20;
  const lbl = (v: number) => (v === 0 ? "0" : fmtPct(v, v < 0.001 ? 2 : 1));
  // where the widest whisker's figure ends: a tooltip beside the pointer may only sit right of this
  const clearX = Math.max(LABEL_W + 120, ...measured.map((x) => X(x.c!.pairwise[2]) + 7 + lbl(x.c!.pairwise[0]).length * 6.6));
  const sub = (c: DetEntry) => `${fmtInt(c.cell.n_decisions)} decisions · ${c.cell.k} runs`;
  // Motion (ui.tsx): drawn in the order rows first appeared (usePresence) and placed by rank with a transform, so a re-sort slides rows instead
  // of moving DOM nodes; rows fade in and out, leavers where they last stood. Bars grow from 0 on first paint and whisker ends ease (useTween).
  const presence = usePresence(shown, (x) => x.r.model);
  const lastTop = useRef(new Map<string, number>());
  sorted.forEach((x, i) => lastTop.current.set(x.r.model, i * ROW));
  const drawn = presence.map((p) => ({ x: p.item, state: p.state }));
  const target: Record<string, number> = {};
  for (const { x } of drawn) if (x.c) { target[`${x.r.model}:v`] = X(x.c.pairwise[0]); target[`${x.r.model}:lo`] = X(x.c.pairwise[1]); target[`${x.r.model}:hi`] = X(x.c.pairwise[2]); }
  const geo = useTween(target, 320, () => LABEL_W, W);
  const g = (k: string) => geo[k] ?? target[k];
  // An emphasised row (`emphasis`, Compare models' Jev row) carries a faint tint that breathes for a few cycles when the card loads or its rows change (ui.tsx usePulseWindow, RowTint).
  const sig = shown.map((x) => `${x.r.model}:${x.c ? x.c.pairwise[0].toFixed(5) : "-"}`).join("|");
  const pulsing = usePulseWindow(sig, !!emphasis && shown.some((x) => emphasis(x.r)), ROW_PULSE_MS);
  return (
    <div className="card">
      <div className="card-t">
        <h3>Determinism</h3>
        <span className="unit">{det ? `disagreement between ${rows.find((x) => x.d?.cell)?.d?.cell?.k ?? 5} identical runs on ${fmtInt(det.sample.n_docs)} emails` : "not measured"}</span>
        <span className="right">
          {hasT0 && <Seg value={setting} onChange={setSetting} options={[{ id: "default", label: "default", title: "Vendor default sampling" }, { id: "t0", label: "t = 0", title: "Temperature 0 where the API accepts it" }]} />}
          <Hint items={DET_ITEMS} more="About" />
        </span>
      </div>
      <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${h}`} width={W} height={h} style={{ display: "block", overflow: "visible" }}>
          {drawn.map(({ x, state }) => {
            // the row's group is translated to its rank (CSS transition on transform); everything inside is drawn at y = 0..ROW
            const top = lastTop.current.get(x.r.model) ?? 0, cy = ROW / 2;
            const c = colorOf(x.r), nm = nameOf(x.r), k = x.r.model;
            const dec = isDecider(x.r.kind);
            const tint = emphasis?.(x.r) ? <RowTint sig={sig} pulsing={pulsing} width={W} height={ROW} /> : null;
            const wrap = { className: `mv fd${highlight === k ? " hl" : ""}`, style: { transform: `translate(0px, ${top}px)`, ...fadeStyle(state) } };
            if (!x.c) {
              return (
                <g key={k} {...wrap} {...hoverable(onHover, k)}>{/* cross-chart hover (hover.tsx) */}
                <g {...selectable(pickRow, x.r, nm)}>
                  {tint}
                  <rect className="hit" x={0} y={0} width={W} height={ROW} fill="transparent" />
                  <g color="var(--ink-4)"><LogoGlyph model={k} cx={8} cy={cy} opacity={0.5} /></g>
                  <text x={22} y={cy + 4} fontSize={12} fill="var(--ink-4)">{nm}</text>
                  <text x={LABEL_W + 7} y={cy + 4} fontSize={11} fill="var(--ink-4)">{setting === "t0" ? "API rejects temperature" : "not measured"}</text>
                </g>
                </g>
              );
            }
            const v = x.c.pairwise[0], lo = x.c.pairwise[1], hi = x.c.pairwise[2];
            const xv = g(`${k}:v`), xlo = g(`${k}:lo`), xhi = g(`${k}:hi`);
            return (
              <g key={k} {...wrap} {...hoverable(onHover, k)}>{/* cross-chart hover (hover.tsx) wraps the tooltip group */}
              <g onMouseMove={(e) => show(e, { kind: "row", top, height: ROW, clearX }, { title: `${nm}${x.c!.setting === "t0" ? " · temperature 0" : ""}`, color: c, icon: <Logo model={k} size={12} />, value: v === 0 ? "0" : fmtPct(v, 2), unit: "pairwise disagreement", lines: v === 0 ? undefined : [["95% interval", `${fmtPct(lo, 2)} – ${fmtPct(hi, 2)}`]], sub: sub(x.c!) })} onMouseLeave={hide} {...selectable(pickRow, x.r, nm)}>
                {tint}
                <rect className="hit" x={0} y={0} width={W} height={ROW} fill="transparent" />
                <g color="var(--ink-2)"><LogoGlyph model={k} cx={8} cy={cy} /></g>
                <text x={22} y={cy + 4} fontSize={12} fill="var(--ink-2)" style={dec ? DECIDER_TEXT : undefined}>{nm}</text>
                <rect x={LABEL_W} y={cy - 4} width={Math.max(1.5, xv - LABEL_W)} height={8} fill={c} rx={1.5} style={{ fillOpacity: "var(--bar-alpha)" }} />
                <line x1={xlo} x2={xhi} y1={cy} y2={cy} stroke="var(--ink)" strokeWidth={1} opacity={0.6} />
                <text x={xhi + 7} y={cy + 4} fontSize={11} fill="var(--ink)" className="mono">{lbl(v)}</text>
              </g>
              </g>
            );
          })}
          <line x1={LABEL_W} x2={LABEL_W} y1={0} y2={sorted.length * ROW} stroke="var(--axis)" />
          <text x={LABEL_W} y={sorted.length * ROW + 17} fontSize={10.5} fill="var(--ink-3)">probability two runs disagree{setting === "t0" ? " · temperature 0" : ""}</text>
        </svg>
        <TipBox tip={tip} hint={onSelect ? CLICK_HINT : undefined} />
      </div>
    </div>
  );
}
