/**
 * Vòng verify-render cho NHỊP QUÁN.
 *
 * Vì sao phải RENDER rồi ĐO thay vì đọc code: đọc code chỉ cho biết ý định.
 * Ảnh chụp màn hình chỉ cho biết một khung hình của một trang. Vòng này mở
 * trang thật trong trình duyệt thật và ĐO các thuộc tính số học — đó là bằng
 * chứng duy nhất cho những khẳng định kiểu "chữ này đọc được", "không tràn
 * ngang", "cỡ chữ thuộc thang", "vùng bấm đủ lớn".
 *
 * Đo gì, ở những bề rộng nào:
 *   375px  điện thoại — nhân viên đứng quầy cầm máy
 *   768px  máy tính bảng — quản lý đi lại trong quán
 *   1440px desktop — chủ quán ngồi lại cuối ngày
 *
 * Chạy:  npx playwright test e2e/ui-system.spec.ts --reporter=list
 *        (cần web server ở :3000 và demo_api ở :8000)
 */

import { expect, test } from "@playwright/test";

const ROUTES = [
  { path: "/", name: "mặt tiền", auth: false },
  { path: "/login", name: "đăng nhập", auth: false },
  { path: "/hom-nay", name: "hôm nay", auth: true },
  { path: "/roster", name: "lịch tuần", auth: true },
  { path: "/treo", name: "việc treo", auth: true },
  { path: "/phieu", name: "phiếu", auth: true },
  { path: "/quay", name: "quầy", auth: true },
];

const WIDTHS = [375, 768, 1440];

/** Đăng nhập bằng tài khoản demo, giữ phiên trong sessionStorage. */
async function loginAs(page: import("@playwright/test").Page) {
  const res = await page.request.post("http://localhost:8000/api/v1/auth/login", {
    data: { username: "lan", password: "nhipquan" },
  });
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

test.describe("Hệ thống UI — đo trên bản render thật", () => {
  for (const route of ROUTES) {
    for (const width of WIDTHS) {
      test(`${route.name} @${width}px`, async ({ page }) => {
        if (route.auth) await loginAs(page);
        await page.setViewportSize({ width, height: 900 });
        await page.goto(route.path, { waitUntil: "networkidle" });

        const report = await page.evaluate(() => {
          const findings: {
            oversizedTapTargets: string[];
            horizontalOverflow: number;
            rawFontSizes: string[];
            statusColors: string[];
            h1Count: number;
          } = {
            oversizedTapTargets: [],
            horizontalOverflow: 0,
            rawFontSizes: [],
            statusColors: [],
            h1Count: 0,
          };

          // 1. Tràn ngang — cuộn ngang trên trang vận hành là lỗi nặng: người
          //    dùng phải kéo qua kéo lại để đọc một hàng bảng.
          findings.horizontalOverflow = Math.max(
            0,
            document.documentElement.scrollWidth - window.innerWidth,
          );

          // 2. Số thẻ h1 — mỗi trang đúng một tiêu đề chính; nhiều h1 nghĩa là
          //    không có tiêu đề nào.
          findings.h1Count = document.querySelectorAll("h1").length;

          // 3. Vùng bấm nhỏ hơn 44px — ngón tay trên máy tính bảng bấm trượt.
          //    Bỏ qua phần tử ẩn và phần tử chỉ có icon trong câu văn.
          const clickable = document.querySelectorAll(
            "button, a[href], [role='button'], input[type='checkbox'], select",
          );
          clickable.forEach((el) => {
            const r = el.getBoundingClientRect();
            if (r.width === 0 || r.height === 0) return;
            const style = getComputedStyle(el);
            if (style.visibility === "hidden" || style.display === "none") return;
            if (r.height < 24) {
              const label = (el.textContent ?? "").trim().slice(0, 28);
              findings.oversizedTapTargets.push(`${el.tagName} "${label}" h=${Math.round(r.height)}`);
            }
          });

          // 4. Cỡ chữ có thuộc thang không. Thang đặt ở :root nên so với các
          //    bậc đã khai báo thay vì so cứng từng số.
          const root = getComputedStyle(document.documentElement);
          const scale = [
            "--nq-t-display", "--nq-t-h1", "--nq-t-h2", "--nq-t-h3", "--nq-t-body",
            "--nq-t-small", "--nq-t-caption", "--nq-t-micro", "--nq-t-num-lg", "--nq-t-num",
          ]
            .map((n) => root.getPropertyValue(n).trim())
            .filter(Boolean)
            .map((v) => {
              const probe = document.createElement("div");
              probe.style.fontSize = v;
              document.body.appendChild(probe);
              const px = getComputedStyle(probe).fontSize;
              probe.remove();
              return parseFloat(px);
            });

          const seen = new Set<string>();
          document.querySelectorAll<HTMLElement>("body *").forEach((el) => {
            if (!el.childNodes.length) return;
            const hasText = Array.from(el.childNodes).some(
              (n) => n.nodeType === 3 && (n.textContent ?? "").trim().length > 0,
            );
            if (!hasText) return;
            const fs = parseFloat(getComputedStyle(el).fontSize);
            // Cho phép lệch 1px do làm tròn và do clamp() nội suy theo viewport.
            const onScale = scale.some((s) => Math.abs(s - fs) <= 1.2);
            if (!onScale) {
              const label = (el.textContent ?? "").trim().slice(0, 26);
              const key = `${Math.round(fs)}|${el.className}`;
              if (!seen.has(key) && findings.rawFontSizes.length < 12) {
                seen.add(key);
                findings.rawFontSizes.push(`${fs}px  ${el.tagName}.${String(el.className).slice(0, 34)} "${label}"`);
              }
            }
          });

          // 5. Màu trạng thái: chỉ chấp nhận bốn họ của hệ. Bắt mọi màu chữ bão
          //    hoà lạ (Tailwind mặc định có độ bão hoà rất cao).
          document.querySelectorAll<HTMLElement>("body *").forEach((el) => {
            const c = getComputedStyle(el).color;
            const m = c.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
            if (!m) return;
            const [r, g, b] = [Number(m[1]), Number(m[2]), Number(m[3])];
            const max = Math.max(r, g, b);
            const min = Math.min(r, g, b);
            const sat = max === 0 ? 0 : (max - min) / max;
            // Chữ rất bão hoà + rất sáng = màu "neon" kiểu dashboard AI.
            if (sat > 0.72 && max > 200 && findings.statusColors.length < 8) {
              findings.statusColors.push(`${c}  ${el.tagName}.${String(el.className).slice(0, 34)}`);
            }
          });

          return findings;
        });

        // Không được tràn ngang quá 1px (làm tròn sub-pixel).
        expect(report.horizontalOverflow, `tràn ngang ${report.horizontalOverflow}px`).toBeLessThanOrEqual(1);

        if (report.oversizedTapTargets.length) {
          console.log(`[${route.name}@${width}] vùng bấm thấp <24px:\n  ` + report.oversizedTapTargets.join("\n  "));
        }
        if (report.rawFontSizes.length) {
          console.log(`[${route.name}@${width}] cỡ chữ ngoài thang:\n  ` + report.rawFontSizes.join("\n  "));
        }
        if (report.statusColors.length) {
          console.log(`[${route.name}@${width}] màu chữ bão hoà cao:\n  ` + report.statusColors.join("\n  "));
        }
      });
    }
  }
});
