/**
 * Font self-host — file nằm TRONG repo, nạp qua `next/font/local`.
 *
 * ── Vì sao KHÔNG dùng `next/font/google` ──
 * `next/font/google` tải font lúc BUILD. Trong Docker build của CI, lời gọi tới
 * `@next/font/dist/google/loader.js` vỡ:
 *
 *     An error occurred in `next/font`.
 *     TypeError: Cannot read properties of null (reading '1')
 *     at .../@next/font/dist/google/loader.js:122:78
 *     at async nextFontGoogleFontLoader
 *
 * Triệu chứng đánh lừa: `next build` ở máy local XANH, chỉ image build trong
 * Docker ĐỎ — nên lỗi ẩn tới tận bước deploy. Nguyên nhân: loader của Next đọc
 * phản hồi Google như CSS và không khớp khi Google trả trang khác (400 /
 * rate-limit / trang đồng ý), rồi truy cập nhóm bắt `null`.
 *
 * Điều quan trọng: đây KHÔNG chỉ là lỗi CI. Guideline của repo
 * (docs/design-guidelines.md §Typography) đã yêu cầu "self-host, không CDN" và
 * nêu cổng §14.9: **demo phải chạy khi đã rút mạng**. Nạp font qua mạng ở bước
 * build nghĩa là build KHÔNG TẤT ĐỊNH — hôm nay xanh, mai Google trả khác là đỏ.
 * `next/font/local` cắt hẳn phụ thuộc đó: build không cần mạng, runtime cũng không.
 *
 * ── File font ──
 * `apps/web/src/fonts/*.woff2`, tải một lần rồi commit vào repo.
 * Mỗi họ có 3 subset (latin, latin-ext, vietnamese) cho từng weight.
 * `next/font/local` tự phát `@font-face` kèm `unicode-range` đúng cho từng file,
 * nên trình duyệt chỉ tải subset cần — cùng hành vi như bản Google, nhưng không
 * phụ thuộc mạng lúc build.
 *
 * Ba font, ba vai — không hơn (xem docs/design-guidelines.md):
 *   fontDisplay  Space Grotesk   tiêu đề trang và tiêu đề khối
 *   fontBody     IBM Plex Sans   chữ đọc chính, nhãn, nút
 *   fontMono     IBM Plex Mono   số trong bảng, mã, thời lượng
 * Không dùng font hệ thống làm font chính: máy nào cũng có, nên không mã hoá
 * được gì và trông giống mọi dashboard khác.
 *
 * SỬA ĐƯỢC KÈM THEO: IBM Plex Mono trước đây KHÔNG khai subset `vietnamese`, nên
 * chữ có dấu trong bảng/mã/mono rơi về font fallback. Nay đã có đủ 3 subset.
 */
import localFont from "next/font/local";

/*
  LƯU Ý KỸ THUẬT: `next/font/local` phân tích `src` ở tầng BIÊN DỊCH và đòi mọi
  giá trị phải là CHUỖI VIẾT THẲNG. Không dùng được vòng lặp hay hàm sinh mảng —
  build sẽ báo "Font loader values must be explicitly written literals". Vì vậy
  khối `src` dưới đây dài, và đó là điều bắt buộc, không phải viết tay cẩu thả.

  Mỗi họ liệt kê đủ 3 subset (latin, latin-ext, vietnamese) cho từng weight.
  `unicode-range` do Next tự sinh theo từng file, nên trình duyệt chỉ tải subset
  cần — cùng hành vi như bản Google, nhưng build không cần mạng.
*/

/**
 * Tiêu đề. Hình học, hơi nén, có cá tính ở chữ số và dấu câu — đủ khác để tiêu
 * đề trang không lẫn với chữ nội dung, nhưng không trang trí tới mức át số liệu
 * đặt cạnh nó.
 */
