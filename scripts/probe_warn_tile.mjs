/**
 * Kiem chung MOT gia thuyet: o KPI tone warn co that su "chu vo hinh" khong,
 * hay anh chup bi chup giua luc hieu ung fade-in chua chay xong?
 *
 * Cach phan biet: cho MOI animation dung han (document.getAnimations() rong,
 * cong them delay), roi moi do. Neu luc do chu van khong doc duoc => loi that.
 * Dong thoi in chuoi opacity cua to tien de xem co lop nao lam mo ca o khong.
 *
 * Chay: node scripts/probe_warn_tile.mjs
 */

import { mkdirSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..");
const requireWeb = createRequire(resolve(ROOT, "apps/web/package.json"));
const { chromium } = requireWeb("playwright-core");

const OUT = resolve(ROOT, "data/out/contrast-cases");
mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
const ctx = await browser.newContext({
  viewport: { width: 1440, height: 900 },
  deviceScaleFactor: 3,
  reducedMotion: "reduce", // tat hieu ung de loai bien so animation
});
const page = await ctx.newPage();

await page.goto("http://localhost:3000/login", { waitUntil: "domcontentloaded" });
const d = await page.evaluate(async () => {
  const r = await fetch("http://127.0.0.1:8000/api/v1/auth/login", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: "lan", password: "nhipquan" }),
  });
  return r.json();
});
await page.evaluate((v) => {
  sessionStorage.setItem("nq_token", v.token);
  sessionStorage.setItem("nq_role", v.role);
  sessionStorage.setItem("nq_display_name", v.display_name);
  sessionStorage.setItem("nq_nv_id", v.nv_id);
}, d);

for (const route of ["/lich-tuan", "/roster"]) {
  await page.goto("http://localhost:3000" + route, { waitUntil: "load" });
  await page.waitForTimeout(3000);

  // Cho animation dung han (bien so dung de loai bo gia thuyet "chup giua hieu ung").
  const anim = await page.evaluate(async () => {
    for (let i = 0; i < 40; i++) {
      const a = document.getAnimations().filter((x) => x.playState === "running");
      if (!a.length) return { running: 0, waited: i * 100 };
      await new Promise((r) => setTimeout(r, 100));
    }
    return { running: document.getAnimations().filter((x) => x.playState === "running").length, waited: 4000 };
  });
  console.log(`\n########## ${route}  (animation dang chay: ${anim.running} sau ${anim.waited}ms)`);

  const rows = await page.evaluate(() => {
    const out = [];
    document.querySelectorAll(".nq-summary-cell").forEach((el, i) => {
      const tone = el.getAttribute("data-tone") || "-";
      if (tone === "default") return;
      const cs = getComputedStyle(el);
      // Chuoi opacity tu o len goc.
      const chain = [];
      let n = el;
      while (n && n !== document.body) {
        const o = getComputedStyle(n).opacity;
        if (o !== "1") chain.push(`${n.tagName.toLowerCase()}.${String(n.className).slice(0, 40)}=${o}`);
        n = n.parentElement;
      }
      const bgLayer = getComputedStyle(el);
      out.push({
        i, tone,
        opacitySelf: cs.opacity,
        opacityChain: chain,
        bgColor: cs.backgroundColor,
        bgImage: bgLayer.backgroundImage === "none" ? null : bgLayer.backgroundImage.slice(0, 45),
        filter: cs.filter,
        mixBlend: cs.mixBlendMode,
        textColor: cs.color,
        nestedColor: (() => {
          const s = el.querySelector(".nq-summary-n");
          return s ? getComputedStyle(s).color : null;
        })(),
        animName: cs.animationName,
        text: (el.textContent || "").trim().replace(/\s+/g, " ").slice(0, 24),
      });
    });
    return out;
  });

  for (const r of rows) {
    console.log(
      `  [${r.i}] tone=${r.tone} "${r.text}"\n` +
        `       text=${r.textColor}  nested=${r.nestedColor}\n` +
        `       bgColor=${r.bgColor}\n` +
        `       bgImage=${r.bgImage}\n` +
        `       opacitySelf=${r.opacitySelf}  chain=${r.opacityChain.length ? r.opacityChain.join(" | ") : "(khong co)"}\n` +
        `       filter=${r.filter}  blend=${r.mixBlend}  anim=${r.animName}`,
    );
    const f = resolve(OUT, `probe_${route.replace(/\//g, "_")}_${r.tone}_settled.png`);
    await page.locator(".nq-summary-cell").nth(r.i).screenshot({ path: f });
    console.log(`       -> ${f}`);
  }
}

await browser.close();
