/**
 * Dem "khoanh khac chuyen dong" tren tung route — do dung cau hoi cua tieu chi 2.
 *
 * Tieu chi 2: "moi trang dung 1 khoanh khac hieu ung manh".
 *
 * Cach do KHONG phai dem so animation (moi hover deu co transition, dem het thi
 * trang nao cung tram cai). Do cai ma nguoi dung THUC SU thay khi trang vua mo:
 *
 *   - chuyen dong CHAY MOT LAN luc tai trang (entrance), khong phai hover;
 *   - tren mot khoi du lon de doc ra la "khoanh khac" (khong phai mot chip nho).
 *
 * Ba con so can biet cho moi route:
 *   vao   = so khoi co entrance animation  → tieu chi doi DUNG 1
 *   vo han= so vong lap vo han             → da xu ly o tieu chi 5/6
 *   hover = so phan tu chi co transition   → binh thuong, khong tinh
 *
 * Y nghia hai dau:
 *   0  = trang "chet" — khong co khoanh khac nao, mo ra la dung yen
 *   >2 = nhieu khoi cung tranh chuyen dong → khong con la "mot" khoanh khac
 *
 * Chay: node scripts/audit_motion_moments.mjs [--base URL]
 */

import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("./../apps/web/node_modules/playwright");

const args = process.argv.slice(2);
const getArg = (n, d) => {
  const i = args.indexOf(n);
  return i >= 0 ? args[i + 1] : d;
};
const BASE = getArg("--base", "http://localhost:3001");
const OUT = getArg("--out", "data/out/motion-moments.json");

const ROUTES = [
  "/", "/ai-learning", "/cam-nang", "/chat", "/cong-bang", "/contracts", "/copilot",
  "/cuoc-hop", "/dang-ky", "/de-xuat-thong-minh", "/doi-ca", "/giai-thich", "/handover",
  "/hao-phi", "/hom-nay", "/huong-dan", "/inbox", "/khao-sat-gia", "/lich-tuan", "/login",
  "/menu", "/nguoi", "/page-quan", "/page-quan/dat-ban", "/page-quan/fb-inbox", "/pha",
  "/phieu", "/qr", "/quanverse", "/quanverse/rules", "/quanverse/shift-rescue",
  "/quanverse/spatial-memory", "/quanverse/war-room", "/quay", "/roster", "/skills",
  "/sop", "/them", "/thu-nghiem-an-toan", "/tieu-thu", "/tkb", "/toi", "/treo", "/vet",
];

/**
 * Thu thập animation bằng cách LẤY MẪU LIÊN TỤC trong một cửa sổ thời gian, thay vì
 * lấy một lần tại một thời điểm.
 *
 * Vì sao phải làm thế: cách đo "lấy mẫu ngay sau khi trang commit" là một cuộc đua.
 * Animation vào trang do React dựng SAU khi thuỷ hợp, chạy 240–420ms, rồi biến mất
 * (fill mode `both` giữ lại nhưng danh sách có thể đã dọn). Lần đo thứ nhất tôi chờ
 * 180ms → báo 5 route Quánverse "chết". Lần thứ hai lấy mẫu ở khung hình thứ hai →
 * báo một danh sách "chết" KHÁC HẲN (7 route) và số vòng lặp vô hạn tụt từ 17 xuống 4.
 *
 * Kết quả đổi giữa hai lần chạy nghĩa là phép đo không đáng tin, không phải trang
 * đổi. Cách sửa: cài bộ thu NGAY TRƯỚC khi trang nạp (addInitScript), rồi gom HỢP
 * của mọi animation thấy được trong 1,5 giây. Không còn phụ thuộc thời điểm.
 */
const COLLECTOR = () => {
  window.__nqAnims = { seen: {}, t0: performance.now(), done: false };

  const cls = (el) =>
    (el.className && typeof el.className === "string" ? el.className : "")
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 3)
      .join(".");

  const sample = () => {
    const st = window.__nqAnims;
    if (!st || st.done) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const anims = document.getAnimations ? document.getAnimations() : [];
    for (const a of anims) {
      let t;
      try {
        t = a.effect?.getTiming?.() || {};
      } catch {
        continue;
      }
      const target = a.effect?.target;
      if (!target) continue;
      const iter = t.iterations === undefined ? 1 : t.iterations;
      const dur = typeof t.duration === "number" ? t.duration : 0;
      let r = { width: 0, height: 0, left: 0, top: 0, right: 0, bottom: 0 };
      try {
        r = target.getBoundingClientRect();
      } catch {
        /* bo qua */
      }
      const visW = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0));
      const visH = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
      const area = Math.round(visW * visH);
      const tag = target.tagName ? target.tagName.toLowerCase() : "?";
      const c = cls(target);
      const key = `${iter === Infinity ? "inf" : iter}|${Math.round(dur)}|${tag}.${c}`;
      if (!st.seen[key]) {
        st.seen[key] = {
          iter: iter === Infinity ? "inf" : iter,
          dur,
          area,
          tag,
          cls: c,
          firstSeenMs: Math.round(performance.now() - st.t0),
        };
      }
    }
    if (performance.now() - st.t0 < 1500) requestAnimationFrame(sample);
    else st.done = true;
  };
  requestAnimationFrame(sample);
};

