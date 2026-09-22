import { createContext, useContext, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";

export type TipLine = string | [string, string];
/**
 * What a hover tooltip is anchored to, in host pixels. A `row` spans the chart's width: the tooltip sits beside the pointer only where that
 * leaves the row's bars and figures (everything left of `clearX`) uncovered, otherwise just outside the card. A `mark` is a point: above-right.
 */
export type TipAnchor = { kind: "row"; top: number; height: number; clearX: number } | { kind: "mark"; x: number; y: number; r: number };
/** A compact hover tooltip: the name, the chart's primary value (`value` + `unit`, or the `lines` pairs) and one secondary `sub` line. */
export type TipContent = { title: string; color?: string; icon?: ReactNode; value?: string; unit?: string; lines?: TipLine[]; sub?: string };
export type Tip = (TipContent & { x: number; y: number; anchor: TipAnchor }) | null;

/** How long the pointer rests on a row or mark before its tooltip opens; sweeping across rows never shows one. */
export const TIP_DELAY_MS = 220;

/** One absolutely positioned tooltip per chart; coordinates are relative to the nearest [data-tip-host]. Opens after TIP_DELAY_MS on one target, closes at once on leave. */
export function useTip() {
  const [tip, setTip] = useState<Tip>(null);
  const hostRef = useRef<HTMLDivElement>(null);
  const timer = useRef<number | null>(null);
  const pending = useRef<NonNullable<Tip> | null>(null);
  const shown = useRef<string | null>(null);
  const cancel = () => { if (timer.current != null) { clearTimeout(timer.current); timer.current = null; } pending.current = null; };
  useEffect(() => cancel, []);
  const hide = () => { cancel(); shown.current = null; setTip(null); };
  // A row can slide out from under a resting pointer without a mouseleave (page load, scroll, resize), so while a tooltip is open any pointer
  // movement outside the host closes it.
  useEffect(() => {
    if (!tip) return;
    const onMove = (e: MouseEvent) => { if (!hostRef.current?.contains(e.target as Node)) hide(); };
    document.addEventListener("mousemove", onMove);
    return () => document.removeEventListener("mousemove", onMove);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tip]);
  const show = (e: { clientX: number; clientY: number }, anchor: TipAnchor, t: TipContent) => {
    if (shown.current === t.title) return; // already open for this target; it stays where it opened
    const host = hostRef.current;
    const r = host ? host.getBoundingClientRect() : { left: 0, top: 0 };
    const next = { x: e.clientX - r.left, y: e.clientY - r.top, anchor, ...t };
    if (pending.current?.title === t.title) { pending.current = next; return; } // still resting on the same target: keep the timer, take the latest pointer position
    cancel();
    pending.current = next;
    timer.current = window.setTimeout(() => {
      timer.current = null;
      const p = pending.current;
      pending.current = null;
      if (!p || !hostRef.current?.matches(":hover")) return; // the pointer has gone without a mouseleave
      shown.current = p.title;
      setTip(p);
    }, TIP_DELAY_MS);
  };
  return { tip, show, hide, hostRef };
}

// ------------------------------------------------------------------------------------------------
// Motion. Every animation on the site is either a CSS transition/animation (styles.css, `.mv` and `.fd`, tooltip, popover and modal
// entrances) or one of the two hooks below, and all of it is off under prefers-reduced-motion: the stylesheet zeroes CSS durations, the
// hooks snap.

/** Whether the user asked for reduced motion; follows the media query live (CDP emulation and OS changes included). */
export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() => typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches);
  useEffect(() => {
    const mq = matchMedia("(prefers-reduced-motion: reduce)");
    const on = () => setReduced(mq.matches);
    mq.addEventListener("change", on);
    return () => mq.removeEventListener("change", on);
  }, []);
  return reduced;
}

