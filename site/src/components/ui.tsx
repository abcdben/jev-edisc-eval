import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";

export type TipLine = string | [string, string];
export type Tip = { x: number; y: number; title: string; color?: string; lines: TipLine[]; notes?: string[] } | null;

/** One absolutely positioned tooltip per chart; coordinates are relative to the nearest [data-tip-host]. */
export function useTip() {
  const [tip, setTip] = useState<Tip>(null);
  const hostRef = useRef<HTMLDivElement>(null);
  const show = (e: { clientX: number; clientY: number }, t: Omit<NonNullable<Tip>, "x" | "y">) => {
    const host = hostRef.current;
    const r = host ? host.getBoundingClientRect() : { left: 0, top: 0, width: 0 };
    // cursor position relative to the host; TipBox measures itself and flips left when it would overflow
    setTip({ x: e.clientX - r.left, y: e.clientY - r.top, ...t });
  };
  return { tip, show, hide: () => setTip(null), hostRef };
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

export function TipBox({ tip, hint }: { tip: Tip; hint?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!tip || !el) { setPos(null); return; }
    const host = el.parentElement!.getBoundingClientRect();
    const w = el.offsetWidth, h = el.offsetHeight;
    const GAP = 10;
    let left = tip.x + GAP;
    if (left + w > host.width) left = Math.max(0, tip.x - GAP - w);
    let top = tip.y + GAP;
    if (host.top + top + h > window.innerHeight - 8) top = Math.max(0, tip.y - GAP - h);
    setPos({ left, top });
  }, [tip]);
  if (!tip) return null;
  return (
    <div ref={ref} className="tip" style={{ left: pos?.left ?? tip.x + 10, top: pos?.top ?? tip.y + 10, visibility: pos ? "visible" : "hidden" }}>
      <div className="t">
        {tip.color && <span className="sw" style={{ background: tip.color }} />}
        {tip.title}
      </div>
      {tip.lines.map((l, i) =>
        typeof l === "string" ? (
          <div key={i} className="line">{l}</div>
        ) : (
          <div key={i} className="kv"><span className="k">{l[0]}</span><span className="v">{l[1]}</span></div>
        ),
      )}
      {tip.notes?.filter(Boolean).map((n, i) => <div key={i} className="note">{n}</div>)}
      {hint && <div className="cta">{hint}</div>}
    </div>
  );
}

/** id of the "Notes on method" <details> at the foot of the page; `Hint`'s `more` link opens and scrolls to it. */
export const NOTES_ID = "method";

export function scrollToNotes() {
  const el = document.getElementById(NOTES_ID);
  if (!el) return;
  if (el instanceof HTMLDetailsElement) el.open = true;
  // leave room for the sticky control bar
  const bar = document.querySelector<HTMLElement>(".controls");
  window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - (bar?.offsetHeight ?? 0) - 12, behavior: "smooth" });
}

export type HintItem = { k: string; v: ReactNode };

/**
 * The "i" control in card headers and the control bar. Click opens a small anchored popover (no hover behaviour) that closes on outside click,
 * Esc, or clicking the icon again. Content is either structured `items` (a compact label/value list, one short sentence per value) or a legacy
 * `text` paragraph. `title` defaults to the enclosing card's title. `more` is the label of a link that opens and scrolls to the notes on method.
 * The popover hangs below the icon, right-aligned to it, and flips to left-aligned (or above) when that would leave the viewport.
 */
export function Hint({ text, items, more, title }: { text?: string; items?: HintItem[]; more?: string; title?: string }) {
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLSpanElement>(null);
  const pop = useRef<HTMLDivElement>(null);
  const [place, setPlace] = useState<{ l: boolean; up: boolean } | null>(null);
  const [cardTitle, setCardTitle] = useState<string | undefined>(undefined);
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
          {more && <button type="button" className="more" onClick={() => { setOpen(false); scrollToNotes(); }}>{more}</button>}
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
