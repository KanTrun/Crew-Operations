import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: "list",
  timeout: 60_000,
  use: {
    baseURL: "http://localhost:3001",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: "python ../../scripts/demo_api.py",
      url: "http://127.0.0.1:8000/health",
      cwd: __dirname,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: {
        NHIPQUAN_API_HOST: "0.0.0.0",
        NHIPQUAN_API_PORT: "8000",
        NHIPQUAN_DISABLE_RATE_LIMIT: "true",
      },
    },
    {
      command: "npx next start -p 3001",
      url: "http://localhost:3001",
      cwd: __dirname,
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        NEXT_PUBLIC_API_URL: "http://127.0.0.1:8000",
      },
    },
  ],
});
