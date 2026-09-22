import laya from "./logos/laya-mask.png";
import typesafe from "./logos/typesafe.png";

const CLAUDE_PATH = "M4.709 15.955l4.72-2.647.08-.23-.08-.128H9.2l-.79-.048-2.698-.073-2.339-.097-2.266-.122-.571-.121L0 11.784l.055-.352.48-.321.686.06 1.52.103 2.278.158 1.652.097 2.449.255h.389l.055-.157-.134-.098-.103-.097-2.358-1.596-2.552-1.688-1.336-.972-.724-.491-.364-.462-.158-1.008.656-.722.881.06.225.061.893.686 1.908 1.476 2.491 1.833.365.304.145-.103.019-.073-.164-.274-1.355-2.446-1.446-2.49-.644-1.032-.17-.619a2.97 2.97 0 01-.104-.729L6.283.134 6.696 0l.996.134.42.364.62 1.414 1.002 2.229 1.555 3.03.456.898.243.832.091.255h.158V9.01l.128-1.706.237-2.095.23-2.695.08-.76.376-.91.747-.492.584.28.48.685-.067.444-.286 1.851-.559 2.903-.364 1.942h.212l.243-.242.985-1.306 1.652-2.064.73-.82.85-.904.547-.431h1.033l.76 1.129-.34 1.166-1.064 1.347-.881 1.142-1.264 1.7-.79 1.36.073.11.188-.02 2.856-.606 1.543-.28 1.841-.315.833.388.091.395-.328.807-1.969.486-2.309.462-3.439.813-.042.03.049.061 1.549.146.662.036h1.622l3.02.225.79.522.474.638-.079.485-1.215.62-1.64-.389-3.829-.91-1.312-.329h-.182v.11l1.093 1.068 2.006 1.81 2.509 2.33.127.578-.322.455-.34-.049-2.205-1.657-.851-.747-1.926-1.62h-.128v.17l.444.649 2.345 3.521.122 1.08-.17.353-.608.213-.668-.122-1.374-1.925-1.415-2.167-1.143-1.943-.14.08-.674 7.254-.316.37-.729.28-.607-.461-.322-.747.322-1.476.389-1.924.315-1.53.286-1.9.17-.632-.012-.042-.14.018-1.434 1.967-2.18 2.945-1.726 1.845-.414.164-.717-.37.067-.662.401-.589 2.388-3.036 1.44-1.882.93-1.086-.006-.158h-.055L4.132 18.56l-1.13.146-.487-.456.061-.746.231-.243 1.908-1.312-.006.006z";
const GEMINI_PATH = "M20.616 10.835a14.147 14.147 0 01-4.45-3.001 14.111 14.111 0 01-3.678-6.452.503.503 0 00-.975 0 14.134 14.134 0 01-3.679 6.452 14.155 14.155 0 01-4.45 3.001c-.65.28-1.318.505-2.002.678a.502.502 0 000 .975c.684.172 1.35.397 2.002.677a14.147 14.147 0 014.45 3.001 14.112 14.112 0 013.679 6.453.502.502 0 00.975 0c.172-.685.397-1.351.677-2.003a14.145 14.145 0 013.001-4.45 14.113 14.113 0 016.453-3.678.503.503 0 000-.975 13.245 13.245 0 01-2.003-.678z";
const GEMMA_PATH = "M12.34 5.953a8.233 8.233 0 01-.247-1.125V3.72a8.25 8.25 0 015.562 2.232H12.34zm-.69 0c.113-.373.199-.755.257-1.145V3.72a8.25 8.25 0 00-5.562 2.232h5.304zm-5.433.187h5.373a7.98 7.98 0 01-.267.696 8.41 8.41 0 01-1.76 2.65L6.216 6.14zm-.264-.187H2.977v.187h2.915a8.436 8.436 0 00-2.357 5.767H0v.186h3.535a8.436 8.436 0 002.357 5.767H2.977v.186h2.976v2.977h.187v-2.915a8.436 8.436 0 005.767 2.357V24h.186v-3.535a8.436 8.436 0 005.767-2.357v2.915h.186v-2.977h2.977v-.186h-2.915a8.436 8.436 0 002.357-5.767H24v-.186h-3.535a8.436 8.436 0 00-2.357-5.767h2.915v-.187h-2.977V2.977h-.186v2.915a8.436 8.436 0 00-5.767-2.357V0h-.186v3.535A8.436 8.436 0 006.14 5.892V2.977h-.187v2.976zm6.14 14.326a8.25 8.25 0 005.562-2.233H12.34c-.108.367-.19.743-.247 1.126v1.107zm-.186-1.087a8.015 8.015 0 00-.258-1.146H6.345a8.25 8.25 0 005.562 2.233v-1.087zm-8.186-7.285h1.107a8.23 8.23 0 001.125-.247V6.345a8.25 8.25 0 00-2.232 5.562zm1.087.186H3.72a8.25 8.25 0 002.232 5.562v-5.304a8.012 8.012 0 00-1.145-.258zm15.47-.186a8.25 8.25 0 00-2.232-5.562v5.315c.367.108.743.19 1.126.247h1.107zm-1.086.186c-.39.058-.772.144-1.146.258v5.304a8.25 8.25 0 002.233-5.562h-1.087zm-1.332 5.69V12.41a7.97 7.97 0 00-.696.267 8.409 8.409 0 00-2.65 1.76l3.346 3.346zm0-6.18v-5.45l-.012-.013h-5.451c.076.235.162.468.26.696a8.698 8.698 0 001.819 2.688 8.698 8.698 0 002.688 1.82c.228.097.46.183.696.259zM6.14 17.848V12.41c.235.078.468.167.696.267a8.403 8.403 0 012.688 1.799 8.404 8.404 0 011.799 2.688c.1.228.19.46.267.696H6.152l-.012-.012zm0-6.245V6.326l3.29 3.29a8.716 8.716 0 01-2.594 1.728 8.14 8.14 0 01-.696.259zm6.257 6.257h5.277l-3.29-3.29a8.716 8.716 0 00-1.728 2.594 8.135 8.135 0 00-.259.696zm-2.347-7.81a9.435 9.435 0 01-2.88 1.96 9.14 9.14 0 012.88 1.94 9.14 9.14 0 011.94 2.88 9.435 9.435 0 011.96-2.88 9.14 9.14 0 012.88-1.94 9.435 9.435 0 01-2.88-1.96 9.434 9.434 0 01-1.96-2.88 9.14 9.14 0 01-1.94 2.88z";
const OPENAI_PATH = "M9.205 8.658v-2.26c0-.19.072-.333.238-.428l4.543-2.616c.619-.357 1.356-.523 2.117-.523 2.854 0 4.662 2.212 4.662 4.566 0 .167 0 .357-.024.547l-4.71-2.759a.797.797 0 00-.856 0l-5.97 3.473zm10.609 8.8V12.06c0-.333-.143-.57-.429-.737l-5.97-3.473 1.95-1.118a.433.433 0 01.476 0l4.543 2.617c1.309.76 2.189 2.378 2.189 3.948 0 1.808-1.07 3.473-2.76 4.163zM7.802 12.703l-1.95-1.142c-.167-.095-.239-.238-.239-.428V5.899c0-2.545 1.95-4.472 4.591-4.472 1 0 1.927.333 2.712.928L8.23 5.067c-.285.166-.428.404-.428.737v6.898zM12 15.128l-2.795-1.57v-3.33L12 8.658l2.795 1.57v3.33L12 15.128zm1.796 7.23c-1 0-1.927-.332-2.712-.927l4.686-2.712c.285-.166.428-.404.428-.737v-6.898l1.974 1.142c.167.095.238.238.238.428v5.233c0 2.545-1.974 4.472-4.614 4.472zm-5.637-5.303l-4.544-2.617c-1.308-.761-2.188-2.378-2.188-3.948A4.482 4.482 0 014.21 6.327v5.423c0 .333.143.571.428.738l5.947 3.449-1.95 1.118a.432.432 0 01-.476 0zm-.262 3.9c-2.688 0-4.662-2.021-4.662-4.519 0-.19.024-.38.047-.57l4.686 2.71c.286.167.571.167.856 0l5.97-3.448v2.26c0 .19-.07.333-.237.428l-4.543 2.616c-.619.357-1.356.523-2.117.523zm5.899 2.83a5.947 5.947 0 005.827-4.756C22.287 18.339 24 15.84 24 13.296c0-1.665-.713-3.282-1.998-4.448.119-.5.19-.999.19-1.498 0-3.401-2.759-5.947-5.946-5.947-.642 0-1.26.095-1.88.31A5.962 5.962 0 0010.205 0a5.947 5.947 0 00-5.827 4.757C1.713 5.447 0 7.945 0 10.49c0 1.666.713 3.283 1.998 4.448-.119.5-.19 1-.19 1.499 0 3.401 2.759 5.946 5.946 5.946.642 0 1.26-.095 1.88-.309a5.96 5.96 0 004.162 1.713z";

