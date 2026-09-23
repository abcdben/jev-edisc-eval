import { useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { CORPORA, DEFAULT_CORPUS, PRIMARY, PRIMARY_BY_KEY, fmtInt, fmtPct, modelKind } from "./data";
import { Control, Hint, Seg } from "./components/ui";
import { Picker, type PickGroup } from "./components/Picker";
import { Logo } from "./logos";
import { IssueSpark, PRCurveChart, type GhostCurve, type PRPoint } from "./components/CutoffCharts";
import {
  DEFAULT_CUTOFF_IDX, GRID_N, buildIssueStats, decodeCutoffs, gridValue, issueCountsLabel, issueCurve, issueHistogram, issueMetrics, metrics,
  optimizePerIssueF1, optimizePooledF1, pooledCounts, pooledCountsLabel, splitHalfCheck, splitHalfRepeat, sweepCurve, targetRecall,
  type CorpusData, type CutoffsFile, type Gray, type IssueStats, type Level, type Metrics, type ModelData, type SplitResult,
} from "./cutoffEngine";

/**
 * Cutoffs (cutoffs.html → cutoffs.tsx → this page; unlinked from the site). Every model in the benchmark returns a probability per
 * (document, issue); the benchmark calls a decision responsive at p ≥ 0.5. This page moves that cutoff per issue and shows what happens to
 * recall, precision and F1, per issue and pooled, against the published 0.5 figures. Data: public/cutoffs.json, written by
 * site/tools/build_cutoffs.py from results/<corpus>/multi and fetched when the page opens; the arithmetic is in cutoffEngine.ts.
 */

type Sort = "prev" | "gain";
type Spark = "hist" | "pr";
type Tune = "issue" | "pooled";
type Repeat = { meanTestGain: number; meanTrainGain: number; positiveShare: number };
/** One row of the split-half check run for every shown model: the single seeded split's held-out figures and the 20-split mean. */
type SplitAllRow = { key: string; split: SplitResult; repeat: Repeat };
type SplitAll = { rows: SplitAllRow[]; level: Level; gray: Gray; tune: Tune; seed: number; pending: number };
type CorpusState = {
  model: string; compare: string[]; cutoffs: number[]; target: number; targetMiss: boolean[] | null; pooledDiff: number | null;
  seed: number; split: SplitResult | null; repeat: Repeat | null; splitAll: SplitAll | null;
};
const freshState = (nIssues: number): CorpusState => ({
  model: "jev@base", compare: [], cutoffs: new Array(nIssues).fill(DEFAULT_CUTOFF_IDX), target: 90, targetMiss: null, pooledDiff: null,
  seed: 1, split: null, repeat: null, splitAll: null,
});
const KIND_LABEL: Record<string, string> = { system1: "Decision models", system1_ft: "Supervised", llm: "LLM", local_llm: "Local LLM", baseline: "Floor" };
const KIND_ORDER = ["system1", "system1_ft", "baseline", "llm", "local_llm"];
const kindOf = (key: string): string => PRIMARY_BY_KEY[key]?.kind ?? modelKind(key) ?? (key.startsWith("jev@") ? "system1" : "llm");

const pts = (v: number | null | undefined, d = 1) => (v == null ? "—" : `${(v * 100).toFixed(d)}`);
const EMPTY_METRICS: Metrics = metrics({ tp: 0, fp: 0, fn: 0, tn: 0 });
/** A change in percentage points with its direction; `good` says which direction is the improvement (null: neither). */
function Delta({ cur, ref, good = "up", d = 1 }: { cur: number | null | undefined; ref: number | null | undefined; good?: "up" | "down" | null; d?: number }) {
  if (cur == null || ref == null) return <span className="cut-delta none">—</span>;
  const v = (cur - ref) * 100;
  if (Math.abs(v) < 0.05) return <span className="cut-delta none">—</span>;
  const up = v > 0, cls = good == null ? "neutral" : (up === (good === "up") ? "good" : "bad");
  return <span className={`cut-delta ${cls}`}>{up ? "▲" : "▼"} {Math.abs(v).toFixed(d)}</span>;
}

/** The per-issue slider: a native range for input and keyboard, drawn as a track whose flagged side (p ≥ cutoff) is tinted in the model's colour, so a programmatic move can transition. */
function CutoffSlider({ idx, onChange, color, label }: { idx: number; onChange: (i: number) => void; color: string; label: string }) {
  const pct = (idx / GRID_N) * 100;
  return (
    <span className="cut-slider" style={{ "--v": `${pct}%`, "--c": color } as React.CSSProperties}>
      <span className="track"><span className="fill" /><span className="thumb" /></span>
      <input type="range" min={0} max={GRID_N} step={1} value={idx} onChange={(e) => onChange(Number(e.target.value))} aria-label={`${label} cutoff`} />
    </span>
  );
}

function useCopy() {
  const [status, setStatus] = useState<{ msg: string; err?: boolean } | null>(null);
  const [fallback, setFallback] = useState<string | null>(null);
  const timer = useRef(0);
  const flash = (msg: string, err = false) => { setStatus({ msg, err }); window.clearTimeout(timer.current); timer.current = window.setTimeout(() => setStatus(null), err ? 5000 : 1500); };
  const copy = async (text: string) => {
    try { await navigator.clipboard.writeText(text); flash("Copied"); setFallback(null); }
    catch { flash("Clipboard blocked; text shown below", true); setFallback(text); }
  };
  return { status, fallback, copy, clearFallback: () => setFallback(null) };
}

export default function CutoffsPage() {
  const [theme, setTheme] = useState<"dark" | "light">(() => (localStorage.getItem("theme") as "dark" | "light") || "light");
  useEffect(() => { document.documentElement.dataset.theme = theme; localStorage.setItem("theme", theme); }, [theme]);

  const [data, setData] = useState<CutoffsFile | null>(null);
  const [loadErr, setLoadErr] = useState<string | null>(null);
  useEffect(() => {
    // fetched lazily, relative to the page (base is "./"), so the main bundle carries none of it
    fetch(`${import.meta.env.BASE_URL}cutoffs.json`).then((r) => { if (!r.ok) throw new Error(`${r.status} ${r.statusText}`); return r.json(); })
      .then((raw) => setData(decodeCutoffs(raw))).catch((e: unknown) => setLoadErr(e instanceof Error ? e.message : String(e)));
  }, []);

  const [corpus, setCorpus] = useState(DEFAULT_CORPUS);
  const [gray, setGray] = useState<Gray>("all");
  const [level, setLevel] = useState<Level>("doc");
  const [sort, setSort] = useState<Sort>("prev");
  const [spark, setSpark] = useState<Spark>("hist");
  const [ghosts, setGhosts] = useState(false);
  const [zoom, setZoom] = useState(true);
  const [tune, setTune] = useState<Tune>("issue");
  const [showOwn, setShowOwn] = useState(false);
  const [states, setStates] = useState<Record<string, CorpusState>>({});
  const [anim, setAnim] = useState(false);
  const animTimer = useRef(0);
  const animate = () => { setAnim(true); window.clearTimeout(animTimer.current); animTimer.current = window.setTimeout(() => setAnim(false), 600); };
  const clip = useCopy();
  const hashRead = useRef(false);

  const c: CorpusData | null = data?.corpora[corpus] ?? null;
  const nq = c?.issues.length ?? 0;
  const st: CorpusState = states[corpus] ?? freshState(nq);
  const patch = (p: Partial<CorpusState>) => setStates((s) => ({ ...s, [corpus]: { ...(s[corpus] ?? freshState(nq)), ...p } }));
  const setCutoffs = (cutoffs: number[], extra: Partial<CorpusState> = {}) => { patch({ cutoffs, targetMiss: null, pooledDiff: null, ...extra }); };

  // State in the URL hash, so a configuration can be shared: read once when the data is in, written on every change after that.
  useEffect(() => {
    if (!data || hashRead.current) return;
    hashRead.current = true;
    const h = new URLSearchParams(location.hash.replace(/^#/, ""));
    const s = h.get("s"); if (s && data.corpora[s]) setCorpus(s);
    const g = h.get("g"); if (g === "all" || g === "nogray") setGray(g);
    const l = h.get("l"); if (l === "doc" || l === "decision") setLevel(l);
    if (h.get("own") === "1") setShowOwn(true);
    const next: Record<string, CorpusState> = {};
    for (const [ck, cd] of Object.entries(data.corpora)) {
      const cs = freshState(cd.issues.length);
      const m = h.get(`m.${ck}`); if (m && cd.models[m]) cs.model = m;
      // `cmp.<corpus>` is the comparison set; `x.<corpus>` was the single comparison model of earlier links
      const cmp = (h.get(`cmp.${ck}`) ?? h.get(`x.${ck}`) ?? "").split(",").filter((k) => k && cd.models[k] && k !== cs.model);
      cs.compare = Array.from(new Set(cmp));
      const cut = h.get(`cut.${ck}`)?.split(",").map(Number);
      if (cut && cut.length === cd.issues.length && cut.every((v) => Number.isInteger(v) && v >= 0 && v <= GRID_N)) cs.cutoffs = cut;
      next[ck] = cs;
    }
    setStates(next);
  }, [data]);
  // The write is debounced: a slider drag fires hundreds of changes a second, and Safari throws a SecurityError past 100 replaceState calls
  // in 30 s (Chrome silently drops them). It is also wrapped, so a refused write can never take the page down; the hash is a convenience.
  const pendingHash = useRef<string | null>(null);
  const hashTimer = useRef(0);
  const flushHash = () => {
    window.clearTimeout(hashTimer.current);
    const h = pendingHash.current; pendingHash.current = null;
    if (h == null || location.hash === h) return;
    try { history.replaceState(null, "", h); } catch { /* throttled by the browser; the next flush will carry the latest state */ }
  };
  useEffect(() => {
    if (!data || !hashRead.current) return;
    const h = new URLSearchParams();
    h.set("s", corpus); h.set("g", gray); h.set("l", level);
    if (showOwn) h.set("own", "1");
    for (const [ck, cd] of Object.entries(data.corpora)) {
      const cs = states[ck]; if (!cs) continue;
      if (cs.model !== "jev@base") h.set(`m.${ck}`, cs.model);
      if (cs.compare.length) h.set(`cmp.${ck}`, cs.compare.join(","));
      if (cs.cutoffs.some((v) => v !== DEFAULT_CUTOFF_IDX) && cs.cutoffs.length === cd.issues.length) h.set(`cut.${ck}`, cs.cutoffs.join(","));
    }
    pendingHash.current = `#${h.toString()}`;
    window.clearTimeout(hashTimer.current);
    hashTimer.current = window.setTimeout(flushHash, 400);
  }, [data, corpus, gray, level, states, showOwn]);
  useEffect(() => {
    // settle the address as soon as the pointer lifts or the page is left, so a copied link is never stale
    const flush = () => flushHash();
    window.addEventListener("pointerup", flush); window.addEventListener("pagehide", flush); window.addEventListener("blur", flush);
    return () => { window.removeEventListener("pointerup", flush); window.removeEventListener("pagehide", flush); window.removeEventListener("blur", flush); window.clearTimeout(hashTimer.current); };
  }, []);

  // ---- the model and its precomputed structures ----
  const roster = useMemo(() => (c ? PRIMARY.filter((p) => c.models[p.key]) : []), [c]);
  const modelKey = c && c.models[st.model] ? st.model : roster[0]?.key;
  const m: ModelData | null = c && modelKey ? c.models[modelKey] : null;
  const meta = modelKey ? PRIMARY_BY_KEY[modelKey] : null;
  const color = meta?.color ?? "var(--ink)";
  const stats: IssueStats[] = useMemo(() => (c && m ? c.issues.map((_, q) => buildIssueStats(c, m, q)) : []), [c, m]);
  const cutoffs = useMemo(() => (st.cutoffs.length === nq ? st.cutoffs : new Array(nq).fill(DEFAULT_CUTOFF_IDX) as number[]), [st.cutoffs, nq]);
  const cutVals = useMemo(() => cutoffs.map(gridValue), [cutoffs]);

  const cur: Metrics | null = useMemo(() => (c && m ? metrics(pooledCounts(level, c, m, stats, cutVals, gray)) : null), [c, m, stats, cutVals, gray, level]);
  const def: Metrics | null = useMemo(() => (c && m ? metrics(pooledCountsLabel(level, c, m, gray)) : null), [c, m, gray, level]);
  const curve = useMemo(() => (c && m ? sweepCurve(level, c, m, stats, gray) : []), [c, m, stats, gray, level]);
  const perIssue = useMemo(() => {
    if (!c || !m) return [];
    return c.issues.map((iss, q) => {
      const s = stats[q];
      return {
        iss, q, s,
        def: metrics(issueCountsLabel(c, m, q, gray)),
        hist: issueHistogram(c, m, q, gray),
        curve: issueCurve(s, gray),
        n: gray === "all" ? s.n : s.nNG, nPos: gray === "all" ? s.nPos : s.nPosNG,
      };
    });
  }, [c, m, stats, gray]);
  const rows = useMemo(() => perIssue.map((r) => ({ ...r, cur: issueMetrics(r.s, cutVals[r.q], gray) })), [perIssue, cutVals, gray]);
  const sorted = useMemo(() => {
    const out = rows.slice();
    if (sort === "prev") out.sort((a, b) => b.nPos / Math.max(1, b.n) - a.nPos / Math.max(1, a.n));
    else out.sort((a, b) => ((b.cur.f1 ?? 0) - (b.def.f1 ?? 0)) - ((a.cur.f1 ?? 0) - (a.def.f1 ?? 0)));
    return out;
  }, [rows, sort]);

  // ---- comparison models ----
  // Any number from the roster. Each one's sorted stats, shared-cutoff sweep and published default depend only on (corpus, model, gold, level),
  // never on the sliders, and are kept in a cache so switching a model off and on again costs nothing.
  const cmpKeys = useMemo(() => (c ? st.compare.filter((k) => c.models[k] && k !== modelKey) : []), [c, st.compare, modelKey]);
  const setCompare = (keys: string[]) => patch({ compare: keys });
  const cmpCache = useRef(new Map<string, { stats: IssueStats[]; curve: Metrics[]; def: Metrics; own: number[]; ownM: Metrics; issueCurves: Metrics[][] }>());
  const cmpData = useMemo(() => {
    if (!c) return [];
    return cmpKeys.map((key) => {
      const id = `${corpus}|${level}|${gray}|${key}`;
      let e = cmpCache.current.get(id);
      if (!e) {
        const cm = c.models[key];
        const stats = c.issues.map((_, q) => buildIssueStats(c, cm, q));
        const own = optimizePerIssueF1(stats, gray);
        e = {
          stats, curve: sweepCurve(level, c, cm, stats, gray), def: metrics(pooledCountsLabel(level, c, cm, gray)),
          own, ownM: metrics(pooledCounts(level, c, cm, stats, own.map(gridValue), gray)), issueCurves: stats.map((s) => issueCurve(s, gray)),
        };
        cmpCache.current.set(id, e);
      }
      const p = PRIMARY_BY_KEY[key];
      return { key, name: p.short, color: p.color, m: c.models[key], ...e };
    });
  }, [c, corpus, cmpKeys, gray, level]);
  // the primary's own per-issue optimum (the same figure the "best F1 per issue" button sets)
  const ownPrimary = useMemo(() => (c && m ? optimizePerIssueF1(stats, gray) : []), [c, m, stats, gray]);
  const ownPrimaryM = useMemo(() => (c && m && ownPrimary.length ? metrics(pooledCounts(level, c, m, stats, ownPrimary.map(gridValue), gray)) : null), [c, m, stats, ownPrimary, gray, level]);

  // Everything that follows the sliders for the comparison models runs a beat behind (useDeferredValue): the primary's tables update on every
  // tick, the chart and comparison figures may skip intermediate frames of a fast drag.
  const dCutVals = useDeferredValue(cutVals);
  const chartCur = useDeferredValue(cur ?? EMPTY_METRICS);
  const cmpCur = useMemo(() => (c ? cmpData.map((g) => metrics(pooledCounts(level, c, g.m, g.stats, dCutVals, gray))) : []), [c, cmpData, dCutVals, gray, level]);
  const pt = (id: string, name: string, color: string, x: Metrics | null): PRPoint => ({ id, name, color, recall: x?.recall ?? null, precision: x?.precision ?? null, f1: x?.f1 ?? null });
  const ghostCurves: GhostCurve[] = useMemo(() => cmpData.map((g, i) => ({
    id: g.key, name: g.name, color: g.color, curve: g.curve,
    def: pt(g.key, g.name, g.color, g.def), cur: pt(g.key, g.name, g.color, cmpCur[i] ?? null), own: showOwn ? pt(g.key, g.name, g.color, g.ownM) : null,
  })), [cmpData, cmpCur, showOwn]);
  // the comparison models' per-issue points at the primary's cutoffs, for the PR sparklines
  const cmpIssuePts = useMemo(() => cmpData.map((g) => g.stats.map((s, q) => { const x = issueMetrics(s, dCutVals[q], gray); return { id: g.key, name: g.name, color: g.color, recall: x.recall, precision: x.precision, f1: x.f1 }; })), [cmpData, dCutVals, gray]);
  // the comparison table: primary and every comparison model at 0.5, at the primary's cutoffs and (when shown) at each one's own optimum, by current F1
  const compareRows = useMemo(() => {
    if (!c || !meta || !cur || !def) return [];
    const rows = [
      { key: modelKey!, name: meta.short, color, me: true, def, cur: chartCur, own: ownPrimaryM, nDocs: m!.nDocs },
      ...cmpData.map((g, i) => ({ key: g.key, name: g.name, color: g.color, me: false, def: g.def, cur: cmpCur[i] ?? g.def, own: g.ownM, nDocs: g.m.nDocs })),
    ];
    return rows.sort((a, b) => (b.cur.f1 ?? -1) - (a.cur.f1 ?? -1));
  }, [c, meta, cur, def, modelKey, color, chartCur, ownPrimaryM, m, cmpData, cmpCur]);
  const rosterPts: PRPoint[] = useMemo(() => {
    if (!c || !ghosts) return [];
    return roster.filter((p) => p.key !== modelKey && !cmpKeys.includes(p.key)).map((p) => { const x = metrics(pooledCountsLabel(level, c, c.models[p.key], gray)); return { id: p.key, name: p.short, color: p.color, recall: x.recall, precision: x.precision, f1: x.f1 }; });
  }, [c, ghosts, roster, modelKey, cmpKeys, gray, level]);
  const pickGroups: PickGroup[] = useMemo(() => KIND_ORDER.map((k) => ({
    id: k, label: KIND_LABEL[k] ?? k,
    items: roster.filter((p) => p.key !== modelKey && kindOf(p.key) === k).map((p) => ({ id: p.key, label: p.short, title: p.note, mark: <span style={{ color: p.color }}><Logo model={p.key} /></span>, accent: k === "system1" || k === "system1_ft" ? p.color : undefined })),
  })).filter((g) => g.items.length), [roster, modelKey]);

  // ---- actions ----
  const shared = cutoffs.every((v) => v === cutoffs[0]) ? cutoffs[0] : null;
  const setShared = (i: number) => setCutoffs(new Array(nq).fill(i));
  const reset = () => { animate(); setCutoffs(new Array(nq).fill(DEFAULT_CUTOFF_IDX)); };
  const optIssue = () => { animate(); setCutoffs(optimizePerIssueF1(stats, gray)); };
  const optPooled = () => {
    if (!c || !m) return;
    animate();
    const per = optimizePerIssueF1(stats, gray), pooled = optimizePooledF1(level, c, m, stats, gray, per);
    setCutoffs(pooled, { pooledDiff: pooled.filter((v, q) => v !== per[q]).length });
  };
  const applyTarget = () => {
    animate();
    const t = targetRecall(stats, gray, st.target / 100);
    setCutoffs(t.map((x) => x.idx), { targetMiss: t.map((x) => !x.reached) });
  };
  const runSplit = (seed: number) => {
    if (!c || !m) return;
    const split = splitHalfCheck(level, c, m, gray, seed, tune);
    const repeat = splitHalfRepeat(level, c, m, gray, tune, 20, seed * 1000 + 17);
    patch({ seed, split, repeat });
  };
  const applySplitCutoffs = () => { if (st.split) { animate(); setCutoffs(st.split.cutoffs); } };
  /** "What if everyone tuned": the primary's sliders go to its own per-issue optimum and every model's own-optimum figures are shown. */
  const optAll = () => { animate(); setShowOwn(true); setCutoffs(ownPrimary); };
  /**
   * The split-half check for the primary and every comparison model, one model per macrotask so the table fills in as it goes and the page
   * stays responsive; the result records the level, gold and tuning it was run with, so a later change shows as stale rather than silently wrong.
   */
  const splitAllRun = useRef(0);
  const runSplitAll = (seed: number) => {
    if (!c || !m || !modelKey) return;
    const keys = [modelKey, ...cmpKeys], run = ++splitAllRun.current, cc = c, cp = corpus;
    const params = { level, gray, tune, seed };
    patch({ splitAll: { rows: [], ...params, pending: keys.length } });
    const step = (i: number) => {
      if (run !== splitAllRun.current || i >= keys.length) return;
      const key = keys[i], cm = cc.models[key];
      const split = splitHalfCheck(params.level, cc, cm, params.gray, seed, params.tune);
      const repeat = splitHalfRepeat(params.level, cc, cm, params.gray, params.tune, 20, seed * 1000 + 17);
      setStates((s) => {
        const prev = s[cp]?.splitAll; if (!prev) return s;
        return { ...s, [cp]: { ...s[cp], splitAll: { ...prev, rows: [...prev.rows, { key, split, repeat }], pending: keys.length - i - 1 } } };
      });
      window.setTimeout(() => step(i + 1), 0);
    };
    window.setTimeout(() => step(0), 0);
  };
  const splitAllStale = st.splitAll && (st.splitAll.level !== level || st.splitAll.gray !== gray || st.splitAll.tune !== tune);
  const splitAllRows = useMemo(() => (st.splitAll ? st.splitAll.rows.slice().sort((a, b) => b.repeat.meanTestGain - a.repeat.meanTestGain) : []), [st.splitAll]);

  const levelWord = level === "doc" ? "documents" : "decisions";
  const levelNote = level === "doc" ? "Document level: a document is responsive if any issue is, pooled over the documents the model scored." : "Decision level: every (document, issue) judgment pooled.";
  const jsonText = () => JSON.stringify(Object.fromEntries((c?.issues ?? []).map((iss, q) => [iss.id, gridValue(cutoffs[q])])), null, 2);
  const summaryText = () => {
    if (!c || !cur || !def || !meta) return "";
    const L: string[] = [];
    L.push(`# Cutoffs · ${c.label} · ${meta.short} (${modelKey}) · ${gray === "all" ? "all gold" : "gray excluded"} · ${level} level`, "");
    L.push(`| Pooled (${levelWord}) | Benchmark 0.5 | Current | Δ pts |`, "|---|---:|---:|---:|");
    const row = (k: string, a: number | null, b: number | null) => L.push(`| ${k} | ${pts(a)} | ${pts(b)} | ${a == null || b == null ? "—" : ((b - a) * 100).toFixed(1)} |`);
    row("Recall", def.recall, cur.recall); row("Precision", def.precision, cur.precision); row("F1", def.f1, cur.f1); row("Elusion", def.elusion, cur.elusion); row("Review share", def.reviewShare, cur.reviewShare);
    if (compareRows.length > 1) {
      const d = (a: number | null, b: number | null) => (a == null || b == null ? "—" : ((b - a) * 100).toFixed(1));
      L.push("", `## Models compared (${levelWord})`, "");
      L.push(`| Model | R @0.5 | P @0.5 | F1 @0.5 | R at these cutoffs | P | F1 | Review share | Δ F1 pts${showOwn ? " | R at own optimum | P | F1 | Δ F1 pts" : ""} |`, `|---|---:|---:|---:|---:|---:|---:|---:|---:|${showOwn ? "---:|---:|---:|---:|" : ""}`);
      for (const r of compareRows) L.push(`| ${r.name}${r.me ? " (primary)" : ""} | ${pts(r.def.recall)} | ${pts(r.def.precision)} | ${pts(r.def.f1)} | ${pts(r.cur.recall)} | ${pts(r.cur.precision)} | ${pts(r.cur.f1)} | ${pts(r.cur.reviewShare)} | ${d(r.def.f1, r.cur.f1)}${showOwn ? ` | ${pts(r.own?.recall)} | ${pts(r.own?.precision)} | ${pts(r.own?.f1)} | ${d(r.def.f1, r.own?.f1 ?? null)}` : ""} |`);
    }
    L.push("", "| Issue | Cutoff | Flagged | Recall | Precision | F1 | Δ F1 pts |", "|---|---:|---:|---:|---:|---:|---:|");
    for (const r of sorted) L.push(`| ${r.iss.short} | ${gridValue(cutoffs[r.q]).toFixed(3)} | ${fmtInt(r.cur.flagged)} (${fmtPct(r.cur.reviewShare)}) | ${pts(r.cur.recall)} | ${pts(r.cur.precision)} | ${pts(r.cur.f1)} | ${r.cur.f1 == null || r.def.f1 == null ? "—" : ((r.cur.f1 - r.def.f1) * 100).toFixed(1)} |`);
    L.push("", "Exploratory: cutoffs tuned on the evaluation set are in-sample; the published benchmark uses 0.5 with no tuning.");
    return L.join("\n");
  };

  const optimizeHint = (
    <Hint title="Optimize" items={[
      { k: "Per-issue F1", v: "For each issue alone, the cutoff on the 0.005 grid with the highest F1 for that issue; ties go to the value nearest 0.5." },
      { k: "Pooled F1", v: `Coordinate ascent on the pooled ${level === "doc" ? "document" : "decision"}-level F1, starting from the per-issue optimum: one issue at a time, the others fixed, until a pass changes nothing.` },
      { k: "In-sample", v: "Both choose cutoffs on the same documents they are scored on, so the gain is optimistic. The split-half check below tunes on half the documents and scores the other half." },
      { k: "Every model", v: "Only this model's cutoffs have sliders. 'Optimize all shown models' sets them to its per-issue optimum and shows every compared model at its own per-issue optimum too (the Models compared table and the square marks on the chart)." },
    ]} />
  );

  return (
    <div className="page cutoffs">
      <header className="masthead">
        <h1 className="title"><em>Cutoffs ·</em> Jev vs Frontier LLMs</h1>
        <span className="theme"><Seg value={theme} onChange={setTheme} options={[{ id: "dark", label: "Dark" }, { id: "light", label: "Light" }]} /></span>
      </header>
      <p className="lede cut-lede">
        Every model returns a probability that a document is responsive to each issue; the benchmark calls it responsive at 0.5. A <b>cutoff</b> is that line:
        at or above it a decision is responsive, below it not. Move it per issue and watch recall, precision and F1 move against the published figures.
        The published benchmark uses 0.5 everywhere with no tuning; this page is exploratory.
      </p>

      <div className="controls">
        <Control label="Study">
          <Seg value={corpus} onChange={setCorpus} options={CORPORA.map((x) => ({ id: x.id, label: x.label }))} />
        </Control>
        <Control label="Model">
          <span className="select">
            <select value={modelKey ?? ""} onChange={(e) => patch({ model: e.target.value })} disabled={!c}>
              {roster.map((p) => <option key={p.key} value={p.key}>{p.short}</option>)}
            </select>
          </span>
        </Control>
        <Control label="Compare">
          <Picker
            label="Models" summary={cmpKeys.length ? `${cmpKeys.length} of ${Math.max(0, roster.length - 1)}` : "none"} groups={pickGroups}
            on={new Set(cmpKeys)} onChange={(s) => setCompare(roster.map((p) => p.key).filter((k) => s.has(k) && k !== modelKey))}
            footer={<span className="unit">a group header picks its whole group</span>}
          />
        </Control>
        <Control label="Gold">
          <Seg value={gray} onChange={setGray} options={[{ id: "all", label: "all", title: "Every gold label counts" }, { id: "nogray", label: "exclude gray", title: "Drop decisions whose gold is debatable; at document level, drop every document with a debatable label" }]} />
        </Control>
        <Control label="Level">
          <Seg value={level} onChange={setLevel} options={[{ id: "doc", label: "document", title: "A document is responsive if any issue is" }, { id: "decision", label: "decision", title: "Every (document, issue) judgment" }]} />
        </Control>
      </div>

      {loadErr && <div className="empty">Could not load cutoffs.json: {loadErr}</div>}
      {!data && !loadErr && <div className="empty">Loading cutoffs.json…</div>}

      {c && m && meta && cur && def && (
        <>
          {/* ---- pooled impact ---- */}
          <section className="section">
            <div className="cut-grid">
              <div className="card">
                <div className="card-t">
                  <h3>Pooled impact</h3>
                  <span className="unit">{c.label} · {meta.short} · {fmtInt(cur.n)} {levelWord}</span>
                  <span className="right"><Hint title="Pooled impact" items={[
                    { k: "Benchmark 0.5", v: "The published figures: the model's stated label for every decision, which is p ≥ 0.5 except where a model contradicted its own probability." },
                    { k: "Current", v: "The same decisions re-called at the per-issue cutoffs set below: responsive when p ≥ cutoff." },
                    { k: "Level", v: levelNote },
                    { k: "Elusion", v: "Share of the documents (or decisions) left unflagged that are in fact responsive." },
                    { k: "Review share", v: "Share flagged for review." },
                  ]} /></span>
                </div>
                <table className="cut-pool">
                  <thead><tr><th /><th>Benchmark 0.5</th><th>Current</th><th>Δ pts</th></tr></thead>
                  <tbody>
                    <tr><th>Recall</th><td className="num">{pts(def.recall)}%</td><td className="num hl">{pts(cur.recall)}%</td><td><Delta cur={cur.recall} ref={def.recall} /></td></tr>
                    <tr><th>Precision</th><td className="num">{pts(def.precision)}%</td><td className="num hl">{pts(cur.precision)}%</td><td><Delta cur={cur.precision} ref={def.precision} /></td></tr>
                    <tr className="f1"><th>F1</th><td className="num">{pts(def.f1)}%</td><td className="num hl">{pts(cur.f1)}%</td><td><Delta cur={cur.f1} ref={def.f1} /></td></tr>
                    <tr><th>Elusion</th><td className="num">{pts(def.elusion)}%</td><td className="num">{pts(cur.elusion)}%</td><td><Delta cur={cur.elusion} ref={def.elusion} good="down" /></td></tr>
                    <tr><th>Review share</th><td className="num">{pts(def.reviewShare)}%</td><td className="num">{pts(cur.reviewShare)}%</td><td><Delta cur={cur.reviewShare} ref={def.reviewShare} good={null} /></td></tr>
                    <tr className="cnt"><th>Flagged · positives</th><td className="num">{fmtInt(def.flagged)} · {fmtInt(def.nPos)}</td><td className="num">{fmtInt(cur.flagged)} · {fmtInt(cur.nPos)}</td><td /></tr>
                  </tbody>
                </table>
                {m.nDocs < c.nDocs && <p className="cut-note">Scored on {fmtInt(m.nDocs)} of {fmtInt(c.nDocs)} documents (a stratified subsample); every figure here is over those.</p>}
                {m.nErr > 0 && <p className="cut-note">{fmtInt(m.nErr)} decisions errored and are left out, as in the benchmark.</p>}
                {m.nDisagree > 0 && <p className="cut-note">On {fmtInt(m.nDisagree)} decisions this model's stated label contradicts its probability (for example “not responsive” at p = 0.99). The benchmark scored the label; this page thresholds the probability, so the current figures at 0.5 differ from the published ones for this model.</p>}
              </div>
              <div className="card">
                <div className="card-t">
                  <h3>Precision against recall</h3>
                  <span className="unit">line: one shared cutoff swept 0–1 · hollow: benchmark 0.5 · filled: current cutoffs{showOwn ? " · square: own optimum" : ""} · dashed: compared models · dotted: iso-F1</span>
                  <span className="right">
                    <Seg value={ghosts ? "on" : "off"} onChange={(v) => setGhosts(v === "on")} options={[{ id: "off", label: "model only" }, { id: "on", label: "roster at 0.5", title: "Every other model's published point, faint" }]} />
                    <Seg value={zoom ? "zoom" : "full"} onChange={(z) => setZoom(z === "zoom")} options={[{ id: "full", label: "0–100%" }, { id: "zoom", label: "fit to data" }]} />
                  </span>
                </div>
                <PRCurveChart
                  curve={curve} color={color} zoom={zoom} ghosts={ghostCurves} roster={rosterPts}
                  def={{ id: modelKey!, name: meta.short, color, recall: def.recall, precision: def.precision, f1: def.f1 }}
                  cur={{ id: modelKey!, name: meta.short, color, recall: chartCur.recall, precision: chartCur.precision, f1: chartCur.f1 }}
                  own={showOwn ? pt(modelKey!, meta.short, color, ownPrimaryM) : null}
                  xLabel={`Recall · ${levelWord}`} yLabel={`Precision · ${levelWord}`}
                />
                <div className="cut-chips">
                  <span className="cut-chip me" style={{ "--c": color } as React.CSSProperties}><span className="sw" />{meta.short}</span>
                  {cmpData.map((g) => (
                    <button key={g.key} type="button" className="cut-chip" style={{ "--c": g.color } as React.CSSProperties} onClick={() => setCompare(cmpKeys.filter((k) => k !== g.key))} title={`Remove ${g.name} from the comparison`}>
                      <span className="sw dash" />{g.name}<span className="x">×</span>
                    </button>
                  ))}
                  {cmpKeys.length === 0 && <span className="unit">Compare adds other models' frontiers here, in their colours.</span>}
                </div>
                <div className="legend-note"><span>Per-issue cutoffs can leave the shared-cutoff line: the current point above it means the issues have been tuned past what one cutoff reaches.</span></div>
              </div>
            </div>
            {compareRows.length > 1 && (
              <div className="card cut-cmp-card">
                <div className="card-t">
                  <h3>Models compared</h3>
                  <span className="unit">{levelWord} · at 0.5 and at the cutoffs set below, applied to every model{showOwn ? " · and at each model's own best cutoff per issue" : ""} · by F1 at these cutoffs</span>
                  <span className="right"><Hint title="Models compared" items={[
                    { k: "At these cutoffs", v: "The primary model's per-issue cutoffs applied to every model. Every model's probability is on the same 0–1 scale, so one set of cutoffs is a fair common rule, though not each model's best one." },
                    { k: "Own optimum", v: "Each model at its own best cutoff per issue (best F1 for that issue alone), the fairest 'what if everyone tuned' comparison. In-sample, like the Optimize buttons; the split-half check below has the honest version." },
                    { k: "Subsets", v: "Models scored on a subsample are pooled over their own documents; their rows are marked." },
                  ]} /></span>
                </div>
                <div className="cut-table-wrap">
                  <table className="cut-pool cut-cmp">
                    <thead>
                      <tr><th rowSpan={2}>Model</th><th colSpan={3} className="grp">Benchmark 0.5</th><th colSpan={5} className="grp">At these cutoffs</th>{showOwn && <th colSpan={4} className="grp">At own optimum</th>}</tr>
                      <tr><th>Recall</th><th>Precision</th><th>F1</th><th>Recall</th><th>Precision</th><th>F1</th><th>Review</th><th>Δ F1</th>{showOwn && <><th>Recall</th><th>Precision</th><th>F1</th><th>Δ F1</th></>}</tr>
                    </thead>
                    <tbody>
                      {compareRows.map((r) => (
                        <tr key={r.key} className={r.me ? "me" : ""}>
                          <th><span className="cut-chip-name" style={{ "--c": r.color } as React.CSSProperties}><span className={`sw${r.me ? "" : " dash"}`} />{r.name}{r.me ? <span className="unit"> · primary</span> : null}{r.nDocs < c.nDocs ? <span className="unit" title={`scored on ${fmtInt(r.nDocs)} of ${fmtInt(c.nDocs)} documents`}> · {fmtInt(r.nDocs)} docs</span> : null}</span></th>
                          <td className="num">{pts(r.def.recall)}</td><td className="num">{pts(r.def.precision)}</td><td className="num">{pts(r.def.f1)}</td>
                          <td className="num">{pts(r.cur.recall)}</td><td className="num">{pts(r.cur.precision)}</td><td className="num hl">{pts(r.cur.f1)}</td><td className="num">{pts(r.cur.reviewShare)}</td><td><Delta cur={r.cur.f1} ref={r.def.f1} /></td>
                          {showOwn && <><td className="num">{pts(r.own?.recall)}</td><td className="num">{pts(r.own?.precision)}</td><td className="num">{pts(r.own?.f1)}</td><td><Delta cur={r.own?.f1} ref={r.def.f1} /></td></>}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </section>

          {/* ---- global controls ---- */}
          <section className="section">
            <div className="card cut-actions">
              <div className="card-t"><h3>Set every issue</h3><span className="unit">the buttons move the sliders below; each issue can then be adjusted on its own</span><span className="right">{optimizeHint}</span></div>
              <div className="cut-act-row">
                <Control label="Shared cutoff">
                  <span className="cut-shared">
                    <CutoffSlider idx={shared ?? DEFAULT_CUTOFF_IDX} onChange={(i) => { setShared(i); }} color={color} label="shared" />
                    <span className="num cut-val">{shared == null ? "mixed" : gridValue(shared).toFixed(3)}</span>
                  </span>
                </Control>
                <Control label="Optimize">
                  <button type="button" className="studio-btn" onClick={optIssue} title="Best F1 for each issue on its own">best F1 per issue</button>
                  <button type="button" className="studio-btn" onClick={optPooled} title={`Best pooled ${level === "doc" ? "document" : "decision"}-level F1 by coordinate ascent`}>best pooled F1 · {level === "doc" ? "document" : "decision"}</button>
                  {st.pooledDiff != null && <span className="cut-status">{st.pooledDiff === 0 ? "same as per-issue" : `differs from per-issue on ${st.pooledDiff} issue${st.pooledDiff === 1 ? "" : "s"}`}</span>}
                </Control>
                <Control label="Every model">
                  <button type="button" className="studio-btn" onClick={optAll} title="This model's sliders go to its best F1 per issue; every compared model is also shown at its own best cutoff per issue">
                    optimize all shown models
                  </button>
                  {showOwn && <span className="cut-status">own optimum shown for {compareRows.length} model{compareRows.length === 1 ? "" : "s"} · <button type="button" className="cut-link" onClick={() => setShowOwn(false)}>hide</button></span>}
                </Control>
                <Control label="Target recall">
                  <span className="studio-size">
                    <input type="number" min={1} max={100} step={1} value={st.target} onChange={(e) => patch({ target: Math.min(100, Math.max(1, Math.round(Number(e.target.value) || st.target))) })} aria-label="target recall, percent" />
                    <span className="unit">%</span>
                  </span>
                  <button type="button" className="studio-btn" onClick={applyTarget} title="Per issue, the highest cutoff whose recall still reaches the target">apply</button>
                  {st.targetMiss && st.targetMiss.some(Boolean) && <span className="cut-status err">{st.targetMiss.filter(Boolean).length} issue{st.targetMiss.filter(Boolean).length === 1 ? "" : "s"} reach it only at cutoff 0 (everything flagged)</span>}
                </Control>
                <Control label="">
                  <button type="button" className="studio-btn" onClick={reset}>reset to 0.5</button>
                </Control>
              </div>
            </div>
          </section>

          {/* ---- per-issue table ---- */}
          <section className="section">
            <div className="card">
              <div className="card-t">
                <h3>Per issue</h3>
                <span className="unit">{nq} issues · decision level · Δ in points against the published 0.5</span>
                <span className="right">
                  <Seg value={spark} onChange={setSpark} options={[{ id: "hist", label: "histogram" }, { id: "pr", label: "PR curve" }]} />
                  <Seg value={sort} onChange={setSort} options={[{ id: "prev", label: "by prevalence" }, { id: "gain", label: "by F1 gain" }]} />
                </span>
              </div>
              <div className="cut-table-wrap">
                <table className={`cut-table${anim ? " anim" : ""}`}>
                  <thead>
                    <tr><th>Issue</th><th>Cutoff</th><th className="r">Flagged</th><th className="r">Recall</th><th className="r">Precision</th><th className="r">F1</th><th>{spark === "hist" ? "Scores" : "PR"}</th></tr>
                  </thead>
                  <tbody>
                    {sorted.map((r) => {
                      const idx = cutoffs[r.q], miss = st.targetMiss?.[r.q];
                      return (
                        <tr key={r.iss.id} className={miss ? "miss" : ""}>
                          <td className="iss">
                            <div className="t" title={r.iss.title}>{r.iss.short}</div>
                            <div className="s">{fmtPct(r.nPos / Math.max(1, r.n), 1)} · {fmtInt(r.nPos)} of {fmtInt(r.n)}{r.iss.n_gray > 0 ? ` · ${fmtInt(r.iss.n_gray)} gray` : ""}{miss ? " · target only at 0" : ""}</div>
                          </td>
                          <td className="cut">
                            <CutoffSlider idx={idx} onChange={(i) => setCutoffs(cutoffs.map((v, q) => (q === r.q ? i : v)))} color={color} label={r.iss.short} />
                            <input className="cut-num" type="number" min={0} max={1} step={0.005} value={gridValue(idx).toFixed(3)} onChange={(e) => { const v = Number(e.target.value); if (Number.isFinite(v)) setCutoffs(cutoffs.map((x, q) => (q === r.q ? Math.min(GRID_N, Math.max(0, Math.round(v * GRID_N))) : x))); }} aria-label={`${r.iss.short} cutoff value`} />
                          </td>
                          <td className="r num"><div>top {fmtInt(r.cur.flagged)}</div><div className="s">{fmtPct(r.cur.reviewShare)} of {fmtInt(r.n)}</div></td>
                          <td className="r num"><div>{pts(r.cur.recall)}%</div><Delta cur={r.cur.recall} ref={r.def.recall} /></td>
                          <td className="r num"><div>{pts(r.cur.precision)}%</div><Delta cur={r.cur.precision} ref={r.def.precision} /></td>
                          <td className="r num f1">
                            <div>{pts(r.cur.f1)}%</div><Delta cur={r.cur.f1} ref={r.def.f1} />
                            {cmpData.length === 1 && cmpIssuePts[0] && <div className="s cmp1" style={{ "--c": cmpData[0].color } as React.CSSProperties} title={`${cmpData[0].name} at this cutoff`}><span className="sw dash" />{pts(cmpIssuePts[0][r.q].f1)}%</div>}
                          </td>
                          <td className="sp"><IssueSpark kind={spark} hist={r.hist} curve={r.curve} cutoffIdx={idx} color={color} marks={spark === "pr" ? cmpIssuePts.map((ps) => ps[r.q]) : undefined} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              <div className="legend-note">
                <span>{spark === "hist" ? "Scores: the issue's decisions by probability in 0.05 bins, gold not-responsive above the line and responsive below, each side scaled to its own peak; the rule is the cutoff and the tinted side is flagged." : `PR: the issue's precision (y) against recall (x) over every cutoff; hollow mark at 0.5, filled at the current cutoff${cmpData.length ? "; small dots: the compared models at the same cutoff, in their colours" : ""}.`}</span>
                {cmpData.length === 1 && <span>Under F1, in {cmpData[0].name}'s colour: that model's F1 for the issue at the same cutoff.</span>}
                <span>Flagged: decisions at or above the cutoff, i.e. the top k documents for that issue and the share of the corpus that is.</span>
                <span>Prevalence and counts are over the decisions this model has{gray === "nogray" ? ", gray excluded" : ""}.</span>
              </div>
            </div>
          </section>

          {/* ---- honesty panel ---- */}
          <section className="section">
            <div className="card">
              <div className="card-t">
                <h3>Split-half check</h3>
                <span className="unit">tune on a random half of the documents, score the other half · {levelWord}, {gray === "all" ? "all gold" : "gray excluded"}</span>
                <span className="right">
                  <Seg value={tune} onChange={setTune} options={[{ id: "issue", label: "tune per-issue F1" }, { id: "pooled", label: "tune pooled F1" }]} />
                  <button type="button" className="studio-btn" onClick={() => runSplit(st.seed)}>{st.split ? "run again" : "run"}</button>
                  <button type="button" className="studio-btn" onClick={() => runSplit(st.seed + 1)} title="A different random split">re-roll</button>
                  {st.split && <button type="button" className="studio-btn" onClick={applySplitCutoffs} title="Set the sliders to the cutoffs tuned on the training half">use these cutoffs</button>}
                  {cmpKeys.length > 0 && <button type="button" className="studio-btn" onClick={() => runSplitAll(st.seed)} disabled={!!st.splitAll?.pending} title="The same check for this model and every compared model: does tuning help each one, on held-out documents?">{st.splitAll?.pending ? `running · ${st.splitAll.rows.length} of ${st.splitAll.rows.length + st.splitAll.pending}` : "run for all shown models"}</button>}
                  <Hint title="Split-half check" text="Optimizing cutoffs on the evaluation set and scoring them on the same set is in-sample: some of the F1 gain is fit to noise. Here the documents are split at random (seeded, so a roll can be repeated); the cutoffs are tuned on one half exactly as the Optimize button does, then both halves are scored at those cutoffs and at the benchmark 0.5. The held-out half is the honest estimate; the mean over 20 splits steadies it. 'Run for all shown models' repeats this for every compared model, each split on its own scored documents." />
                </span>
              </div>
              {st.splitAll && (
                <div className="cut-split-all">
                  <div className="cut-table-wrap">
                    <table className="cut-pool cut-cmp">
                      <thead>
                        <tr><th rowSpan={2}>Model</th><th colSpan={3} className="grp">Held-out half · seed {st.splitAll.seed}</th><th colSpan={3} className="grp">Over 20 splits</th></tr>
                        <tr><th>F1 at 0.5</th><th>F1 tuned</th><th>Δ F1</th><th>Mean held-out Δ</th><th>Mean tuning-half Δ</th><th>Splits improved</th></tr>
                      </thead>
                      <tbody>
                        {splitAllRows.map((r) => {
                          const p = PRIMARY_BY_KEY[r.key], me = r.key === modelKey;
                          return (
                            <tr key={r.key} className={me ? "me" : ""}>
                              <th><span className="cut-chip-name" style={{ "--c": p.color } as React.CSSProperties}><span className={`sw${me ? "" : " dash"}`} />{p.short}{me ? <span className="unit"> · primary</span> : null}</span></th>
                              <td className="num">{pts(r.split.test.base.f1)}</td><td className="num">{pts(r.split.test.tuned.f1)}</td><td><Delta cur={r.split.test.tuned.f1} ref={r.split.test.base.f1} /></td>
                              <td className={`num hl ${r.repeat.meanTestGain >= 0.0005 ? "good" : r.repeat.meanTestGain <= -0.0005 ? "bad" : ""}`}>{r.repeat.meanTestGain >= 0 ? "+" : "−"}{Math.abs(r.repeat.meanTestGain * 100).toFixed(1)}</td>
                              <td className="num">{r.repeat.meanTrainGain >= 0 ? "+" : "−"}{Math.abs(r.repeat.meanTrainGain * 100).toFixed(1)}</td>
                              <td className="num">{Math.round(r.repeat.positiveShare * 100)}%</td>
                            </tr>
                          );
                        })}
                        {st.splitAll.pending > 0 && <tr className="cnt"><th colSpan={7}>{st.splitAll.pending} model{st.splitAll.pending === 1 ? "" : "s"} still running…</th></tr>}
                      </tbody>
                    </table>
                  </div>
                  <div className="cut-split-note">
                    <div>Tuned {st.splitAll.tune === "issue" ? "per-issue F1" : "pooled F1"} on a random half of each model's documents, scored on the other half at {st.splitAll.level === "doc" ? "document" : "decision"} level, {st.splitAll.gray === "all" ? "all gold" : "gray excluded"}. Δ in F1 points against the benchmark 0.5 on the same half; the 20-split mean is the steadier figure.</div>
                    {splitAllStale && <div className="bad">The level, gold or tuning has changed since this ran; run it again for figures that match the rest of the page.</div>}
                  </div>
                </div>
              )}
              {!st.split && !st.splitAll && <div className="empty small">Press run. Seed {st.seed}.</div>}
              {st.split && st.repeat && (
                <div className="cut-split">
                  {(["train", "test"] as const).map((half) => {
                    const h = st.split![half];
                    return (
                      <table key={half} className="cut-pool">
                        <thead><tr><th>{half === "train" ? `Tuning half · ${fmtInt(half === "train" ? st.split!.nTrain : st.split!.nTest)} docs` : `Held-out half · ${fmtInt(st.split!.nTest)} docs`}</th><th>0.5</th><th>Tuned</th><th>Δ pts</th></tr></thead>
                        <tbody>
                          <tr><th>Recall</th><td className="num">{pts(h.base.recall)}%</td><td className="num">{pts(h.tuned.recall)}%</td><td><Delta cur={h.tuned.recall} ref={h.base.recall} /></td></tr>
                          <tr><th>Precision</th><td className="num">{pts(h.base.precision)}%</td><td className="num">{pts(h.tuned.precision)}%</td><td><Delta cur={h.tuned.precision} ref={h.base.precision} /></td></tr>
                          <tr className="f1"><th>F1</th><td className="num">{pts(h.base.f1)}%</td><td className={`num${half === "test" ? " hl" : ""}`}>{pts(h.tuned.f1)}%</td><td><Delta cur={h.tuned.f1} ref={h.base.f1} /></td></tr>
                        </tbody>
                      </table>
                    );
                  })}
                  <div className="cut-split-note">
                    <div>Seed {st.split.seed}. Tuned cutoffs: {st.split.cutoffs.map((i, q) => `${c.issues[q].short} ${gridValue(i).toFixed(3)}`).join(" · ")}.</div>
                    <div>Over 20 splits: mean held-out F1 change <b className={st.repeat.meanTestGain >= 0 ? "good" : "bad"}>{st.repeat.meanTestGain >= 0 ? "+" : "−"}{Math.abs(st.repeat.meanTestGain * 100).toFixed(1)} pts</b> (tuning half {st.repeat.meanTrainGain >= 0 ? "+" : "−"}{Math.abs(st.repeat.meanTrainGain * 100).toFixed(1)}); held-out F1 improved in {Math.round(st.repeat.positiveShare * 100)}% of splits.</div>
                    <div>The published benchmark uses 0.5 with no tuning; this page is exploratory.</div>
                  </div>
                </div>
              )}
            </div>
          </section>

          {/* ---- export ---- */}
          <section className="section">
            <div className="card">
              <div className="card-t"><h3>Export</h3><span className="unit">the current cutoffs and figures; the page address carries the same state</span></div>
              <div className="cut-act-row">
                <button type="button" className="studio-btn" onClick={() => clip.copy(jsonText())}>copy cutoffs as JSON</button>
                <button type="button" className="studio-btn" onClick={() => clip.copy(summaryText())}>copy summary (markdown)</button>
                <button type="button" className="studio-btn" onClick={() => clip.copy(location.href)}>copy link</button>
                {clip.status && <span className={`studio-status${clip.status.err ? " err" : ""}`} role="status">{clip.status.msg}</span>}
              </div>
              {clip.fallback && (
                <div className="cut-fallback">
                  <textarea readOnly value={clip.fallback} rows={8} onFocus={(e) => e.currentTarget.select()} />
                  <button type="button" className="studio-btn" onClick={clip.clearFallback}>close</button>
                </div>
              )}
            </div>
          </section>
        </>
      )}

      <footer className="notes"><span className="notes-t">Cutoffs are thresholds on each model's own probability. Nothing here changes the published comparison, which scores every model at 0.5.</span></footer>
    </div>
  );
}