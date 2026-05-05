import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Per build/02-web-boundary the frontend is a thin client over the
// Rust server. We proxy /api requests to the local pdftr-server.
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            "/api": {
                target: "http://127.0.0.1:7878",
                changeOrigin: true
            }
        }
    }
});
