import { expect, test, type Page } from "@playwright/test";

/** Rule learning e2e — replay fixture, không tự kích hoạt. */

async function loginAs(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
}

test.describe("Quan tu viet luat", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
    await page.goto("/quanverse/rules");
  });

  test("discover -> evidence -> shadow -> confirm, no auto activation", async ({ page }) => {
    // Tìm quyết định lặp lại.
    await page.getByTestId("rules-discover").click();
    await expect(page.locator(".nq-rules__item")).toHaveCount(1, { timeout: 15_000 });

    // Bằng chứng.
    await page.getByTestId("evidence-btn").first().click();
    await expect(page.locator(".nq-drawer")).toBeVisible();
    await page.getByRole("button", { name: "Đóng" }).click();

    // Shadow test → confirm enabled.
    await page.getByTestId("shadow-btn").first().click();
    await expect(page.locator(".nq-shadow")).toBeVisible({ timeout: 10_000 });

    // Confirm chỉ sau shadow; không tự kích hoạt.
    await page.getByTestId("confirm-btn").first().click();
    await expect(page.locator(".nq-alert--info")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/AI đề xuất, quản lý quyết định/)).toBeVisible();
  });

  test("reject candidate without activation", async ({ page }) => {
    await page.getByTestId("rules-discover").click();
    await expect(page.locator(".nq-rules__item")).toHaveCount(1, { timeout: 15_000 });
    await page.getByTestId("reject-btn").first().click();
    await expect(page.locator(".nq-alert--info")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(".nq-rules__item").first()).toContainText("rejected");
  });
});