/**
 * Bảng màu Tailwind gốc — NHỊP QUÁN.
 *
 * Vì sao bảng màu nằm ở đây thay vì sửa từng lớp trong markup:
 * mã đang dùng 13 họ màu mặc định của Tailwind (amber, emerald, rose, zinc,
 * purple, indigo...) ở đủ 11 bậc, khoảng 1.100 chỗ. Đó là bảng màu mặc định
 * của mọi dashboard do máy dựng — xám trung tính, vàng/ngọc/hồng bão hoà kiểu
 * "dark mode mặc định", không liên quan gì tới một quán cà phê vận hành ban
 * đêm. Sửa 1.100 chỗ trong markup là không kiểm chứng được; thay bảng màu ở
 * tầng cấu hình thì mọi lớp sẵn có tự trỏ về màu của quán, giữ nguyên thang
 * bậc mà mã đang dựa vào.
 *
 * Nguồn: do `scripts/gen_tailwind_palette.py` sinh và kiểm chứng. Script đó đo
 * từng tổ hợp lớp mà mã THỰC SỰ dùng (chữ sáng trên nền tối, chữ tối trên nút
 * sáng, nền pha loãng, hình chỉ báo) và chặn nếu có tổ hợp tụt dưới ngưỡng
 * WCAG. Đừng sửa tay file này — sửa ở script rồi chạy lại:
 *
 *   python scripts/gen_tailwind_palette.py            # kiểm chứng (exit 0 = đạt)
 *   python scripts/gen_tailwind_palette.py --emit-js  # in bảng mới
 */

/**
 * Thang chữ — ghi đè mặc định của Tailwind để mọi cỡ chữ trong app thuộc MỘT
 * thang, thay vì mỗi file tự chọn.
 *
 * Số đo trước khi đổi (đếm trong src): 13 cỡ chữ khác nhau đang chạy —
 * text-xs 343 lần, text-sm 190, text-[10px] 76, text-[11px] 61, text-lg 23,
 * text-base 17, text-3xl 11, text-[9px] 10, text-2xl 10, text-xl 9, text-4xl 9,
 * text-5xl 5, text-6xl 2, text-[8px] 1. Bốn cỡ nhỏ nhất (8/9/10/11px) đều nằm
 * dưới 12px — dưới ngưỡng đọc được, và tiếng Việt có dấu ở cỡ đó thì dấu chồng
 * lên nhau. Đó là "năm cỡ chữ ở chỗ ba cỡ là đủ" trong danh mục lỗi.
 *
 * Bảng dưới đây ánh xạ từng lớp cũ về bậc của hệ (khớp `--nq-t-*` trong
 * globals.css). Vì là ghi đè `fontSize` nên mọi lớp sẵn có tự đổi — không phải
 * sửa 780 chỗ trong markup. `lineHeight` đi kèm từng bậc vì chữ có dấu tiếng
 * Việt cần nhiều dòng hơn chữ Latin thuần.
 */

