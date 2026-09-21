import { useEffect, useRef, useState, type ReactNode } from "react";

/** `accent` draws a 2px rule in that colour down the row's left edge (the decider marker, data.ts isDecider). */
export type PickItem = { id: string; label: string; mark?: ReactNode; title?: string; suffix?: ReactNode; detail?: () => void; accent?: string };
export type PickGroup = { id: string; label: string; items: PickItem[] };

/**
 * A dropdown multi-select: a compact button summarising the selection, opening a panel of grouped checkbox rows.
 * Group headers toggle their whole group; the footer offers reset / all / none.
 */
export function Picker({ label, summary, groups, on, onChange, onReset, footer }: {
  label: string; summary: string; groups: PickGroup[]; on: Set<string>;
  onChange: (next: Set<string>) => void; onReset?: () => void; footer?: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const [alignR, setAlignR] = useState(false);
  const [maxW, setMaxW] = useState<number | undefined>();
  const ref = useRef<HTMLSpanElement>(null);
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
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onKey);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onKey); };
  }, [open]);

  const all = groups.flatMap((g) => g.items.map((i) => i.id));
  const set = (ids: string[], val: boolean) => { const n = new Set(on); ids.forEach((id) => (val ? n.add(id) : n.delete(id))); onChange(n); };

  return (
    <span className={`pick-wrap${open ? " open" : ""}`} ref={ref}>
      <button className="pick-btn" onClick={toggleOpen} aria-haspopup="listbox" aria-expanded={open}>
        <span className="pick-lab">{label}</span>
        <span className="pick-sum">{summary}</span>
        <span className="chev" />
      </button>
      {open && (
        <div className={`pick-pop${alignR ? " r" : ""}`} style={maxW ? { maxWidth: Math.min(maxW, 760) } : undefined} role="listbox" aria-multiselectable>
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
                  return (
                    <div className={`pick-row${isOn ? " on" : ""}`} key={it.id} role="option" aria-selected={isOn}>
                      {it.accent && <span className="rule" style={{ background: it.accent }} aria-hidden />}
                      <button className="pick-main" onClick={() => set([it.id], !isOn)} title={it.title}>
                        <span className={`box${isOn ? " on" : ""}`} />
                        {it.mark && <span className="mark">{it.mark}</span>}
                        <span className="nm">{it.label}</span>
                        {it.suffix}
                      </button>
                      {it.detail && <button className="pick-i" onClick={it.detail} title="How this one is asked">i</button>}
                    </div>
                  );
                })}
              </div>
            );
          })}
          </div>
          <div className="pick-foot">
            {onReset && <button onClick={onReset}>reset</button>}
            <button onClick={() => set(all, true)}>all</button>
            <button onClick={() => set(all, false)}>none</button>
            {footer && <span className="pick-foot-r">{footer}</span>}
          </div>
        </div>
      )}
    </span>
  );
}
