/**
 * Cầu nối `globals.css` → `framer-motion`.
 *
 * Vì sao cần tệp này: `framer-motion` nhận thời lượng bằng số giây và đường cong
 * bằng mảng số ngay trong JavaScript, nên nó **không đọc được** `var(--nq-beat-*)`
 * hay `var(--nq-ease-out)`. Không có cầu nối thì mỗi component tự khai báo giá
 * trị riêng, và thang nhịp trên giấy không ràng buộc được gì.
 *
 * Đo trên mã nguồn trước khi viết tệp này — 7 tệp dùng `framer-motion`, và có
 * **7 mốc thời lượng** khác nhau trong khi thang nhịp chỉ định nghĩa **4 bậc**:
 * `0.22` (đúng `beat-settle`) · `0.3` · `0.35` · `0.4` · `0.42` (đúng
 * `beat-focus`) · `0.48` · `0.6`. Đường cong thì đã trùng `--nq-ease-out` ở mọi
 * chỗ, nhưng trùng hợp không phải ràng buộc — không có gì ngăn lần sửa sau lệch đi.
 *
 * Nguồn sự thật vẫn là `globals.css`. Tệp này **đọc biến CSS lúc chạy**, không
 * chép lại giá trị — nên đổi một bậc nhịp trong CSS là đổi luôn chuyển động của
 * mọi component, không phải đi tìm từng tệp.
 *
 * Giá trị dự phòng bên dưới chỉ dùng khi chưa có DOM (lần render phía server).
 * Chúng **phải bằng đúng** giá trị trong `globals.css` — cổng
 * `scripts/audit_motion_tokens.py` kiểm tra điều đó, và kiểm tra luôn rằng không
 * tệp nào ngoài tệp này còn khai báo thời lượng/đường cong bằng số.
 */

export type BeatName = "ack" | "settle" | "focus" | "chapter";

/** Bốn điểm điều khiển của `cubic-bezier(x1, y1, x2, y2)`. */
export type Cubic = [number, number, number, number];

export type Transition = {
  duration: number;
  delay: number;
  ease: Cubic;
};

/**
 * Bốn nhịp, đặt tên theo việc nó phục vụ — không theo con số. Ý nghĩa từng bậc
 * chép từ `globals.css`; chọn sai bậc thì chuyển động vẫn chạy nhưng nói sai
 * chuyện:
 *   ack      phản hồi cú bấm (lún, đổi màu). Phải xong dưới 200ms.
 *   settle   trạng thái đổi tại chỗ (hover, mở chip, gạt tab).
 *   focus    đưa mắt tới một khối mới xuất hiện (bảng tải xong, kết quả mới).
 *   chapter  chuyển "chương" — chỉ dùng ở mặt tiền (landing/login/hub).
 */
const FALLBACK_SECONDS: Record<BeatName, number> = {
  ack: 0.14,
  settle: 0.22,
  focus: 0.42,
  chapter: 0.72,
};

const FALLBACK_EASE_OUT: Cubic = [0.22, 1, 0.36, 1];
const FALLBACK_EASE_INOUT: Cubic = [0.65, 0, 0.35, 1];

const BEAT_VAR: Record<BeatName, string> = {
  ack: "--nq-beat-ack",
  settle: "--nq-beat-settle",
  focus: "--nq-beat-focus",
  chapter: "--nq-beat-chapter",
};

const EASE_OUT_VAR = "--nq-ease-out";
const EASE_INOUT_VAR = "--nq-ease-inout";

function readVar(name: string): string {
  if (typeof window === "undefined") return "";
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** `"420ms"` → `0.42`; `"0.42s"` → `0.42`. Trả về dự phòng nếu không đọc được. */
function parseSeconds(raw: string, fallback: number): number {
  const m = /^(-?[\d.]+)(ms|s)$/.exec(raw);
  if (!m) return fallback;
  const n = Number(m[1]);
  if (!Number.isFinite(n)) return fallback;
  return m[2] === "ms" ? n / 1000 : n;
}

/** `"cubic-bezier(0.22, 1, 0.36, 1)"` → `[0.22, 1, 0.36, 1]`. */
function parseCubic(raw: string, fallback: Cubic): Cubic {
  const m = /^cubic-bezier\(([^)]*)\)$/.exec(raw);
  if (!m) return fallback;
  const parts = m[1].split(",").map((s) => Number(s.trim()));
  if (parts.length !== 4 || !parts.every((n) => Number.isFinite(n))) return fallback;
  return [parts[0], parts[1], parts[2], parts[3]];
}

/**
 * Đọc một lần rồi nhớ. Lần đọc đầu tiên diễn ra khi component render trên
 * trình duyệt — lúc đó bảng kiểu đã áp dụng xong, nên giá trị đọc được là giá
 * trị thật. Trước đó (render phía server) dùng dự phòng, và vì dự phòng bằng
 * đúng giá trị CSS nên không có chênh lệch khi thuỷ hợp.
 */
const secondsCache = new Map<BeatName, number>();
const cubicCache = new Map<string, Cubic>();

function cachedCubic(name: string, fallback: Cubic): Cubic {
  const hit = cubicCache.get(name);
  if (hit !== undefined) return hit;
  const value = parseCubic(readVar(name), fallback);
  cubicCache.set(name, value);
  return value;
}

/** Thời lượng của một bậc nhịp, tính bằng giây — cho chỗ cần tự tính toán. */
export function beatSeconds(name: BeatName): number {
  const hit = secondsCache.get(name);
  if (hit !== undefined) return hit;
  const value = parseSeconds(readVar(BEAT_VAR[name]), FALLBACK_SECONDS[name]);
  secondsCache.set(name, value);
  return value;
}

