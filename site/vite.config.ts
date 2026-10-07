import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import fs from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));

const input: Record<string, string> = {
  main: path.resolve(root, "index.html"),
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
  // Three pages: the site (index.html), its B variant with the Compare models charts as full-width tabs (b.html → src/b.tsx → src/AppB.tsx; links back
  // to A, A does not link to it), and the unlinked screenshot studio (studio.html → src/studio.tsx → src/StudioPage.tsx).
  build: { outDir: "dist", emptyOutDir: true, rollupOptions: { input } },
});
