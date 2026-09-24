import { expect, test } from "@playwright/test";

test("index -> pair -> split step visible", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Where did the failing run go wrong?" })).toBeVisible();
  await page.locator("table a").first().click();
  await expect(page.getByRole("region", { name: "Aligned runs" })).toBeVisible();
  // The judge's split step when judged, the alignment's candidate otherwise.
  await expect(page.locator('[data-tone="split"], [data-tone="candidate"]').first()).toBeVisible();
});

test("findings and label mode load", async ({ page }) => {
  await page.goto("/findings/");
  await expect(page.getByRole("heading", { name: "Findings" })).toBeVisible();
  await page.goto("/label/");
  await expect(page.getByText(/Pair 1 of \d+/)).toBeVisible();
  await expect(page.getByTestId("judge-card")).toHaveCount(0);
});
