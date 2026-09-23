/**
 * Quét tương phản màu chữ/nền THẬT trên bản render — ngưỡng WCAG AA 4.5:1.
 *
 * Vì sao đo trên trình duyệt chứ không đọc CSS: màu chữ hiện tại là kết quả của
 * NHIỀU lớp (màu gốc, opacity của tổ tiên, color-mix, blend mode). Đọc file CSS
 * chỉ thấy lớp cuối cùng — đúng lớp mà người dùng không hề nhìn thấy.
 *
 * Script mở Chromium thật, đăng nhập, rồi với từng phần tử có chữ:
 *   - lấy màu chữ và màu nền THỰC TẾ (đi ngược cây để tìm nền không trong suốt đầu tiên)
 *   - tính tỉ lệ tương phản theo WCAG 2.1
 *   - ghi lại mọi cặp dưới 4.5:1 (chuẩn) và dưới 3:1 (chữ lớn)
 *
 * Chạy:  node scripts/contrast.mjs [--base http://localhost:3000] [--out data/out/contrast.json]
 */


import { mkdirSync, writeFileSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const requireWeb = createRequire(resolve(ROOT, "apps/web/package.json"));
const { chromium } = requireWeb("playwright-core");

const argv = process.argv.slice(2);
const flag = (n, d) => (argv.indexOf(`--${n}`) >= 0 ? argv[argv.indexOf(`--${n}`) + 1] : d);
const BASE = flag("base", "http://localhost:3000");
const API = flag("api", "http://127.0.0.1:8000");
const OUT = resolve(ROOT, flag("out", "data/out/contrast.json"));

const ROUTES = [
  "/", "/login", "/dang-ky", "/huong-dan", "/hom-nay", "/lich-tuan", "/roster",
  "/phieu", "/treo", "/toi", "/doi-ca", "/inbox", "/chat", "/cuoc-hop",
  "/cam-nang", "/sop", "/handover", "/qr", "/tieu-thu", "/hao-phi", "/menu",
  "/khao-sat-gia", "/nguoi", "/cong-bang", "/vet", "/them", "/tkb", "/quay",
  "/pha", "/copilot", "/ai-learning", "/skills", "/de-xuat-thong-minh",
  "/page-quan", "/page-quan/fb-inbox", "/page-quan/dat-ban", "/quanverse",
  "/quanverse/war-room", "/quanverse/shift-rescue", "/quanverse/rules",
  "/quanverse/spatial-memory", "/contracts", "/giai-thich", "/thu-nghiem-an-toan",
];

/**
 * Tắt lớp phủ toàn màn hình trước khi đo.
 *
 * Vì sao: /hom-nay tự mở tour hướng dẫn ở lần truy cập đầu, phủ `.nq-tour-mask`
 * rgba(6,5,4,0.62) lên toàn trang. Mọi phép đo màu lúc đó đều bị tối đi ~40% và
 * cho ra kết luận sai (đã từng đo "nền ô KPI vàng" thành rgb(79,59,10) thay vì
 * rgb(196,148,22)). Đây là lớp phủ của MỘT trạng thái khác, không phải giao diện
 * đang xét, nên phải tắt trước khi chấm tương phản.
 */
const DISMISS_OVERLAYS = () => {
  const killed = [];
  const hide = (el, tag) => {
    killed.push(tag);
    el.style.display = "none";
  };
  document.querySelectorAll("body > div, body > aside, body > section").forEach((el) => {
    const cs = getComputedStyle(el);
    if (cs.position !== "fixed" && cs.position !== "absolute") return;
    if (cs.pointerEvents === "none") return;
    const z = parseInt(cs.zIndex, 10);
    if (Number.isNaN(z) || z < 100) return;
    const r = el.getBoundingClientRect();
    if (r.width >= window.innerWidth * 0.9 && r.height >= window.innerHeight * 0.9) {
      hide(el, String(el.className || el.tagName).slice(0, 40));
    }
  });
  document.querySelectorAll('[role="dialog"][aria-modal="true"]').forEach((el) => {
    const r = el.getBoundingClientRect();
    if (r.width >= window.innerWidth * 0.9 && r.height >= window.innerHeight * 0.9) {
      hide(el, "dialog:" + String(el.className || "").slice(0, 34));
    }
  });
  return killed;
};

/**
 * Do tuong phan cho moi phan tu co chu rieng.
 *
 * BAY DA GAP: Chromium tra ve `color(srgb 0.769 0.581 0.086)` (khong phai
 * `rgb(...)`) khi mau sinh ra tu `color-mix()` / oklab. Bo doc mau chi hieu
 * `rgb()` se tra null cho lop nen THAT, phep di nguoc cay tut xuong nen trang,
 * va bao dong gia kieu "chu den tren nen den" — trong khi thuc te la chu den
 * tren nen vang (6.86:1, dat). Phat hien nho doi chieu chuoi nen cua cay DOM
 * trong `verify_contrast_case.mjs`. Phai doc duoc MOI cu phap mau hien dai.
 */
const AUDIT = () => {
  const parse = (s) => {
    const str = String(s);
    // rgb()/rgba() — ke ca cu phap phan cach bang dau cach cua CSS4.
    let m = str.match(/rgba?\(([^)]+)\)/);
    if (m) {
      const p = m[1].split(/[,\s/]+/).filter(Boolean).map(Number);
      if (p.length >= 3 && p.slice(0, 3).every((v) => !Number.isNaN(v))) {
        return { r: p[0], g: p[1], b: p[2], a: p.length > 3 && !Number.isNaN(p[3]) ? p[3] : 1 };
      }
    }
    // color(srgb r g b [/ a]) — thanh phan 0..1.
    m = str.match(/color\(\s*srgb\s+([^)]+)\)/);
    if (m) {
      const p = m[1].split(/[\s/]+/).filter(Boolean).map(Number);
      if (p.length >= 3 && p.slice(0, 3).every((v) => !Number.isNaN(v))) {
        return {
          r: p[0] * 255, g: p[1] * 255, b: p[2] * 255,
          a: p.length > 3 && !Number.isNaN(p[3]) ? p[3] : 1,
        };
      }
    }
    return null;
  };

  const lum = (c) => {
    const f = (v) => {
      const x = v / 255;
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const over = (fg, bg) => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };

  const findings = [];
  const seen = new Set();

  document.querySelectorAll("*").forEach((el) => {
    // Chi phan tu co chu truc tiep.
    const hasText = Array.from(el.childNodes).some(
      (n) => n.nodeType === 3 && (n.textContent || "").trim().length > 1,
    );
    if (!hasText) return;

    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return;
    const b = el.getBoundingClientRect();
    if (b.width < 2 || b.height < 2) return;

    // Trạng thái VÔ HIỆU nằm ngoài phạm vi WCAG 1.4.3: điều khiển bị tắt không
    // phải chỗ để đọc, và thiết kế mờ nó đi là chủ ý. Không loại trừ thì bộ quét
    // báo lỗi cho mọi nút disabled (`opacity: 0.5` làm tương phản tụt còn 2.8:1)
    // — đã kiểm chứng: cả 5 ca `.nq-btn-primary` bị báo đều `:disabled=true`.
    if (el.matches(":disabled") || el.getAttribute("aria-disabled") === "true") return;
    // Phần tử nằm trong vùng bị vô hiệu (fieldset[disabled]) cũng vậy.
    if (el.closest("fieldset[disabled], [aria-disabled='true']")) return;

    let fg = parse(cs.color);
    if (!fg) return;
    const opacity = parseFloat(cs.opacity);
    if (!Number.isNaN(opacity) && opacity < 1) fg.a *= opacity;

    // Di nguoc cay tim nen khong trong suot dau tien.
    // Phai doc CA `background-image` (gradient): nut dang bat trong he nay ve nen
    // bang `linear-gradient(...)` voi `background-color` trong suot, nen neu chi
    // doc background-color thi phep di nguoc se tut xuong nen trang va bao dong
    // gia "chu den tren nen den" trong khi thuc te la chu dam tren nen vang.
    let node = el, bg = null;
    while (node && node !== document.documentElement.parentElement) {
      const bcs = getComputedStyle(node);
      let c = parse(bcs.backgroundColor);
      if (!c || c.a <= 0.05) {
        // Gradient: lay diem mau dau tien lam mau nen dai dien.
        const g = String(bcs.backgroundImage || "");
        if (g && g !== "none") {
          const stops = g.match(/(?:rgba?\([^)]+\)|color\(\s*srgb\s+[^)]+\))/g);
          if (stops && stops.length) {
            const gc = parse(stops[0]);
            if (gc) c = gc;
          }
        }
      }
      if (c && c.a > 0.05) {
        bg = bg ? over(bg, c) : c;
        if (bg.a >= 0.999) break;
      }
      node = node.parentElement;
    }
    if (!bg) bg = { r: 14, g: 12, b: 10, a: 1 };
    if (bg.a < 1) bg = over(bg, { r: 14, g: 12, b: 10, a: 1 });

    const fgc = fg.a < 1 ? over(fg, bg) : fg;
    const r = ratio(fgc, bg);

    const px = parseFloat(cs.fontSize);
    const bold = parseInt(cs.fontWeight, 10) >= 700;
    // WCAG: "chu lon" = >=24px, hoac >=18.66px neu dam.
    const large = px >= 24 || (bold && px >= 18.66);
    const need = large ? 3.0 : 4.5;

    if (r < need) {
      const text = (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 62);
      const key = `${cs.color}|${px}|${text}`;
      if (seen.has(key)) return;
      seen.add(key);
      const hex = (c) =>
        "#" + [c.r, c.g, c.b].map((v) => Math.round(v).toString(16).padStart(2, "0")).join("");
      findings.push({
        text,
        cls: String(el.className || "").slice(0, 110),
        tag: el.tagName.toLowerCase(),
        color: cs.color,
        bg: hex(bg),
        fgHex: hex(fgc),
        ratio: Math.round(r * 100) / 100,
        need,
        px,
        bold,
        large,
      });
    }
  });

  return findings;
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
  }, d);
}

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const page = await ctx.newPage();
await login(page);

