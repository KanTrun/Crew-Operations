import { expect, test, type Page } from "@playwright/test";

/**
 * GRAND EXPERIENCE — một câu chuyện replay 5 phút xuyên 5 ý tưởng chính.
 * KHÔNG cần mạng LLM, microphone, camera, WebGL (đã tắt getContext).
 */

async function loginAs(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
}

test.describe("Grand AI Experience — 5-minute replay story", () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript(() => {
      // Tắt WebGL (2D fallback bắt buộc).
      Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
        value: () => null,
      });
    });
    await loginAs(page);
  });

  test("full story: flavor -> live map -> mode -> rescue -> war room -> rule", async ({ page }) => {
    // 1) QUANVERSE: khách nói khẩu vị → gợi ý coffee.
    await page.goto("/quanverse");
    await expect(page.locator(".nq-living-map")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("flavor-ngot").selectOption("it");
    await page.getByTestId("flavor-sua").uncheck();
    await page.getByTestId("flavor-go").click();
    await expect(page.getByTestId("flavor-results").first()).toBeVisible({ timeout: 10_000 });

    // 2) Manager bật mode "Đêm nhạc" — nếu chưa active (idempotent-friendly).
    const demBtn = page.getByTestId("mode-confirm-dem_nhac").first();
    if (await demBtn.isVisible().catch(() => false)) {
      await demBtn.click();
      await expect(page.locator(".nq-moderail__item.is-active").first()).toBeVisible({ timeout: 10_000 });
    } else {
      // Đã active từ lần chạy trước — ghi nhận không lỗi.
      await expect(page.locator(".nq-moderail__item.is-active").first()).toBeVisible({ timeout: 10_000 });
    }

    // 3) HỒN QUÁN: voice turn grounded (text input) về quầy pha chế.
    await page.goto("/quanverse/spatial-memory");
    await expect(page.locator(".nq-map2d")).toBeVisible({ timeout: 15_000 });
    await page.getByTestId("voice-input").fill("khách thích gì ở quầy pha chế?");
    await page.getByTestId("voice-ask").click();
    const resp = page.getByTestId("voice-response");
    await expect(resp).toBeVisible({ timeout: 10_000 });
    // Grounded: có citation (lớp .nq-voicedock__citations) — chứa số ký ức đã xác nhận.
    await expect(resp.locator(".nq-voicedock__citations")).toContainText("1", { timeout: 10_000 });

    // 4) SHIFT RESCUE: báo vắng → tìm người bù an toàn.
    await page.goto("/quanverse/shift-rescue");
    await page.getByTestId("rescue-intake").click();
    await expect(page.locator(".nq-rescue__case")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId("invite-btn").first()).toBeEnabled();

    // 5) WAR ROOM: so sánh 2 scenario.
    await page.goto("/quanverse/war-room");
    const picker = page.locator(".nq-war-picker");
    await picker.getByRole("button", { name: /Mưa lớn/ }).click();
    await picker.getByRole("button", { name: /Giờ cao điểm/ }).click();
    await page.getByRole("button", { name: "Chạy mô phỏng" }).click();
    await expect(page.locator(".nq-war-compare")).toBeVisible({ timeout: 15_000 });

    // 6) QUÁN TỰ VIẾT LUẬT: discover -> shadow -> confirm, không tự kích hoạt.
    await page.goto("/quanverse/rules");
    await page.getByTestId("rules-discover").click();
    await expect(page.locator(".nq-rules__item")).toHaveCount(1, { timeout: 15_000 });
    await page.getByTestId("shadow-btn").first().click();
    await expect(page.locator(".nq-shadow")).toBeVisible({ timeout: 10_000 });
    await page.getByTestId("confirm-btn").first().click();
    await expect(page.locator(".nq-alert--info")).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/AI đề xuất, quản lý quyết định/)).toBeVisible();
  });

  test("failure path: no live LLM, replay still complete", async ({ page }) => {
    await page.goto("/quanverse/spatial-memory");
    await expect(page.locator(".nq-map2d")).toBeVisible({ timeout: 15_000 });
    // Chọn anchor stockroom (không có memory confirmed) → hỏi → không bịa.
    const kho = page.locator('.nq-map2d__anchor[aria-label="Kho"]');
    await kho.scrollIntoViewIfNeeded().catch(() => undefined);
    await page.mouse.move(500, 400);
    await kho.dispatchEvent("click");
    await page.waitForTimeout(500);
    await page.getByTestId("voice-input").fill("chuyện gì đã xảy ra ở đây?");
    await page.getByTestId("voice-ask").click();
    const resp = page.getByTestId("voice-response");
    await expect(resp).toBeVisible({ timeout: 10_000 });
    // Không có memory confirmed → không citation + không bịa (dùng class).
    await expect(resp.locator(".nq-voicedock__citations")).toHaveCount(0);
  });
});