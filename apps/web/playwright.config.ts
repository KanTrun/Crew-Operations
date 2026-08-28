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
      url: "http://localhost:8000/health",
      cwd: __dirname,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npx next start -p 3001",
      url: "http://localhost:3001",
      cwd: __dirname,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
