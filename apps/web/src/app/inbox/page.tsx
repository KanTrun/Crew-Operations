"use client";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
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

const THU_TU = ["cho_duyet", "moi", "duyet", "tu_choi"];

const TEN_NHOM: Record<string, string> = {
  cho_duyet: "Chờ bạn quyết",
  moi: "Mới vào hộp thư",
  duyet: "Đã duyệt",
  tu_choi: "Đã từ chối",
};

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
  const { push } = useToasts();

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setChuQuan(isChuQuan());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Item[] }>("/api/v1/inbox/rang-buoc")
      .then((d) => setItems(d.items ?? []))
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
    extra?: { ca_id?: string; doi_tac_nv_id?: string; ap_dat?: boolean },
  ) {
    setBusy(id);
    try {
      await apiSend(`/api/v1/inbox/rang-buoc/${id}`, { quyet_dinh, ...extra });
      push(
        quyet_dinh === "duyet"
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
    decide(it.id, "duyet");
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--wide">
      <PageHeader
        kicker="Người duyệt · hệ thống không tự chọn"
        title="Hộp thư ràng buộc"
        meta="Khi hai claim mâu thuẫn, người quyết. Không tự chọn hộ."
      />
      {error ? <Alert>{error}</Alert> : null}
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
                  <>
                    {kenhLabel(it.nguon)} · {agentLabel(it.agent)}
                    {it.nv_id ? ` · ${it.nv_id}` : ""}
                    {it.rang_buoc?.tuan_id ? ` · Tuần ${it.rang_buoc.tuan_id}` : ""}
                    {it.rang_buoc?.loai
                      ? ` · ràng buộc ${rangBuocLabel(it.rang_buoc.loai).toLowerCase()}`
                      : ""}
                    {it.rang_buoc?.thu ? ` · ${thuLabel(it.rang_buoc.thu)}` : ""}
                    {it.rang_buoc?.start && it.rang_buoc?.end
                      ? ` · ${it.rang_buoc.start}–${it.rang_buoc.end}`
                      : it.rang_buoc?.khung
                      ? ` ${khungLabel(it.rang_buoc.khung).toLowerCase()}`
                      : ""}
                    {it.rang_buoc?.ca_id ? ` · Ca ${it.rang_buoc.ca_id}` : ""}
                    {it.rang_buoc?.doi_tac ? ` · Đối tác: ${it.rang_buoc.doi_tac}` : ""}
                    {it.created_at ? ` · ${formatLuc(it.created_at)}` : ""}
                    {it.noi_dung_goc ? ` · gốc: ${safeText(it.noi_dung_goc).slice(0, 80)}` : ""}
                    {it.hieu_luc?.ghi ? ` · ${it.hieu_luc.ghi}` : ""}
                  </>
                }
                side={
                  <>
                    <StatusChip tone={inboxTone(it.trang_thai)}>{inboxLabel(it.trang_thai)}</StatusChip>
                    <StatusChip>{kenhLabel(it.nguon)}</StatusChip>
                    <StatusChip>{yDinhLabel(it.y_dinh)}</StatusChip>
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
                      <Btn
                        variant="primary"
                        busy={busy === it.id}
                        busyLabel="Đang ghi quyết định…"
                        onClick={() => handleDuyet(it)}
                      >
                        Duyệt ràng buộc
                      </Btn>
                      <Btn variant="danger" disabled={busy === it.id} onClick={() => decide(it.id, "tu_choi")}>
                        Từ chối
                      </Btn>
                    </>
                  ) : undefined
                }
              />
            ))}
          </Group>
        ))}

      {swapModalItem ? (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-[var(--nq-panel-bg,#222)] border-2 border-[var(--nq-copper)] p-6 max-w-md w-full shadow-2xl rounded">
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
        </div>
      ) : null}

      {showReopenModal ? (
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
        </div>
      ) : null}
    </div>
  );
}
