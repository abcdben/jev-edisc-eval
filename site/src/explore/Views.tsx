import { TipBox, useTip, useWidth, type TipContent } from "../components/ui";
import { OUTCOME_ORDER, bucketOf, fmtN, fmtShare, type Arm, type BucketDef, type BucketKey, type Lab, type Outcome } from "../exploreData";

/** Counts per (standard, A, B) cell; B is "x" when there is no overlay. */
export type Cells = Map<string, number>;
export const cellKey = (s: Lab, a: Lab, b: Lab | null) => `${s}|${a}|${b ?? "x"}`;
export type Sel = { kind: "bucket"; key: BucketKey } | { kind: "bin"; lo: number; hi: number } | null;
export type Scale = "linear" | "sqrt";
type Common = { cells: Cells; S: Arm; A: Arm | null; B: Arm | null; defs: BucketDef[]; scale: Scale; sel: Sel; onSel: (s: Sel) => void };

const NEUTRAL = "var(--line-2)", GRAYF = "var(--ink-4)";
const sc = (n: number, s: Scale) => (s === "sqrt" ? Math.sqrt(n) : n);
const LABS: Lab[] = [1, 0, -1];
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);

function outcomeCells(cells: Cells, o: Outcome, hasB: boolean): { n: number; b1: number; b0: number; bg: number; sA: [Lab, Lab][] } {
  // the (s, a) pairs that make up this outcome
  const pairs: [Lab, Lab][] = [];
  for (const s of LABS) for (const a of LABS) if ((s === -1 || a === -1 ? "gray" : s === 1 && a === 1 ? "agree_r" : s === 0 && a === 0 ? "agree_nr" : s === 1 ? "miss" : "over") === o) pairs.push([s, a]);
  let b1 = 0, b0 = 0, bg = 0;
  for (const [s, a] of pairs) {
    if (!hasB) { b0 += cells.get(cellKey(s, a, null)) ?? 0; continue; }
    b1 += cells.get(cellKey(s, a, 1)) ?? 0; b0 += cells.get(cellKey(s, a, 0)) ?? 0; bg += cells.get(cellKey(s, a, -1)) ?? 0;
  }
  return { n: b1 + b0 + bg, b1, b0, bg, sA: pairs };
}

const useHost = () => { const t = useTip(); const w = useWidth(t.hostRef, 820); const at = (e: React.MouseEvent) => { const r = t.hostRef.current?.getBoundingClientRect(); return { x: e.clientX - (r?.left ?? 0), y: e.clientY - (r?.top ?? 0) }; }; return { ...t, w, at }; };

