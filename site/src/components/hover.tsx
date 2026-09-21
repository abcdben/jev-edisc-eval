import { createContext, useContext, useMemo, useState, type FocusEvent, type ReactNode } from "react";

/** The model (or configuration) highlighted across one dashboard section's charts, keyed like `onSelect` ids (`Rec.model`); null when none. */
export type Hover = { id: string | null; set: (id: string | null) => void };

const NONE: Hover = { id: null, set: () => {} };
const HoverContext = createContext<Hover>(NONE);

/** One hover state per dashboard section, so Compare models and Configurations each highlight within their own cards. */
export function HoverProvider({ children }: { children: ReactNode }) {
  const [id, set] = useState<string | null>(null);
  const value = useMemo<Hover>(() => ({ id, set }), [id]);
  return <HoverContext.Provider value={value}>{children}</HoverContext.Provider>;
}

/** The enclosing section's hover state; outside a provider it is inert (id null, set a no-op). */
export function useHover(): Hover {
  return useContext(HoverContext);
}

/**
 * Handlers for a chart row or mark that report its id while the pointer is over it or it has keyboard focus. Pointer events, so they sit
 * beside a chart's own mouse handlers (tooltips) without touching them; focus counts only when the browser would draw a focus ring.
 * Without `onHover` the element gets nothing.
 */
export function hoverable(onHover: ((id: string | null) => void) | undefined, id: string) {
  if (!onHover) return {};
  return {
    onPointerEnter: () => onHover(id),
    onPointerLeave: () => onHover(null),
    onFocus: (e: FocusEvent) => { if ((e.target as Element).matches(":focus-visible")) onHover(id); },
    onBlur: () => onHover(null),
  };
}
