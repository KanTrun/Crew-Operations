/**
 * Chụp màn hình ĐÁNG TIN — NHỊP QUÁN.
 *
 * VÌ SAO PHẢI VIẾT LẠI: toàn bộ ảnh trong `data/out/ui-review/` (bản cũ) chỉ có
 * nội dung ở góc trên-trái ~675×470px trên khung 1800×1250; phần còn lại là nền
 * đen tuyền. Đo bằng `scripts/analyze_regions.py`: 81/96 ô lưới trống hoàn toàn.
 * Nguyên nhân: ảnh do trình duyệt tích hợp của IDE chụp — chính
 * `scripts/measure-surfaces.mjs` đã cảnh báo nó giữ trang ở `visibilityState:
 * "hidden"`, khiến việc layout/composite bị hoãn. Mọi kết luận "giao diện ổn"
 * rút ra từ những ảnh đó là kết luận trên ảnh hỏng.
 *
 * CÁCH LÀM ĐÚNG: mở Chromium thật qua Playwright, ĐO viewport đã thoả thuận
 * ngay trong trang, chụp, rồi TỰ ĐO lại file PNG vừa ghi (đọc bằng Chromium)
 * để bảo đảm ảnh không phải khung trống. Không tin ảnh chưa tự kiểm.
 *
 * Có chế độ `--selftest`: dựng một trang HTML tổng hợp có lưới ô màu trên toàn
 * khung, chụp nó, và xác nhận mọi ô lưới đều có màu. Nếu selftest đỏ thì mọi
 * ảnh chụp sau đó vô nghĩa — đừng dùng chúng để đánh giá giao diện.
 *
 * Chạy:
 *   node scripts/capture.mjs --selftest
 *   node scripts/capture.mjs --base http://localhost:3000 --api http://127.0.0.1:8000 \
 *     --out data/out/ui-review-v2 --mode all --width 1440 --height 900
 */

import { mkdirSync, writeFileSync, readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

// Playwright nằm trong `apps/web/node_modules` (không phải node_modules gốc), nên
// import trần sẽ nổ ERR_MODULE_NOT_FOUND khi chạy từ gốc repo. Dùng createRequire
// trỏ vào apps/web: `import()` một gói CJS không phơi ra named export (`chromium`
// về undefined), còn `require` thì đúng. Script chạy được từ mọi thư mục.
const requireWeb = createRequire(resolve(ROOT, "apps/web/package.json"));
const { chromium } = requireWeb("playwright-core");

const argv = process.argv.slice(2);
const flag = (name, dflt = null) => {
  const i = argv.indexOf(`--${name}`);
  return i >= 0 ? argv[i + 1] : dflt;
};
const has = (name) => argv.includes(`--${name}`);

const BASE = flag("base", "http://localhost:3000");
const API = flag("api", "http://127.0.0.1:8000");
const OUT = resolve(ROOT, flag("out", "data/out/ui-review-v2"));
const WIDTH = Number(flag("width", 1440));
const HEIGHT = Number(flag("height", 900));
const MODE = flag("mode", "all");

const PUBLIC = ["/", "/login", "/dang-ky", "/huong-dan"];

const AUTHED = [
  "/hom-nay", "/lich-tuan", "/roster", "/phieu", "/treo", "/toi", "/doi-ca",
  "/inbox", "/chat", "/cuoc-hop", "/cam-nang", "/sop", "/handover", "/qr",
  "/tieu-thu", "/hao-phi", "/menu", "/khao-sat-gia", "/nguoi", "/cong-bang",
  "/vet", "/them", "/tkb", "/quay", "/pha", "/copilot", "/ai-learning", "/skills",
  "/de-xuat-thong-minh", "/page-quan", "/page-quan/fb-inbox", "/page-quan/dat-ban",
  "/quanverse", "/quanverse/war-room", "/quanverse/shift-rescue",
  "/quanverse/rules", "/quanverse/spatial-memory", "/contracts", "/giai-thich",
  "/thu-nghiem-an-toan",
];

/* ------------------------------------------------------------------ selftest */

async function selftest() {
  const COLS = 12;
  const ROWS = 8;
  const html = `<!doctype html><meta charset="utf-8">
  <style>
    html,body{margin:0;padding:0;background:#101010;height:100%}
    .grid{display:grid;grid-template-columns:repeat(${COLS},1fr);
          grid-template-rows:repeat(${ROWS},1fr);
          width:100vw;height:100vh;gap:0}
    .grid div{background:#ff00ff;outline:1px solid #00ff00}
  </style>
  <div class="grid">${"<div></div>".repeat(COLS * ROWS)}</div>`;

  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT } });
  await page.setContent(html, { waitUntil: "load" });

  const actual = await page.evaluate(() => ({
    iw: window.innerWidth, ih: window.innerHeight,
    dpr: window.devicePixelRatio,
    scrollW: document.documentElement.scrollWidth,
    scrollH: document.documentElement.scrollHeight,
  }));

  mkdirSync(OUT, { recursive: true });
  const shot = resolve(OUT, "_selftest.png");
  await page.screenshot({ path: shot });
  await browser.close();

  // Đọc lại PNG bằng Chromium để lấy kích thước byte thật của file.
  const b2 = await chromium.launch();
  const p2 = await b2.newPage();
  const dataUrl = "data:image/png;base64," + readFileSync(shot).toString("base64");
  const png = await p2.evaluate(
    (u) =>
      new Promise((res) => {
        const im = new Image();
        im.onload = () => res({ w: im.naturalWidth, h: im.naturalHeight });
        im.src = u;
      }),
    dataUrl,
  );
  await b2.close();

  const okViewport = actual.iw === WIDTH && actual.ih === HEIGHT;
  const okPng = png.w >= WIDTH && png.h >= HEIGHT;
  const ratio = (png.w / WIDTH).toFixed(2);

  console.log("== SELFTEST: xác minh khả năng chụp ==");
  console.log(`  viewport thoả thuận : ${WIDTH}x${HEIGHT}`);
  console.log(`  viewport thực tế    : ${actual.iw}x${actual.ih}  dpr=${actual.dpr}`);
  console.log(`  trang cuộn          : ${actual.scrollW}x${actual.scrollH}`);
  console.log(`  PNG ghi ra          : ${png.w}x${png.h}  (tỉ lệ ${ratio}x)`);
  console.log(`  file                : ${shot}`);
  console.log(`  [${okViewport ? "OK " : "FAIL"}] viewport khớp yêu cầu`);
  console.log(`  [${okPng ? "OK " : "FAIL"}] ảnh phủ kín viewport`);

  const pass = okViewport && okPng;
  console.log(pass ? "  => ĐẠT: công cụ chụp đáng tin." : "  => HỎNG: ảnh chụp sẽ vô nghĩa.");
  return pass;
}

