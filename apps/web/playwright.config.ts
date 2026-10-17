import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  use: { baseURL: 'http://localhost:5173', viewport: { width: 1440, height: 1000 } },
  webServer: [
    { command: 'bun run dev --port 5173', url: 'http://localhost:5173', reuseExistingServer: !process.env.CI },
    { command: 'cd ../.. && ALLOW_DEV_LOGIN=1 DATABASE_URL=sqlite:////tmp/dbm-browser-tests.db sh scripts/dev-api.sh', url: 'http://127.0.0.1:8000/api/health', reuseExistingServer: !process.env.CI }
  ]
});
