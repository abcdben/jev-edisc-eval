import { useMemo, useRef, useState } from "react";
import { TipBox, useTip, useWidth, type TipContent } from "../components/ui";
import { bucketOf, fmtN, fmtShare, type Arm, type BucketDef, type BucketKey, type Lab } from "../exploreData";
import { hitProps, type Cells, type Scale, type Sel } from "./Views";

/*
 * Area-proportional Euler diagram. One circle per arm, area = units that arm called responsive; the circles are placed so every pairwise
 * and triple overlap matches the real count as closely as circles allow (exact for two arms, a least-squares fit for three). The outer
 * box is the whole judged population, so the space outside the circles is "nobody called it responsive". Gray / unjudged units sit in
 * a hatched circle of their own outside the box. Geometry after Frederickson's venn.js: intersection areas from the arc polygon, a
 * greedy initial layout by bisection on pairwise distances, then gradient descent on the squared area error.
 */

type C = { x: number; y: number; r: number };
type P = { x: number; y: number; parents: number[] };
const TAU = 2 * Math.PI;
const dist = (a: { x: number; y: number }, b: { x: number; y: number }) => Math.hypot(a.x - b.x, a.y - b.y);

/** Area of a circular segment of radius r cut by a chord at height w from the arc. */
const segment = (r: number, w: number) => (w <= 0 ? 0 : w >= 2 * r ? Math.PI * r * r : r * r * Math.acos(1 - w / r) - (r - w) * Math.sqrt(w * (2 * r - w)));

function circleCircle(a: C, b: C): { x: number; y: number }[] {
  const d = dist(a, b);
  if (d >= a.r + b.r || d <= Math.abs(a.r - b.r) || d === 0) return [];
  const l = (a.r * a.r - b.r * b.r + d * d) / (2 * d), h = Math.sqrt(Math.max(0, a.r * a.r - l * l));
  const mx = a.x + (l * (b.x - a.x)) / d, my = a.y + (l * (b.y - a.y)) / d;
  return [{ x: mx + (h * (b.y - a.y)) / d, y: my - (h * (b.x - a.x)) / d }, { x: mx - (h * (b.y - a.y)) / d, y: my + (h * (b.x - a.x)) / d }];
}

/** Area of the intersection of every circle in `cs`. */
function intersectionArea(cs: C[]): number {
  if (cs.length === 1) return Math.PI * cs[0].r * cs[0].r;
  const pts: P[] = [];
  for (let i = 0; i < cs.length; i++) for (let j = i + 1; j < cs.length; j++) for (const p of circleCircle(cs[i], cs[j])) {
    if (cs.every((c, k) => k === i || k === j || dist(p, c) <= c.r + 1e-9)) pts.push({ ...p, parents: [i, j] });
  }
  if (pts.length < 2) {
    // no crossing inside all circles: either one circle sits inside all the others, or they are disjoint
    for (const [i, c] of cs.entries()) if (cs.every((o, k) => k === i || dist(c, o) + c.r <= o.r + 1e-9)) return Math.PI * c.r * c.r;
    return 0;
  }
  const cx = pts.reduce((s, p) => s + p.x, 0) / pts.length, cy = pts.reduce((s, p) => s + p.y, 0) / pts.length;
  pts.sort((a, b) => Math.atan2(b.y - cy, b.x - cx) - Math.atan2(a.y - cy, a.x - cx));
  let poly = 0, arcs = 0;
  let p2 = pts[pts.length - 1];
  for (const p1 of pts) {
    poly += (p2.x + p1.x) * (p1.y - p2.y);
    let best: { r: number; w: number } | null = null;
    for (const k of p1.parents) if (p2.parents.includes(k)) {
      const c = cs[k];
      const a1 = Math.atan2(p1.y - c.y, p1.x - c.x), a2 = Math.atan2(p2.y - c.y, p2.x - c.x);
      let da = a2 - a1; if (da < 0) da += TAU;
      const am = a2 - da / 2;
      let w = dist({ x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 }, { x: c.x + c.r * Math.cos(am), y: c.y + c.r * Math.sin(am) });
      if (w > 2 * c.r) w = 2 * c.r;
      if (!best || best.w > w) best = { r: c.r, w };
    }
    if (best) arcs += segment(best.r, best.w);
    p2 = p1;
  }
  return Math.abs(poly) / 2 + arcs;
}

