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

test("thông báo lịch: click deep-link tự động ack", async ({ page }) => {
  const targetWeek = "2026-W44";
  const notificationId = "notif-test-001";
  let ackCalled = false;

  // Intercept notification API to supply test data
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
              tieu_de: "Lịch tuần đã công bố",
              noi_dung: "Lịch tuần " + targetWeek + " đã được cập nhật.",
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

  // Intercept ack endpoint and track the call
  await page.route(`**/api/v1/lich/thong-bao/${notificationId}/ack`, async (route) => {
    if (route.request().method() === "POST") {
      ackCalled = true;
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

  // Notification banner should show unread count
  const banner = page.locator("text=1 chưa xem");
  await expect(banner).toBeVisible({ timeout: 5_000 });

  // Click the notification link — UI auto-acks on click
  const notifLink = page.locator(`a[href="/lich-tuan?tuan=${targetWeek}"]`).first();
  await expect(notifLink).toBeVisible();
  await notifLink.click();

  // URL should navigate to the target week
  await expect(page).toHaveURL(new RegExp(`tuan=${targetWeek}`), { timeout: 5_000 });

  // Ack fires in the background after link click; wait briefly then verify
  await page.waitForTimeout(1_000);
  expect(ackCalled).toBe(true);
});