async function readAnimations(page) {
  // Chờ bộ thu chạy hết cửa sổ, nhưng không lâu hơn 2,5s.
  await page
    .waitForFunction(() => window.__nqAnims && window.__nqAnims.done, { timeout: 2500 })
    .catch(() => undefined);
  return page.evaluate(() => {
    const st = window.__nqAnims || { seen: {} };
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const minArea = vw * vh * 0.01;
    const all = Object.values(st.seen);
    const entrance = all.filter((x) => x.iter !== "inf" && x.dur >= 120 && x.area >= minArea);
    const infinite = all.filter((x) => x.iter === "inf");
    return { total: all.length, entrance, infinite };
  });
}

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("Tài khoản").fill(process.env.NQ_USER || "lan");
  await page.getByLabel("Mật khẩu").fill(process.env.NQ_PASS || "nhipquan");
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 20000 });
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const results = [];

  try {
    await login(page);
    // Cài bộ thu MỘT LẦN cho cả phiên. `addInitScript` cộng dồn nên chỉ được gọi ở đây.
    await page.addInitScript(COLLECTOR);
    for (const route of ROUTES) {
      const alive = await fetch(`${BASE}/login`, { method: "HEAD" })
        .then((r) => r.ok)
        .catch(() => false);
      if (!alive) {
        console.error(`\n[!] server :3001 khong phan hoi tai ${route} — dung do.`);
        break;
      }
      try {
        // Phai lay mau NGAY, khong cho `networkidle`: cac animation vao trang dung
        // fill mode `both` nen chung CHAY XONG va roi khoi danh sach truoc khi
        // `networkidle` kip tra ve. Lan do dau tien cho 180ms va vi the bao 5 route
        // Quanverse la "CHET" — trong khi `experience.css` co `nq-fade-up` 240-280ms,
        // `nq-canvas-in` 420ms, `nq-detail-in` 280ms. Cac route do CO chuyen dong;
        // cong cu lay mau qua muon. Doi tu `commit` sang lay ngay la sua duoc.
        // KHÔNG cài bộ thu ở đây. `page.addInitScript` cộng dồn: mỗi lần gọi là thêm
        // một script chạy MÃI về sau. Gọi trong vòng lặp thì tới route thứ 44 có 44
        // bản cùng ghi vào `window.__nqAnims`, mỗi bản lại reset nó — dữ liệu thành
        // rác, và mọi route báo cùng một lớp `nq-page--center py-16` (thực ra là của
        // route nào đó chạy trước). Cài MỘT LẦN trước vòng lặp, bên dưới.
        await page.goto(`${BASE}${route}`, { waitUntil: "commit", timeout: 30000 });
        const r = await readAnimations(page);
        // Chan doan trang loi nhu o audit_emphasis.
        const isErr = await page.evaluate(() =>
          /Application error|client-side exception/i.test(document.body?.innerText || "")
        );
        if (isErr) {
          results.push({ route, error: "trang loi (error boundary)" });
          continue;
        }
        results.push({ route, ...r });
      } catch (e) {
        results.push({ route, error: String(e.message).slice(0, 90) });
      }
    }
  } finally {
    await browser.close();
  }

  mkdirSync(dirname(OUT), { recursive: true });
  writeFileSync(OUT, JSON.stringify({ base: BASE, results }, null, 2), "utf8");

  const ok = results.filter((r) => !r.error);
  const erred = results.filter((r) => r.error);

  console.log(`=== KHOANH KHAC CHUYEN DONG — ${ok.length}/${ROUTES.length} route @1440x900 ===`);
  console.log("");
  console.log("route".padEnd(30) + "vao".padStart(4) + "  vo han" + "  khoi vao trang");
  console.log("-".repeat(96));
  for (const r of results) {
    if (r.error) {
      console.log(`${r.route.padEnd(30)}  [LOI] ${r.error}`);
      continue;
    }
    const names = r.entrance.map((e) => `${e.tag}.${e.cls}`).join(", ").slice(0, 52);
    const flag = r.entrance.length === 0 ? " <- CHET" : r.entrance.length > 2 ? " <- NHIEU" : "";
    console.log(
      `${r.route.padEnd(30)}${String(r.entrance.length).padStart(4)}` +
        `  ${String(r.infinite.length).padStart(6)}  ${names}${flag}`
    );
  }

  const dead = ok.filter((r) => r.entrance.length === 0);
  const many = ok.filter((r) => r.entrance.length > 2);
  const inf = ok.filter((r) => r.infinite.length > 0);

  console.log("");
  console.log(`route do duoc              : ${ok.length}/${ROUTES.length}`);
  if (erred.length) {
    console.log(`route KHONG do duoc        : ${erred.length}`);
    for (const r of erred) console.log(`    ${r.route} — ${r.error}`);
  }
  console.log(`VAO = 0 (trang dung yen)   : ${dead.length}  ${dead.map((r) => r.route).join(" ")}`);
  console.log(`VAO > 2 (tranh nhau)       : ${many.length}  ${many.map((r) => r.route).join(" ")}`);
  console.log(`con vong lap vo han        : ${inf.length}  ${inf.map((r) => r.route).join(" ")}`);
  console.log(`ghi: ${OUT}`);
  process.exit(erred.length ? 1 : 0);
}

main().catch((e) => {
  console.error("loi:", e.message);
  process.exit(1);
});
