import { useCallback, useEffect, useState } from "react";
import { Modal } from "./ui";

/**
 * First-visit disclaimer: what these numbers are and are not. Shown once, after the page has painted, and remembered in
 * localStorage under ACK_KEY so it never reopens on that browser; the footer's "Disclaimer" link brings it back on demand.
 */

/** Where "contact" points. The author's address from the repository's git config; no other public contact is published in the repo. */
const CONTACT_HREF = "mailto:abcdben@gmail.com";
const CONTACT_LABEL = "email";

const ACK_KEY = "disclaimer_ack_v2";

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
    <Modal className="disclaimer" eyebrow="Status of this work" title="Preliminary results" onClose={onClose}>
      <div className="disc-body">
        <p>
          This is a working study. The evaluations were designed and run carefully, and the findings seemed important enough to share now,
          but they have not been independently replicated or peer reviewed and should be read as preliminary.
        </p>
        <p>
          The figures describe how a set of decision models, language models and classical TAR workflows performed on three specific corpora
          under specific conditions: particular issue criteria, gold labels, configurations, pricing modes and samples. Changing any of these
          would change the results. They are a snapshot for orientation, not a forecast of what any model will do on your matter, and not a
          claim of general superiority.
        </p>
        <p>
          Where a result looks surprising, assume there is a reason in the method before assuming it is a finding. The Method table lists
          the main choices, and the details view on any row shows exactly what that model was asked.
        </p>
        <p>
          Questions, corrections and requests for the underlying data are welcome: <a href={CONTACT_HREF}>{CONTACT_LABEL}</a>.
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
