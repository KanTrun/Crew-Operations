"use client";

/**
 * Tour hướng dẫn cho người lần đầu vào quán.
 *
 * Vì sao tự viết thay vì lấy thư viện tour: §10.3 giữ dự án ở mức 0 đồng và
 * `docs/design-guidelines.md` cấm thêm dependency runtime. Toàn bộ tour là ba
 * thứ có sẵn trong nền tảng: `getBoundingClientRect` để vẽ vòng sáng, một hộp
 * thoại `role="dialog"` để giải thích, `localStorage` để nhớ đã xem.
 *
 * Ba ràng buộc tiếp cận, không được bỏ:
 *  - `Esc` đóng tour ở bất kỳ bước nào.
 *  - `Tab` không thoát khỏi hộp thoại (bẫy tiêu điểm), vì phía sau là cả trang
 *    nút bấm mà người dùng chưa nên chạm tới.
 *  - `aria-modal` + `aria-labelledby` để trình đọc màn hình biết đây là lớp phủ.
 *
 * "AI hướng dẫn" ở đây là AG-SOP thật, không phải hộp chat giả: mỗi bước có một
 * hai câu hỏi bấm được, bấm là sang `/sop` với câu đã điền sẵn. AG-SOP chỉ trả
 * lời từ mẫu phiếu và cẩm nang quán, kèm trích dẫn nguồn; không có căn cứ thì
 * nói thẳng là chưa có trong cẩm nang.
 *
 * Nội dung khác nhau theo vai: quản lý đi đường xếp lịch và duyệt, nhân viên đi
 * đường chạy phiếu và nhận ca. Đưa nhân viên đi xem Hộp thư ràng buộc là dạy
 * việc họ không có quyền làm.
 */

import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { isManager } from "../lib/session";

/** Khoá nhớ đã xem. Hậu tố phiên bản để lần sau đổi nội dung thì chạy lại. */
const KEY_SEEN = "nq_onboarding_v1";
/** Cờ "chạy tour ngay lần vào tới" — trang đăng ký đặt cờ này. */
const KEY_FORCE = "nq_onboarding_force";
/** Sự kiện để bất kỳ trang nào cũng mở lại tour được (trang /them dùng). */
export const TOUR_EVENT = "nq-tour-start";

export type TourStep = {
  /** Bộ chọn phần tử thật trên trang. Không tìm thấy thì bước vẫn chạy, chỉ không có vòng sáng. */
  target?: string;
  title: string;
  body: string;
  /** Câu hỏi gợi ý — bấm là sang /sop với câu đã điền. */
  hoi?: string[];
};

const BUOC_QUAN_LY: TourStep[] = [
  {
    target: '[data-tour="nav-hom-nay"]',
    title: "Hôm nay — nhìn một màn là biết quán đang thế nào",
    body: "Vùng này gộp số việc treo, số mục chờ bạn duyệt và cảnh báo tồn của ca đang chạy, nên bạn không phải đi từng trang để dò.",
    hoi: ["Mỗi ngày quản lý cần xem những gì trước khi mở quán?"],
  },
  {
    target: '[data-tour="nav-roster"]',
    title: "Lịch tuần — ai đứng ca nào",
    body: "Vùng này để ghim người vào ô ca rồi chuyển trạng thái tuần cho tới khi công bố; trước khi công bố thì nhân viên chưa thấy lịch.",
    hoi: ["Ca sáng cần bao nhiêu người?", "Ca tối cần người có kinh nghiệm bao lâu?"],
  },
  {
    target: '[data-tour="nav-inbox"]',
    title: "Hộp thư ràng buộc — chỗ bạn quyết, máy không quyết hộ",
    body: "Vùng này giữ những ràng buộc đâm nhau: hệ thống không tự chọn, nó đưa vào đây kèm tóm tắt và độ tin cậy để bạn duyệt hoặc từ chối.",
    hoi: ["Khi nào một đề nghị đổi ca được coi là đã đồng ý?"],
  },
  {
    target: '[data-tour="nav-cam-nang"]',
    title: "Cẩm nang — luật của quán lớn lên từ việc thật",
    body: "Vùng này giữ luật quán: chỉ vào hiệu lực khi có đủ lần sửa thật làm bằng chứng và qua vòng kiểm; luật nói về một người cụ thể bị loại thẳng.",
    hoi: ["Ly nhựa còn bao nhiêu thì phải nhập thêm?", "Ca sáng phải kiểm kê mấy mặt hàng?"],
  },
  {
    target: '[data-tour="nav-them"]',
    title: "Thêm — nơi mở lại hướng dẫn này",
    body: "Còn lại (sổ tiêu thụ, hao phí, chợ đổi ca, hỏi SOP) nằm trong Thêm. Muốn xem lại năm bước này thì bấm “Xem lại hướng dẫn” trong đó.",
    hoi: ["Hao phí ghi thế nào cho đúng?"],
  },
];