/** Duration of a chart move, and the ease used for every transition on the site (cubic-bezier(.2,.7,.2,1) in styles.css). */
export const MOVE_MS = 320;
const bezier = (p1: number, p2: number, t: number) => 3 * (1 - t) * (1 - t) * t * p1 + 3 * (1 - t) * t * t * p2 + t * t * t;
export function ease(u: number): number {
  if (u <= 0) return 0;
  if (u >= 1) return 1;
  // solve x(t) = u for the curve's x control points (.2, .2), then read y at t (control points .7, 1)
  let t = u;
  for (let i = 0; i < 8; i++) {
    const x = bezier(0.2, 0.2, t) - u;
    const dx = 3 * (1 - t) * (1 - t) * 0.2 + 3 * t * t * 0.8; // x'(t); the middle term vanishes since both x control points are .2
    if (Math.abs(x) < 1e-5 || dx === 0) break;
    t -= x / dx;
  }
  return bezier(0.7, 1, Math.min(1, Math.max(0, t)));
}

/**
 * A bounded pulsing window: true for `ms` (plus a little slack) after `sig` changes, including on mount, while `enabled`; false otherwise and
 * under prefers-reduced-motion. `sig` is a signature of what the chart shows (ids and point estimates), so the window opens when the plotted
 * set changes and stays shut while it is still. Callers key the animated element on `sig` too, so its CSS animation restarts from the top.
 */
export function usePulseWindow(sig: string, enabled: boolean, ms: number): boolean {
  const reduced = useReducedMotion();
  const [pulsing, setPulsing] = useState(false);
  useEffect(() => {
    if (!enabled || !sig || reduced) { setPulsing(false); return; }
    setPulsing(true);
    const t = window.setTimeout(() => setPulsing(false), ms + 200);
    return () => window.clearTimeout(t);
  }, [enabled, sig, ms, reduced]);
  return pulsing;
}

/** How long the emphasised (Jev) row's tint breathes after a table loads or its rows change: ROW_PULSE_CYCLES cycles of the styles.css row-breathe animation (keep in step with `.row-jev.pulse`). */
export const ROW_PULSE_CYCLES = 3, ROW_PULSE_CYCLE_MS = 1400;
export const ROW_PULSE_MS = ROW_PULSE_CYCLES * ROW_PULSE_CYCLE_MS;

/**
 * The full-width tint behind an emphasised table row (Compare models: the Jev row, `emphasis: true` on the item), drawn first in the row's
 * `.sel` group so the hover band (`.hit`) sits on top; styles.css `.row-jev` is the faint rest tint on the --hl highlight, `.pulse` breathes it
 * for ROW_PULSE_CYCLES cycles. Keyed on `sig` so the animation restarts whenever the table's rows change; hidden while the row is hovered or highlighted (CSS).
 */
export function RowTint({ sig, pulsing, width, height }: { sig: string; pulsing: boolean; width: number; height: number }) {
  return <rect key={`tint:${sig}`} className={pulsing ? "row-jev pulse" : "row-jev"} x={0} y={0} width={width} height={height} rx={2} />;
}

type Tween = { from: Record<string, number>; to: Record<string, number>; t0: number };
const tweenAt = (tw: Tween, now: number, ms: number): Record<string, number> => {
  const e = ms <= 0 ? 1 : ease((now - tw.t0) / ms);
  if (e >= 1) return tw.to;
  const out: Record<string, number> = {};
  for (const k in tw.to) out[k] = tw.from[k] + (tw.to[k] - tw.from[k]) * e;
  return out;
};
const sameValues = (a: Record<string, number>, b: Record<string, number>) => {
  const ka = Object.keys(a), kb = Object.keys(b);
  return ka.length === kb.length && ka.every((k) => a[k] === b[k]);
};

/**
 * SVG geometry that CSS cannot transition (rect width and height, whisker ends, x/y attributes): eases every field of `target` from its
 * displayed value to its new value over `ms`, re-rendering each frame while anything moves. A key that is new (including every key on first
 * paint) starts at `enter(key, value)` when given, so bars can grow from 0; otherwise it appears in place. Retargeting mid-move continues
 * from the current position. A change of `layout` (the chart's measured size) is a re-layout, not a move: the values jump to their
 * entry-or-target positions at the move's current progress, so a chart never slides in from its pre-measurement fallback size and a
 * bar still growing on first paint simply grows toward the corrected width. Snaps under prefers-reduced-motion.
 */