/** Centre distance at which two circles overlap by `want` (bisection; overlap falls monotonically with distance). */
function distanceFor(r1: number, r2: number, want: number): number {
  const small = Math.PI * Math.min(r1, r2) ** 2;
  if (want >= small - 1e-9) return Math.abs(r1 - r2);
  if (want <= 0) return r1 + r2;
  let lo = Math.abs(r1 - r2), hi = r1 + r2;
  for (let i = 0; i < 60; i++) { const d = (lo + hi) / 2; if (intersectionArea([{ x: 0, y: 0, r: r1 }, { x: d, y: 0, r: r2 }]) > want) lo = d; else hi = d; }
  return (lo + hi) / 2;
}

type Want = { idx: number[]; size: number };
function loss(cs: C[], wants: Want[]): number {
  let s = 0;
  for (const w of wants) { const a = intersectionArea(w.idx.map((i) => cs[i])); s += (a - w.size) ** 2; }
  return s;
}

/** Circles for set areas `areas` honouring the pairwise and triple overlaps in `wants` as closely as possible. */
function layout(areas: number[], wants: Want[]): C[] {
  const rs = areas.map((a) => Math.sqrt(a / Math.PI));
  const live = rs.map((r, i) => (r > 0 ? i : -1)).filter((i) => i >= 0);
  const cs: C[] = rs.map((r) => ({ x: 0, y: 0, r }));
  const pair = (i: number, j: number) => wants.find((w) => w.idx.length === 2 && w.idx.includes(i) && w.idx.includes(j))?.size ?? 0;
  if (live.length >= 2) {
    const [a, b] = live;
    cs[b].x = distanceFor(rs[a], rs[b], pair(a, b));
    if (live.length >= 3) {
      const c = live[2];
      const dac = distanceFor(rs[a], rs[c], pair(a, c)), dbc = distanceFor(rs[b], rs[c], pair(b, c));
      const pts = circleCircle({ x: cs[a].x, y: cs[a].y, r: dac }, { x: cs[b].x, y: cs[b].y, r: dbc });
      if (pts.length) { cs[c].x = pts[0].x; cs[c].y = pts[0].y; }
      else { // the two distance constraints cannot both hold: put it on the line, as close to both as possible
        const dab = cs[b].x; cs[c].x = dac + dbc > dab ? (dac > dab + dbc ? cs[b].x + dbc : dbc > dab + dac ? cs[a].x - dac : (dac + dab - dbc) / 2) : (dac + dab - dbc) / 2; cs[c].y = 0;
      }
    }
    // gradient descent on circle centres, finite differences, backtracking step
    const liveW = wants.filter((w) => w.idx.every((i) => rs[i] > 0));
    let step = Math.max(...rs) * 0.05, cur = loss(cs, liveW);
    const h = Math.max(...rs) * 1e-4;
    for (let it = 0; it < 300 && step > 1e-6; it++) {
      const g: number[] = [];
      for (const i of live) for (const k of ["x", "y"] as const) { const o = cs[i][k]; cs[i][k] = o + h; const l1 = loss(cs, liveW); cs[i][k] = o; g.push((l1 - cur) / h); }
      const gn = Math.hypot(...g) || 1;
      let gi = 0; const before = live.map((i) => ({ x: cs[i].x, y: cs[i].y }));
      for (const i of live) { cs[i].x -= (step * g[gi++]) / gn; cs[i].y -= (step * g[gi++]) / gn; }
      const next = loss(cs, liveW);
      if (next < cur) { cur = next; step *= 1.2; } else { live.forEach((i, j) => { cs[i].x = before[j].x; cs[i].y = before[j].y; }); step *= 0.5; }
    }
  }
  return cs;
}

// ------------------------------------------------------------------------------------------------ component

