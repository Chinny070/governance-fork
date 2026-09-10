import { defineConfig } from "vitest/config";

// Standalone test config — the unit tests cover pure logic (receipt
// classification, formatting, enum/lineage helpers) and need no Vite plugins.
export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
});
