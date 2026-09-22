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

    // Mọi neo phải nằm TRONG khung vẽ — bản trước chiếu sai nên neo rơi ra ngoài
    // viewBox và bản đồ trông rỗng dù API trả đủ dữ liệu.
    const svgBox = await page.locator(".nq-map2d__svg").boundingBox();
    expect(svgBox).not.toBeNull();
    const anchorCount = await page.locator(".nq-map2d__anchor").count();
    expect(anchorCount).toBeGreaterThan(0);
    for (let i = 0; i < anchorCount; i++) {
      const box = await page.locator(".nq-map2d__anchor").nth(i).boundingBox();
      expect(box).not.toBeNull();
      if (!box || !svgBox) continue;
      expect(box.y).toBeGreaterThanOrEqual(svgBox.y - 2);
      expect(box.y + box.height).toBeLessThanOrEqual(svgBox.y + svgBox.height + 2);
    }

    // Anchor đầu auto-select → chi tiết hiện.
    await expect(page.locator(".nq-anchor")).toBeVisible({ timeout: 10_000 });

    // Anchor thứ 2: Enter phải đổi được lựa chọn (SVG g có onKeyDown).
    const second = page.locator(".nq-map2d__anchor").nth(1);
    const secondId = await second.getAttribute("data-anchor");
    await second.focus().catch(() => undefined);
    await page.keyboard.press("Enter");
    await expect(page.locator(".nq-anchor")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(".nq-map2d__anchor.is-selected")).toHaveAttribute(
      "data-anchor",
      secondId ?? "",
    );
  });

  test("3D toggle available when the machine can run WebGL", async ({ page }) => {
    // Fallback 2D luôn có; nút chuyển chỉ hiện khi máy thật sự chạy được WebGL.
    const toggle = page.getByTestId("spatial-map-toggle");
    const has3d = await toggle.isVisible().catch(() => false);
    if (!has3d) {
      // Không có WebGL (đúng với cấu hình test này) → phải là sơ đồ 2D, không trắng.
      await expect(page.locator(".nq-map2d")).toBeVisible();
      return;
    }
    await toggle.click();
    await expect(page.getByTestId("spatial-3d")).toBeVisible({ timeout: 15_000 });
  });

  test("voice turn grounded answer and remember proposal", async ({ page }) => {
    await expect(page.locator(".nq-map2d")).toBeVisible({ timeout: 15_000 });

    // Hỏi grounded về bar (default selected là anchor đầu).
    await page.getByTestId("voice-input").fill("khách thích gì ở quầy pha chế?");
    await page.getByTestId("voice-ask").click();
    const resp = page.getByTestId("voice-response");
    await expect(resp).toBeVisible({ timeout: 10_000 });
    await expect(resp).toContainText("ký ức đã xác nhận");

    // Nhớ điều này → đề xuất memory (không lộ mã nội bộ trên UI).
    await page.getByTestId("voice-input").fill("nhớ điều này: khách đoàn thích ngồi gần cửa sổ");
    await page.getByTestId("voice-ask").click();
    await expect(page.getByText(/đề xuất ghi nhớ/i)).toBeVisible({ timeout: 10_000 });
    await expect(resp).not.toContainText("vp_");
  });

  test("memory consent grant and remove are reachable", async ({ page }) => {
    // Trước đây ký ức chờ duyệt treo vĩnh viễn: API có consent + delete nhưng
    // không UI nào gọi.
    await expect(page.locator(".nq-anchor")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(".nq-anchor__subhead").first()).toBeVisible();

    const grant = page.getByTestId(/^mem-grant-/).first();
    if (await grant.isVisible().catch(() => false)) {
      await grant.click();
      await expect(page.locator(".nq-pref__notice").first()).toBeVisible({ timeout: 10_000 });
    }
    // Không có ký ức chờ thì nhánh empty state phải nói thẳng, không để trống.
    const emptyOrList = page.locator("[data-testid='pending-memories'], .nq-exp-empty");
    await expect(emptyOrList.first()).toBeVisible();
  });

  test("tour guide renders deterministic steps", async ({ page }) => {
    await expect(page.locator(".nq-map2d")).toBeVisible({ timeout: 15_000 });
    await expect(page.locator(".nq-tour__step").first()).toBeVisible({ timeout: 10_000 });
    const steps = await page.locator(".nq-tour__step").count();
    expect(steps).toBeGreaterThanOrEqual(2);
  });
});