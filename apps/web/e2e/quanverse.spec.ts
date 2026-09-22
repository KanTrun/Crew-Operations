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
    // Mặt bằng có cột tải thật, không chỉ chữ.
    await expect(page.locator(".nq-loadbar__fill").first()).toBeVisible();
  });

  test("role switch (replay) changes projection", async ({ page }) => {
    await expect(page.locator(".nq-living-map")).toBeVisible({ timeout: 15_000 });
    // Switch sang khách → không còn sự kiện staff.
    await page.getByTestId("role-khach").click();
    await expect(page.getByText(/Không có sự kiện vận hành cho bản chiếu này/)).toBeVisible({ timeout: 10_000 });
  });

  test("chọn khu vực mở bảng chi tiết", async ({ page }) => {
    await expect(page.locator(".nq-living-map")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(".nq-zone-detail")).toHaveCount(0);
    await page.getByTestId("zone-bar").click();
    const detail = page.locator(".nq-zone-detail");
    await expect(detail).toBeVisible({ timeout: 10_000 });
    await expect(page.getByTestId("zone-bar")).toHaveAttribute("aria-pressed", "true");
    // Bấm lại khu vực khác thì bảng chi tiết đổi theo, không chồng hai bảng.
    await page.getByTestId("zone-cashier").click();
    await expect(page.locator(".nq-zone-detail")).toHaveCount(1);
    await expect(page.getByTestId("zone-cashier")).toHaveAttribute("aria-pressed", "true");
    // Nút đóng trả về trạng thái gợi ý chọn khu vực.
    await page.locator(".nq-zdetail__close").click();
    await expect(page.locator(".nq-zone-detail")).toHaveCount(0);
  });

  test("manager confirms mode", async ({ page }) => {
    await expect(page.locator(".nq-living-map")).toBeVisible({ timeout: 15_000 });
    // quan_yen_tinh — click nếu chưa active (idempotent-friendly với DB bền).
    const btn = page.getByTestId("mode-confirm-quan_yen_tinh").first();
    if (await btn.isVisible().catch(() => false)) {
      await btn.click();
    }
    // Dù đã active từ lần chạy trước, khẳng định có mode đang bật (công tắc bật).
    await expect(page.locator(".nq-moderail__item.is-active").first()).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(".nq-switch.is-on").first()).toBeVisible();
  });

  test("flavor recommendation with reasons", async ({ page }) => {
    await expect(page.locator(".nq-flavor")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("flavor-ngot-it").click();
    await page.getByTestId("flavor-sua").uncheck();
    await page.getByTestId("flavor-go").click();
    await expect(page.getByTestId("flavor-results").first()).toBeVisible({ timeout: 10_000 });
    // Mỗi gợi ý có điểm số trực quan + lý do, không chỉ tên món.
    await expect(page.locator(".nq-flavor__meter-fill").first()).toBeVisible();
    await expect(page.locator(".nq-flavor__reasons li").first()).toBeVisible();
  });

  test("ar-lite fallback path", async ({ page }) => {
    await expect(page.locator(".nq-ar")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("ar-qr").fill("blender-02");
    await page.getByTestId("ar-start").click();
    const result = page.getByTestId("ar-result");
    await expect(result).toBeVisible({ timeout: 10_000 });
    // Mã nội bộ không được in lên UI — vẫn truy vết được qua data-attribute.
    await expect(result).toHaveAttribute("data-fallback", "map_or_qr_text");
    await expect(result).not.toContainText("map_or_qr_text");
    await expect(page.locator(".nq-ar__anchorbox")).toBeVisible();
  });
});