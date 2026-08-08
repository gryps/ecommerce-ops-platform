import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/workbench/",
  build: {
    outDir: "../../ops-workbench-runtime/static-workbench",
    emptyOutDir: true,
  },
});
