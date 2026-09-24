import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { fs: { allow: [path.resolve(root, "..")] } },
  // Four pages: the site (index.html), its B variant with the Compare models charts as full-width tabs (b.html → src/b.tsx → src/AppB.tsx; links back
  // to A, A does not link to it), the unlinked screenshot studio (studio.html → src/studio.tsx → src/StudioPage.tsx) and the unlinked
  // cutoff explorer (cutoffs.html → src/cutoffs.tsx → src/CutoffsPage.tsx; its data, public/cutoffs.json, is fetched by the page, not bundled).
  build: { outDir: "dist", emptyOutDir: true, rollupOptions: { input: { main: path.resolve(root, "index.html"), b: path.resolve(root, "b.html"), studio: path.resolve(root, "studio.html"), cutoffs: path.resolve(root, "cutoffs.html") } } },
});
