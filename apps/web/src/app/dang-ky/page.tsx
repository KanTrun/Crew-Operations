"use client";

/**
 * Đăng ký tài khoản quán.
 *
 * Ba quy tắc, kiểm ngay trên máy người dùng trước khi gửi (máy chủ kiểm lại lần
 * nữa — client chỉ để người dùng biết sớm, không phải để thay máy chủ):
 *  - tên đăng nhập: chữ thường không dấu, số, gạch dưới; 3–24 ký tự
 *  - mật khẩu: từ 8 ký tự
 *  - tên hiển thị: 2–60 ký tự
 *
 * Bốn mã lỗi 409 của máy chủ được dịch thành câu tiếng Việt gắn đúng ô cần sửa
 * (xem `dangKyLoi` trong `src/lib/present.ts`). Mã thô không bao giờ ra UI, và
 * mật khẩu không bao giờ được in lại — chỉ có đồng hồ đo độ mạnh.
 */

import { FormEvent, useMemo, useState, useEffect, useRef } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, apiSend } from "../../lib/api";
import { dangKyLoi, viError } from "../../lib/present";
import { Alert, Btn, Field, Hint } from "../../ui/kit";
import { datCoTourSauDangKy } from "../../ui/tour";

type RegisterOut = { token: string; role: string; display_name: string; nv_id: string };

const TEN_RE = /^[a-z0-9_]{3,24}$/;
const MK_TOI_THIEU = 8;

function loiTen(v: string): string | null {
  const t = v.trim();
  if (!t) return "Chưa nhập tên đăng nhập.";
  if (t.length < 3) return "Tên đăng nhập cần ít nhất 3 ký tự.";
  if (t.length > 24) return "Tên đăng nhập dài quá, tối đa 24 ký tự.";
  if (!TEN_RE.test(t)) {
    return "Tên đăng nhập chỉ nhận chữ thường không dấu, số và dấu gạch dưới. Ví dụ: minh_pha_che.";
  }
  return null;
}

function loiMatKhau(v: string): string | null {
  if (!v) return "Chưa nhập mật khẩu.";
  if (v.length < MK_TOI_THIEU) return `Mật khẩu cần từ ${MK_TOI_THIEU} ký tự. Còn thiếu ${MK_TOI_THIEU - v.length}.`;
  return null;
}

function loiTenHienThi(v: string): string | null {
  const t = v.trim();
  if (t.length < 2) return "Tên hiển thị cần ít nhất 2 ký tự.";
  if (t.length > 60) return "Tên hiển thị dài quá, tối đa 60 ký tự.";
  return null;
}

/**
 * Đo độ mạnh mật khẩu: 0–4.
 *
 * Tính bằng bốn dấu hiệu độc lập (đủ dài, có chữ hoa lẫn thường, có số, có ký tự
 * khác) chứ không gọi thư viện — thêm dependency cho một thanh bốn ô là không đáng.
 * Không log, không gửi đi đâu; chỉ đếm trong bộ nhớ của trang.
 */
function doManh(v: string): { diem: number; nhan: string } {
  if (!v) return { diem: 0, nhan: "Chưa nhập mật khẩu." };
  let d = 0;
  if (v.length >= MK_TOI_THIEU) d += 1;
  if (v.length >= 12) d += 1;
  if (/[a-z]/.test(v) && /[A-Z]/.test(v)) d += 1;
  if (/\d/.test(v) && /[^\w\s]/.test(v)) d += 1;
  const diem = Math.min(4, d);
  const nhan =
    diem <= 1
      ? "Yếu — thêm chữ hoa, số hoặc ký tự đặc biệt."
      : diem === 2
        ? "Tạm được — dài thêm vài ký tự nữa thì chắc hơn."
        : diem === 3
          ? "Khá — dùng được cho tài khoản quán."
          : "Mạnh.";
  return { diem, nhan };
}

