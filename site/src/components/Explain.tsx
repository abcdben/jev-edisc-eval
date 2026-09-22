import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { ABLATION_GROUPS, CORPORA, DATA, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER, fmtMs, fmtPct, isDecider, modelKind, variantDefinition } from "../data";
import { EX, EX_GROUPS, exCorpus, groupOf, membersOf, type ExOutput } from "../examples";
import { DeciderTag, Seg, usePopDismiss, usePopPlace, type TipLine } from "./ui";

/** The Metrics block: the full figures for one model on one corpus (what the chart tooltips used to carry), one fact list per card. */
export type MetricSection = { title: string; lines: TipLine[]; notes?: string[] };
export type Metrics = { name: string; color: string; context: string; sections: MetricSection[] };

/** `**term**` in a string renders as <b>: the one bit of markup the group intros and lead sentences use. */
function Rich({ s }: { s: string }) {
  const parts = s.split(/\*\*(.+?)\*\*/);
  return <>{parts.map((p, i) => (i % 2 ? <b key={i}>{p}</b> : p))}</>;
}
/** The first occurrence of `term` in `s`, in bold; the whole string untouched when the term is absent. */
function Emph({ s, term }: { s: string; term?: string }) {
  const i = term ? s.indexOf(term) : -1;
  if (i < 0 || !term) return <>{s}</>;
  return <>{s.slice(0, i)}<b>{term}</b>{s.slice(i + term.length)}</>;
}

function MetricsBlock({ m }: { m: Metrics }) {
  return (
    <section className="ex-metrics" aria-label="Metrics">
      <div className="ex-metrics-t"><span className="sw" style={{ background: m.color }} />Metrics<span className="ex-col-s">{m.name} · {m.context}</span></div>
      <div className="ex-metrics-grid">
        {m.sections.map((s, si) => (
          <div key={s.title} className="ex-metric">
            <div className="ex-metric-t">{s.title}</div>
            <dl>
              {s.lines.map((l, i) => (typeof l === "string"
                ? <div key={i} className="row"><dd className="line">{l}</dd></div>
                : <div key={i} className="row"><dt>{l[0]}</dt><dd className={si === 0 && (l[0] === "Recall" || l[0] === "Precision") ? "hl" : undefined}>{l[1]}</dd></div>))}
            </dl>
            {s.notes?.filter(Boolean).map((n, i) => <p key={i} className="ex-metric-note">{n}</p>)}
          </div>
        ))}
      </div>
    </section>
  );
}

// ------------------------------------------------------------------------------------------------
// diff helpers: leaf paths whose value differs from the family's default configuration

type Leaves = Map<string, string>;
function leaves(v: unknown, path = "", out: Leaves = new Map()): Leaves {
  if (v && typeof v === "object" && !Array.isArray(v)) {
    for (const [k, x] of Object.entries(v as Record<string, unknown>)) leaves(x, path ? `${path}.${k}` : k, out);
  } else if (Array.isArray(v)) {
    v.forEach((x, i) => leaves(x, `${path}[${i}]`, out));
  } else out.set(path, JSON.stringify(v));
  return out;
}
function diff(cur: unknown, base: unknown): { changed: Set<string>; removed: string[] } {
  const a = leaves(cur), b = leaves(base);
  const changed = new Set<string>();
  for (const [p, s] of a) if (b.get(p) !== s) changed.add(p);
  const removed = [...b.keys()].filter((p) => !a.has(p));
  return { changed, removed };
}
const memberLabel = (k: string) => {
  if (k === "laya-ft") return "fine-tuned"; // the Laya row on Compare models, listed among Laya's zero-shot configurations
  if (!k.includes("@")) return PRIMARY_BY_KEY[k]?.short ?? k;
  const v = k.split("@")[1];
  return VARIANT_LABEL[v] ?? v;
};
/** Jev's config object carries Laya-only levers (chunk, compact) that never apply to it. */
const settingsFor = (group: string, s: Record<string, unknown>) => {
  const drop = group === "jev" ? ["chunk", "compact"] : group.startsWith("laya") ? ["model_id"] : [];
  const o = Object.fromEntries(Object.entries(s).filter(([k]) => !drop.includes(k)));
  if (group === "llm" && o.effort == null) o.effort = "vendor default";
  return o;
};
/** Variant order from data.ts; a key without a variant (`laya-ft`, the Compare row) sorts first. */
const sortMembers = (ks: string[]) => [...ks].sort((a, b) => VARIANT_ORDER.indexOf(a.split("@")[1]) - VARIANT_ORDER.indexOf(b.split("@")[1]));

