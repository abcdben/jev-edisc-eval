import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./styles.css";

// Entry for compare.html: the comparison app (App.tsx; Compare models, Compare configurations and Trade-off in the hash). The root, index.html, is the landing page (landing.tsx).
createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
