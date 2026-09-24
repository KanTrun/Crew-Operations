/**
 * Kiem chung: bam anchor "Kho" co THAT SU chon stockroom va goi voice/turn voi
 * anchor_id=stockroom khong? Spec khang dinh 0 citation nhung nhan duoc 1.
 *
 * Chay: node scripts/probe_voicedock.mjs
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

const voiceCalls = [];
p.on("request", (r) => {
  if (r.url().includes("/voice/turn")) {
    voiceCalls.push(`REQ voice/turn body=${JSON.stringify(r.postData()?.slice(0, 200))}`);
  }
});
p.on("response", async (r) => {
  if (r.url().includes("/voice/turn")) {
    let body = null;
    try { body = await r.json(); } catch { /* ignore */ }
    voiceCalls.push(`RES voice/turn citations=${JSON.stringify(body?.citations)} grounded=${body?.grounded}`);
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

await p.goto(`${BASE}/quanverse/spatial-memory`, { waitUntil: "networkidle" });
await p.waitForTimeout(1500);

const probe = async (label) => {
  const s = await p.evaluate(() => {
    const anchors = [...document.querySelectorAll(".nq-map2d__anchor")].map((a) => ({
      label: a.getAttribute("aria-label"),
      pressed: a.getAttribute("aria-pressed"),
      cls: String(a.getAttribute("class") || "").slice(0, 60),
    }));
    const head = document.querySelector(".nq-voicedock__anchor, .nq-voicedock__head, .nq-exp-header");
    return { anchors, heading: head?.textContent?.trim().slice(0, 90) ?? null };
  });
  console.log(`\n[${label}]`);
  console.log(`  heading: ${JSON.stringify(s.heading)}`);
  for (const a of s.anchors) {
    console.log(`  anchor aria-label=${JSON.stringify(a.label)} pressed=${a.pressed}`);
  }
  return s;
};

await probe("sau khi vao trang");

// Dung DUNG cach spec lam.
const kho = p.locator('.nq-map2d__anchor[aria-label="Kho"]');
console.log(`\n  so anchor khop [aria-label="Kho"]: ${await kho.count()}`);
await kho.scrollIntoViewIfNeeded().catch(() => undefined);
await p.mouse.move(500, 400);
await kho.dispatchEvent("click");
await p.waitForTimeout(800);
await probe("sau khi bam Kho");

await p.getByTestId("voice-input").fill("chuyện gì đã xảy ra ở đây?");
await p.getByTestId("voice-ask").click();
await p.waitForTimeout(2500);

const out = await p.evaluate(() => {
  const resp = document.querySelector('[data-testid="voice-response"]');
  const cites = resp?.querySelectorAll(".nq-voicedock__citations");
  return {
    hasResp: !!resp,
    text: resp?.textContent?.trim().slice(0, 130) ?? null,
    nCitationNodes: cites ? cites.length : 0,
    citationText: cites ? [...cites].map((c) => c.textContent.trim()).join(" | ") : null,
  };
});
console.log("\n== Ket qua tra loi ==");
console.log(`  co voice-response: ${out.hasResp}`);
console.log(`  so node .nq-voicedock__citations: ${out.nCitationNodes}`);
console.log(`  noi dung citation: ${JSON.stringify(out.citationText)}`);
console.log(`  text: ${JSON.stringify(out.text)}`);

console.log("\n== Goi API voice/turn ==");
for (const c of voiceCalls) console.log("  " + c);

await b.close();
