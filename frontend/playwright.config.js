import { defineConfig, devices } from '@playwright/test';

/**
 * End-to-end regression tests.
 *
 * The tests are hermetic: the backend API and PocketBase are stubbed with
 * `page.route` (see e2e/helpers.js), so no database, backend or PocketBase
 * instance is required. Playwright only needs to serve the built SPA, which it
 * does via the Vite dev server below.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      VITE_API_URL: 'http://localhost:8000/api/v1',
      VITE_POCKETBASE_URL: 'http://127.0.0.1:8090',
    },
  },
});
