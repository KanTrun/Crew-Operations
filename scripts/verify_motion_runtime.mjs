/**
 * Kiem chung o muc RUNTIME: bang nhip trong `globals.css` co THAT SU dieu khien
 * chuyen dong cua `framer-motion` khong?
 *
 * Cong `audit_motion_tokens.py` doc ma nguon — no chung minh khong con so tran,
 * nhung KHONG chung minh duoc `framer-motion` lay nhip tu CSS. Cau hoi con lai:
 * doi `--nq-beat-focus` thi chuyen dong co doi theo, hay `motion.ts` da dong
 * bang gia tri tu luc tai module?
 *
 * Cach kiem: do thoi gian the KPI di tu trong suot den ro net (no chay
 * `beat("focus")`), lam hai lan — mot lan voi CSS goc, mot lan sau khi ghi de
 * `--nq-beat-focus` thanh 1400ms.
 *
 * Vi sao so sanh TUONG DOI chu khong tuyet doi: moc bat dau do duoc khong phai
 * luc chuyen dong bat dau, ma la luc trinh duyet kip nhin thay phan tu — phu
 * thuoc thoi gian thuỷ hop cua React. Con so tuyet doi vi vay luon lech. Nhung
 * khang dinh can kiem la "doi bien thi chuyen dong doi", va khang dinh do doc
 * duoc bang hieu giua hai lan do.
 *
 * Chay: node scripts/verify_motion_runtime.mjs [--base http://localhost:3001]
 */

import { createRequire } from "node:module";

// `playwright` nam trong `apps/web/node_modules`, khong o goc du an — dung
// createRequire tro vao do thay vi doan duong dan tuong doi.
const require = createRequire(import.meta.url);
const { chromium } = require("./../apps/web/node_modules/playwright");

const args = process.argv.slice(2);
const baseIdx = args.indexOf("--base");
const BASE = baseIdx >= 0 ? args[baseIdx + 1] : "http://localhost:3001";
const USER = process.env.NQ_USER || "lan";
const PASS = process.env.NQ_PASS || "nhipquan";
const CHART_PAGE = "/hom-nay";
const OVERRIDE_MS = 1400;

let failures = 0;
function check(ok, label, detail = "") {
  console.log(`  ${ok ? "[OK]" : "[X] "} ${label}${detail ? ` — ${detail}` : ""}`);
  if (!ok) failures += 1;
}

/**
 * Theo dõi opacity của phần tử khớp `selector`, trả về khoảng thời gian nó chạy
 * từ dưới 1 lên tới 1.
 *
 * Hai điều bắt buộc, và tôi đã làm sai cả hai ở lần đo đầu:
 *
 *  1. Phải ĐỢI phần tử xuất hiện rồi mới bắt đầu tính. Đo từ `waitUntil: "commit"`
 *     thì `querySelector` trả về `null` suốt giai đoạn trước khi React gắn vào
 *     DOM, và mốc bắt đầu bị lấy sai.
 *  2. Phải trả về khoảng giữa "bắt đầu thấy mờ" và "đục hẳn", KHÔNG phải từ lúc
 *     gọi hàm. Lần đo đầu trả về tổng thời gian kể từ lúc gọi, nên nó trộn thời
 *     gian chờ DOM với thời gian chuyển động — và vì lần thứ hai chạy khi DOM đã
 *     ấm, nó ra NGẮN hơn, dẫn tới kết luận ngược (bien không có tác dụng).
 */
const WATCH_OPACITY = async ({ selector, timeoutMs }) => {
  const t0 = performance.now();
  let startedAt = null;
  let peak = 1;
  // Doc bien ngay trong luc do de biet lan do nay dung gia tri nao — neu khong
  // ghi lai thi khong phan biet duoc "ghi de khong ap dung" voi "ghi de ap dung
  // nhung chuyen dong khong doi theo".
  const focusVar = () =>
    getComputedStyle(document.documentElement).getPropertyValue("--nq-beat-focus").trim();
  const focusAtStart = focusVar();

  return await new Promise((resolve) => {
    function tick() {
      const el = document.querySelector(selector);
      const t = performance.now() - t0;
      if (el) {
        const o = Number(getComputedStyle(el).opacity);
        if (startedAt === null) {
          if (o < 0.99) startedAt = t;
          else peak = Math.min(peak, o);
        } else if (o >= 0.99) {
          resolve({
            durationMs: t - startedAt,
            startedAt,
            found: true,
            timeout: false,
            focusAtStart,
            focusAtEnd: focusVar(),
          });
          return;
        }
      }
      if (t > timeoutMs) {
        resolve({
          durationMs: null,
          startedAt,
          found: startedAt !== null,
          timeout: true,
          focusAtStart,
          focusAtEnd: focusVar(),
        });
        return;
      }
      requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
  });
};

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("Tài khoản").fill(USER);
  await page.getByLabel("Mật khẩu").fill(PASS);
  // Nút đổi chữ khi đang tải ("Đang vào…") nên bấm theo `type`, không theo tên.
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 20000 });
}