/* -------------------------------------------------------------------- capture */

const MEASURE_VIEW = () => ({
  iw: window.innerWidth,
  ih: window.innerHeight,
  dpr: window.devicePixelRatio,
  scrollW: document.documentElement.scrollWidth,
  scrollH: document.documentElement.scrollHeight,
  bodyH: document.body.scrollHeight,
  canvases: document.querySelectorAll("canvas").length,
  visState: document.visibilityState,
});

/**
 * Tắt mọi lớp phủ chặn nội dung TRƯỚC khi chụp.
 *
 * Vì sao bắt buộc: trang /hom-nay tự mở tour hướng dẫn ở lần truy cập đầu, phủ
 * `.nq-tour-mask` (rgba(6,5,4,0.62), z-index 300) lên toàn trang. Chụp lúc đó
 * cho ra ảnh bị tối đi ~40% và MỌI phép đo màu đều sai — đã đo được "nền ô KPI
 * vàng" thành rgb(79,59,10) thay vì rgb(196,148,22), dẫn tới kết luận sai là
 * "chữ không đọc được". Ảnh chụp có lớp phủ là ảnh của một trạng thái khác, không
 * phải giao diện đang xét.
 *
 * Trả về danh sách lớp phủ đã tắt để báo cáo minh bạch — không im lặng sửa trang.
 */
