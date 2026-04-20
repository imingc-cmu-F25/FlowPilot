import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      "/api": {
        // Override via VITE_API_PROXY_TARGET for Docker (http://backend:8000)
        // or any non-default backend host.
        target: process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
