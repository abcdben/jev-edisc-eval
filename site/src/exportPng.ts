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
 *  - The serialised document cannot see the page's web fonts (the <img> that rasterises the SVG is its own context), so without an embedded
 *    @font-face every label falls back to a system face with other metrics and text lands where the live layout never put it (an axis title
 *    over a tick label). `webFontCss` fetches the Google Fonts stylesheet(s) linked from the page, keeps the Latin @font-face blocks, inlines
 *    their files as data URLs and hands the result to html-to-image as `fontEmbedCSS`. The result is cached for the page's lifetime; offline
 *    or blocked, it is empty and the export uses the system fallback as before.
 *  - Should the rasteriser still draw text in another face or size, every <text> in the clone carries textLength (its width on the page), so
 *    the legend rows, point labels and columns the charts laid out from measured widths (components/measure.tsx) keep their places.
 * Vendor marks are inline <path>s, or a bundled PNG in an SVG <mask>; html-to-image turns <image href> into a data URL, so nothing taints the canvas.
 */

export type ExportBackground = "panel" | "transparent";

const blobToDataUrl = (b: Blob) => new Promise<string>((res, rej) => { const r = new FileReader(); r.onload = () => res(r.result as string); r.onerror = () => rej(r.error); r.readAsDataURL(b); });

async function fetchWebFontCss(): Promise<string> {
  const links = [...document.querySelectorAll<HTMLLinkElement>('link[rel="stylesheet"][href*="fonts.googleapis.com"]')];
  const blocks: string[] = [];
  for (const link of links) {
    const css = await (await fetch(link.href)).text();
    for (const m of css.matchAll(/@font-face\s*\{[^}]*\}/g)) {
      const block = m[0];
      // Google serves one block per script subset; the charts are Latin (digits, %, ·, – and —, all in the "latin" range).
      const range = /unicode-range:\s*([^;]+);/.exec(block)?.[1];
      if (range && !/U\+0000-00FF/i.test(range)) continue;
      const src = /url\(["']?([^"')]+)["']?\)/.exec(block);
      if (!src) continue;
      const font = await fetch(src[1]);
      if (!font.ok) continue;
      blocks.push(block.replace(src[1], await blobToDataUrl(await font.blob())));
    }
  }
  return blocks.join("\n");
}

let webFontCssCache: Promise<string> | undefined;
/** The page's web fonts as self-contained @font-face CSS, fetched once; "" when none is linked or they cannot be fetched. */
function webFontCss(): Promise<string> {
  webFontCssCache ??= fetchWebFontCss().catch((e) => { console.warn("Studio export: web fonts not embedded", e); webFontCssCache = undefined; return ""; });
  return webFontCssCache;
}

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
    // Pin every label to the width it has on the page (the clone is laid out in the document, so this is the live width): the charts place
    // labels, legend items and columns from measured widths (components/measure.tsx), and the rasterised copy must keep them even if its
    // text comes out in another face or size (a font that failed to embed, a browser setting the <img> context applies). With the same font
    // the natural width equals textLength and nothing changes; with another, the glyphs are fitted to the space rather than run together.
    if (el instanceof SVGTextElement && !el.hasAttribute("textLength") && el.childElementCount === 0 && el.textContent?.trim()) {
      const len = el.getComputedTextLength();
      if (len > 0) { el.setAttribute("textLength", len.toFixed(2)); el.setAttribute("lengthAdjust", "spacingAndGlyphs"); }
    }
  });
}

/**
 * Render the panel to a PNG blob. `scale` is the device-pixel ratio relative to the panel's CSS size. `inherited` is custom properties the live
 * panel inherits from an ancestor (the studio's custom-scheme wrapper): the off-screen clone is placed under a wrapper carrying them, not given
 * them inline, so the panel's own `[data-contrast="high"]` block still overrides them exactly as it does on the page.
 */
export async function renderPanelPng(panel: HTMLElement, scale: number, background: ExportBackground, inherited?: Record<string, string>): Promise<Blob> {
  // the page's web fonts must be in before anything is measured or serialised: a label measured against the fallback face is another width
  await document.fonts?.ready;
  const W = panel.offsetWidth, H = panel.offsetHeight;
  const panelColour = getComputedStyle(panel).backgroundColor;
  const clone = panel.cloneNode(true) as HTMLElement;
  clone.classList.remove("framed");
  clone.querySelector(".studio-grip")?.remove();
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
  let mount: HTMLElement = wrap;
  if (inherited && Object.keys(inherited).length) {
    mount = document.createElement("div");
    mount.style.display = "contents";
    for (const [k, v] of Object.entries(inherited)) mount.style.setProperty(k, v);
    wrap.appendChild(mount);
  }
  mount.appendChild(clone);
  document.body.appendChild(wrap);
  try {
    inlineSvgStyles(clone);
    // fontEmbedCSS (even empty) replaces html-to-image's own stylesheet walk, which cannot read the cross-origin Google Fonts sheet
    const blob = await toBlob(clone, {
      width: W, height: H, pixelRatio: scale, fontEmbedCSS: await webFontCss(),
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
