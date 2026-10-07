import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import ExplorePage from "./ExplorePage";
import "./styles.css";
import "./study.css";
import "./explore.css";

// Entry for explore.html (the population explorer: every judged document of a collection, cut by who called it responsive; static rows and
// scores from public/explore/, text from `bench serve`). Lower-case so it cannot collide with ExplorePage.tsx on a case-insensitive filesystem.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ExplorePage />
  </StrictMode>,
);
