"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type MauPhieu = { ma: string; ten: string };

type BuocDef = {
  ma: string;
  ten: string;
  loai: "text" | "photo" | "confirm" | string;
  bat_buoc?: boolean;
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

const btnPrimary: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  justifyContent: "center",
  minHeight: 44,
  padding: "0.75rem 1.5rem",
  background: "var(--nq-accent)",
  color: "var(--nq-accent-ink)",
  border: "none",
  borderRadius: 4,
  fontWeight: 600,
  fontSize: "1rem",
  cursor: "pointer",
  width: "100%",
};

const btnSecondary: React.CSSProperties = {
  ...btnPrimary,
  background: "var(--nq-surface)",
  color: "var(--nq-ink)",
  border: "1px solid var(--nq-line)",
};

const btnDanger: React.CSSProperties = {
  ...btnPrimary,
  background: "var(--nq-danger, #c0392b)",
  color: "#fff",
};

export default function PhieuPage() {
  const [token, setToken] = useState("");
  const [mauList, setMauList] = useState<MauPhieu[]>([]);
  const [phieu, setPhieu] = useState<PhieuData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [treoText, setTreoText] = useState("");
  const [showTreo, setShowTreo] = useState(false);
  const [inputVal, setInputVal] = useState("");
  const [done, setDone] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    if (t) setToken(t);
  }, []);

  const authHeader = useCallback(
    () => ({ Authorization: `Bearer ${token}` }),
    [token],
  );

  // Load mau list
  useEffect(() => {
    fetch(`${API}/api/v1/phieu/mau`, { headers: authHeader() })
      .then(async (r) => {
        if (!r.ok) throw new Error("load_mau");
        return r.json() as Promise<MauPhieu[] | { items: MauPhieu[] }>;
      })
      .then((d) => setMauList(Array.isArray(d) ? d : d.items ?? []))
      .catch(() => setMauList([{ ma: "mo_quan", ten: "Mở quán" }]));
  }, [authHeader]);

  async function startPhieu(ma: string) {
    setBusy(true);
    setError(null);
    try {
      const checkin = await fetch(`${API}/api/v1/diem-danh`, {
        method: "POST",
        headers: authHeader(),
      });
      if (!checkin.ok) throw new Error("chua_diem_danh");
      const r = await fetch(`${API}/api/v1/phieu/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ mau: ma }),
      });
      if (!r.ok) throw new Error("start_failed");
      const data = (await r.json()) as PhieuData;
      setPhieu(data);
      setDone(false);
    } catch {
      setError("Không tạo được phiếu.");
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
      const r = await fetch(`${API}/api/v1/phieu/${phieu.id}/buoc`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error("buoc_failed");
      const updated = (await r.json()) as PhieuData;
      setPhieu(updated);
      setInputVal("");
      if (updated.trang_thai === "hoan_thanh") setDone(true);
    } catch {
      setError("Không hoàn thành được bước.");
    } finally {
      setBusy(false);
    }
  }

  async function sendPhoto(buocMa: string, dataUrl: string) {
    if (!phieu) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${API}/api/v1/phieu/${phieu.id}/minh-chung`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ buoc_ma: buocMa, data_url: dataUrl }),
      });
      if (!r.ok) throw new Error("photo_failed");
      const updated = (await r.json()) as PhieuData;
      setPhieu(updated);
      if (updated.trang_thai === "hoan_thanh") setDone(true);
      setBusy(false);
    } catch {
      setError("Không gửi được ảnh.");
      setBusy(false);
    }
  }

  async function handleTreo() {
    if (!phieu || !treoText.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const r = await fetch(`${API}/api/v1/phieu/${phieu.id}/treo`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ noi_dung: treoText }),
      });
      if (!r.ok) throw new Error("treo_failed");
      const updated = (await r.json()) as PhieuData;
      setPhieu(updated);
      setTreoText("");
      setShowTreo(false);
    } catch {
      setError("Không treo được phiếu.");
    } finally {
      setBusy(false);
    }
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>, buocMa: string) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setError("Cần ảnh thật, không nhận file khác.");
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const dataUrl = reader.result as string;
      sendPhoto(buocMa, dataUrl);
    };
    reader.readAsDataURL(file);
  }

  const currentBuocIndex = phieu
    ? phieu.buocs.findIndex((b) => !b.hoan_thanh)
    : -1;
  const currentBuoc = currentBuocIndex >= 0 ? phieu!.buocs[currentBuocIndex] : null;
  const completed = phieu ? phieu.buocs.filter((b) => b.hoan_thanh).length : 0;
  const total = phieu ? phieu.buocs.length : 0;

  if (!token) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-8 text-center bg-[var(--nq-bg)]">
        <h1 className="text-4xl font-black uppercase tracking-tighter text-[var(--nq-fg)] mb-4">Phiếu Ca</h1>
        <p className="text-xl text-[var(--nq-dim)] mb-8">Phiếu chạy theo phiên của bạn, nên cần đăng nhập trước.</p>
        <button 
          type="button"
          onClick={() => router.push("/login")}
          className="nq-ink-on-solid bg-[var(--nq-copper)] font-black uppercase tracking-widest py-4 px-8 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[10px_10px_0px_0px_var(--nq-copper-dim)]"
        >
          Đăng nhập để mở phiếu
        </button>
      </div>
    );
  }

  // Success screen
  if (done || phieu?.trang_thai === "hoan_thanh") {
    return (
      <div className="nq-page" style={{ textAlign: "center" }}>
        <p className="nq-kicker">Xong phiếu</p>
        <h1>Hoàn thành</h1>
        <p style={{ color: "var(--nq-ink-muted)", marginBottom: "2rem" }}>
          Phiếu <code style={{ fontFamily: "var(--nq-font-mono)" }}>{phieu?.id}</code> đã xong.
        </p>
        <button onClick={() => { setPhieu(null); setDone(false); }} style={btnPrimary}>
          Tạo phiếu mới
        </button>
      </div>
    );
  }

  return (
    <div className="relative" ref={containerRef}>
      <header className="mb-8 ops-animate-in">
        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter text-[var(--nq-copper)] mb-2">
          {phieu ? tenMau(phieu.mau) : "Mở Phiếu"}
        </h1>
        <p className="text-[var(--nq-dim)] font-mono text-sm">
          {phieu ? "Đang chạy phiếu ca" : "Chọn mẫu phiếu cần chạy"}
        </p>
      )}

      {/* No phieu: pick mau */}
      {!phieu && (
        <div>
          <p className="nq-muted" style={{ marginBottom: "1rem" }}>
            Chọn mẫu phiếu. Hệ thống điểm danh trước khi mở.
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {mauList.map((m) => (
              <button
                key={m.ma}
                disabled={busy}
                onClick={() => startPhieu(m.ma)}
                style={btnPrimary}
              >
                {m.ten || m.ma}
              </button>
            ))}
            {mauList.length === 0 && (
              <button disabled={busy} onClick={() => startPhieu("mo_quan")} style={btnPrimary}>
                Mở quán
              </button>
            )}
          </div>
        </div>
      )}

      {/* Active phieu */}
      {phieu && !done && (
        <div>
          {/* Progress bar */}
          <div style={{ marginBottom: "1.25rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "var(--nq-ink-muted)", marginBottom: "0.4rem" }}>
              <span>Bước {completed + 1} / {total}</span>
              <span style={{ fontFamily: "var(--nq-font-mono)" }}>{phieu.mau}</span>
            </div>
            <div style={{ background: "var(--nq-line)", borderRadius: 99, height: 6, overflow: "hidden" }}>
              <div style={{ background: "var(--nq-accent)", height: "100%", width: `${total > 0 ? (completed / total) * 100 : 0}%`, transition: "width 0.3s" }} />
            </div>
          </div>

          {/* Completed steps */}
          {phieu.buocs.filter((b) => b.hoan_thanh).length > 0 && (
            <div style={{ marginBottom: "1.25rem" }}>
              {phieu.buocs.filter((b) => b.hoan_thanh).map((b) => {
                const timing = phieu.signals?.timing_ms?.[b.ma];
                return (
                  <div key={b.ma} style={{ display: "flex", alignItems: "center", gap: "0.5rem", padding: "0.4rem 0", borderBottom: "1px solid var(--nq-line)", opacity: 0.6 }}>
                    <span style={{ color: "var(--nq-accent)", fontWeight: 700 }}>✓</span>
                    <span style={{ flex: 1, fontSize: "0.875rem" }}>{b.ten}</span>
                    {timing != null && (
                      <span style={{ fontFamily: "var(--nq-font-mono)", fontSize: "0.75rem", color: "var(--nq-ink-muted)" }}>
                        {(timing / 1000).toFixed(1)}s
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Current step card */}
          {currentBuoc && (
            <div style={{ background: "var(--nq-bg-elevated)", border: "1px solid var(--nq-line)", borderRadius: 8, padding: "1.25rem", marginBottom: "1.25rem" }}>
              <p style={{ fontSize: "0.75rem", fontFamily: "var(--nq-font-mono)", color: "var(--nq-ink-muted)", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                {currentBuoc.loai || "bước"}
              </p>
              <h2 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400, margin: "0 0 1rem", fontSize: "1.25rem" }}>
                {currentBuoc.ten}
              </h2>

              {/* Text input step */}
              {(currentBuoc.loai === "text" || currentBuoc.loai === "nhap") && (
                <div>
                  <input
                    type="text"
                    value={inputVal}
                    onChange={(e) => setInputVal(e.target.value)}
                    placeholder="Nhập giá trị…"
                    style={{ width: "100%", boxSizing: "border-box", background: "var(--nq-surface)", border: "1px solid var(--nq-line)", color: "var(--nq-ink)", padding: "0.6rem 0.75rem", borderRadius: 4, fontSize: "1rem", marginBottom: "0.75rem" }}
                  />
                </div>
              )}

              {/* Photo step */}
              {currentBuoc.loai === "photo" && (
                <div style={{ marginBottom: "0.75rem" }}>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    style={{ display: "none" }}
                    onChange={(e) => handleFileChange(e, currentBuoc.ma)}
                  />
                  <button
                    style={btnSecondary}
                    disabled={busy}
                    onClick={() => fileInputRef.current?.click()}
                  >
                    Chụp ảnh minh chứng
                  </button>
                </div>
              )}
            </div>
          )}

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
                  className="flex-1 nq-ink-on-solid bg-[var(--nq-red)] font-black uppercase tracking-widest py-4 border-2 border-[var(--nq-red)] hover:bg-transparent hover:text-[var(--nq-red)] transition-all disabled:opacity-50"
                >
                  Gửi việc treo
                </button>
                <button onClick={() => setShowTreo(false)} style={{ ...btnSecondary, flex: 1 }}>
                  Hủy
                </button>
              </div>
            </div>
          )}
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
                className="flex-1 nq-ink-on-solid bg-[var(--nq-copper)] font-black uppercase tracking-widest py-5 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-2px] hover:translate-y-[-2px] hover:shadow-[10px_10px_0px_0px_var(--nq-copper-dim)] disabled:opacity-50"
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
              {busy ? "Đang xử lý…" : "Xong bước này"}
            </button>
          )}
          <button
            onClick={() => setShowTreo((s) => !s)}
            style={{ ...btnSecondary, minWidth: 44, flex: currentBuoc.loai === "photo" ? 1 : "none", padding: "0.75rem" }}
            title="Để việc treo"
          >
            Treo
          </button>
        </div>
      ) : null}
    </div>
  );
}
