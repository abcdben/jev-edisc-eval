import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import StudyPage from "./StudyPage";
import "./styles.css";
import "./study.css";

// Entry for study.html (the human-anchored study: datasets × experiments × arms from results/study.json). Lower-case so it cannot collide with
// StudyPage.tsx on a case-insensitive filesystem.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <StudyPage />
  </StrictMode>,
);