export function useTween(target: Record<string, number>, ms = MOVE_MS, enter?: (key: string, v: number) => number, layout?: unknown): Record<string, number> {
  const reduced = useReducedMotion();
  const [, tick] = useState(0);
  const ref = useRef<Tween | null>(null);
  const lastLayout = useRef(layout);
  const now = performance.now();
  const dur = reduced ? 0 : ms;
  const entry = (k: string) => (enter ? enter(k, target[k]) : target[k]);
  if (!ref.current) {
    const from: Record<string, number> = {};
    for (const k in target) from[k] = entry(k);
    ref.current = { from, to: target, t0: now };
  } else if (lastLayout.current !== layout) {
    const from: Record<string, number> = {};
    for (const k in target) from[k] = entry(k);
    ref.current = { from, to: target, t0: ref.current.t0 };
  } else if (!sameValues(ref.current.to, target)) {
    const { from: f0, to: t0 } = ref.current;
    if (Object.keys(target).every((k) => t0[k] === target[k])) {
      // only keys left (a faded-out item was dropped): prune without restarting the clock, so a move in flight keeps its pace
      const from: Record<string, number> = {}, to: Record<string, number> = {};
      for (const k in target) { from[k] = f0[k]; to[k] = t0[k]; }
      ref.current = { from, to, t0: ref.current.t0 };
    } else {
      const cur = tweenAt(ref.current, now, dur);
      const from: Record<string, number> = {};
      for (const k in target) from[k] = k in cur ? cur[k] : entry(k);
      ref.current = { from, to: target, t0: now };
    }
  }
  lastLayout.current = layout;
  const tw = ref.current;
  const moving = dur > 0 && now - tw.t0 < dur;
  useEffect(() => {
    if (!moving) return;
    const id = requestAnimationFrame(() => tick((n) => n + 1));
    return () => cancelAnimationFrame(id);
  });
  return tweenAt(tw, now, dur);
}

export type Presence<T> = { item: T; key: string; state: "enter" | "present" | "exit" };
/**
 * Keeps items in the render for `ms` after they leave (state "exit", for a fade-out) and marks items on their first frame "enter" (so a
 * fade-in has an opacity-0 frame to start from). The order is the order items first appeared, not the order given: a keyed element must keep
 * its place in the DOM for its CSS transitions to run (React moves a node whose index changes, which resets them), so callers draw in this
 * order and place rows by transform. Under prefers-reduced-motion everything is simply "present" and leavers are dropped at once.
 */
export function usePresence<T>(items: T[], keyOf: (t: T) => string, ms = 480): Presence<T>[] {
  const reduced = useReducedMotion();
  const [, tick] = useState(0);
  const reg = useRef(new Map<string, { item: T; fresh: boolean; exitAt: number | null }>());
  const now = performance.now();
  const live = new Set<string>();
  for (const item of items) {
    const k = keyOf(item);
    live.add(k);
    const e = reg.current.get(k);
    if (!e) reg.current.set(k, { item, fresh: !reduced, exitAt: null });
    else { e.item = item; e.exitAt = null; }
  }
  for (const [k, e] of reg.current) {
    if (live.has(k)) continue;
    if (e.exitAt == null) e.exitAt = now;
    if (reduced || now - e.exitAt >= ms) reg.current.delete(k);
  }
  const out: Presence<T>[] = [];
  let lastExit = 0;
  for (const [k, e] of reg.current) {
    out.push({ item: e.item, key: k, state: e.exitAt != null ? "exit" : e.fresh ? "enter" : "present" });
    if (e.exitAt != null) lastExit = Math.max(lastExit, e.exitAt);
  }
  const hasFresh = out.some((o) => o.state === "enter");
  // "enter" flips to "present" once the browser has painted the opacity-0 frame: two frames, or 60 ms if frames are throttled. Keyed on the
  // flag, not every render, so a tween re-rendering each frame cannot keep postponing it.
  useEffect(() => {
    if (!hasFresh) return;
    const flip = () => { for (const e of reg.current.values()) e.fresh = false; tick((n) => n + 1); };
    let f2 = 0;
    const f1 = requestAnimationFrame(() => { f2 = requestAnimationFrame(flip); });
    const t = window.setTimeout(flip, 60);
    return () => { cancelAnimationFrame(f1); cancelAnimationFrame(f2); clearTimeout(t); };
  }, [hasFresh]);
  // leavers are dropped on the render after their fade; one timer per departure
  useEffect(() => {
    if (!lastExit) return;
    const t = window.setTimeout(() => tick((n) => n + 1), Math.max(0, ms - (performance.now() - lastExit)) + 5);
    return () => clearTimeout(t);
  }, [lastExit, ms]);
  return out;
}

