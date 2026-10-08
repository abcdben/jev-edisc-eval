import { useEffect, useMemo, useRef, useState } from "react";
import { Modal, Seg } from "./components/ui";
import { THEME_KEY, THEME_OPTIONS, readTheme, type Theme } from "./theme";
import {
  LAB_NAME, LAB_SHORT, TEXT_API, armsOf, bucketDefs, bucketOf, fetchText, fmtN, fmtShare, inheritScores, kappa, labelerFor, loadArm, loadIndex, loadMeta, loadRows, outcomeOf, reviewerScores, scorerFor, topicName, unitsOf,
  type Arm, type ArmScores, type Dataset, type DocText, type Index, type Lab, type Rows, type TarMeta, type Unit,
} from "./exploreData";
import { Confidence, Flow, Mosaic, cellKey, type Cells, type ConfGroup, type Scale, type Sel } from "./explore/Views";
import { Venn } from "./explore/Venn";
import { TarReviewerControl } from "./components/TarReviewer";
import { GRID_RATES, REALISTIC_REVIEWER, asReviewer, isPublished, type ReviewerSetting } from "./tarGrid";

type View = "mosaic" | "flow" | "venn" | "confidence";
type Slots = { standard: string; a: string | null; b: string | null; topics: string[] };
/** `tarReviewer` (tarGrid.ts): the simulated reviewer's error rates for the TAR arms that carry a meta file (exploreData.ts reviewerScores; REALISTIC_REVIEWER to start); "published" is the shipped scores. */
/** `v` marks a state stored since the page opened from scratch (migrate); a stored state without it is from before, when the export's suggested arms were pre-placed. */
/** `rail`: the controls rail (dataset, topics, arms, options) is shown; folded away, the chart has the whole width. */
type State = { v?: 2; dataset: string; slots: Record<string, Slots>; unit: "docs" | "families"; inherit: Record<string, boolean>; view: View; scale: Scale; threshold: number; sort: SortKey; tarReviewer: ReviewerSetting; rail: boolean };
type SortKey = "p_desc" | "p_asc" | "chars" | "psel" | "id";
const KEY = "explore-state-v1";
const DEFAULT: State = { dataset: "legal10", slots: {}, unit: "docs", inherit: {}, view: "mosaic", scale: "sqrt", threshold: 0.5, sort: "p_desc", tarReviewer: REALISTIC_REVIEWER, rail: true };
// a stored null (the shipped scores, before the realistic default existed) coerces to undefined and so starts at the default
const readState = (): State => { try { const s = { ...DEFAULT, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; return { ...s, tarReviewer: asReviewer(s.tarReviewer) ?? REALISTIC_REVIEWER }; } catch { return DEFAULT; } };
/**
 * A state stored before the page opened from scratch (no `v`), once the index is known: a dataset's slots holding exactly the export's suggested
 * pair (index.json `default.a` / `default.b`, pre-placed on every visit back then) are the old default rather than a choice, and are emptied; any
 * other stored placement is kept. Runs once: the state is marked `v: 2` after.
 */
const migrate = (s: State, index: Index): State => {
  if (s.v === 2) return s;
  const slots = Object.fromEntries(Object.entries(s.slots).map(([id, sl]) => { const d = index.datasets.find((x) => x.id === id); return [id, d && sl.a === d.default.a && sl.b === d.default.b ? { ...sl, a: null, b: null } : sl]; }));
  return { ...s, v: 2, slots };
};
/** What the explorer's reviewer setting does, in place of the grid pages' line: the reviewer's own calls re-coded per document from the run's provenance. */
const REVIEWER_ONLY = "Reviewer error re-codes the simulated reviewer's calls document by document from the run's provenance; the classifier and stopping point stay at the published run.";
/** The TAR arms in the slots that carry reviewer provenance: the ones the reviewer sliders can re-code. */
const reviewerArmsOf = (ds: Dataset, slots: Slots) => [slots.standard, slots.a, slots.b].flatMap((id) => { const a = id ? ds.arms.find((x) => x.id === id) : undefined; return a && a.kind === "tar" ? [a] : []; });
const PAGE = 200;

export default function ExplorePage() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem(THEME_KEY, theme); } catch { /* ignore */ } }, [theme]);
  const [s, setS] = useState<State>(readState);
  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* ignore */ } }, [s]);
  const up = (p: Partial<State>) => setS((x) => ({ ...x, ...p }));

  const [index, setIndex] = useState<Index | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => { loadIndex().then((idx) => { setS((cur) => migrate(cur, idx)); setIndex(idx); }).catch((e) => setErr(String(e))); }, []);

  if (err) return <div className="page explore-page"><div className="card"><div className="study-empty">Could not load explore/index.json ({err}). Run <code>bench export-explore</code>.</div></div></div>;
  if (!index) return <div className="page explore-page"><div className="card"><div className="study-empty">Loading…</div></div></div>;
  const ds = index.datasets.find((d) => d.id === s.dataset) ?? index.datasets[0];
  // A fresh visit starts from scratch: the collection's standard and topic (both required for anything to render) with no arm A and no overlay B; the
  // export's suggested arms (index.json `default.a` / `default.b`) are not pre-placed, the visitor picks them in the rail.
  const slots: Slots = s.slots[ds.id] ?? { standard: ds.default.standard, a: null, b: null, topics: ds.default.topics };
  const setSlots = (p: Partial<Slots>) => up({ slots: { ...s.slots, [ds.id]: { ...slots, ...p } } });

  return (
    <div className="page explore-page">
      <header className="study-hdr">
        <div>
          <h1>Population explorer</h1>
          <p className="sub">Who called each judged document responsive. Click a piece of the chart to list and read its documents.</p>
        </div>
        <div className="study-hdr-r">
          <button className="pe-rail-btn" onClick={() => up({ rail: !s.rail })} aria-pressed={!s.rail} title={s.rail ? "Fold the controls away; the chart takes the whole width" : "Show the dataset, topic, arm and option controls"}>{s.rail ? "Hide controls" : "Show controls"}</button>
          <a className="home-link" href="./" title="The landing page: every page of the site">Home</a>
          <a className="pe-link" href="./study.html">Study</a>
          <Seg value={theme} onChange={setTheme} options={THEME_OPTIONS.map((t) => ({ id: t.id, label: t.label, title: t.title }))} />
        </div>
      </header>
      <About />
      <div className={`study-body explore-body${s.rail ? "" : " no-rail"}`}>
        {s.rail && <Rail index={index} ds={ds} slots={slots} setSlots={setSlots} state={s} up={up} />}
        <main className="study-main">
          <Population key={ds.id} ds={ds} slots={slots} state={s} up={up} />
        </main>
      </div>
    </div>
  );
}

