import { expect, test, type Page, type Route } from "@playwright/test";

/**
 * E2E cho luồng review `NEEDS_REVIEW` của `/khao-sat-gia`
 * (plan `260913-1455` mục 10, tiêu chí nghiệm thu Phase 4:
 * "Người dùng thử nghiệm hoàn thành được luồng review một mục `NEEDS_REVIEW`
 * mà không cần hướng dẫn").
 *
 * VÌ SAO PHẢI STUB API — đọc trước khi "sửa cho gọn":
 *
 * 1. `NEEDS_REVIEW` KHÔNG THỂ xảy ra trong môi trường CI. CI đặt
 *    `CA_AGENT_MODE=replay` ở cấp workflow, và `llm.complete()` trả
 *    `LlmResult(ok=False, text="")` cho mọi lời gọi ở chế độ replay
 *    (`packages/agents/src/ca_agents/llm.py:188-189`). Trong
 *    `extract_menu_from_image`, nhánh `if not res.ok or not res.text: continue`
 *    khiến MỌI lần thử đều bỏ qua, nên `all_needs_review` luôn RỖNG và job
 *    không bao giờ dừng ở `needs_review`. Chạy thật thì chỉ ra `completed`
 *    hoặc `failed`.
 * 2. Chạy thật còn đốt tiền thật: mỗi job gọi proxy + Vision API. Plan mục 7
 *    cấm dùng camoufox cho E2E nội bộ, và ADR-002 yêu cầu tầng toán học
 *    thuần tất định. Stub là lựa chọn duy nhất vừa tất định vừa không tốn phí.
 *
 * Cách stub theo đúng convention sẵn có của `fb-inbox.spec.ts`
 * (`page.route` + `route.fulfill`), không phát minh pattern mới.
 *
 * Ràng buộc nghiệp vụ được kiểm ở đây:
 *  - ADR-008: `needs_review` là ĐIỂM DỪNG THẬT. Không có đường nào tự duyệt thay;
 *    job chỉ rời trạng thái đó khi người dùng gửi xác nhận.
 *  - Mỗi dòng GIỮ LẠI bắt buộc phải có giá; dòng không đọc được thì phải đánh
 *    dấu loại. Thiếu giá thì trang chặn ở client và KHÔNG gọi API.
 */

const API_PATTERN = /^http:\/\/(localhost|127\.0\.0\.1):8000\/api\/v1\/market\/catchment-survey/;

const JOB_ID = "job-e2e-needs-review";

/**
 * Ảnh 1x1 dạng data URI. Dùng data URI chứ không trỏ URL thật: `pending_review[].image_url`
 * được render thành `<img src>`, và một URL ngoài sẽ tạo request mạng thật trong CI
 * (chậm, có thể fail, và vi phạm tính hermetic của suite).
 */
const ANH_MENU_1PX =
  "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==";

type PendingReview = {
  store_id: string;
  store_name: string;
  image_url: string;
  name: string;
  raw_text: string;
  reason: string;
};

/**
 * Hai dòng chờ review, cố ý dùng hai `reason` KHÁC nhau để kiểm trang tra đúng
 * bảng nhãn `LY_DO_REVIEW` (`present.ts:645`) chứ không hardcode một câu.
 * Giá trị là fixture kiểm thử, KHÔNG phải số liệu thị trường thật.
 */
const PENDING: PendingReview[] = [
  {
    store_id: "quan_e2e_01",
    store_name: "Cơm Tấm E2E Một",
    image_url: ANH_MENU_1PX,
    name: "Cơm tấm sườn bì",
    raw_text: "Sườn bì ...0.000",
    reason: "price_unreadable",
  },
  {
    store_id: "quan_e2e_02",
    store_name: "Cơm Tấm E2E Hai",
    image_url: ANH_MENU_1PX,
    name: "Cơm tấm chả trứng",
    raw_text: "chả trứng",
    reason: "low_confidence",
  },
];

function jobStatus(status: string, pending: PendingReview[] = PENDING) {
  return {
    job_id: JOB_ID,
    status,
    created_at: "2026-09-13T08:00:00Z",
    updated_at: "2026-09-13T08:05:00Z",
    error_code: null,
    error_message: null,
    stores_flagged_for_review: pending.map((p) => p.store_id),
    pending_review: pending,
    reviewed_by: null,
    progress: { step: 4, total: 5, label: "Chờ chủ quán xác nhận giá" },
  };
}

