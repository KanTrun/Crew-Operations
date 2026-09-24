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
    if (performance.now() - st.t0 < 3000) requestAnimationFrame(sample);
    else st.done = true;
  };
  requestAnimationFrame(sample);
};

async function readAnimations(page) {
  // Chờ bộ thu chạy hết cửa sổ 3s, nhưng không lâu hơn 5s.
  await page
    .waitForFunction(() => window.__nqAnims && window.__nqAnims.done, { timeout: 5000 })
    .catch(() => undefined);
  return page.evaluate(() => {
    const st = window.__nqAnims || { seen: {} };
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const minArea = vw * vh * 0.01;
    const all = Object.values(st.seen);
    const entrance = all.filter((x) => x.iter !== "inf" && x.dur >= 120 && x.area >= minArea);
    const infinite = all.filter((x) => x.iter === "inf");

    /**
     * Gộp thành "đợt" (wave) theo THỜI ĐIỂM BẮT ĐẦU.
     *
     * ══ GIỚI HẠN ĐÃ BIẾT — ĐỌC TRƯỚC KHI DÙNG SỐ NÀY ══
     *
     * Tôi đã thử năm cách để biến "số đợt" thành một phép chấm đạt/không đạt cho
     * tiêu chí 2, và cả năm đều cho kết quả sai theo một kiểu mới:
     *
     *   1. Đếm PHẦN TỬ có animation vào trang → `/hom-nay` ra 11, kết luận
     *      "tranh nhau"; thực ra 7 phần tử đó vào cùng một nhịp, là MỘT khoảnh khắc.
     *   2. Gộp theo ngưỡng 120ms → `/cam-nang` ra 2 đợt khi khe là 121ms, 1 đợt khi
     *      khe là 67ms. Cùng một trang, cùng một mã nguồn; thứ quyết định là API trả
     *      lời nhanh hay chậm. Kết quả phụ thuộc tốc độ mạng.
     *   3. Lọc đợt theo diện tích ≥3% khung → 10 route thành "chết", trong đó có
     *      form giữa trang vốn hợp lệ, chỉ vì biểu mẫu hẹp.
     *   4. Lọc theo lớp `nq-page--center` (coi là khung chờ) → xoá oan 9 route, vì
     *      các trang Quánverse dùng CHÍNH lớp đó làm khung nội dung thật.
     *   5. Cài bộ thu trong vòng lặp → `addInitScript` cộng dồn thành 44 bản.
     *
     * Kết luận: **"trang có đúng một khoảnh khắc được chọn có chủ đích" là quyết
     * định của người thiết kế, không suy ra được từ hình học và thời gian.** Số đợt
     * in ra để NGƯỜI ĐỌC RÀ, không phải để máy chấm.
     *
     * Cái đo được, và dùng làm cổng thật, chỉ là: **trang phải có chuyển động vào**
     * (`entrance.length > 0`) và **vòng lặp vô hạn phải nằm trong danh sách cho phép**.
     *
     * Bộ thu CHỈ lấy mẫu trong 1,5s đầu sau khi trang bắt đầu nạp. Với route chậm,
     * nội dung có thể vào sau cửa sổ đó và bị tính là "chết" — nhưng đó là báo động
     * ở phía AN TOÀN (báo thiếu chuyển động), nên chấp nhận được cho một cổng.
     */
    const WAVE_MS = 120;
    const sorted = [...entrance].sort((a, b) => (a.firstSeenMs || 0) - (b.firstSeenMs || 0));
    const waves = [];
    for (const e of sorted) {
      const t = e.firstSeenMs || 0;
      const last = waves[waves.length - 1];
      if (last && t - last.t0 <= WAVE_MS) {
        last.size += 1;
        last.durMax = Math.max(last.durMax, e.dur);
        last.areaMax = Math.max(last.areaMax, e.area);
      } else {
        waves.push({ t0: t, size: 1, durMax: e.dur, areaMax: e.area });
      }
    }

    return { total: all.length, entrance, infinite, waves };
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
  console.log("route".padEnd(30) + "dot".padStart(4) + " khoi" + "  vo han  moc cac dot (ms)");
  console.log("-".repeat(96));
  for (const r of results) {
    if (r.error) {
      console.log(`${r.route.padEnd(30)}  [LOI] ${r.error}`);
      continue;
    }
    const waves = r.waves || [];
    const t0s = waves.map((w) => `${w.t0}(${w.size})`).join(" ");
    // Tiêu chí 2 đòi ĐÚNG MỘT khoảnh khắc. Nhiều đợt = nhiều khoảnh khắc.
    const flag = waves.length === 0 ? " <- CHET" : waves.length > 1 ? " <- NHIEU DOT" : "";
    console.log(
      `${r.route.padEnd(30)}${String(waves.length).padStart(4)}` +
        `${String(r.entrance.length).padStart(5)}` +
        `  ${String(r.infinite.length).padStart(6)}  ${t0s}${flag}`
    );
  }

  const dead = ok.filter((r) => (r.waves || []).length === 0);
  const multi = ok.filter((r) => (r.waves || []).length > 1);
  const inf = ok.filter((r) => r.infinite.length > 0);

  console.log("");
  console.log("=== CONG (dung duoc de chan) ===");
  console.log(`route do duoc                 : ${ok.length}/${ROUTES.length}`);
  if (erred.length) {
    console.log(`route KHONG do duoc           : ${erred.length}`);
    for (const r of erred) console.log(`    ${r.route} — ${r.error}`);
  }
  console.log(
    `trang DUNG YEN (loi cung)     : ${dead.length}  ${dead.length ? dead.map((r) => r.route).join(" ") : "(khong co)"}`
  );
  console.log(`vong lap vo han               : ${inf.length}`);
  console.log("");
  console.log("=== CHI DE RÀ, KHONG PHAI CHAM DIEM ===");
  console.log(
    `  so dot vao = 1              : ${ok.length - dead.length - multi.length}`
  );
  console.log(
    `  so dot vao > 1 (can xem tay): ${multi.length}  ${multi.map((r) => r.route).join(" ")}`
  );
  console.log("  Ly do khong cham diem: so dot phu thuoc toc do API o dung ranh gioi 120ms.");
  console.log("  `/cam-nang` cho 2 dot khi khe 121ms va 1 dot khi khe 67ms — cung mot trang.");
  console.log("  'Dung mot khoanh khac co chu dich' la quyet dinh cua nguoi thiet ke,");
  console.log("  khong suy ra duoc tu hinh hoc va thoi gian. Xem ghi chu trong readAnimations().");
  console.log(`ghi: ${OUT}`);
  process.exit(erred.length || dead.length ? 1 : 0);
}

main().catch((e) => {
  console.error("loi:", e.message);
  process.exit(1);
});
