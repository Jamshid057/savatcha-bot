/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Dev: API va rasmlar FastAPI ga proksi qilinadi (docker-compose yoki uvicorn :8000)
    proxy: {
      "/api": "http://localhost:8000",
      "/files": "http://localhost:8000",
    },
  },
  test: { environment: "node" },
});
