"use client";

import type { KhungGio, RosterShift } from "../../lib/roster";
import { khungOrder, rosterCellSummary, shiftRowLabel } from "../../lib/roster";

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
  matchCell,
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
                  const shift = (byDay[d] ?? []).find((c) => c.khung === khung);
                  const assigned = shift ? phanCong[shift.id] ?? [] : [];
                  const dimmed = shift && !matchCell(assigned, shift);
                  const lit = spotlightDay === d;
                  const vt = viTriLabel(shift?.vi_tri);
                  const summary = rosterCellSummary(assigned.length, vt, assigned.length > 0 && assigned.length < 2);

                  return (
                    <td
                      key={d}
                      className={`nq-roster-slot ${lit ? "nq-roster-slot--spot" : ""}`}
                      data-dimmed={dimmed ? "1" : undefined}
                    >
                      {shift ? (
                        <button
                          type="button"
                          className={`nq-roster-slot-btn nq-roster-slot-btn--${summary.tone}`}
                          onClick={() => onSelectDay(d)}
                          aria-label={`${dayLabels[DAYS.indexOf(d)]?.title} ${rowLabel}: ${summary.countLabel}, ${vt}`}
                        >
                          <span className="nq-roster-slot-count">{summary.countLabel}</span>
                          <span className="nq-roster-slot-role">{summary.roleLabel}</span>
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
