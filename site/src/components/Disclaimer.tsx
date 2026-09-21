import { useCallback, useEffect, useState } from "react";
import { Modal } from "./ui";

/**
 * First-visit disclaimer: what these numbers are and are not. Shown once, after the page has painted, and remembered in
 * localStorage under ACK_KEY so it never reopens on that browser; the footer's "Disclaimer" link brings it back on demand.
 */

/** Where "contact" points. The author's address from the repository's git config; no other public contact is published in the repo. */
const CONTACT_HREF = "mailto:abcdben@gmail.com";
const CONTACT_LABEL = "email";

const ACK_KEY = "disclaimer_ack_v1";

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
    <Modal className="disclaimer" eyebrow="Disclaimer" title="Before you read the numbers" onClose={onClose}>
      <div className="disc-body">
        <p>
          These evaluations were run with care. Their purpose was a snapshot of how new decision models stack up against LLMs and classical TAR
          on document review tasks, not a conclusive judgement and not a formal academic comparison.
        </p>
        <p>
          The results are meaningful, but they are not what you should expect on your own matter. Many inputs and choices went into them:
          how each corpus was built, how gold labels were made, the criteria, the configurations, the pricing modes, the sampling. A reader
          may not be aware of all of them. The Method table describes the main ones.
        </p>
        <p>
          Questions are welcome, and I am happy to share more. You can reach me by <a href={CONTACT_HREF}>{CONTACT_LABEL}</a>.
        </p>
        <button type="button" className="disc-ok" onClick={onClose}>Understood</button>
        <div className="disc-note">You can reopen this from the footer.</div>
      </div>
    </Modal>
  );
}

/** The footer's "Disclaimer" text link, beside the Method button. */
export function DisclaimerLink({ onClick }: { onClick: () => void }) {
  return <button type="button" className="disc-link" onClick={onClick} title="What these numbers are and are not">Disclaimer</button>;
}
