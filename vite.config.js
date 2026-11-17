import { defineConfig } from 'vite';

// Three pages: the seat map (index.html), the management portal (admin.html) and the sports-complex tour (tour.html).
export default defineConfig({
  // stamped into model and texture addresses, so a new deploy is never mixed with files a browser cached from the last one
  define: { __BUILD__: JSON.stringify(String(Date.now())) },
  build: {
    target: 'es2022', // the code uses top-level await
    chunkSizeWarningLimit: 1200,
    rollupOptions: { input: { main: 'index.html', admin: 'admin.html', tour: 'tour.html' } },
  },
});
