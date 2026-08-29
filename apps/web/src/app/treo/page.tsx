"use client";

/**
 * Việc treo — 18 bản ghi, ba trạng thái.
 *
 * Trước đây đây là một dải thẻ đều nhau xếp theo thứ tự máy chủ trả về: việc quá
 * hạn nằm lẫn giữa việc đã xong, và không có chỗ nào nói tổng bao nhiêu. Giờ
 * chia ba nhóm theo trạng thái, **quá hạn lên trước** vì đó là việc quán đang nợ
 * chính mình, mỗi nhóm có số đếm, và trên cùng là dải tóm tắt đếm từ dữ liệu
 * thật.
 *
 * Sổ lần sửa (30 bản ghi) nhóm theo loại thao tác kèm số lần — bốn lần cùng một
 * mẫu là ngưỡng hệ thống bắt đầu đề xuất luật, nên con số đó có nghĩa với người
 * đọc, không phải số cho đẹp.
 */

import { useCallback, useEffect, useMemo, useState, useRef } from "react";
import { motion } from "framer-motion";
import gsap from "gsap";
import { apiGet } from "../../lib/api";
import {
  matchExact,
  matchSearch,
  matchTime,
  TIME_FILTER_OPTIONS,
  uniqueSorted,
  type TimeFilter,
} from "../../lib/list-filters";
import {
  TREO_THU_TU,
  formatLuc,
  formatNgay,
  ghiNhanLabel,
  khungLabel,
  mauPhieuLabel,
  nvLabel,
  safeText,
  thuLabel,
  treoLabel,
  treoTone,
  viError,
} from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  BtnLink,
  Empty,
  Group,
  Loading,
  NextSteps,
  PageHeader,
  Row,
  StatusChip,
  Summary,
  TabBar,
  TabButton,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type ViecTreo = {
  id: string;
  mau?: string;
  thu?: string;
  khung?: string;
  noi_dung: string;
  han?: string;
  created_at?: string;
  nhan_vien?: string;
  nguoi_nhan?: string;
  trang_thai?: string;
  ca_sau_da_nhan?: boolean;
};

type GhiNhan = { id?: string; loai?: string; ai?: string; luc?: string; dung_lai?: boolean };

const NHOM: Record<string, { ten: string; giai_thich: string }> = {
  qua_han: {
    ten: "Quá hạn — xử trước",
    giai_thich: "Đã qua mốc hẹn mà chưa ai đóng. Ca nào đang chạy thì nhận lấy một việc ở đây.",
  },
  dang_cho: {
    ten: "Đang chờ làm",
    giai_thich: "Còn trong hạn. Ca sau đọc rồi nhận là xong.",
  },
  xong: {
    ten: "Đã xong",
    giai_thich: "Giữ lại để tra khi cần, không phải làm gì thêm.",
  },
};