/** The term set in bold inside the lever callout (the note from examples.py), one per variant; the callout is plain when a variant has none. */
const NOTE_KEY_TERM: Record<string, Record<string, string>> = {
  jev: {
    base: "probability", choice: "Choice", score: "Score", crit_none: "no criteria", crit_struct: "structured object", literal: "'literal' phrasing",
    no_context: "only the document", state_string: "single flat string", gate: "gate probability", ensemble: "averaged", decompose: "logical OR", preview: "jev-preview",
  },
  laya: {
    base: "512", choice: "Choice", score: "Score", literal: "literal phrasing", gate: "gates", ensemble: "averaged", decompose: "OR'd",
    compact: "192-token head", chunk: "max over windows", recipe: "compact + chunk", recipe_choice: "Choice form",
  },
  llm: { "": "JSON schema" },
};
const noteFamily = (group: string) => (group === "jev" ? "jev" : group.startsWith("laya") ? "laya" : group);

/**
 * The opening sentence of the modal: what this configuration is, in plain words, with the definition
 * (data.ts VARIANT_DEFINITION) highlighted. `**…**` marks the bold configuration name.
 */
function leadFor(group: string, key: string, corpus: string, groupLabel: string): { pre: string; def: string; post: string } | null {
  const corpusLabel = CORPORA.find((c) => c.id === corpus)?.label ?? corpus;
  const def = variantDefinition(key, corpusLabel);
  if (!def) return null;
  const v = key.includes("@") ? key.split("@")[1] : "";
  const name = `**${groupLabel}${v ? ` · ${VARIANT_LABEL[v] ?? v}` : ""}**`;
  if (group === "jev") {
    if (v === "base") return { pre: `${name} is the baseline configuration of TypeSafe Jev 1.13, a decision model: `, def, post: ". Every other Jev configuration changes one lever from this one." };
    const star = v === "state_string" ? " It is the configuration selected on the Veridian dev split." : "";
    return { pre: `${name} is the Jev 1.13 configuration in which `, def, post: `. Everything else matches the default.${star}` };
  }
  if (key === "laya-ft") return { pre: `**${groupLabel} · fine-tuned** is the Laya row on Compare models: `, def, post: ". Not on equal footing with the zero-shot configurations." };
  if (group.startsWith("laya")) {
    const ckpt = group === "laya-typed" ? "the typed Laya checkpoint" : group === "laya-multilingual" ? "the multilingual Laya checkpoint" : "ConvAI Laya (English checkpoint), a local decision model";
    if (v === "base") return { pre: `${name} is the baseline configuration of ${ckpt}: `, def, post: `. Every other ${group === "laya" ? "zero-shot " : ""}${groupLabel} configuration changes one lever from this one.` };
    const star = v === "recipe" ? " It is the configuration selected on the Veridian dev split." : "";
    return { pre: `${name} is the ${groupLabel} configuration in which `, def, post: `. Everything else matches the ${groupLabel} default.${star}` };
  }
  if (group === "llm") {
    const p = PRIMARY_BY_KEY[key];
    return { pre: `**${p?.short ?? DATA.models[key]?.name ?? key}** is a generative model asked with `, def, post: `.${p?.note ? ` ${p.note}` : ""}` };
  }
  if (group === "tar") {
    const label = VARIANT_LABEL[v] ?? v;
    const plain = /^t1_\d+(_div)?$/.test(v); // the shown TAR 1.0 rows read as full definitions; F1 / noisy crosses as deltas
    return { pre: `**${label}** is ${plain ? "the classical TAR row in which " : ""}`, def, post: ". No model reads the request; every figure is the median of the random seeds." };
  }
  return null;
}

