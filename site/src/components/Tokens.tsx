import { useMemo, type ReactNode } from "react";

/**
 * A small, dependency-free highlighter for the code-like text the details modal shows: prompt strings with XML-ish tags
 * (`<request id="…">`), JSON (the response schema, the raw response object), and plain text. Each token gets one of the
 * `tk-*` classes below (colours in styles.css, `--tk-*`); text content stays plain ink and is emitted without a span.
 *
 *   tk-tag   tag name                  tk-attr  attribute name            tk-key   JSON object key
 *   tk-str   quoted string             tk-num   number                    tk-bool  true / false / null
 *   tk-p     punctuation: < > / = { } [ ] , :
 */
export type Mode = "tag" | "json" | "plain";
type Tok = [cls: string | null, text: string];

/** A well-formed-looking tag: `<name …>`, `</name>`, `<name … />`; a bare `<` in prose ("p < 0.5") does not match. */
const TAG_TEST = /<\/?[A-Za-z_][\w.:-]*(?:\s[^<>]*)?\/?>/;
const TAG_SCAN = /<(\/?)([A-Za-z_][\w.:-]*)((?:\s[^<>]*?)?)(\/?)>/g;
const ATTR_SCAN = /\s+|=|"[^"]*"|'[^']*'|[^\s="']+/g;
const JSON_SCAN = /("(?:[^"\\]|\\.)*")(\s*:)?|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)|\b(true|false|null)\b|([{}[\],:])|([^"\-\d{}[\],:tfn]+|.)/g;

/** What a string value is: tag mode when it carries XML-like tags, JSON mode when it is a JSON object or array, plain otherwise. */
export function detect(s: string): Mode {
  if (TAG_TEST.test(s)) return "tag";
  const t = s.trim();
  if ((t[0] === "{" && t[t.length - 1] === "}") || (t[0] === "[" && t[t.length - 1] === "]")) {
    try { JSON.parse(t); return "json"; } catch { /* not JSON */ }
  }
  return "plain";
}

function tokenizeTag(s: string, out: Tok[]) {
  let last = 0;
  TAG_SCAN.lastIndex = 0;
  for (let m = TAG_SCAN.exec(s); m; m = TAG_SCAN.exec(s)) {
    if (m.index > last) out.push([null, s.slice(last, m.index)]);
    const [, close, name, attrs, selfClose] = m;
    out.push(["tk-p", `<${close}`], ["tk-tag", name]);
    ATTR_SCAN.lastIndex = 0;
    for (let a = ATTR_SCAN.exec(attrs); a; a = ATTR_SCAN.exec(attrs)) {
      const t = a[0];
      out.push([t === "=" ? "tk-p" : t[0] === '"' || t[0] === "'" ? "tk-str" : /^\s+$/.test(t) ? null : "tk-attr", t]);
    }
    out.push(["tk-p", `${selfClose}>`]);
    last = m.index + m[0].length;
  }
  if (last < s.length) out.push([null, s.slice(last)]);
}

function tokenizeJson(s: string, out: Tok[]) {
  JSON_SCAN.lastIndex = 0;
  for (let m = JSON_SCAN.exec(s); m; m = JSON_SCAN.exec(s)) {
    const [, str, colon, num, lit, p, rest] = m;
    if (str !== undefined) {
      out.push([colon ? "tk-key" : "tk-str", str]);
      if (colon) out.push(["tk-p", colon]);
    } else if (num !== undefined) out.push(["tk-num", num]);
    else if (lit !== undefined) out.push(["tk-bool", lit]);
    else if (p !== undefined) out.push(["tk-p", p]);
    else out.push([null, rest]);
  }
}

/** `s` split into classed tokens; adjacent plain runs are merged so the output stays small. */
export function tokenize(s: string, mode: Mode): Tok[] {
  const raw: Tok[] = [];
  if (mode === "tag") tokenizeTag(s, raw);
  else if (mode === "json") tokenizeJson(s, raw);
  else return [[null, s]];
  const out: Tok[] = [];
  for (const t of raw) {
    const prev = out[out.length - 1];
    if (prev && prev[0] === t[0]) prev[1] += t[1];
    else out.push([t[0], t[1]]);
  }
  return out;
}

/** `s` rendered as highlighted spans; `mode` defaults to what `detect` says. Tokenized once per distinct (s, mode). */
export function Hi({ s, mode }: { s: string; mode?: Mode }): ReactNode {
  const toks = useMemo(() => tokenize(s, mode ?? detect(s)), [s, mode]);
  if (toks.length === 1 && toks[0][0] === null) return s;
  return <>{toks.map(([c, t], i) => (c ? <span key={i} className={c}>{t}</span> : t))}</>;
}

/** JSON.stringify(v, null, 2) with arrays of primitives kept on one line, so a list of three probabilities does not take five rows. */
export function pretty(v: unknown): string {
  return JSON.stringify(v, null, 2).replace(/\[\s*([^[\]{}]*?)\s*\]/g, (_, inner: string) => `[${inner.replace(/,\s+/g, ", ")}]`);
}