const BUOC_NHAN_VIEN: TourStep[] = [
  {
    target: '[data-tour="nav-hom-nay"]',
    title: "Hôm nay — vào ca thì mở vùng này trước",
    body: "Vùng này nói ngay hôm nay còn việc gì treo lại từ ca trước và lịch tuần đã công bố chưa.",
    hoi: ["Vào ca thì làm gì trước tiên?"],
  },
  {
    target: '[data-tour="nav-phieu"]',
    title: "Phiếu — một tay, một bước",
    body: "Vùng này chạy mở quán, đóng quán và bàn giao ca. Mỗi lần chỉ một bước hiện ra; bước nào cần ảnh hoặc số liệu thì phiếu tự hỏi.",
    hoi: ["Nhiệt độ tủ lạnh bao nhiêu là được?", "Mở quán gồm những bước nào?"],
  },
  {
    target: '[data-tour="nav-treo"]',
    title: "Việc treo — đừng nhớ bằng miệng",
    body: "Kẹt gì trong ca thì treo lại ngay trên phiếu. Ca sau đọc được, quản lý thấy được, và việc quá hạn nổi lên đầu danh sách.",
    hoi: ["Việc treo thì ai phải xử lý?"],
  },
  {
    target: '[data-tour="nav-toi"]',
    title: "Ca của tôi — nhả ca và nhận ca",
    body: "Vùng này xem ca bạn đang giữ trong tuần. Đi việc gấp thì nhả ca, ca đó sang chợ đổi ca; cần thêm giờ thì nhận ca đang trống.",
    hoi: ["Nhả ca rồi thì ai nhận?"],
  },
  {
    target: '[data-tour="nav-them"]',
    title: "Thêm — nơi mở lại hướng dẫn này",
    body: "Sổ tiêu thụ, hao phí, điểm danh QR và hỏi SOP nằm trong Thêm. Muốn xem lại năm bước này thì bấm “Xem lại hướng dẫn” trong đó.",
    hoi: ["Ghi sổ tiêu thụ để làm gì?"],
  },
];

function docSeen(): boolean {
  try {
    return localStorage.getItem(KEY_SEEN) === "1";
  } catch {
    // Trình duyệt chặn localStorage (chế độ riêng tư chặt): coi như đã xem để
    // không đập lớp phủ vào mặt người dùng mỗi lần đổi trang.
    return true;
  }
}

function ghiSeen(): void {
  try {
    localStorage.setItem(KEY_SEEN, "1");
  } catch {
    /* không nhớ được thì thôi, không làm gián đoạn việc của người dùng */
  }
}

/** Xoá dấu đã xem rồi phát sự kiện mở tour — dùng cho nút "Xem lại hướng dẫn". */
export function chayLaiTour(): void {
  try {
    localStorage.removeItem(KEY_SEEN);
  } catch {
    /* bỏ qua */
  }
  window.dispatchEvent(new Event(TOUR_EVENT));
}

/** Đặt cờ để tour tự chạy ở trang kế tiếp — trang /dang-ky gọi sau khi tạo tài khoản. */
export function datCoTourSauDangKy(): void {
  try {
    localStorage.removeItem(KEY_SEEN);
    localStorage.setItem(KEY_FORCE, "1");
  } catch {
    /* bỏ qua */
  }
}

type Rect = { top: number; left: number; width: number; height: number };

const KHOANG_HO = 6;

/**
 * Đo phần tử thật để vẽ vòng sáng.
 *
 * Quét tất cả phần tử khớp rồi lấy cái đầu tiên có kích thước thật: cùng một
 * `data-tour` xuất hiện ở cả thanh trên (màn lớn) và thanh dưới (màn nhỏ), và
 * bên bị ẩn có kích thước 0.
 */
function doVungSang(selector?: string): Rect | null {
  if (!selector) return null;
  for (const el of Array.from(document.querySelectorAll(selector))) {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) {
      return {
        top: r.top - KHOANG_HO,
        left: r.left - KHOANG_HO,
        width: r.width + KHOANG_HO * 2,
        height: r.height + KHOANG_HO * 2,
      };
    }
  }
  return null;
}

