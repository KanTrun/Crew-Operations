/**
 * Audit giao diện ĐÃ RENDER trên toàn bộ route — NHỊP QUÁN.
 *
 * Vì sao phải đo trên bản render chứ không đọc mã: mắt người đọc mã luôn thấy
 * "đúng", còn trình duyệt mới biết thật. Lần đo đầu trên `/` cho kết quả
 * 73/79 phần tử có `border-radius: 0px` và 0 phần tử có animation — đúng lời
 * phàn nàn "toàn khung vuông, không có hiệu ứng gì". Những con số đó không suy
 * ra được từ việc đọc `page.tsx`.
 *
 * Script đo cho mỗi route:
 *   - tỉ lệ phần tử VUÔNG (bo góc 0) trên tổng phần tử có bề mặt nhìn thấy
 *   - số phần tử có animation / transition / đổ bóng
 *   - tràn ngang ở bề rộng 375px (máy nhân viên)
 *   - các bậc chữ đang dùng và số bậc khác nhau (thang chữ có bị phân mảnh)
 *   - phần tử bấm được nhỏ hơn 44px (ngưỡng chạm)
 *
 * Chạy:  node scripts/audit_render.mjs [--base http://localhost:3000] [--all]
 * Ghi báo cáo ra data/out/render-audit.json + in bảng tóm tắt.
 */

