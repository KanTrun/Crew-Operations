/**
 * Chup RIENG cac o KPI co tone (warn/ok/danger) de kiem tra chu co doc duoc.
 *
 * NGHI VAN: `Summary` va `kpi-card` dat dong thoi hai class:
 *   - `nq-ink-on-solid`  -> color: var(--nq-accent-ink) = #14100c (gan nhu den)
 *   - `nq-surface-tile`  -> background: color-mix(...bg-elevated 88%...) (nen toi)
 *   - `bg-[var(--nq-warn)]` -> background-color: vang
 * Cung do uu tien (1 class). Trong globals.css, `@tailwind utilities` nam o DAU
 * file con `.nq-surface-tile` nam SAU => shorthand `background` cua
 * `.nq-surface-tile` thang `background-color` cua Tailwind.
 * Neu dung vay: nen bi ghi de thanh toi, chu van la ink toi => CHU VO HINH.
 *
 * Chay: node scripts/check_toned_kpi.mjs
 */

import { mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const requireWeb = createRequire(resolve(ROOT, "apps/web/package.json"));
const { chromium } = requireWeb("playwright-core");

const BASE = "http://localhost:3000";
const API = "http://127.0.0.1:8000";
const OUT = resolve(ROOT, "data/out/contrast-cases");
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 3 });
const page = await ctx.newPage();

await page.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
const d = await page.evaluate(async (api) => {
  const r = await fetch(`${api}/api/v1/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "lan", password: "nhipquan" }),
  });
  return r.json();
}, API);
await page.evaluate((v) => {
  sessionStorage.setItem("nq_token", v.token);
  sessionStorage.setItem("nq_role", v.role);
  sessionStorage.setItem("nq_display_name", v.display_name);
  sessionStorage.setItem("nq_nv_id", v.nv_id);
}, d);

const targets = [
  ["/hom-nay", ".nq-dash-kpi"],
  ["/hom-nay", ".nq-bento-tile"],
  ["/lich-tuan", ".nq-summary-cell"],
  ["/roster", ".nq-summary-cell"],
];

for (const [route, sel] of targets) {
  await page.goto(BASE + route, { waitUntil: "load" });
  await page.waitForTimeout(2500);

  const info = await page.evaluate((s) => {
    const out = [];
    document.querySelectorAll(s).forEach((el, i) => {
      const cs = getComputedStyle(el);
      const inner = el.querySelector(".nq-summary-n, .nq-bento-value, strong, .nq-dash-kpi-value");
      const ics = inner ? getComputedStyle(inner) : null;
      out.push({
        i,
        cls: String(el.className).slice(0, 120),
        tone: el.getAttribute("data-tone") || "-",
        bgColor: cs.backgroundColor,
        bgImage: cs.backgroundImage === "none" ? null : cs.backgroundImage.slice(0, 50),
        bgShorthand: cs.background.slice(0, 70),
        selfColor: cs.color,
        innerText: inner ? (inner.textContent || "").trim().slice(0, 14) : null,
        innerColor: ics ? ics.color : null,
        rect: (() => { const r = el.getBoundingClientRect(); return `${Math.round(r.width)}x${Math.round(r.height)}`; })(),
      });
    });
    return out;
  }, sel);

  console.log(`\n== ${route}  ${sel}  (${info.length} o) ==`);
  for (const o of info) {
    console.log(
      `  [${o.i}] tone=${o.tone} ${o.rect} "${o.innerText}"\n` +
        `      el.color    = ${o.selfColor}\n` +
        `      inner.color = ${o.innerColor}\n` +
        `      bgColor     = ${o.bgColor}\n` +
        `      bgShorthand = ${o.bgShorthand}`,
    );
  }

  // Chup tung o co tone (warn/ok/danger) de do diem anh.
  for (const o of info) {
    if (!/warn|ok|danger/.test(o.cls)) continue;
    const f = resolve(OUT, `${route.replace(/\//g, "_")}_${sel.replace(/[^\w]/g, "")}_${o.i}.png`);
    try {
      await page.locator(sel).nth(o.i).screenshot({ path: f });
      console.log(`      -> ${f}`);
    } catch (e) {
      console.log(`      -> loi chup: ${String(e.message).slice(0, 70)}`);
    }
  }
}

await browser.close();