export function Venn({ cells, S, A, B, defs, scale, sel, onSel, height }: { cells: Cells; S: Arm; A: Arm | null; B: Arm | null; defs: BucketDef[]; scale: Scale; sel: Sel; onSel: (s: Sel) => void; height?: number }) {
  const { tip, show, hide, hostRef } = useTip();
  const w = useWidth(hostRef, 820);
  const H = height ?? 400, PADX = 16, PADT = 30, PADB = 30;
  const arms = [S, A, B].filter((a): a is Arm => !!a); // bit order: S, A, B
  const n = arms.length;

  const model = useMemo(() => {
    // counts per membership mask (bit i = arm i called it responsive) over the judged population; gray separately
    const byMask = new Map<number, number>();
    let gray = 0, total = 0;
    for (const [k, c] of cells) {
      const [s, a, b] = k.split("|");
      const labs = [Number(s), ...(A ? [Number(a)] : []), ...(B ? [Number(b)] : [])];
      if (labs.some((l) => l < 0)) { gray += c; continue; }
      let m = 0; labs.forEach((l, i) => { if (l === 1) m |= 1 << i; });
      byMask.set(m, (byMask.get(m) ?? 0) + c); total += c;
    }
    const sz = (x: number) => (scale === "sqrt" ? Math.sqrt(x) : x);
    const setSize = (i: number) => [...byMask].filter(([m]) => m & (1 << i)).reduce((s, [, c]) => s + c, 0);
    const inter = (idx: number[]) => [...byMask].filter(([m]) => idx.every((i) => m & (1 << i))).reduce((s, [, c]) => s + c, 0);
    const areas = arms.map((_, i) => sz(setSize(i)));
    const wants: Want[] = [];
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) wants.push({ idx: [i, j], size: sz(inter([i, j])) });
    if (n === 3) wants.push({ idx: [0, 1, 2], size: sz(inter([0, 1, 2])) });
    const cs = layout(areas, wants);
    // universe box: area = all judged units, aspect of the plot; grown if the circles do not fit (then the outside is overstated)
    const live = cs.filter((c) => c.r > 0);
    const bb = live.length ? { x0: Math.min(...live.map((c) => c.x - c.r)), x1: Math.max(...live.map((c) => c.x + c.r)), y0: Math.min(...live.map((c) => c.y - c.r)), y1: Math.max(...live.map((c) => c.y + c.r)) } : { x0: 0, x1: 1, y0: 0, y1: 1 };
    const grayR = Math.sqrt(sz(gray) / Math.PI);
    const plotW = w - 2 * PADX, plotH = H - PADT - PADB;
    const aspect = Math.max(1, (plotW - (gray ? plotW * 0.18 : 0)) / plotH);
    const uArea = sz(total);
    let uw = Math.sqrt(uArea * aspect), uh = uw / aspect;
    const pad = 0.06 * Math.max(bb.x1 - bb.x0, bb.y1 - bb.y0);
    let grown = false;
    if (bb.x1 - bb.x0 + 2 * pad > uw) { uw = bb.x1 - bb.x0 + 2 * pad; grown = true; }
    if (bb.y1 - bb.y0 + 2 * pad > uh) { uh = bb.y1 - bb.y0 + 2 * pad; grown = true; }
    const totalW = uw + (gray ? 2 * grayR + uw * 0.08 : 0);
    const f = Math.min(plotW / totalW, plotH / uh); // px per unit length
    const ux = PADX, uy = PADT + (plotH - uh * f) / 2;
    const shift = { x: ux + (uw * f) / 2 - ((bb.x0 + bb.x1) / 2) * f, y: uy + (uh * f) / 2 - ((bb.y0 + bb.y1) / 2) * f };
    const px: C[] = cs.map((c) => ({ x: c.x * f + shift.x, y: c.y * f + shift.y, r: c.r * f }));
    const box = { x: ux, y: uy, w: uw * f, h: uh * f };
    const grayC: C | null = gray ? { x: box.x + box.w + uw * 0.04 * f + grayR * f, y: box.y + box.h - grayR * f, r: grayR * f } : null;
    const inBox = (p: { x: number; y: number }) => p.x >= box.x && p.x <= box.x + box.w && p.y >= box.y && p.y <= box.y + box.h;
    const maskAt = (p: { x: number; y: number }): number | null => { if (grayC && dist(p, grayC) <= grayC.r) return -1; if (!inBox(p)) return null; let m = 0; px.forEach((c, i) => { if (c.r > 0 && dist(p, c) <= c.r) m |= 1 << i; }); return m; };
    // label anchors: the point of each region farthest from any edge, by grid search
    const best = new Map<number, { x: number; y: number; d: number }>();
    const stepPx = Math.max(3, Math.min(box.w, box.h) / 70);
    for (let x = box.x + stepPx / 2; x < box.x + box.w; x += stepPx) for (let y = box.y + stepPx / 2; y < box.y + box.h; y += stepPx) {
      const p = { x, y }, m = maskAt(p)!;
      let d = Math.min(x - box.x, box.x + box.w - x, y - box.y, box.y + box.h - y);
      for (const c of px) if (c.r > 0) d = Math.min(d, Math.abs(dist(p, c) - c.r));
      const b = best.get(m); if (!b || d > b.d) best.set(m, { x, y, d });
    }
    const fit = wants.length ? Math.sqrt(loss(cs, wants) / wants.length) : 0; // rms overlap error, in area units (= units when linear)
    return { byMask, gray, total, px, box, grayC, maskAt, best, grown, fit, areas };
  }, [cells, n, scale, w, H, arms.map((a) => a.id).join()]); // eslint-disable-line react-hooks/exhaustive-deps

  const { byMask, gray, total, px, box, grayC, maskAt, best, grown, fit } = model;
  const keyOf = (m: number): BucketKey => { if (m < 0) return "gray"; const sL = ((m & 1) ? 1 : 0) as Lab; const aL = A ? (((m & 2) ? 1 : 0) as Lab) : sL; const bBit = A ? 4 : 2; return bucketOf(sL, aL, B ? (((m & bBit) ? 1 : 0) as Lab) : null); };
  const defOf = (k: BucketKey) => defs.find((d) => d.key === k);
  const selKey = sel?.kind === "bucket" ? sel.key : null;
  const [hover, setHover] = useState<number | null>(null); // membership mask of the region under the pointer (-1 gray), tinted so it reads as clickable
  const svgRef = useRef<SVGSVGElement>(null);
  const pointer = (e: React.MouseEvent) => { const r = svgRef.current!.getBoundingClientRect(); return { x: e.clientX - r.left, y: e.clientY - r.top }; };
  const onMove = (e: React.MouseEvent) => {
    const p = pointer(e), m = maskAt(p);
    if (m == null) { setHover(null); hide(); return; }
    if (m !== hover) setHover(m);
    const k = keyOf(m), d = defOf(k), c = m < 0 ? gray : byMask.get(m) ?? 0;
    const tipc: TipContent = { title: d?.label ?? k, value: fmtN(c), unit: `${fmtShare(c / (total + gray || 1))} of all`, lines: arms.map((a, i) => [a.short, m < 0 ? "gray" : m & (1 << i) ? "responsive" : "not responsive"] as [string, string]) };
    const hr = hostRef.current?.getBoundingClientRect();
    show(e, { kind: "mark", x: e.clientX - (hr?.left ?? 0), y: e.clientY - (hr?.top ?? 0), r: 8 }, tipc);
  };
  const onClick = (e: React.MouseEvent) => { const m = maskAt(pointer(e)); if (m != null) onSel({ kind: "bucket", key: keyOf(m) }); };

  // every region present in the data, for labels and the selection overlay
  const regions = [...byMask.entries()].filter(([, c]) => c > 0).map(([m]) => m);
  const maskIds = hover != null && hover >= 0 && !regions.includes(hover) ? [...regions, hover] : regions; // the hovered region may be empty (no units) yet still need its mask
  const selMasks = selKey === "gray" ? [-1] : regions.filter((m) => keyOf(m) === selKey);
  const circleClip = (i: number, child: React.ReactNode) => <g clipPath={`url(#venn-c${i})`}>{child}</g>;
  const regionShape = (m: number, fill: string) => {
    const inc = arms.map((_, i) => i).filter((i) => m & (1 << i) && px[i].r > 0), exc = arms.map((_, i) => i).filter((i) => !(m & (1 << i)) && px[i].r > 0);
    let node: React.ReactNode = <rect x={box.x} y={box.y} width={box.w} height={box.h} fill={fill} mask={exc.length ? `url(#venn-m${m})` : undefined} />;
    for (const i of inc) node = circleClip(i, node);
    return <g key={m}>{node}</g>;
  };

  return (
    <div ref={hostRef} data-tip-host style={{ position: "relative" }}>
      <svg ref={svgRef} width={w} height={H} className="study-svg" onMouseMove={onMove} onMouseLeave={() => { setHover(null); hide(); }} onClick={onClick} style={{ cursor: "pointer" }}>
        <defs>
          <pattern id="venn-hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="6" stroke="var(--ink)" strokeWidth="1.2" /></pattern>
          {px.map((c, i) => <clipPath key={i} id={`venn-c${i}`}><circle cx={c.x} cy={c.y} r={Math.max(0, c.r)} /></clipPath>)}
          {maskIds.map((m) => <mask key={m} id={`venn-m${m}`}><rect x={0} y={0} width={w} height={H} fill="white" />{px.map((c, i) => (!(m & (1 << i)) && c.r > 0 ? <circle key={i} cx={c.x} cy={c.y} r={c.r} fill="black" /> : null))}</mask>)}
        </defs>
        <rect x={box.x} y={box.y} width={box.w} height={box.h} fill="var(--bg-2)" stroke="var(--line-2)" rx={4} />
        {px.map((c, i) => c.r > 0 && <circle key={i} cx={c.x} cy={c.y} r={c.r} fill={arms[i].color} fillOpacity={0.26} stroke={arms[i].color} strokeWidth={1.4} />)}
        {hover != null && (hover < 0 ? (grayC && <circle cx={grayC.x} cy={grayC.y} r={grayC.r} fill="var(--ink)" fillOpacity={0.16} style={{ pointerEvents: "none" }} />) : <g fillOpacity={0.16} style={{ pointerEvents: "none" }}>{regionShape(hover, "var(--ink)")}</g>)}
        {selKey != null && ( // the regions not selected fade behind the panel colour, so the selection stands out
          <g fillOpacity={0.55} style={{ pointerEvents: "none" }}>
            {regions.filter((m) => keyOf(m) !== selKey).map((m) => regionShape(m, "var(--panel)"))}
          </g>
        )}
        {selMasks.map((m) => (m < 0 && grayC ? <circle key="g" cx={grayC.x} cy={grayC.y} r={grayC.r} fill="url(#venn-hatch)" /> : regionShape(m, "url(#venn-hatch)")))}
        {/* keyboard targets: one focusable point per region (its label anchor) and the gray circle; focus tints the region as hover does, Enter selects */}
        {[...regions.map((m) => ({ m, p: best.get(m), c: byMask.get(m) ?? 0 })), ...(grayC ? [{ m: -1, p: { x: grayC.x, y: grayC.y }, c: gray }] : [])].map(({ m, p, c }) => {
          if (!p) return null;
          const k = keyOf(m);
          return <circle key={`k${m}`} cx={p.x} cy={p.y} r={10} fill="transparent" {...hitProps(`${defOf(k)?.label ?? k}: ${fmtN(c)}`, () => onSel({ kind: "bucket", key: k }))} onClick={undefined} style={{ pointerEvents: "none" }} onFocus={() => setHover(m)} onBlur={() => setHover(null)} />;
        })}
        {regions.map((m) => { const b = best.get(m); const c = byMask.get(m) ?? 0; if (!b || b.d < 11 || m === 0) return null; const on = selKey != null && keyOf(m) === selKey; return <text key={m} x={b.x} y={b.y + 4} textAnchor="middle" fontSize={b.d < 16 ? 10 : 11.5} fontWeight={on ? 600 : 400} fill="var(--ink)" style={{ pointerEvents: "none", paintOrder: "stroke", stroke: "var(--panel)", strokeWidth: 3, strokeLinejoin: "round" }}>{fmtN(c)}</text>; })}
        {(() => { let x = PADX; return arms.map((a, i) => { const label = `${a.short}${a.planned ? " · placeholder" : ""} · ${fmtN([...byMask].filter(([m]) => m & (1 << i)).reduce((s, [, k]) => s + k, 0))}`; const x0 = x; x += label.length * 6.2 + 30; return <g key={a.id}><rect x={x0} y={8} width={10} height={10} rx={2} fill={a.color} fillOpacity={0.4} stroke={a.color} /><text x={x0 + 15} y={17} fontSize={11.5} fill="var(--ink-2)">{label}</text></g>; }); })()}
        <text x={box.x + 8} y={box.y + box.h - 8} fontSize={11} fill="var(--ink-3)" style={{ pointerEvents: "none" }}>nobody responsive · {fmtN(byMask.get(0) ?? 0)}</text>
        {grayC && (
          <g>
            <circle cx={grayC.x} cy={grayC.y} r={grayC.r} fill="var(--ink-4)" fillOpacity={selKey != null && selKey !== "gray" ? 0.14 : 0.35} stroke="var(--ink-4)" strokeDasharray="3 3" />
            <text x={grayC.x} y={grayC.y - grayC.r - 6} textAnchor="middle" fontSize={11} fill="var(--ink-3)" style={{ pointerEvents: "none" }}>gray · {fmtN(gray)}</text>
          </g>
        )}
        <text x={0} y={H - 4} fontSize={11} fill="var(--ink-4)">Area ∝ {scale === "sqrt" ? "square root of " : ""}units: each circle is an arm's responsive calls, the box is everyone judged{grown ? " (box enlarged to fit the circles)" : ""}. {n === 3 ? (scale === "linear" ? `Overlaps fitted to ±${fmtN(Math.round(fit))} units (rms).` : "Overlaps fitted by least squares.") : "Overlap exact."}</text>
      </svg>
      <TipBox tip={tip} hint="click to list" />
    </div>
  );
}
