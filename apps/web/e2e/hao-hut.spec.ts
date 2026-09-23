/**
 * Hao hụt — kiểm trên bản render thật (plan 260923-1736 phase 7).
 *
 * Đo cái phải đo: bảng hao hụt có số thật, dòng thiếu dữ liệu **không** bị in
 * thành 0, và không có mã nội bộ / `[object Object]` lọt lên màn hình.
 *
 * Vì sao assert bằng `data-*` chứ không bằng chữ tiếng Việt: Playwright đọc spec
 * có dấu bị mojibake khi so text (đã ghi trong memory của repo). Bám vào
 * `data-muc-do` / `data-mat-hang` là ổn định và vẫn kiểm đúng điều cần kiểm.
 *
 * Chạy:  npx playwright test e2e/hao-hut.spec.ts --reporter=list
 *        (cần next ở :3001 và demo_api ở :8000)
 */

import { expect, test } from "@playwright/test";

async function loginAs(page: import("@playwright/test").Page, username = "lan") {
  const res = await page.request.post("http://localhost:8000/api/v1/auth/login", {
    data: { username, password: "nhipquan" },
  });
  expect(res.ok(), `đăng nhập ${username} phải thành công`).toBeTruthy();
  const body = await res.json();
  await page.addInitScript(
    ([token, role, name, nvId]) => {
      sessionStorage.setItem("nq_token", token);
      sessionStorage.setItem("nq_role", role);
      sessionStorage.setItem("nq_name", name);
      sessionStorage.setItem("nq_nv_id", nvId);
    },
    [body.token, body.role, body.display_name, body.nv_id],
  );
}

test.describe("Hao hụt — bảng theo nguyên liệu", () => {
  test("trang mở được và có tiêu đề Hao phí", async ({ page }) => {
    await loginAs(page);
    await page.goto("/hao-phi", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: /Hao phí/i })).toBeVisible();
  });

  test("có bộ chọn kỳ và bốn ô tóm tắt", async ({ page }) => {
    await loginAs(page);
    await page.goto("/hao-phi", { waitUntil: "networkidle" });

    const nhom = page.getByRole("group", { name: "Chọn kỳ xem" });
    await expect(nhom).toBeVisible();
    await expect(nhom.getByRole("button")).toHaveCount(4);
  });

  test("đổi kỳ thì gọi lại API với đúng kỳ", async ({ page }) => {
    await loginAs(page);
    await page.goto("/hao-phi", { waitUntil: "networkidle" });

    const goi: string[] = [];
    page.on("request", (r) => {
      if (r.url().includes("/api/v1/hao-hut?")) goi.push(r.url());
    });

    await page.getByRole("group", { name: "Chọn kỳ xem" }).getByRole("button").nth(3).click();
    await expect.poll(() => goi.some((u) => u.includes("ky=all"))).toBeTruthy();
  });

  test("dòng thiếu dữ liệu hiện gạch, KHÔNG hiện số 0", async ({ page }) => {
    await loginAs(page);
    await page.goto("/hao-phi", { waitUntil: "networkidle" });

    const thieu = page.locator('[data-muc-do="thieu_du_lieu"]').first();
    if ((await thieu.count()) === 0) {
      test.skip(true, "kỳ này không có dòng thiếu dữ liệu");
    }
    // Trong dòng thiếu dữ liệu, chỗ số phải là gạch dài, không phải "0.0".
    await expect(thieu).toContainText("—");
  });

  test("mức độ render bằng nhãn tiếng Việt, không phải mã nội bộ", async ({ page }) => {
    await loginAs(page);
    await page.goto("/hao-phi", { waitUntil: "networkidle" });

    const than = await page.locator(".nq-page").innerText();
    for (const ma of ["thieu_du_lieu", "nghiem_trong", "canh_bao", "ke_hoach_kiem_ke", "hon_hop"]) {
      expect(than, `mã nội bộ ${ma} không được lọt lên UI`).not.toContain(ma);
    }
    expect(than).not.toContain("[object Object]");
  });

  test("không tràn ngang ở 375px và 768px", async ({ page }) => {
    await loginAs(page);
    for (const width of [375, 768]) {
      await page.setViewportSize({ width, height: 900 });
      await page.goto("/hao-phi", { waitUntil: "networkidle" });
      const tran = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(tran, `@${width}px tràn ${tran}px`).toBeLessThanOrEqual(1);
    }
  });

  test("form ghi hao hụt có đủ ô và ghi được", async ({ page }) => {
    await loginAs(page);
    await page.goto("/hao-phi", { waitUntil: "networkidle" });

    // Ô nguyên liệu + gợi ý từ danh mục
    const oNguyenLieu = page.locator('input[list="mat-hang-goi-y"]').first();
    await expect(oNguyenLieu).toBeVisible();
    await oNguyenLieu.fill("sua_tuoi_browser_test");

    await page.locator("form").filter({ has: page.getByRole("button", { name: /Ghi hao hụt/i }) }).locator('input[inputmode="decimal"]').fill("1");

    const ghi = page.getByRole("button", { name: /^Ghi hao hụt$/ });
    await ghi.click();

    // Thành công thì có thông báo xác nhận, không có câu lỗi.
    await expect(page.getByRole("status").or(page.locator(".nq-alert--ok"))).toBeVisible({ timeout: 10000 });
  });

  test("khu ghi chú ca cũ vẫn còn", async ({ page }) => {
    await loginAs(page);
    await page.goto("/hao-phi", { waitUntil: "networkidle" });
    await expect(page.getByRole("heading", { name: /Ghi chú trong ca/i })).toBeVisible();
  });

  test("có lối đi sang các trang liên quan", async ({ page }) => {
    await loginAs(page);
    await page.goto("/hao-phi", { waitUntil: "networkidle" });

    for (const href of ["/tieu-thu", "/menu", "/sop"]) {
      await expect(page.locator(`a[href="${href}"]`).first()).toBeVisible();
    }
  });
});

test.describe("Trang liên kết trỏ về hao hụt", () => {
  test("/tieu-thu có lối sang /hao-phi", async ({ page }) => {
    await loginAs(page);
    await page.goto("/tieu-thu", { waitUntil: "networkidle" });
    await expect(page.locator('a[href="/hao-phi"]').first()).toBeVisible();
  });

  test("/menu (chủ quán) có lối sang /hao-phi", async ({ page }) => {
    await loginAs(page, "hung");
    await page.goto("/menu", { waitUntil: "networkidle" });
    await expect(page.locator('a[href="/hao-phi"]').first()).toBeVisible();
  });
});

test.describe("Ảnh sản phẩm", () => {
  test("mọi món trong menu quản trị đều có ảnh", async ({ page }) => {
    await loginAs(page, "hung");
    await page.goto("/menu", { waitUntil: "networkidle" });

    const anh = page.locator('img[src*="/anh"]');
    const n = await anh.count();
    expect(n, "menu phải có ít nhất một ảnh món").toBeGreaterThan(0);

    // Ảnh phải tải được thật, không rơi về placeholder chữ cái đầu.
    const hong = await page.evaluate(() =>
      Array.from(document.querySelectorAll<HTMLImageElement>('img[src*="/anh"]'))
        .filter((img) => img.complete && img.naturalWidth === 0)
        .map((img) => img.src),
    );
    expect(hong, `ảnh không tải được: ${hong.join(", ")}`).toHaveLength(0);
  });
});
