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
    <Modal className="disclaimer" eyebrow="About this comparison" title="Decision models against LLMs for relevance review" onClose={onClose}>
      <div className="disc-body">
        <h4>What was tested</h4>
        <p>
          <b>Two new decision models</b>, Jev (TypeSafe AI) and Laya (ConvAI), against <b>seven commercially available language models</b>: Haiku 4.5,
          Sonnet 5, GPT‑5.6 Luna and Terra, Gemini 3.5 Flash‑Lite and 3.8 Flash, and a locally run Gemma 3 12B. <b>Classical TAR</b> is included
          for reference: a simulated reviewer with TF‑IDF and logistic regression, as TAR 1.0 at several training-sample sizes, the reviewer's training sample drawn by cluster-stratified diversity sampling rather than at random. The task is the one review teams do in discovery: <mark>is this document responsive, and to which issues.</mark>
        </p>
        <h4>Data sets</h4>
        <ul>
          <li><b>Mallinckrodt</b>: 1,840 emails from the opioid litigation archive; eight issues written for this study in broad and narrow pairs; gold labels from a three‑model panel.</li>
          <li><b>CUAD</b>: 6,494 paragraphs from 102 commercial contracts; twelve clause types framed as requests; expert annotations as gold.</li>
          <li><b>TREC 2016</b>: 3,116 emails drawn from the 286,000‑message Jeb Bush collection; twelve NIST topics; assessor judgments as gold.</li>
        </ul>
        <h4>Set‑up</h4>
        <p>
          Every model saw the <b>same document text, issue criteria and matter context</b>, and returned a label with a 0–1 score: a model
          probability for the decision models, a self‑reported confidence for the LLMs. Compared:
        </p>
        <ul>
          <li><b>Recall and precision</b>, with 95% confidence intervals.</li>
          <li><b>Review time</b> per 100,000 documents in a single stream.</li>
          <li><b>Cost</b> per 100,000 documents, as paid.</li>
          <li><b>Determinism</b>: how often a model changes its answer on the same document across repeated runs.</li>
        </ul>
        <h4>What this is</h4>
        <p>
          The same criteria, documents and scoring were applied to every model, and nothing was tuned against the test data; even so,
          <mark>assumptions and decisions were made that are not documented on this site</mark>, and each result rests on choices about criteria,
          configurations, pricing and sampling that could shift on another matter. <b>This is not meant as a peer‑reviewed study</b> so much as
          <mark>a point‑in‑time snapshot of model performance on established industry data sets</mark>, showing where these new decision models
          stand on review tasks next to the models people already use.
        </p>
        <p>
          Questions, corrections and requests for the underlying data are welcome: <a href={CONTACT_HREF}>{CONTACT_LABEL}</a>.
        </p>
        <button type="button" className="disc-ok" onClick={onClose}>Understood</button>
        <div className="disc-note">You can reopen this from "About this comparison" at the foot of the page.</div>
      </div>
    </Modal>
  );
}

/** The footer's "Disclaimer" text link, beside the Method button. */
export function DisclaimerLink({ onClick }: { onClick: () => void }) {
  return <button type="button" className="disc-link" onClick={onClick} title="What was tested, on which data, and what this comparison is and is not">About this comparison</button>;
}
