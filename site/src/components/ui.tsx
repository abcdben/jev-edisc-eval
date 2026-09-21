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
  const [place, setPlace] = useState<{ l: boolean; up: boolean } | null>(null);
  const [cardTitle, setCardTitle] = useState<string | undefined>(undefined);
  const openMethod = useContext(MethodContext);
  useLayoutEffect(() => {
    if (!open) { setPlace(null); return; }
    const w = wrap.current, p = pop.current;
    if (!w || !p) return;
    const a = w.getBoundingClientRect();
    const pw = p.offsetWidth, ph = p.offsetHeight;
    const M = 8;
    // right-aligned to the icon unless that would leave the viewport; then left-aligned if that fits, or if the icon is in the left half
    const l = a.right - pw < M && (a.left + pw <= window.innerWidth - M || a.left + a.right < window.innerWidth);
    // below unless it would leave the viewport; then above if that fits, or whichever side has more room
    const up = a.bottom + 8 + ph > window.innerHeight - M && (a.top - 8 - ph >= M || a.top > window.innerHeight - a.bottom);
    setPlace({ l, up });
  }, [open]);
  useLayoutEffect(() => {
    if (title === undefined) setCardTitle(wrap.current?.closest(".card-t")?.querySelector("h3")?.textContent ?? undefined);
  }, [title]);
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => { if (!wrap.current?.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("pointerdown", onDown); document.removeEventListener("keydown", onKey); };
  }, [open]);
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
