import { TipBox, useTip, type TipLine } from "./ui";

export type BarItem = { id: string; name: string; color: string; value: number | null; label: string; tip: { lines: TipLine[]; notes?: string[] }; subset?: string | null };

const LABEL_W = 150, W = 560, ROW = 24;

/** Horizontal bars with the number written at the end of each bar. Zero-valued items are drawn as a hairline. */
export function OpsBars({ items, axis, sort = true }: { items: BarItem[]; axis: string; sort?: boolean }) {
  const { tip, show, hide, hostRef } = useTip();
  const rows = sort ? [...items].sort((a, b) => (a.value ?? Infinity) - (b.value ?? Infinity)) : items;
  const max = Math.max(1e-9, ...rows.map((r) => r.value ?? 0));
  const plotW = W - LABEL_W - 80;
  const h = rows.length * ROW + 22;
  const best = rows.find((r) => (r.value ?? 0) > 0)?.value ?? null;
  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${h}`} width="100%" style={{ display: "block", overflow: "visible" }}>
        {rows.map((r, i) => {
          const y = i * ROW;
          const v = r.value;
          const bw = v == null ? 0 : v === 0 ? 1.5 : Math.max(2, (v / max) * plotW);
          const ratio = v != null && best && v > 0 ? v / best : null;
          return (
            <g key={r.id} onMouseMove={(e) => show(e, { title: r.name, color: r.color, lines: [...r.tip.lines, ...(ratio && ratio > 1.05 ? [[`vs. lowest shown`, `${ratio >= 10 ? Math.round(ratio) : ratio.toFixed(1)}×`] as TipLine] : [])], notes: r.tip.notes })} onMouseLeave={hide} style={{ cursor: "default" }}>
              <rect x={0} y={y} width={W} height={ROW} fill="transparent" />
              <text x={LABEL_W - 10} y={y + ROW / 2 + 4} textAnchor="end" fontSize={12} fill="#4a4845">{r.name}{r.subset ? " *" : ""}</text>
              <rect x={LABEL_W} y={y + 6} width={bw} height={ROW - 12} fill={r.color} rx={2} opacity={v === 0 ? 0.5 : 1} />
              <text x={LABEL_W + bw + 7} y={y + ROW / 2 + 4} fontSize={11.5} fill={v == null ? "#aaa69e" : "#171614"} className="mono">{v == null ? "not measured" : r.label}</text>
            </g>
          );
        })}
        <line x1={LABEL_W} x2={LABEL_W} y1={0} y2={rows.length * ROW} stroke="#cfcbc1" />
        <text x={LABEL_W} y={rows.length * ROW + 15} fontSize={10.5} fill="#8a8780">{axis}</text>
        {rows.length === 0 && <text x={W / 2} y={12} textAnchor="middle" fontSize={12} fill="#aaa69e">—</text>}
      </svg>
      <TipBox tip={tip} />
    </div>
  );
}
