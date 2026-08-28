"use client";

import { useCallback, useEffect, useState } from "react";
import { Alert, AuthGate, Loading } from "../../ui/kit";
import { canEdit } from "../../lib/session";

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
  vai_tro?: string;
};

type LichData = {
  nguon?: string;
  adr?: string;
  tuan_iso?: string;
  trang_thai?: string;
  ca?: Shift[];
  nhan_vien?: NhanVien[];
  phan_cong?: Record<string, string[]>;
  pin?: Record<string, string[]>;
};

const VI_TRI_LABEL: Record<string, string> = {
  barista: "Pha chế",
  thu_ngan: "Thu ngân",
  phuc_vu: "Phục vụ",
  chay_ban: "Chạy bàn",
};

function viTriLabel(vt?: string): string {
  if (!vt) return "Chung";
  return VI_TRI_LABEL[vt] ?? vt;
}

function dayTitle(d: string): string {
  const m: Record<string, string> = {
    T2: "Thứ Hai",
    T3: "Thứ Ba",
    T4: "Thứ Tư",
    T5: "Thứ Năm",
    T6: "Thứ Sáu",
    T7: "Thứ Bảy",
    CN: "Chủ Nhật",
  };
  return m[d] ?? d;
}

function nvTenHienThi(ten?: string, id?: string): string {
  return ten || id || "—";
}

export default function RosterPage() {
  const [token, setToken] = useState("");
  const [role, setRole] = useState("nhan_vien");
  const [data, setData] = useState<LichData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pinBusy, setPinBusy] = useState(false);

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

  const loadLich = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/lich-tuan`, { headers: authHeader() });
      if (!res.ok) throw new Error("fetch_failed");
      const json = (await res.json()) as LichData;
      setData(json);
    } catch {
      setError("Không tải được lịch tuần.");
    } finally {
      setLoading(false);
    }
  }, [authHeader]);

  useEffect(() => {
    if (token) loadLich();
  }, [token, loadLich]);

  async function handlePin(caId: string, nvId: string, ghim: boolean) {
    setPinBusy(true);
    try {
      const res = await fetch(`${API}/api/v1/lich-tuan/pin`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ ca_id: caId, nv_id: nvId, ghim }),
      });
      if (!res.ok) throw new Error("pin_failed");
      await loadLich();
    } catch {
      setError("Không cập nhật được ghim.");
    } finally {
      setPinBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  const canWrite = canEdit(role);
  const days = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];
  const shifts = data?.ca ?? [];

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
      <header className="mb-8 ops-animate-in">
        <p className="nq-kicker">Vận hành tuần</p>
        <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tighter text-[var(--nq-copper)] mb-2">
          Lịch tuần
        </h1>
        <p className="text-[var(--nq-dim)] font-mono text-sm">
          Lịch phân công ca theo tuần · {data?.tuan_iso ?? "2026-W01"}
        </p>
      </header>

      {error ? <Alert kind="err">{error}</Alert> : null}
      {loading ? <Loading skeleton="table" rows={3}>Đang tải lịch tuần…</Loading> : null}

      {!loading && shifts.length > 0 ? (
        <div className="nq-table-wrap">
          <table className="nq-table">
            <thead>
              <tr>
                <th scope="col">Khung</th>
                {days.map((d) => (
                  <th key={d} scope="col">
                    <span className="nq-roster-day-full">{dayTitle(d)}</span>
                    <span className="nq-roster-day-short">{d}</span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(["sang", "chieu", "toi"] as const).map((khung) => {
                const label =
                  khung === "sang" ? "Sáng 07–12" : khung === "chieu" ? "Chiều 12–17" : "Tối 17–22";
                return (
                  <tr key={khung}>
                    <th scope="row" className="nq-roster-row-label">
                      {label}
                    </th>
                    {days.map((d) => {
                      const shift = (byDay[d] ?? []).find((c) => (c.khung ?? "") === khung);
                      const assigned: string[] = shift ? (data?.phan_cong?.[shift.id] ?? []) : [];
                      return (
                        <td key={d}>
                          {shift ? (
                            <div className="nq-roster-cell">
                              <p className="nq-roster-role">{viTriLabel(shift.vi_tri)}</p>
                              <ul className="nq-roster-people">
                                {assigned.map((nv_id) => (
                                  <li key={nv_id} className="nq-roster-nv">
                                    <span className="nq-roster-nv-name">{nvName(nv_id)}</span>
                                    {canWrite ? (
                                      <button
                                        type="button"
                                        className="nq-roster-unpin"
                                        disabled={pinBusy}
                                        onClick={() => handlePin(shift.id, nv_id, false)}
                                        aria-label={`Bỏ ${nvName(nv_id)} khỏi ${label} ${dayTitle(d)}`}
                                      >
                                        ×
                                      </button>
                                    ) : null}
                                  </li>
                                ))}
                                {assigned.length === 0 ? (
                                  <li className="nq-roster-empty">Chưa xếp người</li>
                                ) : null}
                              </ul>
                              {canWrite ? (
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
                                          {nvTenHienThi(nv.ten, nv.id)}
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
            Tuần này chưa có ca nào. Chuyển lịch sang trạng thái xếp ca để hệ thống sinh lưới.
          </p>
        )
      )}
    </div>
  );
}
