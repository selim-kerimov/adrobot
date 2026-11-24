import path from "node:path";

import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "./src") },
  },
  build: {
    rolldownOptions: {
      output: {
        // Libraries change less often than our code, so they get their own cacheable chunks.
        codeSplitting: {
          groups: [
            {
              name: "react",
              test: /node_modules[\\/](react|react-dom|react-router|scheduler)[\\/]/,
            },
            { name: "radix", test: /node_modules[\\/](radix-ui|@radix-ui|cmdk)[\\/]/ },
            { name: "forms", test: /node_modules[\\/](react-hook-form|@hookform|zod)[\\/]/ },
            { name: "vendor", test: /node_modules[\\/]/ },
          ],
        },
      },
    },
  },
  server: {
    port: 5180,
    strictPort: true,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
