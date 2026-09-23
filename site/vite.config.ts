import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { fs: { allow: [path.resolve(root, "..")] } },
  // Two pages: the site (index.html) and the unlinked screenshot studio (studio.html → src/studio.tsx → src/StudioPage.tsx).
  build: { outDir: "dist", emptyOutDir: true, rollupOptions: { input: { main: path.resolve(root, "index.html"), studio: path.resolve(root, "studio.html") } } },
});
