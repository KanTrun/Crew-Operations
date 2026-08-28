"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { safeNumber, safeText, viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  Hint,
  inputStyle,
  Loading,
  Notice,
  OpsCard,
  PageHeader,
  StatusChip,
} from "../../ui/kit";

type Row = { id: string; hang: string; so_luong: number; don_vi: string; duoi_nguong?: boolean };

export default function TieuThuPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [items, setItems] = useState<Row[]>([]);
  const [hang, setHang] = useState("sữa tươi");
  const [so, setSo] = useState("3");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<{ items: Row[] }>("/api/v1/tieu-thu")
      .then((d) => {
        setItems((d.items ?? []).filter((x) => x && typeof x.id === "string"));
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "đọc được sổ tiêu thụ" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    const soLuong = Number(so.replace(",", "."));
    if (!hang.trim()) {
      setError("Ghi tên hàng trước khi lưu kiểm kê.");
      return;
    }
    if (!Number.isFinite(soLuong) || soLuong < 0) {
      setError("Số lượng phải là một số không âm, ví dụ 2 hoặc 2.5.");
      return;
    }
    setBusy(true);
    try {
      await apiSend("/api/v1/tieu-thu", { hang: hang.trim(), so_luong: soLuong, don_vi: "khay" });
      setMsg("Đã ghi lần kiểm kê.");
      load();
    } catch (e) {
      setError(
        viError(e, {
          doing: "ghi được lần kiểm kê",
          forbidden: "Chỉ quản lý hoặc chủ quán ghi được số lượng vào sổ.",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="relative" ref={containerRef}>
      <header className="mb-8 ops-animate-in">
        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter text-[var(--nq-copper)] mb-2">
          Sổ Tiêu Thụ
        </h1>
        <p className="text-[var(--nq-dim)] font-mono text-sm max-w-2xl">
          Ghi số còn lại sau ca. Hệ thống chỉ đếm, không tính tiền; mặt hàng dưới ngưỡng thành cảnh báo tồn trên bảng Hôm nay.
        </p>
      </header>

      <div className="ops-animate-in mb-12">
        {items.length > 0 ? (
          <Summary
            cells={[
              { n: items.length, k: "lần kiểm kê" },
              { n: soDuoiNguong, k: "mặt hàng dưới ngưỡng", tone: soDuoiNguong > 0 ? "warn" : "ok" },
              { n: soDonVi, k: "đơn vị đo khác nhau" },
            ]}
          />
        ) : null}
      </div>

      {error ? <Alert className="ops-animate-in mb-8">{error}</Alert> : null}

      <div className="ops-animate-in mb-12">
        {manager ? (
          <div className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-copper)] p-6 md:p-8 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]">
            <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)]">Lần kiểm kê mới</h2>
            <form onSubmit={onSubmit}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                <Field label="Tên hàng">
                  <input 
                    value={hang} 
                    onChange={(e) => setHang(e.target.value)} 
                    className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none" 
                  />
                </Field>
                <Field label="Số khay còn lại">
                  <input 
                    value={so} 
                    onChange={(e) => setSo(e.target.value)} 
                    inputMode="decimal" 
                    className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none" 
                  />
                </Field>
              </div>
              <Hint className="mb-6">Đếm theo khay. Dưới 2 khay thì bảng Hôm nay hiện cảnh báo tồn.</Hint>
              <button 
                type="submit" 
                disabled={busy}
                className="w-full md:w-auto nq-ink-on-solid bg-[var(--nq-copper)] font-black uppercase tracking-widest py-4 px-8 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all disabled:opacity-50"
              >
                {busy ? "Đang ghi..." : "Ghi lần kiểm kê"}
              </button>
            </form>
          </div>
        ) : (
          <Notice>Bạn xem được sổ. Quản lý hoặc chủ quán mới ghi số lượng.</Notice>
        )}
      </div>

      <div className="ops-animate-in mb-12">
        <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)] flex items-center gap-4">
          Những lần đã kiểm kê
          <span className="text-sm nq-ink-on-solid bg-[var(--nq-copper)] px-3 py-1 rounded-full">{items.length}</span>
        </h2>
        {loading ? <Loading skeleton="table" rows={5}>Đang đọc sổ tiêu thụ…</Loading> : null}
        {!loading && !error && items.length === 0 ? (
          <Empty title="Chưa có dữ liệu">Chưa có lần kiểm kê nào trong sổ.</Empty>
        ) : null}
        {!loading && items.length > 0 ? (
          <div className="overflow-x-auto bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]">
            <table className="w-full text-left border-collapse">
              <caption className="sr-only">Sổ tiêu thụ: mặt hàng, số lượng còn lại, đơn vị và thời điểm ghi</caption>
              <thead>
                <tr className="border-b-2 border-[var(--nq-dim)] bg-[var(--nq-surface)]">
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)]">Mặt hàng</th>
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)] text-right">Số lượng</th>
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)]">Đơn vị</th>
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)] text-right">Ghi lúc</th>
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)]">Tình trạng</th>
                </tr>
              </thead>
              <tbody>
                {items.map((it) => (
                  <tr 
                    key={it.id} 
                    className={`border-b border-[var(--nq-dim)]/30 hover:bg-[var(--nq-surface)] transition-colors ${it.duoi_nguong ? "border-l-4 border-l-[var(--nq-warn)]" : ""}`}
                  >
                    <td className="p-4 font-bold text-[var(--nq-fg)]">{matHangLabel(safeText(it.ten, safeText(it.hang, "")))}</td>
                    <td className="p-4 font-mono text-right text-[var(--nq-copper)]">{safeNumber(it.so_luong, 1)}</td>
                    <td className="p-4 text-[var(--nq-dim)]">{safeText(it.don_vi, "khay")}</td>
                    <td className="p-4 font-mono text-right">{formatLuc(it.luc)}</td>
                    <td className="p-4">
                      {it.duoi_nguong ? (
                        <StatusChip tone="warn">Dưới ngưỡng</StatusChip>
                      ) : (
                        <StatusChip tone="ok">Đủ dùng</StatusChip>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="p-4 border-t-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] text-sm font-mono text-[var(--nq-dim)]">
              Cột số căn phải để so được theo cột. Vạch vàng đầu dòng là mặt hàng đã xuống dưới ngưỡng quán đặt.
            </div>
          </div>
        ) : null}
      </div>

      <div className="fixed bottom-0 left-0 w-full p-4 bg-[var(--nq-bg)]/80 backdrop-blur-md border-t-2 border-[var(--nq-dim)] z-50">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row gap-4 items-center justify-between">
          <p className="text-sm font-mono text-[var(--nq-dim)] hidden md:block">Số kiểm kê là bằng chứng cho luật ngưỡng tồn.</p>
          <div className="flex gap-4 w-full sm:w-auto">
            <BtnLink href="/hao-phi" className="flex-1 sm:flex-none nq-ink-on-solid bg-[var(--nq-copper)] font-black uppercase tracking-widest py-3 px-6 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all text-center">
              Ghi hao phí trong ca
            </BtnLink>
            <button 
              type="button"
              onClick={load}
              className="flex-1 sm:flex-none bg-transparent text-[var(--nq-fg)] font-black uppercase tracking-widest py-3 px-6 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all"
            >
              Tải lại sổ
            </button>
          </div>
        </div>
      </div>

      <Toasts toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
