/**
 * E2E — mỗi luồng phải thấy BẢN GHI THẬT, không chỉ thấy cái tiêu đề.
 *
 * Bộ cũ có 8 test và 7 trong số đó chỉ `expect(heading).toBeVisible()`. Chúng
 * xanh trên một trang trống hoàn toàn, nên chúng từng báo "UI xong" khi UI chưa
 * có gì. Bộ này đổi luật chơi: mỗi test đếm bản ghi, tìm nhóm trạng thái, hoặc
 * đọc một con số cụ thể do máy chủ trả về. Trang trống là test đỏ.
 *
 * Dữ liệu quán lúc viết: 18 việc treo (6 quá hạn · 6 đang chờ · 6 xong) · 14 mục
 * hộp thư (6 ý định) · 12 luật cẩm nang (có luật bị vòng kiểm loại, có luật tự
 * tắt) · 3 mẫu phiếu (20 · 4 · 5 bước) · 9 dòng sổ tiêu thụ · 7 cụm hao phí.
 */

import { test, expect, type Page } from "@playwright/test";

const KEY_ONBOARDING = "nq_onboarding_v1";

/**
 * Tắt lớp hướng dẫn trước khi trang chạy.
 *
 * Tour là lớp phủ chặn tương tác. Test nào không kiểm tour thì phải vào với dấu
 * "đã xem", nếu không mọi click sau đó đều bị lớp phủ ăn mất — và lỗi đó nhìn
 * như lỗi của trang chứ không như lỗi của test.
 */
async function tatTour(page: Page) {
  await page.addInitScript((k) => {
    try {
      window.localStorage.setItem(k as string, "1");
    } catch {
      /* trình duyệt chặn localStorage — tour tự coi như đã xem */
    }
  }, KEY_ONBOARDING);
}

async function login(page: Page) {
  await page.goto("/login");
  await page.getByLabel("Tài khoản").fill("lan");
  await page.getByLabel("Mật khẩu").fill("nhipquan");
  await page.getByRole("button", { name: "Vào hệ thống" }).click();
  await expect(page).toHaveURL(/\/hom-nay/);
  await expect(page.getByRole("heading", { name: "Quán hôm nay" })).toBeVisible();
}

/** Đọc con số trong một ô của dải tóm tắt, ví dụ ô "quá hạn". */
async function soTrongDaiTomTat(page: Page, nhan: string): Promise<number> {
  const cell = page.locator(".nq-summary-cell", { hasText: nhan }).first();
  await expect(cell).toBeVisible();
  const raw = await cell.locator(".nq-summary-n").innerText();
  return Number(raw.trim());
}

