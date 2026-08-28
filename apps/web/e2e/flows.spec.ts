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
    await expect(page.getByRole("heading", { name: "Phiếu mở quán" })).toBeVisible();
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
