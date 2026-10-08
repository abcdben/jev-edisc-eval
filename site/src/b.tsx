import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import AppB from "./AppB";
import "./styles.css";

// Entry for b.html: variant B of the site (AppB.tsx), the dashboard with the Compare models charts as full-width tabs, for an A/B comparison
// with compare.html. Lower-case and distinct from AppB.tsx: on a case-insensitive filesystem `b.tsx` and `B.tsx` would be one file.
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <AppB />
  </StrictMode>,
);
