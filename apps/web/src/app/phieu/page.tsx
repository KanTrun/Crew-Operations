"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import gsap from "gsap";
import { apiGet, apiSend } from "../../lib/api";
import { ganVoiLabel, loaiBuocLabel, moKhiLabel, safeText, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  Btn,
  BtnLink,
  Empty,
  Field,
  FixedBottomBar,
  InlineActions,
  inputStyle,
  Loading,
  OpsCard,
  PickCard,
  ProgressBar,
  StepDone,
  Summary,
  TechnicalDrawer,
  textareaStyle,
} from "../../ui/kit";

type MauPhieu = {
  ma: string;
  ten: string;
  so_buoc?: number;
  gan_voi?: string;
  mo_khi?: string;
  han_hoan_thanh_phut?: number;
  buoc?: Array<{ ma?: string; ten?: string; minh_chung?: string }>;
};

type BuocState = {
  ma: string;
  ten: string;
  loai: string;
  hoan_thanh: boolean;
  gia_tri?: string;
  timing_ms?: number;
};

type PhieuData = {
  id: string;
  mau: string;
  trang_thai: "dang_lam" | "hoan_thanh" | "treo" | string;
  buoc_hien_tai?: string;
  buocs: BuocState[];
  signals?: { timing_ms?: Record<string, number> };
};

const MAU_MO_QUAN: MauPhieu = { ma: "mo_quan", ten: "Mở quán", so_buoc: 20 };

/** Số bước: lấy `so_buoc` máy chủ trả, không có thì đếm mảng bước. */
function soBuoc(m: MauPhieu): number {
  if (typeof m.so_buoc === "number" && m.so_buoc > 0) return m.so_buoc;
  return (m.buoc ?? []).length;
}

/**
 * Một câu về loại minh chứng mẫu này đòi.
 *
 * Đếm từ mảng bước thật, không viết sẵn: mẫu đổi thì câu này đổi theo. Người
 * chuẩn bị mở quán cần biết trước "có bước cần ảnh" để không phải quay lại lấy
 * điện thoại giữa lúc đang dở tay.
 */
function moTaMinhChung(m: MauPhieu): string {
  const buoc = m.buoc ?? [];
  const anh = buoc.filter((b) => b.minh_chung === "anh").length;
  const so = buoc.filter((b) => b.minh_chung === "so").length;
  const kiemKe = buoc.filter((b) => b.minh_chung === "kiem_ke").length;
  const phan: string[] = [];
  if (anh > 0) phan.push(`${anh} bước cần ảnh`);
  if (so > 0) phan.push(`${so} bước cần nhập số`);
  if (kiemKe > 0) phan.push(`${kiemKe} bước kiểm kê mặt hàng`);
  return phan.length > 0 ? ` Trong đó ${phan.join(", ")}.` : "";
}

