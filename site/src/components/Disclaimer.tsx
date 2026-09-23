import { useCallback, useEffect, useState } from "react";
import { Modal } from "./ui";

/**
 * First-visit disclaimer: what these numbers are and are not. Shown once, after the page has painted, and remembered in
 * localStorage under ACK_KEY so it never reopens on that browser; the footer's "Disclaimer" link brings it back on demand.
 */

/** Where "contact" points. The author's address from the repository's git config; no other public contact is published in the repo. */
const CONTACT_HREF = "mailto:abcdben@gmail.com";
const CONTACT_LABEL = "email";

const ACK_KEY = "disclaimer_ack_v3";

const read = () => { try { return localStorage.getItem(ACK_KEY) === "1"; } catch { return true; } };
const write = () => { try { localStorage.setItem(ACK_KEY, "1"); } catch { /* private mode: show again next visit */ } };

/** App owns the open state through this hook: `open` after first paint on an unacknowledged browser; `show` from the footer; `close` acknowledges. */
export function useDisclaimer() {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    if (read()) return;
    // two frames after mount, so the charts are on screen before the backdrop dims them
    let f2 = 0;
    const f1 = requestAnimationFrame(() => { f2 = requestAnimationFrame(() => setOpen(true)); });
    return () => { cancelAnimationFrame(f1); cancelAnimationFrame(f2); };
  }, []);
  const show = useCallback(() => setOpen(true), []);
  const close = useCallback(() => { write(); setOpen(false); }, []);
  return { open, show, close };
}

export function DisclaimerModal({ onClose }: { onClose: () => void }) {
  return (
    <Modal className="disclaimer" eyebrow="About this comparison" title="A zero-shot bake-off: decision models against LLMs on relevance review" onClose={onClose}>
      <div className="disc-body">
        <h4>What was tested</h4>
        <p>
          <b>A zero‑shot comparison</b> of <b>two new decision models</b>, Jev (TypeSafe AI) and Laya (ConvAI), against <b>seven commercially available
          language models</b>: Haiku 4.5, Sonnet 5, GPT‑5.6 Luna and Terra, Gemini 3.5 Flash‑Lite and 3.8 Flash, and a locally run Gemma 3 12B. No model
          was trained on examples or given a prompt of its own. The task is relevance review, the one review teams do in discovery: <mark>is this document
          responsive, and to which issues.</mark>
        </p>
        <h4>Data sets</h4>
        <ul>
          <li><b>Mallinckrodt</b>: 1,840 emails from the opioid litigation archive; eight issues written for this study in broad and narrow pairs; gold labels from a three‑model panel.</li>
          <li><b>TREC 2016</b>: 3,016 emails drawn from the 286,000‑message Jeb Bush collection; eleven NIST topics; assessor judgments as gold.</li>
        </ul>
        <h4>Set‑up</h4>
        <p>
          Every model received the <b>same issue criteria and matter context</b> and was scored the same way, and every model but Laya saw the
          <b> same document text</b>: Laya's 512‑token window received condensed one‑sentence criteria and the document in pieces, scored piece by
          piece. Gemma and the fine‑tuned Laya row were scored on stratified subsets of the same population (the * on their names), so their intervals
          are wider. Each model returned a label with a 0–1 score: a model probability for the decision models, a self‑reported confidence for the
          LLMs. Compared:
        </p>
        <ul>
          <li><b>Recall and precision</b>, with 95% confidence intervals.</li>
          <li><b>Speed</b>: median latency to score one document, one request at a time.</li>
          <li><b>Cost</b> per 100,000 documents, as paid, at each corpus's average document length.</li>
          <li><b>Stability</b>: how often a model changes its answer on the same document across repeated identical runs (lower is more stable).</li>
        </ul>
        <p>
          <b>Zero‑shot means nothing was iterated.</b> In practice a review team refines its criteria against sample documents many times before
          scoring a population; here <mark>every model received the criteria as written, once, through a single shared prompt that was not tuned for
          any model</mark>. The one exception on the criteria is TREC, where the NIST topic sentences were refined once on a 668‑email calibration set
          disjoint from the evaluation set, and the refined wording was then given to every model alike. <b>The one exception to zero‑shot is the Laya
          row</b>: it is a fine‑tuned checkpoint that learned from a labelled split of each corpus, the single supervised row on the site; its prompt was
          not iterated either, and Laya's zero‑shot configurations are on the Configurations page. The figures therefore compare models on like inputs;
          they are <b>not a ceiling on what any model can do</b> with a tuned workflow.
        </p>
        <h4>What this is</h4>
        <p>
          <mark>This is a point‑in‑time snapshot of a zero‑shot bake‑off on established industry data sets</mark>, showing where these new decision
          models stand on relevance review next to the models people already use. The same criteria and scoring were applied to every model, and
          nothing was tuned against the test data; even so, <mark>assumptions and decisions were made that are not documented on this site</mark>, and
          each result rests on choices about criteria, configurations, pricing and sampling that could shift on another matter.
          <b>It is not meant as a peer‑reviewed study.</b>
        </p>
        <p>
          Questions, corrections and requests for the underlying data are welcome: <a href={CONTACT_HREF}>{CONTACT_LABEL}</a>.
        </p>
        <div className="disc-note">You can reopen this from "About this comparison" at the foot of the page.</div>
      </div>
    </Modal>
  );
}

/** The footer's "Disclaimer" text link, beside the Method button. */
export function DisclaimerLink({ onClick }: { onClick: () => void }) {
  return <button type="button" className="disc-link" onClick={onClick} title="What was tested, on which data, and what this comparison is and is not">About this comparison</button>;
}
