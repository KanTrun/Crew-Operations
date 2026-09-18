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

test.describe("Self-Explaining System — Hệ thống tự giải thích", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "lan");
  });

  test("Truy vết nhân quả -> Hiển thị kết luận", async ({ page }) => {
    await page.goto("/giai-thich");
    await expect(page.getByRole("heading", { name: /Hệ thống tự giải thích/i })).toBeVisible();

    await page.getByRole("button", { name: /Truy vết nhân quả/i }).click();
    await expect(page.getByText(/Kết luận/i)).toBeVisible({ timeout: 15_000 });
  });
});