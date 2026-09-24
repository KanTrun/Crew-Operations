"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, apiGet, apiSend } from "../lib/api";
import { getToken, setSession } from "../lib/session";
import { Logo } from "../ui/Logo";
import { Icon } from "../ui/icons";

type LoginOut = { token: string; role: string; display_name: string; nv_id: string };
type DemoAccount = { username: string; label: string; role: string };
/** Hình dạng tối thiểu của `/api/v1/hom-nay` mà mặt tiền cần — chỉ để đọc số. */
type TodayFigures = {
  so_ca?: number;
  so_nhan_vien?: number;
  so_treo?: number;
  so_luat?: number;
};

const DEMO_ACCOUNTS: DemoAccount[] = [
  { username: "lan", label: "Lan Nguyễn", role: "Quản lý" },
  { username: "hung", label: "Hùng Trần", role: "Chủ quán" },
  { username: "nam", label: "Nam Lý", role: "Quản lý" },
  { username: "minh", label: "Minh Phạm", role: "Nhân viên" },
  { username: "chi", label: "Chi Vũ", role: "Nhân viên" },
  { username: "dung", label: "Dũng Đặng", role: "Nhân viên" },
  { username: "an", label: "An Lê", role: "Nhân viên" },
  { username: "bao", label: "Bảo Hoàng", role: "Nhân viên" },
  { username: "yen", label: "Yến Kiều", role: "Nhân viên" },
  { username: "thao", label: "Thảo Dương", role: "Nhân viên" },
  { username: "quan", label: "Quân Lương", role: "Nhân viên" },
  { username: "linh", label: "Linh Ngô", role: "Nhân viên" },
  { username: "my", label: "Mỹ Tạ", role: "Nhân viên" },
  { username: "khoa", label: "Khoa Đỗ", role: "Nhân viên" },
  { username: "oanh", label: "Oanh Phan", role: "Nhân viên" },
  { username: "phuc", label: "Phúc Trịnh", role: "Nhân viên" },
  { username: "son", label: "Sơn Hà", role: "Nhân viên" },
  { username: "rosa", label: "Rosa Võ", role: "Nhân viên" },
  { username: "uyen", label: "Uyên Cao", role: "Nhân viên" },
];

/** Số liệu mặt tiền — đọc từ API công khai, không bịa. */
type Figures = { ca: number; nhan_vien: number; viec_mo: number; luat: number };

/** Năng lực vận hành, xếp theo tần suất dùng thật trong ca. */
const CAPABILITIES: { icon: Parameters<typeof Icon>[0]["name"]; name: string; copy: string }[] = [
  {
    icon: "roster",
    name: "Xếp ca & lịch tuần",
    copy: "Ma trận 7 ngày × 3 khung giờ, thấy ngay ca nào thiếu người. Nhân viên xác nhận lịch của mình trên điện thoại.",
  },
  {
    icon: "clock",
    name: "Chấm công & công bằng",
    copy: "Điểm danh QR tại quầy, đối chiếu giờ vào/ra với ca đã duyệt. Chợ đổi ca để nhân viên tự hoán đổi trong khuôn khổ.",
  },
  {
    icon: "coffee",
    name: "Quầy bar & bếp",
    copy: "Màn hình gọi món, điều phối phiếu bar/bếp, cảnh báo món hết. Hao phí và tồn kho cập nhật theo từng ca.",
  },
  {
    icon: "bot",
    name: "Họp ca & SOP sống",
    copy: "Bóc băng ghi âm cuộc họp, đối chiếu với SOP, đề xuất cập nhật cẩm nang. Quản lý duyệt trước khi áp dụng.",
  },
];

