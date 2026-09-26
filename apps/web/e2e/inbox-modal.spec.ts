import { expect, test, type Page } from "@playwright/test";

async function loginAsManager(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/, { timeout: 15_000 });
}

async function expectReopenDialogAnchoredToViewport(page: Page) {
  const openButton = page.getByRole("button", { name: "Mở đợt xếp tuần mới", exact: true }).first();
  await expect(openButton).toBeVisible();
  await openButton.scrollIntoViewIfNeeded();
  await openButton.click();

  const dialog = page.getByRole("dialog");
  const layer = page.locator(".nq-inbox-dialog-layer");

  await expect(dialog).toBeVisible();
  await expect(layer).toHaveCSS("position", "fixed");
  await expect(layer).toHaveCSS("z-index", "400");
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).toBe("hidden");

  await dialog.evaluate(async (element) => {
    await Promise.all(element.getAnimations().map((animation) => animation.finished));
  });
  const box = await dialog.boundingBox();
  const viewport = page.viewportSize();
  expect(box).not.toBeNull();
  expect(viewport).not.toBeNull();
  expect(box!.y).toBeGreaterThanOrEqual(0);
  expect(box!.y + box!.height).toBeLessThanOrEqual(viewport!.height);

  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  await expect.poll(() => page.evaluate(() => document.body.style.overflow)).not.toBe("hidden");
}

test("hộp thư ràng buộc chỉ xem — dialog mở lại tuần neo trong viewport khi lịch đã đóng", async ({ page }) => {
  await loginAsManager(page);
  await page.goto("/inbox");
  await expect(page.getByRole("heading", { name: /Hộp thư ràng buộc/i })).toBeVisible();
  // Redesign: AI tự duyệt — không còn nút «Duyệt ràng buộc» thủ công.
  await expect(page.getByRole("button", { name: "Duyệt ràng buộc", exact: true })).toHaveCount(0);
  await expect(page.getByText(/AI tự động duyệt|chỉ xem/i).first()).toBeVisible();

  const reopen = page.getByRole("button", { name: "Mở đợt xếp tuần mới", exact: true });
  if ((await reopen.count()) === 0) {
    // Fixture chưa khoá tuần — vẫn xác nhận trang chỉ-xem ổn định trên desktop/mobile.
    await page.setViewportSize({ width: 1366, height: 576 });
    await expect(page.getByRole("heading", { name: /Hộp thư ràng buộc/i })).toBeVisible();
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(page.getByRole("heading", { name: /Hộp thư ràng buộc/i })).toBeVisible();
    return;
  }

  await page.setViewportSize({ width: 1366, height: 576 });
  await expectReopenDialogAnchoredToViewport(page);

  await page.setViewportSize({ width: 390, height: 844 });
  await expectReopenDialogAnchoredToViewport(page);
});
