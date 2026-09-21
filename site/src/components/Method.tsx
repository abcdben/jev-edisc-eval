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
const SUBSET_WHY: Record<string, string> = { "laya-ft": "held-out split", "gemma3-12b": "stratified subsample", "tar@cal": "10%-rich pool" };
/** "Laya 1,288 (held-out split)" for every headline row of a corpus that was scored on a subset (all-issues arm), then the corpus size. A decider's name carries the DECIDER tag (data.ts isDecider). */
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
  return <><N v={m.n_docs} /> · <N v={m.n_pos_docs_any} /> responsive to at least one issue (<N v={fmtPct(m.n_pos_docs_any / m.n_docs, 0)} />)</>;
}
function GrayCount({ id }: { id: string }) {
  const m = meta(id);
  return <><N v={sum(m.n_gray_by_issue)} /> of <N v={m.n_docs * m.n_issues} /> decisions</>;
}

const DATASET_ROWS: FactRow[] = [
  {
    k: "Source",
    cells: {
      mnk: "UCSF / JHU Opioid Industry Documents Archive, Mallinckrodt litigation collection: emails of 23 key custodians.",
      cuad: "CUAD v1 (Atticus Project, CC BY 4.0), official test split: 102 EDGAR commercial contracts.",
      trec: "TREC 2016 Total Recall, athome4: Jeb Bush gubernatorial email, 290,099 messages.",
    },
  },
  {
    k: "Documents scored",
    cells: { mnk: <DocsCell id="mnk" />, cuad: <DocsCell id="cuad" />, trec: <DocsCell id="trec" /> },
  },
  {
    k: "Unit · length",
    cells: {
      mnk: "One email with its headers; 300–12,000 characters (median ≈ 2,700).",
      cuad: "One contract paragraph with a title / position header; ≤ 3,000 characters (median ≈ 520).",
      trec: "One email with its headers; ≤ 12,000 characters (median ≈ 1,500).",
    },
  },
  {
    k: "Issues",
    cells: {
      mnk: <><N v={8} />: four broad / narrow pairs (suspicious order monitoring, marketing, distribution data, DEA) written for this study from the opioid MDL record.</>,
      cuad: <><N v={12} /> of CUAD's 41 clause categories, reframed as requests for production; license grant / non-transferable license form a broad / narrow pair.</>,
      trec: <><N v={12} /> of the 34 NIST topics; the official topic sentence is the request, verbatim.</>,
    },
  },
  {
    k: "Criteria",
    cells: {
      mnk: "RFP text, prose positive / negative descriptions, structured includes / excludes; identical for every model.",
      cuad: "Same forms; the 'literal' phrasing is CUAD's own category definition.",
      trec: "Refined once on a 668-email calibration set disjoint from evaluation (Jev and Gemini Flash-Lite on v0; shared misses read per topic). 'Bare topic' shows v0.",
    },
  },
  {
    k: "Truth data",
    cells: {
      mnk: "Provisional gold from a 3-LLM panel (Sonnet 5, GPT-5.6 Terra, Gemini 3.8 Flash), majority vote per decision; Jev and Laya never feed gold.",
      cuad: "Expert-highlighted spans. A paragraph is positive when it carries ≥ 50% of a span, or a span covers ≥ 50% of it.",
      trec: "NIST assessor judgments: rel 1 or 2 → responsive; judged non-relevant and unjudged → not responsive (TREC convention).",
    },
  },
  {
    k: "Gray (debatable)",
    cells: {
      mnk: <>Panel split, or mean p(responsive) in 0.35–0.65: <GrayCount id="mnk" />.</>,
      cuad: <>Overlaps a span below both 50% thresholds (a clause across a paragraph break): <GrayCount id="cuad" />.</>,
      trec: <>None from NIST; <GrayCount id="trec" /> flagged where a facet's gold contradicts the topic text (NRA / non-resident aliens).</>,
    },
  },
  {
    k: "Sampling",
    cells: {
      mnk: "Stratified: keyword-doped strata per issue pair, adjacent-product hard negatives, 700 random; near-duplicate threads thinned. Keyword strata are not labels.",
      cuad: "Every paragraph of the 102 test contracts.",
      trec: "Stratified from the collection: 100 gold positives per topic, 1,000 judged non-relevant, 1,000 random; excludes the calibration set and 696 documents read while exploring.",
    },
  },
  {
    k: "Subsets (*)",
    cells: Object.fromEntries(CORPORA.map((c) => [c.id, subsets(c.id)])),
  },
  {
    k: "What each model saw",
    cells: {
      mnk: "The email text with headers, the issue criteria, and a matter-background paragraph; returned a label and a probability.",
      cuad: "The excerpt with its header, the clause criteria, and a due-diligence background paragraph; label and probability.",
      trec: "The email text with headers, the topic criteria, and a public-records background paragraph; label and probability.",
    },
  },
  {
    k: "Runs",
    cells: {
      mnk: "Both arms (all issues per call; one issue per call). 12 Jev and 11 Laya configurations; Laya fine-tuned. TAR 1.0 at 100 / 300 / 1,000 coded; CAL on the 800-email pool, control set 300; 5 seeds.",
      cuad: "Both arms. 12 Jev and 10 Laya configurations; Laya fine-tuned. TAR 1.0 at 100 / 1,000 / 5,000 coded; CAL, control set 500; 5 seeds.",
      trec: "Both arms, calibrated and bare-topic criteria. 12 Jev and 11 Laya configurations; Laya fine-tuned. TAR over the full 286,326-email collection: TAR 1.0 at 100 / 1,000 / 5,000; CAL, control set 2,000 (fixed); 5 seeds (CAL 3).",
    },
  },
];

