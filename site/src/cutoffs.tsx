import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import CutoffsPage from "./CutoffsPage";
import "./styles.css";

// Entry for cutoffs.html (the unlinked per-issue cutoff explorer). Lower-case and distinct from CutoffsPage.tsx: on a case-insensitive
// filesystem `cutoffs.tsx` and `Cutoffs.tsx` would be one file.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <CutoffsPage />
  </StrictMode>,
);
