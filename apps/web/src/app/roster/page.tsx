"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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

const cellStyle: React.CSSProperties = {
  border: "1px solid var(--nq-line)",
  padding: "0.5rem 0.6rem",
  verticalAlign: "top",
  minWidth: 120,
};

const headerCellStyle: React.CSSProperties = {
  ...cellStyle,
  background: "var(--nq-bg-elevated)",
  fontFamily: "var(--nq-font-mono)",
  fontSize: "0.78rem",
  color: "var(--nq-ink-muted)",
  fontWeight: 600,
  textAlign: "left",
};

export default function RosterPage() {
  const [data, setData] = useState<RosterData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [role, setRole] = useState<string | null>(null);
  const [tuan, setTuan] = useState("2026-W34");
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
  }, []);

  useEffect(() => {
    load(tuan);
  }, [load, tuan]);

  const canWrite = role === "quan_ly" || role === "chu_quan";

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
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: "1.5rem" }}>
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          gap: "1rem",
          borderBottom: "1px solid var(--nq-line)",
          paddingBottom: "1rem",
          marginBottom: "1.25rem",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ fontFamily: "var(--nq-font-display)", fontWeight: 400, margin: 0, fontSize: "1.8rem" }}>
            Lịch tuần
          </h1>
          <p style={{ margin: "0.3rem 0 0", color: "var(--nq-ink-muted)", fontSize: "0.85rem" }}>
            {data ? `${data.tuan_iso} · nguồn: ${data.nguon}` : "Đang tải…"}
            {role ? ` · vai trò: ${role}` : " · ẩn danh (chỉ đọc)"}
          </p>
        </div>
        <div style={{ display: "flex", gap: "0.75rem", alignItems: "center" }}>
          <label style={{ fontSize: "0.85rem", color: "var(--nq-ink-muted)" }}>
            Tuần ISO:
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
          <Link href="/" style={{ minHeight: 44, display: "inline-flex", alignItems: "center", fontSize: "0.9rem" }}>
            Về trang chủ
          </Link>
        </div>
      </header>

      {error && (
        <p role="alert" style={{ color: "var(--nq-danger)", marginBottom: "1rem" }}>
          {error}
        </p>
      )}

      {!canWrite && (
        <p
          style={{
            fontSize: "0.8rem",
            color: "var(--nq-ink-muted)",
            border: "1px solid var(--nq-line)",
            padding: "0.5rem 0.75rem",
            marginBottom: "1rem",
            borderRadius: 2,
          }}
        >
          Chỉ xem — đăng nhập với vai trò <strong>quanly</strong> hoặc <strong>chu</strong> để pin/unpin.
        </p>
      )}

      {data && days.length > 0 ? (
        <div style={{ overflowX: "auto" }}>
          <table
            style={{
              borderCollapse: "collapse",
              width: "100%",
              fontFamily: "var(--nq-font-body)",
              fontSize: "0.875rem",
            }}
          >
            <thead>
              <tr>
                <th style={headerCellStyle}>Ca / Vị trí</th>
                {days.map((d) => (
                  <th key={d} style={headerCellStyle}>
                    {d}
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
                  <td
                    style={{
                      ...cellStyle,
                      fontFamily: "var(--nq-font-mono)",
                      fontSize: "0.78rem",
                      color: "var(--nq-ink-muted)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {label}
                  </td>
                  {days.map((d) => {
                    const shift = (byDay[d] ?? []).find(
                      (c) => (c.khung ?? "") === khung,
                    );
                    const assigned: string[] = shift
                      ? (data.phan_cong[shift.id] ?? [])
                      : [];
                    return (
                      <td key={d} style={cellStyle}>
                        {shift ? (
                          <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                            <li
                              style={{
                                fontSize: "0.7rem",
                                color: "var(--nq-ink-muted)",
                                marginBottom: "0.25rem",
                              }}
                            >
                              {shift.vi_tri}
                            </li>
                            {assigned.map((nv_id) => (
                              <li
                                key={nv_id}
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "space-between",
                                  gap: "0.4rem",
                                  padding: "0.2rem 0",
                                  borderBottom: "1px solid var(--nq-line)",
                                }}
                              >
                                <span style={{ fontSize: "0.82rem" }}>
                                  {nvMap[nv_id] ?? nv_id}
                                </span>
                                {canWrite && (
                                  <button
                                    disabled={pinBusy}
                                    onClick={() => handlePin(shift.id, nv_id, false)}
                                    title="Unpin"
                                    aria-label={`Unpin ${nvMap[nv_id] ?? nv_id}`}
                                    style={{
                                      background: "none",
                                      border: "none",
                                      cursor: "pointer",
                                      color: "var(--nq-accent)",
                                      fontSize: "0.75rem",
                                      padding: "0 0.2rem",
                                    }}
                                  >
                                    ×
                                  </button>
                                )}
                              </li>
                            ))}
                            {canWrite && (
                              <li style={{ paddingTop: "0.3rem" }}>
                                <select
                                  defaultValue=""
                                  disabled={pinBusy}
                                  onChange={(e) => {
                                    if (e.target.value) {
                                      handlePin(shift.id, e.target.value, true);
                                      e.target.value = "";
                                    }
                                  }}
                                  style={{
                                    background: "var(--nq-surface)",
                                    border: "1px solid var(--nq-line)",
                                    color: "var(--nq-ink)",
                                    fontSize: "0.75rem",
                                    padding: "0.2rem 0.3rem",
                                    borderRadius: 2,
                                    width: "100%",
                                  }}
                                  aria-label="Thêm nhân viên"
                                >
                                  <option value="">+ pin NV…</option>
                                  {data.nhan_vien
                                    .filter((nv) => !assigned.includes(nv.id))
                                    .map((nv) => (
                                      <option key={nv.id} value={nv.id}>
                                        {nv.ten}
                                      </option>
                                    ))}
                                </select>
                              </li>
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
        !error && <p style={{ color: "var(--nq-ink-muted)" }}>Đang tải lịch…</p>
      )}
    </main>
  );
}
