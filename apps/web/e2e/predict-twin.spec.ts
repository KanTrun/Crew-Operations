import { expect, test, type Page } from "@playwright/test";

async function loginAs(page: Page, user: "lan" | "minh" | "hung" = "lan") {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill(user);
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  try {
    await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
  } catch (err) {
    const alert = await page.locator(".nq-alert, [role='alert']").textContent().catch(() => null);
    if (alert) {
      throw new Error(`Login failed for user "${user}" with page error: "${alert.trim()}". Original: ${err}`);
    }
    throw err;
  }
}

test.describe("Predictive Playbook — Đề xuất thông minh", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "lan");
  });

  test("Chạy phát hiện mẫu thành công -> Hiển thị đề xuất luật tích cực", async ({ page }) => {
    await page.goto("/de-xuat-thong-minh");
    await expect(page.getByRole("heading", { name: /Đề xuất thông minh/i })).toBeVisible();

    await page.getByRole("button", { name: /Chạy phát hiện mẫu thành công/i }).click();
    await expect(page.getByText(/Đã phát hiện/i)).toBeVisible({ timeout: 15_000 });
  });
});

test.describe("Digital Twin — Thử nghiệm an toàn", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "lan");
  });

  test("Chạy mô phỏng tăng giá -> Hiển thị kết quả", async ({ page }) => {
    await page.goto("/thu-nghiem-an-toan");
    await expect(page.getByRole("heading", { name: /Thử nghiệm an toàn/i })).toBeVisible();

    await page.getByRole("button", { name: /Chạy mô phỏng/i }).click();
    await expect(page.getByText(/Mô phỏng hoàn tất/i)).toBeVisible({ timeout: 15_000 });
  });
});