export const fontDisplay = localFont({
  src: [
    { path: "../fonts/space-grotesk-400-latin.woff2", weight: "400", style: "normal" },
    { path: "../fonts/space-grotesk-400-latin-ext.woff2", weight: "400", style: "normal" },
    { path: "../fonts/space-grotesk-400-vietnamese.woff2", weight: "400", style: "normal" },
    { path: "../fonts/space-grotesk-500-latin.woff2", weight: "500", style: "normal" },
    { path: "../fonts/space-grotesk-500-latin-ext.woff2", weight: "500", style: "normal" },
    { path: "../fonts/space-grotesk-500-vietnamese.woff2", weight: "500", style: "normal" },
    { path: "../fonts/space-grotesk-600-latin.woff2", weight: "600", style: "normal" },
    { path: "../fonts/space-grotesk-600-latin-ext.woff2", weight: "600", style: "normal" },
    { path: "../fonts/space-grotesk-600-vietnamese.woff2", weight: "600", style: "normal" },
    { path: "../fonts/space-grotesk-700-latin.woff2", weight: "700", style: "normal" },
    { path: "../fonts/space-grotesk-700-latin-ext.woff2", weight: "700", style: "normal" },
    { path: "../fonts/space-grotesk-700-vietnamese.woff2", weight: "700", style: "normal" },
  ],
  variable: "--nq-font-display-var",
  display: "swap",
  fallback: ["Avenir Next", "Segoe UI", "sans-serif"],
  /* Không preload display/mono: preload cả 3 họ nghĩa là tải ~300KB woff2 trước
     khi trang vẽ được, mà hai họ này chỉ dùng ở một số khối. Chỉ preload fontBody
     — đó là chữ đọc chính, xuất hiện ở mọi trang. */
  preload: false,
});

/**
 * Chữ đọc chính. Cùng họ với font số liệu nên bảng và văn bản quanh nó có chung
 * tỉ lệ chữ; dấu tiếng Việt ở cỡ nhỏ rõ hơn phần lớn font sans hình học.
 */
export const fontBody = localFont({
  src: [
    { path: "../fonts/ibm-plex-sans-400-latin.woff2", weight: "400", style: "normal" },
    { path: "../fonts/ibm-plex-sans-400-latin-ext.woff2", weight: "400", style: "normal" },
    { path: "../fonts/ibm-plex-sans-400-vietnamese.woff2", weight: "400", style: "normal" },
    { path: "../fonts/ibm-plex-sans-500-latin.woff2", weight: "500", style: "normal" },
    { path: "../fonts/ibm-plex-sans-500-latin-ext.woff2", weight: "500", style: "normal" },
    { path: "../fonts/ibm-plex-sans-500-vietnamese.woff2", weight: "500", style: "normal" },
    { path: "../fonts/ibm-plex-sans-600-latin.woff2", weight: "600", style: "normal" },
    { path: "../fonts/ibm-plex-sans-600-latin-ext.woff2", weight: "600", style: "normal" },
    { path: "../fonts/ibm-plex-sans-600-vietnamese.woff2", weight: "600", style: "normal" },
  ],
  variable: "--nq-font-body-var",
  display: "swap",
  fallback: ["system-ui", "sans-serif"],
  preload: true,
});

/**
 * Số liệu. Bề rộng chữ số bằng nhau (tabular) nên cột số trong bảng không nhảy
 * khi giá trị đổi từ 9 sang 10.
 * Trước đây thiếu subset `vietnamese` → chữ có dấu trong bảng/mã rơi về fallback.
 */
export const fontMono = localFont({
  src: [
    { path: "../fonts/ibm-plex-mono-400-latin.woff2", weight: "400", style: "normal" },
    { path: "../fonts/ibm-plex-mono-400-latin-ext.woff2", weight: "400", style: "normal" },
    { path: "../fonts/ibm-plex-mono-400-vietnamese.woff2", weight: "400", style: "normal" },
    { path: "../fonts/ibm-plex-mono-500-latin.woff2", weight: "500", style: "normal" },
    { path: "../fonts/ibm-plex-mono-500-latin-ext.woff2", weight: "500", style: "normal" },
    { path: "../fonts/ibm-plex-mono-500-vietnamese.woff2", weight: "500", style: "normal" },
  ],
  variable: "--nq-font-mono-var",
  display: "swap",
  fallback: ["ui-monospace", "monospace"],
  preload: false,
});

/** Class gộp, gắn vào <html> để mọi biến font có mặt toàn trang. */
export const fontClass = [
  fontDisplay.variable,
  fontBody.variable,
  fontMono.variable,
].join(" ");
