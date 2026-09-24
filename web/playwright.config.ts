import { defineConfig } from "@playwright/test";

const PORT = 3218;

export default defineConfig({
  testDir: "e2e",
  use: { baseURL: `http://localhost:${PORT}`, channel: "chrome" },
  webServer: {
    command: `pnpm exec serve out -l ${PORT} --no-clipboard`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: false,
  },
});