/** Inline style for a presence state: the `.fd` class transitions opacity over 480 ms (styles.css). */
export const fadeStyle = (state: Presence<unknown>["state"]): React.CSSProperties => ({ opacity: state === "present" ? 1 : 0, pointerEvents: state === "exit" ? "none" : undefined });

/** The small muted "DECIDER" tag after a decider's name in the modals (data.ts isDecider). */
export function DeciderTag() {
  return <span className="decider-tag" title="A decider model (Jev, Laya): answers typed questions with probabilities, writes no text">decider</span>;
}

// Text measurement for SVG labels, on a canvas in the page's font. Cached per string; the cache is dropped and subscribers re-render when a
// web font finishes loading, since a measurement taken in the fallback face is wrong by a few pixels.
let measureCtx: CanvasRenderingContext2D | null = null;
let measureFont: string | null = null;
const widthCache = new Map<string, number>();
const fontListeners = new Set<() => void>();
if (typeof document !== "undefined" && document.fonts) {
  document.fonts.addEventListener("loadingdone", () => { widthCache.clear(); measureFont = null; fontListeners.forEach((f) => f()); });
}
/** Advance width of `text` at `px` pixels in the body's font family; 6.3 px per character when canvas is unavailable. */
export function textWidth(text: string, px = 12): number {
  const key = `${px}|${text}`;
  const hit = widthCache.get(key);
  if (hit != null) return hit;
  measureCtx ??= typeof document === "undefined" ? null : document.createElement("canvas").getContext("2d");
  if (!measureCtx) return text.length * 6.3;
  measureFont ??= getComputedStyle(document.body).fontFamily || "sans-serif";
  measureCtx.font = `${px}px ${measureFont}`;
  const w = measureCtx.measureText(text).width;
  widthCache.set(key, w);
  return w;
}
/** Re-renders the caller when a web font finishes loading, so labels measured with `textWidth` are re-measured in the loaded face. */
export function useFontMetrics(): void {
  const [, tick] = useState(0);
  useEffect(() => {
    const f = () => tick((n) => n + 1);
    fontListeners.add(f);
    return () => { fontListeners.delete(f); };
  }, []);
}

/**
 * The decider marker on a chart row (data.ts isDecider): a hairline rectangle around the row's label cell (logo and name), 1px in the
 * model's colour at 55% opacity, 3px radius, no fill; about 3px of air left and right of the label, 2px above and below the text. The label
 * is drawn with its logo centred at x = 8 and its text at `textX`, baseline `cy + 4`, 12px; the frame's width follows the measured text.
 */
/** Decider rows (data.ts isDecider) set their name a step heavier and in full ink; there is no other marker in the tables. */
export const DECIDER_TEXT = { fill: "var(--ink)", fontWeight: 500 } as const;

