import type { ReactNode } from "react";
import { CORPORA, DATA, GPU_NAME, GPU_USD_PER_HOUR, HUMAN_DEV_DOCS, HUMAN_DEV_DOCS_PER_HOUR, HUMAN_DEV_HOURS, HUMAN_DEV_USD, HUMAN_DEV_USD_PER_HOUR, PRIMARY_BY_KEY, fmtHours, fmtInt, fmtPct, fmtUSD, isDecider } from "../data";
import { DeciderTag, Modal } from "./ui";

/**
 * "Method": how each experiment was run, as two fact tables. Section A has one column per corpus the site offers;
 * section B is the measurement conventions shared by every corpus. Counts are read from findings.json so they
 * match the charts; the prose cells condense the reviewed notes on method that used to sit at the foot of the page.
 */

type Cells = Record<string, ReactNode>;
type FactRow = { k: string; cells: Cells };

const meta = (id: string) => DATA.corpora[id];
const sum = (o: Record<string, number>) => Object.values(o).reduce((a, b) => a + b, 0);
const N = ({ v }: { v: number | string }) => <span className="n">{typeof v === "number" ? fmtInt(v) : v}</span>;

/** Why a headline row was scored on fewer documents than the corpus. */
const SUBSET_WHY: Record<string, string> = { "laya-ft": "held-out split", "gemma3-12b": "stratified subsample" };
/** "Laya 1,288 (held-out split)" for every headline row of a corpus that was scored on a subset (all-issues arm), then the corpus size. A decision model's name carries the DECISION MODEL tag (data.ts isDecider). */
function subsets(id: string): ReactNode {
  const rows = DATA.records.filter((r) => r.corpus === id && r.tag === "" && r.arm === "multi" && r.primary && r.subset && PRIMARY_BY_KEY[r.model]);
  if (!rows.length) return "—";
  const parts = rows.map((r) => {
    const n = Number(r.subset!.match(/^(\d+) of/)?.[1] ?? NaN);
    return <span key={r.model}>{PRIMARY_BY_KEY[r.model].short}{isDecider(r.kind) && <DeciderTag />} <N v={Number.isNaN(n) ? r.subset! : n} />{SUBSET_WHY[r.model] ? ` (${SUBSET_WHY[r.model]})` : ""}</span>;
  });
  return <>{parts.map((p, i) => <span key={i}>{i > 0 && " · "}{p}</span>)}; of <N v={meta(id).n_docs} /> documents.</>;
}

function DocsCell({ id }: { id: string }) {
  const m = meta(id);
  return <><b><N v={m.n_docs} /></b> · <N v={m.n_pos_docs_any} /> responsive to at least one issue (<N v={fmtPct(m.n_pos_docs_any / m.n_docs, 0)} />)</>;
}
function GrayCount({ id }: { id: string }) {
  const m = meta(id);
  return <><N v={sum(m.n_gray_by_issue)} /> of <N v={m.n_docs * m.n_issues} /> decisions</>;
}

const DATASET_ROWS: FactRow[] = [
  {
    k: "Source",
    cells: {
      mnk: <><b>UCSF / JHU Opioid Industry Documents Archive</b>, Mallinckrodt litigation collection: emails of 23 key custodians.</>,
      trec: <><b>TREC 2016 Total Recall</b>, athome4: Jeb Bush gubernatorial email, 290,099 messages.</>,
    },
  },
  {
    k: "Documents scored",
    cells: { mnk: <DocsCell id="mnk" />, trec: <DocsCell id="trec" /> },
  },
  {
    k: "Unit · length",
    cells: {
      mnk: <><b>One email</b> with its headers; 300–12,000 characters (median ≈ 2,700).</>,
      trec: <><b>One email</b> with its headers; ≤ 12,000 characters (median ≈ 1,500).</>,
    },
  },
  {
    k: "Issues",
    cells: {
      mnk: <><b><N v={8} /></b>: four broad / narrow pairs (suspicious order monitoring, marketing, distribution data, DEA) written for this study from the opioid MDL record.</>,
      trec: <><b><N v={12} /></b> of the 34 NIST topics; the official topic sentence is the request, verbatim.</>,
    },
  },
  {
    k: "Criteria",
    cells: {
      mnk: <>RFP text, prose positive / negative descriptions, structured includes / excludes; <b>identical for every model</b>.</>,
      trec: <>Refined once on a <b>668-email calibration set</b> disjoint from evaluation (Jev and Gemini Flash-Lite on the bare NIST topic sentence; shared misses read per topic). Only the refined criteria are shown.</>,
    },
  },
  {
    k: "Truth data",
    cells: {
      mnk: <mark>Provisional gold from a <b>3-LLM panel</b> (Sonnet 5, GPT-5.6 Terra, Gemini 3.8 Flash), majority vote per decision; Jev and Laya never feed gold.</mark>,
      trec: <mark><b>NIST assessor judgments</b>: rel 1 or 2 → responsive; judged non-relevant and unjudged → not responsive (TREC convention).</mark>,
    },
  },
  {
    k: "Gray (debatable)",
    cells: {
      mnk: <>Panel split, or mean p(responsive) in 0.35–0.65: <b><GrayCount id="mnk" /></b>.</>,
      trec: <>None from NIST; <b><GrayCount id="trec" /></b> flagged where a facet's gold contradicts the topic text (NRA / non-resident aliens).</>,
    },
  },
  {
    k: "Sampling",
    cells: {
      mnk: <><b>Stratified</b>: keyword-doped strata per issue pair, adjacent-product hard negatives, 700 random; near-duplicate threads thinned. Keyword strata are not labels.</>,
      trec: <><b>Stratified</b> from the collection: 100 gold positives per topic, 1,000 judged non-relevant, 1,000 random; excludes the calibration set and 696 documents read while exploring.</>,
    },
  },
  {
    k: "Subsets (*)",
    cells: Object.fromEntries(CORPORA.map((c) => [c.id, subsets(c.id)])),
  },
  {
    k: "What each model saw",
    cells: {
      mnk: <>The email text with headers, the issue criteria, and a matter-background paragraph; returned <b>a label and a probability</b>.</>,
      trec: <>The email text with headers, the topic criteria, and a public-records background paragraph; <b>label and probability</b>.</>,
    },
  },
  {
    k: "Runs",
    cells: {
      mnk: <><b>Both arms</b> (all issues per call; one issue per call). 12 Jev and 11 Laya configurations; Laya fine-tuned.</>,
      trec: <><b>Both arms</b>, calibrated and bare-topic criteria. 12 Jev and 11 Laya configurations; Laya fine-tuned.</>,
    },
  },
];