/** The method text, folded away under the title ("About this view"); the page itself is the chart. */
function About() {
  return (
    <details className="pe-about">
      <summary>About this view</summary>
      <div className="pe-about-body">
        <p>Every judged document of a collection, cut by who called it responsive: a <b>standard</b>, an <b>arm A</b> read against it, and an optional <b>overlay B</b>, each a human signal or a model. Pick them in the controls; a model's call is its score against the threshold.</p>
        <p><b>Mosaic</b>: one column per way A came out against the standard (both responsive, both not, A missed, A over-called, gray), width ∝ units, each column split by B's call. <b>Flow</b>: every unit travels A → standard → B, band width ∝ units. <b>Venn</b>: one circle per arm, area ∝ its responsive calls, overlaps where they agree; the box is everyone judged. <b>Confidence</b>: the model's p(responsive) in ten bins, stacked by how the other arms came out.</p>
        <p>Click any piece of the chart to list its documents below and read them (text comes from <code>bench serve</code> on this machine); click it again, press Esc or use × to clear. Hover for the count and share. <b>linear / √</b> sets whether sizes follow the counts or their square roots, which keeps small groups visible. The reviewer sliders re-code a TAR arm's simulated reviewer document by document from the run's provenance; the classifier and stopping point stay at the published run.</p>
      </div>
    </details>
  );
}

// ------------------------------------------------------------------------------------------------ rail

const inheritOn = (s: State, ds: Dataset) => ds.has_attachments && (s.inherit[ds.id] ?? ds.inherit_default);

