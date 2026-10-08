import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));

const input: Record<string, string> = {
  landing: path.resolve(root, "index.html"),
  main: path.resolve(root, "compare.html"),
  b: path.resolve(root, "b.html"),
  studio: path.resolve(root, "studio.html"),
  study: path.resolve(root, "study.html"),
  explore: path.resolve(root, "explore.html"),
};
// Optional local page: included only when its HTML entry is on disk. A clone without that file still builds the published site.
const localPage = path.resolve(root, "cutoffs.html");
if (fs.existsSync(localPage)) input.cutoffs = localPage;

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { fs: { allow: [path.resolve(root, "..")] } },
  // The landing page (index.html → src/landing.tsx → src/LandingPage.tsx) lists the pages; index.html also forwards the comparison app's old hash
  // links (#compare, #configurations, #tradeoff: the app used to be the root) to compare.html. The comparison app (compare.html → src/main.tsx →
  // src/App.tsx), its B variant with the Compare models charts as full-width tabs (b.html → src/b.tsx → src/AppB.tsx; links back to A, A does not
  // link to it), the unlinked screenshot studio (studio.html → src/studio.tsx → src/StudioPage.tsx), the study (study.html) and the explorer (explore.html).
  build: { outDir: "dist", emptyOutDir: true, rollupOptions: { input } },
});
