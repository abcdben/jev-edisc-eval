import { useEffect, useMemo, useState } from "react";
import { Seg } from "./components/ui";
import { PRScatter, type PRItem } from "./components/PRScatter";
import { THEME_KEY, THEME_OPTIONS, readTheme, type Theme } from "./theme";
import {
  ARM_BY_ID, DEFAULT_ARMS, DEFAULT_DATASETS, DS_BY_ID, EX_BY_ID, GROUPS, KIND_LABEL, KIND_ORDER, REVIEWER_MEASURES, STUDY, armsWithData, fmtCell, fmtValue, isHuman, reviewerArms, reviewerCell,
  type Arm, type ArmKind, type Cell, type Experiment, type Measure,
} from "./studyData";
import { ArmMark, DotRows, Frontier, SidesBars, type FrontierItem, type SeriesItem, type SidesItem, type ValueItem } from "./study/Charts";
import { TarReviewerControl } from "./components/TarReviewer";
import { REALISTIC_REVIEWER, asReviewer, type ReviewerSetting } from "./tarGrid";

type Mode = "plot" | "table";
/** `tarReviewer` (tarGrid.ts): the simulated reviewer's error rates for the TAR arms (REALISTIC_REVIEWER to start); "published" is study.json's own cells. */
type State = { mode: Mode; dataset: string; datasets: string[]; experiment: string; experiments: string[]; arms: string[]; measure: string | null; prView: "map" | "ranked"; tarReviewer: ReviewerSetting };
/** A cell lookup: studyData.cell under the page's reviewer setting (reviewerCell). */
type CellFn = (ds: string, ex: string, arm: string, m: string) => Cell | null;

const KEY = "study-state-v1";
const ALL_EXPERIMENTS = STUDY.experiments.map((e) => e.id);
const DEFAULT: State = { mode: "plot", dataset: "trec", datasets: DEFAULT_DATASETS, experiment: "accuracy", experiments: ALL_EXPERIMENTS, arms: DEFAULT_ARMS, measure: null, prView: "map", tarReviewer: REALISTIC_REVIEWER };
// a stored null (the published cells, before the realistic default existed) coerces to undefined and so starts at the default
const readState = (): State => { try { const s = { ...DEFAULT, ...JSON.parse(localStorage.getItem(KEY) || "{}") }; return { ...s, tarReviewer: asReviewer(s.tarReviewer) ?? REALISTIC_REVIEWER }; } catch { return DEFAULT; } };

const seriesOf = (a: Arm): SeriesItem => ({ id: a.id, name: a.short, color: a.color, planned: a.status === "planned", human: isHuman(a), note: a.note });
const withCell = (a: Arm, c: Cell | null): ValueItem => ({ ...seriesOf(a), planned: !!c?.planned || a.status === "planned", v: c?.v ?? null, lo: c?.lo ?? null, hi: c?.hi ?? null, n: c?.n ?? null });