/** Vendor mark for a model key. Bitmap/colour marks are <img>; monochrome marks are inline so they follow the text colour. */
export function logoFor(key: string): { kind: "img"; src: string; alt: string } | { kind: "mask"; src: string; alt: string } | { kind: "path"; d: string; alt: string; fr: "nonzero" | "evenodd" } | { kind: "lexical" } | null {
  const k = key.split("@")[0];
  // TypeSafe's mark is a monochrome glyph; shipped as an alpha mask so it takes the current colour
  if (k === "jev") return { kind: "mask", src: typesafe, alt: "TypeSafe" };
  // Laya's mark likewise ships as an alpha mask so it sits in the text colour like every other vendor glyph
  if (k.startsWith("laya")) return { kind: "mask", src: laya, alt: "ConvAI Laya" };
  if (k.startsWith("claude")) return { kind: "path", d: CLAUDE_PATH, alt: "Anthropic", fr: "nonzero" };
  if (k.startsWith("gpt")) return { kind: "path", d: OPENAI_PATH, alt: "OpenAI", fr: "evenodd" };
  if (k.startsWith("gemini")) return { kind: "path", d: GEMINI_PATH, alt: "Google Gemini", fr: "nonzero" };
  if (k.startsWith("gemma")) return { kind: "path", d: GEMMA_PATH, alt: "Google Gemma", fr: "evenodd" };
  if (k === "lexical") return { kind: "lexical" };
  return null;
}

