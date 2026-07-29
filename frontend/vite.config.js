import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Vite configuration forcing frontend to run on port 5172
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5172,
    strictPort: true,
    host: true
  },
  preview: {
    port: 5172,
    strictPort: true
  }
});
