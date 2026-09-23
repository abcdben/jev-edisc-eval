import { toBlob } from "html-to-image";

/**
 * Studio PNG export (StudioPage.tsx Export controls): the `.studio-plot` panel rendered to a PNG at `scale` × its CSS size, with no frame,
 * corner radius, resize grip or shadow, on the panel colour or on transparent.
 *
 * Approach: an off-screen deep clone of the live panel, sized to it, with the `framed` class removed, is handed to html-to-image, which
 * serialises it into an <svg><foreignObject>, draws that to a canvas at `pixelRatio` and returns the PNG. Two fidelity fixes of our own:
 *  - html-to-image deep-clones each inline <svg> without inlining styles on its descendants, and the serialised document has no stylesheet,
 *    so the chart's class rules (.mono, .gl dashes, high-contrast weights, .pr-box outlines) and every `var(--…)` / `calc(var(--…))` used in
 *    fill, stroke-width, r, opacity and transform attributes would be lost. `inlineSvgStyles` copies the computed value of those properties
 *    onto every SVG descendant of the clone (which, being in the document, has the real computed styles) before html-to-image runs.
 *  - html-to-image's per-node property list comes from :root, so custom properties set only on the panel (--sw-mult, --fs-legend, …) are not
 *    copied; inlining the resolved values sidesteps that for the SVG, and HTML nodes get their resolved standard properties as usual.
 * Vendor marks are inline <path>s, or a bundled PNG in an SVG <mask>; html-to-image turns <image href> into a data URL, so nothing taints the canvas.
 */

export type ExportBackground = "panel" | "transparent";

const SVG_PROPS = [
  "fill", "fill-opacity", "fill-rule", "stroke", "stroke-width", "stroke-dasharray", "stroke-opacity", "stroke-linecap", "stroke-linejoin",
  "opacity", "color", "font-family", "font-size", "font-weight", "font-style", "letter-spacing", "font-variant-numeric", "text-anchor", "dominant-baseline", "r",
];

function inlineSvgStyles(clone: HTMLElement) {
  clone.querySelectorAll("svg *").forEach((el) => {
    if (!(el instanceof SVGElement)) return;
    const cs = getComputedStyle(el);
    for (const p of SVG_PROPS) { const v = cs.getPropertyValue(p); if (v) el.style.setProperty(p, v); }
    // CSS transforms (the high-contrast --mark-scale on glyph groups) resolve to a matrix; only where the element carried one, so attribute transforms stay as authored
    if (el.style.transform) { el.style.transform = cs.transform; el.style.transformOrigin = cs.transformOrigin; }
  });
}

/** Render the panel to a PNG blob. `scale` is the device-pixel ratio relative to the panel's CSS size. */
export async function renderPanelPng(panel: HTMLElement, scale: number, background: ExportBackground): Promise<Blob> {
  const W = panel.offsetWidth, H = panel.offsetHeight;
  const panelColour = getComputedStyle(panel).backgroundColor;
  const clone = panel.cloneNode(true) as HTMLElement;
  clone.classList.remove("framed");
  clone.removeAttribute("id");
  clone.setAttribute("aria-hidden", "true");
  Object.assign(clone.style, {
    width: `${W}px`, height: `${H}px`, maxWidth: "none",
    resize: "none", borderRadius: "0", boxShadow: "none", borderColor: "transparent",
    background: background === "panel" ? panelColour : "transparent",
  } as Partial<CSSStyleDeclaration>);
  // The clone sits in an off-screen wrapper (not offset itself: html-to-image copies the node's computed offsets, and an offset root renders blank)
  const wrap = document.createElement("div");
  Object.assign(wrap.style, { position: "fixed", left: "-100000px", top: "0", width: `${W}px`, height: `${H}px`, overflow: "hidden", pointerEvents: "none" } as Partial<CSSStyleDeclaration>);
  wrap.appendChild(clone);
  document.body.appendChild(wrap);
  try {
    inlineSvgStyles(clone);
    const blob = await toBlob(clone, {
      width: W, height: H, pixelRatio: scale, skipFonts: true,
      backgroundColor: background === "panel" ? panelColour : undefined,
      filter: (n) => !(n instanceof Element && n.classList.contains("no-export")),
    });
    if (!blob) throw new Error("The browser returned no image.");
    return blob;
  } finally {
    wrap.remove();
  }
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.rel = "noopener";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** Copy a PNG to the clipboard. Passing the promise (not the blob) keeps Safari's user-gesture window open; Chrome accepts either. */
export async function copyPng(png: Promise<Blob>) {
  if (typeof ClipboardItem === "undefined" || !navigator.clipboard?.write) throw new Error("This browser cannot copy images; use Download.");
  await navigator.clipboard.write([new ClipboardItem({ "image/png": png })]);
}

/** Lower-case, hyphenated file-name segment. */
export const slug = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