import { chromium } from "@playwright/test";
import { writeFileSync, mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");

const args = process.argv.slice(2);
const BASE = args.includes("--base") ? args[args.indexOf("--base") + 1] : "http://localhost:3000";
// API chạy ở cổng riêng (demo_api.py :8000). Không gọi qua cổng web: không có
// rewrite /api → 8000, nên fetch vào :3000 sẽ nhận trang HTML và JSON.parse vỡ.
const API = args.includes("--api") ? args[args.indexOf("--api") + 1] : "http://localhost:8000";

// Route công khai đo được không cần đăng nhập.
const PUBLIC = ["/", "/login", "/dang-ky", "/huong-dan"];

// Route cần phiên quản lý — đo sau khi đăng nhập.
const AUTHED = [
  "/hom-nay", "/lich-tuan", "/roster", "/phieu", "/treo", "/toi", "/doi-ca",
  "/inbox", "/chat", "/cuoc-hop", "/cam-nang", "/sop", "/handover", "/qr",
  "/tieu-thu", "/hao-phi", "/menu", "/khao-sat-gia", "/nguoi", "/cong-bang",
  "/vet", "/them", "/tkb", "/quay", "/pha", "/copilot", "/ai-learning", "/skills",
  "/de-xuat-thong-minh", "/page-quan", "/page-quan/fb-inbox", "/page-quan/dat-ban",
  "/quanverse", "/quanverse/war-room", "/quanverse/shift-rescue",
  "/quanverse/rules", "/quanverse/spatial-memory", "/contracts", "/giai-thich",
  "/thu-nghiem-an-toan", "/huong-dan",
];

const MEASURE = () => {
  const all = [...document.querySelectorAll("*")];
  const vis = all.filter((e) => {
    const b = e.getBoundingClientRect();
    const s = getComputedStyle(e);
    return b.width > 40 && b.height > 24 && s.display !== "none" &&
      s.visibility !== "hidden" && s.opacity !== "0";
  });

  // "Bề mặt" = phần tử người dùng NHÌN THẤY như một khối: có viền, có nền
  // không trong suốt, hoặc có đổ bóng. Chỉ những phần tử này mới nên được chấm
  // bo góc — div bố cục trong suốt thì vuông là đúng, không phải lỗi. Bản đo
  // đầu gộp cả hai loại nên ra "83% vuông" nghe nặng hơn thực tế; con số dưới
  // đây mới là thứ người dùng gọi là "khung".
  const surfaced = vis.filter((e) => {
    const s = getComputedStyle(e);
    const hasBorder = parseFloat(s.borderTopWidth) > 0 && s.borderTopStyle !== "none";
    const bg = s.backgroundColor;
    const m = bg.match(/rgba?\(([^)]+)\)/);
    let alpha = 1;
    if (m) {
      const parts = m[1].split(/[,\s/]+/).filter(Boolean);
      alpha = parts.length > 3 ? parseFloat(parts[3]) : 1;
    }
    const hasBg = alpha > 0.08;
    const hasShadow = s.boxShadow !== "none" && s.boxShadow !== "";
    return hasBorder || hasBg || hasShadow;
  });

  const radius = {};
  let square = 0, rounded = 0, animated = 0, transitions = 0, shadows = 0, blurred = 0;
  surfaced.forEach((e) => {
    const s = getComputedStyle(e);
    const br = parseFloat(s.borderTopLeftRadius) || 0;
    radius[s.borderTopLeftRadius] = (radius[s.borderTopLeftRadius] || 0) + 1;
    if (br === 0) square++; else rounded++;
  });
  vis.forEach((e) => {
    const s = getComputedStyle(e);
    if (s.animationName !== "none") animated++;
    if (s.transitionDuration !== "0s") transitions++;
    if (s.boxShadow !== "none") shadows++;
    if (s.backdropFilter !== "none") blurred++;
  });

  // Các bo góc khác nhau đang tồn tại — nhiều giá trị lạ = không có thang bo góc.
  const distinctRadius = Object.keys(radius).filter((r) => parseFloat(r) > 0);

  // Bậc chữ: gom cỡ chữ của phần tử có chữ.
  const sizes = {};
  vis.forEach((e) => {
    if (!e.textContent || !e.textContent.trim()) return;
    if (e.children.length > 0) return;
    const fs = getComputedStyle(e).fontSize;
    sizes[fs] = (sizes[fs] || 0) + 1;
  });

  const small = [...document.querySelectorAll("a,button,[role=button]")].filter((e) => {
    const b = e.getBoundingClientRect();
    const s = getComputedStyle(e);
    return s.display !== "none" && b.width > 0 && b.height > 0 && (b.height < 44 || b.width < 44);
  }).length;

  return {
    visible: vis.length,
    surfaces: surfaced.length,
    square, rounded,
    squarePct: surfaced.length ? Math.round((square / surfaced.length) * 100) : 0,
    distinctRadius: distinctRadius.sort((a, b) => parseFloat(a) - parseFloat(b)),
    animated, transitions, shadows, blurred,
    sizes, sizeSteps: Object.keys(sizes).length,
    smallTargets: small,
    pageH: document.body.scrollHeight,
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
  };
};

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
  const data = await page.evaluate(async (api) => {
    const r = await fetch(`${api}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "lan", password: "nhipquan" }),
    });
    if (!r.ok) throw new Error(`login ${r.status}`);
    return r.json();
  }, API);
  await page.evaluate((d) => {
    sessionStorage.setItem("nq_token", d.token);
    sessionStorage.setItem("nq_role", d.role);
    sessionStorage.setItem("nq_name", d.display_name);
    sessionStorage.setItem("nq_nv", d.nv_id);
    localStorage.setItem("nq_role", d.role);
    localStorage.setItem("nq_name", d.display_name);
    localStorage.setItem("nq_nv", d.nv_id);
  }, data);
}

const rows = [];

async function measure(page, route, viewport) {
  try {
    await page.goto(`${BASE}${route}`, { waitUntil: "domcontentloaded" });
    // Chờ dữ liệu về: các trang này đều gọi API rồi mới dựng bảng.
    await page.waitForTimeout(2600);
    await page.setViewportSize(viewport);
    await page.waitForTimeout(400);
    const m = await page.evaluate(MEASURE);
    rows.push({ route, vp: `${viewport.width}x${viewport.height}`, ...m });
    return m;
  } catch (e) {
    rows.push({ route, vp: `${viewport.width}x${viewport.height}`, error: String(e.message).slice(0, 160) });
    return null;
  }
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await ctx.newPage();

console.log(`== Audit render @ ${BASE} ==`);
console.log(`   (vuông% tính trên BỀ MẶT: phần tử có viền/nền/đổ bóng — thứ người dùng gọi là "khung")`);
const fmt = (m) =>
  `bề mặt ${String(m.surfaces).padStart(3)}  vuông ${String(m.squarePct).padStart(3)}%  ` +
  `bo góc ${String(m.distinctRadius.length).padStart(2)} kiểu  anim ${String(m.animated).padStart(3)}  ` +
  `bóng ${String(m.shadows).padStart(3)}  bậc chữ ${String(m.sizeSteps).padStart(2)}`;

for (const r of PUBLIC) {
  const m = await measure(page, r, { width: 1280, height: 900 });
  if (m) console.log(`  ${r.padEnd(32)} ${fmt(m)}`);
}

await login(page);
console.log(`  (đã đăng nhập — đo route vận hành)`);
for (const r of AUTHED) {
  const m = await measure(page, r, { width: 1280, height: 900 });
  if (m) console.log(`  ${r.padEnd(32)} ${fmt(m)}`);
  else console.log(`  ${r.padEnd(32)} LỖI`);
}

// Tràn ngang trên máy nhân viên (375px) — 5 route đông người dùng nhất.
console.log(`\n== Tràn ngang @ 375px ==`);
for (const r of ["/", "/hom-nay", "/lich-tuan", "/roster", "/phieu", "/chat"]) {
  const m = await measure(page, r, { width: 375, height: 812 });
  if (m) console.log(`  ${r.padEnd(20)} tràn ${String(m.overflowX).padStart(4)}px  vùng chạm nhỏ ${String(m.smallTargets).padStart(3)}/…  vuông ${m.squarePct}%`);
}

await browser.close();

const out = resolve(ROOT, "data/out/render-audit.json");
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify({ base: BASE, at: new Date().toISOString(), rows }, null, 1), "utf8");

// Tổng hợp
const ok = rows.filter((r) => !r.error);
const avgSquare = ok.length ? Math.round(ok.reduce((s, r) => s + (r.squarePct || 0), 0) / ok.length) : 0;
const worst = [...ok].sort((a, b) => (b.squarePct || 0) - (a.squarePct || 0)).slice(0, 12);
const noMotion = ok.filter((r) => r.animated === 0 && r.transitions < 3);
console.log(`\n== Tổng hợp ==`);
console.log(`  route đo được: ${ok.length}/${rows.length}`);
console.log(`  tỉ lệ vuông trung bình: ${avgSquare}%`);
console.log(`  route nhiều khung vuông nhất:`);
worst.forEach((r) => console.log(`    ${String(r.squarePct).padStart(3)}%  ${r.route} (${r.vp})`));
console.log(`  route gần như không có chuyển động: ${noMotion.length}`);
console.log(`  báo cáo: ${out}`);