/** Measured content box of the host element. */
export function useSize(hostRef: React.RefObject<HTMLDivElement | null>, fallback: { w: number; h: number }): { w: number; h: number } {
  const [sz, setSz] = useState(fallback);
  useEffect(() => {
    const el = hostRef.current;
    if (!el) return;
    const upd = (w: number, h: number) => { if (w && h) setSz((p) => (p.w === w && p.h === h ? p : { w, h })); };
    const ro = new ResizeObserver((es) => { const r = es[0]?.contentRect; if (r) upd(r.width, r.height); });
    ro.observe(el);
    const r = el.getBoundingClientRect(); upd(r.width, r.height);
    return () => ro.disconnect();
  }, [hostRef]);
  return sz;
}

/** Measured content width of the host element, so SVG charts can draw at native pixel scale instead of stretching a viewBox. */
export function useWidth(hostRef: React.RefObject<HTMLDivElement | null>, fallback: number): number {
  const [w, setW] = useState(fallback);
  useEffect(() => {
    const el = hostRef.current;
    if (!el) return;
    const ro = new ResizeObserver((es) => { const cw = es[0]?.contentRect.width; if (cw) setW(cw); });
    ro.observe(el);
    const cw = el.getBoundingClientRect().width;
    if (cw) setW(cw);
    return () => ro.disconnect();
  }, [hostRef]);
  return w;
}

/**
 * Props for an SVG row or mark that opens something on click (the details modal): pointer cursor, button role, Enter/Space, and the `sel` class
 * whose `.hit` child (the transparent full-row rect behind the row) tints on hover. Without `onSelect` the element stays inert.
 */
export function selectable<T>(onSelect: ((t: T) => void) | undefined, t: T, label: string) {
  if (!onSelect) return { style: { cursor: "default" } as React.CSSProperties };
  return {
    className: "sel", role: "button" as const, tabIndex: 0, "aria-label": `${label}: details`, style: { cursor: "pointer" } as React.CSSProperties,
    onClick: (e: React.MouseEvent) => { e.stopPropagation(); onSelect(t); },
    onKeyDown: (e: React.KeyboardEvent) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.stopPropagation(); onSelect(t); } },
  };
}

/** The muted last line of a chart tooltip when its rows open the details modal. */
export const CLICK_HINT = "click for details";

/**
 * Placement. Rows: 14px right of the pointer, vertically centred on the row, clamped to the viewport; where that would cover the row's bars
 * or figures the box moves just outside the card's right edge (left edge when the viewport ends), and just below the row (above it at the
 * bottom of the viewport) when neither fits. Marks: above-right of the mark, flipping left or below at the viewport. The hovered row or
 * mark is never covered.
 */
export function TipBox({ tip, hint }: { tip: Tip; hint?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!tip || !el) { setPos(null); return; }
    const host = el.parentElement!;
    const hr = host.getBoundingClientRect();
    const card = host.closest(".card")?.getBoundingClientRect() ?? hr;
    const w = el.offsetWidth, h = el.offsetHeight;
    const M = 8, GAP = 14;
    // viewport bounds in host coordinates
    const vx0 = M - hr.left, vx1 = window.innerWidth - M - hr.left, vy0 = M - hr.top, vy1 = window.innerHeight - M - hr.top;
    const clampX = (l: number) => Math.min(Math.max(l, vx0), vx1 - w);
    const clampY = (t: number) => Math.min(Math.max(t, vy0), vy1 - h);
    const a = tip.anchor;
    if (a.kind === "mark") {
      let left = a.x + a.r + 6;
      if (left + w > vx1) left = a.x - a.r - 6 - w;
      let top = a.y - a.r - 6 - h;
      if (top < vy0) top = a.y + a.r + 6;
      setPos({ left: clampX(left), top: clampY(top) });
      return;
    }
    const top = clampY(a.top + a.height / 2 - h / 2);
    let left = tip.x + GAP;
    if (left >= a.clearX && left + w <= vx1) { setPos({ left, top }); return; }
    const outsideR = card.right - hr.left + 10, outsideL = card.left - hr.left - 10 - w;
    if (outsideR + w <= vx1) { setPos({ left: outsideR, top }); return; }
    if (outsideL >= vx0) { setPos({ left: outsideL, top }); return; }
    const below = a.top + a.height + 6;
    setPos({ left: clampX(left), top: below + h <= vy1 ? below : Math.max(vy0, a.top - 6 - h) });
  }, [tip]);
  if (!tip) return null;
  return (
    <div ref={ref} className="tip" style={{ left: pos?.left ?? 0, top: pos?.top ?? 0, visibility: pos ? "visible" : "hidden" }}>
      <div className="t">
        {tip.icon ? <span className="ic" style={{ color: tip.color }}>{tip.icon}</span> : tip.color ? <span className="sw" style={{ background: tip.color }} /> : null}
        {tip.title}
      </div>
      {tip.value && <div className="val"><span className="n">{tip.value}</span>{tip.unit && <span className="u">{tip.unit}</span>}</div>}
      {tip.lines?.map((l, i) =>
        typeof l === "string" ? (
          <div key={i} className="line">{l}</div>
        ) : (
          <div key={i} className="kv"><span className="k">{l[0]}</span><span className="v">{l[1]}</span></div>
        ),
      )}
      {tip.sub && <div className="sub">{tip.sub}</div>}
      {hint && <div className="cta">{hint}</div>}
    </div>
  );
}

