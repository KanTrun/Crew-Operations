import { expect, test } from "@playwright/test";
import { disableWebgl, loginAs, resetExperienceState } from "./_helpers";

/**
 * Trợ lý Quánverse — tóm tắt tất định + hỏi đáp có căn cứ, trên cả 5 trang.
 *
 * Ba điều bài này khoá, và chúng là lý do tồn tại của bộ test (không phải chỉ để
 * "có test"):
 *
 *  1. **Panel phải có mặt trên MỌI trang** — mục đích của nó là trả lời "trang này
 *     để làm gì" ở nơi người dùng đang đứng. Thiếu một trang là thiếu đúng chỗ đó.
 *  2. **Tóm tắt phải có số THẬT** — nếu chọn sai nguồn dữ liệu, panel vẫn render
 *     nhưng ra "0 neo" dù quán có 8 neo (lỗi thật đã vấp). Test neo vào con số > 0.
 *  3. **Không bịa**: khi câu trả lời không có trích dẫn thì phải nói rõ, và KHÔNG
 *     được render khối `assistant-citations`. Sự VẮNG MẶT của khối đó là bằng
 *     chứng máy kiểm được, cùng hợp đồng với `VoiceDock`.
 */

const MANAGER_PAGES = [
  { route: "/quanverse", summary: "Tóm tắt trang" },
  { route: "/quanverse/war-room", summary: "Tóm tắt trang" },
  { route: "/quanverse/shift-rescue", summary: "Tóm tắt trang" },
  { route: "/quanverse/rules", summary: "Tóm tắt trang" },
  { route: "/quanverse/spatial-memory", summary: "Tóm tắt trang" },
] as const;

test.describe("TRỢ LÝ QUÁNVERSE", () => {
  test.beforeEach(async ({ page }) => {
    await disableWebgl(page);
    await loginAs(page);
    await resetExperienceState(page);
  });

  test("mọi trang Quánverse đều có panel trợ lý với tóm tắt thật", async ({ page }) => {
    for (const { route } of MANAGER_PAGES) {
      await page.goto(route);
      const panel = page.getByTestId("page-assistant");
      await expect(panel).toBeVisible({ timeout: 20_000 });

      // Tóm tắt là tab mặc định — phải có headline, không được rỗng.
      const headline = page.getByTestId("brief-headline");
      await expect(headline).toBeVisible({ timeout: 20_000 });
      await expect(headline).not.toBeEmpty();

      // Trang phải NÓI ĐƯỢC điều gì đó: hoặc có chỉ số/dữ kiện, hoặc nói rõ vì
      // sao chưa có (War Room chưa chạy mô phỏng nào là trạng thái HỢP LỆ, không
      // phải lỗi). Điều không được phép là panel im lặng, không nói gì.
      const metricCount = await page.locator("[data-metric]").count();
      const factCount = await page.getByTestId("brief-facts").locator("li").count();
      const explainsEmpty = await page
        .getByTestId("brief-next")
        .locator("li")
        .count();
      const noRefsNote = await page.getByTestId("brief-no-refs").count();
      expect(metricCount + factCount + explainsEmpty + noRefsNote).toBeGreaterThan(0);
    }
  });

  test("bản đồ sống: tóm tắt khớp số khu vực thật trên mặt bằng", async ({ page }) => {
    await page.goto("/quanverse");
    await expect(page.getByTestId("brief-headline")).toBeVisible({ timeout: 20_000 });

    // Số "Khu vực đang mở" trong brief phải là số THẬT, không phải 0.
    const zones = page.locator('[data-metric="zones"] .nq-brief-metric__value');
    await expect(zones).toBeVisible();
    const text = (await zones.textContent())?.trim() ?? "0";
    expect(Number.parseInt(text, 10)).toBeGreaterThan(0);

    // Và khớp với số chip khu vực trên mặt bằng.
    const chips = await page.locator("[data-testid^='zone-chip-']").count();
    if (chips > 0) {
      expect(Number.parseInt(text, 10)).toBe(chips);
    }
  });

  test("hồn quán: neo đọc từ nguồn thật, không phải 0", async ({ page }) => {
    // Regression cho lỗi đã vấp: brief đọc `anchors` từ fixture
    // `spatial-memory.json` (không có khoá đó) nên LUÔN báo "0 neo".
    await page.goto("/quanverse/spatial-memory");
    const anchors = page.locator('[data-metric="anchors"] .nq-brief-metric__value');
    await expect(anchors).toBeVisible({ timeout: 20_000 });
    const text = (await anchors.textContent())?.trim() ?? "0";
    expect(Number.parseInt(text, 10)).toBeGreaterThan(0);
  });

  test("hỏi đáp trả lời có trích dẫn khi có dữ liệu", async ({ page }) => {
    await page.goto("/quanverse");
    await expect(page.getByTestId("page-assistant")).toBeVisible({ timeout: 20_000 });

    await page.getByTestId("assistant-tab-ask").click();
    await page.getByTestId("assistant-input").fill("Hôm nay có gì cần chú ý?");
    await page.getByTestId("assistant-ask").click();

    await expect(page.getByTestId("assistant-answer")).toBeVisible({ timeout: 20_000 });
    // Có dữ liệu thì phải trích dẫn, và KHÔNG hiện cảnh báo "thiếu căn cứ".
    await expect(page.getByTestId("assistant-citations")).toBeVisible();
    await expect(page.getByTestId("assistant-no-citations")).toHaveCount(0);
  });

  test("không bịa: câu trả lời không có trích dẫn thì phải nói rõ", async ({ page }) => {
    // War Room chưa chạy mô phỏng nào → không có bản ghi để dẫn chứng.
    await page.goto("/quanverse/war-room");
    await expect(page.getByTestId("page-assistant")).toBeVisible({ timeout: 20_000 });

    await page.getByTestId("assistant-tab-ask").click();
    await page.getByTestId("assistant-input").fill("Phương án nào tốt nhất?");
    await page.getByTestId("assistant-ask").click();

    await expect(page.getByTestId("assistant-answer")).toBeVisible({ timeout: 20_000 });

    const hasCitations = await page.getByTestId("assistant-citations").count();
    if (hasCitations === 0) {
      // Vắng trích dẫn PHẢI kèm cảnh báo — đây là hợp đồng "không bịa".
      await expect(page.getByTestId("assistant-no-citations")).toBeVisible();
    }
  });

  test("đổi tab không làm mất tóm tắt, và nút hỏi tắt khi ô trống", async ({ page }) => {
    await page.goto("/quanverse");
    await expect(page.getByTestId("brief-headline")).toBeVisible({ timeout: 20_000 });
    const firstHeadline = await page.getByTestId("brief-headline").textContent();

    await page.getByTestId("assistant-tab-ask").click();
    await expect(page.getByTestId("assistant-input")).toBeVisible();
    // Ô trống → nút Hỏi phải tắt (không gửi câu hỏi rỗng lên máy chủ).
    await expect(page.getByTestId("assistant-ask")).toBeDisabled();

    await page.getByTestId("assistant-tab-summary").click();
    await expect(page.getByTestId("brief-headline")).toHaveText(firstHeadline ?? "");
  });
});