/** Kết quả sau khi review xong — khớp `KetQua` trong `page.tsx`. */
const KET_QUA = {
  job_id: JOB_ID,
  status: "completed",
  online_stats: { p25: 32000, p50: 40000, p75: 48000, sample_size: 24, insufficient_data: false },
  dinein_stats: { p25: 30000, p50: 38000, p75: 45000, sample_size: 12, insufficient_data: false },
  substitute_comparison: {
    core_category: "cơm tấm",
    positioning_tier: "street_food",
    core_stats: { p25: 31000, p50: 39000, p75: 47000, sample_size: 36, insufficient_data: false },
    substitutes: [
      {
        category_name: "bún thịt nướng",
        stats: { p25: 33000, p50: 41000, p75: 49000, sample_size: 18, insufficient_data: false },
      },
    ],
    ambi: 39000,
    sweet_spot_low_display: 35000,
    sweet_spot_high_display: 43000,
    min_viable_price: null,
    cost_plus_warning: false,
  },
  area_context: { area_type: "office", competitive_intensity: 6.4 },
  survey_captured_at: "2026-09-13T08:05:00Z",
  generated_at: "2026-09-13T08:06:00Z",
};

async function setSession(page: Page, role: "quan_ly" | "chu_quan" | "nhan_vien") {
  await page.addInitScript((sessionRole) => {
    sessionStorage.setItem("nq_token", "e2e-token");
    sessionStorage.setItem("nq_role", sessionRole);
    sessionStorage.setItem("nq_name", "E2E");
    sessionStorage.setItem("nq_nv", `e2e-${sessionRole}`);
  }, role);
}

/**
 * Stub toàn bộ tuyến `/api/v1/market/catchment-survey*`.
 *
 * `reviewRequests` thu lại thân của mỗi lời gọi `POST .../review` để test khẳng
 * định được payload gửi lên máy chủ — không chỉ khẳng định UI đổi màn hình.
 * `statusAfterReview` quyết định job đi đâu sau khi chủ quán xác nhận.
 */
async function mockKhaoSat(
  page: Page,
  reviewRequests: Array<Record<string, unknown>>,
  statusAfterReview = "completed",
) {
  await page.route(API_PATTERN, async (route: Route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();

    if (method === "POST" && url.pathname.endsWith("/review")) {
      reviewRequests.push(route.request().postDataJSON() as Record<string, unknown>);
      await route.fulfill({
        json: {
          ok: true,
          data: jobStatus(statusAfterReview, statusAfterReview === "completed" ? [] : PENDING),
        },
      });
      return;
    }

    if (method === "POST") {
      // 202 theo plan mục 5.1 — tạo job, chưa có kết quả.
      await route.fulfill({
        status: 202,
        json: {
          ok: true,
          data: { job_id: JOB_ID, status: "queued", idempotent_replay: false, poll_after_seconds: 3 },
        },
      });
      return;
    }

    if (url.pathname.endsWith("/result")) {
      await route.fulfill({ json: { ok: true, data: KET_QUA } });
      return;
    }

    // GET trạng thái: job ĐỨNG ở needs_review cho tới khi có xác nhận (ADR-008).
    await route.fulfill({ json: { ok: true, data: jobStatus("needs_review") } });
  });
}

/** Mở trang và bấm "Bắt đầu khảo sát" — form mặc định đã hợp lệ nên không cần điền. */
async function moTaoJob(page: Page) {
  await page.goto("/khao-sat-gia");
  await expect(page.getByRole("heading", { name: /Khảo sát giá/i }).first()).toBeVisible();
  await page.getByRole("button", { name: "Bắt đầu khảo sát" }).click();
}