/** Mosaic: one column per outcome of A against the standard (width = units), each split by B's call. */
export function Mosaic({ cells, S, A, B, defs, scale, sel, onSel }: Common) {
  const { tip, show, hide, hostRef, w, at } = useHost();
  const H = 320, top = 40, bottom = 40, gap = 6;
  const cols = OUTCOME_ORDER.map((o) => ({ o, ...outcomeCells(cells, o, !!B) })).filter((c) => c.n > 0);
  const total = sum(cols.map((c) => sc(c.n, scale))) || 1;
  const all = sum(cols.map((c) => c.n)) || 1;
  const title: Record<Outcome, string> = A
    ? { agree_nr: `${A.short} and ${S.short}: not responsive`, over: `${A.short} responsive · ${S.short} not`, miss: `${A.short} not · ${S.short} responsive`, agree_r: `${A.short} and ${S.short}: responsive`, gray: "Gray / unjudged" }
    : { agree_nr: `${S.short}: not responsive`, over: "", miss: "", agree_r: `${S.short}: responsive`, gray: "Gray / unjudged" };
  const brief: Record<Outcome, string> = A ? { agree_nr: "Both NR", over: `${A.short} over-called`, miss: `${A.short} missed`, agree_r: "Both R", gray: "Gray" } : { agree_nr: "NR", over: "", miss: "", agree_r: "R", gray: "Gray" };
  const on = (k: BucketKey) => sel?.kind === "bucket" && sel.key === k;
  const dim = (k: BucketKey) => (sel ? (on(k) ? 1 : 0.3) : 1);
  const def = (k: BucketKey) => defs.find((d) => d.key === k);
  let x = 0;
  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg width={w} height={H} className="study-svg">
        <defs><pattern id="pe-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--ink-3)" strokeWidth="1" /></pattern></defs>
        {cols.map((c) => {
          const cw = (sc(c.n, scale) / total) * (w - gap * (cols.length - 1));
          const x0 = x; x += cw + gap;
          const hAvail = H - top - bottom;
          const isGray = c.o === "gray", contested = c.o === "miss" || c.o === "over";
          const segs: { k: BucketKey; n: number; fill: string; hatch: boolean; who: string }[] = [];
          if (B && !isGray) {
            const [s, a] = c.sA[0];
            if (c.b1) segs.push({ k: bucketOf(s, a, 1), n: c.b1, fill: B.color, hatch: contested, who: `${B.short}: responsive` });
            if (c.b0) segs.push({ k: bucketOf(s, a, 0), n: c.b0, fill: NEUTRAL, hatch: contested, who: `${B.short}: not responsive` });
            if (c.bg) segs.push({ k: bucketOf(s, a, -1), n: c.bg, fill: GRAYF, hatch: true, who: `${B.short}: gray` });
          } else {
            const sR = c.o === "agree_r" || c.o === "miss";
            segs.push({ k: c.o, n: c.n, fill: isGray ? GRAYF : sR ? S.color : NEUTRAL, hatch: contested || isGray, who: isGray ? "unjudged" : `${S.short}: ${sR ? "responsive" : "not responsive"}` });
          }
          let y = top;
          return (
            <g key={c.o}>
              <text x={x0 + cw / 2} y={14} textAnchor="middle" fontSize={11} fill="var(--ink-2)">{title[c.o].length * 5.6 < cw - 6 ? title[c.o] : brief[c.o].length * 5.6 < cw - 6 ? brief[c.o] : ""}</text>
              <text x={x0 + cw / 2} y={28} textAnchor="middle" fontSize={11} fill="var(--ink-4)">{fmtN(c.n)}{cw > 60 ? ` · ${fmtShare(c.n / all)}` : ""}</text>
              {segs.map((sg) => {
                const sh = (sg.n / c.n) * hAvail, y0 = y; y += sh;
                const d = def(sg.k);
                const tipc: TipContent = { title: d?.label ?? sg.who, value: fmtN(sg.n), unit: `${fmtShare(sg.n / all)} of all · ${fmtShare(sg.n / c.n)} of column`, lines: [sg.who] };
                return (
                  <g key={sg.k + sg.who} className="pe-hit" style={{ cursor: "pointer" }} opacity={dim(sg.k)} onClick={() => onSel({ kind: "bucket", key: sg.k })} onMouseMove={(e) => { const p = at(e); show(e, { kind: "mark", x: p.x, y: p.y, r: 8 }, tipc); }} onMouseLeave={hide}>
                    <rect x={x0} y={y0} width={cw} height={Math.max(1, sh)} fill={sg.fill} />
                    {sg.hatch && <rect x={x0} y={y0} width={cw} height={Math.max(1, sh)} fill="url(#pe-hatch)" />}
                    {on(sg.k) && <rect x={x0 + 0.75} y={y0 + 0.75} width={cw - 1.5} height={Math.max(1, sh) - 1.5} fill="none" stroke="var(--ink)" strokeWidth={1.5} />}
                    {sh > 16 && cw > 44 && <text x={x0 + cw / 2} y={y0 + sh / 2 + 4} textAnchor="middle" fontSize={11} fill={sg.fill === NEUTRAL ? "var(--ink)" : "var(--panel)"} style={{ pointerEvents: "none" }}>{fmtN(sg.n)}</text>}
                  </g>
                );
              })}
              {B && !isGray && (() => { const full = `${B.short} R ${fmtShare(c.b1 / c.n)}`, pc = fmtShare(c.b1 / c.n); const t = full.length * 5.4 < cw - 6 ? full : pc.length * 5.4 < cw - 4 ? pc : ""; return t && <text x={x0 + cw / 2} y={H - 22} textAnchor="middle" fontSize={10.5} fill="var(--ink-3)">{t}</text>; })()}
            </g>
          );
        })}
        <text x={0} y={H - 4} fontSize={11} fill="var(--ink-4)">Width: {scale === "sqrt" ? "square root of " : ""}units per column. {B ? `Fill: ${B.short} calls responsive (colour) or not (neutral).` : `Fill: ${S.short} calls responsive (colour) or not.`} {A && <> Hatched: {A.short} and {S.short} disagree.</>}</text>
      </svg>
      <TipBox tip={tip} hint="click to list" />
    </div>
  );
}

