import { defineConfig } from '@playwright/test';
const production = process.env.DBM_TEST_PRODUCTION === '1';
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,
  use: { baseURL: 'http://localhost:4173', viewport: { width: 1440, height: 1000 } },
  webServer: [
    { env: { API_INTERNAL_URL: 'http://127.0.0.1:18000', PORT: '4173', HOST: '127.0.0.1', ORIGIN: 'http://localhost:4173', NODE_ENV: production ? 'production' : 'development' }, command: production ? 'bun build/index.js' : 'bun run dev --port 4173 --strictPort', url: 'http://localhost:4173', reuseExistingServer: false },
    { command: 'cd ../.. && ALLOW_DEV_LOGIN=1 PORT=18000 PUBLIC_ORIGIN=http://localhost:4173 DATABASE_URL=sqlite:////tmp/dbm-browser-tests.db sh scripts/dev-api.sh', url: 'http://127.0.0.1:18000/api/health', reuseExistingServer: false }
  ]
});