// ------------------------------------------------------------------------------------------------
// JSON renderer with {{document}} / {{context}} chips and change highlighting

function Str({ s, doc, ctx }: { s: string; doc: string; ctx: string }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const parts = s.split(/(\{\{document\}\}|\{\{context\}\})/);
  return (
    <span className="ex-str">
      {parts.map((p, i) => {
        if (p === "{{document}}" || p === "{{context}}") {
          const id = p.slice(2, -2), full = id === "document" ? doc : ctx;
          return (
            <span key={i}>
              <button className={`ex-chip${open[id] ? " on" : ""}`} onClick={() => setOpen((o) => ({ ...o, [id]: !o[id] }))} title={open[id] ? "collapse" : "expand"}>
                {id === "document" ? "the document" : "matter background"} · {full.length.toLocaleString()} chars {open[id] ? "▾" : "▸"}
              </button>
              {open[id] && <span className="ex-inline">{full}</span>}
            </span>
          );
        }
        return <span key={i}>{p}</span>;
      })}
    </span>
  );
}

function Node({ v, path, changed, doc, ctx }: { v: unknown; path: string; changed: Set<string>; doc: string; ctx: string }): ReactNode {
  if (v === null || v === undefined) return <code className="ex-lit">null</code>;
  if (typeof v === "boolean" || typeof v === "number") return <code className="ex-lit">{String(v)}</code>;
  if (typeof v === "string") return <Str s={v} doc={doc} ctx={ctx} />;
  if (Array.isArray(v)) {
    if (v.every((x) => typeof x === "string") && v.length > 6) return <span className="ex-str">{(v as string[]).join(", ")}</span>;
    return (
      <div className="ex-arr">
        {v.map((x, i) => {
          const p = `${path}[${i}]`;
          return <div key={i} className={`ex-item${changed.has(p) ? " chg" : ""}`}><span className="ex-idx">{i + 1}</span><Node v={x} path={p} changed={changed} doc={doc} ctx={ctx} /></div>;
        })}
      </div>
    );
  }
  const o = v as Record<string, unknown>;
  const entries = Object.entries(o);
  // a map of objects (e.g. questions keyed by issue id): titled blocks at full width instead of nested key columns
  if (entries.length && entries.every(([, x]) => x && typeof x === "object" && !Array.isArray(x))) {
    return (
      <div className="ex-blocks">
        {entries.map(([k, x]) => {
          const p = path ? `${path}.${k}` : k;
          return (
            <div key={k} className="ex-block">
              <div className="ex-block-t">{k}</div>
              <Node v={x} path={p} changed={changed} doc={doc} ctx={ctx} />
            </div>
          );
        })}
      </div>
    );
  }
  return (
    <div className="ex-obj">
      {entries.map(([k, x]) => {
        const p = path ? `${path}.${k}` : k;
        const leaf = x === null || typeof x !== "object";
        const sub = !leaf && [...changed].some((c) => c.startsWith(p + ".") || c.startsWith(p + "["));
        if (k === "response_schema") {
          return (
            <div key={k} className="ex-row">
              <div className="ex-k">{k}</div>
              <details className="ex-details"><summary>JSON schema enforced on the reply</summary><pre>{JSON.stringify(x, null, 2)}</pre></details>
            </div>
          );
        }
        const isMap = !leaf && !Array.isArray(x) && Object.values(x as object).length > 0 && Object.values(x as object).every((y) => y && typeof y === "object" && !Array.isArray(y));
        if (isMap) {
          return (
            <div key={k} className={`ex-row full${sub ? " sub" : ""}`}>
              <div className="ex-k">{k}</div>
              <Node v={x} path={p} changed={changed} doc={doc} ctx={ctx} />
            </div>
          );
        }
        return (
          <div key={k} className={`ex-row${leaf && changed.has(p) ? " chg" : ""}${sub ? " sub" : ""}`}>
            <div className="ex-k">{k}{k === "type" && typeof x === "string" ? <span className="ex-type">{x}</span> : null}</div>
            <div className="ex-v"><Node v={x} path={p} changed={changed} doc={doc} ctx={ctx} /></div>
          </div>
        );
      })}
    </div>
  );
}