export default function HomePage() {
  const router = useRouter();
  const [hasSession, setHasSession] = useState(false);
  const [quickLogin, setQuickLogin] = useState<string | null>(null);
  const [quickLoginError, setQuickLoginError] = useState<string | null>(null);
  const [figures, setFigures] = useState<Figures | null>(null);

  useEffect(() => {
    if (getToken()) {
      setHasSession(true);
    }
  }, []);

  // Nhịp vào của từng chương khi cuộn tới. Cố ý KHÔNG ẩn nội dung khi chưa có
  // JS: chỉ những chương được observer gắn cờ mới bắt đầu ở trạng thái mờ, và
  // nếu IntersectionObserver không có thì mọi chương hiện ngay.
  useEffect(() => {
    const nodes = Array.from(document.querySelectorAll<HTMLElement>(".nq-chapter"));
    if (nodes.length === 0) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced || typeof IntersectionObserver === "undefined") return;
    nodes.forEach((n) => n.setAttribute("data-enter", "pending"));
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.setAttribute("data-enter", "in");
            io.unobserve(e.target);
          }
        });
      },
      // `rootMargin` đáy chỉ -6%: chương cuối trang cao hơn vùng cuộn còn lại,
      // nên biên âm lớn (từng là -12%) khiến nó không bao giờ đủ "đang thấy" và
      // kẹt ở trạng thái `pending` — nội dung mờ vĩnh viễn. Ngưỡng 0.05 thay vì
      // số lớn cũng vì lý do đó: chỉ cần một phần nhỏ chương lọt vào khung.
      { rootMargin: "0px 0px -6% 0px", threshold: 0.05 },
    );
    nodes.forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, []);

  // Số liệu thật của quán làm điểm nhấn thị giác — thay cho hạt sáng trang trí.
  // Không đăng nhập được thì mặt tiền vẫn đứng vững ở nhánh không có số.
  // Phải gọi qua `apiGet` (đi tới API base + kèm token), KHÔNG dùng `fetch`
  // đường dẫn tương đối: `/api/v1/hom-nay` là route của máy chủ API, không phải
  // của Next, nên gọi tương đối sẽ 404 và khối số liệu không bao giờ hiện.
  useEffect(() => {
    let alive = true;
    apiGet<TodayFigures>("/api/v1/hom-nay")
      .then((d) => {
        if (!alive) return;
        setFigures({
          ca: Number(d?.so_ca ?? 0),
          nhan_vien: Number(d?.so_nhan_vien ?? 0),
          viec_mo: Number(d?.so_treo ?? 0),
          luat: Number(d?.so_luat ?? 0),
        });
      })
      .catch(() => {
        /* Chưa đăng nhập / API chưa lên: mặt tiền vẫn đứng ở nhánh không có số. */
      });
    return () => {
      alive = false;
    };
  }, []);

  async function loginAs(account: DemoAccount) {
    setQuickLogin(account.username);
    setQuickLoginError(null);
    try {
      const data = await apiSend<LoginOut>("/api/v1/auth/login", {
        username: account.username,
        password: "nhipquan",
      });
      setSession(data.token, data.role, data.display_name, data.nv_id);
      router.push("/hom-nay");
    } catch (error) {
      setQuickLoginError(error instanceof ApiError && error.status === 401 ? "Tài khoản demo chưa sẵn sàng." : "Không thể vào hệ thống lúc này.");
    } finally {
      setQuickLogin(null);
    }
  }


  return (
    <main className="nq-landing">
      <div className="relative z-10 mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-16 lg:px-8">
        {/* ── Chương 1: mở đầu ──
            Headline 2 dòng + một hành động. Số liệu thật của quán nằm ngay dưới,
            là điểm nhấn thị giác chính — thay cho khối "9 Agent" cố định trước
            đây, vốn không đo được gì và không đổi theo ca. */}
        <section className="nq-chapter nq-chapter--opening">
          <Logo />
          {/* Năm vạch nhịp: "nhịp quán" nhìn thấy được. Đây là khoảnh khắc
              chuyển động mạnh duy nhất của trang. */}
          <div className="nq-pulse" aria-hidden="true">
            <span /><span /><span /><span /><span />
          </div>
          <h1 className="nq-chapter__title">
            Quán chạy theo <em>nhịp</em>, không theo bảng tính.
          </h1>
          <p className="nq-chapter__lead">
            Xếp ca, chấm công, quầy bar và họp ca trong một chỗ. Việc gì tới hạn thì nổi lên trước,
            việc gì đã xong thì im lặng.
          </p>
          <div className="flex w-full flex-col justify-center gap-3 sm:flex-row">
            <Link href={hasSession ? "/hom-nay" : "/login"} className="nq-cta nq-cta--primary nq-cta--lg">
              {hasSession ? "Tiếp tục phiên làm việc" : "Vào ca"}
            </Link>
            <Link href="/huong-dan" className="nq-cta nq-cta--ghost nq-cta--lg">
              Bản đồ hệ thống
            </Link>
          </div>

          {/* Số thật của quán. Không có phiên đăng nhập thì không hiện khối này
              — thà thiếu còn hơn bịa số. */}
          {figures ? (
            <div className="nq-figures">
              <div className="nq-figure" data-tone={figures.viec_mo > 0 ? "warn" : undefined}>
                <span className="nq-figure__value">{figures.viec_mo}</span>
                <span className="nq-figure__label">Việc đang mở</span>
              </div>
              <div className="nq-figure">
                <span className="nq-figure__value">{figures.nhan_vien}</span>
                <span className="nq-figure__label">Nhân sự trong ca</span>
              </div>
              <div className="nq-figure">
                <span className="nq-figure__value">{figures.luat}</span>
                <span className="nq-figure__label">Luật cẩm nang</span>
              </div>
            </div>
          ) : null}
        </section>

        {/* ── Chương 2: hệ thống làm được gì ── */}
        <section className="nq-chapter">
          <h2 className="nq-chapter__title">
            Bốn việc <em>chiếm hết</em> thời gian của quản lý.
          </h2>
          <p className="nq-chapter__lead">
            Mỗi việc đều đang chạy thật trong hệ thống, không phải mô tả trên giấy.
          </p>
          <div className="nq-capability">
            {CAPABILITIES.map((c) => (
              <div key={c.name} className="nq-capability__row">
                <p className="nq-capability__name">
                  <span className="nq-capability__icon">
                    <Icon name={c.icon} size={15} />
                  </span>
                  {c.name}
                </p>
                <p className="nq-capability__copy">{c.copy}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Chương 3: vào hệ thống ── */}
        <section className="nq-chapter">
          <h2 className="nq-chapter__title">
            Bắt đầu từ <em>ca hôm nay</em>.
          </h2>
          <p className="nq-chapter__lead">
            Mỗi vai trò thấy một màn hình khác nhau. Nhân viên chỉ thấy ca của mình; quản lý thấy
            toàn bộ lịch tuần và hàng chờ duyệt.
          </p>
          <div className="flex flex-col gap-3 sm:flex-row">
            <Link href="/login" className="nq-cta nq-cta--primary">
              Đăng nhập
            </Link>
            <Link href="/dang-ky" className="nq-cta nq-cta--ghost">
              Tạo tài khoản nhân viên
            </Link>
          </div>

          {/* Tài khoản demo của buổi trình diễn: tiện ích, không phải nội dung
              chính — gấp vào ngăn kéo, mặc định đóng. */}
          <details className="nq-demo">
            <summary>
              <span>Tài khoản trình diễn ({DEMO_ACCOUNTS.length})</span>
              <Icon name="users" size={16} />
            </summary>
            <div className="nq-demo__grid">
              {DEMO_ACCOUNTS.map((account) => (
                <button
                  key={account.username}
                  type="button"
                  onClick={() => loginAs(account)}
                  disabled={quickLogin !== null}
                  className="nq-demo__item"
                >
                  {quickLogin === account.username ? <span className="nq-demo__pending" aria-hidden="true" /> : null}
                  <span>
                    <span className="nq-demo__name">
                      {quickLogin === account.username ? "Đang vào…" : account.label}
                    </span>
                    <span className="nq-demo__role">{account.role}</span>
                  </span>
                </button>
              ))}
            </div>
          </details>
          {quickLoginError ? (
            <p role="alert" className="nq-muted" style={{ margin: 0 }}>
              {quickLoginError}
            </p>
          ) : null}
        </section>

        {/* FOOTER */}
        <footer className="nq-landing-footer">
          <div>NHỊP QUÁN (Crew Operations) • Single Store Release</div>
          <div className="flex items-center gap-4">
            <button
              type="button"
              onClick={() => router.push("/login")}
              className="nq-landing-footer-link"
            >
              Đăng nhập tài khoản khác
            </button>
            <button
              type="button"
              onClick={() => router.push("/cuoc-hop")}
              className="nq-landing-footer-link"
            >
              AG-Meeting
            </button>
            <button
              type="button"
              onClick={() => router.push("/lich-tuan")}
              className="nq-landing-footer-link"
            >
              Lịch tuần
            </button>
          </div>
        </footer>
      </div>
    </main>
  );
}

