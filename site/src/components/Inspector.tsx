import type { ReactNode } from "react";

/**
 * The screenshot studio's settings inspector (StudioPage.tsx): one disclosure section per group of controls, stacked under the top bar.
 * A closed section shows a one-line summary of its current values in its header; open, it lays its controls out in a grid
 * (styles.css `.studio-sec-b`). Which sections are open is one field of the studio's state (studioState.ts `sections`, remembered under
 * `studio-sections` and carried by presets); the page hands it here with its updater.
 */

type OpenMap = Record<string, boolean>;
/** Toggle and set over the page's open-sections field; `set` opens or closes one without a click (Style → Custom opens Scheme). */
export function sectionsApi(open: OpenMap, update: (f: (p: OpenMap) => OpenMap) => void) {
  const toggle = (id: string) => update((p) => ({ ...p, [id]: !p[id] }));
  const set = (id: string, v: boolean) => update((p) => (p[id] === v ? p : { ...p, [id]: v }));
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
