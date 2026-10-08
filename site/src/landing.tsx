import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import LandingPage from "./LandingPage";
import "./styles.css";

// Entry for index.html (the site root): the landing page listing the site's pages (LandingPage.tsx). The comparison app itself is compare.html
// (main.tsx). Lower-case so it cannot collide with LandingPage.tsx on a case-insensitive filesystem.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <LandingPage />
  </StrictMode>,
);
