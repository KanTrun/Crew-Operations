"use client";

import type { KhungGio, RosterShift } from "../../lib/roster";
import { khungOrder, rosterCellSummary, shiftRowLabel } from "../../lib/roster";
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
  phuTrachCa?: Record<string, string>;
  canManageResponsibility?: boolean;
  onSetResponsibility?: (occurrenceId: string, nvId: string) => void;
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
  phuTrachCa = {},
  canManageResponsibility = false,
  onSetResponsibility,
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
                  const occurrenceId = `${d}|${khung}`;
                  const responsibleId = phuTrachCa[occurrenceId] ?? "";

                  return (
                    <td
                      key={d}
                      className={`nq-roster-slot ${lit ? "nq-roster-slot--spot" : ""}`}
                      data-dimmed={dimmed ? "1" : undefined}
                    >
                      {shifts.length > 0 ? (
                        <>
                        <button
                          type="button"
                          className={`nq-roster-slot-btn nq-roster-slot-btn--${summary.tone} ${hasUnconfirmed ? "ring-1 ring-amber-500/70" : ""}`}
                          onClick={() => onSelectDay(d)}
                          aria-label={`${dayLabels[DAYS.indexOf(d)]?.title} ${rowLabel}: ${summary.countLabel}, ${roleLabel}${hasUnconfirmed ? " (Có nhân sự chưa xác nhận lịch)" : ""}`}
                        >
                          <span className="nq-roster-slot-count inline-flex items-center justify-center gap-1">
                            {assigned.length >= required
                              ? `Đủ ${assigned.length}/${required}`
                              : `Thiếu ${required - assigned.length} · ${assigned.length}/${required}`}
                            {hasUnconfirmed && (
                              <span className="text-amber-400" title="Có nhân sự chưa xác nhận lịch">
                                <Icon name="warn" size={10} />
                              </span>
                            )}
                          </span>
                          <span className="nq-roster-slot-role">{summary.roleLabel}</span>
                          <span className="nq-roster-slot-people">
                            {assigned.length > 0
                              ? assigned.map((id) => `${nvName(id)}${pinnedIds.has(id) ? " · ghim" : ""}`).join(", ")
                              : "Chưa có nhân viên"}
                          </span>
                          <span className="mt-2 block border-t border-[var(--nq-dim)] pt-2 text-xs">
                            Phụ trách: {responsibleId ? nvName(responsibleId) : "Chưa chọn"}
                          </span>
                        </button>
                        {canManageResponsibility && assigned.length > 0 ? (
                          <select
                            aria-label={`Phụ trách ${d} ${khung}`}
                            value={responsibleId}
                            onChange={(event) => {
                              if (event.target.value) onSetResponsibility?.(occurrenceId, event.target.value);
                            }}
                            className="mt-2 w-full border border-[var(--nq-dim)] bg-[var(--nq-surface)] px-2 py-1 text-xs"
                          >
                            <option value="">Chọn phụ trách</option>
                            {assigned.map((nvId) => (
                              <option key={nvId} value={nvId}>{nvName(nvId)}</option>
                            ))}
                          </select>
                        ) : null}
                        </>
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
