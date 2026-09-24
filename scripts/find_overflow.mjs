/**
 * Tìm PHẦN TỬ gây tràn ngang — thay vì chỉ biết "trang tràn N px".
 *
 * `ui-system.spec.ts` báo `tràn ngang 5px` nhưng không nói do cái gì, nên không
 * sửa được. Script này đi từng phần tử, so `right` của nó với bề rộng khung nhìn,
 * rồi in ra phần tử VƯỢT XA NHẤT kèm chuỗi tổ tiên — đủ để biết sửa ở đâu.
 *
 * Chạy: node scripts/find_overflow.mjs --route /quay --width 375
 */

import { resolve } from "node:path";
import { createRequire } from "node:module";

const requireWeb = createRequire(resolve(".", "apps/web/package.json"));
const { chromium } = requireWeb("playwright-core");

const argv = process.argv.slice(2);
const flag = (n, d) => (argv.indexOf(`--${n}`) >= 0 ? argv[argv.indexOf(`--${n}`) + 1] : d);
const BASE = flag("base", "http://localhost:3001");
const API = flag("api", "http://127.0.0.1:8000");
const ROUTE = flag("route", "/quay");
const WIDTH = Number(flag("width", 375));

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: WIDTH, height: 900 } });
const p = await ctx.newPage();

await p.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
const d = await p.evaluate(async (api) => {
  const r = await fetch(`${api}/api/v1/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "lan", password: "nhipquan" }),
  });
  if (!r.ok) throw new Error(`login ${r.status}`);
  return r.json();
}, API);
await p.evaluate((v) => {
  sessionStorage.setItem("nq_token", v.token);
  sessionStorage.setItem("nq_role", v.role);
  sessionStorage.setItem("nq_name", v.display_name);
  sessionStorage.setItem("nq_nv_id", v.nv_id);
}, d);

await p.goto(BASE + ROUTE, { waitUntil: "networkidle" });
await p.waitForTimeout(2500);

const info = await p.evaluate((vw) => {
  const docW = document.documentElement.clientWidth;
  const out = [];
  document.querySelectorAll("*").forEach((el) => {
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden") return;
    const r = el.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) return;
    // Vượt mép phải khung nhìn nhiều hơn 1px (bỏ qua làm tròn sub-pixel).
    const over = r.right - docW;
    if (over > 1) {
      const chain = [];
      let n = el;
      for (let i = 0; i < 3 && n && n !== document.body; i++) {
        chain.push(`${n.tagName.toLowerCase()}${n.className ? "." + String(n.className).split(" ").filter(Boolean).slice(0, 3).join(".") : ""}`);
        n = n.parentElement;
      }
      out.push({
        over: Math.round(over * 10) / 10,
        right: Math.round(r.right),
        w: Math.round(r.width),
        left: Math.round(r.left),
        tag: el.tagName.toLowerCase(),
        cls: String(el.className || "").slice(0, 100),
        text: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 44),
        chain: chain.join(" < "),
      });
    }
  });
  return { docW, scrollW: document.documentElement.scrollWidth, out: out.sort((a, b) => b.over - a.over).slice(0, 14) };
}, WIDTH);

console.log(`\n== ${ROUTE} @${WIDTH}px ==`);
console.log(`  clientWidth=${info.docW}  scrollWidth=${info.scrollW}  tràn=${info.scrollW - info.docW}px`);
console.log(`  phần tử vượt mép phải: ${info.out.length}`);
for (const x of info.out) {
  console.log(
    `\n  +${x.over}px  ${x.tag}.${x.cls}\n` +
      `      right=${x.right} left=${x.left} w=${x.w}  "${x.text}"\n` +
      `      ${x.chain}`,
  );
}
await b.close();
