import { expect, test } from "@playwright/test";

test("lịch tuần hiển thị đủ 21 ô và không trắng trang", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });

  await page.goto("/lich-tuan");
  await expect(page.getByRole("heading", { name: /Lịch/i })).toBeVisible();
  await expect(page.getByText("1. Nháp", { exact: true })).toBeVisible();
  await expect(page.getByText("Ràng buộc & kiểm tra lần xếp này")).toBeVisible();
  await expect(page.locator(".nq-roster-slot-btn")).toHaveCount(21);
  await expect(page.locator("body")).not.toBeEmpty();
});
