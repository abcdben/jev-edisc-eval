import { useCallback, useEffect, useLayoutEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";

/**
 * Text widths as the browser draws them, for the charts that position text by its width: the legend rows (PRScatter.tsx Legend), the point
 * labels the placement keeps clear of each other, the name and value columns of StudioBars and PRRail.
 *
 * Until the studio's Text and Style controls the charts estimated a name at a fixed width per character; the estimate over-shoots for Inter
 * and under-shoots for wider or heavier faces (a Custom scheme's font, high contrast's weight 500/600), so at large text sizes items laid out
 * from it could run into each other. This measures instead: a hidden canvas 2D context (`measureText`) with the face the chart's text really
 * gets, read off hidden probe <text> elements the chart renders inside its SVG (one per class that sets its own weight or face, plus the
 * plain default) in a layout effect, so the presets' `svg text.nm { font-weight }` rules, the high-contrast block and a Custom scheme's
 * `--sans` are all honoured without the chart knowing about them. The first render (no probes measured yet) uses a per-character estimate;
 * the layout effect then sets the faces and React re-renders before paint, so nothing is seen twice. Widths are re-read when the page's web
 * fonts finish loading (a face measured against the fallback is a different width), and the faces after every render (a preset change
 * alters them without a prop change); state only changes when a value did, so this settles in one pass.
 *
 * `.mono` text (tabular figures via font-feature-settings, which a canvas font string cannot carry) is measured with every digit as a 0,
 * the width a tabular figure takes in Inter and most faces.
 */
export type Measure = (text: string, fs: number, cls?: string) => number;
/** A probe: `key` is what callers pass as `cls`; `className` and `style` are what the chart's text of that kind carries. A string is both key and className. */
export type Probe = string | { key: string; className?: string; style?: CSSProperties };

/** Per-character estimate (em) when nothing has been measured yet: about Inter's mixed-case average. */
const EST_EM = 0.58;
/** Probe font size; letter-spacing read in px at this size is em × 100. */
const PROBE_FS = 100;

type Face = { style: string; weight: string; family: string; lsEm: number };
const sameFace = (a: Face | undefined, b: Face) => !!a && a.style === b.style && a.weight === b.weight && a.family === b.family && a.lsEm === b.lsEm;

let ctx: CanvasRenderingContext2D | null | undefined;
const cache = new Map<string, number>();
/** Advance width of `text` in `font` (a CSS font shorthand); NaN when the canvas or the shorthand is unusable. */
function canvasWidth(text: string, font: string): number {
  const k = `${font}|${text}`;
  const hit = cache.get(k);
  if (hit != null) return hit;
  if (ctx === undefined) ctx = typeof document === "undefined" ? null : document.createElement("canvas").getContext("2d");
  if (!ctx) return NaN;
  // an unparseable shorthand leaves the previous font in place, so start from a sentinel and see that it changed
  ctx.font = "7px serif";
  ctx.font = font;
  if (ctx.font === "7px serif") return NaN;
  const w = ctx.measureText(text).width;
  cache.set(k, w);
  return w;
}

export function useTextMeasure(probes: readonly Probe[]): { measure: Measure; probes: ReactNode } {
  const ref = useRef<SVGGElement>(null);
  const [faces, setFaces] = useState<Record<string, Face>>({});
  const [fontsTick, setFontsTick] = useState(0);
  // no dependency list: the face of a class can change with no prop change (a Style preset, high contrast); setState only when a face did
  useLayoutEffect(() => {
    const g = ref.current;
    if (!g) return;
    const next: Record<string, Face> = {};
    g.querySelectorAll("text").forEach((t) => {
      const cs = getComputedStyle(t);
      const ls = cs.letterSpacing;
      next[t.dataset.probe ?? ""] = { style: cs.fontStyle, weight: cs.fontWeight, family: cs.fontFamily, lsEm: ls === "normal" ? 0 : (parseFloat(ls) || 0) / PROBE_FS };
    });
    setFaces((p) => (Object.keys(p).length === Object.keys(next).length && Object.keys(next).every((k) => sameFace(p[k], next[k])) ? p : next));
  });
  // web fonts arriving change every width under the same face: drop the cache and lay out again
  useEffect(() => {
    const fs = document.fonts;
    if (!fs) return;
    const bump = () => { cache.clear(); setFontsTick((t) => t + 1); };
    fs.addEventListener("loadingdone", bump);
    let live = true;
    fs.ready.then(() => { if (live) bump(); });
    return () => { live = false; fs.removeEventListener("loadingdone", bump); };
  }, []);
  const measure = useCallback<Measure>((text, fs, cls = "") => {
    const f = faces[cls] ?? faces[""];
    if (!f) return text.length * EST_EM * fs;
    const t = cls === "mono" ? text.replace(/\d/g, "0") : text;
    const w = canvasWidth(t, `${f.style} ${f.weight} ${fs}px ${f.family}`);
    return Number.isNaN(w) ? text.length * EST_EM * fs : w + f.lsEm * fs * text.length;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [faces, fontsTick]);
  const node = (
    <g ref={ref} className="no-export" visibility="hidden" aria-hidden="true">
      {probes.map((p) => {
        const { key, className, style } = typeof p === "string" ? { key: p, className: p || undefined, style: undefined } : p;
        return <text key={key} data-probe={key} className={className} style={style} fontSize={PROBE_FS} x={-10000} y={-10000}>M</text>;
      })}
    </g>
  );
  return { measure, probes: node };
}
