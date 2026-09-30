import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "comparison-series-colors-v1";
const EVENT = "comparison-series-colors";

export const SERIES_SWATCHES = ["#8b5cf6", "#2563eb", "#0891b2", "#059669", "#ca8a04", "#ea580c", "#dc2626", "#db2777", "#64748b"];

type SeriesColors = Record<string, string>;

const valid = (value: unknown): value is string => typeof value === "string" && /^#[0-9a-f]{6}$/i.test(value);
const read = (): SeriesColors => {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) return {};
    return Object.fromEntries(Object.entries(parsed).filter(([, value]) => valid(value)));
  } catch {
    return {};
  }
};

/** Persisted per-series colors shared by the Study and Studio pages. */
export function useSeriesColors() {
  const [colors, setColors] = useState<SeriesColors>(read);
  useEffect(() => {
    const sync = () => setColors(read());
    window.addEventListener(EVENT, sync);
    window.addEventListener("storage", sync);
    return () => { window.removeEventListener(EVENT, sync); window.removeEventListener("storage", sync); };
  }, []);
  const setColor = useCallback((id: string, color: string) => {
    if (!valid(color)) return;
    const next = { ...read(), [id]: color.toLowerCase() };
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch { /* choice remains in this page through the event */ }
    setColors(next);
    window.dispatchEvent(new Event(EVENT));
  }, []);
  return { colors, setColor, colorOf: (id: string, fallback: string) => colors[id] ?? fallback };
}

function fallbackHex(color: string): string {
  if (valid(color)) return color;
  const match = /^var\((--[^,)]+)/.exec(color);
  if (match && typeof document !== "undefined") {
    const resolved = getComputedStyle(document.documentElement).getPropertyValue(match[1]).trim();
    if (valid(resolved)) return resolved;
  }
  return SERIES_SWATCHES[8];
}

/** Compact accessible native picker plus a professional quick palette. */
export function SeriesColorControl({ id, color, onColor, label }: { id: string; color: string; onColor: (id: string, color: string) => void; label: string }) {
  const value = fallbackHex(color);
  return (
    <span className="series-color" onClick={(e) => e.stopPropagation()}>
      <input type="color" value={value} onChange={(e) => onColor(id, e.target.value)} aria-label={`Choose color for ${label}`} title={`Choose color for ${label}`} />
      <span className="series-swatches" aria-label={`Quick colors for ${label}`}>
        {SERIES_SWATCHES.map((swatch) => (
          <button key={swatch} type="button" className={value.toLowerCase() === swatch ? "on" : ""} style={{ background: swatch }}
            onClick={() => onColor(id, swatch)} aria-label={`Set ${label} to ${swatch}`} title={swatch} />
        ))}
      </span>
    </span>
  );
}
