"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { API, apiSend } from "../../lib/api";
import { matchSearch, uniqueSorted } from "../../lib/list-filters";
import { nvTenHienThi, viTriLabel } from "../../lib/present";
import { getToken, lifeLabel, roleLabel } from "../../lib/session";
import {
  Alert,
  Btn,
  Empty,
  inputClassName,
  Loading,
  Notice,
  OpsCard,
  PageHeader,
  StatusChip,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

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

const KHUNG_OPTS = [
  { value: "all", label: "Mọi ca" },
  { value: "sang", label: "Sáng" },
  { value: "chieu", label: "Chiều" },
  { value: "toi", label: "Tối" },
];

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

function dayTitle(d: string): string {
  return d;
}

function nvName(nvMap: Record<string, string>, id: string): string {
  return nvMap[id] ?? id;
}

export default function RosterPage() {
  const [data, setData] = useState<RosterData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [token, setToken] = useState("");
  const [role, setRole] = useState("");
  const [tuan, setTuan] = useState("2026-W34");
  const [life, setLife] = useState("");
  const [lifeBusy, setLifeBusy] = useState(false);
  const [pinBusy, setPinBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [personF, setPersonF] = useState("all");
  const [khungF, setKhungF] = useState("all");

  const load = useCallback(
    (week: string) => {
      if (!getToken()) return;
      setLoading(true);
      fetch(`${API}/api/v1/lich-tuan?tuan=${week}`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      })
        .then(async (r) => {
          if (!r.ok) throw new Error("roster_failed");
          return r.json() as Promise<RosterData>;
        })
        .then((d) => {
          setData(d);
          setError(null);
        })
        .catch(() => setError("Không tải được lịch từ API."))
        .finally(() => setLoading(false));
    },
    [],
  );

  useEffect(() => {
    setToken(getToken());
    setRole(sessionStorage.getItem("nq_role") ?? "");
    const t = getToken();
    if (t) {
      fetch(`${API}/api/v1/lich/lifecycle`, { headers: { Authorization: `Bearer ${t}` } })
        .then((x) => x.json())
        .then((d) => setLife(d.trang_thai ?? ""));
    } else setLoading(false);
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

  const nvMap = useMemo(
    () => Object.fromEntries((data?.nhan_vien ?? []).map((nv) => [nv.id, nv.ten])),
    [data],
  );

  const personOptions = useMemo(
    () => [
      { value: "all", label: "Mọi người" },
      ...(data?.nhan_vien ?? []).map((nv) => ({ value: nv.id, label: nvTenHienThi(nv.ten, nv.id) })),
    ],
    [data],
  );

  const byDay = data ? groupByDay(data.ca) : {};
  const days = Object.keys(byDay).sort();

  const visibleKhung = (["sang", "chieu", "toi"] as const).filter((k) => khungF === "all" || khungF === k);

  const cellMatches = useCallback(
    (assigned: string[], viTri: string, khung: string) => {
      const hay = [viTri, khung, ...assigned.map((id) => nvName(nvMap, id))].join(" ");
      if (!matchSearch(hay, search)) return false;
      if (personF !== "all" && !assigned.includes(personF)) return false;
      return true;
    },
    [nvMap, personF, search],
  );

  const visibleCellCount = useMemo(() => {
    if (!data) return 0;
    let n = 0;
    for (const khung of visibleKhung) {
      for (const d of days) {
        const shift = (byDay[d] ?? []).find((c) => (c.khung ?? "") === khung);
        if (!shift) continue;
        const assigned = data.phan_cong[shift.id] ?? [];
        if (cellMatches(assigned, shift.vi_tri, khung)) n += 1;
      }
    }
    return n;
  }, [byDay, cellMatches, data, days, visibleKhung]);

  const totalCells = visibleKhung.length * days.length;
  const filterActive = search.length > 0 || personF !== "all" || khungF !== "all";

  function clearFilters() {
    setSearch("");
    setPersonF("all");
    setKhungF("all");
  }

  const khungLabel = (khung: string) =>
    khung === "sang" ? "Sáng 07–12" : khung === "chieu" ? "Chiều 12–17" : "Tối 17–22";

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
                {" "}
                · <StatusChip>{lifeLabel(life)}</StatusChip>
              </>
            ) : null}
          </>
        }
      />

      {error ? <Alert>{error}</Alert> : null}
      {!canWrite ? <Notice>Chỉ xem. Quản lý hoặc chủ quán mới ghim được ô.</Notice> : null}

      <OpsCard eyebrow="Điều khiển" title="Tuần & bộ lọc lưới">
        <div className="nq-roster-controls">
          <label className="nq-filter-field">
            <span className="nq-filter-label">Tuần ISO</span>
            <input className={inputClassName} type="text" value={tuan} onChange={(e) => setTuan(e.target.value)} />
          </label>
          {canWrite && NEXT[life] ? (
            <Btn variant="primary" disabled={lifeBusy} onClick={advanceLife}>
              {lifeBusy ? "Đang xử lý…" : `Chuyển sang ${lifeLabel(NEXT[life])}`}
            </Btn>
          ) : null}
        </div>
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm tên NV, vị trí, khung ca…"
          person={personF}
          onPersonChange={setPersonF}
          personOptions={personOptions}
          status={khungF}
          onStatusChange={setKhungF}
          statusOptions={KHUNG_OPTS}
          statusLabel="Khung ca"
          shown={visibleCellCount}
          total={totalCells}
          filtered={filterActive}
        />
      </OpsCard>

      <OpsCard eyebrow="Lưới" title="Phân công theo ngày" count={visibleCellCount} countLabel="ô khớp">
        {loading ? <Loading skeleton="card">Đang tải lịch tuần…</Loading> : null}
        {!loading && data && days.length === 0 ? (
          <Empty title="Chưa có ca">Tuần này chưa có ca. Chuyển lịch sang trạng thái xếp ca để sinh lưới.</Empty>
        ) : null}
        {!loading && data && days.length > 0 && visibleCellCount === 0 && filterActive ? (
          <FilteredEmpty onClear={clearFilters} />
        ) : null}

        {data && days.length > 0 ? (
          <div className="nq-roster-wrap">
            <table className="nq-roster-table">
              <caption className="nq-roster-caption">Lịch tuần {data.tuan_iso}</caption>
              <thead>
                <tr>
                  <th scope="col">Ca / Vị trí</th>
                  {days.map((d) => (
                    <th key={d} scope="col">
                      <span className="nq-roster-day-full">{dayTitle(d)}</span>
                      <span className="nq-roster-day-short">{d}</span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {visibleKhung.map((khung) => (
                  <tr key={khung}>
                    <th scope="row" className="nq-roster-row-label">
                      {khungLabel(khung)}
                    </th>
                    {days.map((d) => {
                      const shift = (byDay[d] ?? []).find((c) => (c.khung ?? "") === khung);
                      const assigned: string[] = shift ? (data.phan_cong?.[shift.id] ?? []) : [];
                      const show = shift && cellMatches(assigned, shift.vi_tri, khung);
                      return (
                        <td key={d} data-dimmed={filterActive && !show ? "1" : "0"}>
                          {shift && show ? (
                            <div className="nq-roster-cell">
                              <p className="nq-roster-role">{viTriLabel(shift.vi_tri)}</p>
                              <ul className="nq-roster-people">
                                {assigned.map((nv_id) => (
                                  <li
                                    key={nv_id}
                                    className={`nq-roster-nv ${personF !== "all" && nv_id === personF ? "nq-roster-nv--hit" : ""}`}
                                  >
                                    <span className="nq-roster-nv-name">{nvName(nvMap, nv_id)}</span>
                                    {canWrite ? (
                                      <button
                                        type="button"
                                        className="nq-roster-unpin"
                                        disabled={pinBusy}
                                        onClick={() => handlePin(shift.id, nv_id, false)}
                                        aria-label={`Bỏ ${nvName(nvMap, nv_id)} khỏi ${khungLabel(khung)} ${dayTitle(d)}`}
                                      >
                                        ×
                                      </button>
                                    ) : null}
                                  </li>
                                ))}
                                {assigned.length === 0 ? <li className="nq-roster-empty">Chưa xếp người</li> : null}
                              </ul>
                              {canWrite ? (
                                <div className="nq-roster-add">
                                  <select
                                    className="nq-select"
                                    defaultValue=""
                                    disabled={pinBusy}
                                    aria-label={`Thêm người vào ${khungLabel(khung)} ${dayTitle(d)}`}
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
                          ) : shift && filterActive ? (
                            <span className="nq-muted">—</span>
                          ) : shift ? (
                            <div className="nq-roster-cell">
                              <p className="nq-roster-role">{viTriLabel(shift.vi_tri)}</p>
                              <ul className="nq-roster-people">
                                {assigned.map((nv_id) => (
                                  <li key={nv_id} className="nq-roster-nv">
                                    <span className="nq-roster-nv-name">{nvName(nvMap, nv_id)}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          ) : (
                            <span className="nq-muted">—</span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </OpsCard>
    </div>
  );
}
