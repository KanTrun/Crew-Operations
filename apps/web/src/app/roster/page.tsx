"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, AuthGate, Loading, Summary } from "../../ui/kit";
import { canEdit, getNvId, getRole, getToken, isManager, lifeLabel } from "../../lib/session";
import { apiSend } from "../../lib/api";
import { matchSearch } from "../../lib/list-filters";
import { viError } from "../../lib/present";
import type { KhungGio } from "../../lib/roster";
import { shiftRowLabel } from "../../lib/roster";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";
import { KhungConfigPanel } from "./KhungConfigPanel";
import { RosterGrid } from "./RosterGrid";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Shift = {
  id: string;
  thu: string;
  khung: "sang" | "chieu" | "toi" | string;
  bat_dau?: string;
  ket_thuc?: string;
  vi_tri?: string;
};

type NhanVien = {
  id: string;
  ten: string;
};

type LichData = {
  nguon?: string;
  tuan_iso?: string;
  so_tuan?: number;
  danh_sach_tuan?: string[];
  trang_thai?: string;
  ca?: Shift[];
  nhan_vien?: NhanVien[];
  phan_cong?: Record<string, string[]>;
  khung_gio?: KhungGio;
};

const VI_TRI_LABEL: Record<string, string> = {
  barista: "Pha chế",
  pha_che: "Pha chế",
  thu_ngan: "Thu ngân",
  phuc_vu: "Phục vụ",
  chay_ban: "Chạy bàn",
  kho: "Kho",
};

const TRANG_THAI_NEXT: Record<string, { label: string; next: string }> = {
  may_sinh: { label: "Chuyển sang nháp", next: "nhap" },
  nhap: { label: "Gửi duyệt", next: "cho_duyet" },
  cho_duyet: { label: "Duyệt lịch", next: "da_duyet" },
  da_duyet: { label: "Công bố cho nhân viên", next: "da_cong_bo" },
  da_cong_bo: { label: "Đóng tuần", next: "da_dong" },
  da_dong: { label: "", next: "" },
};

const TRANG_THAI_COLOR: Record<string, string> = {
  may_sinh: "warn",
  nhap: "default",
  cho_duyet: "warn",
  da_duyet: "ok",
  da_cong_bo: "ok",
  da_dong: "default",
};

function viTriLabel(vt?: string): string {
  if (!vt) return "Chung";
  return VI_TRI_LABEL[vt] ?? vt;
}

const DEFAULT_KHUNG_GIO: KhungGio = {
  sang: { bat_dau: "07:00", ket_thuc: "12:00" },
  chieu: { bat_dau: "12:00", ket_thuc: "17:00" },
  toi: { bat_dau: "17:00", ket_thuc: "22:00" },
};

function isoWeekToMonday(week: string): Date {
  const m = week.match(/^(\d{4})-W(\d{2})$/);
  if (!m) return new Date();
  const year = parseInt(m[1]);
  const wk = parseInt(m[2]);
  const jan4 = new Date(year, 0, 4);
  const mon = new Date(jan4);
  mon.setDate(jan4.getDate() - ((jan4.getDay() + 6) % 7) + (wk - 1) * 7);
  return mon;
}

function shiftWeek(week: string, delta: number): string {
  const mon = isoWeekToMonday(week);
  mon.setDate(mon.getDate() + delta * 7);
  const tmp = new Date(mon);
  tmp.setHours(0, 0, 0, 0);
  tmp.setDate(tmp.getDate() + 3 - ((tmp.getDay() + 6) % 7));
  const week1 = new Date(tmp.getFullYear(), 0, 4);
  const wkNum = 1 + Math.round(((tmp.getTime() - week1.getTime()) / 86400000 - 3 + ((week1.getDay() + 6) % 7)) / 7);
  return `${tmp.getFullYear()}-W${String(wkNum).padStart(2, "0")}`;
}

