import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  base: "./",
  server: { fs: { allow: [path.resolve(root, "..")] } },
  build: { outDir: "dist", emptyOutDir: true },
});