const report = {};
const overlays = {};
let total = 0;
console.log(`== Tuong phan WCAG AA @ ${BASE} ==`);
for (const route of ROUTES) {
  try {
    await page.goto(BASE + route, { waitUntil: "load", timeout: 45000 });
    await page.waitForTimeout(1600);
    const killed = await page.evaluate(DISMISS_OVERLAYS);
    if (killed.length) {
      overlays[route] = killed;
      await page.waitForTimeout(300);
    }
    await page.evaluate(async () => {
      const step = window.innerHeight * 0.8;
      for (let y = 0; y < document.body.scrollHeight; y += step) {
        window.scrollTo(0, y);
        await new Promise((r) => setTimeout(r, 70));
      }
      window.scrollTo(0, 0);
    });
    await page.waitForTimeout(500);
    const f = await page.evaluate(AUDIT);
    report[route] = f;
    total += f.length;
    if (f.length) {
      console.log(`  ${route.padEnd(30)} ${String(f.length).padStart(3)} cap duoi nguong`);
    }
  } catch (e) {
    report[route] = [{ error: String(e.message).slice(0, 120) }];
    console.log(`  ${route.padEnd(30)} LOI ${String(e.message).slice(0, 70)}`);
  }
}
await browser.close();

mkdirSync(dirname(OUT), { recursive: true });
writeFileSync(OUT, JSON.stringify({ overlays, report }, null, 1), "utf8");

