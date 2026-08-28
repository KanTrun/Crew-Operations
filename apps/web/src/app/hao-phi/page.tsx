"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, btnPrimary, Empty, Field, inputStyle, Kicker, Loading } from "../../ui/kit";

type Cluster = { cau?: string; thu?: string; n?: number };

export default function HaoPhiPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Cluster[]>([]);
  const [thu, setThu] = useState("T3");
  const [ghi, setGhi] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Cluster[] }>("/api/v1/waste")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không đọc được hao phí."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await apiSend("/api/v1/waste", { thu, ghi_chu: ghi });
      setGhi("");
      load();
    } catch {
      setError("Không ghi được ghi chú hao phí.");
    }
  }

  if (!token) return <AuthGate />;

  return (
<<<<<<< Updated upstream
    <div className="nq-page">
      <Kicker>Gom cụm từ ghi chú ca</Kicker>
      <h1>Hao phí</h1>
      {error ? <Alert>{error}</Alert> : null}
      <form onSubmit={onSubmit}>
        <Field label="Thứ">
          <input value={thu} onChange={(e) => setThu(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Ghi chú">
          <input value={ghi} onChange={(e) => setGhi(e.target.value)} style={inputStyle} />
        </Field>
        <button type="submit" style={btnPrimary}>
          Ghi chú
        </button>
      </form>
      <h2>Cụm</h2>
      {loading ? <Loading /> : null}
      {!loading && items.length === 0 ? <Empty>Chưa có ghi chú để gom cụm.</Empty> : null}
      <div className="nq-list">
        {items.map((it, i) => (
          <article key={i} className="nq-item">
            <p style={{ margin: 0, fontWeight: 600 }}>{it.cau ?? "Chưa đủ mẫu để gom cụm"}</p>
            <p className="nq-muted">
              {it.thu} · {it.n ?? 0} lần
            </p>
          </article>
        ))}
      </div>
=======
    <div className="relative" ref={containerRef}>
      <header className="mb-8 ops-animate-in">
        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter text-[var(--nq-copper)] mb-2">
          Hao Phí
        </h1>
        <p className="text-[var(--nq-dim)] font-mono text-sm max-w-2xl">
          Ghi chỗ hao trong ca bằng một câu. Ghi chú lặp lại gom thành cụm để quán thấy chỗ đang chảy máu.
        </p>
      </header>

      <div className="ops-animate-in mb-12">
        {items.length > 0 || ghiChu.length > 0 ? (
          <Summary
            cells={[
              { n: items.length, k: "cụm đã gom" },
              { n: ghiChu.length, k: "lần hao đã ghi" },
              { n: theoMatHang.length, k: "mặt hàng có hao" },
              { n: soLap, k: `mặt hàng hao từ ${NGUONG_LAP} lần`, tone: soLap > 0 ? "warn" : "ok" },
            ]}
          />
        ) : null}
      </div>

      {error ? <Alert className="ops-animate-in mb-8">{error}</Alert> : null}

      <div className="ops-animate-in bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-copper)] p-6 md:p-8 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] mb-12">
        <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)]">Ghi chú hao phí</h2>
        <form onSubmit={onSubmit}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            <Field label="Thứ trong tuần">
              <select 
                value={thu} 
                onChange={(e) => setThu(e.target.value)} 
                className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none appearance-none rounded-none"
              >
                {THU_HOP_LE.map((t) => (
                  <option key={t} value={t}>
                    {thuLabel(t)}
                  </option>
                ))}
              </select>
            </Field>
            <div className="md:col-span-2">
              <Field label="Hao ở đâu">
                <input
                  value={ghi}
                  onChange={(e) => setGhi(e.target.value)}
                  placeholder="Ví dụ: đổ bỏ 2 ly sữa vì pha sai"
                  className="w-full bg-[var(--nq-surface)] border-2 border-[var(--nq-dim)] p-4 text-[var(--nq-fg)] font-mono focus:border-[var(--nq-copper)] focus:outline-none"
                />
              </Field>
            </div>
          </div>
          <Hint className="mb-6">Viết như nói với đồng nghiệp. Không cần số tiền.</Hint>
          <button 
            type="submit" 
            disabled={busy}
            className="w-full md:w-auto nq-ink-on-solid bg-[var(--nq-copper)] font-black uppercase tracking-widest py-4 px-8 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all disabled:opacity-50"
          >
            {busy ? "Đang ghi..." : "Ghi hao phí"}
          </button>
        </form>
      </div>

      <div className="ops-animate-in mb-12">
        <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)] flex items-center gap-4">
          Hao phí gom theo mặt hàng
          <span className="text-sm nq-ink-on-solid bg-[var(--nq-copper)] px-3 py-1 rounded-full">{theoMatHang.length}</span>
        </h2>
        {loading ? <Loading skeleton="table" rows={5}>Đang gom hao phí theo mặt hàng…</Loading> : null}
        {!loading && theoMatHang.length === 0 ? (
          <Empty title="Chưa có dữ liệu">Chưa có lần hao nào được ghi kèm mặt hàng và số lượng.</Empty>
        ) : null}
        {!loading && theoMatHang.length > 0 ? (
          <div className="overflow-x-auto bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] shadow-[8px_8px_0px_0px_var(--nq-copper-dim)]">
            <table className="w-full text-left border-collapse">
              <caption className="sr-only">Hao phí theo mặt hàng: tổng lượng, đơn vị, số lần và nguyên nhân hay gặp</caption>
              <thead>
                <tr className="border-b-2 border-[var(--nq-dim)] bg-[var(--nq-surface)]">
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)]">Mặt hàng</th>
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)] text-right">Tổng hao</th>
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)]">Đơn vị</th>
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)] text-right">Số lần</th>
                  <th className="p-4 font-black uppercase tracking-widest text-[var(--nq-dim)]">Nguyên nhân hay gặp</th>
                </tr>
              </thead>
              <tbody>
                {theoMatHang.map((x) => (
                  <tr 
                    key={`${x.mat_hang}-${x.don_vi}`} 
                    className={`border-b border-[var(--nq-dim)]/30 hover:bg-[var(--nq-surface)] transition-colors ${x.lan >= NGUONG_LAP ? "border-l-4 border-l-[var(--nq-warn)]" : ""}`}
                  >
                    <td className="p-4 font-bold text-[var(--nq-fg)]">{matHangLabel(x.mat_hang)}</td>
                    <td className="p-4 font-mono text-right text-[var(--nq-copper)]">{safeNumber(x.tong, 1)}</td>
                    <td className="p-4 text-[var(--nq-dim)]">{safeText(x.don_vi, "—")}</td>
                    <td className="p-4 font-mono text-right">{x.lan}</td>
                    <td className="p-4 text-[var(--nq-dim)]">
                      {x.nguyen_nhan}
                      {x.lan >= NGUONG_LAP ? (
                        <span className="ml-2 inline-block"><StatusChip tone="warn">Lặp lại</StatusChip></span>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="p-4 border-t-2 border-[var(--nq-dim)] bg-[var(--nq-surface)] text-sm font-mono text-[var(--nq-dim)]">
              Vạch vàng đầu dòng là mặt hàng hao từ {NGUONG_LAP} lần trở lên — đủ ngưỡng để hệ thống gom cụm và đề xuất luật. Đơn vị khác nhau giữ dòng riêng, không cộng lẫn.
            </div>
          </div>
        ) : null}
      </div>

      <div className="ops-animate-in mb-12">
        <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)] flex items-center gap-4">
          Cụm đã gom theo thứ
          <span className="text-sm nq-ink-on-solid bg-[var(--nq-copper)] px-3 py-1 rounded-full">{items.length}</span>
        </h2>
        {loading ? <Loading skeleton="rows" rows={4}>Đang gom cụm hao phí…</Loading> : null}
        {!loading && !error && items.length === 0 ? (
          <Empty title="Chưa đủ dữ liệu">Chưa đủ ghi chú để gom cụm. Ghi thêm vài lần trong ca.</Empty>
        ) : null}
        {!loading && cumTheoThu.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {cumTheoThu.map((it, i) => (
              <div 
                key={`${safeText(it.thu, "?")}-${i}`}
                className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-4px] hover:translate-y-[-4px] hover:shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex justify-between items-start mb-4">
                    <span className="text-sm font-mono text-[var(--nq-dim)] border-2 border-[var(--nq-dim)] px-2 py-1">{thuLabel(it.thu)}</span>
                    {(it.n ?? 0) >= NGUONG_LAP ? <StatusChip tone="warn">Đủ ngưỡng</StatusChip> : null}
                  </div>
                  <h3 className="text-xl font-bold mb-4 text-[var(--nq-fg)]">{safeText(it.cau, "Chưa đủ mẫu để gom thành cụm")}</h3>
                  <p className="text-sm text-[var(--nq-dim)] font-mono mb-4">Gom từ ghi chú của nhiều ca</p>
                  <p className="text-2xl font-black text-[var(--nq-copper)]">
                    {typeof it.n === "number" ? it.n : 0} <span className="text-sm text-[var(--nq-dim)] font-mono uppercase tracking-widest">lần</span>
                  </p>
                </div>
              </div>
            ))}
          </div>
        ) : null}
      </div>

      {!loading && ghiChu.length > 0 ? (
        <div className="ops-animate-in mb-12">
          <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)] flex items-center gap-4">
            Lần hao gần đây
            <span className="text-sm nq-ink-on-solid bg-[var(--nq-copper)] px-3 py-1 rounded-full">{Math.min(ghiChu.length, 8)}</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {ghiChu.slice(0, 8).map((g, i) => (
              <div 
                key={safeText(g.id, String(i))}
                className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 hover:border-[var(--nq-copper)] transition-colors"
              >
                <div className="flex justify-between items-start mb-2">
                  <h3 className="text-lg font-bold text-[var(--nq-fg)]">{safeText(g.ghi_chu, "Ghi chú chưa có nội dung")}</h3>
                  <span className="font-mono text-xl font-black text-[var(--nq-copper)] whitespace-nowrap ml-4">
                    {safeNumber(g.so_luong, 0)} <span className="text-sm text-[var(--nq-dim)]">{safeText(g.don_vi, "")}</span>
                  </span>
                </div>
                <p className="text-sm text-[var(--nq-dim)] font-mono">
                  {thuLabel(g.thu)} {khungLabel(g.khung).toLowerCase()} · {nguyenNhanLabel(g.nguyen_nhan)}
                </p>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div className="fixed bottom-0 left-0 w-full p-4 bg-[var(--nq-bg)]/80 backdrop-blur-md border-t-2 border-[var(--nq-dim)] z-50">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row gap-4 items-center justify-between">
          <p className="text-sm font-mono text-[var(--nq-dim)] hidden md:block">Hao phí lặp lại là bằng chứng cho luật nguyên nhân hao hụt.</p>
          <div className="flex gap-4 w-full sm:w-auto">
            <BtnLink href="/tieu-thu" className="flex-1 sm:flex-none nq-ink-on-solid bg-[var(--nq-copper)] font-black uppercase tracking-widest py-3 px-6 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all text-center">
              Ghi sổ tiêu thụ
            </BtnLink>
            <button 
              type="button"
              onClick={load}
              className="flex-1 sm:flex-none bg-transparent text-[var(--nq-fg)] font-black uppercase tracking-widest py-3 px-6 border-2 border-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)] transition-all"
            >
              Tải lại
            </button>
          </div>
        </div>
      </div>

      <Toasts toasts={toasts} onDismiss={dismiss} />
>>>>>>> Stashed changes
    </div>
  );
}