const MEASURE_ROWS: [string, ReactNode][] = [
  ["Intervals", "95% Wilson score. Recall over the gold-positive set, precision over the flagged set; every document carries a gold label."],
  ["Level", "Document: responsive if positive for any issue. Decision: every (document, issue) judgment pooled. Single issue: that issue alone."],
  ["Label", "The model's own label (responsive when p ≥ 50%); no tuned threshold."],
  ["Subsets (*)", "Rows scored on a stratified subset are marked *; intervals widen to match."],
  ["Time", "Median wall-clock per document, one request at a time, × 100,000. All-issues arm: one call per document; one-issue arm: the sum over issues."],
  ["Concurrency", "Every service accepts parallel requests, so hours shrink for all rows alike; compare ratios, not absolutes."],
  ["Cost", "As paid: OpenAI on flex pricing (half of list); Anthropic with prompt caching on the all-issues arm; Google and TypeSafe at list."],
  ["GPU rows", <>Laya and Gemma 3 12B ran on a rented {GPU_NAME}: ${GPU_USD_PER_HOUR.toFixed(2)}/h (Lambda list, September 2026) × single-stream review time, an upper bound. Gemma via Ollama on 400–600-document subsets.</>],
  ["+ human time", <>{HUMAN_DEV_DOCS} documents at {HUMAN_DEV_DOCS_PER_HOUR}/h and ${HUMAN_DEV_USD_PER_HOUR}/h = {fmtHours(HUMAN_DEV_HOURS)} and {fmtUSD(HUMAN_DEV_USD)} of prompt or criteria development, once per 100k-document project, added to every non-TAR row.</>],
  ["Determinism", "300 Mallinckrodt emails (100 gray, 100 clear positive, 100 clear negative) scored five times, both arms; the benchmark run is repeat one. Shown for every corpus."],
  ["Determinism metric", "Probability that two runs disagree on a decision (pairwise), 95% bootstrap interval over decisions. Temperature 0 where the API accepts it; Sonnet 5 rejects sampling parameters; Jev and Laya expose none. TAR is 0 by construction."],
  ["TAR reviewer", "Simulated from gold labels: 50 documents/hour, $65/hour; classifier compute not charged. Perfect reviewer in the TAR 1.0 rows; imperfect (misses 10% of relevant, over-codes 2% of non-relevant) in the CAL row. Both offered as variants."],
  ["TAR classifier", "TF-IDF (word 1–2-grams) + logistic regression, one model per issue and one for any-issue relevance."],
  ["TAR 1.0", "The reviewer codes a random sample; cutoff by 5-fold cross-validation on that sample alone, targeting 80% recall (or best F1). Median of 5 seeds."],
  ["TAR 2.0 (CAL)", "Imperfect reviewer codes a random control set first (never queued or trained on; counts as effort), then classifier-ranked batches. Stops when the control-set recall estimate is ≥ 80% for two consecutive batches."],
  ["CAL recall estimate", "A control document counts as reached once its score is at or above the lowest score queued in a batch; conservative with an imperfect reviewer (over-coded control documents are never 'found')."],
  ["CAL plotted set", "Production set: every document the reviewer coded relevant, control set included, scored against gold on the pool CAL ran over. Tooltip: reviewed count, control set, estimated vs true recall, review-set precision, classifier alone on the eval set."],
  ["CAL on Mallinckrodt", "The sample is 61% rich by design, so CAL runs on a 10%-rich pool of 800 emails (all gold-negatives + 80 random positives per seed); control set 300."],
  ["CAL ablations", "75% target; perfect reviewer; knee-method stop (Cormack & Grossman 2016, no control set)."],
  ["Laya fine-tuned", "RLCD recipe on a 30% document-level split of the same corpus (CUAD split by contract; TREC: the 668-email calibration set), scored on the held-out rest. Its labeled data is not counted in time or cost."],
  ["Optimized configurations", "Jev flat-string state and Laya compact + chunk (★) were selected on the Veridian synthetic dev split before any other corpus was scored."],
  ["Absent cells", "Some one-issue-per-call Laya configurations stalled and are omitted from that view. The fine-tuned Laya checkpoint on CUAD collapsed to a constant negative and is shown as such."],
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
