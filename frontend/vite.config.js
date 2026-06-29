import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * The PocketBase SDK declares a class method literally named `import`
 * (`async import(...)`). Vite's dev-time import analysis (es-module-lexer)
 * misreads `import(` as a dynamic import() and rewrites the argument list,
 * producing invalid JS that crashes the app in dev (the production rollup
 * build is unaffected).
 *
 * This pre-transform rewrites the method to a computed key `["import"]`, which
 * is functionally identical (`pb.collection().import()` still works) but is no
 * longer mistaken for a dynamic import.
 */
function pocketbaseImportMethodFix() {
  return {
    name: 'pocketbase-import-method-fix',
    enforce: 'pre',
    transform(code, id) {
      if (id.includes('node_modules/pocketbase') && code.includes('async import(')) {
        return { code: code.replace(/async import\(/g, 'async ["import"]('), map: null };
      }
      return null;
    },
  };
}

export default defineConfig({
  plugins: [pocketbaseImportMethodFix(), react()],
  // Skip pre-bundling so the fix above runs on PocketBase's served source.
  optimizeDeps: {
    exclude: ['pocketbase'],
  },
  server: {
    port: 3000,
    host: true,
    // Allow the dev server to be reached through the Caddy reverse proxy on
    // any <tenant>.angeallvet.localhost sub-domain.
    allowedHosts: ['.angeallvet.localhost', 'localhost', '127.0.0.1'],
  },
  build: {
    outDir: 'build',
  },
});
