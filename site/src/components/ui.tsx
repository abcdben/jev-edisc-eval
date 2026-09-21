import { useEffect, useRef, useState, type ReactNode } from "react";

export type TipLine = string | [string, string];
export type Tip = { x: number; y: number; title: string; color?: string; lines: TipLine[]; notes?: string[] } | null;

/** One absolutely positioned tooltip per chart; coordinates are relative to the nearest [data-tip-host]. */
export function useTip() {
  const [tip, setTip] = useState<Tip>(null);
  const hostRef = useRef<HTMLDivElement>(null);
  const show = (e: { clientX: number; clientY: number }, t: Omit<NonNullable<Tip>, "x" | "y">) => {
    const host = hostRef.current;
    const r = host ? host.getBoundingClientRect() : { left: 0, top: 0, width: 0 };
    let x = e.clientX - r.left + 14;
    const y = e.clientY - r.top + 12;
    if (host && x + 380 > r.width) x = Math.max(0, e.clientX - r.left - 384);
    setTip({ x, y, ...t });
  };
  return { tip, show, hide: () => setTip(null), hostRef };
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

export function TipBox({ tip }: { tip: Tip }) {
  if (!tip) return null;
  return (
    <div className="tip" style={{ left: tip.x, top: tip.y }}>
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
    </div>
  );
}

export function Hint({ text, left }: { text: string; left?: boolean }) {
  const [open, setOpen] = useState(false);
  return (
    <span className="hint" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <span className="i">i</span>
      {open && <span className={`pop${left ? " left" : ""}`}>{text}</span>}
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
