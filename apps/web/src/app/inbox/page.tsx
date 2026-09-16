"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { apiGet, apiSend } from "../../lib/api";
import {
  agentLabel,
  formatLuc,
  inboxLabel,
  inboxTone,
  kenhLabel,
  khungLabel,
  rangBuocLabel,
  safeText,
  thuLabel,
  yDinhLabel,
} from "../../lib/present";
import { matchExact, matchSearch, matchTime, TIME_FILTER_OPTIONS, uniqueSorted, type TimeFilter } from "../../lib/list-filters";
import { getToken, isChuQuan, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Confidence,
  Empty,
  FixtureChip,
  Group,
  Loading,
  Notice,
  PageHeader,
  Row,
  StatusChip,
  useToasts,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";
import { PersonSelect, ShiftSelect } from "../../ui/ops-pickers";

type Lifecycle = {
  tuan_iso?: string;
  trang_thai?: string;
  solver?: {
    status?: string;
    ok?: boolean;
    danh_sach_xung_dot?: string[];
  };
};

type AutoScheduleResult = {
  ok?: boolean;
  skipped?: boolean;
  status?: string;
  detail?: string;
  tong_so_o_ca?: number;
  so_o_ca_da_xep?: number;
};

type Candidate = {
  nv_id: string;
  ten: string;
  score: number;
  is_qualified: boolean;
  is_available: boolean;
  reasons?: string[];
  warnings?: string[];
};

type Item = {
  id: string;
  tom_tat: string;
  trang_thai: string;
  agent: string;
  y_dinh?: string;
  do_tin_cay?: number;
  created_at?: string;
  nguon?: string;
  noi_dung_goc?: string;
  nv_id?: string;
  can_xac_minh?: boolean;
  doi_tac_khong_ro?: boolean;
  khan_cap?: boolean;
  goi_y_doi_tac?: Candidate[];
  ly_do_quyet?: string;
  hieu_luc?: { loai?: string; ghi?: string; swap_id?: string; tuan_id?: string };
  rang_buoc?: {
    loai?: string;
    thu?: string;
    khung?: string;
    start?: string;
    end?: string;
    tuan_id?: string;
    ca_id?: string;
    doi_tac?: string;
    doi_tac_khong_ro?: boolean;
    can_xac_minh?: boolean;
  };
};

type DecisionResponse = Item & {
  tu_dong_xep_lich?: AutoScheduleResult;
};

const THU_TU = ["cho_duyet", "moi", "duyet", "tu_choi"];

const TEN_NHOM: Record<string, string> = {
  cho_duyet: "Chờ bạn quyết",
  moi: "Mới vào hộp thư",
  duyet: "Đã duyệt",
  tu_choi: "Đã từ chối",
};

/** Diễn đạt mục đích ràng buộc bằng một câu người đọc hiểu ngay. */
function mucDichCau(it: Item): string {
  const y = it.y_dinh ?? "khac";
  const rb = it.rang_buoc ?? {};
  const thuFull = rb.thu ? thuLabel(rb.thu) : "";
  switch (y) {
    case "xin_nghi":
      return thuFull
        ? `Xin nghỉ cả ngày ${thuFull}`
        : "Xin nghỉ một ca (chưa rõ ngày)";
    case "doi_ca":
      return "Đổi ca sang người khác trong tuần";
    case "nhan_ca":
      return "Nhận thêm ca trong tuần";
    case "bao_tre":
      return rb.start
        ? `Báo đến trễ từ ${rb.start} ngày ${thuFull || "ca này"}`
        : "Báo đến trễ trong ca";
    case "cap_nhat_tkb":
      return rb.start && rb.end
        ? `Lịch bận ${thuFull || "ngày"} khung ${rb.start}–${rb.end}`
        : "Cập nhật lịch bận (thời khóa biểu)";
    default:
      return "Ghi nhận việc trong ca, không đổi lịch";
  }
}

/** Diễn đạt lý do bị ràng buộc — từ nội dung gốc hoặc hiệu lực đã ghi. */
function lyDoCau(it: Item): string {
  if (it.hieu_luc?.ghi) return it.hieu_luc.ghi;
  const goc = it.noi_dung_goc?.trim();
  if (goc) return goc.length > 160 ? `${goc.slice(0, 160)}…` : goc;
  return it.tom_tat;
}

/** Nhãn loại ràng buộc (cho solver) dễ đọc. */
function loaiRangBuocCau(it: Item): string {
  const hl = it.hieu_luc?.loai;
  if (hl === "rang_buoc_cho_solver") return "Ràng buộc cho lần xếp lịch tới";
  if (hl === "cho_doi_ca") return "Phiếu đổi ca";
  if (hl === "ghi_nhan") return "Chỉ ghi nhận, không đổi lịch";
  if (it.trang_thai === "cho_duyet" || it.trang_thai === "moi") {
    return "Chờ duyệt — duyệt mới nạp vào xếp lịch";
  }
  return "Ràng buộc ca làm việc";
}

function ngayRangBuoc(it: Item): string {
  const rb = it.rang_buoc ?? {};
  const parts: string[] = [];
  if (rb.thu) parts.push(thuLabel(rb.thu));
  if (rb.start && rb.end) parts.push(`${rb.start}–${rb.end}`);
  else if (rb.khung) parts.push(khungLabel(rb.khung) || "");
  if (rb.tuan_id) parts.push(`Tuần ${rb.tuan_id}`);
  return parts.filter(Boolean).join(" · ") || "Không rõ ngày";
}

function itemHaystack(it: Item): string {
  return [
    it.tom_tat,
    it.nguon,
    it.agent,
    it.nv_id,
    it.noi_dung_goc,
    it.hieu_luc?.ghi,
    inboxLabel(it.trang_thai),
    yDinhLabel(it.y_dinh),
  ]
    .filter(Boolean)
    .join(" ");
}

function anhHuongXepLich(it: Item): boolean {
  return ["xin_nghi", "bao_tre", "cap_nhat_tkb"].includes(it.y_dinh ?? "");
}

export default function InboxPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [manager, setManager] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusF, setStatusF] = useState("all");
  const [personF, setPersonF] = useState("all");
  const [timeF, setTimeF] = useState<TimeFilter>("all");
  const [swapModalItem, setSwapModalItem] = useState<Item | null>(null);
  const [swapCaId, setSwapCaId] = useState("");
  const [swapDoiTac, setSwapDoiTac] = useState("");
  const [swapApDat, setSwapApDat] = useState(false);
  const [life, setLife] = useState<Lifecycle | null>(null);
  const [chuQuan, setChuQuan] = useState(false);
  const [showReopenModal, setShowReopenModal] = useState(false);
  const [reopenReason, setReopenReason] = useState("");
  const [duyetModalItem, setDuyetModalItem] = useState<Item | null>(null);
  const [autoXepSauDuyet, setAutoXepSauDuyet] = useState(true);
  const [autoScheduleResult, setAutoScheduleResult] = useState<AutoScheduleResult | null>(null);
  const [tuChoiModalItem, setTuChoiModalItem] = useState<Item | null>(null);
  const [tuChoiLyDo, setTuChoiLyDo] = useState("");
  const [coMau, setCoMau] = useState(false);
  const { push } = useToasts();
  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setChuQuan(isChuQuan());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Item[]; co_du_lieu_mau?: boolean }>("/api/v1/inbox/rang-buoc")
      .then((d) => {
        setItems(d.items ?? []);
        setCoMau(d.co_du_lieu_mau === true);
      })
      .catch(() => setError("Không tải được hộp thư."))
      .finally(() => setLoading(false));
    apiGet<Lifecycle>("/api/v1/lich/lifecycle")
      .then((l) => setLife(l))
      .catch(() => {});
  }, []);

  async function reopenWeek() {
    if (!reopenReason.trim()) {
      setError("Vui lòng nhập lý do mở lại lịch.");
      return;
    }
    setBusy("reopen");
    try {
      await apiSend("/api/v1/lich/lifecycle", { to: "nhap", ly_do: reopenReason.trim() });
      push("Đã mở lại lịch sang trạng thái nháp. Bạn có thể xếp lịch tuần mới.");
      setShowReopenModal(false);
      setReopenReason("");
      load();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể mở lại lịch.";
      setError(msg);
    } finally {
      setBusy(null);
    }
  }

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  const personOptions = useMemo(
    () => [{ value: "all", label: "Mọi người" }, ...uniqueSorted(items.map((i) => i.nv_id)).map((v) => ({ value: v, label: v }))],
    [items],
  );

  const statusOptions = useMemo(
    () => [{ value: "all", label: "Mọi trạng thái" }, ...THU_TU.map((s) => ({ value: s, label: TEN_NHOM[s] ?? inboxLabel(s) }))],
    [],
  );

  const filtered = useMemo(() => {
    return items.filter((it) => {
      if (!matchSearch(itemHaystack(it), search)) return false;
      if (!matchExact(it.trang_thai, statusF)) return false;
      if (!matchExact(it.nv_id, personF)) return false;
      if (!matchTime(it.created_at, timeF)) return false;
      return true;
    });
  }, [items, search, statusF, personF, timeF]);

  const nhom = useMemo(() => {
    const buckets = new Map<string, Item[]>();
    for (const tt of THU_TU) buckets.set(tt, []);
    for (const it of filtered) {
      const key = buckets.has(it.trang_thai) ? it.trang_thai : "moi";
      buckets.get(key)!.push(it);
    }
    return THU_TU.map((tt) => [tt, buckets.get(tt)!] as const).filter(([, list]) => list.length > 0);
  }, [filtered]);

  const filterActive = search.length > 0 || statusF !== "all" || personF !== "all" || timeF !== "all";

  function clearFilters() {
    setSearch("");
    setStatusF("all");
    setPersonF("all");
    setTimeF("all");
  }

  async function decide(
    id: string,
    quyet_dinh: string,
    extra?: {
      ca_id?: string;
      doi_tac_nv_id?: string;
      ap_dat?: boolean;
      ly_do?: string;
      tu_dong_xep_lich?: boolean;
    },
  ) {
    setBusy(id);
    setAutoScheduleResult(null);
    try {
      const response = await apiSend<DecisionResponse>(
        `/api/v1/inbox/rang-buoc/${id}`,
        { quyet_dinh, ...extra },
      );
      if (response.tu_dong_xep_lich) {
        setAutoScheduleResult(response.tu_dong_xep_lich);
      }
      push(
        response.tu_dong_xep_lich?.ok
          ? `Đã duyệt và tự xếp đủ ${response.tu_dong_xep_lich.so_o_ca_da_xep ?? 0}/${response.tu_dong_xep_lich.tong_so_o_ca ?? 21} ô ca tuần.`
          : quyet_dinh === "duyet"
          ? "Đã duyệt. Hệ thống ghi hiệu lực — không sửa lịch âm thầm."
          : "Đã từ chối. Ràng buộc này không vào lượt xếp lịch.",
      );
      setSwapModalItem(null);
      load();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Cần quyền quản lý hoặc thông tin đổi ca chưa đủ.";
      setError(msg);
    } finally {
      setBusy(null);
    }
  }

  function handleDuyet(it: Item) {
    if (it.y_dinh === "doi_ca" || it.y_dinh === "nhan_ca") {
      const existingCa = it.rang_buoc?.ca_id || "";
      const existingDoiTac = it.rang_buoc?.doi_tac || "";
      if (!existingCa || !existingDoiTac || it.doi_tac_khong_ro || it.rang_buoc?.doi_tac_khong_ro) {
        setSwapModalItem(it);
        setSwapCaId(existingCa);
        setSwapDoiTac(existingDoiTac);
        setSwapApDat(false);
        return;
      }
    }
    // Mở khung chi tiết để người duyệt đọc đủ thông tin trước khi bấm chốt.
    setAutoXepSauDuyet(anhHuongXepLich(it));
    setDuyetModalItem(it);
  }

  async function xacNhanDuyet(it: Item, extra?: { ca_id?: string; doi_tac_nv_id?: string; ap_dat?: boolean }) {
    await decide(it.id, "duyet", {
      ...extra,
      tu_dong_xep_lich: anhHuongXepLich(it) && autoXepSauDuyet,
    });
    setDuyetModalItem(null);
  }

  async function xacNhanTuChoi(it: Item) {
    await decide(it.id, "tu_choi", tuChoiLyDo.trim() ? { ly_do: tuChoiLyDo.trim() } : undefined);
    setTuChoiModalItem(null);
    setTuChoiLyDo("");
  }

  async function handleSmartApprove(it: Item, selectedNvId?: string) {
    if (!manager) return;
    setBusy(it.id);
    setError(null);
    try {
      await apiSend(`/api/v1/inbox/rang-buoc/${it.id}/smart-approve`, {
        selected_nv_id: selectedNvId || null,
        ap_dat: true,
      });
      push("Đã duyệt đổi ca thông minh thành công!");
      await load();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Không thể duyệt đổi ca.";
      setError(msg);
    } finally {
      setBusy(null);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--wide">
      <PageHeader
        kicker="Người duyệt · hệ thống không tự chọn"
        title="Hộp thư ràng buộc"
        meta="Khi hai claim mâu thuẫn, người quyết. Không tự chọn hộ."
      />
      {coMau ? (
        <p className="mb-4">
          <FixtureChip />
        </p>
      ) : null}
      {error ? <Alert>{error}</Alert> : null}
      {autoScheduleResult ? (
        autoScheduleResult.ok ? (
          <Notice>
            Đã tự xếp đủ{" "}
            <strong>
              {autoScheduleResult.so_o_ca_da_xep ?? 0}/{autoScheduleResult.tong_so_o_ca ?? 21} ô ca tuần
            </strong>
            . Lịch đang chờ quản lý duyệt. <Link href="/roster" className="underline">Mở lịch tuần →</Link>
          </Notice>
        ) : (
          <Alert>
            Ràng buộc đã được duyệt nhưng chưa thể tự xếp lịch
            {autoScheduleResult.status === "LIFECYCLE_LOCKED"
              ? " vì lịch đã duyệt, công bố hoặc đóng. Hãy mở đợt xếp tuần mới."
              : " vì không đủ nhân sự phù hợp với các ràng buộc hiện tại."}
          </Alert>
        )
      ) : null}
      {!manager ? <Notice>Bạn xem được nội dung. Quản lý hoặc chủ quán mới bấm duyệt.</Notice> : null}
      {life?.solver && (!life.solver.ok || life.solver.status?.includes("INFEASIBLE")) ? (
        <div className="mb-4 p-4 border-2 border-red-500 bg-red-950/40 text-red-200 rounded">
          <div className="font-bold uppercase tracking-wider mb-1 flex items-center gap-2">
            <span>⚠️</span> Lịch tuần này đang xung đột — Solver không khả thi
          </div>
          <p className="text-sm mb-2">
            Các ràng buộc xin nghỉ hoặc TKB đã duyệt khiến một số ca thiếu nhân sự tối thiểu. Chi tiết:
          </p>
          <ul className="list-disc list-inside text-xs space-y-1">
            {life.solver.danh_sach_xung_dot && life.solver.danh_sach_xung_dot.length > 0 ? (
              life.solver.danh_sach_xung_dot.map((c, i) => <li key={i}>{c}</li>)
            ) : (
              <li>Mâu thuẫn giữa ràng buộc nghỉ phép/TKB và yêu cầu số người của ca.</li>
            )}
          </ul>
        </div>
      ) : null}

      {life?.trang_thai === "da_dong" ? (
        <div className="mb-4 p-4 border-2 border-[var(--nq-copper)] bg-[var(--nq-copper-dim,#332211)] text-[var(--nq-fg)] rounded flex flex-col md:flex-row items-start md:items-center justify-between gap-3">
          <div>
            <div className="font-bold uppercase tracking-wider">
              Lịch tuần {life.tuan_iso ?? ""} đã đóng băng
            </div>
            <div className="text-sm opacity-80">
              Đợt xếp lịch tuần này đã đóng. Chủ quán có thể mở lại đợt xếp tuần mới.
            </div>
          </div>
          {chuQuan ? (
            <Btn variant="primary" onClick={() => setShowReopenModal(true)}>
              Mở đợt xếp tuần mới
            </Btn>
          ) : null}
        </div>
      ) : null}

      <ListToolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Tìm tóm tắt, kênh, agent, mã NV…"
        status={statusF}
        onStatusChange={setStatusF}
        statusOptions={statusOptions}
        person={personF}
        onPersonChange={setPersonF}
        personOptions={personOptions}
        time={timeF}
        onTimeChange={(v) => setTimeF(v as TimeFilter)}
        timeOptions={TIME_FILTER_OPTIONS}
        shown={filtered.length}
        total={items.length}
        filtered={filterActive}
      />

      {loading ? (
        <Loading skeleton="rows" rows={4} groups={3}>
          Đang mở hộp thư…
        </Loading>
      ) : null}

      {!loading && !error && items.length === 0 ? (
        <Empty title="Hộp thư trống">Không có ràng buộc nào chờ người quyết.</Empty>
      ) : null}

      {!loading && items.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}

      {!loading &&
        nhom.map(([tt, list]) => (
          <Group key={tt} title={TEN_NHOM[tt] ?? inboxLabel(tt)} count={list.length} countLabel="mục">
            {list.map((it) => (
              <Row
                key={it.id}
                title={safeText(it.tom_tat, "Ràng buộc chưa có tóm tắt")}
                sub={
                  <div className="space-y-2 text-sm leading-relaxed">
                    {/* Nội dung gốc — người duyệt đọc đúng lời nhân sự đã nhắn */}
                    <p className="text-[var(--nq-fg)]">
                      {safeText(it.noi_dung_goc, "Ràng buộc không kèm nội dung gốc")}
                    </p>
                    {/* Chi tiết ràng buộc dạng bảng ghi rõ ràng */}
                    <dl className="grid grid-cols-1 gap-x-6 gap-y-1 text-xs sm:grid-cols-[auto_1fr]">
                      <dt className="font-bold uppercase tracking-wide text-[var(--nq-dim)]">Ngày bị ràng buộc</dt>
                      <dd className="text-[var(--nq-fg)]">{ngayRangBuoc(it)}</dd>
                      <dt className="font-bold uppercase tracking-wide text-[var(--nq-dim)]">Mục đích ràng buộc</dt>
                      <dd className="text-[var(--nq-fg)]">{mucDichCau(it)}</dd>
                      <dt className="font-bold uppercase tracking-wide text-[var(--nq-dim)]">Loại ràng buộc</dt>
                      <dd className="text-[var(--nq-fg)]">
                        {it.rang_buoc?.loai ? `${rangBuocLabel(it.rang_buoc.loai)} — ${loaiRangBuocCau(it)}` : loaiRangBuocCau(it)}
                      </dd>
                      <dt className="font-bold uppercase tracking-wide text-[var(--nq-dim)]">Lý do</dt>
                      <dd className="text-[var(--nq-fg)]">{lyDoCau(it)}</dd>
                      <dt className="font-bold uppercase tracking-wide text-[var(--nq-dim)]">Nhận lúc</dt>
                      <dd className="text-[var(--nq-fg)]">
                        {it.created_at ? formatLuc(it.created_at) : "—"}
                        {it.nv_id ? ` · ${it.nv_id}` : ""}
                        {` · ${kenhLabel(it.nguon)} · ${agentLabel(it.agent)}`}
                      </dd>
                    </dl>
                    {it.hieu_luc?.ghi ? (
                      <p className="text-xs text-[var(--nq-dim)]">
                        Hiệu lực đã ghi: {it.hieu_luc.ghi}
                      </p>
                    ) : null}
                    {it.ly_do_quyet && it.trang_thai === "tu_choi" ? (
                      <p className="text-xs text-rose-300">
                        Lý do từ chối: {it.ly_do_quyet}
                      </p>
                    ) : null}
                    {it.goi_y_doi_tac && it.goi_y_doi_tac.length > 0 && it.trang_thai === "cho_duyet" && (
                      <div className="mt-2 rounded-lg border border-purple-800/40 bg-purple-950/20 p-2.5 text-xs space-y-1.5">
                        <div className="font-bold text-purple-300 flex items-center gap-1.5">
                          <span>💡</span> AI Đề Xuất Ứng Viên Phù Hợp Nhất:
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {it.goi_y_doi_tac.map((cand) => (
                            <div
                              key={cand.nv_id}
                              className="flex items-center gap-1.5 rounded bg-zinc-900/90 px-2 py-1 border border-zinc-700"
                            >
                              <span className="font-semibold text-white">⭐ {cand.ten}</span>
                              <span className="text-[10px] text-amber-300 font-bold">({cand.score}%)</span>
                              {cand.reasons && cand.reasons.length > 0 && (
                                <span className="text-[10px] text-zinc-400">· {cand.reasons[0]}</span>
                              )}
                              {manager && (
                                <button
                                  type="button"
                                  disabled={busy === it.id}
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleSmartApprove(it, cand.nv_id);
                                  }}
                                  className="ml-1 rounded bg-purple-600 hover:bg-purple-500 text-white px-1.5 py-0.5 text-[10px] font-bold"
                                >
                                  ✓ Chọn & Duyệt
                                </button>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                }
                side={
                  <>
                    <StatusChip tone={inboxTone(it.trang_thai)}>{inboxLabel(it.trang_thai)}</StatusChip>
                    <StatusChip>{kenhLabel(it.nguon)}</StatusChip>
                    <StatusChip>{yDinhLabel(it.y_dinh)}</StatusChip>
                    {it.khan_cap ? (
                      <StatusChip tone="danger">🚨 Khẩn cấp (&lt;24h)</StatusChip>
                    ) : null}
                    {it.trang_thai === "duyet" ? (
                      it.y_dinh === "doi_ca" || it.y_dinh === "nhan_ca" ? (
                        <Link href="/doi-ca">
                          <StatusChip tone="ok">Đổi ca · Chợ đổi ca ↗</StatusChip>
                        </Link>
                      ) : (
                        <StatusChip tone="ok">
                          Solver: đã nạp {it.hieu_luc?.tuan_id || it.rang_buoc?.tuan_id || life?.tuan_iso || "tuần"}
                        </StatusChip>
                      )
                    ) : null}
                    {it.can_xac_minh || (it.do_tin_cay != null && it.do_tin_cay < 0.7) ? (
                      <StatusChip tone="danger">Cần xác minh</StatusChip>
                    ) : null}
                    {it.doi_tac_khong_ro || it.rang_buoc?.doi_tac_khong_ro ? (
                      <StatusChip tone="danger">Trùng tên đối tác</StatusChip>
                    ) : null}
                    <Confidence value={it.do_tin_cay} />
                  </>
                }
                actions={
                  it.trang_thai === "cho_duyet" && manager ? (
                    <>
                      {it.goi_y_doi_tac && it.goi_y_doi_tac.length > 0 && (it.doi_tac_khong_ro || it.rang_buoc?.doi_tac_khong_ro) ? (
                        <Btn
                          variant="primary"
                          busy={busy === it.id}
                          busyLabel="Đang duyệt…"
                          onClick={() => handleSmartApprove(it)}
                          className="bg-purple-600 hover:bg-purple-500 font-bold text-white shadow-md border border-purple-400"
                        >
                          ⚡ Duyệt AI ({it.goi_y_doi_tac[0].ten})
                        </Btn>
                      ) : (
                        <Btn
                          variant="primary"
                          busy={busy === it.id}
                          busyLabel="Đang ghi quyết định…"
                          onClick={() => handleDuyet(it)}
                        >
                          Duyệt ràng buộc
                        </Btn>
                      )}
                      <Btn variant="danger" disabled={busy === it.id} onClick={() => { setTuChoiModalItem(it); setTuChoiLyDo(""); }}>
                        Từ chối
                      </Btn>
                    </>
                  ) : undefined
                }
              />
            ))}
          </Group>
        ))}

      {duyetModalItem && typeof document !== "undefined" ? createPortal(
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          onClick={() => setDuyetModalItem(null)}
          onKeyDown={(e) => e.key === 'Escape' && setDuyetModalItem(null)}
        >
          <div
            className="bg-[var(--nq-surface)] border-2 border-emerald-500/70 p-6 max-w-lg w-full shadow-2xl rounded max-h-[85vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold uppercase tracking-wider mb-2 text-emerald-300">
              Duyệt ràng buộc — xem chi tiết trước khi chốt
            </h3>
            <p className="text-sm opacity-80 mb-4 text-[var(--nq-fg)]">
              Duyệt đồng nghĩa ràng buộc này sẽ được nạp vào lượt xếp lịch tiếp theo. Vui lòng đọc
              kỹ chi tiết bên dưới rồi bấm xác nhận.
            </p>
            <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm mb-5">
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-[var(--nq-dim)]">Nội dung tin nhắn</dt>
                <dd className="text-[var(--nq-fg)] mt-0.5">{safeText(duyetModalItem.noi_dung_goc, duyetModalItem.tom_tat)}</dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-[var(--nq-dim)]">Ngày bị ràng buộc</dt>
                <dd className="text-[var(--nq-fg)] mt-0.5">{ngayRangBuoc(duyetModalItem)}</dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-[var(--nq-dim)]">Mục đích</dt>
                <dd className="text-[var(--nq-fg)] mt-0.5">{mucDichCau(duyetModalItem)}</dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-[var(--nq-dim)]">Loại ràng buộc</dt>
                <dd className="text-[var(--nq-fg)] mt-0.5">
                  {duyetModalItem.rang_buoc?.loai
                    ? `${rangBuocLabel(duyetModalItem.rang_buoc.loai)} — ${loaiRangBuocCau(duyetModalItem)}`
                    : loaiRangBuocCau(duyetModalItem)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-[var(--nq-dim)]">Lý do</dt>
                <dd className="text-[var(--nq-fg)] mt-0.5">{lyDoCau(duyetModalItem)}</dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-[var(--nq-dim)]">Người gửi · Kênh</dt>
                <dd className="text-[var(--nq-fg)] mt-0.5">
                  {duyetModalItem.nv_id || "—"} · {kenhLabel(duyetModalItem.nguon)} · {yDinhLabel(duyetModalItem.y_dinh)}
                </dd>
              </div>
            </dl>
            {anhHuongXepLich(duyetModalItem) ? (
              <label className="flex items-start gap-3 rounded border border-emerald-700/50 bg-emerald-950/20 p-3 text-sm text-[var(--nq-fg)]">
                <input
                  type="checkbox"
                  checked={autoXepSauDuyet}
                  onChange={(event) => setAutoXepSauDuyet(event.target.checked)}
                  className="mt-0.5 h-4 w-4"
                />
                <span>
                  <strong>Tự động xếp lại đủ 21 ô ca tuần sau khi duyệt</strong>
                  <span className="mt-1 block text-xs text-[var(--nq-dim)]">
                    Solver tôn trọng TKB, nghỉ phép, kỹ năng và giới hạn giờ; lịch mới sẽ ở trạng thái chờ duyệt.
                  </span>
                </span>
              </label>
            ) : null}
            <div className="mt-6 flex justify-end gap-3">
              <Btn variant="ghost" onClick={() => setDuyetModalItem(null)}>
                Xem lại sau
              </Btn>
              <Btn
                variant="primary"
                busy={busy === duyetModalItem.id}
                onClick={() => void xacNhanDuyet(duyetModalItem)}
              >
                Duyệt ràng buộc
              </Btn>
            </div>
          </div>
        </div>,
        document.body,
      ) : null}

      {tuChoiModalItem && typeof document !== "undefined" ? createPortal(
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          onClick={() => setTuChoiModalItem(null)}
          onKeyDown={(e) => e.key === 'Escape' && setTuChoiModalItem(null)}
        >
          <div
            className="bg-[var(--nq-surface)] border-2 border-rose-500/70 p-6 max-w-md w-full shadow-2xl rounded"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold uppercase tracking-wider mb-2 text-rose-300">
              Từ chối ràng buộc
            </h3>
            <p className="text-sm opacity-80 mb-4 text-[var(--nq-fg)]">
              Ràng buộc sẽ không vào lượt xếp lịch. Bạn có thể gửi kèm một câu lý do để người gửi hiểu
              vì sao (chỉ lưu nội bộ hộp thư).
            </p>
            <dl className="grid grid-cols-1 gap-y-2 text-sm mb-4">
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-[var(--nq-dim)]">Nội dung</dt>
                <dd className="text-[var(--nq-fg)] mt-0.5">
                  {safeText(tuChoiModalItem.noi_dung_goc, tuChoiModalItem.tom_tat)}
                </dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-[var(--nq-dim)]">Ngày bị ràng buộc</dt>
                <dd className="text-[var(--nq-fg)] mt-0.5">{ngayRangBuoc(tuChoiModalItem)}</dd>
              </div>
              <div>
                <dt className="text-xs font-bold uppercase tracking-wide text-[var(--nq-dim)]">Mục đích</dt>
                <dd className="text-[var(--nq-fg)] mt-0.5">{mucDichCau(tuChoiModalItem)}</dd>
              </div>
            </dl>
            <div>
              <label className="block text-xs font-bold uppercase mb-1 text-[var(--nq-fg)]">
                Lý do từ chối (không bắt buộc)
              </label>
              <input
                type="text"
                placeholder="Ví dụ: Lịch thứ 2 đã thiếu người, lần sau báo sớm hơn nhé..."
                value={tuChoiLyDo}
                onChange={(e) => setTuChoiLyDo(e.target.value)}
                className="nq-input w-full"
              />
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <Btn variant="ghost" onClick={() => setTuChoiModalItem(null)}>
                Huỷ
              </Btn>
              <Btn
                variant="danger"
                disabled={busy === tuChoiModalItem.id}
                busy={busy === tuChoiModalItem.id}
                onClick={() => void xacNhanTuChoi(tuChoiModalItem)}
              >
                Xác nhận từ chối
              </Btn>
            </div>
          </div>
        </div>,
        document.body,
      ) : null}

      {swapModalItem && typeof document !== "undefined" ? createPortal(
        <div
          className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          onClick={() => setSwapModalItem(null)}
          onKeyDown={(e) => e.key === 'Escape' && setSwapModalItem(null)}
        >
          <div
            className="bg-[var(--nq-surface)] border-2 border-[var(--nq-copper)] p-6 max-w-md w-full shadow-2xl rounded"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold uppercase tracking-wider mb-2 text-[var(--nq-fg)]">
              Chỉ định ca & đối tác đổi ca
            </h3>
            <p className="text-sm opacity-80 mb-4 text-[var(--nq-fg)]">
              {swapModalItem.doi_tac_khong_ro || swapModalItem.rang_buoc?.doi_tac_khong_ro
                ? "Tên đối tác bị trùng — vui lòng chọn đúng nhân viên trong danh sách."
                : "Vui lòng chọn ca và nhân viên nhận ca để mở phiếu đổi ca."}
            </p>
            <div className="space-y-4">
              <ShiftSelect
                label="Ca làm việc"
                placeholder="-- Chọn ca làm việc --"
                value={swapCaId}
                onChange={setSwapCaId}
              />
              <PersonSelect
                label="Người nhận ca"
                placeholder="-- Chọn nhân viên nhận ca --"
                value={swapDoiTac}
                onChange={setSwapDoiTac}
              />
              <label className="flex items-center gap-2 text-sm text-[var(--nq-fg)] cursor-pointer pt-2">
                <input
                  type="checkbox"
                  checked={swapApDat}
                  onChange={(e) => setSwapApDat(e.target.checked)}
                  className="w-4 h-4 text-[var(--nq-copper)]"
                />
                <span>Áp đặt bởi Quản lý (xác nhận ngay, không chờ đối tác đồng ý)</span>
              </label>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <Btn variant="ghost" onClick={() => setSwapModalItem(null)}>
                Huỷ
              </Btn>
              <Btn
                variant="primary"
                disabled={!swapCaId || !swapDoiTac}
                onClick={() =>
                  decide(swapModalItem.id, "duyet", {
                    ca_id: swapCaId,
                    doi_tac_nv_id: swapDoiTac,
                    ap_dat: swapApDat,
                  })
                }
              >
                Xác nhận duyệt
              </Btn>
            </div>
          </div>
        </div>,
        document.body,
      ) : null}

      {showReopenModal && typeof document !== "undefined" ? createPortal(
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--nq-panel-bg,#222)] border-2 border-[var(--nq-copper)] p-6 max-w-md w-full shadow-2xl rounded">
            <h3 className="text-lg font-bold uppercase tracking-wider mb-2 text-[var(--nq-fg)]">
              Mở lại đợt xếp lịch tuần mới
            </h3>
            <p className="text-sm opacity-80 mb-4 text-[var(--nq-fg)]">
              Chuyển lịch từ «Đã đóng» về «Bản nháp» để nạp các ràng buộc mới và chạy Solver. Bắt buộc nhập lý do (sẽ ghi vào Audit log).
            </p>
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase mb-1 text-[var(--nq-fg)]">
                  Lý do mở lại
                </label>
                <input
                  type="text"
                  placeholder="Ví dụ: Mở đợt xếp lịch tuần mới hoặc chỉnh sửa gấp..."
                  value={reopenReason}
                  onChange={(e) => setReopenReason(e.target.value)}
                  className="nq-input w-full"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <Btn variant="ghost" onClick={() => setShowReopenModal(false)}>
                Huỷ
              </Btn>
              <Btn
                variant="primary"
                disabled={!reopenReason.trim() || busy === "reopen"}
                busy={busy === "reopen"}
                onClick={reopenWeek}
              >
                Xác nhận mở lại
              </Btn>
            </div>
          </div>
        </div>,
        document.body,
      ) : null}
    </div>
  );
}