export default function PhieuPage() {
  const router = useRouter();
  const [token, setToken] = useState("");
  const [mauList, setMauList] = useState<MauPhieu[]>([]);
  const [mauLoading, setMauLoading] = useState(true);
  const [phieu, setPhieu] = useState<PhieuData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [treoText, setTreoText] = useState("");
  const [showTreo, setShowTreo] = useState(false);
  const [inputVal, setInputVal] = useState("");
  const [done, setDone] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setToken(getToken());
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      gsap.fromTo(
        ".ops-animate-in",
        { y: 30, opacity: 0 },
        { y: 0, opacity: 1, stagger: 0.1, duration: 0.5, ease: "power2.out" }
      );
    }
  }, [mauList, phieu]);

  const loadMau = useCallback(() => {
    if (!getToken()) return;
    setMauLoading(true);
    apiGet<MauPhieu[] | { items: MauPhieu[] }>("/api/v1/phieu/mau")
      .then((d) => {
        const list = Array.isArray(d) ? d : d.items ?? [];
        setMauList(list.length > 0 ? list : [MAU_MO_QUAN]);
      })
      .catch(() => setMauList([MAU_MO_QUAN]))
      .finally(() => setMauLoading(false));
  }, []);

  useEffect(() => {
    if (token) loadMau();
  }, [token, loadMau]);

  const tenMau = useCallback(
    (ma?: string) => {
      const found = mauList.find((m) => m.ma === ma);
      if (found) return safeText(found.ten, "Phiếu ca");
      return ma === MAU_MO_QUAN.ma ? MAU_MO_QUAN.ten : "Phiếu ca";
    },
    [mauList],
  );

  async function startPhieu(ma: string) {
    setBusy(true);
    setError(null);
    try {
      await apiSend("/api/v1/diem-danh");
    } catch (e) {
      setError(
        viError(e, {
          doing: "điểm danh để mở phiếu",
          forbidden: "Bạn chưa có ca hôm nay nên chưa điểm danh được. Nhờ quản lý gán ca rồi mở lại phiếu.",
        }),
      );
      setBusy(false);
      return;
    }
    try {
      const data = await apiSend<PhieuData>("/api/v1/phieu/start", { mau: ma });
      setPhieu(data);
      setDone(false);
    } catch (e) {
      setError(viError(e, { doing: "mở được phiếu mới" }));
    } finally {
      setBusy(false);
    }
  }

  async function completeBuoc(ma: string, gia_tri?: string) {
    if (!phieu) return;
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { ma };
      if (gia_tri !== undefined) body.gia_tri = gia_tri;
      const updated = await apiSend<PhieuData>(`/api/v1/phieu/${phieu.id}/buoc`, body);
      setPhieu(updated);
      setInputVal("");
      if (updated.trang_thai === "hoan_thanh") setDone(true);
    } catch (e) {
      setError(viError(e, { doing: "đóng được bước này" }));
    } finally {
      setBusy(false);
    }
  }

  async function sendPhoto(buocMa: string, dataUrl: string) {
    if (!phieu) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiSend<PhieuData>(`/api/v1/phieu/${phieu.id}/minh-chung`, {
        buoc_ma: buocMa,
        data_url: dataUrl,
      });
      setPhieu(updated);
      if (updated.trang_thai === "hoan_thanh") setDone(true);
    } catch (e) {
      setError(viError(e, { doing: "gửi được ảnh minh chứng" }));
    } finally {
      setBusy(false);
    }
  }

  async function handleTreo() {
    if (!phieu || !treoText.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await apiSend<PhieuData>(`/api/v1/phieu/${phieu.id}/treo`, {
        noi_dung: treoText,
      });
      setPhieu(updated);
      setTreoText("");
      setShowTreo(false);
    } catch (e) {
      setError(viError(e, { doing: "treo được phiếu này" }));
    } finally {
      setBusy(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>, buocMa: string) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Cần một tấm ảnh. Chụp lại bằng camera hoặc chọn ảnh trong máy.");
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => setError("Không đọc được ảnh vừa chọn. Chụp lại một tấm khác.");
    reader.onload = () => sendPhoto(buocMa, String(reader.result ?? ""));
    reader.readAsDataURL(file);
  }

  const tongBuoc = mauList.reduce((s, m) => s + soBuoc(m), 0);
  const buocs = phieu?.buocs ?? [];
  const currentBuocIndex = buocs.findIndex((b) => !b.hoan_thanh);
  const currentBuoc = currentBuocIndex >= 0 ? buocs[currentBuocIndex] : null;
  const completed = buocs.filter((b) => b.hoan_thanh).length;
  const total = buocs.length;
  const activeRun = Boolean(phieu && !done && currentBuoc);

  if (!token) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-8 text-center bg-[var(--nq-bg)]">
        <h1 className="text-4xl font-black uppercase tracking-tighter text-[var(--nq-fg)] mb-4">Phiếu Ca</h1>
        <p className="text-xl text-[var(--nq-dim)] mb-8">Phiếu chạy theo phiên của bạn, nên cần đăng nhập trước.</p>
        <button 
          type="button"
          onClick={() => router.push("/login")}
          className="bg-[var(--nq-copper)] text-[#0e0c0a] font-black uppercase tracking-widest py-4 px-8 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[10px_10px_0px_0px_var(--nq-copper-dim)]"
        >
          Đăng nhập để mở phiếu
        </button>
      </div>
    );
  }

  if (done || phieu?.trang_thai === "hoan_thanh") {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-8 text-center bg-[var(--nq-bg)] ops-animate-in">
        <h2 className="text-6xl font-black uppercase tracking-tighter text-[var(--nq-green)] mb-6">Hoàn Thành</h2>
        <p className="text-xl text-[var(--nq-dim)] mb-12 max-w-md">
          Đã đóng đủ {total} bước của {tenMau(phieu?.mau)}. Việc treo (nếu có) đã sang trang Việc treo.
        </p>
        <button
          type="button"
          onClick={() => {
            setPhieu(null);
            setDone(false);
          }}
          className="bg-transparent text-[var(--nq-fg)] font-black uppercase tracking-widest py-5 px-12 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all"
        >
          Mở phiếu tiếp theo
        </button>
      </div>
    );
  }

  return (
    <main className="min-h-screen p-4 md:p-8 relative" ref={containerRef}>
      <header className="mb-8 ops-animate-in">
        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter text-[var(--nq-copper)] mb-2">
          {phieu ? tenMau(phieu.mau) : "Mở Phiếu"}
        </h1>
        <p className="text-[var(--nq-dim)] font-mono text-sm">
          {phieu ? "Đang chạy phiếu ca" : "Chọn mẫu phiếu cần chạy"}
        </p>
      </header>

      {error ? <Alert className="ops-animate-in mb-8">{error}</Alert> : null}

      {!phieu && (
        <div className="ops-animate-in">
          {mauLoading ? (
            <Loading skeleton="card" rows={3}>
              Đang lấy danh sách mẫu phiếu…
            </Loading>
          ) : null}
          {!mauLoading && mauList.length === 0 ? (
            <Empty>Quán chưa cài mẫu phiếu nào. Nhờ quản lý thêm mẫu trong cẩm nang.</Empty>
          ) : null}
          {!mauLoading && mauList.length > 0 ? (
            <>
              <Summary
                cells={[
                  { n: mauList.length, k: "mẫu phiếu quán đang dùng" },
                  { n: tongBuoc, k: "bước tất cả" },
                ]}
                className="mb-8"
              />
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {mauList.map((m) => (
                  <div 
                    key={m.ma} 
                    className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-4px] hover:translate-y-[-4px] hover:shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] transition-all cursor-pointer flex flex-col justify-between"
                    onClick={() => startPhieu(m.ma)}
                  >
                    <div>
                      <h3 className="text-2xl font-black uppercase mb-4 text-[var(--nq-fg)]">{safeText(m.ten, "Phiếu ca")}</h3>
                      <div className="text-sm text-[var(--nq-dim)] font-mono space-y-2 mb-6">
                        <p className="text-[var(--nq-copper)] font-bold">{soBuoc(m)} bước</p>
                        <p>{ganVoiLabel(m.gan_voi)}</p>
                        <p>{moKhiLabel(m.mo_khi)}</p>
                        {m.han_hoan_thanh_phut && <p>Hạn: {m.han_hoan_thanh_phut} phút</p>}
                      </div>
                    </div>
                    <button className="w-full bg-transparent border-2 border-[var(--nq-copper)] text-[var(--nq-copper)] font-bold uppercase tracking-widest py-3 hover:bg-[var(--nq-copper)] hover:text-[#0e0c0a] transition-colors">
                      {busy ? "Đang mở…" : "Bắt đầu"}
                    </button>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </div>
      )}

      {phieu && !done && (
        <div className="ops-animate-in max-w-2xl mx-auto pb-32">
          <div className="mb-8">
            <div className="flex justify-between font-mono text-sm mb-2 text-[var(--nq-dim)] uppercase tracking-widest">
              <span>Bước {Math.min(completed + 1, Math.max(total, 1))} / {total}</span>
              <span className="text-[var(--nq-copper)]">{tenMau(phieu.mau)}</span>
            </div>
            <ProgressBar value={completed} max={total} />
          </div>

          <div className="space-y-4 mb-8">
            {buocs
              .filter((b) => b.hoan_thanh)
              .map((b) => (
                <StepDone
                  key={b.ma}
                  label={safeText(b.ten, "Bước đã xong")}
                  timingMs={phieu.signals?.timing_ms?.[b.ma]}
                />
              ))}
          </div>

          {currentBuoc ? (
            <div className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-copper)] p-6 md:p-8 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] mb-8">
              <h2 className="text-2xl font-black uppercase mb-2 text-[var(--nq-fg)]">{safeText(currentBuoc.ten, "Bước tiếp theo")}</h2>
              <p className="text-[var(--nq-dim)] font-mono text-sm mb-6 uppercase tracking-widest">{loaiBuocLabel(currentBuoc.loai)}</p>

              {(currentBuoc.loai === "text" || currentBuoc.loai === "nhap") && (
                <Field label="Số liệu đọc được">
                  <input
                    type="text"
                    value={inputVal}
                    onChange={(e) => setInputVal(e.target.value)}
                    placeholder="Ví dụ: 4 độ C"
                    className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none text-xl"
                  />
                </Field>
              )}
              {currentBuoc.loai === "photo" && (
                <div className="mb-6">
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    style={{ display: "none" }}
                    onChange={(e) => handleFileChange(e, currentBuoc.ma)}
                  />
                  <button 
                    type="button"
                    disabled={busy} 
                    onClick={() => fileInputRef.current?.click()}
                    className="w-full bg-[var(--nq-surface)] border-2 border-dashed border-[var(--nq-copper)] text-[var(--nq-copper)] font-bold uppercase tracking-widest py-8 hover:bg-[var(--nq-copper-glow)] transition-colors disabled:opacity-50"
                  >
                    Chụp ảnh minh chứng
                  </button>
                </div>
              )}
            </div>
          ) : null}

          {showTreo ? (
            <div className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-red)] p-6 md:p-8 shadow-[8px_8px_0px_0px_var(--nq-red-dim)] mb-8">
              <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-red)]">Để lại việc treo</h2>
              <Field label="Kẹt ở đâu">
                <textarea
                  value={treoText}
                  onChange={(e) => setTreoText(e.target.value)}
                  placeholder="Ví dụ: máy pha không lên áp, đã tắt nguồn chờ thợ"
                  rows={3}
                  className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-red)] focus:outline-none min-h-[100px]"
                />
              </Field>
              <div className="flex flex-col sm:flex-row gap-4 mt-8">
                <button 
                  type="button"
                  disabled={busy || !treoText.trim()} 
                  onClick={handleTreo}
                  className="flex-1 bg-[var(--nq-red)] text-[#0e0c0a] font-black uppercase tracking-widest py-4 border-2 border-[var(--nq-red)] hover:bg-transparent hover:text-[var(--nq-red)] transition-all disabled:opacity-50"
                >
                  Gửi việc treo
                </button>
                <button 
                  type="button"
                  onClick={() => setShowTreo(false)}
                  className="sm:w-auto bg-transparent text-[var(--nq-dim)] font-bold uppercase tracking-widest py-4 px-6 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-fg)] hover:text-[var(--nq-fg)] transition-all"
                >
                  Quay lại phiếu
                </button>
              </div>
            </div>
          ) : null}

          <TechnicalDrawer
            lines={[`Mã lần chạy: ${safeText(phieu.id)}`, `Mã mẫu: ${safeText(phieu.mau)}`]}
          />
        </div>
      )}

      {activeRun && currentBuoc ? (
        <div className="fixed bottom-0 left-0 w-full p-4 bg-[var(--nq-bg)]/80 backdrop-blur-md border-t-2 border-[var(--nq-dim)] z-50">
          <div className="max-w-2xl mx-auto flex gap-4">
            {currentBuoc.loai !== "photo" ? (
              <button
                type="button"
                disabled={busy}
                onClick={() =>
                  completeBuoc(
                    currentBuoc.ma,
                    currentBuoc.loai === "text" || currentBuoc.loai === "nhap" ? inputVal || undefined : undefined,
                  )
                }
                className="flex-1 bg-[var(--nq-copper)] text-[#0e0c0a] font-black uppercase tracking-widest py-5 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[10px_10px_0px_0px_var(--nq-copper-dim)] disabled:opacity-50"
              >
                {busy ? "Đang xử lý…" : "Xong bước này"}
              </button>
            ) : null}
            <button 
              type="button"
              title="Để lại việc treo" 
              onClick={() => setShowTreo((s) => !s)}
              className="bg-transparent text-[var(--nq-dim)] font-bold uppercase tracking-widest py-5 px-6 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-red)] hover:text-[var(--nq-red)] transition-all bg-[var(--nq-surface)]"
            >
              Treo lại
            </button>
          </div>
        </div>
      ) : null}
    </main>
  );
}
