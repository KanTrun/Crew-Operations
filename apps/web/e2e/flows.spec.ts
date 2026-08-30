import { expect, test, type Page } from "@playwright/test";

async function loginAs(page: Page, user: "lan" | "minh" | "hung" = "lan") {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill(user);
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/);
}

test.describe("8 luồng vận hành chính (Quản lý - lan)", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "lan");
  });

  test("1 — đăng nhập → hôm nay", async ({ page }) => {
    await expect(page.getByRole("heading", { name: "Quán hôm nay" })).toBeVisible();
  });

  test("2 — phiếu mở quán", async ({ page }) => {
    await page.goto("/phieu");
    await expect(page.getByRole("heading", { name: /Mở phiếu|Phiếu/i })).toBeVisible();
  });

  test("3 — lịch của tôi", async ({ page }) => {
    await page.goto("/toi");
    await expect(page.getByRole("heading", { name: /Lịch của tôi/i })).toBeVisible();
  });

  test("4 — việc treo", async ({ page }) => {
    await page.goto("/treo");
    await expect(page.getByRole("heading", { name: /Việc treo/i })).toBeVisible();
  });

  test("5 — inbox ràng buộc", async ({ page }) => {
    await page.goto("/inbox");
    await expect(page.getByRole("heading", { name: /Hộp thư ràng buộc/i })).toBeVisible();
  });

  test("6 — cẩm nang", async ({ page }) => {
    await page.goto("/cam-nang");
    await expect(page.getByRole("heading", { name: /Cẩm nang/i })).toBeVisible();
  });

  test("7 — hỏi SOP", async ({ page }) => {
    await page.goto("/sop");
    await expect(page.getByRole("heading", { name: /Hỏi SOP/i })).toBeVisible();
  });

  test("8 — công bằng", async ({ page }) => {
    await page.goto("/cong-bang");
    await expect(page.getByRole("heading", { name: /Công bằng/i })).toBeVisible();
  });
});

test.describe("3 vỏ theo vai trò & Phân quyền RoleGate", () => {
  test("Nhân viên (minh): thấy vỏ nhân viên, vào được quầy/pha, bị chặn khỏi lịch tuần/menu/người", async ({
    page,
  }) => {
    await loginAs(page, "minh");

    // Vỏ nhân viên hiển thị nav Quầy và Pha chế
    await expect(page.getByRole("link", { name: "Quầy" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Pha chế" })).toBeVisible();

    // Vào /quay
    await page.goto("/quay");
    await expect(page.getByRole("heading", { name: /Ghi đơn tại quầy|Quầy/i })).toBeVisible();

    // Vào /pha
    await page.goto("/pha");
    await expect(page.getByRole("heading", { name: /Màn hình pha chế|KDS/i })).toBeVisible();

    // Bị chặn khỏi /roster (quản lý)
    await page.goto("/roster");
    await expect(page.getByRole("heading", { name: /Trang này dành cho vai trò khác|Không đủ quyền/i })).toBeVisible();

    // Bị chặn khỏi /menu (chủ quán)
    await page.goto("/menu");
    await expect(page.getByRole("heading", { name: /Trang này dành cho vai trò khác|Không đủ quyền/i })).toBeVisible();

    // Bị chặn khỏi /nguoi (chủ quán)
    await page.goto("/nguoi");
    await expect(page.getByRole("heading", { name: /Trang này dành cho vai trò khác|Không đủ quyền/i })).toBeVisible();

    // Nhân viên không vào các bề mặt duyệt, quản trị hoặc kênh khách.
    for (const route of ["/inbox", "/page-quan", "/vet", "/menu"]) {
      await page.goto(route);
      await expect(
        page.getByRole("heading", { name: /Trang này dành cho vai trò khác|Không đủ quyền/i }),
      ).toBeVisible();
    }

    // Nhân viên được đọc luật, nhưng API vẫn chặn thao tác xét/chốt ở role quản lý.
    await page.goto("/cam-nang");
    await expect(page.getByRole("heading", { name: /Cẩm nang/i })).toBeVisible();
  });

  test("Quản lý (lan): vào được lịch tuần/hộp thư, bị chặn khỏi menu/người", async ({ page }) => {
    await loginAs(page, "lan");

    // Vào /roster
    await page.goto("/roster");
    await expect(page.getByRole("heading", { name: /Lịch/i })).toBeVisible();

    // Vào /inbox
    await page.goto("/inbox");
    await expect(page.getByRole("heading", { name: /Hộp thư ràng buộc/i })).toBeVisible();

    // Quản lý cần thấy đủ các bề mặt vận hành, không chỉ lịch và hộp thư.
    for (const [route, heading] of [
      ["/page-quan", /Page quán/i],
      ["/cam-nang", /Cẩm nang/i],
      ["/tkb", /Thời khoá biểu/i],
      ["/tieu-thu", /Tiêu thụ/i],
      ["/hao-phi", /Hao phí/i],
      ["/cong-bang", /Công bằng/i],
      ["/sop", /Hỏi SOP/i],
    ] as const) {
      await page.goto(route);
      await expect(page.getByRole("heading", { name: heading })).toBeVisible();
    }

    // Bị chặn khỏi /menu (chủ quán)
    await page.goto("/menu");
    await expect(page.getByRole("heading", { name: /Trang này dành cho vai trò khác|Không đủ quyền/i })).toBeVisible();

    // Bị chặn khỏi /nguoi (chủ quán)
    await page.goto("/nguoi");
    await expect(page.getByRole("heading", { name: /Trang này dành cho vai trò khác|Không đủ quyền/i })).toBeVisible();
  });

  test("Chủ quán (hung): toàn quyền menu, người dùng và lịch", async ({ page }) => {
    await loginAs(page, "hung");

    // Vỏ chủ quán có Menu & giá, Người dùng
    await expect(page.getByRole("link", { name: "Menu & giá" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Người dùng" })).toBeVisible();

    // Vào /menu
    await page.goto("/menu");
    await expect(page.getByRole("heading", { name: "Menu & giá", exact: true })).toBeVisible();

    // Vào /nguoi
    await page.goto("/nguoi");
    await expect(page.getByRole("heading", { name: /Người dùng/i })).toBeVisible();

    // Vào /roster
    await page.goto("/roster");
    await expect(page.getByRole("heading", { name: /Lịch/i })).toBeVisible();

    // Chủ quán cũng vào được /inbox, /quay, /pha
    await page.goto("/inbox");
    await expect(page.getByRole("heading", { name: /Hộp thư/i })).toBeVisible();
    await page.goto("/quay");
    await expect(page.getByRole("heading", { name: /Quầy/i })).toBeVisible();
    await page.goto("/pha");
    await expect(page.getByRole("heading", { name: /Pha chế|KDS/i })).toBeVisible();
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
  test("AuthGate Đăng nhập: ink lúc nghỉ — không dính đen trên nền tối", async ({
    page,
  }) => {
    await page.goto("/treo");
    const btn = page.locator("a.nq-ink-on-solid", { hasText: "Đăng nhập" });
    await expect(btn).toBeVisible();

    const rest = await btn.evaluate((el) => getComputedStyle(el).color);
    expect(rgbLuminance(rest), `rest color ${rest}`).toBeLessThan(0.35);
  });
});
