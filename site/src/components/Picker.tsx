import { useEffect, useId, useRef, useState, type ReactNode } from "react";

/** `accent` marks a decider row (data.ts isDecider): its name is set a step heavier, in full ink. */
export type PickItem = { id: string; label: string; section?: string; mark?: ReactNode; title?: string; suffix?: ReactNode; detail?: () => void; accent?: string };
export type PickGroup = { id: string; label: string; items: PickItem[] };

/**
 * A dropdown multi-select: a compact button summarising the selection, opening a panel of grouped checkbox rows.
 * Group headers toggle their whole group; the footer offers the suggested set (`onReset`) / all / none. Pages open with nothing selected.
 */
export function Picker({ label, summary, groups, on, onChange, onReset, footer, description, selected, className = "" }: {
  label: string; summary: string; groups: PickGroup[]; on: Set<string>;
  onChange: (next: Set<string>) => void; onReset?: () => void; footer?: ReactNode;
  description?: ReactNode; selected?: ReactNode; className?: string;
}) {
  const [open, setOpen] = useState(false);
  const [alignR, setAlignR] = useState(false);
  const [maxW, setMaxW] = useState<number | undefined>();
  const ref = useRef<HTMLSpanElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const id = useId();
  // Anchor the panel to the button's right edge when it sits in the right half of the viewport, and cap its width to the
  // room on that side, so it never runs off-screen; the group columns then wrap to fewer per row.
  const toggleOpen = () => {
    const b = ref.current?.getBoundingClientRect();
    const r = !!b && b.left > window.innerWidth / 2;
    setAlignR(r);
    setMaxW(b ? Math.max(240, (r ? b.right : window.innerWidth - b.left) - 12) : undefined);
    setOpen((o) => !o);
  };
  useEffect(() => {
    if (!open) return;
    const onDoc = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setOpen(false);
      buttonRef.current?.focus();
    };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    requestAnimationFrame(() => {
      const firstSelected = panelRef.current?.querySelector<HTMLElement>('[role="checkbox"][aria-checked="true"]');
      (firstSelected ?? panelRef.current?.querySelector<HTMLElement>('[role="checkbox"]'))?.focus();
    });
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const all = groups.flatMap((g) => g.items.map((i) => i.id));
  const set = (ids: string[], val: boolean) => { const n = new Set(on); ids.forEach((id) => (val ? n.add(id) : n.delete(id))); onChange(n); };

  return (
    <span className={`pick-wrap${open ? " open" : ""}${className ? ` ${className}` : ""}`} ref={ref}>
      <button ref={buttonRef} className="pick-btn" onClick={toggleOpen} aria-haspopup="dialog" aria-expanded={open} aria-controls={open ? id : undefined}>
        <span className="pick-lab">{label}</span>
        <span className="pick-sum">{summary}</span>
        <span className="chev" />
      </button>
      {open && (
        <div ref={panelRef} id={id} className={`pick-pop${alignR ? " r" : ""}`} style={maxW ? { maxWidth: Math.min(maxW, 760) } : undefined} role="dialog" aria-label={`${label} selection`}>
          {(description || selected) && (
            <div className="pick-head">
              <div className="pick-head-copy">
                <strong>{label}</strong>
                {description && <span>{description}</span>}
              </div>
              <button type="button" className="pick-close" onClick={() => { setOpen(false); buttonRef.current?.focus(); }} aria-label={`Close ${label} selection`}>×</button>
              {selected && <div className="pick-selected" aria-live="polite">{selected}</div>}
            </div>
          )}
          <div className="pick-grps">
          {groups.map((g) => {
            const ids = g.items.map((i) => i.id);
            const nOn = ids.filter((id) => on.has(id)).length;
            return (
              <div className="pick-grp" key={g.id}>
                <button className="pick-gh" onClick={() => set(ids, nOn < ids.length)} title={nOn < ids.length ? "Select all in group" : "Clear group"}>
                  <span>{g.label}</span><span className="n">{nOn}/{ids.length}</span>
                </button>
                {g.items.map((it) => {
                  const isOn = on.has(it.id);
                  const previous = g.items[g.items.indexOf(it) - 1];
                  return (
                    <div key={it.id}>
                      {it.section && it.section !== previous?.section && <div className="pick-sh">{it.section}</div>}
                      <div className={`pick-row${isOn ? " on" : ""}`}>
                      <button className="pick-main" role="checkbox" aria-checked={isOn} onClick={() => set([it.id], !isOn)} title={it.title}>
                        <span className={`box${isOn ? " on" : ""}`} />
                        <span className={`lbl${it.accent ? " dec" : ""}`}>
                          {it.mark && <span className="mark">{it.mark}</span>}
                          <span className="nm">{it.label}</span>
                          {it.suffix}
                        </span>
                      </button>
                      {it.detail && <button className="pick-i" onClick={it.detail} title="How this one is asked">i</button>}
                      </div>
                    </div>
                  );
                })}
              </div>
            );
          })}
          </div>
          <div className="pick-foot">
            {onReset && <button onClick={onReset} title="Select the curated comparison set">Suggested set</button>}
            <button onClick={() => set(all, true)}>Select all</button>
            <button onClick={() => set(all, false)}>Clear all</button>
            {footer && <span className="pick-foot-r">{footer}</span>}
          </div>
        </div>
      )}
    </span>
  );
}