// ------------------------------------------------------------------------------------------------

function Output({ o, gold, contended }: { o: ExOutput; gold: string; contended: boolean }) {
  if (!o) return <div className="ex-empty">This configuration was not run on this document.</div>;
  const ok = o.label === gold;
  const rows: [string, ReactNode][] = [
    ["label", <span className={`ex-label ${ok ? "ok" : "bad"}`}>{o.label ?? "—"} <span className="ex-gold">{ok ? "matches gold" : `gold is ${gold}`}</span></span>],
    ["p(responsive)", o.p_positive == null ? "—" : o.p_positive.toFixed(3)],
    ["confidence", o.confidence == null ? "—" : `${o.confidence.toFixed(2)}  (|2p − 1|)`],
    ["latency", o.latency_ms == null ? "—" : contended ? `${fmtMs(o.latency_ms)} (queued behind 64 concurrent requests on one A100; the site's review-time panel uses a one-at-a-time sample)` : fmtMs(o.latency_ms)],
    ["tokens", o.input_tokens == null ? "—" : `${o.input_tokens.toLocaleString()} in · ${(o.output_tokens ?? 0).toLocaleString()} out`],
    ["cost", o.cost_usd == null ? "—" : o.cost_usd === 0 ? (o.model_resolved === "tfidf-logreg" ? "$0 compute; the reviewer's time is in the request" : "$0 (local)") : `$${o.cost_usd.toFixed(6)}`],
    ["served by", o.model_resolved ?? "—"],
  ];
  const isTar = o.model_resolved === "tfidf-logreg";
  const shown = isTar ? rows.filter(([k]) => k !== "latency" && k !== "tokens" && k !== "confidence") : rows;
  if (o.error) shown.push(["error", <code className="ex-lit">{o.error}</code>]);
  return (
    <div className="ex-obj">
      {shown.map(([k, v]) => <div key={k} className="ex-row"><div className="ex-k">{k}</div><div className="ex-v">{v}</div></div>)}
      {o.raw && Object.keys(o.raw).length > 0 && (
        <div className="ex-row"><div className="ex-k">raw</div><div className="ex-v"><Node v={o.raw} path="raw" changed={new Set()} doc="" ctx="" /></div></div>
      )}
      <div className="ex-foot">{isTar ? "The median seed's call on this document. p(responsive) is the classifier's probability, or 1 / 0 when the reviewer coded the document by hand." : `Recorded in the ${o.arm === "single" ? "one-issue-per-call" : "all-issues-per-call"} run; the request shown is the one-issue form.`}</div>
    </div>
  );
}

// ------------------------------------------------------------------------------------------------
// title menus: the h2 is two menu buttons, [family ▾] · [configuration ▾]

type MenuItem = { id: string; label: string; def?: string; tags?: { text: string; title?: string }[] };
/** `s` cut at a word boundary to about `n` characters, with an ellipsis; unchanged when it fits. The row's CSS ellipsis does the exact fit; this bounds the text. */

/**
 * One title menu: a button styled as the h2's text with a small chevron, opening a fixed-position menu below it (right-aligned or above at the
 * viewport edge, the same rules as Hint). Rows are menuitemradios, the current one checked; ↑↓ move focus, Enter selects, Esc closes and returns
 * focus to the button; a pointerdown outside closes it. The menu re-renders live while open, so ← → on the modal move the check mark.
 */
