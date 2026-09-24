"use client";

import type { KhungGio, RosterShift } from "../../lib/roster";
import { initialsOf, khungOrder, rosterCellSummary, shiftRowLabel } from "../../lib/roster";
import { Icon } from "../../ui/icons";

const KHUNGS = ["sang", "chieu", "toi"] as const;
const DAYS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"] as const;

type Props = {
  byDay: Record<string, RosterShift[]>;
  phanCong: Record<string, string[]>;
  khungGio?: KhungGio;
  dayLabels: { title: string; date: string }[];
  spotlightDay: string | null;
  filterKhung: string;
  filterViTri: string;
  searchNeedle: string;
  viTriLabel: (vt?: string) => string;
  nvName: (id: string) => string;
  matchCell: (assigned: string[], shift: RosterShift) => boolean;
  onSelectDay: (day: string) => void;
  nvStatusMap?: Record<string, string>;
  pins?: Array<{ ca_id: string; nv_id: string }>;
};

export function RosterGrid({
  byDay,
  phanCong,
  khungGio,
  dayLabels,
  spotlightDay,
  filterKhung,
  onSelectDay,
  viTriLabel,
  nvName,
  matchCell,
  nvStatusMap,
  pins = [],
}: Props) {
  const visibleKhungs = filterKhung === "all" ? KHUNGS : KHUNGS.filter((k) => k === filterKhung);

  return (
    <div className="nq-roster-wrap">
      <table className="nq-roster-table nq-roster-table--compact">
        <caption className="nq-roster-caption">
          Lưới tuần — bấm ô hoặc tiêu đề ngày để mở chi tiết và chỉnh nhân sự
        </caption>
        <thead>
          <tr>
            <th scope="col" className="nq-roster-corner">
              Khung
            </th>
            {DAYS.map((d, i) => {
              const dayShifts = byDay[d] ?? [];
              let total = 0;
              dayShifts.forEach((s) => {
                total += (phanCong[s.id] ?? []).length;
              });
              const lit = spotlightDay === d;
              return (
                <th
                  key={d}
                  scope="col"
                  className={`nq-roster-day-head ${lit ? "nq-roster-day-head--spot" : ""}`}
                >
                  <button
                    type="button"
                    className="nq-roster-day-btn"
                    onClick={() => onSelectDay(d)}
                    aria-pressed={lit}
                  >
                    <span className="nq-roster-day-full">{dayLabels[i]?.title}</span>
                    <span className="nq-roster-day-short">{d}</span>
                    <span className="nq-roster-day-date">{dayLabels[i]?.date}</span>
                    <span className="nq-roster-day-meta">{total} NV</span>
                  </button>
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {visibleKhungs.map((khung, rowIdx) => {
            const sample = DAYS.map((d) => (byDay[d] ?? []).find((c) => c.khung === khung)).find(Boolean);
            const rowLabel = shiftRowLabel(sample, khung, khungGio);
            return (
              <tr
                key={khung}
                className={`nq-roster-band nq-roster-band--${khung} ${rowIdx % 2 === 0 ? "nq-roster-band--even" : "nq-roster-band--odd"}`}
              >
                <th scope="row" className="nq-roster-row-label">
                  {rowLabel}
                </th>
                {DAYS.map((d) => {
                  const shifts = (byDay[d] ?? []).filter((c) => c.khung === khung);
                  const assigned = [...new Set(shifts.flatMap((shift) => phanCong[shift.id] ?? []))];
                  const visibleShifts = shifts.filter((shift) => matchCell(phanCong[shift.id] ?? [], shift));
                  const dimmed = shifts.length > 0 && visibleShifts.length === 0;
                  const lit = spotlightDay === d;
                  const roles = [...new Set(shifts.map((shift) => viTriLabel(shift.vi_tri)).filter(Boolean))];
                  const roleLabel = roles.length > 0 ? roles.join(" · ") : "Nhiều vị trí";
                  const required = shifts.reduce(
                    (sum, shift) => sum + Number(shift.so_nguoi_toi_thieu ?? 1),
                    0,
                  );
                  const summary = rosterCellSummary(assigned.length, roleLabel, assigned.length < required);
                  const hasUnconfirmed = assigned.some((id) => nvStatusMap?.[id] === "chua_xac_nhan");
                  const pinnedIds = new Set(
                    pins
                      .filter((pin) => shifts.some((shift) => shift.id === pin.ca_id))
                      .map((pin) => pin.nv_id),
                  );

                  return (
                    <td
                      key={d}
                      className={`nq-roster-slot ${lit ? "nq-roster-slot--spot" : ""}`}
                      data-dimmed={dimmed ? "1" : undefined}
                    >
                      {shifts.length > 0 ? (
                        <button
                          type="button"
                          className={`nq-roster-slot-btn nq-roster-slot-btn--${summary.tone}`}
                          data-unconfirmed={hasUnconfirmed ? "1" : undefined}
                          onClick={() => onSelectDay(d)}
                          aria-label={`${dayLabels[DAYS.indexOf(d)]?.title} ${rowLabel}: ${summary.countLabel}, ${roleLabel}${hasUnconfirmed ? " (Có nhân sự chưa xác nhận lịch)" : ""}`}
                        >
                          <span className="nq-roster-slot-head">
                            <span className="nq-roster-slot-count">
                              {assigned.length >= required
                                ? `Đủ ${assigned.length}/${required}`
                                : `Thiếu ${required - assigned.length} · ${assigned.length}/${required}`}
                            </span>
                            {hasUnconfirmed && (
                              <span className="nq-roster-slot-flag" title="Có nhân sự chưa xác nhận lịch">
                                <Icon name="warn" size={11} />
                              </span>
                            )}
                          </span>
                          {/* Viết tắt thay vì tên đầy đủ: giữ đủ số người trong ô,
                              tên đầy đủ nằm ở `title` và bảng chi tiết ngày. */}
                          <span className="nq-roster-slot-crew">
                            {assigned.length > 0 ? (
                              <>
                                {assigned.slice(0, 4).map((id) => (
                                  <span
                                    key={id}
                                    className="nq-avatar"
                                    data-pinned={pinnedIds.has(id) ? "1" : undefined}
                                    title={`${nvName(id)}${pinnedIds.has(id) ? " · ghim ca" : ""}`}
                                  >
                                    {initialsOf(nvName(id))}
                                  </span>
                                ))}
                                {assigned.length > 4 && (
                                  <span
                                    className="nq-avatar nq-avatar--more"
                                    title={assigned.map((id) => nvName(id)).join(", ")}
                                  >
                                    +{assigned.length - 4}
                                  </span>
                                )}
                              </>
                            ) : (
                              <span className="nq-roster-slot-none">Chưa có nhân viên</span>
                            )}
                          </span>
                        </button>
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
  );
}

export { DAYS as ROSTER_DAYS, KHUNGS as ROSTER_KHUNGS, khungOrder };
