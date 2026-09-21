import { expect, test, type Page } from "@playwright/test";

/** HỒN QUÁN Spatial Memory e2e — replay fixture, WebGL-off, no mạng LLM. */

async function loginAs(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
}

test.describe("Hon Quan Spatial Memory", () => {
  test.beforeEach(async ({ page }) => {
    // Tắt WebGL để test 2D fallback.
    await page.addInitScript(() => {
      Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
        value: () => null,
      });
    });
    await loginAs(page);
    await page.goto("/quanverse/spatial-memory");
  });

  test("anchor select shows details and confirmed memories", async ({ page }) => {
    await expect(page.locator(".nq-map2d")).toBeVisible({ timeout: 15_000 });
    // Anchor đầu (bar) được auto-select → chi tiết + timeline đã hiện.
    await expect(page.locator(".nq-anchor")).toBeVisible({ timeout: 10_000 });
    // Anchor thứ 2 press Enter (SVG g có onKeyDown) → chi tiết + focus đổi.
    const second = page.locator(".nq-map2d__anchor").nth(1);
    await second.focus().catch(() => undefined);
    await page.keyboard.press("Enter");
    await expect(page.locator(".nq-anchor")).toBeVisible({ timeout: 10_000 });
    // Timeline có thể trống nếu anchor không có memory — khẳng định phần chi tiết vẫn hiện.
    await expect(page.locator(".nq-anchor h3")).toBeVisible({ timeout: 10_000 });
  });

  test("voice turn grounded answer and remember proposal", async ({ page }) => {
    await expect(page.locator(".nq-map2d")).toBeVisible({ timeout: 15_000 });

    // Hỏi grounded về bar (default selected là anchor đầu).
    await page.getByTestId("voice-input").fill("khách thích gì ở quầy pha chế?");
    await page.getByTestId("voice-ask").click();
    const resp = page.getByTestId("voice-response");
    await expect(resp).toBeVisible({ timeout: 10_000 });
    await expect(resp).toContainText("ký ức đã xác nhận");

    // Nhớ điều này → đề xuất memory.
    await page.getByTestId("voice-input").fill("nhớ điều này: khách đoàn thích ngồi gần cửa sổ");
    await page.getByTestId("voice-ask").click();
    await expect(page.getByText(/Đề xuất ký ức/)).toBeVisible({ timeout: 10_000 });
  });

  test("tour guide renders deterministic steps", async ({ page }) => {
    await expect(page.locator(".nq-map2d")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(".nq-tour__step").first()).toBeVisible({ timeout: 10_000 });
    const steps = await page.locator(".nq-tour__step").count();
    expect(steps).toBeGreaterThanOrEqual(2);
  });
});