/** @type {[string, { lineHeight: string; letterSpacing?: string }]} */
const TYPE_SCALE = {
  // Bậc thấp nhất còn đọc được — chỉ dùng cho nhãn số trên badge/huy hiệu.
  "3xs": ["0.625rem", { lineHeight: "1.5" }],   // 10px
  "2xs": ["0.6875rem", { lineHeight: "1.5" }],  // 11px — text-[9px] cũ
  xs: ["0.75rem", { lineHeight: "1.55" }],      // 12px — text-[10px]/[11px]/xs cũ
  sm: ["0.84rem", { lineHeight: "1.55" }],      // 13.4px — text-sm cũ
  base: ["0.9375rem", { lineHeight: "1.65" }],  // 15px — text-base cũ
  lg: ["1.0625rem", { lineHeight: "1.5" }],     // 17px — text-lg cũ
  // text-xl/2xl/3xl/4xl cũ đều là tiêu đề khối trở lên → gom về thang tiêu đề.
  xl: ["1.2rem", { lineHeight: "1.3" }],        // --nq-t-h2
  "2xl": ["1.375rem", { lineHeight: "1.25" }],
  "3xl": ["1.6rem", { lineHeight: "1.15" }],    // --nq-t-h1
  "4xl": ["1.9rem", { lineHeight: "1.1" }],     // --nq-t-display
  "5xl": ["2.2rem", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
  "6xl": ["2.6rem", { lineHeight: "1.02", letterSpacing: "-0.02em" }],
};

/** @type {Record<string, Record<string, string>>} */
const NHIP_QUAN_COLORS = {
  // Vàng đèn quầy — cảnh báo (thiếu người, sắp hạn, chờ xử lý).
  amber: {
    50: "#fbeecb", 100: "#f7e3ac", 200: "#ead188", 300: "#deb444", 400: "#d6a82d",
    500: "#cd9b16", 600: "#be8e14", 700: "#6d520d", 800: "#5b420c", 900: "#4a320b",
    950: "#38220a",
  },
  yellow: {
    50: "#fbeecb", 100: "#f7e3ac", 200: "#ead188", 300: "#deb444", 400: "#d6a82d",
    500: "#cd9b16", 600: "#be8e14", 700: "#6d520d", 800: "#5b420c", 900: "#4a320b",
    950: "#38220a",
  },
  orange: {
    50: "#fbeecb", 100: "#f7e3ac", 200: "#ead188", 300: "#deb444", 400: "#d6a82d",
    500: "#cd9b16", 600: "#be8e14", 700: "#6d520d", 800: "#5b420c", 900: "#4a320b",
    950: "#38220a",
  },

  // Xanh lá trà — tốt (đủ người, đúng hạn, đã xong).
  emerald: {
    50: "#dcebe1", 100: "#c4dbc9", 200: "#accbab", 300: "#8aaf94", 400: "#7aa384",
    500: "#639170", 600: "#567f63", 700: "#3d5c47", 800: "#2b4533", 900: "#1d3225",
    950: "#0e2b1d",
  },
  green: {
    50: "#dcebe1", 100: "#c4dbc9", 200: "#accbab", 300: "#8aaf94", 400: "#7aa384",
    500: "#639170", 600: "#567f63", 700: "#3d5c47", 800: "#2b4533", 900: "#1d3225",
    950: "#0e2b1d",
  },
  lime: {
    50: "#dcebe1", 100: "#c4dbc9", 200: "#accbab", 300: "#8aaf94", 400: "#7aa384",
    500: "#639170", 600: "#567f63", 700: "#3d5c47", 800: "#2b4533", 900: "#1d3225",
    950: "#0e2b1d",
  },

  // Đỏ gạch nung — lỗi (quá hạn, trống ca, gửi thất bại).
  rose: {
    50: "#f7dcd7", 100: "#efbdb2", 200: "#e6a294", 300: "#dd7d6d", 400: "#d66f5e",
    500: "#cf6150", 600: "#bd5949", 700: "#8a3f34", 800: "#6b2f28", 900: "#55201e",
    950: "#3a1013",
  },
  red: {
    50: "#f7dcd7", 100: "#efbdb2", 200: "#e6a294", 300: "#dd7d6d", 400: "#d66f5e",
    500: "#cf6150", 600: "#bd5949", 700: "#8a3f34", 800: "#6b2f28", 900: "#55201e",
    950: "#3a1013",
  },

  // Xanh khói — trạng thái đang xử lý, chờ xác nhận (chưa xấu).
  // Họ này thay toàn bộ purple/indigo/violet/cyan/teal/fuchsia/pink: các họ đó
  // trong mã đều là màu trang trí, không mang nghĩa nghiệp vụ nào.
  sky: {
    50: "#dbe8f2", 100: "#c0d2e0", 200: "#a4bcd0", 300: "#88a5bf", 400: "#7797b3",
    500: "#6b8aa8", 600: "#5c7893", 700: "#40566a", 800: "#2b3c4c", 900: "#20303f",
    950: "#16283a",
  },
  blue: {
    50: "#dbe8f2", 100: "#c0d2e0", 200: "#a4bcd0", 300: "#88a5bf", 400: "#7797b3",
    500: "#6b8aa8", 600: "#5c7893", 700: "#40566a", 800: "#2b3c4c", 900: "#20303f",
    950: "#16283a",
  },
  indigo: {
    50: "#dbe8f2", 100: "#c0d2e0", 200: "#a4bcd0", 300: "#88a5bf", 400: "#7797b3",
    500: "#6b8aa8", 600: "#5c7893", 700: "#40566a", 800: "#2b3c4c", 900: "#20303f",
    950: "#16283a",
  },
  purple: {
    50: "#dbe8f2", 100: "#c0d2e0", 200: "#a4bcd0", 300: "#88a5bf", 400: "#7797b3",
    500: "#6b8aa8", 600: "#5c7893", 700: "#40566a", 800: "#2b3c4c", 900: "#20303f",
    950: "#16283a",
  },
  violet: {
    50: "#dbe8f2", 100: "#c0d2e0", 200: "#a4bcd0", 300: "#88a5bf", 400: "#7797b3",
    500: "#6b8aa8", 600: "#5c7893", 700: "#40566a", 800: "#2b3c4c", 900: "#20303f",
    950: "#16283a",
  },
  cyan: {
    50: "#dbe8f2", 100: "#c0d2e0", 200: "#a4bcd0", 300: "#88a5bf", 400: "#7797b3",
    500: "#6b8aa8", 600: "#5c7893", 700: "#40566a", 800: "#2b3c4c", 900: "#20303f",
    950: "#16283a",
  },
  teal: {
    50: "#dbe8f2", 100: "#c0d2e0", 200: "#a4bcd0", 300: "#88a5bf", 400: "#7797b3",
    500: "#6b8aa8", 600: "#5c7893", 700: "#40566a", 800: "#2b3c4c", 900: "#20303f",
    950: "#16283a",
  },
  fuchsia: {
    50: "#dbe8f2", 100: "#c0d2e0", 200: "#a4bcd0", 300: "#88a5bf", 400: "#7797b3",
    500: "#6b8aa8", 600: "#5c7893", 700: "#40566a", 800: "#2b3c4c", 900: "#20303f",
    950: "#16283a",
  },
  pink: {
    50: "#dbe8f2", 100: "#c0d2e0", 200: "#a4bcd0", 300: "#88a5bf", 400: "#7797b3",
    500: "#6b8aa8", 600: "#5c7893", 700: "#40566a", 800: "#2b3c4c", 900: "#20303f",
    950: "#16283a",
  },

  // Than và gỗ — chữ phụ, nền tối, vạch kẻ. Bậc 300–400 giữ đúng độ sáng của
  // `--nq-ink-muted` để chỗ nào đang dùng `text-zinc-400` cho chữ phụ vẫn đọc
  // được (đo: 7.20:1 trên nền trang, hơn cả bảng mặc định 7.02:1).
  zinc: {
    50: "#f5ead8", 100: "#dfd5c4", 200: "#cec5b5", 300: "#beb5a6", 400: "#aba396",
    500: "#6f675e", 600: "#544d46", 700: "#38332e", 800: "#292521", 900: "#1d1a18",
    950: "#131110",
  },
  neutral: {
    50: "#f5ead8", 100: "#dfd5c4", 200: "#cec5b5", 300: "#beb5a6", 400: "#aba396",
    500: "#6f675e", 600: "#544d46", 700: "#38332e", 800: "#292521", 900: "#1d1a18",
    950: "#131110",
  },
  stone: {
    50: "#f5ead8", 100: "#dfd5c4", 200: "#cec5b5", 300: "#beb5a6", 400: "#aba396",
    500: "#6f675e", 600: "#544d46", 700: "#38332e", 800: "#292521", 900: "#1d1a18",
    950: "#131110",
  },
  slate: {
    50: "#f5ead8", 100: "#dfd5c4", 200: "#cec5b5", 300: "#beb5a6", 400: "#aba396",
    500: "#6f675e", 600: "#544d46", 700: "#38332e", 800: "#292521", 900: "#1d1a18",
    950: "#131110",
  },
  gray: {
    50: "#f5ead8", 100: "#dfd5c4", 200: "#cec5b5", 300: "#beb5a6", 400: "#aba396",
    500: "#6f675e", 600: "#544d46", 700: "#38332e", 800: "#292521", 900: "#1d1a18",
    950: "#131110",
  },
  grey: {
    50: "#f5ead8", 100: "#dfd5c4", 200: "#cec5b5", 300: "#beb5a6", 400: "#aba396",
    500: "#6f675e", 600: "#544d46", 700: "#38332e", 800: "#292521", 900: "#1d1a18",
    950: "#131110",
  },
};

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: NHIP_QUAN_COLORS,
      fontSize: TYPE_SCALE,
    },
  },
  plugins: [],
}
