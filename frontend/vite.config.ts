import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import { fileURLToPath } from 'url';
import pkg from './package.json';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  plugins: [react()],
  define: {
    'import.meta.env.VITE_APP_VERSION': JSON.stringify(pkg.version),
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // The frontend's Docker image always serves a static nginx build (see
      // docker-compose.yml) — it never runs the Vite dev server in-container,
      // so this proxy only ever runs on a developer's host via `npm run dev`
      // (see docker-compose.dev.yml's comment). `backend` is a Docker-network
      // hostname and doesn't resolve from the host; the backend's dev compose
      // override exposes it on localhost:8000 for exactly this.
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Mirrors frontend/nginx.conf: the landing page's probe path maps onto
      // the MCP container's own /health, and /mcp is the endpoint itself.
      // Both only answer if the MCP server runs on the host (`uvicorn
      // server:app --port 8001` from mcp/); the dev compose stack does not
      // publish its port. Without it the section stays hidden, exactly as on
      // a deployment without the `mcp` profile.
      '/mcp/health': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        rewrite: () => '/health',
      },
      '/mcp': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
});