/** Đo một lần: vào /hom-nay, theo dõi thẻ KPI, trả về ms. */
async function measureOnce(page, { overrideCss }) {
  if (overrideCss) {
    await page.addInitScript((ms) => {
      // `document.documentElement` CHUA TON TAI khi script init chay, nen lan goi
      // dau tien phai chiu duoc null. Loi o day khong chi lam hong lan goi dau —
      // no nem ra truoc dong `addEventListener`, nen trinh nghe DOMContentLoaded
      // KHONG BAO GIO duoc dang ky, va bien vinh vien khong duoc dat. Trieu chung
      // ben ngoai chi la "chuyen dong khong doi", khong he chi ra nguyen nhan.
      const apply = () => {
        if (document.documentElement) {
          document.documentElement.style.setProperty("--nq-beat-focus", `${ms}ms`);
        }
      };
      apply();
      document.addEventListener("DOMContentLoaded", apply);
      window.addEventListener("load", apply);
    }, overrideCss);
  }
  await page.goto(`${BASE}${CHART_PAGE}`, { waitUntil: "commit" });
  return page.evaluate(WATCH_OPACITY, { selector: ".nq-dash-kpi-cell", timeoutMs: 6000 });
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  try {
    console.log("=== 1. Bang nhip trong CSS (nguon su that) ===");
    await login(page);
    const tokens = await page.evaluate(() => {
      const cs = getComputedStyle(document.documentElement);
      const g = (n) => cs.getPropertyValue(n).trim();
      return {
        ack: g("--nq-beat-ack"),
        settle: g("--nq-beat-settle"),
        focus: g("--nq-beat-focus"),
        chapter: g("--nq-beat-chapter"),
        easeOut: g("--nq-ease-out"),
      };
    });
    for (const [k, v] of Object.entries(tokens)) console.log(`  ${k} = ${v}`);

    check(tokens.ack === "140ms", "beat-ack = 140ms", tokens.ack);
    check(tokens.settle === "220ms", "beat-settle = 220ms", tokens.settle);
    check(tokens.focus === "420ms", "beat-focus = 420ms", tokens.focus);
    check(tokens.chapter === "720ms", "beat-chapter = 720ms", tokens.chapter);
    // Chromium bo dau cach khi tra ve, nen phai chuan hoa truoc khi so sanh —
    // so sanh nguyen van se bao loi sai.
    const norm = (s) => s.replace(/\s+/g, "");
    check(
      norm(tokens.easeOut) === "cubic-bezier(0.22,1,0.36,1)",
      "ease-out khop motion.ts",
      tokens.easeOut
    );

    console.log();
    console.log("=== 2. The KPI co chay chuyen dong that khong ===");
    // Trang chu phai tai so lieu truoc khi the KPI xuat hien — dem ngay sau khi
    // dang nhap se ra 0 va bao loi sai.
    await page.goto(`${BASE}${CHART_PAGE}`, { waitUntil: "networkidle" });
    await page.locator(".nq-dash-kpi-cell").first().waitFor({ state: "attached", timeout: 20000 });
    await page.waitForTimeout(1500);
    const cells = await page.locator(".nq-dash-kpi-cell").count();
    console.log(`  so the KPI tren ${CHART_PAGE}: ${cells}`);
    check(cells > 0, "co the KPI de do");
    if (cells === 0) return;

    const baseRun = await measureOnce(page, { overrideCss: null });
    console.log(
      `  lan 1 (CSS goc): chay ${baseRun.durationMs === null ? "(khong do duoc)" : baseRun.durationMs.toFixed(0) + "ms"}` +
        ` — bat dau thay o ${baseRun.startedAt === null ? "?" : baseRun.startedAt.toFixed(0) + "ms"}` +
        ` · --nq-beat-focus luc chay = ${baseRun.focusAtStart}`
    );
    check(baseRun.focusAtStart === "420ms", "lan 1 dung CSS goc", baseRun.focusAtStart);
    check(baseRun.found && !baseRun.timeout, "the KPI chay tu mo sang ro");
    if (!baseRun.found || baseRun.timeout) return;

    console.log();
    console.log(`=== 3. RANG BUOC THAT: ghi de --nq-beat-focus = ${OVERRIDE_MS}ms ===`);
    const overRun = await measureOnce(page, { overrideCss: OVERRIDE_MS });
    console.log(
      `  lan 2 (ghi de ${OVERRIDE_MS}ms): chay ${
        overRun.durationMs === null ? "(khong do duoc)" : overRun.durationMs.toFixed(0) + "ms"
      } · --nq-beat-focus luc chay = ${overRun.focusAtStart}`
    );
    check(
      overRun.focusAtStart === `${OVERRIDE_MS}ms`,
      "lan 2 thuc su dung bien da ghi de",
      overRun.focusAtStart
    );
    check(overRun.found && !overRun.timeout, "lan 2 cung chay duoc");
    if (!overRun.found || overRun.timeout) return;

    const delta = overRun.durationMs - baseRun.durationMs;
    console.log(`  chenh lech: ${delta >= 0 ? "+" : ""}${delta.toFixed(0)}ms`);
    // `beat-focus` tang tu 420ms len 1400ms (+980ms). Do duoc phai thay phan lon
    // muc tang do. Do dai do duoc ngan hon gia tri dat vi 420ms thuong da troi
    // qua truoc khi vong lap kip thay trang thai dau tien. Nguong 400ms du rong
    // de phan biet "co doc bien" (>0.9s) voi "dong bang 420ms" (~0.4s).
    check(
      delta > 400,
      "chuyen dong CHAM HON ro ret khi beat-focus dai hon → doc bien luc chay",
      `${delta >= 0 ? "+" : ""}${delta.toFixed(0)}ms (ky vong ~+980ms)`
    );

    console.log();
    console.log("=== 4. Kiem chung nguoc ===");
    console.log("  Cong doc ma nguon co that su bat duoc loi khong:");
    console.log("    .venv\\Scripts\\python.exe scripts/prove_motion_gate.py");
  } finally {
    await browser.close();
  }

  console.log();
  if (failures) console.log(`=== THAT BAI: ${failures} phep kiem khong dat ===`);
  else console.log("=== DAT: bang nhip trong CSS dieu khien duoc chuyen dong that ===");
  process.exit(failures ? 1 : 0);
}

main().catch((e) => {
  console.error("loi:", e.message);
  process.exit(1);
});
