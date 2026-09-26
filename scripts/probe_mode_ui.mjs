/**
 * Tai hien buoc spec that bai va DOC TRANG THAI THAT cua nut sau khi bam "De xuat".
 *
 * Cau hoi can tra loi: sau khi bam `mode-propose-dem_nhac`, DOM chua gi?
 *   - co `mode-confirm-dem_nhac` khong?
 *   - item dang o lop nao (is-waiting / is-active)?
 *   - `proposal_status` ma UI nhan duoc la gi?
 *
 * Chay: node scripts/probe_mode_ui.mjs
 */

import { resolve } from "node:path";
import { createRequire } from "node:module";

const requireWeb = createRequire(resolve(".", "apps/web/package.json"));
const { chromium } = requireWeb("playwright-core");

const BASE = "http://localhost:3001";
const API = "http://127.0.0.1:8000";
const MODE = "dem_nhac";

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
const p = await ctx.newPage();

// Ghi lai moi phan hoi cua API ve modes de doi chieu voi DOM.
const calls = [];
p.on("response", async (r) => {
  const u = r.url();
  if (!u.includes("/quanverse/")) return;
  let body = null;
  try {
    body = await r.json();
  } catch {
    /* khong phai json */
  }
  const short = u.replace(API, "").replace(BASE, "");
  if (short.includes("/snapshot") && body?.modes) {
    const m = body.modes.find((x) => x.mode === MODE);
    calls.push(`GET snapshot -> ${MODE}: active=${m?.active} proposal_status=${JSON.stringify(m?.proposal_status)}`);
  } else if (short.includes("/modes/")) {
    calls.push(`POST ${short} -> ${r.status()} ${JSON.stringify(body)?.slice(0, 120)}`);
  }
});

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

await p.goto(`${BASE}/quanverse`, { waitUntil: "networkidle" });
await p.waitForTimeout(2000);

const snap = async (label) => {
  const s = await p.evaluate((mode) => {
    const item = document.querySelector(`[data-testid="mode-item-${mode}"]`);
    const q = (t) => !!document.querySelector(`[data-testid="${t}"]`);
    return {
      itemCls: item ? String(item.className) : null,
      stateText: item?.querySelector(".nq-moderail__state")?.textContent?.trim() ?? null,
      propose: q(`mode-propose-${mode}`),
      confirm: q(`mode-confirm-${mode}`),
      deactivate: q(`mode-deactivate-${mode}`),
      drop: q(`mode-drop-${mode}`),
    };
  }, MODE);
  console.log(`\n[${label}]`);
  console.log(`  item class   : ${s.itemCls}`);
  console.log(`  nhan trang thai: ${JSON.stringify(s.stateText)}`);
  console.log(`  nut co mat   : propose=${s.propose} confirm=${s.confirm} deactivate=${s.deactivate} drop=${s.drop}`);
  return s;
};

const before = await snap("TRUOC khi bam");
console.log(`\n  => JSX chon nhanh nao?`);
console.log(`     waitingNow (confirm hien)  = ${before.confirm || before.drop}`);
console.log(`     active     (deactivate hien) = ${before.deactivate}`);

if (before.propose) {
  console.log(`\n-- bam mode-propose-${MODE} --`);
  await p.getByTestId(`mode-propose-${MODE}`).click();
  await p.waitForTimeout(2500);
  await snap("SAU khi bam De xuat");
} else {
  console.log(`\n  KHONG co nut propose => spec bo qua nhanh nay.`);
}

console.log("\n== Cac goi API lien quan ==");
for (const c of calls) console.log("  " + c);

await b.close();
