import { useEffect, useState, type ReactNode } from "react";

/**
 * The screenshot studio's settings inspector (StudioPage.tsx): one disclosure section per group of controls, stacked under the top bar.
 * A closed section shows a one-line summary of its current values in its header; open, it lays its controls out in a grid
 * (styles.css `.studio-sec-b`). Which sections are open is remembered in localStorage (`studio-sections`).
 */

const KEY = "studio-sections";
const isOpenMap = (o: unknown): o is Record<string, boolean> => !!o && typeof o === "object" && !Array.isArray(o) && Object.values(o).every((v) => typeof v === "boolean");

/** Open/closed state of the sections, `defaults` for a first visit; `set` opens or closes one without a click (Style → Custom opens Scheme). */
export function useSections(defaults: Record<string, boolean>) {
  const [open, setOpen] = useState<Record<string, boolean>>(() => {
    try { const o: unknown = JSON.parse(localStorage.getItem(KEY) || "null"); return isOpenMap(o) ? { ...defaults, ...o } : defaults; } catch { return defaults; }
  });
  useEffect(() => { localStorage.setItem(KEY, JSON.stringify(open)); }, [open]);
  const toggle = (id: string) => setOpen((p) => ({ ...p, [id]: !p[id] }));
  const set = (id: string, v: boolean) => setOpen((p) => (p[id] === v ? p : { ...p, [id]: v }));
  return { open, toggle, set };
}

/** Joins the defined, non-empty parts of a section summary with middle dots. */
export const summarize = (...parts: (string | number | false | null | undefined)[]) => parts.filter((p) => p !== false && p != null && p !== "").join(" · ");

export function Section({ id, title, summary, open, onToggle, children }: { id: string; title: string; summary?: string; open: boolean; onToggle: () => void; children: ReactNode }) {
  const bodyId = `studio-sec-${id}`;
  return (
    <section className={`studio-sec${open ? " open" : ""}`}>
      <h2 className="studio-sec-h">
        <button type="button" aria-expanded={open} aria-controls={bodyId} onClick={onToggle}>
          <span className="chev" aria-hidden="true" />
          <span className="t">{title}</span>
          {!open && summary && <span className="sum">{summary}</span>}
        </button>
      </h2>
      {open && <div id={bodyId} className="studio-sec-b">{children}</div>}
    </section>
  );
}
