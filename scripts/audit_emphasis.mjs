/**
 * Kiểm kê "một giọng nhấn" (one voice of emphasis) trên cả 44 route.
 *
 * Vì sao đo cái này: `design-taste.md` định nghĩa thiết kế tốt là "một giọng nhấn —
 * DUY NHẤT một accent làm hết việc 'nhìn đây', màu trung tính làm phần còn lại.
 * Nhấn ở mọi chỗ là nhấn ở không đâu." Kèm theo: "#1 element thắng phép thử nheo
 * mắt", và mục Evaluate ghi rõ bằng chứng phải là RENDERED INSPECTION, không phải
 * đọc mã nguồn.
 *
 * Nên ở đây không grep class. Đo trên bản render thật:
 *
 *  1. Phần tử nào ĐANG chiếm sự chú ý nhất? Xếp hạng theo "trọng số thị giác" tính
 *     từ hình học thật + độ tương phản thật + kích thước chữ thật:
 *       điểm = (độ tương phản với nền) × (diện tích) × (hệ số theo bậc chữ)
 *     Đây là cách lượng hoá phép "nheo mắt": nheo mắt thì mất chi tiết, chỉ còn
 *     mảng màu lớn và tương phản mạnh.
 *
 *  2. Accent đang bị TIÊU ở mấy chỗ? Đếm phần tử có màu accent làm nền HOẶC chữ
 *     với diện tích đủ lớn để mắt bắt được. Nhiều chỗ cùng lúc = nhấn rải rác.
 *
 *  3. Có bao nhiêu phần tử đang tranh nhau ở hạng cao? Nếu #1 và #2 sát điểm nhau
 *     thì phép thử nheo mắt KHÔNG có người thắng rõ ràng — đó là lỗi thật.
 *
 * Chạy: node scripts/audit_emphasis.mjs [--base URL] [--out FILE]
 */

import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";

const require = createRequire(import.meta.url);
const { chromium } = require("./../apps/web/node_modules/playwright");

const args = process.argv.slice(2);
const getArg = (name, dflt) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : dflt;
};
const BASE = getArg("--base", "http://localhost:3001");
const OUT = getArg("--out", "data/out/emphasis-audit.json");
const USER = process.env.NQ_USER || "lan";
const PASS = process.env.NQ_PASS || "nhipquan";

/** Trang không cần đăng nhập; còn lại đăng nhập trước. */
const PUBLIC_ROUTES = new Set(["/login", "/dang-ky", "/"]);

const ROUTES = [
  "/", "/ai-learning", "/cam-nang", "/chat", "/cong-bang", "/contracts", "/copilot",
  "/cuoc-hop", "/dang-ky", "/de-xuat-thong-minh", "/doi-ca", "/giai-thich", "/handover",
  "/hao-phi", "/hom-nay", "/huong-dan", "/inbox", "/khao-sat-gia", "/lich-tuan", "/login",
  "/menu", "/nguoi", "/page-quan", "/page-quan/dat-ban", "/page-quan/fb-inbox", "/pha",
  "/phieu", "/qr", "/quanverse", "/quanverse/rules", "/quanverse/shift-rescue",
  "/quanverse/spatial-memory", "/quanverse/war-room", "/quay", "/roster", "/skills",
  "/sop", "/them", "/thu-nghiem-an-toan", "/tieu-thu", "/tkb", "/toi", "/treo", "/vet",
];

/**
 * Chạy TRONG trang. Trả về bảng xếp hạng trọng số thị giác + chỗ tiêu accent.
 *
 * Cố ý bỏ qua phần tử không nhìn thấy, phần tử chỉ là lớp bọc trong suốt, và chữ
 * trang trí (`aria-hidden`). Giữ lại cả phần tử SVG vì biểu đồ cũng là "nội dung
 * thị giác chính" theo tiêu chí 3.
 */
