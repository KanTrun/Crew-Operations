/**
 * Đo bề mặt render thật — NHỊP QUÁN.
 *
 * Vì sao không dùng trình duyệt tích hợp của IDE: nó giữ trang ở trạng thái
 * `visibilityState: "hidden"`, và trình duyệt hoãn IntersectionObserver /
 * requestAnimationFrame khi trang không hiển thị. Hệ quả: mọi phép đo chuyển
 * động trả về 0 dù hiệu ứng có thật, còn animation chờ cuộn thì không bao giờ
 * chạy — dễ kết luận sai thành "trang không có hiệu ứng".
 *
 * Script này mở Chromium thật (có thể headless tuỳ cờ), đăng nhập bằng API,
 * rồi đo từng route: bán kính bo góc, bóng, transition, animation, và LẤY MẪU
 * SAU KHI CUỘN để animation theo IntersectionObserver kịp chạy.
 *
 * Chạy:
 *   node scripts/measure-surfaces.mjs http://localhost:3000
 */

import { chromium } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";

const BASE = process.argv[2] || "http://localhost:3000";
const API = process.argv[3] || "http://127.0.0.1:8000";
const OUT = "d:/CA-CÔNG-BẰNG/data/out/ui-review";

const ROUTES = [
  "/", "/login", "/huong-dan",
  "/hom-nay", "/roster", "/treo", "/phieu", "/quay", "/lich-tuan",
  "/chat", "/cuoc-hop", "/inbox", "/copilot", "/cam-nang", "/sop",
  "/nguoi", "/doi-ca", "/qr", "/tieu-thu", "/hao-phi", "/menu",
  "/khao-sat-gia", "/vet", "/cong-bang", "/toi", "/tkb", "/handover",
  "/de-xuat-thong-minh", "/ai-learning", "/skills", "/contracts",
  "/page-quan", "/page-quan/fb-inbox", "/page-quan/dat-ban",
  "/quanverse", "/quanverse/war-room", "/quanverse/shift-rescue",
  "/quanverse/rules", "/quanverse/spatial-memory",
  "/them", "/dang-ky", "/pha", "/thu-nghiem-an-toan", "/giai-thich",
];

/** Đo mọi bề mặt thấy được trong viewport hiện tại. */
const MEASURE = () => {
  const radii = new Set();
  let squareSurfaces = 0, totalSurfaces = 0, shadows = 0, transitions = 0;
  const animNames = new Set();
  document.querySelectorAll("*").forEach((el) => {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || cs.opacity === "0") return;
    if (cs.animationName && cs.animationName !== "none") animNames.add(cs.animationName);
    if (cs.transitionDuration && cs.transitionDuration !== "0s") transitions++;
    const b = el.getBoundingClientRect();
    if (b.width < 40 || b.height < 28) return;
    const hasBorder = parseFloat(cs.borderTopWidth) > 0;
    const hasBg = cs.backgroundColor !== "rgba(0, 0, 0, 0)";
    if (!hasBorder && !hasBg) return;
    totalSurfaces++;
    const r = parseFloat(cs.borderTopLeftRadius) || 0;
    radii.add(r);
    if (cs.boxShadow !== "none") shadows++;
    // "Vuông" = không bo góc VÀ không có bóng: hộp phẳng cứng, đúng kiểu bị chê.
    if (r === 0 && cs.boxShadow === "none") squareSurfaces++;
  });
  return {
    radii: [...radii].sort((a, b) => a - b),
    totalSurfaces, squareSurfaces, shadows, transitions,
    animNames: [...animNames],
    squarePct: totalSurfaces ? Math.round((squareSurfaces / totalSurfaces) * 100) : 0,
  };
};

const main = async () => {
  mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  const page = await ctx.newPage();

  // Đăng nhập qua API rồi gieo phiên vào sessionStorage — bỏ qua UI login.
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  const auth = await page.evaluate(async (api) => {
    const r = await fetch(`${api}/api/v1/auth/login`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "lan", password: "nhipquan" }),
    });
    if (!r.ok) return null;
    const d = await r.json();
    sessionStorage.setItem("nq_token", d.token);
    sessionStorage.setItem("nq_role", d.role);
    sessionStorage.setItem("nq_display_name", d.display_name);
    sessionStorage.setItem("nq_nv_id", d.nv_id);
    return d.role;
  }, API);

  const rows = [];
  for (const route of ROUTES) {
    try {
      await page.goto(BASE + route, { waitUntil: "load", timeout: 30000 });
      await page.waitForTimeout(1400);
      // Cuộn hết trang rồi về đầu: animation theo IntersectionObserver chỉ chạy
      // khi phần tử thực sự vào khung nhìn.
      await page.evaluate(async () => {
        const step = window.innerHeight * 0.8;
        for (let y = 0; y < document.body.scrollHeight; y += step) {
          window.scrollTo(0, y);
          await new Promise((r) => setTimeout(r, 90));
        }
        window.scrollTo(0, 0);
      });
      await page.waitForTimeout(500);
      const m = await page.evaluate(MEASURE);
      const title = await page.title();
      rows.push({ route, title: title.slice(0, 40), ...m, ok: true });
    } catch (e) {
      rows.push({ route, ok: false, error: String(e).slice(0, 80) });
    }
  }

  await browser.close();

  rows.sort((a, b) => (b.squarePct || 0) - (a.squarePct || 0));
  const pad = (s, n) => String(s).padEnd(n);
  console.log(`\nauth=${auth}  routes=${rows.length}\n`);
  console.log(pad("route", 30) + pad("%vuong", 8) + pad("beMat", 7) + pad("bong", 6) + pad("trans", 7) + "anim");
  console.log("-".repeat(84));
  for (const r of rows) {
    if (!r.ok) { console.log(pad(r.route, 30) + "LỖI  " + r.error); continue; }
    console.log(
      pad(r.route, 30) + pad(r.squarePct + "%", 8) + pad(r.totalSurfaces, 7) +
      pad(r.shadows, 6) + pad(r.transitions, 7) + (r.animNames.slice(0, 2).join(",") || "-")
    );
  }
  writeFileSync(`${OUT}/measure-surfaces.json`, JSON.stringify({ auth, rows }, null, 1), "utf8");
  console.log(`\nChi tiết: ${OUT}/measure-surfaces.json`);
};

main().catch((e) => { console.error(e); process.exit(1); });