function TitleMenu({ label, value, items, onPick, muted, wide, ariaLabel, foot }: {
  label: string; value: string; items: MenuItem[]; onPick: (id: string) => void; muted?: boolean; wide?: boolean; ariaLabel: string; foot?: string;
}) {
  // ariaLabel doubles as the small caption over the control ("Family", "Configuration", "Model") so it reads as a selector, not a title
  const [open, setOpen] = useState(false);
  const wrap = useRef<HTMLSpanElement>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const pop = useRef<HTMLDivElement>(null);
  const id = useId();
  const place = usePopPlace(open, wrap, pop, "left");
  usePopDismiss(open, wrap, () => setOpen(false));
  // focus the checked row once the menu is placed (it is visibility: hidden until then, and cannot take focus); the keyboard handler below moves it
  const placed = open && place !== null;
  useEffect(() => {
    if (!placed) return;
    const el = pop.current?.querySelector<HTMLElement>('[role="menuitemradio"][aria-checked="true"]') ?? pop.current?.querySelector<HTMLElement>('[role="menuitemradio"]');
    el?.focus();
  }, [placed]);
  const close = (refocus: boolean) => { setOpen(false); if (refocus) btn.current?.focus(); };
  const onKey = (e: React.KeyboardEvent) => {
    if (!open) return;
    const rows = [...(pop.current?.querySelectorAll<HTMLElement>('[role="menuitemradio"]') ?? [])];
    const i = rows.findIndex((r) => r === document.activeElement);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault(); e.stopPropagation();
      const n = rows.length;
      rows[i < 0 ? (e.key === "ArrowDown" ? 0 : n - 1) : (i + (e.key === "ArrowDown" ? 1 : n - 1)) % n]?.focus();
    } else if (e.key === "Home" || e.key === "End") {
      e.preventDefault(); e.stopPropagation();
      rows[e.key === "Home" ? 0 : rows.length - 1]?.focus();
    } else if (e.key === "Escape") {
      e.preventDefault(); e.stopPropagation(); close(true);
    } else if (e.key === "Tab") close(false);
  };
  return (
    <span ref={wrap} className={`ex-menu${open ? " open" : ""}`} onKeyDown={onKey}>
      <span className="ex-menu-cap" aria-hidden="true">{ariaLabel}</span>
      <button
        ref={btn} type="button" className={`ex-menu-b${muted ? " muted" : ""}`} aria-haspopup="menu" aria-expanded={open} aria-controls={open ? id : undefined} aria-label={`${ariaLabel}: ${label}`}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="ex-menu-v">{label}</span><svg className="ex-chev" aria-hidden="true" viewBox="0 0 10 10" width="10" height="10"><path d="M2 3.5 5 6.5 8 3.5" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </button>
      {open && (
        <div ref={pop} id={id} role="menu" aria-label={ariaLabel} className={`ex-menu-pop${wide ? " wide" : ""}`} style={{ left: place?.left ?? 0, top: place?.top ?? 0, visibility: place ? "visible" : "hidden" }}>
          <div className="ex-menu-list">
            {items.map((it) => (
              <button
                key={it.id} type="button" role="menuitemradio" aria-checked={it.id === value} className={`ex-mi${it.id === value ? " on" : ""}`} title={it.def}
                onClick={() => { onPick(it.id); close(true); }}
              >
                <span className="ex-mi-chk" aria-hidden="true">{it.id === value ? "✓" : ""}</span>
                <span className="ex-mi-body">
                  <span className="ex-mi-l">{it.label}{it.tags?.map((t) => <span key={t.text} className="tag" title={t.title}>{t.text}</span>)}</span>
                </span>
              </button>
            ))}
          </div>
          {foot && <div className="ex-menu-foot">{foot}</div>}
        </div>
      )}
    </span>
  );
}

// ------------------------------------------------------------------------------------------------