function Rail({ index, ds, slots, setSlots, state: s, up }: { index: Index; ds: Dataset; slots: Slots; setSlots: (p: Partial<Slots>) => void; state: State; up: (p: Partial<State>) => void }) {
  const arms = armsOf(ds);
  const inherit = inheritOn(s, ds);
  const kinds = [...new Set(ds.topics.map((t) => t.kind))];
  const toggleTopic = (t: string) => {
    const kind = ds.topics.find((x) => x.id === t)!.kind;
    const sameKind = slots.topics.filter((x) => ds.topics.find((y) => y.id === x)?.kind === kind);
    if (sameKind.length !== slots.topics.length) return setSlots({ topics: [t] }); // switching between responsiveness and privilege: start over
    const next = slots.topics.includes(t) ? slots.topics.filter((x) => x !== t) : [...slots.topics, t];
    if (next.length) setSlots({ topics: ds.topics.filter((x) => next.includes(x.id)).map((x) => x.id) });
  };
  const place = (slot: "standard" | "a" | "b", id: string | null) => {
    const cur: Record<string, string | null> = { standard: slots.standard, a: slots.a, b: slots.b };
    const was = id != null ? Object.keys(cur).find((k) => cur[k] === id) : undefined;
    if (was === slot) { if (slot === "standard") return; id = null; } // clicking the checked radio again takes the arm out (the standard is required)
    if (was && was !== slot) cur[was] = null; // the arm leaves the slot it held; the arm it displaces is dropped, not swapped in
    cur[slot] = id;
    if (cur.a == null && cur.b != null) { cur.a = cur.b; cur.b = null; } // an overlay with nothing to overlay is arm A
    if (cur.standard == null) return;
    setSlots({ standard: cur.standard, a: cur.a, b: cur.b });
  };
  const anyModel = [slots.standard, slots.a, slots.b].some((id) => id && !arms.find((a) => a.id === id)?.human);
  const tarArms = reviewerArmsOf(ds, slots);
  const { metas } = useScores(ds, tarArms.map((a) => a.id));
  const [hover, setHover] = useState<{ id: string; top: number; left: number } | null>(null);
  const [reqOpen, setReqOpen] = useState(false);
  const hoverTimer = useRef<number | null>(null);
  const enter = (e: React.MouseEvent, id: string) => { const r = (e.currentTarget as HTMLElement).getBoundingClientRect(); if (hoverTimer.current) clearTimeout(hoverTimer.current); hoverTimer.current = window.setTimeout(() => setHover({ id, top: r.top, left: r.right + 10 }), 260); };
  const leave = () => { if (hoverTimer.current) clearTimeout(hoverTimer.current); hoverTimer.current = null; setHover(null); };
  const hovered = hover ? ds.topics.find((t) => t.id === hover.id) : null;
  return (
    <aside className="study-rail explore-rail">
      <section>
        <h4>Dataset</h4>
        {index.datasets.map((d) => (
          <div key={d.id} className={`pick-row${d.id === ds.id ? " on" : ""}`}>
            <button className="pick-main" role="radio" aria-checked={d.id === ds.id} onClick={() => up({ dataset: d.id })} title={d.short}>
              <span className={`box radio${d.id === ds.id ? " on" : ""}`} /><span className="lbl"><span className="nm">{d.label}</span>{d.placeholders && <span className="tag" title="No model has been run on this collection yet; model arms are placeholders">planned</span>}{!d.text && <span className="tag">no text</span>}</span>
            </button>
          </div>
        ))}
        <p className="study-ds-note">{ds.short} · {fmtN(ds.n)} judgments · {fmtN(ds.n_docs)} documents{ds.has_attachments ? ` · ${fmtN(ds.n_families)} message families` : ""}</p>
      </section>

      <section>
        <h4>Topics<span className="n">{slots.topics.length}/{ds.topics.length}</span></h4>
        {kinds.map((k) => (
          <div key={k}>
            {kinds.length > 1 && <div className="pick-sh">{k === "privilege" ? "Privilege review" : "Responsiveness"}</div>}
            {ds.topics.filter((t) => t.kind === k).map((t) => {
              const on = slots.topics.includes(t.id);
              return (
                <div key={t.id} className={`pick-row${on ? " on" : ""}`} onMouseEnter={(e) => enter(e, t.id)} onMouseLeave={leave}>
                  <button className="pick-main" role="checkbox" aria-checked={on} onClick={() => toggleTopic(t.id)}>
                    <span className={`box${on ? " on" : ""}`} /><span className="lbl"><span className="nm">{topicName(t)}</span><span className="pe-tn">{fmtN(t.n)}</span></span>
                  </button>
                  <button className="pick-i" aria-label={`Request ${t.id}`} onClick={() => { leave(); setReqOpen(true); }}>i</button>
                </div>
              );
            })}
          </div>
        ))}
        {kinds.length > 1 && <p className="study-ds-note">Responsiveness topics pool together; the privilege review is viewed on its own.</p>}
        <button className="pe-req-btn" onClick={() => { leave(); setReqOpen(true); }}>All requests · {ds.topics.length}</button>
        {hovered && hover && (
          <div className="pe-topic-pop" style={{ top: Math.min(hover.top, window.innerHeight - 320), left: hover.left }}>
            <div className="t">{topicName(hovered)}</div>
            <div className="m">{fmtN(hovered.n)} judged · {fmtN(hovered.n_pos)} responsive ({fmtShare(hovered.n_pos / (hovered.n || 1))}){hovered.n_contested ? ` · ${fmtN(hovered.n_contested)} contested` : ""}{hovered.kind === "privilege" ? " · privilege review" : ""}</div>
            {hovered.rfp_text ? <p>{hovered.rfp_text.length > 520 ? `${hovered.rfp_text.slice(0, 520).replace(/\s+\S*$/, "")}…` : hovered.rfp_text}</p> : <p className="pe-rfp-note">Request text not recovered.</p>}
            {hovered.note && <p className="pe-rfp-note">{hovered.note}</p>}
          </div>
        )}
        {reqOpen && (
          <Modal eyebrow={ds.label} title="Requests for production" onClose={() => setReqOpen(false)} className="pe-req-modal">
            <div className="pe-req-list">
              {ds.topics.map((t) => {
                const on = slots.topics.includes(t.id);
                return (
                  <div key={t.id} className={`pe-req${on ? " on" : ""}`}>
                    <button className="pick-main" role="checkbox" aria-checked={on} onClick={() => toggleTopic(t.id)}>
                      <span className={`box${on ? " on" : ""}`} /><span className="lbl"><span className="nm">{topicName(t)}</span></span>
                    </button>
                    <div className="m">{t.kind === "privilege" ? "Privilege review · " : ""}{fmtN(t.n)} judged · {fmtN(t.n_pos)} responsive ({fmtShare(t.n_pos / (t.n || 1))}) · {fmtN(t.n_gray)} gray{t.n_contested ? ` · ${fmtN(t.n_contested)} contested` : ""}</div>
                    {t.rfp_text ? <p>{t.rfp_text}</p> : <p className="pe-rfp-note">Request text not recovered.</p>}
                    {t.note && <p className="pe-rfp-note">{t.note}</p>}
                  </div>
                );
              })}
            </div>
          </Modal>
        )}
      </section>

      <section>
        <h4>Arms<span className="n">standard · A · overlay</span></h4>
        <div className="pe-slots-h"><span /><span title="Reference standard">S</span><span title="Arm A, read against the standard">A</span><span title="Overlay B, optional">B</span></div>
        {arms.map((a) => (
          <div key={a.id} className={`pe-slot-row${[slots.standard, slots.a, slots.b].includes(a.id) ? " on" : ""}`}>
            <span className="pe-slot-name" title={a.note ?? a.name}><span className="pe-sw" style={{ background: a.color }} />{a.short}{a.planned && <span className="tag">planned</span>}{a.coverage != null && a.coverage < 0.98 && <span className="tag" title={`This run scored ${fmtShare(a.coverage)} of the judged documents; the rest show as unscored (gray). TAR simulations do not score the documents the simulated reviewer read.`}>{fmtShare(a.coverage)} scored</span>}</span>
            {(["standard", "a", "b"] as const).map((slot) => <button key={slot} className={`box radio${slots[slot] === a.id ? " on" : ""}`} role="radio" aria-checked={slots[slot] === a.id} onClick={() => place(slot, a.id)} title={`${a.short} as ${slot === "standard" ? "the standard" : slot === "a" ? "arm A" : "overlay B"}`} />)}
          </div>
        ))}
        <div className={`pe-slot-row${slots.a == null || slots.b == null ? " on" : ""}`}>
          <span className="pe-slot-name pe-none">none · the standard alone</span><span />
          <button className={`box radio${slots.a == null ? " on" : ""}`} role="radio" aria-checked={slots.a == null} onClick={() => place("a", null)} title="No arm A: show the standard on its own" />
          <button className={`box radio${slots.b == null ? " on" : ""}`} role="radio" aria-checked={slots.b == null} onClick={() => place("b", null)} title="No overlay" />
        </div>
      </section>

      <section>
        <h4>Options</h4>
        {ds.has_attachments ? (
          <>
            <div className="pe-opt"><span>Unit</span><Seg value={s.unit} onChange={(u) => up({ unit: u })} options={[{ id: "docs", label: "Documents", title: "Every parent email and attachment is its own unit, as the track judged them" }, { id: "families", label: "Families", title: "Message + attachments as one unit; responsive if any member is; model p = max over members. The track's primary scoring unit, one vote per message." }]} /></div>
            {s.unit === "docs" && (
              <label className="pe-check" title="The track deemed a parent email responsive when any attachment was. With this on, a model's parent score is the max over the parent and its attachments, so document-level comparisons follow the same rule the gold did. Attachments keep their own score.">
                <input type="checkbox" checked={inherit} onChange={(e) => up({ inherit: { ...s.inherit, [ds.id]: e.target.checked } })} />
                <span>Models inherit from attachments</span>
              </label>
            )}
          </>
        ) : (
          <div className="pe-opt"><span>Unit</span><span className="pe-opt-fixed">documents <span className="pe-dim">· no attachment structure in this collection</span></span></div>
        )}
        {anyModel && <div className="pe-opt"><span>Model threshold <b>{s.threshold.toFixed(2)}</b></span><input type="range" min={0.05} max={0.95} step={0.05} value={s.threshold} onChange={(e) => up({ threshold: Number(e.target.value) })} /></div>}
        {tarArms.length > 0 && (
          <div className="pe-opt">
            <span>TAR reviewer</span>
            <TarReviewerControl stacked value={s.tarReviewer} onChange={(r) => up({ tarReviewer: r })} movedHint={REVIEWER_ONLY} fixedHint="no reviewer provenance exported for this run"
              arms={tarArms.map((a) => ({ model: a.id, name: a.short, grid: a.meta && metas[a.id] ? { ...GRID_RATES, default: metas[a.id].default } : null }))} />
          </div>
        )}
      </section>
    </aside>
  );
}

