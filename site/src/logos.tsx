import claude from "./logos/claude.svg";
import gemini from "./logos/gemini.svg";
import gemma from "./logos/gemma.svg";
import laya from "./logos/laya.png";
import typesafe from "./logos/typesafe.png";

const OPENAI_PATH = "M9.205 8.658v-2.26c0-.19.072-.333.238-.428l4.543-2.616c.619-.357 1.356-.523 2.117-.523 2.854 0 4.662 2.212 4.662 4.566 0 .167 0 .357-.024.547l-4.71-2.759a.797.797 0 00-.856 0l-5.97 3.473zm10.609 8.8V12.06c0-.333-.143-.57-.429-.737l-5.97-3.473 1.95-1.118a.433.433 0 01.476 0l4.543 2.617c1.309.76 2.189 2.378 2.189 3.948 0 1.808-1.07 3.473-2.76 4.163zM7.802 12.703l-1.95-1.142c-.167-.095-.239-.238-.239-.428V5.899c0-2.545 1.95-4.472 4.591-4.472 1 0 1.927.333 2.712.928L8.23 5.067c-.285.166-.428.404-.428.737v6.898zM12 15.128l-2.795-1.57v-3.33L12 8.658l2.795 1.57v3.33L12 15.128zm1.796 7.23c-1 0-1.927-.332-2.712-.927l4.686-2.712c.285-.166.428-.404.428-.737v-6.898l1.974 1.142c.167.095.238.238.238.428v5.233c0 2.545-1.974 4.472-4.614 4.472zm-5.637-5.303l-4.544-2.617c-1.308-.761-2.188-2.378-2.188-3.948A4.482 4.482 0 014.21 6.327v5.423c0 .333.143.571.428.738l5.947 3.449-1.95 1.118a.432.432 0 01-.476 0zm-.262 3.9c-2.688 0-4.662-2.021-4.662-4.519 0-.19.024-.38.047-.57l4.686 2.71c.286.167.571.167.856 0l5.97-3.448v2.26c0 .19-.07.333-.237.428l-4.543 2.616c-.619.357-1.356.523-2.117.523zm5.899 2.83a5.947 5.947 0 005.827-4.756C22.287 18.339 24 15.84 24 13.296c0-1.665-.713-3.282-1.998-4.448.119-.5.19-.999.19-1.498 0-3.401-2.759-5.947-5.946-5.947-.642 0-1.26.095-1.88.31A5.962 5.962 0 0010.205 0a5.947 5.947 0 00-5.827 4.757C1.713 5.447 0 7.945 0 10.49c0 1.666.713 3.283 1.998 4.448-.119.5-.19 1-.19 1.499 0 3.401 2.759 5.946 5.946 5.946.642 0 1.26-.095 1.88-.309a5.96 5.96 0 004.162 1.713z";

/** Vendor mark for a model key. Bitmap/colour marks are <img>; monochrome marks are inline so they follow the text colour. */
export function logoFor(key: string): { kind: "img"; src: string; alt: string } | { kind: "openai" } | { kind: "lexical" } | null {
  const k = key.split("@")[0];
  if (k === "jev") return { kind: "img", src: typesafe, alt: "TypeSafe" };
  if (k.startsWith("laya")) return { kind: "img", src: laya, alt: "ConvAI Laya" };
  if (k.startsWith("claude")) return { kind: "img", src: claude, alt: "Anthropic" };
  if (k.startsWith("gpt")) return { kind: "openai" };
  if (k.startsWith("gemini")) return { kind: "img", src: gemini, alt: "Google Gemini" };
  if (k.startsWith("gemma")) return { kind: "img", src: gemma, alt: "Google Gemma" };
  if (k === "lexical") return { kind: "lexical" };
  return null;
}

export function Logo({ model, size = 14, className = "" }: { model: string; size?: number; className?: string }) {
  const l = logoFor(model);
  if (!l) return null;
  const st = { width: size, height: size, flex: "none" as const };
  if (l.kind === "img") return <img className={`logo ${className}`} src={l.src} alt={l.alt} title={l.alt} style={st} draggable={false} />;
  if (l.kind === "openai")
    return (
      <svg className={`logo ${className}`} viewBox="0 0 24 24" style={st} aria-label="OpenAI" role="img"><path fill="currentColor" fillRule="evenodd" d={OPENAI_PATH} /></svg>
    );
  return (
    <svg className={`logo ${className}`} viewBox="0 0 24 24" style={st} fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" aria-label="keyword" role="img">
      <circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5L21 21" /><path d="M7.5 13l1.6-5h1.2l1.7 5M8.2 11.2h3.1" strokeWidth={1.4} />
    </svg>
  );
}

/** The same mark drawn inside an SVG chart, centred on (cx, cy). */
export function LogoGlyph({ model, cx, cy, size = 13, opacity = 1 }: { model: string; cx: number; cy: number; size?: number; opacity?: number }) {
  const l = logoFor(model);
  if (!l) return null;
  const x = cx - size / 2, y = cy - size / 2;
  if (l.kind === "img") return <image href={l.src} x={x} y={y} width={size} height={size} opacity={opacity} style={{ pointerEvents: "none" }} />;
  const k = size / 24;
  if (l.kind === "openai") return <path transform={`translate(${x} ${y}) scale(${k})`} d={OPENAI_PATH} fill="currentColor" fillRule="evenodd" opacity={opacity} style={{ pointerEvents: "none" }} />;
  return (
    <g transform={`translate(${x} ${y}) scale(${k})`} fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" opacity={opacity} style={{ pointerEvents: "none" }}>
      <circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5L21 21" /><path d="M7.5 13l1.6-5h1.2l1.7 5M8.2 11.2h3.1" strokeWidth={1.4} />
    </g>
  );
}
