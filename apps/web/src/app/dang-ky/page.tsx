"use client";

/**
 * Đăng ký tài khoản quán — form gọn ngang trên desktop.
 */

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, apiSend } from "../../lib/api";
import { dangKyLoi, viError } from "../../lib/present";
import { Alert, Btn, Field } from "../../ui/kit";

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

  const manh = useMemo(() => doManh(password), [password]);
  const kiemU = loiTen(username);
  const kiemP = loiMatKhau(password);
  const kiemD = loiTenHienThi(displayName);
  const hopLe = !kiemU && !kiemP && !kiemD;
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
    <main className="relative flex min-h-dvh items-center justify-center overflow-hidden p-4 md:p-8">
      <div className="pointer-events-none absolute top-[-10%] right-[-10%] h-[40vw] w-[40vw] rounded-full bg-[var(--nq-copper-glow)] opacity-40 blur-[100px] mix-blend-screen" />
      <div className="pointer-events-none absolute bottom-[-10%] left-[-10%] h-[35vw] w-[35vw] rounded-full bg-[var(--nq-green-dim)] opacity-25 blur-[120px] mix-blend-screen" />

      <form
        onSubmit={onSubmit}
        noValidate
        className="nq-login-card relative z-10 grid w-full max-w-5xl grid-cols-1 overflow-hidden border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] shadow-[-12px_12px_0px_0px_var(--nq-copper-dim)] md:grid-cols-2"
      >
        <aside className="flex flex-col justify-between border-b-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-6 md:border-r-2 md:border-b-0 md:p-8">
          <p className="font-black tracking-tighter text-2xl text-[var(--nq-copper)]">NHỊP QUÁN</p>
          <div className="mt-8 md:mt-0">
            <p className="mb-2 font-mono text-xs tracking-widest text-[var(--nq-copper)] uppercase">
              Gia nhập · đội ngũ
            </p>
            <h1 className="text-4xl font-black tracking-tighter text-[var(--nq-fg)] uppercase md:text-5xl">
              Đăng ký
            </h1>
            <p className="mt-4 max-w-sm text-sm text-[var(--nq-dim)]">
              Tài khoản tạo ở đây luôn là <strong className="text-[var(--nq-fg)]">nhân viên</strong>.
              Muốn thêm quyền quản lý thì nhờ chủ quán nâng vai.
            </p>
          </div>
          <p className="mt-8 hidden text-xs font-mono text-[var(--nq-dim)] md:block">
            NHỊP QUÁN · Digital System
          </p>
        </aside>

        <div className="flex flex-col gap-3 p-6 md:gap-4 md:p-8">
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
              className="w-full border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-3 font-mono text-[var(--nq-fg)] transition-colors focus:border-[var(--nq-copper)] focus:outline-none"
            />
          </Field>
          {hienU ? (
            <p className="text-sm font-bold text-[var(--nq-red)]" id="nq-goi-y-ten" role="alert">
              {hienU}
            </p>
          ) : (
            <p className="text-xs font-mono text-[var(--nq-dim)]" id="nq-goi-y-ten">
              Chữ thường không dấu, số và _ ; 3–24 ký tự.
            </p>
          )}

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <div>
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
                  className="w-full border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-3 font-mono text-[var(--nq-fg)] transition-colors focus:border-[var(--nq-copper)] focus:outline-none"
                />
              </Field>
              <div className="mt-2 flex h-1.5 gap-1" aria-hidden="true">
                {[1, 2, 3, 4].map((k) => (
                  <div
                    key={k}
                    className={`flex-1 transition-colors ${
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
              <p className="mt-1 text-xs font-mono text-[var(--nq-dim)]" id="nq-do-manh" aria-live="polite">
                {manh.nhan}
              </p>
              {hienP ? (
                <p className="text-sm font-bold text-[var(--nq-red)]" role="alert">
                  {hienP}
                </p>
              ) : null}
            </div>

            <div>
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
                  className="w-full border-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] p-3 font-mono text-[var(--nq-fg)] transition-colors focus:border-[var(--nq-copper)] focus:outline-none"
                />
              </Field>
              {hienD ? (
                <p className="text-sm font-bold text-[var(--nq-red)]" id="nq-goi-y-hien-thi" role="alert">
                  {hienD}
                </p>
              ) : (
                <p className="mt-1 text-xs font-mono text-[var(--nq-dim)]" id="nq-goi-y-hien-thi">
                  Tên trên lịch ca, 2–60 ký tự.
                </p>
              )}
            </div>
          </div>

          {loiChung ? <Alert>{loiChung}</Alert> : null}

          <Btn
            type="submit"
            busy={busy}
            disabled={!hopLe}
            busyLabel="Đang tạo…"
            className="nq-ink-on-solid mt-1 w-full border-2 border-[var(--nq-copper)] bg-[var(--nq-copper)] py-3.5 font-black tracking-widest uppercase transition-all hover:bg-transparent hover:text-[var(--nq-copper)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            Tạo tài khoản
          </Btn>

          <p className="border-t-2 border-dashed border-[var(--nq-dim)] pt-3 text-sm text-[var(--nq-dim)]">
            Đã có tài khoản?{" "}
            <Link href="/login" className="text-[var(--nq-copper)] underline-offset-4 hover:underline">
              Vào hệ thống
            </Link>
          </p>
        </div>
      </form>
    </main>
  );
}