/** `metrics` supplies the Metrics block for the selected configuration on the modal's corpus; without it (or when it returns null) the block is omitted. */
export function ExplainModal({ initialKey, initialCorpus, onClose, metrics }: { initialKey: string; initialCorpus: string; onClose: () => void; metrics?: (key: string, corpus: string) => Metrics | null }) {
  const [corpus, setCorpus] = useState(exCorpus(initialCorpus));
  const [group, setGroup] = useState(groupOf(initialKey));
  const [key, setKey] = useState(initialKey);
  const [docIdx, setDocIdx] = useState(0);

  const C = EX.corpora[corpus];
  const members = useMemo(() => sortMembers(membersOf(corpus, group)), [corpus, group]);
  const G = EX_GROUPS.find((g) => g.id === group)!;
  const active = members.includes(key) ? key : members[0];
  const cfg = active ? C.configs[active] : null;
  const baseKey = group === "llm" ? null : group === "tar" ? (members.includes("tar@t1_1000_div") ? "tar@t1_1000_div" : members.includes("tar@t1_1000") ? "tar@t1_1000" : members.find((m) => m.includes("@t1_")) ?? null) : members.find((m) => m.endsWith("@base")) ?? null;
  const base = baseKey && baseKey !== active ? C.configs[baseKey] : null;

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        const i = members.indexOf(active);
        if (i < 0) return;
        setKey(members[(i + (e.key === "ArrowRight" ? 1 : members.length - 1)) % members.length]);
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [members, active, onClose]);
  useEffect(() => { document.body.style.overflow = "hidden"; return () => { document.body.style.overflow = ""; }; }, []);

  const ex = cfg?.examples[docIdx];
  const d = diff(ex?.request, base ? base.examples[docIdx]?.request : ex?.request);
  const doc = C.documents[docIdx];
  const variant = cfg?.variant ?? "";
  const note = group === "jev" ? EX.notes.jev[variant] : group.startsWith("laya") && active !== "laya-ft" ? EX.notes.laya[variant] : group === "llm" ? EX.notes.llm : G.intro;
  const m = metrics && active ? metrics(active, corpus) : null;
  const lead = active ? leadFor(group, active, corpus, G.label) : null;
  const recipe = ABLATION_GROUPS.find((g) => g.id === group)?.recipe;
  const corpusLabel = CORPORA.find((c) => c.id === corpus)?.label ?? corpus;
  // For Jev and the Laya checkpoints the lever callout (examples.py note) says what the lead's highlighted definition already says, so the
  // lead replaces it. The LLM callout stays: the prompt's parts and the cache-friendly prefix are not in the lead or the request pane.
  const showNote = !!note && note !== G.intro && (!lead || group === "llm");

  // hidden families (the typed / multilingual Laya checkpoints, reachable from the Configurations page) are listed only while current
  const familyItems: MenuItem[] = EX_GROUPS.filter((g) => (!g.hidden || g.id === group) && membersOf(corpus, g.id).length).map((g) => ({ id: g.id, label: g.label }));
  // the configuration rows: label, tags, and the one-line definition (for the generative models, the roster note: their definition is shared)
  const memberItems: MenuItem[] = members.map((k) => ({
    id: k, label: memberLabel(k),
    def: group === "llm" ? PRIMARY_BY_KEY[k]?.note ?? variantDefinition(k, corpusLabel) : variantDefinition(k, corpusLabel),
    tags: [
      ...(k.endsWith("@base") || (group === "tar" && k === baseKey) ? [{ text: "reference" }] : []),
      ...(k === "laya-ft" ? [{ text: "Compare models", title: "the Laya row charted on Compare models; the other configurations are zero-shot" }] : []),
      ...(recipe && k.split("@")[1] === recipe ? [{ text: "★ selected", title: "selected on the Veridian dev split" }] : []),
    ],
  }));

  return (
    <div className="ex-back" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="ex-modal" role="dialog" aria-modal="true" aria-label="How each model is asked">
        <div className="ex-head">
          <div>
            <h2 className="ex-title">
              <TitleMenu label={G.label} value={group} items={familyItems} ariaLabel="Family" onPick={(g) => { setGroup(g); setKey(membersOf(corpus, g)[0]); }} />
              {cfg && members.length > 1 && (
                <TitleMenu
                  label={memberLabel(active)} value={active} items={memberItems} wide ariaLabel={group === "llm" ? "Model" : "Configuration"}
                  onPick={setKey} foot={`← → cycle ${group === "llm" ? "models" : "configurations"}`}
                />
              )}
              {active && isDecider(modelKind(active)) && <DeciderTag />}
            </h2>
          </div>
          <div className="ex-head-ctl">
            <Seg value={corpus} onChange={(c) => setCorpus(c)} options={CORPORA.filter((c) => EX.corpora[c.id]).map((c) => ({ id: c.id, label: c.label, title: c.short }))} />
            <button className="ex-close" onClick={onClose} aria-label="close">×</button>
          </div>
        </div>

        <div className="ex-body">
          <div className="ex-main">
            {lead && <p className="ex-lead"><Rich s={lead.pre} /><mark>{lead.def}</mark><Rich s={lead.post} /></p>}
            {m && <MetricsBlock m={m} />}
            <p className="ex-intro"><Rich s={G.intro} /></p>
            {cfg && (
              <>
                {showNote && <p className="ex-note"><Emph s={note} term={NOTE_KEY_TERM[noteFamily(group)]?.[group === "llm" ? "" : variant]} /></p>}
                {base && d.changed.size === 0 && d.removed.length === 0 && (
                  <p className="ex-same">On this corpus and issue the request is identical to the default: the lever has nothing to act on here{variant === "decompose" ? " (this issue has no sub-questions in the task file; try CUAD or TREC)" : ""}. Any difference in the output is run-to-run variation.</p>
                )}
                <div className="ex-sec">
                  <span className="ex-sec-t">Example</span>
                  <span className="ex-col-s">{group === "tar" ? "one document from this corpus: the workflow that produced the classifier, and the call it recorded" : "one document from this corpus: the exact request that was sent, and the output that came back"}</span>
                </div>
                <div className="ex-cols">
                  <div className="ex-col">
                    <div className="ex-col-t">{group === "tar" ? "Example workflow" : "Example input"}<span className="ex-col-s">{group === "tar" ? "how the coded sample and classifier were produced" : "the request as sent, with the document and background folded"}</span></div>
                    {ex && <Node v={ex.request} path="" changed={d.changed} doc={doc.text} ctx={C.context} />}
                    {base && d.removed.length > 0 && (
                      <div className="ex-removed">Not present in this configuration (present in the default): {d.removed.map((p) => p.replace(/^questions\.[^.]+\./, "question.")).join(", ")}</div>
                    )}
                  </div>
                  <div className="ex-col pin">
                    <div className="ex-col-t">Settings<span className="ex-col-s">fixed for the whole run</span></div>
                    <Node v={settingsFor(group, cfg.settings)} path="settings" changed={base ? diff(settingsFor(group, cfg.settings), settingsFor(group, base.settings)).changed : new Set()} doc="" ctx="" />
                    <div className="ex-col-t ex-out-t">
                      <span className="ex-out-row">
                        Example output
                        <Seg
                          value={String(docIdx)} onChange={(v) => setDocIdx(Number(v))}
                          options={C.documents.map((dd, i) => ({ id: String(i), label: dd.gold === "responsive" ? "gold-responsive" : "gold-not-responsive", title: `${dd.gold === "responsive" ? "a gold-responsive" : "a gold-not-responsive"} document (${dd.id})` }))}
                        />
                      </span>
                      <span className="ex-col-s">Issue: <b>{C.question.title}</b> · what the model returned on this document</span>
                    </div>
                    <Output o={ex?.output ?? null} gold={doc.gold} contended={group.startsWith("laya")} />
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
        <div className="ex-legend">
          {base && <span><span className="ex-sw chg" /> differs from the default configuration</span>}
          <span>Probabilities are the model's own; every model's label is “responsive” when p ≥ {fmtPct(0.5, 0)}.</span>
          <span>Nothing here was re-run: requests are rebuilt by the benchmark code, outputs are the recorded rows.</span>
        </div>
      </div>
    </div>
  );
}

/** Small "how it works" affordance used next to picker rows and section heads. */
export function ExplainButton({ onClick, label = "details", compact = false }: { onClick: () => void; label?: string; compact?: boolean }) {
  // a span, not a button: it lives inside picker rows that are themselves <button>s
  return (
    <span
      className={compact ? "ex-btn ex-i" : "ex-btn"} role="button" tabIndex={0} aria-label={compact ? "details" : undefined}
      onClick={(e) => { e.stopPropagation(); e.preventDefault(); onClick(); }}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.stopPropagation(); e.preventDefault(); onClick(); } }}
      title="Configuration details: the request sent and the answer returned"
    >
      {compact ? "i" : label}
    </span>
  );
}
