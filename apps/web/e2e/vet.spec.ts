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

test.describe("Vết hệ thống (sổ vết) — truy vết người ↔ agent", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "lan");
  });

  test("1 — trang /vet hiển thị được", async ({ page }) => {
    await page.goto("/vet");
    await expect(page.getByRole("heading", { name: /Vết hệ thống/i })).toBeVisible();
  });

  test("2 — có ít nhất một vết được hiển thị", async ({ page }) => {
    await page.goto("/vet");
    // Chờ danh sách vết tải xong (không còn loading)
    await expect(page.locator(".nq-item, [class*='item']").first()).toBeVisible({ timeout: 15_000 });
  });

  test("3 — vết do agent hiển thị badge agent + người điều khiển", async ({ page }) => {
    // Chặn API để trả về một vết agent giả lập, kiểm tra UI render đúng
    await page.route("**/api/v1/audit", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              id: 1,
              at: "2026-09-18T10:30:00Z",
              ai: "ag_copilot",
              hanh: "schedule.lifecycle",
              actor_type: "agent",
              agent_name: "ag_copilot",
              controller_user_id: "nv_01",
              payload: { entity_type: "schedule", entity_id: "2026-W38" },
            },
            {
              id: 2,
              at: "2026-09-18T10:31:00Z",
              ai: "nv_05",
              hanh: "shift_swap.request",
              actor_type: "human",
              payload: { entity_type: "swap" },
            },
          ],
        }),
      });
    });
    await page.goto("/vet");
    // Tên agent hiển thị (actorLabelEx → "AG-COPILOT") — nhắm vào <strong> badge,
    // tránh match trúng <option> hidden trong <select> filter.
    await expect(page.locator("strong", { hasText: "AG-COPILOT" }).first()).toBeVisible({ timeout: 15_000 });
    // Badge agent hiển thị nhãn "AI TỰ ĐỘNG" (redesign enterprise-ui-v3)
    await expect(page.getByText("AI TỰ ĐỘNG").first()).toBeVisible();
    // Người điều khiển hiển thị ("· do ...")
    await expect(page.getByText(/· do /)).toBeVisible();
  });
});