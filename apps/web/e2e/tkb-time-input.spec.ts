import { expect, test } from "@playwright/test";
import { loginAs } from "./_helpers";

/**
 * Hồi quy cho `TimeField` — ô giờ 24h hai số ở trang /tkb.
 *
 * Lỗi thật đã gặp (người dùng báo "không thể setting giờ chiều như 12:00 đến
 * 23:00 vì không thể nhập hai số khi phát hiện được lịch bận"):
 *
 *  `clampDigits` cũ trả `String(Math.min(Number(digits), max))`. Ép qua SỐ rồi
 *  về chuỗi nên ăn mất số 0 đứng đầu và nuốt ký tự thứ hai khi giá trị số
 *  không đổi:
 *
 *    - `09` → Number=9  → `"9"`      (mất số 0 đầu)
 *    - `00` → Number=0  → `"0"`      (gõ phím thứ hai như không có gì xảy ra)
 *
 *  Mà `TIME_PATTERN` của chính trang này đòi `HH:mm` có số 0 đầu (`[01]\d`).
 *  Hệ quả: `09:00` bị báo "Nhập đủ giờ…", và với phút thì gõ hai số luôn thấy
 *  một số. Đây là lỗi ở tầng hiển thị giá trị ô nhập, KHÔNG phải lỗi mạng —
 *  nên test phải chạy trên trang thật, không mock.
 *
 * Vì sao phải bấm «Thử ảnh mẫu» TRƯỚC khi sửa tay: toàn bộ thẻ «Bước 2 — Sửa
 * & xác nhận» chỉ render khi `result` khác null (`{result ? (...) : null}` trong
 * tkb/page.tsx). Nghĩa là lưới có nút «Thêm khung» KHÔNG tồn tại cho tới khi
 * chạy OCR. Bài này dùng ảnh mẫu (fixture) nên không cần Gemini.
 */
test.describe("TimeField — ô giờ 24h hai số", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, "lan");
  });

  /** Vào /tkb, đặt tuần, chạy OCR bằng ảnh mẫu để lưới sửa tay xuất hiện. */
  async function moLuoiSuaTay(page: import("@playwright/test").Page, tuan = "2026-W44") {
    await page.goto("/tkb");
    await expect(page.getByRole("heading", { name: /Tải ảnh lịch bận/i })).toBeVisible();
    // Ô tuần là `<input type="week">` bọc trong `<Field label>` (không aria-label).
    await page.locator('input[type="week"]').fill(tuan);
    // OCR ảnh mẫu → `result` khác null → lưới sửa tay mới render.
    await page.getByRole("button", { name: "Thử ảnh mẫu" }).click();
    await expect(page.getByTitle("Thêm khung bận cho Chủ Nhật")).toBeVisible({ timeout: 30_000 });
  }

  test("gõ được số 0 đứng đầu (09:00) và giữ nguyên hai chữ số", async ({ page }) => {
    await moLuoiSuaTay(page);

    // Thêm khung bận cho Chủ Nhật, rồi gõ 09:00 → 12:00.
    await page.getByTitle("Thêm khung bận cho Chủ Nhật").click();

    // Nhãn aria thật có kèm NGÀY ("… Chủ Nhật 03/11/2026 — giờ") nên phải khớp
    // theo regex, không khớp chuỗi tuyệt đối.
    const gio = page.getByLabel(/^Giờ bắt đầu bận Chủ Nhật.*— giờ$/).first();
    const phut = page.getByLabel(/^Giờ bắt đầu bận Chủ Nhật.*— phút$/).first();
    const gioKetThuc = page.getByLabel(/^Giờ kết thúc bận Chủ Nhật.*— giờ$/).first();
    const phutKetThuc = page.getByLabel(/^Giờ kết thúc bận Chủ Nhật.*— phút$/).first();

    await gio.fill("0");
    await gio.fill("09");
    await phut.fill("0");
    await phut.fill("00");

    // Số 0 đứng đầu PHẢI còn: đây chính là chỗ bản cũ ăn mất.
    await expect(gio).toHaveValue("09");
    await expect(phut).toHaveValue("00");

    await gioKetThuc.fill("12");
    await phutKetThuc.fill("00");
    await expect(gioKetThuc).toHaveValue("12");
    await expect(phutKetThuc).toHaveValue("00");

    // Không được báo lỗi định dạng cho khung vừa nhập hợp lệ.
    await expect(page.getByText("Nhập đủ giờ bắt đầu và kết thúc theo định dạng HH:mm.")).toHaveCount(0);
  });

  test("nhập được khung chiều 12:00 → 23:00 (đúng ca người dùng báo lỗi)", async ({ page }) => {
    await moLuoiSuaTay(page);

    await page.getByTitle("Thêm khung bận cho Chủ Nhật").click();

    const gio = page.getByLabel(/^Giờ bắt đầu bận Chủ Nhật.*— giờ$/).first();
    const phut = page.getByLabel(/^Giờ bắt đầu bận Chủ Nhật.*— phút$/).first();
    const gioKetThuc = page.getByLabel(/^Giờ kết thúc bận Chủ Nhật.*— giờ$/).first();
    const phutKetThuc = page.getByLabel(/^Giờ kết thúc bận Chủ Nhật.*— phút$/).first();

    await gio.fill("12");
    await phut.fill("00");
    await gioKetThuc.fill("23");
    await phutKetThuc.fill("00");

    await expect(gio).toHaveValue("12");
    await expect(phut).toHaveValue("00");
    await expect(gioKetThuc).toHaveValue("23");
    await expect(phutKetThuc).toHaveValue("00");

    await expect(page.getByText("Nhập đủ giờ bắt đầu và kết thúc theo định dạng HH:mm.")).toHaveCount(0);
    await expect(page.getByText("Giờ kết thúc phải sau giờ bắt đầu.")).toHaveCount(0);
  });

  test("giờ vượt trần bị kẹp đúng (25→23 giờ, 99→59 phút)", async ({ page }) => {
    await moLuoiSuaTay(page);

    await page.getByTitle("Thêm khung bận cho Chủ Nhật").click();

    const gio = page.getByLabel(/^Giờ bắt đầu bận Chủ Nhật.*— giờ$/).first();
    const phut = page.getByLabel(/^Giờ bắt đầu bận Chủ Nhật.*— phút$/).first();

    await gio.fill("25");
    await expect(gio).toHaveValue("23");

    await phut.fill("99");
    await expect(phut).toHaveValue("59");
  });
});