const ANALYZE = () => {
  /**
   * Phát hiện trang LỖI của Next.js.
   *
   * Vì sao bắt buộc: nếu server chết giữa lúc chạy, trình duyệt hiện error boundary
   * và trang chỉ còn một `h2` "Application error: a client-side exception...".
   * Bản đo đầu tiên của tôi tính luôn trang lỗi đó là một phép đo HỢP LỆ — `/toi`
   * và `/vet` được ghi "đo được" với 1 phần tử xếp hạng và margin 1.00, trông như
   * hai trang rất rõ ràng. Kết luận "44/44 route đo được" khi đó là SAI: hai route
   * chưa hề được đo.
   *
   * Đây là dạng lỗi nguy hiểm nhất của công cụ đo: báo "đủ" trong khi thực ra
   * thiếu. Thà báo lỗi rõ ràng còn hơn.
   */
  const bodyText = document.body ? document.body.innerText || "" : "";
  if (/Application error|client-side exception|Internal Server Error/i.test(bodyText)) {
    return { error: "trang loi (error boundary) — khong do duoc" };
  }
  const parseColor = (s) => {
    if (!s) return null;
    let m = /^rgba?\(([^)]+)\)$/.exec(s);
    if (m) {
      const p = m[1].split(/[\s,/]+/).filter(Boolean).map(Number);
      if (p.length >= 3) return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
      return null;
    }
    // Chromium trả `color(srgb r g b)` cho màu sinh từ color-mix()/oklab.
    m = /^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+))?\)$/.exec(s);
    if (m) {
      return {
        r: Number(m[1]) * 255,
        g: Number(m[2]) * 255,
        b: Number(m[3]) * 255,
        a: m[4] === undefined ? 1 : Number(m[4]),
      };
    }
    return null;
  };

  const lum = ({ r, g, b }) => {
    const f = (v) => {
      const x = v / 255;
      return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };

  const ratio = (fg, bg) => {
    if (!fg || !bg) return 1;
    const a = lum(fg);
    const b = lum(bg);
    const [hi, lo] = a > b ? [a, b] : [b, a];
    return (hi + 0.05) / (lo + 0.05);
  };

  /**
   * Nền của TRANG nằm dưới phần tử — bắt đầu từ cha, KHÔNG phải từ chính nó.
   *
   * Bắt đầu từ `el` là lỗi tôi đã mắc: hàm trả về nền của chính phần tử, nên phép
   * so `ratio(bg, pageBack)` thành `ratio(bg, bg)` = 1.0, và mọi phần tử có nền
   * đục đều bị luật "khối bao vô hình" loại oan. Hệ quả: `/toi` chỉ còn 1 phần tử
   * xếp hạng và `margin` báo 1.00 — trông như trang rất rõ ràng, thực ra là công cụ
   * đã xoá gần hết dữ liệu.
   *
   * Tên gọi phải nói đúng việc: đây là nền NẰM DƯỚI, không phải "nền hiệu dụng
   * của phần tử".
   */
  const pageUnder = (el) => {
    let cur = el.parentElement;
    while (cur) {
      const c = parseColor(getComputedStyle(cur).backgroundColor);
      if (c && c.a >= 0.999) return c;
      cur = cur.parentElement;
    }
    const body = parseColor(getComputedStyle(document.body).backgroundColor);
    return body && body.a >= 0.999 ? body : { r: 255, g: 255, b: 255, a: 1 };
  };

  const accent = parseColor(
    getComputedStyle(document.documentElement).getPropertyValue("--nq-copper").trim()
  ) || { r: 196, g: 165, b: 116, a: 1 };

  /**
   * Trộn alpha của `fg` lên `bg` để ra màu thật mắt nhìn thấy.
   *
   * BẮT BUỘC phải trộn, không được so RGB trần: `--nq-accent-soft` là
   * `rgba(196,165,116,0.18)` — CÙNG RGB với accent nhưng chỉ 18% đục. So RGB trần
   * thì mọi chip nền nhạt đều bị tính là "accent đang được tiêu", và bản đo đầu
   * tiên báo 28/44 route "nhiều chỗ nhấn" — đó là báo động giả do chính công cụ.
   * Nền nhạt 18% KHÔNG phải nhấn; nó là bề mặt.
   */
  const composite = (fg, bg) => {
    if (!fg) return bg;
    const a = fg.a === undefined ? 1 : fg.a;
    return {
      r: fg.r * a + bg.r * (1 - a),
      g: fg.g * a + bg.g * (1 - a),
      b: fg.b * a + bg.b * (1 - a),
      a: 1,
    };
  };

  const nearAccent = (c, tol = 46) => {
    if (!c) return false;
    const d = Math.abs(c.r - accent.r) + Math.abs(c.g - accent.g) + Math.abs(c.b - accent.b);
    return d <= tol;
  };

  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const rows = [];
  const accentSpent = [];

  const all = document.querySelectorAll("body *");
  for (const el of all) {
    if (el.closest("[aria-hidden='true']")) continue;
    const cs = getComputedStyle(el);
    if (cs.display === "none" || cs.visibility === "hidden" || Number(cs.opacity) < 0.08) continue;
    // Bỏ phần tử chỉ là lớp bọc: không chữ của chính nó, không nền, không viền.
    const text = (el.textContent || "").trim();
    const hasOwnText = [...el.childNodes].some(
      (n) => n.nodeType === 3 && n.textContent.trim().length > 0
    );
    const bg = parseColor(cs.backgroundColor);
    const bgA = bg ? bg.a : 0;
    const hasBg = bgA > 0.06;
    const hasBorder =
      cs.borderTopWidth !== "0px" || cs.borderLeftWidth !== "0px" || cs.borderBottomWidth !== "0px";

    const r = el.getBoundingClientRect();
    if (r.width < 8 || r.height < 8) continue;
    // Bỏ phần tử gần như nằm ngoài khung (băng chuyền, menu đóng).
    const visW = Math.max(0, Math.min(r.right, vw) - Math.max(r.left, 0));
    const visH = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0));
    const visArea = visW * visH;
    if (visArea < 400) continue;

    if (!hasOwnText && !hasBg && !hasBorder) continue;

    const pageBack = pageUnder(el);
    // Bỏ khối BAO ngoài: không có chữ của chính nó, và nền KHÔNG khác nền trang.
    // Mắt không hề thấy nó — nó chỉ là thẻ gói bố cục.
    //
    // Điều kiện đúng là "vô hình", KHÔNG phải "to". Bản trước tôi chặn theo ngưỡng
    // diện tích >= 50% khung, nên `/chat` lọt lưới với `div.nq-chat-stream` ở 47.9%
    // — một khung cuộn rỗng, tương phản 1.0, vẫn đứng #1. Ngưỡng theo kích thước
    // luôn có khe hở; điều kiện theo "có nhìn thấy hay không" thì không.
    if (!hasOwnText && !hasBorder) {
      const shownBg = composite(bg, pageBack);
      if (bgA < 0.06 || ratio(shownBg, pageBack) < 1.15) continue;
    }

    const fg = parseColor(cs.color);
    // Chữ đọc trên nền của chính nó nếu nó có nền đặc, không thì đọc trên nền trang.
    const back = bgA >= 0.999 ? bg : composite(bg, pageBack);
    const cr = hasOwnText ? ratio(fg, back) : 1;
    const fs = parseFloat(cs.fontSize) || 14;
    const weight = Number(cs.fontWeight) || 400;

    // Hệ số theo bậc chữ: chữ lớn ăn nhiều chú ý hơn ở cùng diện tích.
    const fsK = fs >= 40 ? 3.0 : fs >= 28 ? 2.2 : fs >= 20 ? 1.6 : fs >= 16 ? 1.2 : 1.0;
    // Chữ đậm ăn hơn chữ thường.
    const wK = weight >= 800 ? 1.35 : weight >= 700 ? 1.2 : weight >= 600 ? 1.08 : 1.0;
    // Tương phản là "độ sáng" của mảng — chuẩn hoá quanh 4.5.
    const cK = hasOwnText ? Math.min(cr, 21) / 4.5 : 1;
    // Diện tích tương đối, bù căn bậc hai để một khối lớn không át hết.
    const aK = Math.sqrt(visArea) / Math.sqrt(vw * vh) * 6;

    const score = cK * fsK * wK * (0.55 + aK);

    // Accent bị "tiêu" (nhấn) chỉ khi khối đó NỔI HẲN khỏi nền trang.
    //
    // Ba điều kiện, và phải đủ cả ba:
    //   - màu đã trộn alpha nằm trong khoảng accent (không phải bề mặt nhạt);
    //   - khối đủ lớn để mắt bắt được;
    //   - khối ĐỦ KHÁC nền trang để đọc ra là "nhìn đây" — đây là điều kiện thật
    //     sự tách "nhấn" khỏi "bề mặt". Một dải màu nhạt cùng họ accent vẫn là
    //     bề mặt; chỉ khi nó tương phản với nền trang thì mới là nhấn.
    let spent = null;
    if (hasBg) {
      const shown = composite(bg, pageBack);
      const vsPage = ratio(shown, pageBack);
      if (nearAccent(shown) && visArea > 2600 && vsPage >= 1.5) spent = "nen";
    }
    if (!spent && hasOwnText && nearAccent(fg) && fs >= 18 && text.length > 1) spent = "chu";

    const rec = {
      tag: el.tagName.toLowerCase(),
      cls: (el.className && typeof el.className === "string" ? el.className : "")
        .split(/\s+/).filter(Boolean).slice(0, 3).join("."),
      text: text.slice(0, 70),
      score: Number(score.toFixed(2)),
      area: Math.round(visArea),
      fontSize: fs,
      contrast: Number(cr.toFixed(2)),
      spent,
    };
    rows.push(rec);
    if (spent) accentSpent.push(rec);
  }

  rows.sort((a, b) => b.score - a.score);

  // Gộp phần tử lồng nhau: cha và con cùng mô tả một khối thì chỉ giữ cái điểm cao.
  const distinct = [];
  for (const r of rows) {
    const dup = distinct.find(
      (d) => d.text && r.text && (d.text.startsWith(r.text) || r.text.startsWith(d.text))
    );
    if (dup) continue;
    distinct.push(r);
    if (distinct.length >= 8) break;
  }

  const top = distinct[0] || null;
  const second = distinct[1] || null;

  /**
   * Nhóm "ngang hàng": các phần tử ở hạng đầu CHIA SẺ một lớp chung.
   *
   * Vì sao cần tách khỏi "khoảng cách #1-#2": `design-taste.md` yêu cầu
   * "các phần tử NGANG HÀNG thì trông phải ngang nhau". Bốn thẻ KPI cùng cỡ chữ
   * 43.2px trên `/hom-nay` là bốn số liệu cùng cấp — chúng PHẢI hoà nhau, và hoà
   * nhau là ĐÚNG. Bản đo đầu tiên gắn cờ "không có người thắng" cho trường hợp
   * đó, tức là đã lấy tiêu chuẩn sai: thiết kế đúng mà công cụ báo lỗi.
   *
   * Ngược lại, hai phần tử KHÁC LOẠI mà sát điểm nhau mới là tranh chấp thật —
   * mắt không biết nhìn cái nào trước.
   */
  const classSet = (el) => new Set((el.cls || "").split(".").filter(Boolean));
  const sharedClass = (a, b) => {
    if (!a || !b) return false;
    const A = classSet(a);
    for (const c of classSet(b)) if (A.has(c)) return true;
    return false;
  };

  /**
   * Phần tử CHROME (thanh điều hướng, thương hiệu, khung ứng dụng) khác công việc
   * với phần tử NỘI DUNG của trang, nên không "tranh chấp" với nhau.
   *
   * Vì sao cần tách: `/chat` bị gắn cờ tranh chấp vì #1 là `span` 19.1px in đậm
   * "NHỊP QUÁN" — dòng thương hiệu trên thanh trên — và #2 là một bong bóng tin
   * nhắn 13.5px. Hai thứ làm hai việc khác hẳn. `design-taste.md` chỉ đòi "các
   * phần tử NGANG HÀNG thì trông phải ngang nhau"; nó không đòi dòng thương hiệu
   * phải nổi hơn bong bóng tin nhắn. Gắn cờ ở đây là lấy tiêu chuẩn sai.
   *
   * Nhận diện theo chữ ký thật đo được: thanh trên dùng `font-black uppercase`,
   * và tin nhắn nằm trong vùng cuộn của khung chat.
   */
  const isChrome = (el) => {
    const c = el.cls || "";
    if (/font-black/.test(c) && /uppercase/.test(c) && el.fontSize < 24) return true;
    if (/^(h1|h2)$/i.test(el.tag) && el.fontSize < 17) return true;
    return false;
  };

  const peers = [];
  if (top) {
    peers.push(top);
    for (let i = 1; i < distinct.length; i += 1) {
      const e = distinct[i];
      if (e.score >= top.score * 0.85 && sharedClass(top, e)) peers.push(e);
      else break;
    }
  }
  // Chỉ tính là "ngang hàng" khi có từ 2 phần tử trở lên VÀ chúng cùng cỡ chữ —
  // cùng lớp nhưng khác cỡ thì vẫn là một thứ lớn hơn một thứ nhỏ.
  const peerGroup =
    peers.length >= 2 && peers.every((p) => Math.abs(p.fontSize - peers[0].fontSize) < 0.5)
      ? peers
      : [];

  // Tranh chấp thật: #1 và #2 sát điểm, KHÁC loại, và CÙNG CẤP (không phải chrome
  // đứng cạnh nội dung — hai thứ đó không tranh nhau vì làm hai việc khác nhau).
  const competitor =
    second && !sharedClass(top, second) && !isChrome(top) && !isChrome(second) ? second : null;
  const margin = top && second ? (top.score - second.score) / top.score : 1;
  const contention = competitor && margin < 0.15 ? Number(margin.toFixed(3)) : null;
  // Ghi lại cả trường hợp bị bỏ qua vì chrome, để không âm thầm giấu dữ liệu.
  const chromePair =
    second && !sharedClass(top, second) && margin < 0.15 && (isChrome(top) || isChrome(second))
      ? { top: `${top.tag}.${top.cls}`, second: `${second.tag}.${second.cls}` }
      : null;

  return {
    accent,
    top,
    second,
    margin: Number(margin.toFixed(3)),
    contention,
    chromePair,
    peerGroup: peerGroup.map((p) => `${p.tag}.${p.cls}`),
    ranking: distinct,
    accentSpent,
    // Đếm chỗ accent làm NỀN đặc — đây mới là "nhấn", chữ accent là ngữ nghĩa thương hiệu.
    accentBackgrounds: accentSpent.filter((x) => x.spent === "nen").length,
    accentTexts: accentSpent.filter((x) => x.spent === "chu").length,
  };
};

