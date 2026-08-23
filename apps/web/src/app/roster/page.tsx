"use client";

import { useCallback, useEffect, useState } from "react";
import { API, apiSend } from "../../lib/api";
import { lifeLabel, roleLabel } from "../../lib/session";
import {
  Alert,
  Btn,
  Loading,
  Notice,
  PageHeader,
  StatusChip,
  Toolbar,
} from "../../ui/kit";

type RosterData = {
  tuan_iso: string;
  nguon: string;
  nhan_vien: Array<{ id: string; ten: string }>;
  ca: Array<{
    id: string;
    ngay?: string;
    ngay_offset?: number;
    bat_dau: string;
    ket_thuc: string;
    vi_tri: string;
    khung?: string;
  }>;
  phan_cong: Record<string, string[]>;
};

const THU_LABEL: Record<number, string> = {
  1: "T2",
  2: "T3",
  3: "T4",
  4: "T5",
  5: "T6",
  6: "T7",
  7: "CN",
};

function dayKey(c: RosterData["ca"][number]): string {
  if (c.ngay_offset != null) return THU_LABEL[c.ngay_offset] ?? `N${c.ngay_offset}`;
  if (c.ngay) return c.ngay;
  return "?";
}

function groupByDay(ca: RosterData["ca"]) {
  const map: Record<string, RosterData["ca"]> = {};
  for (const c of ca) {
    (map[dayKey(c)] ??= []).push(c);
  }
  return map;
}

export default function RosterPage() {
  const [data, setData] = useState<RosterData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [tuan, setTuan] = useState("2026-W34");
  const [life, setLife] = useState("");
  const [lifeBusy, setLifeBusy] = useState(false);
  const [pinBusy, setPinBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = useCallback(
    (week: string) => {
      setLoading(true);
      fetch(`${API}/api/v1/lich-tuan?tuan=${week}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
        .then(async (r) => {
          if (!r.ok) throw new Error("roster_failed");
          return r.json() as Promise<RosterData>;
        })
        .then(setData)
        .catch(() => setError("Không tải được lịch từ API."))
        .finally(() => setLoading(false));
    },
    [token],
  );

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    const r = sessionStorage.getItem("nq_role");
    setToken(t);
    setRole(r);
    if (t) {
      fetch(`${API}/api/v1/lich/lifecycle`, { headers: { Authorization: `Bearer ${t}` } })
        .then((x) => x.json())
        .then((d) => setLife(d.trang_thai ?? ""));
    }
  }, []);

  useEffect(() => {
    if (token) load(tuan);
  }, [load, tuan, token]);

  const canWrite = role === "quan_ly" || role === "chu_quan";

  const NEXT: Record<string, string> = {
    nhap: "dang_giai",
    dang_giai: "cho_duyet",
    cho_duyet: "da_cong_bo",
    da_cong_bo: "da_dong",
  };

  async function advanceLife() {
    const to = NEXT[life];
    if (!to || !token) return;
    setLifeBusy(true);
    try {
      const d = await apiSend<{ trang_thai: string }>("/api/v1/lich/lifecycle", { to });
      setLife(d.trang_thai);
      load(tuan);
    } catch {
      setError("Không chuyển được trạng thái lịch. Cần quyền quản lý.");
    } finally {
      setLifeBusy(false);
    }
  }

  async function handlePin(ca_id: string, nv_id: string, pinned: boolean) {
    if (!token || !canWrite) return;
    setPinBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/lich-tuan/pin`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ ca_id, nv_id, pinned }),
      });
      if (!r.ok) throw new Error("pin_failed");
      load(tuan);
    } catch {
      setError("Không thể cập nhật pin.");
    } finally {
      setPinBusy(false);
    }
  }

  const byDay = data ? groupByDay(data.ca) : {};
  const days = Object.keys(byDay).sort();
  const nvMap = Object.fromEntries((data?.nhan_vien ?? []).map((nv) => [nv.id, nv.ten]));

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Lưới ca · ghim ô"
        title="Lịch tuần"
        meta={
          <>
            {data ? `${data.tuan_iso} · nguồn quán` : "Đang tải…"}
            {role ? ` · ${roleLabel(role)}` : ""}
            {life ? (
              <>
                {" · "}
                <StatusChip tone={life === "da_cong_bo" ? "ok" : "default"}>{lifeLabel(life)}</StatusChip>
              </>
            ) : null}
          </>
        }
      />

      <Toolbar>
        <label className="nq-muted">
          Tuần ISO
          <input type="text" value={tuan} onChange={(e) => setTuan(e.target.value)} style={{ width: 100 }} />
        </label>
        {canWrite && NEXT[life] ? (
          <Btn variant="ghost" disabled={lifeBusy} onClick={advanceLife}>
            {lifeBusy ? "Đang xử lý…" : `Chuyển sang ${lifeLabel(NEXT[life])}`}
          </Btn>
        ) : null}
      </Toolbar>

      {error ? <Alert>{error}</Alert> : null}
      {!canWrite ? <Notice>Chỉ xem. Quản lý hoặc chủ quán mới ghim được ô.</Notice> : null}
      {loading ? <Loading skeleton="list">Đang tải lịch…</Loading> : null}

      {data && days.length > 0 ? (
        <div className="nq-roster-wrap">
          <table className="nq-roster-table">
            <thead>
              <tr>
                <th>Ca / Vị trí</th>
                {days.map((d) => (
                  <th key={d}>{d}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(["sang", "chieu", "toi"] as const).map((khung) => {
                const label =
                  khung === "sang" ? "Sáng 07–12" : khung === "chieu" ? "Chiều 12–17" : "Tối 17–22";
                return (
                  <tr key={khung}>
                    <td className="nq-roster-row-label">{label}</td>
                    {days.map((d) => {
                      const shift = (byDay[d] ?? []).find((c) => (c.khung ?? "") === khung);
                      const assigned: string[] = shift ? (data.phan_cong[shift.id] ?? []) : [];
                      return (
                        <td key={d}>
                          {shift ? (
                            <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                              <li className="nq-roster-shift-meta">{shift.vi_tri}</li>
                              {assigned.map((nv_id) => (
                                <li key={nv_id} className="nq-roster-nv">
                                  <span>{nvMap[nv_id] ?? nv_id}</span>
                                  {canWrite ? (
                                    <button
                                      type="button"
                                      className="nq-roster-unpin"
                                      disabled={pinBusy}
                                      onClick={() => handlePin(shift.id, nv_id, false)}
                                      aria-label={`Unpin ${nvMap[nv_id] ?? nv_id}`}
                                    >
                                      ×
                                    </button>
                                  ) : null}
                                </li>
                              ))}
                              {canWrite ? (
                                <li className="nq-roster-add">
                                  <select
                                    defaultValue=""
                                    disabled={pinBusy}
                                    aria-label="Thêm nhân viên"
                                    onChange={(e) => {
                                      if (e.target.value) {
                                        handlePin(shift.id, e.target.value, true);
                                        e.target.value = "";
                                      }
                                    }}
                                  >
                                    <option value="">Thêm nhân viên…</option>
                                    {data.nhan_vien
                                      .filter((nv) => !assigned.includes(nv.id))
                                      .map((nv) => (
                                        <option key={nv.id} value={nv.id}>
                                          {nv.ten}
                                        </option>
                                      ))}
                                  </select>
                                </li>
                              ) : null}
                            </ul>
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
        !loading && !error && <p className="nq-muted">Chưa có dữ liệu lịch.</p>
      )}
    </div>
  );
}
