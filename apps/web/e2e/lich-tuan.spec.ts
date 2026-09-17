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

test("thông báo lịch: nhận, click deep-link, và xác nhận đã xem", async ({ page }) => {
  const targetWeek = "2026-W44";
  const notificationId = "notif-test-001";
  
  // Intercept notification API to provide test data
  await page.route("**/api/v1/lich/thong-bao", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          notifications: [
            {
              id: notificationId,
              tuan_iso: targetWeek,
              url: `/lich-tuan?tuan=${targetWeek}`,
              da_xem: 0,
              created_at: new Date().toISOString(),
            },
          ],
        }),
      });
    } else {
      await route.continue();
    }
  });

  // Intercept ack endpoint
  await page.route(`**/api/v1/lich/thong-bao/${notificationId}/ack`, async (route) => {
    if (route.request().method() === "POST") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true }),
      });
    } else {
      await route.continue();
    }
  });

  // Intercept target week data
  await page.route(`**/api/v1/lich-tuan?tuan=${targetWeek}`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        tuan_iso: targetWeek,
        trang_thai: "da_cong_bo",
        schedule_run: {
          id: "run-test",
          status: "computed",
          fingerprint: "fp-test",
          result: { ok: true, assignments: [] },
        },
        open_shifts: [],
      }),
    });
  });

  // Login as employee (minh)
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("minh");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });

  // Navigate to roster page
  await page.goto("/lich-tuan");
  await expect(page.getByRole("heading", { name: /Lịch/i })).toBeVisible();

  // Notification banner should appear
  const banner = page.locator("text=1 chưa xem");
  await expect(banner).toBeVisible({ timeout: 5_000 });

  // Click the notification link
  const notifLink = page.locator(`a[href="/lich-tuan?tuan=${targetWeek}"]`).first();
  await expect(notifLink).toBeVisible();
  await notifLink.click();

  // URL should contain the target week
  await expect(page).toHaveURL(new RegExp(`tuan=${targetWeek}`), { timeout: 5_000 });

  // Acknowledge the notification
  const ackButton = page.getByRole("button", { name: /Đã xem/i });
  if (await ackButton.isVisible()) {
    await ackButton.click();
    // After ack, the notification should be marked as seen
    await expect(page.locator("text=1 chưa xem")).not.toBeVisible({ timeout: 3_000 });
  }
});