/** Opens the Method modal (App owns its state); `Hint`'s `more` link calls it. */
export const MethodContext = createContext<() => void>(() => {});

/**
 * The modal chrome shared with the details modal (Explain.tsx, which still renders it inline): dimmed backdrop that closes on an
 * outside mousedown, Esc to close, body scroll locked while open, and a header with eyebrow, title, optional controls and ×.
 * `className` is added to the box (e.g. to change its size); the children fill the rest of the box.
 */
export function Modal({ eyebrow, title, controls, onClose, className, children }: { eyebrow?: string; title: string; controls?: ReactNode; onClose: () => void; className?: string; children: ReactNode }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onClose]);
  useEffect(() => { document.body.style.overflow = "hidden"; return () => { document.body.style.overflow = ""; }; }, []);
  return (
    <div className="ex-back" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className={`ex-modal${className ? ` ${className}` : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="ex-head">
          <div>
            {eyebrow && <div className="ex-eyebrow">{eyebrow}</div>}
            <h2>{title}</h2>
          </div>
          <div className="ex-head-ctl">
            {controls}
            <button className="ex-close" onClick={onClose} aria-label="close">×</button>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

export type HintItem = { k: string; v: ReactNode };

/** Where an anchored popover goes: `l` left-aligned to its anchor (else right-aligned), `up` above it (else below); `left`/`top` are the same placement in viewport pixels for a position: fixed box. */
export type PopPlace = { l: boolean; up: boolean; left: number; top: number };
/**
 * Placement of a popover hanging off `anchor`, measured once it is in the DOM (`open`). `prefer` is the horizontal alignment when both fit:
 * `right` (right edges flush, the popover extends left; the Hint icon at a card's right edge) or `left` (left edges flush, it extends right;
 * the title menus). The other alignment is used when the preferred one would leave the viewport, or when neither fits, whichever side the anchor
 * has more room on. Below the anchor unless that leaves the viewport and above fits (or has more room). `null` until measured.
 */
export function usePopPlace(open: boolean, anchor: React.RefObject<HTMLElement | null>, pop: React.RefObject<HTMLElement | null>, prefer: "left" | "right" = "right"): PopPlace | null {
  const [place, setPlace] = useState<PopPlace | null>(null);
  useLayoutEffect(() => {
    if (!open) { setPlace(null); return; }
    const w = anchor.current, p = pop.current;
    if (!w || !p) return;
    const a = w.getBoundingClientRect();
    const pw = p.offsetWidth, ph = p.offsetHeight;
    const M = 8, GAP = 7;
    const fitsL = a.left + pw <= window.innerWidth - M; // left-aligned: extends right
    const fitsR = a.right - pw >= M; // right-aligned: extends left
    const leftHalf = a.left + a.right < window.innerWidth;
    const l = prefer === "left" ? fitsL || (!fitsR && leftHalf) : !fitsR && (fitsL || leftHalf);
    const up = a.bottom + GAP + ph > window.innerHeight - M && (a.top - GAP - ph >= M || a.top > window.innerHeight - a.bottom);
    const left = Math.max(M, Math.min(l ? a.left : a.right - pw, window.innerWidth - M - pw));
    const top = Math.max(M, up ? a.top - GAP - ph : a.bottom + GAP);
    setPlace({ l, up, left, top });
  }, [open, prefer, anchor, pop]);
  return place;
}

/** Closes an open popover on a pointerdown outside `wrap` or on Esc; the Esc is stopped so an enclosing modal's Esc handler does not fire too. */
export function usePopDismiss(open: boolean, wrap: React.RefObject<HTMLElement | null>, close: () => void): void {
  const closeRef = useRef(close);
  closeRef.current = close;
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => { if (!wrap.current?.contains(e.target as Node)) closeRef.current(); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") { e.stopPropagation(); closeRef.current(); } };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("pointerdown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open, wrap]);
}

/**
 * The "i" control in card headers and the control bar. Click opens a small anchored popover (no hover behaviour) that closes on outside click,
 * Esc, or clicking the icon again. Content is either structured `items` (a compact label/value list, one short sentence per value) or a legacy
 * `text` paragraph. `title` defaults to the enclosing card's title. `more` is the label of a link that opens the Method modal.
 * The popover hangs below the icon, right-aligned to it, and flips to left-aligned (or above) when that would leave the viewport.
 */
export function Hint({ text, items, more, title }: { text?: string; items?: HintItem[]; more?: string; title?: string }) {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLSpanElement>(null);
  const pop = useRef<HTMLDivElement>(null);
  // right-aligned to the icon unless that would leave the viewport, below unless it would (usePopPlace); the .l / .up classes place it
  const place = usePopPlace(open, wrap, pop, "right");
  const [cardTitle, setCardTitle] = useState<string | undefined>(undefined);
  const openMethod = useContext(MethodContext);
  useLayoutEffect(() => {
    if (title === undefined) setCardTitle(wrap.current?.closest(".card-t")?.querySelector("h3")?.textContent ?? undefined);
  }, [title]);
  usePopDismiss(open, wrap, () => setOpen(false));
  const t = title ?? cardTitle;
  return (
    <span ref={wrap} className={`hint${open ? " open" : ""}`}>
      <button type="button" className="i" aria-label={t ? `About ${t}` : "About this"} aria-expanded={open} onClick={() => setOpen((o) => !o)}>i</button>
      {open && (
        <div ref={pop} role="dialog" aria-label={t} className={`pop${place?.l ? " l" : ""}${place?.up ? " up" : ""}`} style={{ visibility: place ? "visible" : "hidden" }}>
          {t && <div className="t">{t}</div>}
          {items && (
            <dl>
              {items.map((it, i) => <div key={i} className="row"><dt>{it.k}</dt><dd>{it.v}</dd></div>)}
            </dl>
          )}
          {text && <p>{text}</p>}
          {more && <button type="button" className="more" onClick={() => { setOpen(false); openMethod(); }}>{more}</button>}
        </div>
      )}
    </span>
  );
}

export function Seg<T extends string>({ value, onChange, options }: { value: T; onChange: (v: T) => void; options: { id: T; label: string; title?: string }[] }) {
  return (
    <span className="seg" role="radiogroup">
      {options.map((o) => (
        <button key={o.id} className={o.id === value ? "on" : ""} onClick={() => onChange(o.id)} title={o.title} role="radio" aria-checked={o.id === value}>
          {o.label}
        </button>
      ))}
    </span>
  );
}

export function Control({ label, children }: { label: string; children: ReactNode }) {
  return (
    <span className="control">
      <span className="lab">{label}</span>
      {children}
    </span>
  );
}
