/**
 * In hop mo hinh (box model) cua chuoi to tien quanh mot phan tu — de tim NGUYEN NHAN
 * tran ngang thay vi doan.
 *
 * Chay: node scripts/box_model.mjs --route /quay --width 375
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
const SEL = flag("sel", ".nq-pos-menu");

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: WIDTH, height: 900 } });
const p = await ctx.newPage();
await p.goto(`${BASE}/login`, { waitUntil: "domcontentloaded" });
const d = await p.evaluate(async (api) => {
  const r = await fetch(`${api}/api/v1/auth/login`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "lan", password: "nhipquan" }),
  });
  return r.json();
}, API);
await p.evaluate((v) => {
  sessionStorage.setItem("nq_token", v.token);
  sessionStorage.setItem("nq_role", v.role);
  sessionStorage.setItem("nq_name", v.display_name);
  sessionStorage.setItem("nq_nv_id", v.nv_id);
}, d);
await p.goto(BASE + ROUTE, { waitUntil: "networkidle" });
await p.waitForTimeout(2200);

const rows = await p.evaluate((sel) => {
  const el = document.querySelector(sel);
  const out = [];
  let n = el;
  while (n && n !== document.documentElement) {
    const cs = getComputedStyle(n);
    const r = n.getBoundingClientRect();
    out.push({
      tag: n.tagName.toLowerCase(),
      cls: String(n.className || "").slice(0, 62),
      left: Math.round(r.left * 10) / 10,
      right: Math.round(r.right * 10) / 10,
      w: Math.round(r.width * 10) / 10,
      box: cs.boxSizing,
      display: cs.display,
      padX: `${cs.paddingLeft} / ${cs.paddingRight}`,
      marX: `${cs.marginLeft} / ${cs.marginRight}`,
      width: cs.width,
      maxW: cs.maxWidth,
      minW: cs.minWidth,
      gridCols: cs.gridTemplateColumns,
      overflowX: cs.overflowX,
      cols: cs.columnCount,
    });
    n = n.parentElement;
  }
  return { vw: document.documentElement.clientWidth, sw: document.documentElement.scrollWidth, out };
}, SEL);

console.log(`\n== Hop mo hinh tu ${SEL} len goc — ${ROUTE} @${WIDTH}px ==`);
console.log(`  clientWidth=${rows.vw}  scrollWidth=${rows.sw}  TRAN=${rows.sw - rows.vw}px\n`);
for (const r of rows.out) {
  console.log(
    `${r.tag}.${r.cls}\n` +
      `   left=${r.left} right=${r.right} w=${r.w}  widget=${r.width} max=${r.maxW} min=${r.minW} box=${r.box}\n` +
      `   pad=${r.padX}  mar=${r.marX}  display=${r.display}  overflowX=${r.overflowX}` +
      (r.gridCols !== "none" ? `\n   grid-cols=${r.gridCols}` : ""),
  );
}
await b.close();
