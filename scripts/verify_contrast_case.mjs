/**
 * Kiem chung mot phat hien tuong phan: chu co THUC SU doc duoc khong?
 *
 * Vi sao can: bo quet tuong phan co the bao dong gia khi nen cua the duoc ve bang
 * `background-image` (gradient) chu khong phai `background-color` — luc do phep
 * di nguoc cay se roi xuong nen trang va bao "chu den tren nen den" trong khi mat
 * nguoi van thay chu ro. Truoc khi sua, phai phan biet that/gia.
 *
 * Cach lam: chup RIENG tung phan tu nghi van roi do do lech mau giua "mau chu
 * tinh toan" va "mau diem anh thuc te trong vung chu". Neu anh thuc te co nhieu
 * diem sang gan mau chu thi ket luan tuong phan truoc do la GIA.
 *
 * Chay: node scripts/verify_contrast_case.mjs --route /hom-nay --sel ".nq-bento-value"
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
const ROUTE = flag("route", "/hom-nay");
const SEL = flag("sel", ".nq-bento-value");
const OUTDIR = resolve(ROOT, "data/out/contrast-cases");
mkdirSync(OUTDIR, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
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

await page.goto(BASE + ROUTE, { waitUntil: "load" });
await page.waitForTimeout(2500);

const info = await page.evaluate((sel) => {
  const els = [...document.querySelectorAll(sel)];
  return els.slice(0, 4).map((el) => {
    const cs = getComputedStyle(el);
    // Di nguoc cay, ghi lai MOI lop nen gap duoc (ke ca background-image).
    const chain = [];
    let n = el;
    while (n && n !== document.documentElement.parentElement) {
      const c = getComputedStyle(n);
      chain.push({
        tag: n.tagName.toLowerCase(),
        cls: String(n.className || "").slice(0, 60),
        bgColor: c.backgroundColor,
        bgImage: c.backgroundImage === "none" ? null : c.backgroundImage.slice(0, 60),
        boxShadow: c.boxShadow === "none" ? null : c.boxShadow.slice(0, 50),
      });
      n = n.parentElement;
    }
    const r = el.getBoundingClientRect();
    return {
      text: (el.textContent || "").trim().slice(0, 40),
      color: cs.color,
      fontSize: cs.fontSize,
      fontWeight: cs.fontWeight,
      rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) },
      chain: chain.slice(0, 6),
    };
  });
}, SEL);

console.log(`== Kiem chung ${SEL} tren ${ROUTE} ==`);
for (let i = 0; i < info.length; i++) {
  const el = info[i];
  console.log(`\n[${i}] "${el.text}"  color=${el.color}  ${el.fontSize}/${el.fontWeight}  ${el.rect.w}x${el.rect.h}`);
  el.chain.forEach((c, j) => {
    console.log(
      `    ${" ".repeat(j)}${c.tag}.${c.cls}\n` +
        `    ${" ".repeat(j)}   bg=${c.bgColor}${c.bgImage ? `  IMAGE=${c.bgImage}` : ""}${c.boxShadow ? `  shadow=${c.boxShadow}` : ""}`,
    );
  });

  const handle = page.locator(SEL).nth(i);
  const f = resolve(OUTDIR, `${ROUTE.replace(/\//g, "_")}_${i}.png`);
  try {
    await handle.screenshot({ path: f });
    console.log(`    -> anh: ${f}`);
  } catch (e) {
    console.log(`    -> khong chup duoc: ${String(e.message).slice(0, 80)}`);
  }
}

await browser.close();