const MEASURE_ROWS: [string, ReactNode][] = [
  ["Intervals", <mark><b>95% Wilson</b> score. Recall over the gold-positive set, precision over the flagged set; every document carries a gold label.</mark>],
  ["Level", <><b>Document</b>: responsive if positive for any issue. Decision: every (document, issue) judgment pooled. Single issue: that issue alone.</>],
  ["Label", <><b>The model's own label</b> (responsive when p ≥ 50%); no tuned threshold.</>],
  ["Subsets (*)", <>Rows scored on a <b>stratified subset</b> are marked *; intervals widen to match.</>],
  ["Time", <><b>Median</b> wall-clock per document, one request at a time, × 100,000. All-issues arm: one call per document; one-issue arm: the sum over issues.</>],
  ["Concurrency", <>Every service accepts parallel requests, so hours shrink for all rows alike; <b>compare ratios, not absolutes</b>.</>],
  ["Cost", <><b>As paid</b>: OpenAI on flex pricing (half of list); Anthropic with prompt caching on the all-issues arm; Google and TypeSafe at list.</>],
  ["GPU rows", <>Laya and Gemma 3 12B ran on a rented {GPU_NAME}: ${GPU_USD_PER_HOUR.toFixed(2)}/h (Lambda list, September 2026) × single-stream review time, <b>an upper bound</b>. Gemma via Ollama on 400–600-document subsets.</>],
  ["+ human time", <mark>{HUMAN_DEV_DOCS} documents at {HUMAN_DEV_DOCS_PER_HOUR}/h and ${HUMAN_DEV_USD_PER_HOUR}/h = <b>{fmtHours(HUMAN_DEV_HOURS)} and {fmtUSD(HUMAN_DEV_USD)}</b> of prompt or criteria development, once per 100k-document project, added to every row.</mark>],
  ["Determinism", <><b>300 Mallinckrodt emails</b> (100 gray, 100 clear positive, 100 clear negative) scored five times, both arms; the benchmark run is repeat one. Shown for every corpus.</>],
  ["Determinism metric", <><b>Probability that two runs disagree</b> on a decision (pairwise), 95% bootstrap interval over decisions. Temperature 0 where the API accepts it; Sonnet 5 rejects sampling parameters; Jev and Laya expose none.</>],
  ["Laya fine-tuned", <>RLCD recipe on a 30% document-level split of the same corpus (TREC: the 668-email calibration set), scored on the held-out rest. Its labeled data is <b>not counted in time or cost</b>.</>],
  ["Optimized configurations", <mark>Jev flat-string state and Laya compact + chunk (★) were selected on the <b>Veridian synthetic dev split</b> before any other corpus was scored.</mark>],
  ["Absent cells", "Some one-issue-per-call Laya configurations stalled and are omitted from that view."],
];

export function MethodModal({ onClose }: { onClose: () => void }) {
  return (
    <Modal className="method" eyebrow="Notes on method" title="How each experiment was run" onClose={onClose}>
      <div className="method-body">
        <table className="fact">
          <thead>
            <tr>
              <th scope="col">Data sets</th>
              {CORPORA.map((c) => <th key={c.id} scope="col">{c.label}<span className="fact-sub">{c.short}</span></th>)}
            </tr>
          </thead>
          <tbody>
            {DATASET_ROWS.map((r) => (
              <tr key={r.k}>
                <th scope="row">{r.k}</th>
                {CORPORA.map((c) => <td key={c.id}>{r.cells[c.id] ?? "—"}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
        <table className="fact two">
          <thead>
            <tr><th scope="col">Measurement</th><th scope="col">Every corpus</th></tr>
          </thead>
          <tbody>
            {MEASURE_ROWS.map(([k, v]) => <tr key={k}><th scope="row">{k}</th><td>{v}</td></tr>)}
          </tbody>
        </table>
      </div>
      <div className="ex-legend">
        <span>Counts are read from the same findings file as the charts.</span>
        <span>* on a chart row: scored on the subset named here.</span>
      </div>
    </Modal>
  );
}

/** The "Method" affordance: header slot and the foot of the page. */
export function MethodButton({ onClick }: { onClick: () => void }) {
  return <button type="button" className="ex-btn" onClick={onClick} title="How each experiment was run: data sets, truth data, measurement">Method</button>;
}
