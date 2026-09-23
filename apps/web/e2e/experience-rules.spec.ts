import { expect, test, type Page } from "@playwright/test";

/** Rule learning e2e — replay fixture, không tự kích hoạt. */

async function loginAs(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
}

/**
 * Xoá ứng viên luật trong bộ nhớ server trước mỗi bài.
 *
 * `_CANDIDATES` là store TRONG BỘ NHỚ, sống suốt phiên server; các bài e2e dùng
 * chung một server nên trạng thái rò sang nhau — bài "từ chối ứng viên" chạy sau
 * bài "thu hồi luật" sẽ thấy ứng viên đã `revoked` và mất nút Từ chối. Endpoint
 * reset chỉ mở ở chế độ replay nên an toàn cho production.
 */
async function resetRuleState(page: Page) {
  const api = process.env.NQ_API ?? "http://127.0.0.1:8000";
  const res = await page.request
    .post(`${api}/api/v1/auth/login`, {
      data: { username: "lan", password: "nhipquan" },
    })
    .catch(() => null);
  if (!res || !res.ok()) return;
  const { token } = (await res.json()) as { token: string };
  await page.request
    .post(`${api}/api/v1/experience/rules/reset`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    .catch(() => undefined);
}

test.describe("Quan tu viet luat", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
    await resetRuleState(page);
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

  test("candidates load on mount, not only after discover", async ({ page }) => {
    // Bản trước khởi tạo danh sách rỗng và không nạp khi mount — mở lại trang
    // là thấy trống dù máy chủ vẫn giữ ứng viên.
    await page.getByTestId("rules-discover").click();
    await expect(page.locator(".nq-rules__item")).toHaveCount(1, { timeout: 15_000 });

    await page.reload();
    await expect(page.locator(".nq-rules__item")).toHaveCount(1, { timeout: 15_000 });
  });

  test("published rule can be revoked", async ({ page }) => {
    // Luật đã ban hành mà không thu hồi được nghĩa là quán không sửa được luật
    // của chính mình.
    await page.getByTestId("rules-discover").click();
    const item = page.locator(".nq-rules__item").first();
    await expect(item).toBeVisible({ timeout: 15_000 });

    // Đi hết tới ban hành.
    const shadow = page.getByTestId("shadow-btn").first();
    if (await shadow.isEnabled().catch(() => false)) {
      await shadow.click();
      await expect(page.locator(".nq-shadow")).toBeVisible({ timeout: 10_000 });
    }
    const confirm = page.getByTestId("confirm-btn").first();
    if (await confirm.isVisible().catch(() => false)) {
      await confirm.click();
      await expect(page.locator(".nq-alert--info")).toBeVisible({ timeout: 10_000 });
    }

    const revoke = page.getByTestId("revoke-btn").first();
    await expect(revoke).toBeVisible({ timeout: 10_000 });
    await revoke.click();
    await expect(item).toContainText("Đã thu hồi", { timeout: 10_000 });
  });

  test("reject candidate without activation", async ({ page }) => {
    await page.getByTestId("rules-discover").click();
    await expect(page.locator(".nq-rules__item")).toHaveCount(1, { timeout: 15_000 });
    await page.getByTestId("reject-btn").first().click();
    await expect(page.locator(".nq-alert--info")).toBeVisible({ timeout: 10_000 });
    // Nhãn tiếng Việt (exp-present) — không in mã thô "rejected".
    await expect(page.locator(".nq-rules__item").first()).toContainText("Bị từ chối");
  });
});