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

    // Ít nhất 1 ứng viên an toàn hiển thị. Bảng mới dùng `tr[data-candidate]`
    // trong khối "đủ điều kiện"; người bị loại nằm ở bảng riêng có `.is-blocked`.
    const safe = await page
      .locator("[data-testid='rescue-candidate-table'] tbody tr[data-candidate]:not(.is-blocked)")
      .count();
    expect(safe).toBeGreaterThanOrEqual(1);

    // Mời ứng viên đầu tiên (data-testid).
    await page.getByTestId("invite-btn").first().click();
    await expect(page.locator(".nq-alert--info")).toBeVisible({ timeout: 10_000 });

    const elapsed = (Date.now() - start) / 1000;
    expect(elapsed).toBeLessThan(90);
  });

  test("full lifecycle reaches confirmed", async ({ page }) => {
    // Trước đây UI dừng ở bước mời nên ca cứu không bao giờ chốt được.
    await page.getByTestId("rescue-intake").click();
    await expect(page.locator(".nq-rescue__case")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("invite-btn").first().click();

    const respond = page.locator(".nq-rescue__respond");
    await expect(respond).toBeVisible({ timeout: 10_000 });

    // Chưa phản hồi thì chưa chốt được — nút chốt phải khoá.
    await expect(page.getByTestId("rescue-confirm")).toBeDisabled();

    await page.getByTestId("rescue-accept").click();
    await expect(page.getByTestId("rescue-confirm")).toBeEnabled({ timeout: 10_000 });
    await page.getByTestId("rescue-confirm").click();

    // Trạng thái cuối đọc được bằng nhãn tiếng Việt, không phải mã thô.
    await expect(page.getByTestId("rescue-status")).toContainText("Đã xác nhận", {
      timeout: 10_000,
    });
  });

  test("shift and absence are chosen, not hardcoded", async ({ page }) => {
    // Bản trước hardcode ca t7_toi / nv_absent_quan nên chỉ chạy một kịch bản.
    const shift = page.getByTestId("rescue-shift");
    await expect(shift).toBeVisible({ timeout: 15_000 });
    const optionCount = await shift.locator("option").count();
    expect(optionCount).toBeGreaterThanOrEqual(1);
    await expect(page.getByTestId("rescue-absence")).toBeVisible();
  });

  test("no unsafe recommend: blocked candidates never have invite button", async ({ page }) => {
    await page.getByTestId("rescue-intake").click();
    await expect(page.locator(".nq-rescue__case")).toBeVisible({ timeout: 15_000 });

    // Nút invite chỉ nằm trong candidate an toàn (không blocked).
    const blockedInvites = await page
      .locator("tr.is-blocked [data-testid='invite-btn']")
      .count();
    expect(blockedInvites).toBe(0);
  });
});