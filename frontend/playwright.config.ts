import { defineConfig, devices } from '@playwright/test'

const webPort = 15173
const apiPort = 18000

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  outputDir: 'test-results/artifacts',
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    ...devices['Desktop Chrome'],
  },
  webServer: [
    {
      command: `uv run uvicorn e2e_app:app --app-dir ../tests --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/openapi.json`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: `npm run dev -- --config vite.e2e.config.ts --host 127.0.0.1 --port ${webPort}`,
      url: `http://127.0.0.1:${webPort}/create`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
})