export function Logo({ model, size = 14, className = "" }: { model: string; size?: number; className?: string }) {
  const l = logoFor(model);
  if (!l) return null;
  const st = { width: size, height: size, flex: "none" as const };
  if (l.kind === "img") return <img className={`logo ${className}`} src={l.src} alt={l.alt} title={l.alt} style={st} draggable={false} />;
  if (l.kind === "mask")
    return (
      <span
        className={`logo ${className}`} role="img" aria-label={l.alt} title={l.alt}
        style={{ ...st, display: "inline-block", background: "currentColor", WebkitMaskImage: `url(${l.src})`, maskImage: `url(${l.src})`, WebkitMaskSize: "contain", maskSize: "contain", WebkitMaskRepeat: "no-repeat", maskRepeat: "no-repeat", WebkitMaskPosition: "center", maskPosition: "center" }}
      />
    );
  if (l.kind === "path")
    return (
      <svg className={`logo ${className}`} viewBox="0 0 24 24" style={st} aria-label={l.alt} role="img"><path fill="currentColor" fillRule={l.fr} d={l.d} /></svg>
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
  if (l.kind === "mask") {
    const id = `lm-${model.replace(/[^a-z0-9]/gi, "")}-${Math.round(cx)}-${Math.round(cy)}`;
    return (
      <g opacity={opacity} style={{ pointerEvents: "none" }}>
        <mask id={id} maskUnits="userSpaceOnUse" x={x} y={y} width={size} height={size}>
          <image href={l.src} x={x} y={y} width={size} height={size} />
        </mask>
        <rect x={x} y={y} width={size} height={size} fill="currentColor" mask={`url(#${id})`} />
      </g>
    );
  }
  const k = size / 24;
  if (l.kind === "path") return <path transform={`translate(${x} ${y}) scale(${k})`} d={l.d} fill="currentColor" fillRule={l.fr} opacity={opacity} style={{ pointerEvents: "none" }} />;
  return (
    <g transform={`translate(${x} ${y}) scale(${k})`} fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" opacity={opacity} style={{ pointerEvents: "none" }}>
      <circle cx="10.5" cy="10.5" r="6.5" /><path d="M15.5 15.5L21 21" /><path d="M7.5 13l1.6-5h1.2l1.7 5M8.2 11.2h3.1" strokeWidth={1.4} />
    </g>
  );
}