export default function DangKyPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [daNhap, setDaNhap] = useState({ u: false, p: false, d: false });
  const [loiO, setLoiO] = useState<{ username?: string; password?: string; display_name?: string }>({});
  const [loiChung, setLoiChung] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const containerRef = useRef<HTMLDivElement>(null);

  const manh = useMemo(() => doManh(password), [password]);

  const kiemU = loiTen(username);
  const kiemP = loiMatKhau(password);
  const kiemD = loiTenHienThi(displayName);
  const hopLe = !kiemU && !kiemP && !kiemD;

  // Gợi ý dưới ô: hiện ngay khi người dùng đã chạm vào ô đó, hoặc khi máy chủ trả lỗi.
  const hienU = loiO.username ?? (daNhap.u ? kiemU ?? undefined : undefined);
  const hienP = loiO.password ?? (daNhap.p ? kiemP ?? undefined : undefined);
  const hienD = loiO.display_name ?? (daNhap.d ? kiemD ?? undefined : undefined);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoiChung(null);
    setLoiO({});
    setDaNhap({ u: true, p: true, d: true });
    if (!hopLe) return;
    setBusy(true);
    try {
      const data = await apiSend<RegisterOut>("/api/v1/auth/register", {
        username: username.trim(),
        password,
        display_name: displayName.trim(),
      });
      sessionStorage.setItem("nq_token", data.token);
      sessionStorage.setItem("nq_role", data.role);
      sessionStorage.setItem("nq_name", data.display_name);
      sessionStorage.setItem("nq_nv", data.nv_id);
      // Người vừa tạo tài khoản là người chưa biết quán chạy thế nào: cho tour
      // tự mở ở bảng Hôm nay ngay sau khi vào.
      datCoTourSauDangKy();
      router.push("/hom-nay");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const { o, cau } = dangKyLoi(err.detail);
        if (o === "chung") setLoiChung(cau);
        else setLoiO({ [o]: cau });
      } else {
        setLoiChung(viError(err, { doing: "tạo được tài khoản mới" }));
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden" ref={containerRef}>
      {/* Abstract background elements */}
      <div className="absolute top-[-10%] right-[-10%] w-[50vw] h-[50vw] rounded-full bg-[var(--nq-copper-glow)] blur-[100px] opacity-50 mix-blend-screen" />
      <div className="absolute bottom-[-10%] left-[-10%] w-[40vw] h-[40vw] rounded-full bg-[var(--nq-green-dim)] blur-[120px] opacity-20 mix-blend-screen" />
      
      <form onSubmit={onSubmit} className="nq-login-card relative z-10 w-full max-w-[480px] bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-8 md:p-12 shadow-[-16px_16px_0px_0px_var(--nq-copper-dim)] transition-transform hover:translate-x-[4px] hover:translate-y-[-4px] hover:shadow-[-20px_20px_0px_0px_var(--nq-copper-dim)]" noValidate>
        <div className="nq-login-body flex flex-col gap-6">
          <div className="nq-kinetic-text flex gap-2 overflow-hidden text-[var(--nq-copper)] font-bold uppercase tracking-widest text-sm mb-2">
            <span>Gia</span>
            <span>Nhập</span>
            <span>·</span>
            <span>Đội</span>
            <span>Ngũ</span>
          </div>
          
          <h1 className="text-5xl md:text-6xl font-black uppercase leading-none tracking-tighter mb-4 text-[var(--nq-fg)] mix-blend-difference">
            Đăng<br/>Ký
          </h1>
          
          <p className="text-[var(--nq-dim)] text-sm mb-4 border-r-4 border-[var(--nq-copper)] pr-4 text-right">
            Tài khoản tạo ở đây luôn là <strong>nhân viên</strong>. Muốn thêm quyền quản lý thì nhờ chủ quán nâng vai — trang này không tự cấp quyền quản lý.
          </p>

          <div className="flex flex-col gap-5">
            <Field label="Tên đăng nhập">
              <input
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value.toLowerCase());
                  setLoiO((v) => ({ ...v, username: undefined }));
                }}
                onBlur={() => setDaNhap((v) => ({ ...v, u: true }))}
                autoComplete="username"
                aria-invalid={hienU ? true : undefined}
                aria-describedby="nq-goi-y-ten"
                className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none transition-colors"
              />
            </Field>
            {hienU ? (
              <p className="text-[var(--nq-red)] text-sm font-bold" id="nq-goi-y-ten" role="alert">
                {hienU}
              </p>
            ) : (
              <p className="text-[var(--nq-dim)] text-xs font-mono" id="nq-goi-y-ten">
                Chữ thường không dấu, số và dấu gạch dưới; 3–24 ký tự.
              </p>
            )}

            <Field label="Mật khẩu">
              <input
                type="password"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  setLoiO((v) => ({ ...v, password: undefined }));
                }}
                onBlur={() => setDaNhap((v) => ({ ...v, p: true }))}
                autoComplete="new-password"
                aria-invalid={hienP ? true : undefined}
                aria-describedby="nq-do-manh"
                className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none transition-colors"
              />
            </Field>
            
            <div className="mt-2 flex gap-1 h-2" aria-hidden="true">
              {[1, 2, 3, 4].map((k) => (
                <div
                  key={k}
                  className={`flex-1 transition-colors duration-300 ${
                    k <= manh.diem
                      ? manh.diem <= 1
                        ? "bg-[var(--nq-red)]"
                        : manh.diem === 2
                          ? "bg-[var(--nq-copper)]"
                          : "bg-[var(--nq-green)]"
                      : "bg-[var(--nq-surface)]"
                  }`}
                />
              ))}
            </div>
            <p className="text-[var(--nq-dim)] text-xs font-mono" id="nq-do-manh" aria-live="polite">
              Độ mạnh: {manh.nhan}
            </p>
            {hienP ? (
              <p className="text-[var(--nq-red)] text-sm font-bold" role="alert">
                {hienP}
              </p>
            ) : null}

            <Field label="Tên hiển thị">
              <input
                value={displayName}
                onChange={(e) => {
                  setDisplayName(e.target.value);
                  setLoiO((v) => ({ ...v, display_name: undefined }));
                }}
                onBlur={() => setDaNhap((v) => ({ ...v, d: true }))}
                autoComplete="name"
                aria-invalid={hienD ? true : undefined}
                aria-describedby="nq-goi-y-hien-thi"
                className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none transition-colors"
              />
            </Field>
            {hienD ? (
              <p className="text-[var(--nq-red)] text-sm font-bold" id="nq-goi-y-hien-thi" role="alert">
                {hienD}
              </p>
            ) : (
              <p className="text-[var(--nq-dim)] text-xs font-mono" id="nq-goi-y-hien-thi">
                Tên đồng nghiệp thấy trên lịch ca, 2–60 ký tự.
              </p>
            )}
          </div>

          {loiChung ? (
            <div className="animate-in fade-in slide-in-from-bottom-2">
              <Alert>{loiChung}</Alert>
            </div>
          ) : null}

          <button
            type="submit"
            disabled={busy || !hopLe}
            className="w-full mt-4 bg-[var(--nq-copper)] text-[#0e0c0a] font-black uppercase tracking-widest py-5 px-6 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {busy ? "Đang tạo…" : "Tạo tài khoản"}
          </button>

          <div className="mt-8 pt-6 border-t-2 border-dashed border-[var(--nq-dim)] flex flex-col gap-2 text-sm text-[var(--nq-dim)] text-right">
            <p>Đã có tài khoản? <Link href="/login" className="text-[var(--nq-copper)] hover:underline underline-offset-4 decoration-2">Vào hệ thống</Link></p>
          </div>
        </div>
      </form>
    </main>
  );
}