async function login(page) {
  await page.goto(`${BASE}/login`, { waitUntil: "networkidle" });
  await page.getByLabel("Tài khoản").fill(USER);
  await page.getByLabel("Mật khẩu").fill(PASS);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 20000 });
}

/** Tắt lớp phủ (tour/modal) — nếu không, phép đo đọc phải lớp phủ chứ không phải trang. */
async function dismissOverlays(page) {
  return page.evaluate(() => {
    let killed = 0;
    for (const el of document.querySelectorAll("body *")) {
      const cs = getComputedStyle(el);
      if (cs.position !== "fixed" && cs.position !== "absolute") continue;
      const z = Number(cs.zIndex) || 0;
      if (z < 100) continue;
      const r = el.getBoundingClientRect();
      const covers = (r.width * r.height) / (window.innerWidth * window.innerHeight);
      if (covers >= 0.9) {
        el.style.display = "none";
        killed += 1;
      }
    }
    return killed;
  });
}

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const results = [];
  let failures = 0;

  try {
    await login(page);

    for (const route of ROUTES) {
      if (PUBLIC_ROUTES.has(route)) {
        // vẫn dùng phiên đã đăng nhập; chỉ khác là không cần điều hướng đặc biệt
      }
      // Kiểm server còn sống TRƯỚC mỗi route. Lần chạy trước, web server chết giữa
      // chừng và các route sau đó trả về trang lỗi — nếu không kiểm, ta đo nhầm
      // trang lỗi và vẫn tưởng là đo được trang thật.
      const alive = await fetch(`${BASE}/login`, { method: "HEAD" })
        .then((r) => r.ok)
        .catch(() => false);
      if (!alive) {
        console.error(`\n[!] server :3001 khong phan hoi tai ${route} — dung do, khong ket luan.`);
        break;
      }
      try {
        await page.goto(`${BASE}${route}`, { waitUntil: "networkidle", timeout: 30000 });
      } catch {
        results.push({ route, error: "goto failed" });
        failures += 1;
        continue;
      }
      await page.waitForTimeout(700);
      const overlays = await dismissOverlays(page);
      if (overlays) await page.waitForTimeout(250);

      const r = await page.evaluate(ANALYZE).catch((e) => ({ error: String(e).slice(0, 120) }));
      if (r.error) {
        results.push({ route, error: r.error });
        failures += 1;
        continue;
      }
      results.push({ route, overlays, ...r });
    }
  } finally {
    await browser.close();
  }

  mkdirSync(dirname(OUT), { recursive: true });
  writeFileSync(OUT, JSON.stringify({ base: BASE, viewport: "1440x900", results }, null, 2), "utf8");

  console.log(`=== KIEM KE MOT GIONG NHAN — ${results.length} route @1440x900 ===`);
  console.log("");
  console.log(
    "route".padEnd(30) + "top1".padEnd(34) + "diem".padStart(7) + "  lech  " + "nhom  accent"
  );
  console.log("-".repeat(96));
  for (const r of results) {
    if (r.error) {
      console.log(`${r.route.padEnd(30)}[LOI] ${r.error}`);
      continue;
    }
    const t = r.top ? `${r.top.tag}.${r.top.cls}`.slice(0, 32) : "(khong co)";
    const mark = r.contention !== null ? " TRANH" : "";
    const peer = r.peerGroup.length >= 2 ? ` ${r.peerGroup.length}` : " -";
    console.log(
      `${r.route.padEnd(30)}${t.padEnd(34)}${String(r.top ? r.top.score : 0).padStart(7)}` +
        `  ${r.margin.toFixed(2)}${mark.padEnd(6)}${peer.padStart(4)}` +
        `  nen=${r.accentBackgrounds} chu=${r.accentTexts}`
    );
  }

  const ok = results.filter((r) => !r.error);
  const erred = results.filter((r) => r.error);
  const competent = ok.filter((r) => r.contention !== null);
  const peerG = ok.filter((r) => r.peerGroup.length >= 2);
  const chromeG = ok.filter((r) => r.chromePair);
  console.log("");
  console.log(
    `route do duoc                         : ${ok.length}/${ROUTES.length}` +
      (ok.length < ROUTES.length ? "  <-- CHUA DO HET, dung ket luan" : "")
  );
  if (erred.length) {
    console.log(`route KHONG do duoc                   : ${erred.length}`);
    for (const r of erred) console.log(`    ${r.route} — ${r.error}`);
  }
  console.log(
    `TRANH CHAP that (#1,#2 khac loai, sat) : ${competent.length}  ${competent.map((r) => r.route).join(" ")}`
  );
  console.log(
    `nhom ngang hang (#1 hoa nhau, dung)    : ${peerG.length}  ${peerG.map((r) => r.route).join(" ")}`
  );
  console.log(
    `bo qua vi chrome<->noi dung            : ${chromeG.length}  ${chromeG.map((r) => r.route).join(" ")}`
  );
  console.log(`accent lam nen > 1 cho               : ${ok.filter((r) => r.accentBackgrounds > 1).length}`);
  console.log(`ghi: ${OUT}`);
  process.exit(erred.length ? 1 : 0);
}

main().catch((e) => {
  console.error("loi:", e.message);
  process.exit(1);
});