// ------------------------------------------------------------------------------------------------ population

/** The score files of the arms named, and the reviewer meta file of the ones that have it (fetched once each; exploreData.ts caches the requests). */
function useScores(ds: Dataset, ids: (string | null)[]) {
  const [got, setGot] = useState<Record<string, ArmScores>>({});
  const [metas, setMetas] = useState<Record<string, TarMeta>>({});
  const want = ids.filter((id): id is string => !!id && !!ds.arms.find((a) => a.id === id));
  useEffect(() => {
    for (const id of want) {
      const a = ds.arms.find((x) => x.id === id)!;
      loadArm(ds.id, a.file).then((sc) => setGot((g) => (g[id] ? g : { ...g, [id]: sc })));
      if (a.meta) loadMeta(ds.id, a.meta).then((m) => setMetas((g) => (g[id] ? g : { ...g, [id]: m })));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ds.id, want.join("|")]);
  return { scores: got, metas };
}

function Population({ ds, slots, state: s, up }: { ds: Dataset; slots: Slots; state: State; up: (p: Partial<State>) => void }) {
  const [rows, setRows] = useState<Rows | null>(null);
  useEffect(() => { loadRows(ds.id).then(setRows); }, [ds.id]);
  const { scores: shipped, metas } = useScores(ds, [slots.standard, slots.a, slots.b]);
  const inherit = inheritOn(s, ds);
  const arms = armsOf(ds);
  const S = arms.find((a) => a.id === slots.standard) ?? arms[0], A = slots.a ? arms.find((a) => a.id === slots.a) ?? null : null, B = A && slots.b ? arms.find((a) => a.id === slots.b) ?? null : null;
  const ready = rows && [S, A, B].every((a) => !a || a.human || (shipped[a.id] && (!a.meta || metas[a.id])));
  // the scores as the TAR reviewer setting has them (exploreData.ts reviewerScores): a TAR arm's reviewer rows re-coded, every other arm as shipped
  const scores = useMemo(() => {
    if (!rows || isPublished(s.tarReviewer)) return shipped;
    const r = s.tarReviewer;
    return Object.fromEntries(Object.entries(shipped).map(([id, sc]) => [id, metas[id] ? reviewerScores(rows, sc, metas[id], r) : sc]));
  }, [rows, shipped, metas, s.tarReviewer]);
  const [sel, setSel] = useState<Sel>({ kind: "bucket", key: !A ? "agree_r" : B ? "miss.std" : "miss" });
  const [pick, setPick] = useState<Unit | null>(null);
  const [shown, setShown] = useState(PAGE);
  useEffect(() => { setPick(null); setShown(PAGE); }, [sel, slots.topics.join(), s.unit, inherit, slots.standard, slots.a, slots.b, s.threshold, s.tarReviewer]);
  const sameSel = (x: Sel, y: Sel) => JSON.stringify(x) === JSON.stringify(y);
  const toggle = (x: Sel) => setSel((prev) => (prev && x && sameSel(prev, x) ? null : x));
  // Esc clears the selection (unless a modal is open: its own Esc closes it)
  useEffect(() => { const h = (e: KeyboardEvent) => { if (e.key === "Escape" && !document.querySelector(".ex-modal")) setSel(null); }; window.addEventListener("keydown", h); return () => window.removeEventListener("keydown", h); }, []);
  const chartH = useChartHeight();

  const pop = useMemo(() => {
    if (!rows || !ready) return null;
    const topicIdx = new Set(slots.topics.map((t) => rows.topics.indexOf(t)).filter((i) => i >= 0));
    const families = s.unit === "families" && ds.has_attachments;
    const units = unitsOf(rows, topicIdx, families);
    // at document level the track's rule can be applied to the models too (parent p = max over its family); families already take the max
    const sc = (a: Arm): ArmScores | null => { const x = scores[a.id]; return x ? (!families && inherit ? inheritScores(rows, x) : x) : null; };
    const lS = labelerFor(S, rows, sc(S), s.threshold), lA = A ? labelerFor(A, rows, sc(A), s.threshold) : null, lB = B ? labelerFor(B, rows, sc(B), s.threshold) : null;
    const xs = units.map(lS), ya = lA ? units.map(lA) : xs, zb = lB ? units.map(lB) : null; // with no arm A the standard stands in for it: every unit "agrees"
    const cells: Cells = new Map();
    const keys = units.map((_, i) => { const k = cellKey(xs[i], ya[i], zb ? zb[i] : null); cells.set(k, (cells.get(k) ?? 0) + 1); return bucketOf(xs[i], ya[i], zb ? zb[i] : null); });
    const defs = bucketDefs(S.short, A?.short ?? null, B?.short ?? null);
    const counts = new Map<string, number>();
    for (const k of keys) counts.set(k, (counts.get(k) ?? 0) + 1);
    // the confidence view reads the first model among B, A, S; the stacks are the outcome of the other arms
    const modelArm = [B, A, S].find((a) => a && !a.human) ?? null;
    const scorer = modelArm ? scorerFor(modelArm, sc(modelArm)) : null;
    const others = [S, A, B].filter((a): a is Arm => !!a && a !== modelArm);
    let groups: ConfGroup[] = [], bins: number[][] = [], groupOf: ((i: number) => number) | null = null;
    if (scorer) {
      const lab = (a: Arm) => (a === S ? xs : a === A ? ya : zb!);
      if (others.length === 0) {
        groups = [{ id: "all", name: "all units", color: modelArm!.color }];
        groupOf = () => 0;
      } else if (others.length >= 2) {
        const [o1, o2] = others, l1 = lab(o1), l2 = lab(o2);
        groups = [
          { id: "agree_r", name: `${o2.short} and ${o1.short} responsive`, color: o1.color },
          { id: "contested", name: `${o2.short} and ${o1.short} disagree`, color: "var(--ink-3)", hatch: true },
          { id: "agree_nr", name: "both not responsive", color: "var(--ink-4)" },
          { id: "gray", name: "gray", color: "var(--line-2)" },
        ];
        groupOf = (i) => { const o = outcomeOf(l1[i], l2[i]); return o === "agree_r" ? 0 : o === "miss" || o === "over" ? 1 : o === "agree_nr" ? 2 : 3; };
      } else {
        const o1 = others[0], l1 = lab(o1);
        groups = [{ id: "r", name: `${o1.short} responsive`, color: o1.color }, { id: "nr", name: `${o1.short} not responsive`, color: "var(--ink-4)" }, { id: "gray", name: "gray", color: "var(--line-2)" }];
        groupOf = (i) => (l1[i] === 1 ? 0 : l1[i] === 0 ? 1 : 2);
      }
      bins = Array.from({ length: 10 }, () => groups.map(() => 0));
      units.forEach((u, i) => { const p = scorer(u); if (p == null) return; bins[Math.min(9, Math.floor(p * 10))][groupOf!(i)]++; });
    }
    const contested = units.filter((_, i) => outcomeOf(xs[i], ya[i]) === "miss" || outcomeOf(xs[i], ya[i]) === "over").length;
    const bWithS = zb ? units.filter((_, i) => { const o = outcomeOf(xs[i], ya[i]); return (o === "miss" || o === "over") && zb[i] === xs[i]; }).length : null;
    const prev = xs.filter((x) => x === 1).length / (xs.filter((x) => x >= 0).length || 1);
    return { units, xs, ya, zb, keys, counts, defs, cells, modelArm, scorer, groups, bins, contested, bWithS, prev, kAS: A ? kappa(ya, xs) : null, kBS: zb ? kappa(zb, xs) : null, kBA: zb ? kappa(zb, ya) : null };
  }, [rows, ready, slots.topics, s.unit, inherit, s.threshold, S, A, B, scores]);
  // a selection the chart no longer has a piece for (the arms changed, so the bucket catalogue did; the model left, so no bins) clears
  useEffect(() => { if (pop && sel && (sel.kind === "bucket" ? !pop.defs.some((d) => d.key === sel.key) : !pop.scorer)) setSel(null); }, [pop, sel]);

  if (!pop) return <div className="card study-card"><div className="study-empty">Loading {ds.label}…</div></div>;
  const listed = (() => {
    if (!sel) return [];
    const idx: number[] = [];
    if (sel.kind === "bucket") pop.keys.forEach((k, i) => { if (k === sel.key) idx.push(i); });
    else if (pop.scorer) pop.units.forEach((u, i) => { const p = pop.scorer!(u); if (p != null && p >= sel.lo && (p < sel.hi || (sel.hi >= 1 && p <= 1))) idx.push(i); });
    const sc = pop.scorer;
    const cmp: Record<SortKey, (i: number, j: number) => number> = {
      p_desc: (i, j) => (sc?.(pop.units[j]) ?? -1) - (sc?.(pop.units[i]) ?? -1),
      p_asc: (i, j) => (sc?.(pop.units[i]) ?? 2) - (sc?.(pop.units[j]) ?? 2),
      chars: (i, j) => (pop.units[j].chars ?? 0) - (pop.units[i].chars ?? 0),
      psel: (i, j) => (pop.units[j].psel ?? 0) - (pop.units[i].psel ?? 0),
      id: (i, j) => pop.units[i].docid.localeCompare(pop.units[j].docid),
    };
    return idx.sort(cmp[pop.scorer ? s.sort : s.sort === "p_desc" || s.sort === "p_asc" ? "chars" : s.sort]);
  })();
  const selDef = sel?.kind === "bucket" ? pop.defs.find((d) => d.key === sel.key) : null;
  const unitWord = s.unit === "families" && ds.has_attachments ? "families" : "documents";
  const views: { id: View; label: string; title?: string }[] = [{ id: "mosaic", label: "Mosaic" }, ...(A ? [{ id: "flow" as View, label: "Flow" }] : []), { id: "venn", label: "Venn" }, ...(pop.scorer ? [{ id: "confidence" as View, label: "Confidence" }] : [])];
  const view = views.some((v) => v.id === s.view) ? s.view : "mosaic";
  const placeholder = [S, A, B].some((a) => a?.planned);
  const hasPsel = pop.units.some((u) => u.psel != null);
  const selTitle = selDef ? selDef.label : sel?.kind === "bin" ? `${pop.modelArm?.short} p ∈ [${sel.lo.toFixed(1)}, ${sel.hi.toFixed(1)})` : "";
  const k2 = (k: number | null) => (k == null ? "—" : k.toFixed(2));

  return (
    <>
      <div className="card study-card pe-chart-card">
        <div className="card-t">
          <h3>Who called it responsive</h3>
          <span className="unit">{ds.label} · {slots.topics.length === 1 ? topicName(ds.topics.find((t) => t.id === slots.topics[0])!) : `${slots.topics.length} topics: ${slots.topics.map((id) => { const t = ds.topics.find((x) => x.id === id)!; return /^\d/.test(t.id) ? t.id : t.title; }).join(", ")}`}{placeholder ? " · placeholder scores" : ""}</span>
          <span className="right">
            {view !== "confidence" && <Seg value={s.scale} onChange={(v) => up({ scale: v })} options={[{ id: "linear", label: "linear" }, { id: "sqrt", label: "√" }]} />}
            <Seg value={view} onChange={(v) => up({ view: v })} options={views} />
          </span>
        </div>
        <div className="pe-sub">
          <span className="q">{view === "mosaic" ? (A ? <>Columns: how <b>{A.short}</b> came out against <b>{S.short}</b>{B && <>, each split by <b>{B.short}</b></>}.</> : <>What <b>{S.short}</b> called responsive, on its own. Choose an arm A in the controls to compare against it.</>) : view === "flow" && A ? <>Each unit travels <b>{A.short}</b> → <b>{S.short}</b>{B && <> → <b>{B.short}</b></>}.</> : view === "venn" ? <>One circle per arm, sized by its responsive calls; overlaps are the units they agree on.</> : <>Where <b>{pop.modelArm!.short}</b>'s confidence puts the units the other arms agreed or disagreed on.</>}</span>
          {sel ? (
            <span className="pe-sel" title="The selected piece of the chart; its documents are listed below">
              <b>{selTitle}</b><span className="n">{fmtN(listed.length)} · {fmtShare(pop.units.length ? listed.length / pop.units.length : 0)}</span>
              <button className="x" onClick={() => setSel(null)} title="Clear the selection (Esc)" aria-label="Clear selection">×</button>
            </span>
          ) : <span className="pe-sel-none">click a piece of the chart to list its {unitWord}</span>}
        </div>
        <div className="pe-sub">
          <span className="st">
            <span><b>{fmtN(pop.units.length)}</b> {unitWord}</span>
            <span><b>{fmtShare(pop.prev)}</b> responsive per {S.short}</span>
            {A && <span><b>{fmtN(pop.contested)}</b> {A.short} ≠ {S.short}</span>}
            {A && <span title={`Cohen's κ, ${A.short} against ${S.short}, over the units both judged`}>κ {A.short} vs {S.short} <b>{k2(pop.kAS)}</b></span>}
            {B && <span title={`Cohen's κ, ${B.short} against ${S.short}`}>κ {B.short} vs {S.short} <b>{k2(pop.kBS)}</b></span>}
            {A && B && <span title={`Cohen's κ, ${B.short} against ${A.short}`}>κ {B.short} vs {A.short} <b>{k2(pop.kBA)}</b></span>}
            {B && pop.bWithS != null && <span><b>{pop.contested ? fmtShare(pop.bWithS / pop.contested) : "—"}</b> {B.short} with {S.short} where they disagree</span>}
          </span>
        </div>
        {view === "mosaic" && <Mosaic cells={pop.cells} S={S} A={A} B={B} defs={pop.defs} scale={s.scale} sel={sel} onSel={toggle} height={chartH} />}
        {view === "flow" && A && <Flow cells={pop.cells} S={S} A={A} B={B} defs={pop.defs} scale={s.scale} sel={sel} onSel={toggle} height={chartH} />}
        {view === "venn" && <Venn cells={pop.cells} S={S} A={A} B={B} defs={pop.defs} scale={s.scale} sel={sel} onSel={toggle} height={chartH} />}
        {view === "confidence" && pop.modelArm && <Confidence model={pop.modelArm} groups={pop.groups} bins={pop.bins} threshold={s.threshold} sel={sel} onSel={toggle} height={chartH} />}
      </div>

      {sel && (
        <div className="pe-split">
          <div className="card pe-list-card">
            <div className="card-t">
              <h3>{selTitle}</h3>
              <span className="unit">{fmtN(listed.length)} {unitWord}</span>
              <span className="right">
                <select className="pe-sort" value={s.sort} onChange={(e) => up({ sort: e.target.value as SortKey })}>
                  {pop.scorer && <option value="p_desc">{pop.modelArm!.short} p, high first</option>}
                  {pop.scorer && <option value="p_asc">{pop.modelArm!.short} p, low first</option>}
                  <option value="chars">longest first</option>
                  {hasPsel && <option value="psel">sampling probability</option>}
                  <option value="id">id</option>
                </select>
              </span>
            </div>
            {listed.length === 0 ? <div className="study-empty">No {unitWord} here.</div> : (
              <>
                <div className="pe-list-wrap">
                  <table className="pe-list">
                    <thead><tr><th>{s.unit === "families" ? "Family" : "Document"}</th>{slots.topics.length > 1 && <th>Topic</th>}<th title={S.name}>{S.short}</th>{A && <th title={A.name}>{A.short}</th>}{B && <th title={B.name}>{B.short}</th>}{pop.scorer && <th>{pop.modelArm!.short} p</th>}<th>Chars</th>{hasPsel && <th title="Stratified-sample inclusion probability">p(sel)</th>}</tr></thead>
                    <tbody>
                      {listed.slice(0, shown).map((i) => {
                        const u = pop.units[i];
                        const p = pop.scorer?.(u);
                        return (
                          <tr key={u.docid + u.topic} className={`${pick === u ? "on" : ""}${pop.xs[i] !== pop.ya[i] && pop.xs[i] >= 0 && pop.ya[i] >= 0 ? " contested" : ""}`} onClick={() => setPick(u)}>
                            <td className="id"><span className={`pe-kind ${u.att ? "att" : "msg"}`} title={u.att ? "attachment" : "message"} />{shortId(u.docid)}{u.n > 1 && <span className="pe-fam-n">+{u.n - 1}</span>}</td>
                            {slots.topics.length > 1 && <td>{rows!.topics[u.topic]}</td>}
                            <td><Lab l={pop.xs[i]} /></td>{A && <td><Lab l={pop.ya[i]} /></td>}{B && <td><Lab l={pop.zb![i]} /></td>}
                            {pop.scorer && <td className="num">{p == null ? "—" : p.toFixed(2)}</td>}
                            <td className="num">{u.chars == null ? "—" : fmtN(u.chars)}</td>
                            {hasPsel && <td className="num">{u.psel == null ? "—" : u.psel.toFixed(3)}</td>}
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                {listed.length > shown && <button className="pe-more" onClick={() => setShown(shown + PAGE)}>Show {fmtN(Math.min(PAGE, listed.length - shown))} more of {fmtN(listed.length - shown)}</button>}
              </>
            )}
          </div>
          <Viewer ds={ds} rows={rows!} unit={pick ?? (listed.length ? pop.units[listed[0]] : null)} arms={[S, A, B].filter((a): a is Arm => !!a)} scores={scores} threshold={s.threshold} />
        </div>
      )}
    </>
  );
}

const shortId = (id: string) => (id.length > 26 ? `${id.slice(0, 12)}…${id.slice(-8)}` : id);
const Lab = ({ l }: { l: Lab }) => <span className={`pe-lab l${l === 1 ? "r" : l === 0 ? "nr" : "g"}`} title={LAB_NAME[l]}>{LAB_SHORT[l]}</span>;

/** The chart's height: most of the viewport (70%), never under 420px; follows window resizes. */
function useChartHeight() {
  const calc = () => Math.max(420, Math.round(window.innerHeight * 0.7));
  const [h, setH] = useState(calc);
  useEffect(() => { const f = () => setH(calc()); window.addEventListener("resize", f); return () => window.removeEventListener("resize", f); }, []);
  return h;
}

// ------------------------------------------------------------------------------------------------ viewer

function Viewer({ ds, rows, unit, arms, scores, threshold }: { ds: Dataset; rows: Rows; unit: Unit | null; arms: Arm[]; scores: Record<string, ArmScores>; threshold: number }) {
  const [doc, setDoc] = useState<DocText | null>(null);
  const [state, setState] = useState<"idle" | "loading" | "offline" | "missing">("idle");
  // in family mode the unit is the message; show the message itself (its own row when judged, else the first member)
  const ri = unit ? (unit.ids.find((i) => !rows.att[i]) ?? unit.ids[0]) : null;
  const docid = ri != null ? rows.docid[ri] : null;
  useEffect(() => {
    if (!docid || !ds.text) { setDoc(null); return; }
    let live = true;
    setState("loading");
    fetchText(ds.id, docid).then((d) => { if (!live) return; setDoc(d); setState("idle"); }).catch((e: Error) => { if (!live) return; setDoc(null); setState(/404/.test(e.message) ? "missing" : "offline"); });
    return () => { live = false; };
  }, [ds.id, ds.text, docid]);
  if (!unit || ri == null) return <div className="card pe-viewer"><div className="study-empty">Pick a document.</div></div>;
  // the rest of the family, from the rows we know of (same topic)
  const kin: number[] = [];
  for (let i = 0; i < rows.n; i++) if (i !== ri && rows.family[i] === rows.family[ri] && rows.topic[i] === unit.topic) kin.push(i);
  const isAtt = !!rows.att[ri];
  const atts = kin.filter((i) => rows.att[i]).length;
  const topic = ds.topics[unit.topic];
  const labelOf = (a: Arm, i: number | undefined): { lab: Lab; p: number | null } => {
    if (i == null) return { lab: -1, p: null };
    if (a.human) return { lab: rows.humans[a.id][i], p: null };
    const p = scores[a.id]?.p[i] ?? null;
    return { lab: p == null ? -1 : p >= threshold ? 1 : 0, p };
  };
  return (
    <div className="card pe-viewer">
      <div className="card-t">
        <h3>{isAtt ? "Attachment" : "Message"} <span className="pe-id">{docid}</span></h3>
        <span className="unit">{topic.id} · {topic.title}</span>
      </div>
      {(isAtt || atts > 0) && (
        <p className="pe-kin">{isAtt ? <>Attachment {docid!.split(".").pop()} of message <code>{unit.family}</code>{kin.length ? ` · ${kin.length} other ${kin.length === 1 ? "part" : "parts"} judged for this topic` : ""}.</> : <>This message has {atts} judged {atts === 1 ? "attachment" : "attachments"}; they are listed as their own documents.</>}</p>
      )}
      <div className="pe-fields">
        {arms.map((a) => { const { lab, p } = labelOf(a, ri); return <div key={a.id} className="pe-field"><div className="k"><span className="pe-sw" style={{ background: a.color }} />{a.short}{a.planned ? " · placeholder" : ""}</div><div className="v"><Lab l={lab} /> {LAB_NAME[lab]}{p != null && <span className="p"> · p {p.toFixed(3)}</span>}</div></div>; })}
        {ri != null && rows.psel[ri] != null && <div className="pe-field"><div className="k">sampling probability</div><div className="v">{rows.psel[ri]!.toFixed(4)}</div></div>}
        {ri != null && rows.chars[ri] != null && <div className="pe-field"><div className="k">characters</div><div className="v">{fmtN(rows.chars[ri]!)}</div></div>}

      </div>
      <div className="pe-text">
        {!ds.text ? <div className="pe-note">The text for this collection is not on this machine. {ds.text_note ?? "Only the judgments are here."}</div>
          : state === "offline" ? <div className="pe-note">Text is read from <code>data/</code> on this machine. Start <code>bench serve</code> ({TEXT_API}) to read documents here.</div>
          : state === "loading" && !doc ? <div className="pe-note">Loading…</div>
          : doc ? <pre>{doc.text.trim() || "(no extractable text)"}</pre> : <div className="pe-note">{state === "missing" ? "Not found in the local corpus." : "Loading…"}</div>}
      </div>
    </div>
  );
}
