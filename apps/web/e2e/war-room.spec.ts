import { expect, test, type Page } from "@playwright/test";

/** War Room e2e — replay mode, không mạng/LLM thật. */

async function loginAs(page: Page, user: "lan" | "minh" = "lan") {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill(user);
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
}

test.describe("War Room", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "lan"); // lan = quan_ly
    await page.goto("/quanverse/war-room");
  });

  test("manager can pick scenarios, compare and propose", async ({ page }) => {
    await page.goto("/quanverse/war-room");

    // Chọn 2 preset crisis (mưa lớn + giờ cao điểm) — trong ScenarioPicker.
    const picker = page.locator(".nq-war-picker");
    await picker.getByRole("button", { name: /Mưa lớn/ }).click();
    await picker.getByRole("button", { name: /Giờ cao điểm/ }).click();

    await page.getByRole("button", { name: "Chạy mô phỏng" }).click();

    // So sánh baseline + options hiện ra (dùng class thay text tiếng Việt để
    // tránh mojibake encoding trên một số máy).
    await expect(page.locator(".nq-war-compare")).toBeVisible();
    await expect(page.locator(".nq-war-compare__baseline")).toBeVisible();

    // Đề xuất một option (dùng data-testid tránh mojibake tiếng Việt).
    await page.getByTestId("propose-btn").first().click();
    await expect(page.locator(".nq-alert--info")).toBeVisible({ timeout: 10000 });
  });

  test("blocked option shows violation, no propose", async ({ page }) => {
    await page.goto("/quanverse/war-room");
    // Chọn thiếu nhân sự (feasibility chạy solver) — trong ScenarioPicker.
    const picker = page.locator(".nq-war-picker");
    await picker.getByRole("button", { name: /Thiếu nhân sự/ }).click();
    await picker.getByRole("button", { name: /Giờ cao điểm/ }).click();
    await page.getByRole("button", { name: "Chạy mô phỏng" }).click();
    await expect(page.locator(".nq-war-compare")).toBeVisible();
    // Mọi option "Thiếu nhân sự" vi phạm ràng buộc cứng → nút Đề xuất disabled.
    // (Không cho "chọn bừa" một ứng viên không an toàn.)
    await expect(page.getByTestId("propose-btn").first()).toBeDisabled();
  });
});