/** Đường cong duy nhất cho chuyển động vào. */
export function easeOut(): Cubic {
  return cachedCubic(EASE_OUT_VAR, FALLBACK_EASE_OUT);
}

/** Chỉ dùng khi phần tử đi qua lại giữa hai vị trí đều có nghĩa. */
export function easeInOut(): Cubic {
  return cachedCubic(EASE_INOUT_VAR, FALLBACK_EASE_INOUT);
}

/**
 * Đối tượng `transition` cho `framer-motion`, lấy nhịp từ thang của hệ.
 *
 * `delayS` là độ trễ bằng giây. Cố ý không đặt mặc định theo số bậc — độ trễ là
 * chuyện so le của từng danh sách, không phải một bậc nhịp.
 */
export function beat(name: BeatName, delayS = 0): Transition {
  return { duration: beatSeconds(name), delay: delayS, ease: easeOut() };
}

/** Như `beat`, nhưng dùng đường cong đi-về. Chỉ cho chỗ đi rồi về đều có nghĩa. */
export function beatInOut(name: BeatName, delayS = 0): Transition {
  return { duration: beatSeconds(name), delay: delayS, ease: easeInOut() };
}

/**
 * Chu kỳ của một vòng lặp **do người dùng khởi động** (ví dụ vòng tròn dấu gạch
 * của logo quay khi trỏ vào).
 *
 * Vì sao không nằm trong thang nhịp: `beat-*` là **thời lượng chuyển tiếp** —
 * thời gian để một thứ đi từ trạng thái A sang B rồi dừng. Vòng lặp không có
 * đích, nó có **chu kỳ**. Trộn hai đại lượng vào một thang là nói sai bản chất,
 * nên nó được tách ra và đặt tên riêng.
 *
 * 1.2s: vòng tròn gạch 4/8 có 12,5 chu kỳ quanh chu vi. Ngắn hơn 1s thì thành
 * nhấp nháy; dài hơn 2s thì mắt không còn đọc ra là "đang quay". Khoảng giữa đó
 * đọc ra chuyển động đều — đúng nhịp gõ đều của tên quán.
 */
export const LOOP_PERIOD_S = 1.2;

/**
 * Đường cong tuyến tính, cho chuyển động vòng lặp.
 *
 * Vòng lặp phải **đều**: dùng `ease-out` thì mỗi vòng lại khựng ở cuối, và mắt
 * đọc ra mười hai vòng riêng lẻ thay vì một chuyển động liền. `globals.css` đã
 * ghi rõ `ease-inout` "chỉ dùng khi phần tử đi qua lại giữa hai vị trí đều có
 * nghĩa", nên vòng lặp quay một chiều không thuộc trường hợp đó.
 */
export const LINEAR: Cubic = [0, 0, 1, 1];

/**
 * Nhịp so le cho danh sách.
 *
 * Không phải một bậc trong thang nhịp: nó là **khoảng chia** giữa các phần tử,
 * nên phải theo số phần tử chứ không theo một mốc cố định. Trước đây mã nguồn
 * dùng hai giá trị khác nhau (`0.05` và `0.06`) cho cùng một ý.
 *
 * Ràng buộc để chọn 40ms: danh sách dài nhất được vẽ có giới hạn là 8 mục
 * (`TonBarChart` cắt còn 8). Mục cuối nhận trễ `7 × 40ms = 280ms`, cộng
 * `beat-focus` (420ms) là `700ms` — vẫn nằm trong `beat-chapter` (720ms), tức
 * toàn bộ danh sách đã vào chỗ trước khi mắt kịp rời đi.
 */
export const STAGGER_S = 0.04;

/**
 * Lò xo cho việc **bám theo con trỏ** — nghiêng thẻ, kéo tay nắm.
 *
 * Vì sao cần một hàm riêng thay vì dùng `beat()`: chuyển động bám con trỏ không
 * chạy theo `duration`, nó chạy theo độ cứng lò xo. Nhưng nếu để tự do thì giá
 * trị sẽ trôi khỏi thang nhịp — đúng chuyện đã xảy ra: `kpi-card.tsx` khai
 * `stiffness 320 / damping 30 / mass 0.6` kèm chú thích "đặt theo nhịp
 * `beat-settle`", trong khi đo lại thì lò xo đó cần **292ms** mới ổn định, không
 * phải 220ms như `beat-settle`. Chú thích nói một đàng, con số làm một nẻo.
 *
 * Cách suy ra: chọn **tắt dần tới hạn** (`zeta = 1`) để không bao giờ vượt đích —
 * với bảng số liệu, độ nảy khiến con số rung khi người dùng chỉ đang rê chuột
 * qua. Với `zeta = 1`, độ lệch còn lại là `(1 + u)·e^(-u)`; lấy `2%` làm mốc
 * "đã vào chỗ" thì `u = 5.83`, nên `omega_n = 5.83 / T` và
 * `stiffness = m·omega_n²`, `damping = 2·m·omega_n`.
 *
 * `zeta` nhỏ hơn 1 một chút vẫn giữ được tính không-nảy (dưới ngưỡng cảm nhận)
 * mà phản hồi nhanh hơn, nên giữ nguyên `mass` của bên gọi để khớp quán tính kéo.
 */
export function springFor(name: BeatName, mass = 0.6): {
  type: "spring";
  stiffness: number;
  damping: number;
  mass: number;
} {
  const t = beatSeconds(name);
  const omega = 5.83 / t;
  return {
    type: "spring",
    stiffness: Math.round(mass * omega * omega),
    damping: Math.round(2 * mass * omega * 10) / 10,
    mass,
  };
}
