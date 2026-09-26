/**
 * Tai hien spec "published rule can be revoked" theo TUNG BUOC va in trang thai DOM.
 *
 * Spec that bai o `expect(revoke).toBeVisible()`. Can biet: nut revoke co duoc ve
 * khong, va vi sao. Script in ra tung buoc de thay cho doan.
 *
 * Chay: node scripts/probe_rules_ui.mjs
 */

import { resolve } from "node:path";
import { createRequire } from "node:module";

const requireWeb = createRequire(resolve(".", "apps/web/package.json"));
const { chromium } = requireWeb("playwright-core");

const BASE = "http://localhost:3001";
const API = "http://127.0.0.1:8000";

const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 } });
const p = await ctx.newPage();

p.on("response", async (r) => {
  const u = r.url();
  if (!u.includes("/experience/rules/")) return;
  let body = null;
  try { body = await r.json(); } catch { /* ignore */ }
  const short = u.replace(API, "");
  console.log(`    [API] ${r.request().method()} ${short} -> ${r.status()} ${JSON.stringify(body)?.slice(0, 130)}`);
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

const dump = async (label) => {
  const s = await p.evaluate(() => {
    const items = [...document.querySelectorAll(".nq-rules__item")].map((el) => ({
      sentence: el.querySelector(".nq-rules__sentence")?.textContent?.trim().slice(0, 46),
      meta: el.querySelector(".nq-rules__meta")?.textContent?.trim().slice(0, 60),
      cls: String(el.className).replace("nq-rules__item", "").trim(),
      btn: ["evidence-btn", "shadow-btn", "confirm-btn", "reject-btn", "revoke-btn"]
        .filter((t) => el.querySelector(`[data-testid="${t}"]`))
        .map((t) => {
          const e = el.querySelector(`[data-testid="${t}"]`);
          return `${t}${e.disabled ? "(disabled)" : ""}`;
        }),
    }));
    return {
      count: items.length,
      items,
      notice: document.querySelector(".nq-alert--info")?.textContent?.trim().slice(0, 80) ?? null,
      err: document.querySelector(".nq-alert--err, [data-testid=error]")?.textContent?.trim().slice(0, 80) ?? null,
    };
  });
  console.log(`\n[${label}]  so item=${s.count}`);
  for (const it of s.items) {
    console.log(`  • "${it.sentence}"`);
    console.log(`    meta: ${it.meta}`);
    console.log(`    class: "${it.cls}"   nut: ${it.btn.join(", ") || "(khong co)"}`);
  }
  if (s.notice) console.log(`  notice: ${s.notice}`);
  if (s.err) console.log(`  ERROR : ${s.err}`);
  return s;
};

await p.goto(`${BASE}/quanverse/rules`, { waitUntil: "networkidle" });
await p.waitForTimeout(1200);
await dump("1. vao trang");

console.log("\n-- bam rules-discover --");
await p.getByTestId("rules-discover").click();
await p.waitForTimeout(2000);
let s = await dump("2. sau discover");

const shadow = p.getByTestId("shadow-btn").first();
const shadowEnabled = await shadow.isEnabled().catch(() => false);
console.log(`\n  shadow-btn isEnabled = ${shadowEnabled}`);
if (shadowEnabled) {
  await shadow.click();
  await p.waitForTimeout(2000);
  s = await dump("3. sau shadow test");
}

const confirmBtn = p.getByTestId("confirm-btn").first();
const confirmVisible = await confirmBtn.isVisible().catch(() => false);
const confirmEnabled = await confirmBtn.isEnabled().catch(() => false);
console.log(`\n  confirm-btn isVisible = ${confirmVisible}  isEnabled = ${confirmEnabled}`);
if (confirmVisible) {
  await confirmBtn.click();
  await p.waitForTimeout(2000);
  s = await dump("4. sau confirm");
}

const revoke = p.getByTestId("revoke-btn").first();
const revokeVisible = await revoke.isVisible().catch(() => false);
console.log(`\n  revoke-btn isVisible = ${revokeVisible}`);
if (revokeVisible) {
  await revoke.click();
  await p.waitForTimeout(2000);
  await dump("5. sau revoke");
  const txt = await p.locator(".nq-rules__item").first().textContent();
  console.log(`\n  item text co "Đã thu hồi"? ${(txt || "").includes("Đã thu hồi")}`);
  console.log(`  trich: ${JSON.stringify((txt || "").slice(0, 120))}`);
}

await b.close();