if (Object.keys(overlays).length) {
  console.log(`\n== Lop phu da tat truoc khi do (khong phai giao dien dang xet) ==`);
  for (const [r, list] of Object.entries(overlays)) console.log(`  ${r}: ${list.join(", ")}`);
}

// Gom nhom theo cap mau de biet cho nao can sua goc.
const byPair = {};
for (const [route, f] of Object.entries(report)) {
  for (const x of f) {
    if (x.error) continue;
    const k = `${x.fgHex} tren ${x.bg}  (can ${x.need})`;
    byPair[k] = byPair[k] || { n: 0, routes: new Set(), ex: x };
    byPair[k].n++;
    byPair[k].routes.add(route);
  }
}

console.log(`\n== TONG: ${total} cap duoi nguong ==`);
const sorted = Object.entries(byPair).sort((a, b) => b[1].n - a[1].n);
console.log(`== ${sorted.length} cap mau khac nhau ==`);
for (const [k, v] of sorted) {
  const ex = v.ex;
  console.log(
    `  ${String(v.n).padStart(4)}x  ${k}  [${[...v.routes].slice(0, 3).join(", ")}]` +
      `\n        vi du: "${ex.text}"  (${ex.px}px${ex.bold ? " dam" : ""})  class=${ex.cls.slice(0, 70)}`,
  );
}
console.log(`\njson -> ${OUT}`);
