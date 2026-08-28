import { test, expect, type Page } from "@playwright/test";

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/);
  await expect(page.getByRole("heading", { name: "Quán hôm nay" })).toBeVisible();
}

test.describe("8 luồng vận hành chính", () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test("1 — đăng nhập → hôm nay", async ({ page }) => {
    await expect(page.getByText(/nguồn/)).toBeVisible();
  });

  test("2 — phiếu mở quán", async ({ page }) => {
    await page.goto("/phieu");
    await expect(page.getByRole("heading", { name: "Phiếu Ca" })).toBeVisible();
  });

  test("3 — lịch của tôi", async ({ page }) => {
    await page.goto("/toi");
    await expect(page.getByRole("heading", { name: "Lịch của tôi" })).toBeVisible();
  });

  test("4 — việc treo", async ({ page }) => {
    await page.goto("/treo");
    await expect(page.getByRole("heading", { name: "Việc treo" })).toBeVisible();
  });

  test("5 — inbox ràng buộc", async ({ page }) => {
    await page.goto("/inbox");
    await expect(page.getByRole("heading", { name: "Hộp thư ràng buộc" })).toBeVisible();
  });

  test("6 — cẩm nang", async ({ page }) => {
    await page.goto("/cam-nang");
    await expect(page.getByRole("heading", { name: "Cẩm nang quán" })).toBeVisible();
  });

  test("7 — hỏi SOP", async ({ page }) => {
    await page.goto("/sop");
    await expect(page.getByRole("heading", { name: "Hỏi SOP" })).toBeVisible();
  });

  test("8 — công bằng", async ({ page }) => {
    await page.goto("/cong-bang");
    await expect(page.getByRole("heading", { name: "Công bằng" })).toBeVisible();
    // Hồ sơ §13.4: chỉ số dư của chính mình so với trung bình nhóm, không xếp
    // hạng tên. Tài khoản test là quản lý, máy chủ trả số dư cả nhóm — UI phải
    // giữ đúng một dòng của người đang xem.
    await expect(page.getByText("Bạn so với trung bình nhóm")).toBeVisible();
    await expect(page.getByText(/không liệt kê số dư của từng người/)).toBeVisible();
  });
});

function rgbLuminance(color: string): number {
  const m = color.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
  if (!m) return -1;
  const chan = [Number(m[1]), Number(m[2]), Number(m[3])].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * chan[0] + 0.7152 * chan[1] + 0.0722 * chan[2];
}

test.describe("Chữ trên nút solid", () => {
  test("AuthGate Đăng nhập: ink lúc nghỉ, copper lúc hover — không dính đen trên nền tối", async ({
    page,
  }) => {
    await page.goto("/treo");
    const btn = page.locator("a.nq-ink-on-solid", { hasText: "Đăng nhập" });
    await expect(btn).toBeVisible();

    const rest = await btn.evaluate((el) => getComputedStyle(el).color);
    expect(rgbLuminance(rest), `rest color ${rest}`).toBeLessThan(0.15);

    await btn.hover();
    const hover = await btn.evaluate((el) => getComputedStyle(el).color);
    expect(rgbLuminance(hover), `hover color ${hover}`).toBeGreaterThan(0.3);
  });
});
