"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, AuthGate, Loading } from "../../ui/kit";
import { canEdit, lifeLabel } from "../../lib/session";
import { apiSend } from "../../lib/api";
import { viError } from "../../lib/present";

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
  nhap: { label: "Gửi duyệt →", next: "cho_duyet" },
  cho_duyet: { label: "Duyệt ✓", next: "da_duyet" },
  da_duyet: { label: "Công bố 📢", next: "da_cong_bo" },
  da_cong_bo: { label: "Đóng tuần ✗", next: "da_dong" },
  da_dong: { label: "", next: "" },
};

const TRANG_THAI_COLOR: Record<string, string> = {
  nhap: "default",
  cho_duyet: "warn",
  da_duyet: "ok",
  da_cong_bo: "ok",
  da_dong: "default",
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

function viTriLabel(vt?: string): string {
  if (!vt) return "Chung";
  return VI_TRI_LABEL[vt] ?? vt;
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
  const [soTuan, setSoTuan] = useState<number>(1);
  const [baseWeek, setBaseWeek] = useState(currentISOWeek());
  const [activeWeekIndex, setActiveWeekIndex] = useState<number>(0);
  const [data, setData] = useState<LichData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pinBusy, setPinBusy] = useState(false);
  const [lifecycleBusy, setLifecycleBusy] = useState(false);
  const [lifecycleMsg, setLifecycleMsg] = useState<string | null>(null);

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    const r = sessionStorage.getItem("nq_role");
    if (t) setToken(t);
    if (r) setRole(r);
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

  const byDay: Record<string, Shift[]> = {};
  for (const d of days) byDay[d] = [];
  for (const s of shifts) {
    if (byDay[s.thu]) byDay[s.thu].push(s);
  }

  function nvName(id: string): string {
    const found = (data?.nhan_vien ?? []).find((x) => x.id === id);
    return found ? found.ten : id;
  }

  return (
    <div className="nq-page">
      <header className="mb-6 ops-animate-in">
        <p className="nq-kicker">Vận hành tuần</p>
        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter text-[var(--nq-copper)] mb-3">
          Lịch tuần
        </h1>

        {/* Chu kỳ xếp lịch (1, 2, 3, 4 tuần) */}
        {canWrite && (
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
        <div className="nq-item mb-6 flex items-center gap-4 flex-wrap">
          <span className="text-sm text-[var(--nq-dim)]">Trạng thái:</span>
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
      )}

      {error ? <Alert kind="err">{error}</Alert> : null}
      {loading ? <Loading skeleton="table" rows={3}>Đang tải lịch tuần…</Loading> : null}

      {!loading && shifts.length > 0 ? (
        <div className="nq-table-wrap">
          <table className="nq-table">
            <thead>
              <tr>
                <th scope="col">Khung</th>
                {days.map((d, i) => (
                  <th key={d} scope="col">
                    <span className="block font-bold">{dayTitle(d)}</span>
                    <span className="block font-mono text-xs text-[var(--nq-dim)]">
                      {dayDate(monday, dayOffsets[i])}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(["sang", "chieu", "toi"] as const).map((khung) => {
                const label =
                  khung === "sang"
                    ? "Sáng 07–12"
                    : khung === "chieu"
                    ? "Chiều 12–17"
                    : "Tối 17–22";
                return (
                  <tr key={khung}>
                    <th scope="row" className="nq-roster-row-label">
                      {label}
                    </th>
                    {days.map((d) => {
                      const shift = (byDay[d] ?? []).find(
                        (c) => (c.khung ?? "") === khung,
                      );
                      const assigned: string[] = shift
                        ? data?.phan_cong?.[shift.id] ?? []
                        : [];
                      return (
                        <td key={d}>
                          {shift ? (
                            <div className="nq-roster-cell">
                              <p className="nq-roster-role">
                                {viTriLabel(shift.vi_tri)}
                              </p>
                              <ul className="nq-roster-people">
                                {assigned.map((nv_id) => (
                                  <li key={nv_id} className="nq-roster-nv">
                                    <span className="nq-roster-nv-name">
                                      {nvName(nv_id)}
                                    </span>
                                    {canWrite && trangThai !== "da_dong" ? (
                                      <button
                                        type="button"
                                        className="nq-roster-unpin"
                                        disabled={pinBusy}
                                        onClick={() => handlePin(shift.id, nv_id, false)}
                                        aria-label={`Bỏ ${nvName(nv_id)} khỏi ca`}
                                      >
                                        ×
                                      </button>
                                    ) : null}
                                  </li>
                                ))}
                                {assigned.length === 0 ? (
                                  <li className="nq-roster-empty">
                                    Chưa xếp người
                                  </li>
                                ) : null}
                              </ul>
                              {canWrite && trangThai !== "da_dong" ? (
                                <div className="nq-roster-add">
                                  <select
                                    defaultValue=""
                                    disabled={pinBusy}
                                    aria-label={`Thêm người vào ${label} ${dayTitle(d)}`}
                                    onChange={(e) => {
                                      if (e.target.value) {
                                        handlePin(shift.id, e.target.value, true);
                                        e.target.value = "";
                                      }
                                    }}
                                  >
                                    <option value="">Thêm người…</option>
                                    {(data?.nhan_vien ?? [])
                                      .filter((nv) => !assigned.includes(nv.id))
                                      .map((nv) => (
                                        <option key={nv.id} value={nv.id}>
                                          {nv.ten || nv.id}
                                        </option>
                                      ))}
                                  </select>
                                </div>
                              ) : null}
                            </div>
                          ) : (
                            <span className="nq-muted">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        !loading &&
        !error && (
          <p className="nq-muted">
            Tuần {currentDisplayWeek} chưa có ca nào.
          </p>
        )
      )}
    </div>
  );
}
