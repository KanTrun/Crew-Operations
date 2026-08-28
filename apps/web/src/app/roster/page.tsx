"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { nvTenHienThi, safeText, viError, viTriLabel } from "../../lib/present";
import { getToken, lifeLabel, roleLabel } from "../../lib/session";
import {
  Alert,
  Btn,
  Hint,
  Loading,
  Notice,
  PageHeader,
  StatusChip,
  TechnicalDrawer,
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
  1: "Thứ Hai",
  2: "Thứ Ba",
  3: "Thứ Tư",
  4: "Thứ Năm",
  5: "Thứ Sáu",
  6: "Thứ Bảy",
  7: "Chủ Nhật",
};

const THU_SHORT: Record<number, string> = {
  1: "T2",
  2: "T3",
  3: "T4",
  4: "T5",
  5: "T6",
  6: "T7",
  7: "CN",
};

function dayKey(c: RosterData["ca"][number]): string {
  if (c.ngay_offset != null) return THU_SHORT[c.ngay_offset] ?? `N${c.ngay_offset}`;
  if (c.ngay) return c.ngay;
  return "?";
}

function dayTitle(key: string): string {
  const entry = Object.entries(THU_SHORT).find(([, short]) => short === key);
  if (entry) return THU_LABEL[Number(entry[0])] ?? key;
  return key;
}

function groupByDay(ca: RosterData["ca"]) {
  const map: Record<string, RosterData["ca"]> = {};
  for (const c of ca) {
    (map[dayKey(c)] ??= []).push(c);
  }
  return map;
}

const DAY_ORDER = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

export default function RosterPage() {
  const [data, setData] = useState<RosterData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [tuan, setTuan] = useState("2026-W34");
  const [life, setLife] = useState("");
  const [lifeBusy, setLifeBusy] = useState(false);
  const [pinBusy, setPinBusy] = useState(false);

  const load = useCallback(
    (week: string) => {
      fetch(`${API}/api/v1/lich-tuan?tuan=${week}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
        .then(async (r) => {
          if (!r.ok) throw new Error("roster_failed");
          return r.json() as Promise<RosterData>;
        })
        .then(setData)
        .catch(() => setError("Không tải được lịch từ API."));
    },
    [token],
  );

  useEffect(() => {
    const t = sessionStorage.getItem("nq_token");
    const r = sessionStorage.getItem("nq_role");
    setToken(t);
    setRole(r);
    if (t) {
      apiGet<{ trang_thai?: string }>("/api/v1/lich/lifecycle")
        .then((d) => setLife(safeText(d.trang_thai, "")))
        .catch(() => setLife(""));
    }
  }, []);

  useEffect(() => {
    load(tuan);
  }, [load, tuan]);

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

  const byDay = data ? groupByDay(data.ca ?? []) : {};
  const days = [
    ...DAY_ORDER.filter((d) => d in byDay),
    ...Object.keys(byDay)
      .filter((d) => !DAY_ORDER.includes(d))
      .sort(),
  ];
  const nvMap = Object.fromEntries((data?.nhan_vien ?? []).map((nv) => [nv.id, nv.ten]));
  const nvName = (id: string) => nvTenHienThi(nvMap[id], id);

  return (
    <div className="nq-page">
      <p className="nq-kicker">Lưới ca · ghim ô</p>
      <h1>Lịch tuần</h1>
      <p className="nq-muted">
        {data ? `${data.tuan_iso} · nguồn quán` : "Đang tải…"}
        {role ? ` · ${roleLabel(role)}` : ""}
        {life ? ` · ${lifeLabel(life)}` : ""}
      </p>
      <p style={{ display: "flex", gap: "0.65rem", alignItems: "center", flexWrap: "wrap", margin: "0.75rem 0 1rem" }}>
        <label className="nq-muted">
          Tuần ISO
          <input
            type="text"
            value={tuan}
            onChange={(e) => setTuan(e.target.value)}
            style={{
              marginLeft: "0.4rem",
              background: "var(--nq-surface)",
              border: "1px solid var(--nq-line)",
              color: "var(--nq-ink)",
              padding: "0.3rem 0.5rem",
              fontFamily: "var(--nq-font-mono)",
              fontSize: "0.85rem",
              borderRadius: 2,
              width: 100,
            }}
          />
        </label>
        {canWrite && NEXT[life] ? (
          <button disabled={lifeBusy} onClick={advanceLife} type="button">
            {lifeBusy ? "Đang xử lý…" : `Chuyển sang ${lifeLabel(NEXT[life])}`}
          </button>
        ) : null}
      </p>

      {error && (
        <p role="alert" style={{ color: "var(--nq-danger)", marginBottom: "1rem" }}>
          {error}
        </p>
      )}

      {!canWrite && (
        <p className="nq-muted" style={{ border: "1px solid var(--nq-line)", padding: "0.5rem 0.75rem" }}>
          Chỉ xem. Quản lý hoặc chủ quán mới ghim được ô.
        </p>
      )}

      {data && days.length > 0 ? (
        <>
          <div className="nq-roster-wrap">
            <table className="nq-roster-table">
              <caption className="nq-roster-caption">
                Lưới ca tuần {safeText(data.tuan_iso, tuan)}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Khung giờ</th>
                  {days.map((d) => (
                    <th scope="col" key={d}>
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
                        const assigned: string[] = shift ? (data.phan_cong?.[shift.id] ?? []) : [];
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
                                      {(data.nhan_vien ?? [])
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
                          </ul>
                        ) : (
                          <span style={{ color: "var(--nq-line)" }}>—</span>
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
