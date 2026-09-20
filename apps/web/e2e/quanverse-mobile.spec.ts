import { expect, test } from "@playwright/test";

/** QUANVERSE mobile e2e — 390x844 (chromium project chỉ định trong config). */

test.use({
  viewport: { width: 390, height: 844 },
  isMobile: true,
  hasTouch: true,
});

test.describe("QUANVERSE mobile", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/login");
    await page.getByLabel("Tài khoản").fill("lan");
    await page.getByLabel("Mật khẩu").fill("nhipquan");
    await page.getByRole("button", { name: "Vào hệ thống" }).click();
    await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
  });

  test("living map renders without horizontal overflow", async ({ page }) => {
    await page.goto("/quanverse");
    await expect(page.locator(".nq-living-map")).toBeVisible({ timeout: 15_000 });

    // Không overflow ngang ở viewport mobile
    const overflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > window.innerWidth;
    });
    expect(overflow).toBe(false);

    // Zone vẫn tương tác được
    await page.getByTestId("zone-bar").click();
  });

  test("flavor + mode actions accessible on mobile", async ({ page }) => {
    await page.goto("/quanverse");
    await expect(page.locator(".nq-living-map")).toBeVisible({ timeout: 15_000 });

    // Flavor input vẫn dùng được (touch target)
    await page.getByTestId("flavor-ngot").selectOption("it");
    await page.getByTestId("flavor-go").click();
    await expect(page.getByTestId("flavor-results").first()).toBeVisible({ timeout: 10_000 });
  });
});