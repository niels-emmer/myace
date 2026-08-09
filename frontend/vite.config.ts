import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
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
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
  },
});
