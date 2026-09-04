import { test, expect, type Page } from "@playwright/test";

/** Đo latency mở form phiếu (UI), không phải thời gian hoàn thành checklist (#7 nhóm A). */

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
}

test.describe("Phiếu demo — latency mở form (#7 nhóm A)", () => {
  test("thời gian mở form phiếu đến bước đầu (fixture)", async ({ page }) => {
    await login(page);
    const t0 = Date.now();
    await page.goto("/phieu");
    await expect(page.getByRole("heading", { name: "Mở phiếu", exact: true })).toBeVisible();
    const startBtn = page.getByRole("button", { name: /Mở quán|Phiếu/i }).first();
    if (await startBtn.isVisible()) {
      await startBtn.click();
      await expect(page.getByText(/bước/i).first()).toBeVisible({ timeout: 15_000 });
    }
    const elapsed_ms = Date.now() - t0;
    console.log(`PHIEU_DEMO_MS=${elapsed_ms}`);
    expect(elapsed_ms).toBeLessThan(30_000);
  });
});