/** Flow: every unit travels A → standard → B; band width = units. */
export function Flow({ cells, S, A, B, defs, scale, sel, onSel }: Common & { A: Arm }) {
  const { tip, show, hide, hostRef, w, at } = useHost();
  const H = 360, top = 30, bottom = 24, nodeW = 14, gapN = 10;
  const colsArms = B ? [A, S, B] : [A, S];
  const M = 150; // room for the first and last columns' labels outside their nodes
  const colX = colsArms.map((_, i) => M + (i * (w - 2 * M - nodeW)) / (colsArms.length - 1));
  type Strand = { labs: Lab[]; n: number; key: BucketKey };
  const strands: Strand[] = [];
  for (const [k, n] of cells) {
    if (!n) continue;
    const [s, a, b] = k.split("|");
    const S_ = Number(s) as Lab, A_ = Number(a) as Lab, B_ = b === "x" ? null : (Number(b) as Lab);
    strands.push({ labs: B_ == null ? [A_, S_] : [A_, S_, B_], n, key: bucketOf(S_, A_, B_) });
  }
  const total = sum(strands.map((s) => sc(s.n, scale))) || 1;
  const all = sum(strands.map((s) => s.n)) || 1;
  const hAvail = H - top - bottom - 2 * gapN;
  const px = (n: number) => (sc(n, scale) / total) * hAvail;
  const nc = colsArms.length;
  const layout = (c: number) => {
    const ys = new Map<Strand, number>(); let y = top; const nodes: { lab: Lab; y0: number; y1: number; n: number }[] = [];
    for (const lab of LABS) {
      const inNode = strands.filter((s) => s.labs[c] === lab).sort((p, q) => { for (let d = 1; d < nc; d++) { const i = (c + d) % nc, dd = LABS.indexOf(p.labs[i]) - LABS.indexOf(q.labs[i]); if (dd) return dd; } return 0; });
      if (!inNode.length) continue;
      const y0 = y;
      for (const s of inNode) { ys.set(s, y); y += px(s.n); }
      nodes.push({ lab, y0, y1: y, n: sum(inNode.map((s) => s.n)) }); y += gapN;
    }
    return { ys, nodes };
  };
  const L = colsArms.map((_, c) => layout(c));
  const band = (x0: number, ya: number, x1: number, yb: number, h: number) => { const m = (x0 + x1) / 2; return `M${x0},${ya} C${m},${ya} ${m},${yb} ${x1},${yb} L${x1},${yb + h} C${m},${yb + h} ${m},${ya + h} ${x0},${ya + h} Z`; };
  const on = (k: BucketKey) => sel?.kind === "bucket" && sel.key === k;
  const last = colsArms[nc - 1];
  const fillFor = (s: Strand) => { const l = s.labs[nc - 1]; return l === 1 ? last.color : l === 0 ? "var(--ink-3)" : GRAYF; };
  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg width={w} height={H} className="study-svg">
        {colsArms.map((a, i) => <text key={a.id} x={colX[i] + nodeW / 2} y={14} textAnchor="middle" fontSize={11.5} fill="var(--ink-2)">{a.short}{a.planned ? " · placeholder" : ""}</text>)}
        {strands.map((s, i) => {
          const h = Math.max(0.5, px(s.n));
          const op = sel ? (on(s.key) ? 0.9 : 0.1) : s.key === "gray" ? 0.3 : 0.5;
          const contested = s.labs[0] !== s.labs[1] && s.labs[0] >= 0 && s.labs[1] >= 0;
          const d = defs.find((x) => x.key === s.key);
          const tipc: TipContent = { title: d?.label ?? s.key, value: fmtN(s.n), unit: `${fmtShare(s.n / all)} of all`, lines: colsArms.map((a, c) => [a.short, s.labs[c] === 1 ? "responsive" : s.labs[c] === 0 ? "not responsive" : "gray"] as [string, string]) };
          return (
            <g key={i} className="pe-hit" style={{ cursor: "pointer" }} onClick={() => onSel({ kind: "bucket", key: s.key })} onMouseMove={(e) => { const p = at(e); show(e, { kind: "mark", x: p.x, y: p.y, r: 8 }, tipc); }} onMouseLeave={hide}>
              {colsArms.slice(1).map((_, c) => <path key={c} d={band(colX[c] + nodeW, L[c].ys.get(s)!, colX[c + 1], L[c + 1].ys.get(s)!, h)} fill={fillFor(s)} opacity={op} stroke={contested && c === 0 ? "var(--ink)" : "none"} strokeWidth={0.6} />)}
            </g>
          );
        })}
        {L.map((l, c) => l.nodes.map((nd) => (
          <g key={`${c}-${nd.lab}`}>
            <rect x={colX[c]} y={nd.y0} width={nodeW} height={Math.max(2, nd.y1 - nd.y0)} fill={nd.lab === 1 ? colsArms[c].color : nd.lab === 0 ? "var(--ink-3)" : GRAYF} />
            <text x={c === 0 ? colX[c] - 6 : colX[c] + nodeW + 6} y={(nd.y0 + nd.y1) / 2 + 4} textAnchor={c === 0 ? "end" : "start"} fontSize={11} fill="var(--ink)" style={{ paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 3, strokeLinejoin: "round" }}>{nd.lab === 1 ? "responsive" : nd.lab === 0 ? "not responsive" : "gray"} · {fmtN(nd.n)}</text>
          </g>
        )))}
        <text x={0} y={H - 4} fontSize={11} fill="var(--ink-4)">Band width: {scale === "sqrt" ? "square root of " : ""}units. Colour: {last.short}'s call at the end of the path. Outlined bands: {A.short} and {S.short} disagree.</text>
      </svg>
      <TipBox tip={tip} hint="click to list" />
    </div>
  );
}