test.describe("Khảo sát giá — luồng review NEEDS_REVIEW (ADR-008)", () => {
  test("Job DỪNG ở needs_review và không tự duyệt; thiếu giá thì chặn, không gọi API", async ({ page }) => {
    const reviewRequests: Array<Record<string, unknown>> = [];
    await setSession(page, "quan_ly");
    await mockKhaoSat(page, reviewRequests);

    await moTaoJob(page);

    // 1. Trang tự chuyển sang màn review vì job đứng ở needs_review.
    await expect(page.getByRole("heading", { name: /Xác nhận giá đọc từ ảnh/i })).toBeVisible();

    // 2. ADR-008: nói rõ hệ thống KHÔNG tự duyệt thay.
    await expect(page.getByText(/hệ thống không tự duyệt thay/i)).toBeVisible();

    // 3. Đủ 2 dòng chờ, và nhãn lý do lấy từ bảng tra chứ không hardcode.
    await expect(page.locator("li.nq-record")).toHaveCount(2);
    await expect(page.getByText(/Ảnh mờ, không đọc chắc được giá/)).toBeVisible();
    await expect(page.getByText(/Máy đọc ảnh chưa đủ tự tin/)).toBeVisible();

    // 4. Ảnh menu có render để chủ quán đối chiếu bằng mắt.
    await expect(page.getByAltText(/Ảnh thực đơn của Cơm Tấm E2E Một/)).toBeVisible();

    // 5. Bấm xác nhận khi CHƯA nhập giá nào → phải bị chặn ở client,
    //    và quan trọng hơn: KHÔNG có lời gọi API nào được gửi đi.
    //    Khoanh vùng `.nq-alert--err`: Next.js tự chèn một `div[role=alert]`
    //    rỗng tên `__next-route-announcer__`, nên `getByRole("alert")` trần
    //    dính strict-mode violation (2 phần tử).
    await page.getByRole("button", { name: "Xác nhận và tổng hợp" }).click();
    await expect(page.locator('div[role="alert"].nq-alert--err')).toContainText(
      /cần một mức giá đúng/i,
    );
    expect(reviewRequests).toHaveLength(0);

    // 6. Vẫn ở màn review — job không hề nhúc nhích.
    await expect(page.getByRole("heading", { name: /Xác nhận giá đọc từ ảnh/i })).toBeVisible();
  });

  test("Sửa giá một dòng, loại dòng không đọc được → gửi đúng payload → ra dashboard", async ({ page }) => {
    const reviewRequests: Array<Record<string, unknown>> = [];
    await setSession(page, "chu_quan");
    await mockKhaoSat(page, reviewRequests);

    await moTaoJob(page);
    await expect(page.getByRole("heading", { name: /Xác nhận giá đọc từ ảnh/i })).toBeVisible();

    // Dòng 0: chủ quán đọc ảnh và điền giá đúng + giá khuyến mãi.
    const giaDung = page.getByLabel("Giá đúng (VNĐ)");
    await expect(giaDung).toHaveCount(2);
    await giaDung.nth(0).fill("42000");
    await page.getByLabel("Giá khuyến mãi (nếu có)").nth(0).fill("38000");

    // Dòng 1: ảnh không đọc được → loại khỏi mẫu.
    const loaiDong = page.getByLabel(/Loại dòng này khỏi mẫu/);
    await expect(loaiDong).toHaveCount(2);
    await loaiDong.nth(1).check();

    // Dòng bị loại phải ẩn ô nhập giá — không bắt chủ quán điền cho dòng đã bỏ.
    await expect(page.getByLabel("Giá đúng (VNĐ)")).toHaveCount(1);

    await page.getByRole("button", { name: "Xác nhận và tổng hợp" }).click();

    // Payload gửi lên máy chủ phải đúng hợp đồng: dòng giữ lại có giá,
    // dòng loại bỏ có `rejected: true` và `original_price_vnd: null`.
    await expect.poll(() => reviewRequests.length).toBe(1);
    const body = reviewRequests[0];
    expect(body.approve_all_remaining).toBe(false);
    const items = body.items as Array<Record<string, unknown>>;
    expect(items).toHaveLength(2);
    expect(items[0]).toMatchObject({
      store_id: "quan_e2e_01",
      item_name_raw: "Cơm tấm sườn bì",
      original_price_vnd: 42000,
      effective_price_vnd: 38000,
      rejected: false,
    });
    expect(items[1]).toMatchObject({
      store_id: "quan_e2e_02",
      item_name_raw: "Cơm tấm chả trứng",
      original_price_vnd: null,
      effective_price_vnd: 0,
      rejected: true,
    });

    // Sau xác nhận job mới được đi tiếp → màn dashboard kết quả.
    await expect(page.getByText(/Đã ghi nhận xác nhận của bạn/)).toBeVisible();
    await expect(page.getByRole("heading", { name: /Giá theo kênh/i })).toBeVisible();

    // Plan mục 6.2: Sweet Spot luôn là KHOẢNG, không phải một con số.
    // `exact: true` vì chuỗi này còn xuất hiện trong hint của đồng hồ
    // (`nq-dash-chart-hint`) → không exact thì dính strict-mode violation.
    await expect(page.getByText("35.000đ–43.000đ", { exact: true })).toBeVisible();
    await expect(page.getByText(/Khu văn phòng/)).toBeVisible();
  });

  test("Nhân viên không mở được màn review — tính năng tốn chi phí thật", async ({ page }) => {
    const reviewRequests: Array<Record<string, unknown>> = [];
    await setSession(page, "nhan_vien");
    await mockKhaoSat(page, reviewRequests);

    await page.goto("/khao-sat-gia");

    // Chặn ở HAI lớp, và lớp NGOÀI cùng mới là lớp ăn tiền:
    //  1. `AppShell` tra `canAccess(role, path)`; `/khao-sat-gia` nằm trong
    //     `MANAGER_ONLY` (`lib/session.ts:81`) nên với vai `nhan_vien` nó render
    //     thông báo từ chối THAY VÌ `children` — trang khảo sát không hề mount.
    //  2. Bên trong trang còn `isManager()` → `<Empty title="Cần vai quản lý">`,
    //     là lớp phòng thủ thứ hai nếu ai đó mount trang ngoài AppShell.
    // Khẳng định lớp 1: đây là lý do không thấy heading "Khảo sát giá".
    await expect(
      page.getByRole("heading", { name: /Trang này dành cho vai trò khác/i }),
    ).toBeVisible();

    // Không form, không màn review, và tuyệt đối không có lời gọi API nào.
    await expect(page.getByRole("button", { name: "Bắt đầu khảo sát" })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: /Xác nhận giá đọc từ ảnh/i })).toHaveCount(0);
    await expect(page.getByRole("heading", { name: /Cần vai quản lý/i })).toHaveCount(0);
    expect(reviewRequests).toHaveLength(0);
  });
});