function dayDate(monday: Date, offset: number): string {
  const d = new Date(monday);
  d.setDate(d.getDate() + offset);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function dayTitle(d: string): string {
  const m: Record<string, string> = {
    T2: "Thứ 2",
    T3: "Thứ 3",
    T4: "Thứ 4",
    T5: "Thứ 5",
    T6: "Thứ 6",
    T7: "Thứ 7",
    CN: "Chủ Nhật",
  };
  return m[d] ?? d;
}

function currentISOWeek(): string {
  const now = new Date();
  const tmp = new Date(now);
  tmp.setHours(0, 0, 0, 0);
  tmp.setDate(tmp.getDate() + 3 - ((tmp.getDay() + 6) % 7));
  const week1 = new Date(tmp.getFullYear(), 0, 4);
  const wk = 1 + Math.round(((tmp.getTime() - week1.getTime()) / 86400000 - 3 + ((week1.getDay() + 6) % 7)) / 7);
  return `${tmp.getFullYear()}-W${String(wk).padStart(2, "0")}`;
}

export default function RosterPage() {
  const [token, setToken] = useState("");
  const [role, setRole] = useState("nhan_vien");
  const [currentNvId, setCurrentNvId] = useState("");
  const [viewMode, setViewMode] = useState<"my_shifts" | "all">("all");
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const [soTuan, setSoTuan] = useState<number>(1);
  const [baseWeek, setBaseWeek] = useState(currentISOWeek());
  const [activeWeekIndex, setActiveWeekIndex] = useState<number>(0);
  const [data, setData] = useState<LichData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pinBusy, setPinBusy] = useState(false);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const [lifecycleMsg, setLifecycleMsg] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [filterKhung, setFilterKhung] = useState("all");
  const [filterViTri, setFilterViTri] = useState("all");

  useEffect(() => {
    const t = getToken();
    const r = getRole();
    const nv = getNvId();
    if (t) setToken(t);
    if (r) {
      setRole(r);
      setViewMode(isManager(r) ? "all" : "my_shifts");
    }
    if (nv) setCurrentNvId(nv);
  }, []);

  const authHeader = useCallback(
    () => ({ Authorization: `Bearer ${token}` }),
    [token],
  );

  const loadLich = useCallback(
    async (week: string, weeksCount: number) => {
      setLoading(true);
      setError(null);
      setLifecycleMsg(null);
      try {
        const res = await fetch(`${API}/api/v1/lich-tuan?tuan=${week}&so_tuan=${weeksCount}`, {
          headers: authHeader(),
        });
        if (!res.ok) throw new Error("fetch_failed");
        setData((await res.json()) as LichData);
      } catch {
        setError("Không tải được lịch tuần.");
      } finally {
        setLoading(false);
      }
    },
    [authHeader],
  );

  useEffect(() => {
    if (token) void loadLich(baseWeek, soTuan);
  }, [token, loadLich, baseWeek, soTuan]);

  async function handlePin(caId: string, nvId: string, ghim: boolean) {
    setPinBusy(true);
    try {
      const res = await fetch(`${API}/api/v1/lich-tuan/pin`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ ca_id: caId, nv_id: nvId, ghim }),
      });
      if (!res.ok) throw new Error("pin_failed");
      await loadLich(baseWeek, soTuan);
    } catch {
      setError("Không cập nhật được ghim.");
    } finally {
      setPinBusy(false);
    }
  }

  async function handleLifecycle(nextState: string, weekIso: string) {
    if (!nextState) return;
    setLifecycleBusy(true);
    setLifecycleMsg(null);
    try {
      await apiSend(
        "/api/v1/lich-tuan/lifecycle",
        { trang_thai: nextState, tuan_iso: weekIso },
        "PATCH",
      );
      setLifecycleMsg("Đã cập nhật trạng thái lịch.");
      await loadLich(baseWeek, soTuan);
    } catch (e) {
      setError(viError(e, { doing: "cập nhật trạng thái lịch" }));
    } finally {
      setLifecycleBusy(false);
    }
  }

  function navigateBlock(delta: number) {
    const next = shiftWeek(baseWeek, delta * soTuan);
    setBaseWeek(next);
    setActiveWeekIndex(0);
  }

  const shiftsEarly = data?.ca ?? [];
  const nhanVienEarly = data?.nhan_vien ?? [];

  const viTriOptions = useMemo(() => {
    const set = new Set<string>();
    for (const s of shiftsEarly) {
      if (s.vi_tri) set.add(s.vi_tri);
    }
    return [
      { value: "all", label: "Mọi vị trí" },
      ...[...set].sort().map((v) => ({ value: v, label: viTriLabel(v) })),
    ];
  }, [shiftsEarly]);

  const matchCell = useCallback(
    (assigned: string[], shift: { khung?: string; vi_tri?: string; thu?: string }) => {
      if (filterKhung !== "all" && shift.khung !== filterKhung) return false;
      if (filterViTri !== "all" && (shift.vi_tri ?? "") !== filterViTri) return false;
      if (!search.trim()) return true;
      const hay = [
        ...assigned.map((id) => nhanVienEarly.find((x) => x.id === id)?.ten ?? id),
        viTriLabel(shift.vi_tri),
        shift.khung,
        shift.thu,
      ].join(" ");
      return matchSearch(hay, search);
    },
    [filterKhung, filterViTri, search, nhanVienEarly],
  );

  const rosterStats = useMemo(() => {
    const phanCongEarly = data?.phan_cong ?? {};
    let slots = 0;
    let staffed = 0;
    let thin = 0;
    for (const s of shiftsEarly) {
      slots += 1;
      const n = (phanCongEarly[s.id] ?? []).length;
      if (n > 0) staffed += 1;
      if (n > 0 && n < 2) thin += 1;
    }
    return { slots, staffed, thin };
  }, [shiftsEarly, data?.phan_cong]);

  if (!token) return <AuthGate />;

  const canWrite = canEdit(role);
  const days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
  const dayOffsets = [0, 1, 2, 3, 4, 5, 6];
  const shifts = data?.ca ?? [];
  const weekList = data?.danh_sach_tuan && data.danh_sach_tuan.length > 0
    ? data.danh_sach_tuan
    : [baseWeek];

  const currentDisplayWeek = weekList[activeWeekIndex] ?? baseWeek;
  const monday = isoWeekToMonday(currentDisplayWeek);
  const trangThai = data?.trang_thai ?? "nhap";
  const nextAction = TRANG_THAI_NEXT[trangThai];
  const khungGio = data?.khung_gio ?? DEFAULT_KHUNG_GIO;
  const phanCong = data?.phan_cong ?? {};

  const khungOptions = [
    { value: "all", label: "Mọi khung" },
    { value: "sang", label: "Ca sáng" },
    { value: "chieu", label: "Ca chiều" },
    { value: "toi", label: "Ca tối" },
  ];

  const filteredActive = filterKhung !== "all" || filterViTri !== "all" || search.trim().length > 0;

  const dayLabelRows = days.map((d, i) => ({
    title: dayTitle(d),
    date: dayDate(monday, dayOffsets[i]),
  }));

  const byDay: Record<string, Shift[]> = {};
  for (const d of days) byDay[d] = [];
  const offsetToDay: Record<number, string> = { 1: "T2", 2: "T3", 3: "T4", 4: "T5", 5: "T6", 6: "T7", 7: "CN" };

  for (const s of shifts) {
    const rawOffset = (s as unknown as { ngay_offset?: number }).ngay_offset;
    const dayKey = s.thu || (rawOffset ? offsetToDay[Number(rawOffset)] : "") || "T2";
    if (byDay[dayKey]) byDay[dayKey].push({ ...s, thu: dayKey });
  }

  function nvName(id: string): string {
    const found = (data?.nhan_vien ?? []).find((x) => x.id === id);
    return found ? found.ten : id;
  }

  // Resolve employee ID from session (e.g. nv_03 for Minh, nv_01 for Lan...)
  const myEmployee = (data?.nhan_vien ?? []).find(
    (nv) =>
      nv.id === currentNvId ||
      nv.id === `nv_${currentNvId}` ||
      (currentNvId && nv.ten.toLowerCase().includes(currentNvId.toLowerCase()))
  );
  const targetNvId = myEmployee ? myEmployee.id : currentNvId || "nv_03";

  // Calculate shifts assigned to current employee
  const myAssignedDays: { day: string; offset: number; dateStr: string; shifts: Array<{ shift: Shift; coworkers: string[] }> }[] = [];
  let totalMyShifts = 0;

  days.forEach((d, i) => {
    const dayShifts = byDay[d] ?? [];
    const matched: Array<{ shift: Shift; coworkers: string[] }> = [];
    dayShifts.forEach((s) => {
      const assigned = data?.phan_cong?.[s.id] ?? [];
      if (assigned.includes(targetNvId)) {
        matched.push({ shift: s, coworkers: assigned.filter((id) => id !== targetNvId) });
      }
    });

    if (matched.length > 0) {
      totalMyShifts += matched.length;
      myAssignedDays.push({
        day: d,
        offset: dayOffsets[i],
        dateStr: dayDate(monday, dayOffsets[i]),
        shifts: matched,
      });
    }
  });


  return (
    <div className="nq-page nq-page--wide">
      <header className="mb-6 ops-animate-in">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
          <div>
            <p className="nq-kicker">Vận hành tuần</p>
            <h1 className="text-3xl md:text-4xl font-black uppercase tracking-tighter text-[var(--nq-copper)]">
              {viewMode === "my_shifts" ? "Lịch Đi Làm Của Tôi" : "Lịch Toàn Quán (Full Ca)"}
            </h1>
          </div>

          {/* Mode Switcher: My Shifts vs Full Roster */}
          <div className="flex items-center gap-1.5 p-1 bg-neutral-900/80 border border-neutral-800 rounded-lg">
            <button
              type="button"
              onClick={() => setViewMode("my_shifts")}
              className={`px-3 py-1.5 text-xs font-bold rounded transition-all ${
                viewMode === "my_shifts"
                  ? "bg-amber-600 text-neutral-950 shadow"
                  : "text-neutral-400 hover:text-neutral-200"
              }`}
            >
              Lịch của tôi ({totalMyShifts} ca)
            </button>
            <button
              type="button"
              onClick={() => setViewMode("all")}
              className={`px-3 py-1.5 text-xs font-bold rounded transition-all ${
                viewMode === "all"
                  ? "bg-amber-600 text-neutral-950 shadow"
                  : "text-neutral-400 hover:text-neutral-200"
              }`}
            >
              Toàn quán
            </button>
          </div>
        </div>

        {/* Chu kỳ xếp lịch (1, 2, 3, 4 tuần) - Chỉ hiển thị cho Quản lý */}
        {canWrite && viewMode === "all" && (
          <div className="flex items-center gap-2 mb-4 flex-wrap">
            <span className="text-xs uppercase tracking-wider text-[var(--nq-dim)] font-bold">
              Chu kỳ xếp ca:
            </span>
            {[1, 2, 3, 4].map((num) => (
              <button
                key={num}
                type="button"
                className={`px-3 py-1 text-xs font-bold rounded ${
                  soTuan === num
                    ? "bg-[var(--nq-copper)] text-[var(--nq-bg)] shadow"
                    : "nq-btn-outline"
                }`}
                onClick={() => {
                  setSoTuan(num);
                  setActiveWeekIndex(0);
                }}
              >
                {num} Tuần ({num * 21} ca)
              </button>
            ))}
          </div>
        )}

        {/* Điều hướng mốc tuần */}
        <div className="flex items-center gap-3 flex-wrap">
          <button
            type="button"
            className="nq-btn-outline px-3 py-1 text-sm"
            onClick={() => navigateBlock(-1)}
            disabled={loading}
          >
            ← Trước
          </button>
          <span className="font-mono text-base font-bold text-[var(--nq-copper)] min-w-[90px] text-center">
            {baseWeek}
            {soTuan > 1 ? ` → ${weekList[weekList.length - 1]}` : ""}
          </span>
          <button
            type="button"
            className="nq-btn-outline px-3 py-1 text-sm"
            onClick={() => navigateBlock(1)}
            disabled={loading}
          >
            Sau →
          </button>
          <button
            type="button"
            className="nq-btn-outline px-3 py-1 text-sm"
            onClick={() => {
              setBaseWeek(currentISOWeek());
              setActiveWeekIndex(0);
            }}
            disabled={loading || baseWeek === currentISOWeek()}
          >
            Tuần này
          </button>
          <span className="text-[var(--nq-dim)] font-mono text-xs">
            {dayDate(monday, 0)} — {dayDate(monday, 6)} ({currentDisplayWeek})
          </span>
        </div>

        {/* Tab chuyển tuần khi xếp > 1 tuần */}
        {soTuan > 1 && (
          <div className="flex items-center gap-2 mt-4 pt-3 border-t border-[var(--nq-border)] overflow-x-auto">
            <span className="text-xs text-[var(--nq-dim)]">Xem tuần:</span>
            {weekList.map((wk, idx) => {
              const wkMon = isoWeekToMonday(wk);
              return (
                <button
                  key={wk}
                  type="button"
                  className={`px-3 py-1.5 text-xs font-mono rounded transition-colors ${
                    activeWeekIndex === idx
                      ? "bg-[var(--nq-copper)] text-[var(--nq-bg)] font-bold"
                      : "nq-btn-outline"
                  }`}
                  onClick={() => setActiveWeekIndex(idx)}
                >
                  Tuần {idx + 1}: {wk} ({dayDate(wkMon, 0)} - {dayDate(wkMon, 6)})
                </button>
              );
            })}
          </div>
        )}
      </header>

      {/* Trạng thái & nút duyệt của quản lý */}
      {canWrite && (
        <div className="nq-item mb-6 flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
          <div className="flex items-center gap-3 flex-wrap">
            <span className="text-sm text-[var(--nq-dim)]">Trạng thái lịch:</span>
            <span
              className={`nq-chip nq-chip--${
                TRANG_THAI_COLOR[trangThai] ?? "default"
              } font-mono text-xs`}
            >
              {lifeLabel(trangThai)}
            </span>
            {nextAction?.next && (
              <button
                type="button"
                className="nq-btn px-3 py-1 text-sm"
                disabled={lifecycleBusy}
                onClick={() => void handleLifecycle(nextAction.next, currentDisplayWeek)}
              >
                {lifecycleBusy ? "Đang lưu…" : nextAction.label}
              </button>
            )}
            {lifecycleMsg && (
              <span className="text-sm text-[var(--nq-ok)]">{lifecycleMsg}</span>
            )}
          </div>
          {trangThai === "may_sinh" ? (
            <p className="text-xs text-[var(--nq-ink-muted)] max-w-2xl">
              Lịch do hệ thống tự xếp. Quản lý rà soát, chỉnh nhân sự nếu cần, rồi bấm <strong>Chuyển sang nháp</strong> để bắt đầu quy trình duyệt.
            </p>
          ) : null}
        </div>
      )}

      {error ? <Alert kind="err">{error}</Alert> : null}
      {loading ? <Loading skeleton="table" rows={3}>Đang tải lịch tuần…</Loading> : null}

      {/* ========================================================================= */}
      {/* 1. CHẾ ĐỘ NHÂN VIÊN: CHỈ HIỆN NHỮNG NGÀY ĐI LÀM CỦA CÁ NHÂN             */}
      {/* ========================================================================= */}
      {!loading && viewMode === "my_shifts" && (
        <div className="space-y-4">
          {/* Summary Card */}
          <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-700/40 flex items-center justify-between flex-wrap gap-3">
            <div>
              <h3 className="text-sm font-bold text-emerald-300">
                Tuần {currentDisplayWeek} của bạn
              </h3>
              <p className="text-xs text-neutral-300 mt-0.5">
                Bạn có <strong>{myAssignedDays.length} ngày đi làm</strong> với tổng cộng <strong>{totalMyShifts} ca làm việc</strong> (~{totalMyShifts * 5} giờ công).
              </p>
            </div>
            <button
              type="button"
              onClick={() => setViewMode("all")}
              className="text-xs font-mono px-3 py-1.5 rounded bg-emerald-900/60 text-emerald-200 border border-emerald-600 hover:bg-emerald-800"
            >
              Xem lịch toàn quán →
            </button>
          </div>

          {/* List of Working Days */}
          {myAssignedDays.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
              {myAssignedDays.map((item) => (
                <div
                  key={item.day}
                  className="p-4 rounded-lg bg-neutral-900/80 border border-emerald-800/40 shadow-sm hover:border-emerald-600 transition-all space-y-3"
                >
                  <div className="flex justify-between items-center pb-2 border-b border-neutral-800">
                    <span className="font-bold text-base text-emerald-300">
                      {dayTitle(item.day)}
                    </span>
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-neutral-800 text-neutral-300">
                      {item.dateStr}
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {item.shifts.map(({ shift, coworkers }, sIdx) => (
                        <div key={sIdx} className="p-2.5 rounded bg-neutral-950/60 border border-neutral-800 space-y-1.5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-bold text-neutral-200">
                              {shiftRowLabel(shift, shift.khung ?? "", khungGio)}
                            </span>
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-900/70 text-emerald-300 font-bold border border-emerald-700">
                              {viTriLabel(shift.vi_tri)}
                            </span>
                          </div>

                          {coworkers.length > 0 && (
                            <p className="text-[11px] text-neutral-400">
                              Cùng ca: {coworkers.map((id) => nvName(id)).join(", ")}
                            </p>
                          )}
                        </div>
                      ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-8 text-center bg-neutral-900/40 rounded-lg border border-neutral-800 space-y-2">
              <p className="text-neutral-400 text-sm">Tuần này bạn chưa có ca làm việc nào được phân công.</p>
              <button
                type="button"
                onClick={() => setViewMode("all")}
                className="text-xs font-bold text-amber-400 hover:underline"
              >
                Nhấn vào đây để xem toàn bộ lịch quán
              </button>
            </div>
          )}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 2. CHẾ ĐỘ QUẢN LÝ: HIỆN FULL 7 NGÀY & CLICK VÀO NGÀY ĐỂ XEM CHI TIẾT TỪNG CA */}
      {/* ========================================================================= */}
      {!loading && viewMode === "all" && shifts.length > 0 && (
        <div className="space-y-4">
          <Summary
            cells={[
              { n: rosterStats.slots, k: "Ô ca tuần" },
              { n: rosterStats.staffed, k: "Đã có người", tone: "ok" },
              { n: rosterStats.thin, k: "Mỏng (<2 NV)", tone: rosterStats.thin > 0 ? "warn" : "default" },
              { n: lifeLabel(trangThai), k: "Trạng thái lịch" },
            ]}
          />

          {canWrite ? (
            <KhungConfigPanel
              template={khungGio}
              disabled={trangThai === "da_dong" || lifecycleBusy}
              onSaved={() => void loadLich(baseWeek, soTuan)}
            />
          ) : null}

          <ListToolbar
            search={search}
            onSearchChange={setSearch}
            searchPlaceholder="Tìm tên nhân viên, vị trí…"
            status={filterKhung}
            onStatusChange={setFilterKhung}
            statusOptions={khungOptions}
            statusLabel="Khung ca"
            person={filterViTri}
            onPersonChange={setFilterViTri}
            personOptions={viTriOptions}
            personLabel="Vị trí"
            shown={rosterStats.slots}
            total={rosterStats.slots}
            filtered={filteredActive}
          />

          <p className="nq-muted text-xs">
            Bấm <strong>tiêu đề ngày</strong> hoặc <strong>ô ca</strong> để mở chi tiết và ghim nhân sự.
          </p>

          <RosterGrid
            byDay={byDay}
            phanCong={phanCong}
            khungGio={khungGio}
            dayLabels={dayLabelRows}
            spotlightDay={selectedDay}
            filterKhung={filterKhung}
            filterViTri={filterViTri}
            searchNeedle={search}
            viTriLabel={viTriLabel}
            nvName={nvName}
            matchCell={matchCell}
            onSelectDay={setSelectedDay}
          />

          {filteredActive && shifts.every((s) => !matchCell(phanCong[s.id] ?? [], s)) ? (
            <FilteredEmpty
              onClear={() => {
                setSearch("");
                setFilterKhung("all");
                setFilterViTri("all");
              }}
            />
          ) : null}
        </div>
      )}

      {/* ========================================================================= */}
      {/* 3. MODAL CHI TIẾT NGÀY: HIỂN THỊ ĐẦY ĐỦ NHÂN VIÊN TỪNG CA KHI QUẢN LÝ CLICK */}
      {/* ========================================================================= */}
      {selectedDay && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm">
          <div className="bg-neutral-900 border border-neutral-700 rounded-xl max-w-2xl w-full p-6 space-y-5 shadow-2xl overflow-y-auto max-h-[90vh]">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-neutral-800 pb-3">
              <div>
                <h3 className="text-lg font-bold text-amber-400">
                  Chi tiết phân ca · {dayTitle(selectedDay)} (
                  {dayDate(monday, dayOffsets[days.indexOf(selectedDay)])})
                </h3>
                <p className="text-xs text-neutral-400">
                  Tuần {currentDisplayWeek} • Quản lý nhân sự theo từng ca trong ngày
                </p>
              </div>

              <button
                type="button"
                onClick={() => setSelectedDay(null)}
                className="px-3 py-1 text-xs font-bold uppercase tracking-widest text-neutral-400 hover:text-amber-400"
              >
                Đóng
              </button>
            </div>

            {/* Shift Details (Sang, Chieu, Toi) */}
            <div className="space-y-4">
              {(["sang", "chieu", "toi"] as const).map((khung) => {
                const shift = (byDay[selectedDay] ?? []).find((c) => c.khung === khung);
                const assigned = shift ? data?.phan_cong?.[shift.id] ?? [] : [];
                const khungLabelText = shiftRowLabel(shift, khung, khungGio);

                return (
                  <div
                    key={khung}
                    className="p-4 rounded-lg bg-neutral-950 border border-neutral-800 space-y-3"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-sm text-neutral-200">
                          {khungLabelText}
                        </span>
                        {shift && (
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 uppercase">
                            Vị trí: {viTriLabel(shift.vi_tri)}
                          </span>
                        )}
                      </div>

                      <span
                        className={`text-xs font-mono px-2 py-0.5 rounded ${
                          assigned.length >= 2
                            ? "bg-emerald-900/60 text-emerald-300 border border-emerald-700"
                            : assigned.length === 1
                            ? "bg-amber-900/60 text-amber-300 border border-amber-700"
                            : "bg-rose-900/60 text-rose-300 border border-rose-700"
                        }`}
                      >
                        {assigned.length > 0 ? `${assigned.length} Nhân viên` : "Thiếu người"}
                      </span>
                    </div>

                    {/* Assigned Staff Pills */}
                    {assigned.length > 0 ? (
                      <div className="flex flex-wrap gap-2">
                        {assigned.map((nv_id) => (
                          <span
                            key={nv_id}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-neutral-900 border border-neutral-700 text-xs text-neutral-100 font-medium"
                          >
                            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                            {nvName(nv_id)}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-neutral-500 italic">Chưa có nhân viên nào trong ca này.</p>
                    )}

                    {/* Quick Add Staff Dropdown */}
                    {canWrite && trangThai !== "da_dong" && shift && (
                      <div className="pt-2 border-t border-neutral-900 flex items-center gap-2">
                        <span className="text-xs text-neutral-400">Thêm nhanh:</span>
                        <select
                          defaultValue=""
                          disabled={pinBusy}
                          className="text-xs bg-neutral-900 border border-neutral-700 text-neutral-200 rounded px-2 py-1"
                          onChange={(e) => {
                            if (e.target.value) {
                              handlePin(shift.id, e.target.value, true);
                              e.target.value = "";
                            }
                          }}
                        >
                          <option value="">Chọn nhân viên vào ca…</option>
                          {(data?.nhan_vien ?? [])
                            .filter((nv) => !assigned.includes(nv.id))
                            .map((nv) => (
                              <option key={nv.id} value={nv.id}>
                                + {nv.ten || nv.id}
                              </option>
                            ))}
                        </select>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Navigation Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-neutral-800">
              <button
                type="button"
                onClick={() => {
                  const currentIdx = days.indexOf(selectedDay);
                  const prevIdx = (currentIdx - 1 + days.length) % days.length;
                  setSelectedDay(days[prevIdx]);
                }}
                className="px-3 py-1.5 text-xs font-bold rounded bg-neutral-800 text-neutral-200 hover:bg-neutral-700"
              >
                ← {dayTitle(days[(days.indexOf(selectedDay) - 1 + days.length) % days.length])}
              </button>

              <button
                type="button"
                onClick={() => setSelectedDay(null)}
                className="px-4 py-1.5 text-xs font-bold rounded bg-amber-600 hover:bg-amber-500 text-neutral-950"
              >
                Đóng
              </button>

              <button
                type="button"
                onClick={() => {
                  const currentIdx = days.indexOf(selectedDay);
                  const nextIdx = (currentIdx + 1) % days.length;
                  setSelectedDay(days[nextIdx]);
                }}
                className="px-3 py-1.5 text-xs font-bold rounded bg-neutral-800 text-neutral-200 hover:bg-neutral-700"
              >
                {dayTitle(days[(days.indexOf(selectedDay) + 1) % days.length])} →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

