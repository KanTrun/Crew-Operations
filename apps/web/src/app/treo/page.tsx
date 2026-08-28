"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, btnGhost, btnPrimary, Empty, Kicker, Loading } from "../../ui/kit";

type ViecTreo = {
  id: string;
  phieu_id?: string;
  mau?: string;
  noi_dung: string;
  created_at?: string;
  nhan_vien?: string;
};

type GhiNhan = {
  id?: string;
  loai?: string;
  truoc?: unknown;
  sau?: unknown;
  ai?: string;
  luc?: string;
};

export default function TreoPage() {
  const [token, setToken] = useState("");
  const [treo, setTreo] = useState<ViecTreo[]>([]);
  const [sua, setSua] = useState<GhiNhan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"treo" | "sua">("treo");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    Promise.all([
      apiGet<{ items: ViecTreo[] }>("/api/v1/viec-treo")
        .then((d) => setTreo(d.items ?? []))
        .catch(() => setError("Không tải được việc treo.")),
      apiGet<{ items: GhiNhan[] }>("/api/v1/ghi-nhan-sua")
        .then((d) => setSua(d.items ?? []))
        .catch(() => undefined),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!token) return <AuthGate />;

  return (
    <div className="relative" ref={containerRef}>
      <header className="mb-8 ops-animate-in">
        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter text-[var(--nq-copper)] mb-2">
          Việc Treo
        </h1>
        <p className="text-[var(--nq-dim)] font-mono text-sm max-w-2xl">
          Việc kẹt lại từ phiếu ca, kèm sổ những lần quán sửa lịch — để không ai phải nhớ bằng miệng.
        </p>
      </header>

      <div className="ops-animate-in mb-12">
        {tab === "treo" && treo.length > 0 ? (
          <Summary
            cells={[
              { n: treo.length, k: "việc treo" },
              { n: dem("qua_han"), k: "quá hạn", tone: "danger" },
              { n: dem("dang_cho"), k: "đang chờ", tone: "warn" },
              { n: dem("xong"), k: "xong", tone: "ok" },
            ]}
          />
        ) : null}
        {tab === "sua" && sua.length > 0 ? (
          <Summary
            cells={[
              { n: sua.length, k: "lần sửa lịch" },
              { n: nhomSua.length, k: "kiểu thao tác" },
              { n: nhomSua[0] ? nhomSua[0][1].length : 0, k: `lần ${ghiNhanLabel(nhomSua[0]?.[0]).toLowerCase()}` },
            ]}
          />
        ) : null}
      </div>

      <div className="ops-animate-in mb-8 flex border-b-2 border-[var(--nq-dim)]">
        <button 
          className={`flex-1 py-4 font-black uppercase tracking-widest transition-colors ${tab === "treo" ? "text-[var(--nq-copper)] border-b-4 border-[var(--nq-copper)]" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
          onClick={() => setTab("treo")}
        >
          Việc treo ({treo.length})
        </button>
        <button onClick={() => setTab("sua")} style={tab === "sua" ? btnPrimary : btnGhost}>
          Ghi nhận sửa ({sua.length})
        </button>
      </p>
      {tab === "treo" && (
        <div className="ops-animate-in space-y-8">
          {error ? <Alert>{error}</Alert> : null}
          {loading ? <Loading skeleton="rows" rows={4} groups={3}>Đang tải việc treo…</Loading> : null}
          {!loading && !error && treo.length === 0 ? (
            <Empty title="Không có việc treo">Ca chạy sạch, không còn việc nào bị kẹt lại.</Empty>
          ) : null}
          {!loading &&
            nhomTreo.map(([tt, list]) => (
              <div key={tt} className="mb-12">
                <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)] flex items-center gap-4">
                  {NHOM[tt]?.ten ?? treoLabel(tt)}
                  <span className="text-sm nq-ink-on-solid bg-[var(--nq-copper)] px-3 py-1 rounded-full">{list.length}</span>
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {list.map((v) => (
                    <div 
                      key={v.id}
                      className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-4px] hover:translate-y-[-4px] hover:shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] transition-all flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex justify-between items-start mb-4">
                          <StatusChip tone={treoTone(v.trang_thai)}>{treoLabel(v.trang_thai)}</StatusChip>
                          <span className="text-sm font-mono text-[var(--nq-dim)] border-2 border-[var(--nq-dim)] px-2 py-1">Hạn {formatNgay(v.han)}</span>
                        </div>
                        <h3 className="text-xl font-bold mb-4 text-[var(--nq-fg)]">{safeText(v.noi_dung, "Việc treo chưa ghi nội dung")}</h3>
                        <div className="text-sm text-[var(--nq-dim)] font-mono space-y-1">
                          <p>{nvLabel(v.nhan_vien)} để lại từ phiếu {mauPhieuLabel(v.mau).toLowerCase()}</p>
                          <p>
                            {v.thu ? `${thuLabel(v.thu)}` : ""}
                            {v.khung ? ` · ${khungLabel(v.khung).toLowerCase()}` : ""}
                          </p>
                          <p>{v.created_at ? `Ghi lúc ${formatLuc(v.created_at)}` : ""}</p>
                          <p className="text-[var(--nq-copper)] mt-2">
                            Giao cho {nvLabel(v.nguoi_nhan)} {v.ca_sau_da_nhan ? "(Đã nhận)" : "(Chưa nhận)"}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          {!loading && nhomTreo.length > 0 ? (
            <p className="text-sm font-mono text-[var(--nq-dim)] border-l-4 border-[var(--nq-copper)] pl-4 mt-8">
              {NHOM.qua_han.giai_thich} {NHOM.dang_cho.giai_thich}
            </p>
          ) : null}
        </div>
      )}
      {tab === "sua" && (
        <div className="nq-list">
          {loading ? <Loading /> : null}
          {!loading && sua.length === 0 ? (
            <Empty>Chưa có lần sửa. Nhả/nhận ca hoặc ghim ô sẽ ghi vào đây.</Empty>
          ) : null}
          {!loading &&
            nhomSua.map(([loai, list]) => (
              <div key={loai} className="mb-12">
                <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)] flex items-center gap-4">
                  {ghiNhanLabel(loai)}
                  <span className="text-sm nq-ink-on-solid bg-[var(--nq-copper)] px-3 py-1 rounded-full">{list.length}</span>
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {list.slice(0, 8).map((g, i) => (
                    <div 
                      key={safeText(g.id, `${loai}-${i}`)}
                      className="bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-dim)] p-6 shadow-[8px_8px_0px_0px_var(--nq-copper-dim)] hover:translate-x-[-4px] hover:translate-y-[-4px] hover:shadow-[12px_12px_0px_0px_var(--nq-copper-dim)] transition-all flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex justify-end mb-4">
                          {g.dung_lai ? (
                            <StatusChip tone="ok">Mẫu dùng lại</StatusChip>
                          ) : (
                            <StatusChip>Lần riêng lẻ</StatusChip>
                          )}
                        </div>
                        <h3 className="text-xl font-bold mb-2 text-[var(--nq-fg)]">{ghiNhanLabel(g.loai)}</h3>
                        <p className="text-sm text-[var(--nq-dim)] font-mono">
                          {nvLabel(g.ai)}{g.luc ? ` · ${formatLuc(g.luc)}` : ""}
                        </p>
                      </div>
                    </div>
                  ))}
                  {list.length > 8 ? (
                    <div className="bg-[var(--nq-surface)] border-2 border-dashed border-[var(--nq-dim)] p-6 flex flex-col items-center justify-center text-center">
                      <h3 className="text-xl font-bold mb-2 text-[var(--nq-copper)]">Còn {list.length - 8} lần nữa</h3>
                      <p className="text-sm text-[var(--nq-dim)] font-mono">Đủ bốn lần cùng mẫu là hệ thống đề xuất thành luật cẩm nang.</p>
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
        </div>
      )}

      <div className="fixed bottom-0 left-0 w-full p-4 bg-[var(--nq-bg)]/80 backdrop-blur-md border-t-2 border-[var(--nq-dim)] z-50">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row gap-4 items-center justify-between">
          <p className="text-sm font-mono text-[var(--nq-dim)] hidden md:block">Việc treo chỉ đóng được từ phiếu ca.</p>
          <div className="flex gap-4 w-full sm:w-auto">
            <BtnLink href="/phieu" className="flex-1 sm:flex-none nq-ink-on-solid bg-[var(--nq-copper)] font-black uppercase tracking-widest py-3 px-6 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all text-center">
              Mở phiếu ca
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
    </div>
  );
}