export default function StudyPage() {
  const [theme, setTheme] = useState<Theme>(readTheme);
  useEffect(() => { document.documentElement.dataset.theme = theme; try { localStorage.setItem(THEME_KEY, theme); } catch { /* ignore */ } }, [theme]);
  const [s, setS] = useState<State>(readState);
  useEffect(() => { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch { /* ignore */ } }, [s]);
  const up = (p: Partial<State>) => setS((x) => ({ ...x, ...p }));

  const ex = EX_BY_ID[s.experiment] ?? STUDY.experiments[0];
  const ds = DS_BY_ID[s.dataset] ?? STUDY.datasets[0];
  const armSet = new Set(s.arms);
  const toggleArm = (id: string) => up({ arms: armSet.has(id) ? s.arms.filter((a) => a !== id) : [...s.arms, id] });
  const toggleEx = (id: string) => up({ experiments: s.experiments.includes(id) ? s.experiments.filter((e) => e !== id) : ALL_EXPERIMENTS.filter((e) => e === id || s.experiments.includes(e)) });
  const toggleDs = (id: string) => up({ datasets: s.datasets.includes(id) ? s.datasets.filter((d) => d !== id) : STUDY.datasets.filter((d) => d.id === id || s.datasets.includes(d.id)).map((d) => d.id) });

  // Arms offered: every arm in the file, grouped by kind; humans appear only where an experiment defines them (greyed elsewhere in plot mode).
  const armGroups = useMemo(() => KIND_ORDER.map((k) => ({ kind: k, items: STUDY.arms.filter((a) => a.kind === k) })).filter((g) => g.items.length), []);
  const available = new Set(armsWithData(ds.id, ex.id));
  // TAR reviewer error rates (studyData.ts reviewerCell): every cell read below goes through the setting; the control sits in the rail while a TAR arm is on.
  // In table mode the sliders follow the first selected dataset with a grid; each column is patched where its own dataset has one.
  const cellR: CellFn = (d, e, a, m) => reviewerCell(d, e, a, m, s.tarReviewer);
  const selArms = s.arms.map((id) => ARM_BY_ID[id]).filter(Boolean);
  const gridDs = s.mode === "plot" ? ds.id : (s.datasets.find((d) => reviewerArms(d, selArms).some((a) => a.grid)) ?? s.datasets[0] ?? ds.id);
  // ... and only while an experiment on show has a measure the grid moves (the others would not change)
  const revShown = s.mode === "plot" ? ex.id in REVIEWER_MEASURES : s.experiments.some((e) => e in REVIEWER_MEASURES);
  const revArms = revShown ? reviewerArms(gridDs, selArms) : [];

  return (
    <div className="page study-page">
      <header className="study-hdr">
        <div>
          <h1>Machine review vs. the reviewers</h1>
          <p className="sub">Decision models, LLMs and classical TAR beside the human reviewers who built the test collections. Hatched or dashed marks are placeholders for experiments not yet run.</p>
        </div>
        <div className="study-hdr-r">
          <a className="home-link" href="./" title="The landing page: every page of the site">Home</a>
          <Seg value={s.mode} onChange={(m) => up({ mode: m })} options={[{ id: "plot", label: "Plot" }, { id: "table", label: "Table" }]} />
          <Seg value={theme} onChange={setTheme} options={THEME_OPTIONS.map((t) => ({ id: t.id, label: t.label, title: t.title }))} />
        </div>
      </header>

      <div className="study-body">
        <aside className="study-rail">
          <section>
            <h4>Dataset{s.mode === "table" && <span className="n">{s.datasets.length}/{STUDY.datasets.length}</span>}</h4>
            {STUDY.datasets.map((d) => {
              const on = s.mode === "plot" ? d.id === s.dataset : s.datasets.includes(d.id);
              const st = ex.status[d.id];
              return (
                <div key={d.id} className={`pick-row${on ? " on" : ""}`}>
                  <button className="pick-main" role={s.mode === "plot" ? "radio" : "checkbox"} aria-checked={on} onClick={() => (s.mode === "plot" ? up({ dataset: d.id }) : toggleDs(d.id))} title={d.short}>
                    <span className={`box${on ? " on" : ""}${s.mode === "plot" ? " radio" : ""}`} />
                    <span className="lbl"><span className="nm">{d.label}</span>{s.mode === "plot" && st === "na" ? <span className="tag na">n/a</span> : d.status === "planned" && <span className="tag">planned</span>}</span>
                  </button>
                </div>
              );
            })}
            <p className="study-ds-note">{ds.short}{ds.n_docs ? ` · ${ds.n_docs.toLocaleString()} documents · ${ds.n_issues} issues` : ""}{ds.gold ? ` · standard: ${ds.gold}` : ""}</p>
          </section>

          <section>
            <h4>Experiment{s.mode === "table" && <span className="n">{s.experiments.length}/{ALL_EXPERIMENTS.length}</span>}</h4>
            {GROUPS.map((g) => (
              <div key={g.group}>
                <div className="pick-sh">{g.group}</div>
                {g.items.map((e) => {
                  const st = s.mode === "plot" ? e.status[ds.id] : (s.datasets.some((d) => e.status[d] !== "na") ? "measured" : "na");
                  const on = s.mode === "plot" ? e.id === s.experiment : s.experiments.includes(e.id);
                  const disabled = st === "na";
                  return (
                    <div key={e.id} className={`pick-row${on ? " on" : ""}${disabled ? " dis" : ""}`}>
                      <button className="pick-main" role={s.mode === "plot" ? "radio" : "checkbox"} aria-checked={on} disabled={disabled} onClick={() => (s.mode === "plot" ? up({ experiment: e.id, measure: null }) : toggleEx(e.id))} title={disabled ? e.na ?? "Not applicable to this dataset" : e.question}>
                        <span className={`box${on ? " on" : ""}${s.mode === "plot" ? " radio" : ""}`} />
                        <span className="lbl"><span className="nm">{e.title}</span></span>
                      </button>
                    </div>
                  );
                })}
              </div>
            ))}
          </section>

          <section>
            <h4>Arms<span className="n">{s.arms.length}</span></h4>
            {armGroups.map((g) => (
              <div key={g.kind}>
                <button className="pick-gh" onClick={() => { const ids = g.items.map((a) => a.id); const all = ids.every((i) => armSet.has(i)); up({ arms: all ? s.arms.filter((a) => !ids.includes(a)) : [...new Set([...s.arms, ...ids])] }); }}>
                  <span>{KIND_LABEL[g.kind as ArmKind]}</span><span className="n">{g.items.filter((a) => armSet.has(a.id)).length}/{g.items.length}</span>
                </button>
                {g.items.map((a) => {
                  const on = armSet.has(a.id);
                  const absent = s.mode === "plot" && !available.has(a.id);
                  return (
                    <div key={a.id} className={`pick-row${on ? " on" : ""}${absent ? " dim" : ""}`}>
                      <button className="pick-main" role="checkbox" aria-checked={on} onClick={() => toggleArm(a.id)} title={absent ? "No values for this dataset and experiment" : a.note ?? a.name}>
                        <span className={`box${on ? " on" : ""}`} />
                        <span className="lbl">
                          <span className="mark"><svg width={12} height={12}><ArmMark x={6} y={6} r={4} item={seriesOf(a)} /></svg></span>
                          <span className="nm">{a.short}</span>
                          {a.status === "planned" && <span className="tag">planned</span>}
                        </span>
                      </button>
                    </div>
                  );
                })}
              </div>
            ))}
          </section>

          {revArms.length > 0 && (
            <section>
              <h4>TAR reviewer</h4>
              <TarReviewerControl stacked value={s.tarReviewer} onChange={(r) => up({ tarReviewer: r })} arms={revArms} fixedHint={`adjustable runs not yet computed for ${DS_BY_ID[gridDs]?.label ?? gridDs}`} note="recall, precision, F1, review share, hours and cost follow the grid; elusion and the human-side measures do not" />
            </section>
          )}
        </aside>

        <main className="study-main">
          {s.mode === "plot" ? <PlotView ex={ex} dsId={ds.id} arms={s.arms} measure={s.measure} onMeasure={(m) => up({ measure: m })} prView={s.prView} onPrView={(v) => up({ prView: v })} cell={cellR} /> : <TableView state={s} onJump={(dsId, exId) => up({ mode: "plot", dataset: dsId, experiment: exId, measure: null })} cell={cellR} />}
        </main>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------------------------------------ plot mode

function PlotView({ ex, dsId, arms, measure, onMeasure, prView, onPrView, cell }: { ex: Experiment; dsId: string; arms: string[]; measure: string | null; onMeasure: (m: string) => void; prView: "map" | "ranked"; onPrView: (v: "map" | "ranked") => void; cell: CellFn }) {
  const st = ex.status[dsId];
  const sel = arms.map((id) => ARM_BY_ID[id]).filter(Boolean);
  const m: Measure = ex.measures.find((x) => x.id === measure) ?? ex.measures[0];
  const items = sel.map((a) => withCell(a, cell(dsId, ex.id, a.id, m.id))).filter((i) => i.v != null);
  // the cells the reviewer setting re-pointed on this chart (studyData.ts reviewerCell `note`), named under the numbers
  const revNotes = [...new Set(sel.flatMap((a) => ex.measures.map((x) => cell(dsId, ex.id, a.id, x.id)?.note).filter((n): n is string => !!n)))];

  let chart: React.ReactNode;
  if (st === "na") {
    chart = <div className="study-empty">{ex.na ?? "This experiment does not apply to the selected dataset."}</div>;
  } else if (ex.chart === "pr" && prView === "map") {
    const pr: PRItem[] = sel.flatMap((a): PRItem[] => {
      const r = cell(dsId, ex.id, a.id, "recall"), p = cell(dsId, ex.id, a.id, "precision");
      if (!r?.v || !p?.v) return [];
      const ci = (c: Cell): [number, number, number] => [c.v!, c.lo ?? c.v!, c.hi ?? c.v!];
      return [{ id: a.id, name: a.short, color: a.color, recall: ci(r), precision: ci(p), dashed: r.planned || a.status === "planned", sub: r.planned ? "placeholder: not yet measured" : r.note ?? (r.n ? `${r.n.toLocaleString()} documents scored` : undefined), decider: isHuman(a) }];
    });
    chart = <div className="chart-fill" style={{ minHeight: 440 }}><PRScatter items={pr} zoom emptyText="Select at least one arm." fill logos={false} /></div>;
  } else if (ex.chart === "grid") {
    const rows: SidesItem[] = sel.map((a) => {
      const g = (k: string) => cell(dsId, ex.id, a.id, k);
      const parts = ["agree_both", "sides_authority", "sides_reviewer", "neither"].map((k) => g(k)?.v ?? 0) as [number, number, number, number];
      const tot = parts.reduce((x, y) => x + y, 0);
      if (!tot) return null;
      return { ...seriesOf(a), planned: !!g("agree_both")?.planned, parts: parts.map((p) => p / tot) as [number, number, number, number], kappaA: g("kappa_authority")?.v ?? null, kappaR: g("kappa_reviewer")?.v ?? null, dep: g("error_dependence")?.v ?? null };
    }).filter((x): x is SidesItem => !!x);
    chart = <SidesBars items={rows} />;
  } else if (ex.chart === "frontier") {
    const rows: FrontierItem[] = sel.map((a) => {
      const g = (k: string) => cell(dsId, ex.id, a.id, k);
      const r = g("recall"), sh = g("human_share");
      if (r?.v == null || sh?.v == null) return null;
      return { ...seriesOf(a), planned: !!r.planned, recall: r.v, share: sh.v, hours: g("hours_per_100k")?.v ?? null, usd: g("usd_per_100k")?.v ?? null };
    }).filter((x): x is FrontierItem => !!x);
    chart = <Frontier items={rows} />;
  } else {
    const ref = m.unit === "ratio" ? 1 : m.unit === "auc" ? 0.5 : null;
    chart = <DotRows items={items} unit={m.unit} higherBetter={m.higher_better} axis={m.label} reference={ref} />;
  }

  const showMeasureSeg = ex.chart === "bars" || ex.chart === "roc" || (ex.chart === "pr" && prView === "ranked");
  return (
    <div className="card study-card">
      <div className="card-t">
        <h3>{ex.title}</h3>
        <span className="unit">{DS_BY_ID[dsId].label}{st === "planned" ? " · placeholder values" : ""}</span>
        <span className="right">
          {ex.chart === "pr" && <Seg value={prView} onChange={onPrView} options={[{ id: "map", label: "map" }, { id: "ranked", label: "ranked" }]} />}
          {showMeasureSeg && <Seg value={m.id} onChange={onMeasure} options={ex.measures.map((x) => ({ id: x.id, label: x.label }))} />}
        </span>
      </div>
      <p className="study-q">{ex.question}</p>
      {chart}
      {st !== "na" && <Numbers ex={ex} dsId={dsId} arms={sel} cell={cell} />}
      {revNotes.length > 0 && <p className="study-ds-note">* {revNotes.join(" · ")} — the marked cells are the TAR simulation re-run from the precomputed grid (results/tar_grid.json: classifier retrained, stop rule re-applied) and differ from the published values (study.json).</p>}
    </div>
  );
}

/** The numbers behind the chart: one row per selected arm, one column per measure. */
function Numbers({ ex, dsId, arms, cell }: { ex: Experiment; dsId: string; arms: Arm[]; cell: CellFn }) {
  const rows = arms.filter((a) => ex.measures.some((m) => cell(dsId, ex.id, a.id, m.id)?.v != null));
  if (!rows.length) return null;
  return (
    <table className="study-tbl">
      <thead><tr><th>Arm</th>{ex.measures.map((m) => <th key={m.id}>{m.label}</th>)}</tr></thead>
      <tbody>
        {rows.map((a) => (
          <tr key={a.id} className={isHuman(a) ? "human" : ""}>
            <td><svg width={12} height={12}><ArmMark x={6} y={6} r={4} item={seriesOf(a)} /></svg> {a.short}</td>
            {ex.measures.map((m) => { const c = cell(dsId, ex.id, a.id, m.id); return <td key={m.id} className={c?.planned ? "planned" : c?.note ? "rev" : ""} title={c?.planned ? "placeholder: not yet measured" : c?.note ? `${c.note}${c.n ? ` · n = ${c.n.toLocaleString()}` : ""}` : c?.n ? `n = ${c.n.toLocaleString()}` : undefined}>{fmtCell(c, m.unit)}{c?.note && <span className="rev-mark" aria-hidden>*</span>}</td>; })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

// ------------------------------------------------------------------------------------------------ table mode

function TableView({ state, onJump, cell }: { state: State; onJump: (ds: string, ex: string) => void; cell: CellFn }) {
  const dss = STUDY.datasets.filter((d) => state.datasets.includes(d.id));
  const arms = state.arms.map((id) => ARM_BY_ID[id]).filter(Boolean);
  if (!dss.length || !state.experiments.length) return <div className="card study-card"><div className="study-empty">{dss.length ? "Select at least one experiment." : "Select at least one dataset."}</div></div>;
  return (
    <div className="card study-card study-matrix-card">
      <div className="card-t"><h3>All measures by dataset</h3><span className="unit">rows: measures grouped by experiment · columns: datasets · each cell lists the selected arms</span></div>
      <div className="study-matrix-wrap">
        <table className="study-matrix">
          <thead><tr><th className="corner">Measure</th>{dss.map((d) => <th key={d.id}>{d.label}{d.status === "planned" && <span className="tag">planned</span>}<div className="sub">{d.short}</div></th>)}</tr></thead>
          <tbody>
            {STUDY.experiments.filter((e) => state.experiments.includes(e.id)).map((e) => (
              <ExperimentRows key={e.id} e={e} dss={dss.map((d) => d.id)} arms={arms} onJump={onJump} cell={cell} />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ExperimentRows({ e, dss, arms, onJump, cell }: { e: Experiment; dss: string[]; arms: Arm[]; onJump: (ds: string, ex: string) => void; cell: CellFn }) {
  if (dss.every((d) => e.status[d] === "na")) return null;
  return (
    <>
      <tr className="grp"><td colSpan={dss.length + 1}><span className="g">{e.group}</span> {e.title}<span className="q">{e.question}</span></td></tr>
      {e.measures.map((m) => (
        <tr key={m.id}>
          <th>{m.label}<span className="dir">{m.higher_better ? "↑" : "↓"}</span></th>
          {dss.map((d) => <MatrixCell key={d} dsId={d} e={e} m={m} arms={arms} onJump={onJump} cell={cell} />)}
        </tr>
      ))}
    </>
  );
}

function MatrixCell({ dsId, e, m, arms, onJump, cell }: { dsId: string; e: Experiment; m: Measure; arms: Arm[]; onJump: (ds: string, ex: string) => void; cell: CellFn }) {
  const st = e.status[dsId];
  if (st === "na") return <td className="na" title={e.na ?? "Not applicable"}>n/a</td>;
  const rows = arms.map((a) => ({ a, c: cell(dsId, e.id, a.id, m.id) })).filter((x) => x.c?.v != null);
  if (!rows.length) return <td className="na">—</td>;
  rows.sort((x, y) => (m.higher_better ? y.c!.v! - x.c!.v! : x.c!.v! - y.c!.v!));
  const planned = rows.every((x) => x.c!.planned);
  return (
    <td className={`vals${planned ? " planned" : ""}`} onClick={() => onJump(dsId, e.id)} title={`Open ${e.title} on ${DS_BY_ID[dsId].label}`}>
      {rows.map(({ a, c }) => (
        <div key={a.id} className={`v${isHuman(a) ? " human" : ""}${c!.planned ? " p" : ""}${c!.note ? " rev" : ""}`} title={c!.note ? `${fmtCell(c, m.unit)} · ${c!.note}` : fmtCell(c, m.unit)}>
          <svg width={10} height={10}><ArmMark x={5} y={5} r={3.2} item={seriesOf(a)} /></svg>
          <span className="nm">{a.short}</span>
          <span className="num">{fmtValue(c!.v, m.unit)}</span>
        </div>
      ))}
    </td>
  );
}