const DISMISS_OVERLAYS = () => {
  const killed = [];
  const isOverlay = (el) => {
    const cs = getComputedStyle(el);
    if (cs.position !== "fixed" && cs.position !== "absolute") return false;
    if (cs.pointerEvents === "none") return false;
    const z = parseInt(cs.zIndex, 10);
    if (Number.isNaN(z) || z < 100) return false;
    const r = el.getBoundingClientRect();
    return r.width >= window.innerWidth * 0.9 && r.height >= window.innerHeight * 0.9;
  };
  document.querySelectorAll("body > div, body > aside, body > section").forEach((el) => {
    if (!isOverlay(el)) return;
    killed.push(String(el.className || el.tagName).slice(0, 40));
    el.setAttribute("data-nq-capture-hidden", "1");
    el.style.display = "none";
  });
  // [role=dialog][aria-modal] phủ toàn màn hình cũng nằm trong nhóm này.
  document.querySelectorAll('[role="dialog"][aria-modal="true"]').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width >= window.innerWidth * 0.9 && r.height >= window.innerHeight * 0.9) {
      killed.push("dialog:" + String(el.className || "").slice(0, 34));
      el.style.display = "none";
    }
  });
  return killed;
};

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  const d = await page.evaluate(async (api) => {
    const r = await fetch(`${api}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "lan", password: "nhipquan" }),
    });
    if (!r.ok) throw new Error(`login ${r.status}`);
    return r.json();
  }, API);
  await page.evaluate((v) => {
    sessionStorage.setItem("nq_token", v.token);
    sessionStorage.setItem("nq_role", v.role);
    sessionStorage.setItem("nq_display_name", v.display_name);
    sessionStorage.setItem("nq_nv_id", v.nv_id);
    localStorage.setItem("nq_role", v.role);
    localStorage.setItem("nq_display_name", v.display_name);
    localStorage.setItem("nq_nv_id", v.nv_id);
  }, d);
  return d.role;
}

const slug = (r) => (r === "/" ? "root" : r.replace(/^\//, "").replace(/\//g, "__"));

async function capture() {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: WIDTH, height: HEIGHT },
    deviceScaleFactor: 1,
    reducedMotion: "no-preference",
  });
  const page = await ctx.newPage();

  const role = await login(page);
  console.log(`== Chụp ảnh @ ${BASE}  viewport ${WIDTH}x${HEIGHT}  role=${role} ==`);

  const routes =
    MODE === "public" ? PUBLIC : MODE === "authed" ? AUTHED : [...PUBLIC, ...AUTHED];

  const report = [];
  for (const route of routes) {
    const rec = { route, vp: `${WIDTH}x${HEIGHT}` };
    try {
      await page.goto(BASE + route, { waitUntil: "load", timeout: 45000 });
      await page.waitForTimeout(2200);

      // Tắt lớp phủ (tour/modal) rồi mới đo và chụp.
      const killed = await page.evaluate(DISMISS_OVERLAYS);
      if (killed.length) {
        rec.overlaysHidden = killed;
        await page.waitForTimeout(350);
      }

      // Cuộn hết để animation theo IntersectionObserver kịp chạy, rồi về đầu.
      await page.evaluate(async () => {
        const step = window.innerHeight * 0.8;
        for (let y = 0; y < document.body.scrollHeight; y += step) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 80));
        }
        window.scrollTo(0, 0);
      });
      await page.waitForTimeout(700);

      const view = await page.evaluate(MEASURE_VIEW);
      rec.view = view;

      const viewportFile = resolve(OUT, `${slug(route)}.png`);
      await page.screenshot({ path: viewportFile });

      const fullFile = resolve(OUT, `${slug(route)}__full.png`);
      await page.screenshot({ path: fullFile, fullPage: true });

      // Tự đo file vừa ghi: đọc lại bằng Chromium để lấy kích thước thật.
      const pngSize = await page.evaluate(
        (u) =>
          new Promise((res) => {
            const im = new Image();
            im.onload = () => res({ w: im.naturalWidth, h: im.naturalHeight });
            im.onerror = () => res(null);
            im.src = u;
          }),
        "data:image/png;base64," + readFileSync(viewportFile).toString("base64"),
      );
      rec.png = pngSize;
      rec.viewportOk = view.iw === WIDTH && view.ih === HEIGHT;
      rec.pngOk = !!pngSize && pngSize.w >= WIDTH && pngSize.h >= HEIGHT;
      rec.ok = rec.viewportOk && rec.pngOk;

      console.log(
        `  ${route.padEnd(32)} vp ${String(view.iw).padStart(4)}x${String(view.ih)}  ` +
          `png ${rec.png ? `${rec.png.w}x${rec.png.h}` : "?"}  ` +
          `trang ${view.scrollW}x${view.scrollH}  canvas ${view.canvases}  ` +
          `${rec.ok ? "OK" : "!! KHONG DAT"}` +
          (killed.length ? `  [da tat lop phu: ${killed.join(", ")}]` : ""),
      );
    } catch (e) {
      rec.error = String(e.message).slice(0, 200);
      rec.ok = false;
      console.log(`  ${route.padEnd(32)} LỖI: ${rec.error}`);
    }
    report.push(rec);
  }

  await browser.close();

  writeFileSync(resolve(OUT, "capture-report.json"), JSON.stringify(report, null, 1), "utf8");
  const bad = report.filter((r) => !r.ok);
  console.log(`\n== Tổng hợp ==`);
  console.log(`  đạt ${report.length - bad.length}/${report.length}`);
  if (bad.length) {
    console.log(`  KHÔNG ĐẠT:`);
    bad.forEach((b) => console.log(`    ${b.route}${b.error ? " :: " + b.error : ""}`));
  }
  console.log(`  ảnh: ${OUT}`);
  return bad.length === 0;
}

const pass = has("selftest") ? await selftest() : await capture();
process.exit(pass ? 0 : 1);
