import { test, expect, type Page } from "@playwright/test";

/** Đo latency mở form phiếu (UI), không phải thời gian hoàn thành checklist (#7 nhóm A). */

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  try {
    await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
  } catch (err) {
    const alert = await page.locator(".nq-alert, [role='alert']").textContent().catch(() => null);
    if (alert) {
      throw new Error(`Login failed with page error: "${alert.trim()}". Original: ${err}`);
    }
    throw err;
  }
}

test.describe("Phiếu demo — latency mở form (#7 nhóm A)", () => {
  test("thời gian mở form phiếu đến bước đầu (fixture)", async ({ page }) => {
    await login(page);
    const t0 = Date.now();
    await page.goto("/phieu");
    await expect(
      page.getByRole("heading", { name: /Phiếu ca làm việc|Mở phiếu|Phiếu «/i }),
    ).toBeVisible();

    // Nếu đã ở bước đầu (ví dụ khôi phục phiếu đang làm dở từ phiên trước)
    const buocDau = page.getByText(/Bước \d+ \//).first();
    if (await buocDau.isVisible()) {
      const elapsed_ms = Date.now() - t0;
      console.log(`PHIEU_DEMO_MS=${elapsed_ms}`);
      expect(elapsed_ms).toBeLessThan(30_000);
      return;
    }

    // Nếu đang ở màn hình hoàn thành của phiếu cũ, bấm làm phiếu khác
    const lamKhacBtn = page.getByRole("button", { name: /Làm phiếu khác/i });
    if (await lamKhacBtn.isVisible().catch(() => false)) {
      await lamKhacBtn.click();
    }

    // Chờ danh sách mẫu phiếu nạp xong từ API
    const startBtn = page.getByRole("button", { name: /Mở quán/i }).first();
    await expect(startBtn).toBeVisible({ timeout: 15_000 });

    // Điểm danh có mặt nếu nút "Tôi đã có mặt" hiển thị
    const coMatBtn = page.getByRole("button", { name: /Tôi đã có mặt/i });
    if (await coMatBtn.isVisible()) {
      await coMatBtn.click();
      await expect(page.getByText(/Đã ghi có mặt/i)).toBeVisible({ timeout: 10_000 });
    }

    // Chọn phiếu "Mở quán"
    await startBtn.click();

    // Phòng ngừa trường hợp chưa ghi nhận điểm danh kịp thời
    const chuaDiemDanh = page.getByText(/Chưa có mặt hôm nay/i);
    if (await chuaDiemDanh.isVisible().catch(() => false)) {
      if (await coMatBtn.isVisible()) {
        await coMatBtn.click();
        await expect(page.getByText(/Đã ghi có mặt/i)).toBeVisible({ timeout: 10_000 });
        await startBtn.click();
      }
    }

    // Đảm bảo hiển thị bước đầu tiên của phiếu
    await expect(page.getByText(/Bước \d+ \//).first()).toBeVisible({ timeout: 15_000 });
    const elapsed_ms = Date.now() - t0;
    console.log(`PHIEU_DEMO_MS=${elapsed_ms}`);
    expect(elapsed_ms).toBeLessThan(30_000);
  });
});
