import { expect, test, type Page } from "@playwright/test";

/** Shift Rescue e2e — replay fixture, không mạng/LLM thật. */

async function loginAs(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
}

test.describe("Shift Rescue", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
    await page.goto("/quanverse/shift-rescue");
  });

  test("manager resolves absence in under 90s, safe candidates shown", async ({ page }) => {
    const start = Date.now();

    // Báo vắng → tìm người bù (dùng class/data-testid, tránh mojibake).
    await page.getByTestId("rescue-intake").click();
    await expect(page.locator(".nq-rescue__case")).toBeVisible({ timeout: 15_000 });

    // Ít nhất 1 candidate an toàn hiển thị.
    const safe = await page.locator(".nq-candidate:not(.is-blocked)").count();
    expect(safe).toBeGreaterThanOrEqual(1);

    // Mời ứng viên đầu tiên (data-testid).
    await page.getByTestId("invite-btn").first().click();
    await expect(page.locator(".nq-alert--info")).toBeVisible({ timeout: 10_000 });

    const elapsed = (Date.now() - start) / 1000;
    expect(elapsed).toBeLessThan(90);
  });

  test("no unsafe recommend: blocked candidates never have invite button", async ({ page }) => {
    await page.getByTestId("rescue-intake").click();
    await expect(page.locator(".nq-rescue__case")).toBeVisible({ timeout: 15_000 });

    // Nút invite chỉ nằm trong candidate an toàn (không blocked).
    const blockedInvites = await page
      .locator(".nq-candidate.is-blocked [data-testid='invite-btn']")
      .count();
    expect(blockedInvites).toBe(0);
  });
});