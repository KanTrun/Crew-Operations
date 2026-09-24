/**
 * Kiem ke MOI vong lap vo han dang chay tren ban render, theo tung route.
 *
 * Vi sao can ban RUNTIME ben canh cong doc ma nguon (`audit_motion_tokens.py`):
 * cong doc ma nguon chi soi chuoi `repeat: Infinity` trong tep dung `framer-motion`
 * va `animation: ... infinite` trong CSS. No khong tra loi duoc "tren trang nay,
 * luc nay, cai gi dang chay mai". Ban do da bo sot dung dieu do: toi tung khang dinh
 * "khong con vong lap vo han ngoai danh sach cho phep" trong khi 17 route van con
 * animation CSS chay mai — khang dinh chi lo ra la SAI khi do bang
 * `document.getAnimations()`.
 *
 * Nguyen tac: vong lap vo han duoc phep khi va chi khi no thuoc mot trong ba nhom:
 *   1. BAO DANG TAI  — nguoi dung can biet may dang lam viec.
 *   2. MA HOA TRANG THAI — vong lap chi ton tai khi co dieu kien.
 *   3. BIEU TUONG THUONG HIEU — gan voi dung viec he thong lam.
 * Vong lap trang tri tren phan tu luon hien thi khong thuoc nhom nao.
 *
 * Chay: node scripts/audit_infinite_runtime.mjs [--base URL]
 */

import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const { chromium } = require("./../apps/web/node_modules/playwright");

const args = process.argv.slice(2);
const getArg = (n, d) => {
  const i = args.indexOf(n);
  return i >= 0 ? args[i + 1] : d;
};
const BASE = getArg("--base", "http://localhost:3001");
const USER = process.env.NQ_USER || "lan";
const PASS = process.env.NQ_PASS || "nhipquan";

/**
 * Danh sach cho phep anh xa ten animation -> nhom + ly do.
 *
 * Phai khop `CSS_INFINITE_ALLOWED` trong `audit_motion_tokens.py`. Hai cong kiem
 * cung mot luat o hai tang: tang ma nguon bat duoc luc viet, tang runtime bat duoc
 * luc chay (ke ca animation do thu vien ngoai sinh ra, ma tang ma nguon khong thay).
 */
const ALLOWED = {
  pulse: ["dang-tai", "Tailwind animate-pulse — bao dang tai"],
  "nq-shimmer": ["dang-tai", "skeleton bao dang tai"],
  "nq-pulse-load": ["dang-tai", "bao dang tai du lieu"],
  "nq-spin": ["dang-tai", "spinner nut dang gui / khoi cho, co aria-busy"],
  "nq-hz-pulse": ["trang-thai", "chi chay tren .is-urgent — dong hoa tiet diem qua han"],
  "nq-ops-ring-spin": ["trang-thai", "chi chay tren vong --ai — bao tro ly AI dang hoat dong"],
  "nq-pulse-beat": ["thuong-hieu", "nam vach nhịp o trang chu, aria-hidden"],
  "nq-ar-spin": ["thuong-hieu", "o ngam AR xoay cham 8s — bieu tuong thiet bi quet khong gian"],
};

const ROUTES = [
  "/", "/ai-learning", "/cam-nang", "/chat", "/cong-bang", "/contracts", "/copilot",
  "/cuoc-hop", "/dang-ky", "/de-xuat-thong-minh", "/doi-ca", "/giai-thich", "/handover",
  "/hao-phi", "/hom-nay", "/huong-dan", "/inbox", "/khao-sat-gia", "/lich-tuan", "/login",
  "/menu", "/nguoi", "/page-quan", "/page-quan/dat-ban", "/page-quan/fb-inbox", "/pha",
  "/phieu", "/qr", "/quanverse", "/quanverse/rules", "/quanverse/shift-rescue",
  "/quanverse/spatial-memory", "/quanverse/war-room", "/quay", "/roster", "/skills",
  "/sop", "/them", "/thu-nghiem-an-toan", "/tieu-thu", "/tkb", "/toi", "/treo", "/vet",
];

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
await page.getByLabel("Tài khoản").fill(USER);
await page.getByLabel("Mật khẩu").fill(PASS);
await page.locator('button[type="submit"]').click();
await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 20000 });

const seen = new Map();
const unknown = [];
let erred = 0;

for (const route of ROUTES) {
  const alive = await fetch(`${BASE}/login`, { method: "HEAD" })
    .then((r) => r.ok)
    .catch(() => false);
  if (!alive) {
    console.error(`[!] server khong phan hoi tai ${route} — dung do.`);
    erred += 1;
    break;
  }
  await page.goto(`${BASE}${route}`, { waitUntil: "commit" });
  // Cho du de trang kip hien khung cho / skeleton roi moi lay mau.
  await page.waitForTimeout(350);
  const found = await page.evaluate(() => {
    const out = [];
    for (const a of document.getAnimations ? document.getAnimations() : []) {
      let t;
      try {
        t = a.effect?.getTiming?.() || {};
      } catch {
        continue;
      }
      if (t.iterations !== Infinity) continue;
      const el = a.effect?.target;
      if (!el) continue;
      const cs = getComputedStyle(el);
      out.push({
        isCss: cs.animationName && cs.animationName !== "none",
        animName: cs.animationName || "(JS)",
        dur: cs.animationDuration,
        tag: el.tagName.toLowerCase(),
        cls: (typeof el.className === "string" ? el.className : "").split(/\s+/).slice(0, 3).join("."),
        text: (el.textContent || "").trim().slice(0, 34),
      });
    }
    return out;
  });
  for (const f of found) {
    const key = `${f.isCss ? "CSS" : "JS"}|${f.animName}|${f.cls}`;
    if (!seen.has(key)) seen.set(key, { ...f, routes: [] });
    seen.get(key).routes.push(route);
    if (!ALLOWED[f.animName]) {
      unknown.push({ route, name: f.animName, sel: `${f.tag}.${f.cls}`, text: f.text });
    }
  }
}

console.log(`=== VONG LAP VO HAN DANG CHAY — ${ROUTES.length} route @1440x900 ===`);
console.log("");
for (const [, v] of [...seen.entries()].sort((a, b) => b[1].routes.length - a[1].routes.length)) {
  const allow = ALLOWED[v.animName];
  const mark = allow ? `OK  [${allow[0]}]` : "KHONG DUOC PHEP";
  console.log(
    `[${v.isCss ? "CSS" : "JS "}] ${v.animName.padEnd(18)} ${v.dur.padEnd(9)} ${mark}`
  );
  console.log(`      ${v.tag}.${v.cls}  "${v.text}"`);
  console.log(`      tren ${v.routes.length} route: ${v.routes.join(" ")}`);
  console.log("");
}

console.log("=== KET LUAN ===");
console.log(`loai animation vo han gap : ${seen.size}`);
console.log(`loai KHONG nam trong danh sach cho phep : ${new Set(unknown.map((u) => u.name)).size}`);
if (unknown.length) {
  for (const u of unknown.slice(0, 12)) {
    console.log(`  ${u.route}  ${u.name}  ${u.sel}  "${u.text}"`);
  }
} else {
  console.log("  (khong co) — moi vong lap deu thuoc nhom dang-tai / trang-thai / thuong-hieu");
}
if (erred) console.log(`loi: ${erred}`);

await browser.close();
process.exit(unknown.length || erred ? 1 : 0);
