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
 * SÁU bậc, mỗi bậc một vai (khớp `--nq-t-*` trong globals.css). Trước đây có
 * mười hai lớp và bảy trong số đó nằm sát nhau tới mức mắt không phân biệt được
 * — nên mỗi trang tự chọn một lớp cho "tiêu đề khối" và không trang nào khớp
 * trang nào. Đo trên mã: `text-xs` 342 lần, `text-sm` 181, `text-2xs` 130 —
 * ba lớp nhỏ nhất chiếm 92% tổng số, tức phần lớn nội dung nằm ở vùng mà mắt
 * không tách được bậc.
 *
 * Các lớp CŨ vẫn được ánh xạ (không xoá khoá) để ~700 chỗ đang dùng không vỡ,
 * nhưng chúng trỏ về BẬC CỦA HỆ — nên markup cũ tự động nằm trong thang mới:
 *   text-[8/9/10/11px], text-xs, text-2xs  -> xs      (nhãn nhỏ nhất)
 *   text-sm                                -> sm      (phụ chú)
 *   text-base                              -> base    (chữ đọc chính)
 *   text-lg                                -> lg      (tiêu đề mục)
 *   text-xl, text-2xl                      -> xl      (tiêu đề khối)
 *   text-3xl, text-4xl                     -> 3xl     (tiêu đề trang)
 *   text-5xl, text-6xl                     -> 4xl     (mặt tiền)
 * `lineHeight` đi kèm từng bậc vì chữ có dấu tiếng Việt cần nhiều dòng hơn chữ
 * Latin thuần.
 */