export function Tour({ active }: { active: boolean }) {
  const [open, setOpen] = useState(false);
  const [i, setI] = useState(0);
  const [manager, setManager] = useState(false);
  const [rect, setRect] = useState<Rect | null>(null);
  const boxRef = useRef<HTMLDivElement>(null);

  const steps = useMemo(() => (manager ? BUOC_QUAN_LY : BUOC_NHAN_VIEN), [manager]);
  const step = steps[Math.min(i, steps.length - 1)];

  const dong = useCallback(() => {
    setOpen(false);
    setI(0);
    ghiSeen();
  }, []);

  // Mở lần đầu: chỉ trên trang được phép (active), và chỉ khi chưa xem.
  useEffect(() => {
    if (!active) return;
    setManager(isManager());
    let forced = false;
    try {
      forced = localStorage.getItem(KEY_FORCE) === "1";
      if (forced) localStorage.removeItem(KEY_FORCE);
    } catch {
      forced = false;
    }
    if (forced || !docSeen()) {
      // Chờ một nhịp cho trang vẽ xong, nếu không vòng sáng đo vào chỗ trống.
      const t = window.setTimeout(() => setOpen(true), 350);
      return () => window.clearTimeout(t);
    }
    return;
  }, [active]);

  // Mở lại theo yêu cầu, từ bất kỳ trang nào.
  useEffect(() => {
    function onStart() {
      setManager(isManager());
      setI(0);
      setOpen(true);
    }
    window.addEventListener(TOUR_EVENT, onStart);
    return () => window.removeEventListener(TOUR_EVENT, onStart);
  }, []);

  // Đo lại vòng sáng khi đổi bước, khi cuộn, khi đổi kích thước.
  useEffect(() => {
    if (!open) return;
    const domin = () => setRect(doVungSang(step?.target));
    domin();
    window.addEventListener("resize", domin);
    window.addEventListener("scroll", domin, true);
    return () => {
      window.removeEventListener("resize", domin);
      window.removeEventListener("scroll", domin, true);
    };
  }, [open, step?.target]);

  // Bàn phím: Esc đóng, Tab quay vòng trong hộp thoại.
  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        dong();
        return;
      }
      if (e.key !== "Tab") return;
      const box = boxRef.current;
      if (!box) return;
      const focusables = Array.from(
        box.querySelectorAll<HTMLElement>("button:not([disabled]), a[href]"),
      );
      if (focusables.length === 0) return;
      const dau = focusables[0];
      const cuoi = focusables[focusables.length - 1];
      const now = document.activeElement;
      if (e.shiftKey && (now === dau || !box.contains(now))) {
        e.preventDefault();
        cuoi.focus();
      } else if (!e.shiftKey && (now === cuoi || !box.contains(now))) {
        e.preventDefault();
        dau.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, dong]);

  // Tiêu điểm vào hộp thoại khi mở và mỗi lần sang bước mới.
  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => {
      boxRef.current?.querySelector<HTMLElement>("button")?.focus();
    }, 40);
    return () => window.clearTimeout(t);
  }, [open, i]);

  if (!open || !step) return null;

  const cuoi = i >= steps.length - 1;
  const hoi = step.hoi ?? [];

  return (
    <>
      <div className="nq-tour-mask" />
      {rect ? (
        <div
          className="nq-tour-ring"
          style={{ top: rect.top, left: rect.left, width: rect.width, height: rect.height }}
          aria-hidden="true"
        />
      ) : null}
      <div
        className="nq-tour-box"
        role="dialog"
        aria-modal="true"
        aria-labelledby="nq-tour-title"
        aria-describedby="nq-tour-body"
        ref={boxRef}
      >
        <p className="nq-tour-step">
          Hướng dẫn · bước {i + 1} / {steps.length}
        </p>
        <h2 className="nq-tour-title" id="nq-tour-title">
          {step.title}
        </h2>
        <p className="nq-tour-body" id="nq-tour-body">
          {step.body}
        </p>
        {hoi.length > 0 ? (
          <div className="nq-tour-asks">
            <p className="nq-tour-asks-k">
              Hỏi cẩm nang quán — câu trả lời luôn kèm trích dẫn phiếu hoặc luật:
            </p>
            {hoi.map((c) => (
              <Link
                key={c}
                className="nq-ask"
                href={`/sop?q=${encodeURIComponent(c)}`}
                onClick={dong}
              >
                {c}
              </Link>
            ))}
          </div>
        ) : null}
        <div className="nq-tour-dots" aria-hidden="true">
          {steps.map((s, k) => (
            <span key={s.title} className="nq-tour-dot" data-on={k <= i ? "1" : "0"} />
          ))}
        </div>
        <div className="nq-tour-actions">
          <button
            type="button"
            className="nq-btn nq-btn-primary"
            onClick={() => (cuoi ? dong() : setI((v) => v + 1))}
          >
            {cuoi ? "Xong, vào việc" : "Tiếp"}
          </button>
          <button
            type="button"
            className="nq-btn nq-btn-ghost"
            disabled={i === 0}
            onClick={() => setI((v) => Math.max(0, v - 1))}
          >
            Quay lại
          </button>
          <button type="button" className="nq-btn nq-btn-ghost nq-tour-skip" onClick={dong}>
            Bỏ qua
          </button>
        </div>
      </div>
    </>
  );
}