/** Confidence: the model's p(responsive) in ten bins, stacked by how the other arms came out. */
export type ConfGroup = { id: string; name: string; color: string; hatch?: boolean };
export function Confidence({ model, groups, bins, threshold, sel, onSel }: { model: Arm; groups: ConfGroup[]; bins: number[][]; threshold: number; sel: Sel; onSel: (s: Sel) => void }) {
  const { tip, show, hide, hostRef, w, at } = useHost();
  const H = 320, left = 52, top = 20, bottom = 54;
  const totals = bins.map((b) => sum(b));
  const all = sum(totals) || 1;
  const maxBin = Math.max(1, ...totals);
  const y = (n: number) => top + (1 - Math.sqrt(n / maxBin)) * (H - top - bottom);
  const bw = (w - left) / bins.length;
  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg width={w} height={H} className="study-svg">
        <defs><pattern id="pe-hatch2" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--panel)" strokeWidth="1" /></pattern></defs>
        {[0, 0.25, 0.5, 0.75, 1].map((f) => { const n = f * f * maxBin; return <g key={f}><line x1={left} x2={w} y1={y(n)} y2={y(n)} stroke="var(--line)" /><text x={left - 6} y={y(n) + 4} textAnchor="end" fontSize={10.5} fill="var(--ink-4)">{fmtN(Math.round(n))}</text></g>; })}
        {bins.map((b, i) => {
          const lo = i / bins.length, hi = (i + 1) / bins.length, onBin = sel?.kind === "bin" && Math.abs(sel.lo - lo) < 1e-9;
          let acc = 0;
          const tipc: TipContent = { title: `${model.short} p(responsive) ${lo.toFixed(1)}–${hi.toFixed(1)}`, value: fmtN(totals[i]), unit: `${fmtShare(totals[i] / all)} of all`, lines: groups.map((g, gi) => [g.name, `${fmtN(b[gi])} · ${fmtShare(totals[i] ? b[gi] / totals[i] : 0)}`] as [string, string]) };
          return (
            <g key={i} className="pe-hit" style={{ cursor: "pointer" }} opacity={sel?.kind === "bin" && !onBin ? 0.3 : 1} onClick={() => onSel({ kind: "bin", lo, hi })} onMouseMove={(e) => { const p = at(e); show(e, { kind: "mark", x: p.x, y: p.y, r: 8 }, tipc); }} onMouseLeave={hide}>
              <rect x={left + i * bw} y={top} width={bw} height={H - top - bottom} fill="transparent" />
              {b.map((n, gi) => { const y1 = y(acc), y0 = y(acc + n); acc += n; return <g key={gi}><rect x={left + i * bw + 3} y={y0} width={bw - 6} height={Math.max(0, y1 - y0)} fill={groups[gi].color} />{groups[gi].hatch && <rect x={left + i * bw + 3} y={y0} width={bw - 6} height={Math.max(0, y1 - y0)} fill="url(#pe-hatch2)" />}</g>; })}
              {onBin && <rect x={left + i * bw + 2} y={y(totals[i]) - 1} width={bw - 4} height={H - bottom - y(totals[i]) + 1} fill="none" stroke="var(--ink)" strokeWidth={1.5} />}
              <text x={left + i * bw + bw / 2} y={H - bottom + 16} textAnchor="middle" fontSize={10.5} fill="var(--ink-4)">{lo.toFixed(1)}–{hi.toFixed(1)}</text>
            </g>
          );
        })}
        <line x1={left + threshold * (w - left)} x2={left + threshold * (w - left)} y1={top} y2={H - bottom} stroke="var(--ink-2)" strokeDasharray="3 3" />
        <text x={left + threshold * (w - left) + 4} y={top + 10} fontSize={10.5} fill="var(--ink-2)">threshold {threshold.toFixed(2)}</text>
        <text x={left + (w - left) / 2} y={H - bottom + 32} textAnchor="middle" fontSize={11} fill="var(--ink-3)">{model.short} p(responsive){model.planned ? " · placeholder" : ""}</text>
        <text x={0} y={H - 4} fontSize={11} fill="var(--ink-4)">Units per bin, square-root axis. Stacks: {groups.map((g) => g.name).join(" · ")}.</text>
      </svg>
      <TipBox tip={tip} hint="click to list" />
    </div>
  );
}