/** @type {[string, { lineHeight: string; letterSpacing?: string }]} */
const TYPE_SCALE = {
  // ── SÁU BẬC CỦA HỆ ──
  xs: ["0.75rem", { lineHeight: "1.5" }],       // 12px  — nhãn, meta, đơn vị
  sm: ["0.84rem", { lineHeight: "1.55" }],      // 13.4px — phụ chú, dòng hai
  base: ["0.9375rem", { lineHeight: "1.65" }],  // 15px  — chữ đọc chính (--nq-t-body)
  lg: ["1.0625rem", { lineHeight: "1.45" }],    // 17px  — tiêu đề mục (--nq-t-h3)
  xl: ["1.25rem", { lineHeight: "1.3" }],       // 20px  — tiêu đề khối (--nq-t-h2)
  "3xl": ["clamp(1.5rem, 2.2vw, 1.85rem)", { lineHeight: "1.2" }],  // --nq-t-h1
  "4xl": ["clamp(1.9rem, 3.4vw, 2.6rem)", { lineHeight: "1.1" }],   // --nq-t-display

  // ── Ánh xạ lớp CŨ (giữ khoá để markup cũ không vỡ) ──
  "3xs": ["0.75rem", { lineHeight: "1.5" }],
  "2xs": ["0.75rem", { lineHeight: "1.5" }],
  "2xl": ["1.25rem", { lineHeight: "1.3" }],
  "5xl": ["clamp(1.9rem, 3.4vw, 2.6rem)", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
  "6xl": ["clamp(1.9rem, 3.4vw, 2.6rem)", { lineHeight: "1.02", letterSpacing: "-0.02em" }],
};

/** @type {Record<string, Record<string, string>>} */
const NHIP_QUAN_COLORS = {
  // Vàng cam — cảnh báo (thiếu người, sắp hạn, chờ xử lý).
  amber: {
      50: '#fef5e0',
      100: '#fde6af',
      200: '#fcd87f',
      300: '#fbc94e',
      400: '#f8b42c',
      500: '#f59e0b',
      600: '#c07c08',
      700: '#8a5a06',
      800: '#704907',
      900: '#573709',
      950: '#3d260a',
  },

  // = amber
  yellow: {
      50: '#fef5e0',
      100: '#fde6af',
      200: '#fcd87f',
      300: '#fbc94e',
      400: '#f8b42c',
      500: '#f59e0b',
      600: '#c07c08',
      700: '#8a5a06',
      800: '#704907',
      900: '#573709',
      950: '#3d260a',
  },

  // = amber
  orange: {
      50: '#fef5e0',
      100: '#fde6af',
      200: '#fcd87f',
      300: '#fbc94e',
      400: '#f8b42c',
      500: '#f59e0b',
      600: '#c07c08',
      700: '#8a5a06',
      800: '#704907',
      900: '#573709',
      950: '#3d260a',
  },

  // Xanh lá — tốt (đủ người, đã duyệt, hoàn tất).
  emerald: {
      50: '#dcfce7',
      100: '#b7f5cd',
      200: '#93eeb4',
      300: '#6ee79a',
      400: '#48d67c',
      500: '#22c55e',
      600: '#1ca24e',
      700: '#15803d',
      800: '#106530',
      900: '#0a4923',
      950: '#052e16',
  },

  // = emerald
  green: {
      50: '#dcfce7',
      100: '#b7f5cd',
      200: '#93eeb4',
      300: '#6ee79a',
      400: '#48d67c',
      500: '#22c55e',
      600: '#1ca24e',
      700: '#15803d',
      800: '#106530',
      900: '#0a4923',
      950: '#052e16',
  },

  // = emerald
  lime: {
      50: '#dcfce7',
      100: '#b7f5cd',
      200: '#93eeb4',
      300: '#6ee79a',
      400: '#48d67c',
      500: '#22c55e',
      600: '#1ca24e',
      700: '#15803d',
      800: '#106530',
      900: '#0a4923',
      950: '#052e16',
  },

  // Đỏ — lỗi (quá tải, vi phạm, thất bại).
  rose: {
      50: '#fee2e2',
      100: '#fcc7c7',
      200: '#f9adad',
      300: '#f79292',
      400: '#f36b6b',
      500: '#ef4444',
      600: '#ca3232',
      700: '#a52020',
      800: '#8e1c1c',
      900: '#771818',
      950: '#601414',
  },

  // = rose
  red: {
      50: '#fee2e2',
      100: '#fcc7c7',
      200: '#f9adad',
      300: '#f79292',
      400: '#f36b6b',
      500: '#ef4444',
      600: '#ca3232',
      700: '#a52020',
      800: '#8e1c1c',
      900: '#771818',
      950: '#601414',
  },

  // Xanh dương sáng — thông tin / đang xử lý / liên kết.
  sky: {
      50: '#e0f2fe',
      100: '#bfe8fd',
      200: '#9eddfd',
      300: '#7dd3fc',
      400: '#5ac8fa',
      500: '#38bdf8',
      600: '#1e93cc',
      700: '#0369a1',
      800: '#055684',
      900: '#064266',
      950: '#082f49',
  },

  // = sky
  blue: {
      50: '#e0f2fe',
      100: '#bfe8fd',
      200: '#9eddfd',
      300: '#7dd3fc',
      400: '#5ac8fa',
      500: '#38bdf8',
      600: '#1e93cc',
      700: '#0369a1',
      800: '#055684',
      900: '#064266',
      950: '#082f49',
  },

  // = sky
  indigo: {
      50: '#e0f2fe',
      100: '#bfe8fd',
      200: '#9eddfd',
      300: '#7dd3fc',
      400: '#5ac8fa',
      500: '#38bdf8',
      600: '#1e93cc',
      700: '#0369a1',
      800: '#055684',
      900: '#064266',
      950: '#082f49',
  },

  // = sky
  purple: {
      50: '#e0f2fe',
      100: '#bfe8fd',
      200: '#9eddfd',
      300: '#7dd3fc',
      400: '#5ac8fa',
      500: '#38bdf8',
      600: '#1e93cc',
      700: '#0369a1',
      800: '#055684',
      900: '#064266',
      950: '#082f49',
  },

  // = sky
  violet: {
      50: '#e0f2fe',
      100: '#bfe8fd',
      200: '#9eddfd',
      300: '#7dd3fc',
      400: '#5ac8fa',
      500: '#38bdf8',
      600: '#1e93cc',
      700: '#0369a1',
      800: '#055684',
      900: '#064266',
      950: '#082f49',
  },

  // = sky
  cyan: {
      50: '#e0f2fe',
      100: '#bfe8fd',
      200: '#9eddfd',
      300: '#7dd3fc',
      400: '#5ac8fa',
      500: '#38bdf8',
      600: '#1e93cc',
      700: '#0369a1',
      800: '#055684',
      900: '#064266',
      950: '#082f49',
  },

  // = sky
  teal: {
      50: '#e0f2fe',
      100: '#bfe8fd',
      200: '#9eddfd',
      300: '#7dd3fc',
      400: '#5ac8fa',
      500: '#38bdf8',
      600: '#1e93cc',
      700: '#0369a1',
      800: '#055684',
      900: '#064266',
      950: '#082f49',
  },

  // = sky
  fuchsia: {
      50: '#e0f2fe',
      100: '#bfe8fd',
      200: '#9eddfd',
      300: '#7dd3fc',
      400: '#5ac8fa',
      500: '#38bdf8',
      600: '#1e93cc',
      700: '#0369a1',
      800: '#055684',
      900: '#064266',
      950: '#082f49',
  },

  // = sky
  pink: {
      50: '#e0f2fe',
      100: '#bfe8fd',
      200: '#9eddfd',
      300: '#7dd3fc',
      400: '#5ac8fa',
      500: '#38bdf8',
      600: '#1e93cc',
      700: '#0369a1',
      800: '#055684',
      900: '#064266',
      950: '#082f49',
  },

  // Xanh xám lạnh — chữ phụ và nền tối.
  zinc: {
      50: '#e6edf3',
      100: '#d6dfe7',
      200: '#c6d2db',
      300: '#b6c4cf',
      400: '#93a3b0',
      500: '#5f7180',
      600: '#455462',
      700: '#2b3843',
      800: '#212c36',
      900: '#172128',
      950: '#0d151b',
  },

  // = zinc
  neutral: {
      50: '#e6edf3',
      100: '#d6dfe7',
      200: '#c6d2db',
      300: '#b6c4cf',
      400: '#93a3b0',
      500: '#5f7180',
      600: '#455462',
      700: '#2b3843',
      800: '#212c36',
      900: '#172128',
      950: '#0d151b',
  },

  // = zinc
  slate: {
      50: '#e6edf3',
      100: '#d6dfe7',
      200: '#c6d2db',
      300: '#b6c4cf',
      400: '#93a3b0',
      500: '#5f7180',
      600: '#455462',
      700: '#2b3843',
      800: '#212c36',
      900: '#172128',
      950: '#0d151b',
  },

  // = zinc
  gray: {
      50: '#e6edf3',
      100: '#d6dfe7',
      200: '#c6d2db',
      300: '#b6c4cf',
      400: '#93a3b0',
      500: '#5f7180',
      600: '#455462',
      700: '#2b3843',
      800: '#212c36',
      900: '#172128',
      950: '#0d151b',
  },

  // = zinc
  grey: {
      50: '#e6edf3',
      100: '#d6dfe7',
      200: '#c6d2db',
      300: '#b6c4cf',
      400: '#93a3b0',
      500: '#5f7180',
      600: '#455462',
      700: '#2b3843',
      800: '#212c36',
      900: '#172128',
      950: '#0d151b',
  },

  // = zinc
  stone: {
      50: '#e6edf3',
      100: '#d6dfe7',
      200: '#c6d2db',
      300: '#b6c4cf',
      400: '#93a3b0',
      500: '#5f7180',
      600: '#455462',
      700: '#2b3843',
      800: '#212c36',
      900: '#172128',
      950: '#0d151b',
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
