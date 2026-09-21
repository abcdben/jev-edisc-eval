import { useEffect, useMemo, useState, type ReactNode } from "react";
import { CORPORA, PRIMARY_BY_KEY, VARIANT_LABEL, VARIANT_ORDER, fmtMs, fmtPct, isDecider, modelKind } from "../data";
import { EX, EX_GROUPS, exCorpus, groupOf, membersOf, type ExOutput } from "../examples";
import { DeciderTag, Seg, type TipLine } from "./ui";

/** The Metrics block: the full figures for one model on one corpus (what the chart tooltips used to carry), one fact list per card. */
export type MetricSection = { title: string; lines: TipLine[]; notes?: string[] };
export type Metrics = { name: string; color: string; context: string; sections: MetricSection[] };

function MetricsBlock({ m }: { m: Metrics }) {
  return (
    <section className="ex-metrics" aria-label="Metrics">
      <div className="ex-metrics-t"><span className="sw" style={{ background: m.color }} />Metrics<span className="ex-col-s">{m.name} · {m.context}</span></div>
      <div className="ex-metrics-grid">
        {m.sections.map((s) => (
          <div key={s.title} className="ex-metric">
            <div className="ex-metric-t">{s.title}</div>
            <dl>
              {s.lines.map((l, i) => (typeof l === "string"
                ? <div key={i} className="row"><dd className="line">{l}</dd></div>
                : <div key={i} className="row"><dt>{l[0]}</dt><dd>{l[1]}</dd></div>))}
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
  if (k === "laya-ft" || !k.includes("@")) return PRIMARY_BY_KEY[k]?.short ?? k;
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
const sortMembers = (ks: string[]) => [...ks].sort((a, b) => VARIANT_ORDER.indexOf(a.split("@")[1]) - VARIANT_ORDER.indexOf(b.split("@")[1]));

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
  const baseKey = group === "llm" ? null : group === "tar" ? (members.includes("tar@t1_1000") ? "tar@t1_1000" : members.find((m) => m.includes("@t1_")) ?? null) : members.find((m) => m.endsWith("@base")) ?? null;
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
  const note = group === "jev" ? EX.notes.jev[variant] : group.startsWith("laya") && group !== "laya-ft" ? EX.notes.laya[variant] : group === "llm" ? `${PRIMARY_BY_KEY[active]?.note ?? ""} ${EX.notes.llm}` : G.intro;
  const m = metrics && active ? metrics(active, corpus) : null;

  return (
    <div className="ex-back" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="ex-modal" role="dialog" aria-modal="true" aria-label="How each model is asked">
        <div className="ex-head">
          <div>
            <div className="ex-eyebrow">How each model is asked</div>
            <h2>{G.label}{cfg && members.length > 1 ? <span className="ex-h-var"> · {memberLabel(active)}</span> : null}{active && isDecider(modelKind(active)) && <DeciderTag />}</h2>
          </div>
          <div className="ex-head-ctl">
            <Seg value={corpus} onChange={(c) => setCorpus(c)} options={CORPORA.filter((c) => EX.corpora[c.id]).map((c) => ({ id: c.id, label: c.label, title: c.short }))} />
            <button className="ex-close" onClick={onClose} aria-label="close">×</button>
          </div>
        </div>

        <div className="ex-body">
          <aside className="ex-rail">
            <div className="grp">
              <div className="grp-t"><span>Family</span></div>
              {EX_GROUPS.filter((g) => membersOf(corpus, g.id).length).map((g) => (
                <button key={g.id} className={`pick${group === g.id ? "" : " off"}`} onClick={() => { setGroup(g.id); setKey(membersOf(corpus, g.id)[0]); }}>
                  <span className="nm">{g.label}</span>
                </button>
              ))}
            </div>
            {members.length > 1 && (
              <div className="grp">
                <div className="grp-t"><span>{group === "llm" ? "Model" : "Configuration"}</span><span className="ex-kbd">← →</span></div>
                {members.map((m) => (
                  <button key={m} className={`pick${active === m ? "" : " off"}`} onClick={() => setKey(m)}>
                    <span className="nm">{memberLabel(m)}</span>
                    {(m.endsWith("@base") || (group === "tar" && m === baseKey)) && <span className="tag">reference</span>}
                  </button>
                ))}
              </div>
            )}
            <div className="grp">
              <div className="grp-t"><span>Document</span></div>
              {C.documents.map((dd, i) => (
                <button key={dd.id} className={`pick${docIdx === i ? "" : " off"}`} onClick={() => setDocIdx(i)} title={dd.id}>
                  <span className="nm">{dd.gold === "responsive" ? "a gold-responsive document" : "a gold-not-responsive document"}</span>
                </button>
              ))}
              <div className="ex-q">Issue: <b>{C.question.title}</b></div>
            </div>
          </aside>

          <div className="ex-main">
            {m && <MetricsBlock m={m} />}
            <p className="ex-intro">{G.intro}</p>
            {cfg && (
              <>
                {note && note !== G.intro && <p className="ex-note">{note}</p>}
                {base && d.changed.size === 0 && d.removed.length === 0 && (
                  <p className="ex-same">On this corpus and issue the request is identical to the default: the lever has nothing to act on here{variant === "decompose" ? " (this issue has no sub-questions in the task file; try CUAD or TREC)" : ""}. Any difference in the output is run-to-run variation.</p>
                )}
                <div className="ex-cols">
                  <div className="ex-col">
                    <div className="ex-col-t">{group === "tar" ? "Workflow" : "Request"}<span className="ex-col-s">{group === "tar" ? "how the coded sample and classifier were produced" : "what was sent, with the document and background folded"}</span></div>
                    {ex && <Node v={ex.request} path="" changed={d.changed} doc={doc.text} ctx={C.context} />}
                    {base && d.removed.length > 0 && (
                      <div className="ex-removed">Not present in this configuration (present in the default): {d.removed.map((p) => p.replace(/^questions\.[^.]+\./, "question.")).join(", ")}</div>
                    )}
                  </div>
                  <div className="ex-col pin">
                    <div className="ex-col-t">Settings<span className="ex-col-s">fixed for the whole run</span></div>
                    <Node v={settingsFor(group, cfg.settings)} path="settings" changed={base ? diff(settingsFor(group, cfg.settings), settingsFor(group, base.settings)).changed : new Set()} doc="" ctx="" />
                    <div className="ex-col-t" style={{ marginTop: 18 }}>Output<span className="ex-col-s">what the model actually returned</span></div>
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
