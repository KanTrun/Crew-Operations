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
    await expect(
      page.getByRole("heading", { name: /Phiếu ca làm việc|Mở phiếu/i }),
    ).toBeVisible();
    // Luồng mới: xác nhận có mặt → chọn phiếu "Mở quán" → thấy bước đầu.
    const coMatBtn = page.getByRole("button", { name: /Tôi đã có mặt/i });
    if (await coMatBtn.isVisible()) {
      await coMatBtn.click();
      await expect(
        page.getByRole("button", { name: /Mở quán/i }).first(),
      ).toBeVisible({ timeout: 10_000 });
    }
    const startBtn = page.getByRole("button", { name: /Mở quán/i }).first();
    if (await startBtn.isVisible()) {
      await startBtn.click();
      await expect(page.getByText(/Bước \d+ \//).first()).toBeVisible({ timeout: 15_000 });
    }
    const elapsed_ms = Date.now() - t0;
    console.log(`PHIEU_DEMO_MS=${elapsed_ms}`);
    expect(elapsed_ms).toBeLessThan(30_000);
  });
});