test.describe("Luồng vận hành — có bản ghi thật mới xanh", () => {
  test.beforeEach(async ({ page }) => {
    await tatTour(page);
    await login(page);
  });

  test("1 — hôm nay: bento hiện số thật, không ô trống", async ({ page }) => {
    // Nguồn dữ liệu in một lần trong meta của banner.
    await expect(page.getByText(/nguồn/)).toBeVisible();

    // Dải tóm tắt đếm từ danh sách việc treo thật.
    const tong = await soTrongDaiTomTat(page, "việc treo");
    expect(tong).toBeGreaterThanOrEqual(1);
    const quaHan = await soTrongDaiTomTat(page, "quá hạn");
    expect(quaHan).toBeGreaterThanOrEqual(1);

    // Mọi ô bento phải có giá trị, không ô nào để gạch.
    const tiles = page.locator(".nq-bento-tile");
    const n = await tiles.count();
    expect(n).toBeGreaterThanOrEqual(4);
    for (let i = 0; i < n; i += 1) {
      const val = (await tiles.nth(i).locator(".nq-bento-value").innerText()).trim();
      expect(val.length).toBeGreaterThan(0);
      expect(val).not.toBe("—");
    }

    // Ô việc treo phải khớp con số ở dải tóm tắt.
    await expect(page.locator(".nq-bento-tile", { hasText: "Việc treo" }).first()).toContainText(
      String(tong),
    );

    // Khối việc quá hạn cũ nhất là nội dung, không phải hộp trang trí.
    await expect(page.getByRole("heading", { name: "Việc quá hạn cũ nhất" })).toBeVisible();
    await expect(page.getByRole("link", { name: /Xem cả \d+ việc treo/ })).toBeVisible();
  });

  test("2 — phiếu: cả 3 mẫu hiện ra kèm số bước", async ({ page }) => {
    await page.goto("/phieu");
    await expect(page.getByRole("heading", { name: "Phiếu ca" })).toBeVisible();

    const picks = page.locator(".nq-pick");
    await expect(picks).toHaveCount(3);

    const moQuan = picks.filter({ hasText: "Mở quán" });
    const dongQuan = picks.filter({ hasText: "Đóng quán" });
    const banGiao = picks.filter({ hasText: "Bàn giao ca" });
    await expect(moQuan).toHaveCount(1);
    await expect(dongQuan).toHaveCount(1);
    await expect(banGiao).toHaveCount(1);

    // Số bước là số thật của mẫu, không phải nhãn chung.
    await expect(moQuan.locator(".nq-pick-steps")).toContainText("20");
    await expect(dongQuan.locator(".nq-pick-steps")).toContainText("4");
    await expect(banGiao.locator(".nq-pick-steps")).toContainText("5");

    // Mỗi thẻ nói mẫu chạy lúc nào trong ngày.
    await expect(moQuan.locator(".nq-pick-what")).toContainText("ca đầu ngày");
    await expect(dongQuan.locator(".nq-pick-what")).toContainText("ca cuối ngày");
    await expect(banGiao.locator(".nq-pick-what")).toContainText("giao ca");
  });

  test("3 — lịch của tôi: có ca thật hoặc câu giải thích vì sao trống", async ({ page }) => {
    await page.goto("/toi");
    await expect(page.getByRole("heading", { name: "Lịch của tôi" })).toBeVisible();
    await expect(page.getByText("Đang tải lịch của bạn…")).toHaveCount(0);
    const ca = page.locator(".nq-item:not(.nq-skeleton)");
    const trong = page.locator(".nq-empty");
    await expect(ca.first().or(trong.first())).toBeVisible();
    if ((await ca.count()) > 0) {
      await expect(ca.first().locator(".nq-item-title")).not.toHaveText("");
    } else {
      await expect(trong.first()).toContainText(/lịch|ca/i);
    }
  });

  test("4 — việc treo: 3 nhóm trạng thái, quá hạn lên trước", async ({ page }) => {
    await page.goto("/treo");
    await expect(page.getByRole("heading", { name: "Việc treo", exact: true })).toBeVisible();

    const tong = await soTrongDaiTomTat(page, "việc treo");
    expect(tong).toBeGreaterThanOrEqual(1);

    // Nhóm quá hạn phải có mặt và phải là nhóm đầu tiên.
    const nhom = page.locator(".nq-group");
    await expect(nhom.first().locator(".nq-group-title")).toContainText("Quá hạn");
    await expect(page.locator(".nq-group-title", { hasText: "Đang chờ làm" })).toBeVisible();
    await expect(page.locator(".nq-group-title", { hasText: "Đã xong" })).toBeVisible();

    // Có bản ghi thật, và số dòng khớp tổng ở dải tóm tắt.
    const dong = page.locator(".nq-rows > .nq-row-line");
    expect(await dong.count()).toBe(tong);
    await expect(dong.first().locator(".nq-row-title")).not.toHaveText("");
    // Mỗi dòng nói ai để lại, từ phiếu nào, và hạn là ngày nào.
    await expect(dong.first().locator(".nq-row-sub")).toContainText(/phiếu/);
    await expect(dong.first().locator(".nq-row-side")).toContainText(/hạn/);

    // Tab thứ hai: sổ lần sửa, gom theo kiểu thao tác.
    await page.getByRole("button", { name: /Lần sửa lịch \(\d+\)/ }).click();
    await expect(page.locator(".nq-group-title").first()).toBeVisible();
    expect(await page.locator(".nq-rows > .nq-row-line").count()).toBeGreaterThanOrEqual(1);
    expect(await soTrongDaiTomTat(page, "lần sửa lịch")).toBeGreaterThanOrEqual(1);
  });

  test("5 — hộp thư: mục thật, chip ý định, thanh độ tin cậy", async ({ page }) => {
    await page.goto("/inbox");
    await expect(page.getByRole("heading", { name: "Hộp thư ràng buộc" })).toBeVisible();

    const tong = await soTrongDaiTomTat(page, "mục trong hộp");
    expect(tong).toBeGreaterThanOrEqual(1);
    expect(await soTrongDaiTomTat(page, "loại ý định")).toBeGreaterThanOrEqual(2);

    const dong = page.locator(".nq-rows > .nq-row-line");
    expect(await dong.count()).toBe(tong);
    await expect(page.locator(".nq-group-title", { hasText: "Chờ bạn quyết" })).toBeVisible();

    // Chip ý định AG-MSG hiện thành chữ, không hiện mã.
    const chips = page.locator(".nq-chip");
    expect(await chips.count()).toBeGreaterThanOrEqual(tong);
    await expect(page.getByText(/Xin nghỉ ca|Đổi ca|Báo đến trễ|Nhận ca|Cập nhật thời khoá biểu/).first()).toBeVisible();
    // Không mã nội bộ nào lọt ra thân trang.
    await expect(page.locator("body")).not.toContainText("cho_duyet");
    await expect(page.locator("body")).not.toContainText("ag_msg");

    // Thanh độ tin cậy có phần trăm đọc được.
    const conf = page.locator(".nq-conf").first();
    await expect(conf).toBeVisible();
    await expect(conf.locator(".nq-conf-n")).toHaveText(/^\d{1,3}%$/);
  });

  test("6 — cẩm nang: luật thật, có luật bị loại và luật tự tắt", async ({ page }) => {
    await page.goto("/cam-nang");
    await expect(page.getByRole("heading", { name: "Cẩm nang quán" })).toBeVisible();

    const tong = await soTrongDaiTomTat(page, "luật trong cẩm nang");
    expect(tong).toBeGreaterThanOrEqual(1);

    const the = page.locator(".nq-rule");
    expect(await the.count()).toBe(tong);

    // Ba phần hồ sơ §9.3 trên thẻ đầu tiên.
    const dau = the.first();
    await expect(dau.locator(".nq-rule-cau")).not.toHaveText("");
    await expect(dau.getByText("Kết quả tập sự")).toBeVisible();
    await expect(dau.getByText("Đã áp dụng")).toBeVisible();
    await expect(dau.getByText("Bị ghi đè")).toBeVisible();

    // Nguồn gốc bấm xem được.
    const nguon = dau.getByRole("group").filter({ hasText: "Xem nguồn gốc luật này" });
    await dau.getByText("Xem nguồn gốc luật này").click();
    await expect(nguon.getByText("Bằng chứng")).toBeVisible();
    await expect(nguon.getByText("Mẫu lặp lại")).toBeVisible();

    // Nhóm luật đã dừng tồn tại và tách khỏi nhóm đang chạy.
    await expect(page.getByRole("heading", { name: "Luật đang chạy trong quán" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: /Đã dừng — bị loại, bị từ chối, hoặc tự tắt/ }),
    ).toBeVisible();

    // Luật bị vòng kiểm loại: có thẻ, và có câu lý do bằng tiếng Việt.
    const biLoai = the.filter({ hasText: "Bị loại ở vòng kiểm" });
    expect(await biLoai.count()).toBeGreaterThanOrEqual(1);
    await expect(biLoai.first().locator(".nq-rule-why")).toContainText(/Vòng kiểm loại/);

    // Luật tự tắt: nhóm khác, câu giải thích khác.
    const tuTat = the.filter({ hasText: "Tự tắt vì ít dùng" });
    expect(await tuTat.count()).toBeGreaterThanOrEqual(1);
    await expect(tuTat.first().locator(".nq-rule-why")).toContainText(/ghi đè/);

    // Mã cổng VF không được ra thân trang.
    await expect(page.locator("body")).not.toContainText("luat_ve_nguoi");
    await expect(page.locator("body")).not.toContainText("truong_khong_ton_tai");
  });

  test("7 — hỏi SOP: trả lời kèm trích dẫn nguồn", async ({ page }) => {
    await page.goto("/sop");
    await expect(page.getByRole("heading", { name: "Hỏi SOP" })).toBeVisible();
    await page.getByLabel("Bạn muốn biết gì").fill("Nhiệt độ tủ lạnh bao nhiêu là được?");
    await page.getByRole("button", { name: "Hỏi cẩm nang" }).click();

    await expect(page.getByRole("heading", { name: "Cẩm nang trả lời" })).toBeVisible({ timeout: 15_000 });
    const cites = page.locator(".nq-cites li");
    expect(await cites.count()).toBeGreaterThanOrEqual(1);
    await expect(cites.first().locator(".nq-cite-k")).toHaveText(/Mẫu phiếu|Cẩm nang/);
    // Trích dẫn in tên bước, không in mã bước.
    await expect(page.locator(".nq-cites")).not.toContainText("phieu:");
  });

  test("8 — công bằng: chỉ số dư của chính mình", async ({ page }) => {
    await page.goto("/cong-bang");
    await expect(page.getByRole("heading", { name: "Công bằng" })).toBeVisible();
    // Hồ sơ §13.4: chỉ số dư của chính mình so với trung bình nhóm, không xếp
    // hạng tên. Tài khoản test là quản lý, máy chủ trả số dư cả nhóm — UI phải
    // giữ đúng một dòng của người đang xem.
    await expect(page.getByText("Bạn so với trung bình nhóm")).toBeVisible();
    await expect(page.getByText(/không liệt kê số dư của từng người/)).toBeVisible();
    const truc = page.locator(".nq-fair-row");
    expect(await truc.count()).toBeGreaterThanOrEqual(1);
    await expect(truc.first().locator(".nq-fair-nums")).toContainText("TB nhóm");
  });

  test("9 — sổ tiêu thụ: bảng có cột đơn vị và dấu dưới ngưỡng", async ({ page }) => {
    await page.goto("/tieu-thu");
    await expect(page.getByRole("heading", { name: "Sổ tiêu thụ" })).toBeVisible();

    const dong = await soTrongDaiTomTat(page, "lần kiểm kê");
    expect(dong).toBeGreaterThanOrEqual(1);

    await expect(page.getByRole("columnheader", { name: "Đơn vị" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Số lượng" })).toBeVisible();
    const hang = page.locator(".nq-table tbody tr");
    expect(await hang.count()).toBe(dong);
    // Cột số phải là số, và phải căn phải (cột số dùng thuộc tính data-num).
    await expect(hang.first().locator("td[data-num='1']").first()).toHaveText(/^\d+(\.\d+)?$/);
    // Mỗi dòng có tình trạng ngưỡng, không dòng nào để trống.
    for (let i = 0; i < (await hang.count()); i += 1) {
      await expect(hang.nth(i).locator(".nq-chip")).toHaveText(/dưới ngưỡng|đủ dùng/);
    }
  });

  test("10 — hao phí: cụm thật và bảng gom theo mặt hàng", async ({ page }) => {
    await page.goto("/hao-phi");
    await expect(page.getByRole("heading", { name: "Hao phí", exact: true })).toBeVisible();

    const cum = await soTrongDaiTomTat(page, "cụm đã gom");
    expect(cum).toBeGreaterThanOrEqual(1);
    expect(await soTrongDaiTomTat(page, "mặt hàng có hao")).toBeGreaterThanOrEqual(1);

    await expect(page.getByRole("columnheader", { name: "Đơn vị" })).toBeVisible();
    await expect(page.getByRole("columnheader", { name: "Tổng hao" })).toBeVisible();
    const hang = page.locator(".nq-table tbody tr");
    expect(await hang.count()).toBeGreaterThanOrEqual(1);
    // Mặt hàng lặp lại đủ ngưỡng phải được đánh dấu.
    expect(await page.locator(".nq-table tbody tr[data-low='1']").count()).toBeGreaterThanOrEqual(1);

    // Cụm theo thứ hiện thành chữ, không hiện mã T3.
    const dongCum = page.locator(".nq-rows > .nq-row-line");
    expect(await dongCum.count()).toBeGreaterThanOrEqual(cum);
    await expect(dongCum.first().locator(".nq-row-sub")).toContainText(/Thứ |Chủ nhật/);
  });
});

test.describe("Đăng ký tài khoản", () => {
  test("11 — đăng ký mới vào thẳng hôm nay và chạy hướng dẫn", async ({ page }) => {
    // Không tắt tour: người mới đăng ký PHẢI thấy hướng dẫn (Việc 5.4).
    const ten = `e2e_${Date.now().toString(36)}`;
    await page.goto("/dang-ky");
    await expect(page.getByRole("heading", { name: "Tạo tài khoản" })).toBeVisible();
    // Nói rõ vai mặc định là nhân viên.
    await expect(page.getByText(/luôn là/)).toContainText("nhân viên");

    await page.getByLabel("Tên đăng nhập").fill(ten);
    await page.getByLabel("Mật khẩu").fill("caphe12345");
    await page.getByLabel("Tên hiển thị").fill("Người mới E2E");
    await page.getByRole("button", { name: "Tạo tài khoản và vào ca" }).click();

    await expect(page).toHaveURL(/\/hom-nay/, { timeout: 20_000 });
    // Tour tự chạy cho người vừa tạo tài khoản.
    const hopThoai = page.getByRole("dialog");
    await expect(hopThoai).toBeVisible({ timeout: 10_000 });
    await expect(hopThoai).toContainText("Hướng dẫn · bước 1");
    // Mật khẩu và token không được in ra bất cứ đâu.
    await expect(page.locator("body")).not.toContainText("caphe12345");
  });

  test("12 — lỗi client: ba ô sai hiện câu riêng, chưa gửi máy chủ", async ({ page }) => {
    await page.goto("/dang-ky");
    await page.getByLabel("Tên đăng nhập").fill("A B");
    await page.getByLabel("Mật khẩu").fill("123");
    await page.getByLabel("Tên hiển thị").fill("x");
    await page.getByRole("button", { name: "Tạo tài khoản và vào ca" }).click();

    // Vẫn ở trang đăng ký: client chặn trước khi gửi.
    await expect(page).toHaveURL(/\/dang-ky/);
    await expect(page.getByText(/chỉ nhận chữ thường không dấu/)).toBeVisible();
    await expect(page.getByText(/Mật khẩu cần từ 8 ký tự/)).toBeVisible();
    await expect(page.getByText(/Tên hiển thị cần ít nhất 2 ký tự/)).toBeVisible();
  });

  test("13 — trùng tên đăng nhập: câu tiếng Việt riêng, không mã lỗi", async ({ page }) => {
    const ten = `e2e_dup_${Date.now().toString(36)}`;

    async function guiDangKy() {
      await page.goto("/dang-ky");
      await page.getByLabel("Tên đăng nhập").fill(ten);
      await page.getByLabel("Mật khẩu").fill("caphe12345");
      await page.getByLabel("Tên hiển thị").fill("Trùng tên E2E");
      await page.getByRole("button", { name: "Tạo tài khoản và vào ca" }).click();
    }

    await guiDangKy();
    await expect(page).toHaveURL(/\/hom-nay/, { timeout: 20_000 });

    await guiDangKy();
    await expect(page.getByText(/quán đã có người dùng/)).toBeVisible({ timeout: 15_000 });
    await expect(page).toHaveURL(/\/dang-ky/);
    // Mã lỗi thô của máy chủ không ra UI.
    await expect(page.locator("body")).not.toContainText("ten_da_ton_tai");
    await expect(page.locator("body")).not.toContainText("409");
  });
});

test.describe("Hướng dẫn cho người lần đầu", () => {
  test("14 — lần đầu hiện tour, bỏ qua thì không hiện lại", async ({ page }) => {
    await login(page);

    const hopThoai = page.getByRole("dialog");
    await expect(hopThoai).toBeVisible({ timeout: 10_000 });
    await expect(hopThoai).toHaveAttribute("aria-modal", "true");
    await expect(hopThoai).toContainText("bước 1 /");
    // Mỗi bước nói vùng này để làm gì, và có câu hỏi bấm được sang AG-SOP.
    const cauHoi = hopThoai.locator("a.nq-ask").first();
    await expect(cauHoi).toBeVisible();
    await expect(cauHoi).toHaveAttribute("href", /\/sop\?q=/);

    // Đi tiếp một bước rồi bỏ qua.
    await hopThoai.getByRole("button", { name: "Tiếp" }).click();
    await expect(hopThoai).toContainText("bước 2 /");
    await hopThoai.getByRole("button", { name: "Bỏ qua" }).click();
    await expect(hopThoai).toBeHidden();

    // Vào lại: không hiện nữa, vì dấu đã xem nằm trong localStorage.
    await page.reload();
    await expect(page.getByRole("heading", { name: "Quán hôm nay" })).toBeVisible();
    await page.waitForTimeout(1200);
    await expect(page.getByRole("dialog")).toHaveCount(0);
    const seen = await page.evaluate((k) => window.localStorage.getItem(k as string), KEY_ONBOARDING);
    expect(seen).toBe("1");
  });

  test("15 — Esc đóng tour, và mở lại được từ trang Thêm", async ({ page }) => {
    await login(page);
    const hopThoai = page.getByRole("dialog");
    await expect(hopThoai).toBeVisible({ timeout: 10_000 });
    await page.keyboard.press("Escape");
    await expect(hopThoai).toBeHidden();

    await page.goto("/them");
    await expect(page.getByRole("heading", { name: "Hướng dẫn từng vùng" })).toBeVisible();
    await page.getByRole("button", { name: "Xem lại hướng dẫn" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("16 — câu hỏi trong tour nhảy sang /sop đã điền sẵn", async ({ page }) => {
    await login(page);
    const hopThoai = page.getByRole("dialog");
    await expect(hopThoai).toBeVisible({ timeout: 10_000 });
    const cauHoi = hopThoai.locator("a.nq-ask").first();
    const cau = (await cauHoi.innerText()).trim();
    await cauHoi.click();

    await expect(page).toHaveURL(/\/sop\?q=/);
    await expect(page.getByLabel("Bạn muốn biết gì")).toHaveValue(cau);
    // Trang tự hỏi luôn: có câu trả lời hoặc câu "chưa có trong cẩm nang".
    await expect(page.getByRole("heading", { name: "Cẩm nang trả lời" })).toBeVisible({
      timeout: 20_000,
    });
  });
});
