import { expect, test, type Page } from "@playwright/test";

/** QUANVERSE e2e — role projection, mode confirm, flavor, AR fallback. */

async function loginAs(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
}

test.describe("QUANVERSE", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
    await page.goto("/quanverse");
  });

  test("living map renders zones and events", async ({ page }) => {
    await expect(page.locator(".nq-living-map")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("zone-bar")).toBeVisible();
    await expect(page.locator(".nq-quanverse__events")).toBeVisible();
  });

  test("role switch (replay) changes projection", async ({ page }) => {
    await expect(page.locator(".nq-living-map")).toBeVisible({ timeout: 15_000 });
    // Switch sang khách → không còn sự kiện staff.
    await page.getByTestId("role-khach").click();
    await expect(page.getByText(/Không có sự kiện vận hành cho bản chiếu này/)).toBeVisible({ timeout: 10_000 });
  });

  test("manager confirms mode", async ({ page }) => {
    await expect(page.locator(".nq-living-map")).toBeVisible({ timeout: 15_000 });
    // quan_yen_tinh chưa active trong fixture — confirm để bật.
    await page.getByTestId("mode-confirm-quan_yen_tinh").first().click();
    await expect(page.locator(".nq-moderail__item.is-active").first()).toBeVisible({ timeout: 10_000 });
  });

  test("flavor recommendation with reasons", async ({ page }) => {
    await expect(page.locator(".nq-flavor")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("flavor-ngot").selectOption("it");
    await page.getByTestId("flavor-sua").uncheck();
    await page.getByTestId("flavor-go").click();
    await expect(page.getByTestId("flavor-results").first()).toBeVisible({ timeout: 10_000 });
  });

  test("ar-lite fallback path", async ({ page }) => {
    await expect(page.locator(".nq-ar")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("ar-qr").fill("blender-02");
    await page.getByTestId("ar-start").click();
    await expect(page.getByTestId("ar-result")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("ar-result")).toContainText("map_or_qr_text");
  });
});