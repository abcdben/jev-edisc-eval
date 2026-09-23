import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import StudioPage from "./StudioPage";
import "./styles.css";

// Entry for studio.html (the unlinked screenshot studio). Kept lower-case and distinct from StudioPage.tsx: on a case-insensitive filesystem
// `studio.tsx` and `Studio.tsx` would be one file.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <StudioPage />
  </StrictMode>,
);