export default function TreoPage() {
  const [token, setToken] = useState("");
  const [treo, setTreo] = useState<ViecTreo[]>([]);
  const [sua, setSua] = useState<GhiNhan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [suaError, setSuaError] = useState<string | null>(null);
  const [tab, setTab] = useState<"treo" | "sua">("treo");
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [personF, setPersonF] = useState("all");
  const [timeF, setTimeF] = useState<TimeFilter>("all");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  useEffect(() => {
    if (containerRef.current && !loading) {
      gsap.fromTo(
        ".ops-animate-in",
        { y: 30, opacity: 0 },
        { y: 0, opacity: 1, stagger: 0.1, duration: 0.5, ease: "power2.out" }
      );
    }
  }, [tab, loading, treo, sua]);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    Promise.all([
      apiGet<{ items: ViecTreo[] }>("/api/v1/viec-treo")
        .then((d) => {
          setTreo((d.items ?? []).filter((x) => x && typeof x.id === "string"));
          setError(null);
        })
        .catch((e) => setError(viError(e, { doing: "tải được danh sách việc treo" }))),
      apiGet<{ items: GhiNhan[] }>("/api/v1/ghi-nhan-sua")
        .then((d) => {
          setSua(d.items ?? []);
          setSuaError(null);
        })
        .catch((e) => setSuaError(viError(e, { doing: "tải được sổ lần sửa" }))),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  /** Gom theo trạng thái, giữ đúng thứ tự đọc: quá hạn → đang chờ → xong. */
  const nhomTreo = useMemo(() => {
    const filteredTreo = treo.filter((v) => {
      if (!matchSearch([v.noi_dung, v.nhan_vien ?? "", v.nguoi_nhan ?? "", v.mau ?? ""].join(" "), search)) return false;
      if (!matchExact(v.nhan_vien, personF)) return false;
      if (!matchTime(v.created_at, timeF)) return false;
      return true;
    });
    const m = new Map<string, ViecTreo[]>();
    for (const v of filteredTreo) {
      const k = safeText(v.trang_thai, "dang_cho");
      m.set(k, [...(m.get(k) ?? []), v]);
    }
    const thuTu = [...TREO_THU_TU, ...Array.from(m.keys()).filter((k) => !TREO_THU_TU.includes(k))];
    return thuTu.filter((k) => (m.get(k) ?? []).length > 0).map((k) => [k, m.get(k) ?? []] as const);
  }, [treo, search, personF, timeF]);

  const dem = useCallback(
    (tt: string) => treo.filter((v) => safeText(v.trang_thai, "dang_cho") === tt).length,
    [treo],
  );

  /** Sổ lần sửa gom theo loại thao tác: số lần mỗi loại là bằng chứng sinh luật. */
  const nhomSua = useMemo(() => {
    const filteredSua = sua.filter((g) => {
      if (!matchSearch([g.loai ?? "", g.ai ?? ""].join(" "), search)) return false;
      if (!matchExact(g.ai, personF)) return false;
      if (!matchTime(g.luc, timeF)) return false;
      return true;
    });
    const m = new Map<string, GhiNhan[]>();
    for (const g of filteredSua) {
      const k = safeText(g.loai, "khac");
      m.set(k, [...(m.get(k) ?? []), g]);
    }
    return Array.from(m.entries()).sort((a, b) => b[1].length - a[1].length);
  }, [sua, search, personF, timeF]);

  if (!token) return <AuthGate />;

  const personOptions = [
    { value: "all", label: "Mọi người" },
    ...uniqueSorted([...treo.map((v) => v.nhan_vien), ...sua.map((g) => g.ai)]).map((v) => ({ value: v, label: nvLabel(v) })),
  ];
  const filterActive = search.length > 0 || personF !== "all" || timeF !== "all";
  const treoFiltered = nhomTreo.flatMap(([, list]) => list).length;
  const suaFiltered = nhomSua.flatMap(([, list]) => list).length;

  function clearFilters() {
    setSearch("");
    setPersonF("all");
    setTimeF("all");
  }

  return (
    <main className="min-h-screen p-4 md:p-8 pb-32 relative" ref={containerRef}>
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
        <button 
          className={`flex-1 py-4 font-black uppercase tracking-widest transition-colors ${tab === "sua" ? "text-[var(--nq-copper)] border-b-4 border-[var(--nq-copper)]" : "text-[var(--nq-dim)] hover:text-[var(--nq-fg)]"}`}
          onClick={() => setTab("sua")}
        >
          Lần sửa lịch ({sua.length})
        </button>
      </div>

      <div className="ops-animate-in mb-8">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm nội dung, nhân viên, loại thao tác…"
          person={personF}
          onPersonChange={setPersonF}
          personOptions={personOptions}
          time={timeF}
          onTimeChange={(v) => setTimeF(v as TimeFilter)}
          timeOptions={TIME_FILTER_OPTIONS}
          shown={tab === "treo" ? treoFiltered : suaFiltered}
          total={tab === "treo" ? treo.length : sua.length}
          filtered={filterActive}
        />
      </div>

      {tab === "treo" && (
        <div className="ops-animate-in space-y-8">
          {error ? <Alert>{error}</Alert> : null}
          {loading ? <Loading skeleton="rows" rows={4} groups={3}>Đang tải việc treo…</Loading> : null}
          {!loading && !error && treo.length === 0 ? (
            <Empty title="Không có việc treo">Ca chạy sạch, không còn việc nào bị kẹt lại.</Empty>
          ) : null}
          {!loading && treo.length > 0 && treoFiltered === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
          {!loading &&
            nhomTreo.map(([tt, list]) => (
              <div key={tt} className="mb-12">
                <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)] flex items-center gap-4">
                  {NHOM[tt]?.ten ?? treoLabel(tt)}
                  <span className="text-sm bg-[var(--nq-copper)] text-[#0e0c0a] px-3 py-1 rounded-full">{list.length}</span>
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
        <div className="ops-animate-in space-y-8">
          {suaError ? <Alert>{suaError}</Alert> : null}
          {loading ? <Loading skeleton="rows" rows={4} groups={2}>Đang tải sổ lần sửa…</Loading> : null}
          {!loading && !suaError && sua.length === 0 ? (
            <Empty title="Chưa có lần sửa nào">Ghim ca hoặc nhả ca sẽ xuất hiện ở đây.</Empty>
          ) : null}
          {!loading && sua.length > 0 && suaFiltered === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
          {!loading &&
            nhomSua.map(([loai, list]) => (
              <div key={loai} className="mb-12">
                <h2 className="text-2xl font-black uppercase mb-6 text-[var(--nq-fg)] flex items-center gap-4">
                  {ghiNhanLabel(loai)}
                  <span className="text-sm bg-[var(--nq-copper)] text-[#0e0c0a] px-3 py-1 rounded-full">{list.length}</span>
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
            <BtnLink href="/phieu" className="flex-1 sm:flex-none bg-[var(--nq-copper)] text-[#0e0c0a] font-black uppercase tracking-widest py-3 px-6 border-2 border-[var(--nq-copper)] hover:bg-transparent hover:text-[var(--nq-copper)] transition-all text-center">
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
    </main>
  );
}
