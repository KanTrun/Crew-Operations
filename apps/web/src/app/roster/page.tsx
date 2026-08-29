"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { matchSearch, uniqueSorted } from "../../lib/list-filters";
import { nvLabel, safeText, viError } from "../../lib/present";
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
import { ListToolbar } from "../../ui/list-filters";

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

const TUAN_RE = /^\d{4}-W\d{2}$/;

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
  const [search, setSearch] = useState("");
  const [personF, setPersonF] = useState("all");

  const load = useCallback((week: string) => {
    if (!TUAN_RE.test(week)) {
      setLoading(false);
      setError("Mã tuần cần dạng năm-Wsố tuần, ví dụ 2026-W34. Sửa lại ô tuần rồi xem tiếp.");
      return;
    }
    setLoading(true);
    setError(null);
    apiGet<RosterData>(`/api/v1/lich-tuan?tuan=${encodeURIComponent(week)}`)
      .then(setData)
      .catch((e) =>
        setError(
          viError(e, {
            doing: "tải được lịch tuần này",
            missing: "Quán chưa có lịch cho tuần này. Chọn tuần khác, hoặc tạo lịch nháp rồi chạy xếp ca.",
          }),
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    const t = getToken();
    setToken(t || null);
    setRole(sessionStorage.getItem("nq_role"));
    if (t) {
      apiGet<{ trang_thai?: string }>("/api/v1/lich/lifecycle")
        .then((d) => setLife(safeText(d.trang_thai, "")))
        .catch(() => setLife("")); // không có trạng thái thì ẩn chip, không báo lỗi to
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
    setError(null);
    try {
      const d = await apiSend<{ trang_thai: string }>("/api/v1/lich/lifecycle", { to });
      setLife(safeText(d.trang_thai, life));
      load(tuan);
    } catch (e) {
      setError(
        viError(e, {
          doing: "chuyển được trạng thái lịch",
          forbidden: "Chỉ quản lý hoặc chủ quán chuyển được trạng thái lịch tuần.",
          conflict: "Trạng thái lịch vừa đổi ở nơi khác. Tải lại trang để xem trạng thái hiện tại.",
        }),
      );
    } finally {
      setLifeBusy(false);
    }
  }

  async function handlePin(ca_id: string, nv_id: string, pinned: boolean) {
    if (!token || !canWrite) return;
    setPinBusy(true);
    setError(null);
    try {
      await apiSend("/api/v1/lich-tuan/pin", { ca_id, nv_id, pinned });
      load(tuan);
    } catch (e) {
      setError(
        viError(e, {
          doing: pinned ? "ghim người vào ca này" : "bỏ ghim người khỏi ca này",
          forbidden: "Chỉ quản lý hoặc chủ quán sửa được lưới ca.",
          missing: "Ca hoặc nhân viên này không còn trong lịch. Tải lại trang rồi thử lại.",
        }),
      );
    } finally {
      setPinBusy(false);
    }
  }

  const byDay = data ? groupByDay(data.ca ?? []) : {};
  const days = Object.keys(byDay).sort();
  const nvMap = Object.fromEntries((data?.nhan_vien ?? []).map((nv) => [nv.id, safeText(nv.ten, "")]));
  const nvName = (id: string) => nvMap[id] || nvLabel(id);

  const personOptions = useMemo(
    () => [
      { value: "all", label: "Mọi người" },
      ...uniqueSorted((data?.nhan_vien ?? []).map((nv) => nv.id)).map((id) => ({ value: id, label: nvName(id) })),
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data],
  );

  const filteredDays = useMemo(() => {
    if (!search && personF === "all") return days;
    return days.filter((d) => {
      const shifts = byDay[d] ?? [];
      return shifts.some((c) => {
        const assigned: string[] = data?.phan_cong?.[c.id] ?? [];
        if (personF !== "all" && !assigned.includes(personF)) return false;
        if (search) {
          const hay = [c.vi_tri, ...assigned.map(nvName)].join(" ");
          if (!matchSearch(hay, search)) return false;
        }
        return true;
      });
    });
  }, [days, byDay, data, search, personF]);

  const filterActive = search.length > 0 || personF !== "all";

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Lưới ca · ghim ô"
        title="Lịch tuần"
        meta="Ai đứng ca nào trong tuần. Ghim người vào ô để giữ chỗ, đổi trạng thái để công bố lịch."
      />

      <Toolbar>
        <label className="nq-muted">
          Tuần
          <input
            type="text"
            value={tuan}
            onChange={(e) => setTuan(e.target.value.trim())}
            style={{ width: 110 }}
            inputMode="text"
          />
        </label>
        <span className="nq-muted" style={{ fontSize: "0.85rem" }}>
          {data ? `Nguồn quán · ${roleLabel(role ?? "")}` : "Đang tải…"}
        </span>
        {life ? (
          <StatusChip tone={life === "da_cong_bo" ? "ok" : "default"}>{lifeLabel(life)}</StatusChip>
        ) : null}
        {canWrite && NEXT[life] ? (
          <Btn variant="ghost" disabled={lifeBusy} onClick={advanceLife}>
            {lifeBusy ? "Đang xử lý…" : `Chuyển sang ${lifeLabel(NEXT[life])}`}
          </Btn>
        ) : null}
      </Toolbar>
      <Hint>Ô tuần theo lịch ISO: bốn số năm, chữ W, hai số tuần. Ví dụ 2026-W34.</Hint>

      {error ? <Alert>{error}</Alert> : null}
      {!canWrite ? <Notice>Bạn chỉ xem. Quản lý hoặc chủ quán mới ghim được người vào ca.</Notice> : null}

      <ListToolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Tìm tên NV, vị trí ca…"
        person={personF}
        onPersonChange={setPersonF}
        personOptions={personOptions}
        shown={filteredDays.length}
        total={days.length}
        filtered={filterActive}
        timeLabel="Ngày"
      />

      {loading ? <Loading skeleton="list">Đang tải lịch tuần…</Loading> : null}

      {data && filteredDays.length > 0 ? (
        <>
          <div className="nq-roster-wrap">
            <table className="nq-roster-table">
              <caption className="nq-muted" style={{ captionSide: "top", textAlign: "left", padding: "0.5rem 0.6rem" }}>
                Lưới ca tuần {safeText(data.tuan_iso, tuan)}
              </caption>
              <thead>
                <tr>
                  <th scope="col">Ca / Vị trí</th>
                  {filteredDays.map((d) => (
                    <th scope="col" key={d}>
                      {d}
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
                      {filteredDays.map((d) => {
                        const shift = (byDay[d] ?? []).find((c) => (c.khung ?? "") === khung);
                        const assigned: string[] = shift ? (data.phan_cong?.[shift.id] ?? []) : [];
                        return (
                          <td key={d}>
                            {shift ? (
                              <ul style={{ listStyle: "none", margin: 0, padding: 0 }}>
                                <li className="nq-roster-shift-meta">{safeText(shift.vi_tri, "Chưa ghi vị trí")}</li>
                                {assigned.map((nv_id) => (
                                  <li key={nv_id} className="nq-roster-nv">
                                    <span>{nvName(nv_id)}</span>
                                    {canWrite ? (
                                      <button
                                        type="button"
                                        className="nq-roster-unpin"
                                        disabled={pinBusy}
                                        onClick={() => handlePin(shift.id, nv_id, false)}
                                        aria-label={`Bỏ ${nvName(nv_id)} khỏi ${label} ${d}`}
                                      >
                                        ×
                                      </button>
                                    ) : null}
                                  </li>
                                ))}
                                {assigned.length === 0 ? (
                                  <li className="nq-roster-shift-meta">Chưa có người</li>
                                ) : null}
                                {canWrite ? (
                                  <li className="nq-roster-add">
                                    <select
                                      defaultValue=""
                                      disabled={pinBusy}
                                      aria-label={`Thêm người vào ${label} ${d}`}
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
                                            {safeText(nv.ten, nvLabel(nv.id))}
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
          <TechnicalDrawer
            lines={[
              `Mã tuần ISO: ${safeText(data.tuan_iso, tuan)}`,
              `Nguồn dữ liệu: ${safeText(data.nguon, "quán")}`,
              `Số ca trong tuần: ${(data.ca ?? []).length}`,
            ]}
          />
        </>
      ) : (
        !loading && !error && (
          <p className="nq-muted">
            Tuần này chưa có ca nào. Chuyển lịch sang trạng thái xếp ca để hệ thống sinh lưới.
          </p>
        )
      )}
    </div>
  );
}
