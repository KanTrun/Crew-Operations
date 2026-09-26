"use client";

/**
 * CandidateTable — bảng so sánh người bù ca, TRẢI NGANG.
 *
 * Vì sao đổi từ thẻ dọc sang bảng: người quản lý phải SO SÁNH giữa các ứng viên
 * (ai lệch công bằng ít hơn, ai thêm ít giờ hơn, ai phủ nhiều kỹ năng hơn). Xếp
 * thẻ dọc thì mắt phải nhảy lên nhảy xuống và không so được cột nào với cột nào.
 * Bảng đặt đúng tiêu chí thành cột để so theo chiều dọc.
 *
 * Cột lấy thẳng từ payload `/shift-rescue/{id}/candidates`:
 * `rank · nv_ten · fairness_delta · added_hours · skill_coverage · safe`.
 * Không suy diễn thêm số — cột nào trống thì in "—" (quy ước: chưa có dữ liệu,
 * KHÔNG phải 0).
 */

import { Icon } from "../../icons";
import { eligibilityReasonLabel, passReasonLabel } from "../exp-present";

interface Candidate {
  candidate_id: string;
  nv_id: string;
  nv_ten: string;
  safe: boolean;
  reason_passes: string[];
  reason_blocks: string[];
  fairness_delta: number;
  added_hours: number;
  /** Bản đồ kỹ năng → có đáp ứng hay không (KHÔNG phải phần trăm). */
  skill_coverage?: Record<string, boolean>;
  rank?: number;
}

interface Props {
  candidates: Candidate[];
  blocked?: Candidate[];
  onSelect?: (candidateId: string) => void;
  disabled?: boolean;
  selected?: string | null;
}

/**
 * `skill_coverage` là bản đồ kỹ năng → boolean. Hiển thị "đạt/tổng" thay vì
 * phần trăm: hợp đồng gốc không có trường phần trăm, và bịa ra một con số ở đây
 * là nói sai dữ liệu của hệ thống.
 */
function coverage(coverageMap: Record<string, boolean> | undefined): {
  text: string;
  covered: string[];
} {
  const entries = Object.entries(coverageMap ?? {});
  if (entries.length === 0) return { text: "—", covered: [] };
  const covered = entries.filter(([, ok]) => ok).map(([k]) => k);
  return { text: `${covered.length}/${entries.length}`, covered };
}

/** Lệch công bằng: dấu là thông tin (âm = nhận ít hơn), nên giữ dấu. */
function delta(value: number | undefined): string {
  if (typeof value !== "number" || !Number.isFinite(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}`;
}

export default function CandidateTable({
  candidates,
  blocked = [],
  onSelect,
  disabled,
  selected,
}: Props) {
  const ranked = [...candidates].sort((a, b) => (a.rank ?? 999) - (b.rank ?? 999));

  return (
    <div className="nq-ctable" data-testid="rescue-candidate-table">
      <table>
        <thead>
          <tr>
            <th scope="col" className="nq-ctable__rank">
              Hạng
            </th>
            <th scope="col">Người</th>
            <th scope="col" className="nq-ctable__num">
              Lệch công bằng
            </th>
            <th scope="col" className="nq-ctable__num">
              Giờ thêm
            </th>
            <th scope="col" className="nq-ctable__num">
              Phủ kỹ năng
            </th>            <th scope="col">Vì sao đạt</th>
            <th scope="col" className="nq-ctable__act" />
          </tr>
        </thead>
        <tbody>
          {ranked.map((c) => (
            <tr
              key={c.candidate_id}
              className={selected === c.candidate_id ? "is-selected" : undefined}
              data-candidate={c.candidate_id}
            >
              <td className="nq-ctable__rank">
                <span className="nq-ctable__ranknum">{c.rank ?? "—"}</span>
              </td>
              <td className="nq-ctable__name">{c.nv_ten || "Nhân viên"}</td>
              <td className="nq-ctable__num">{delta(c.fairness_delta)}</td>
              <td className="nq-ctable__num">{c.added_hours} h</td>
              <td className="nq-ctable__num">
                {(() => {
                  const cov = coverage(c.skill_coverage);
                  return (
                    <span title={cov.covered.join(", ")} data-coverage={cov.text}>
                      {cov.text}
                    </span>
                  );
                })()}
              </td>
              <td>
                {c.reason_passes?.length ? (
                  <ul className="nq-ctable__reasons">
                    {c.reason_passes.slice(0, 3).map((r, i) => (
                      <li key={i}>{passReasonLabel(r)}</li>
                    ))}
                    {c.reason_passes.length > 3 ? (
                      <li className="nq-ctable__more">
                        +{c.reason_passes.length - 3} lý do khác
                      </li>
                    ) : null}
                  </ul>
                ) : (
                  <span className="nq-ctable__dash">—</span>
                )}
              </td>
              <td className="nq-ctable__act">
                {onSelect ? (
                  <button
                    type="button"
                    className="nq-btn-compact nq-modebtn"
                    data-testid="invite-btn"
                    disabled={disabled}
                    onClick={() => onSelect(c.candidate_id)}
                  >
                    <Icon name="send" size={13} />
                    {selected === c.candidate_id ? "Đã mời" : "Mời"}
                  </button>
                ) : null}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Người bị loại — bảng riêng, cùng cột, để thấy RÕ vì sao loại. */}
      {blocked.length ? (
        <div className="nq-ctable__blocked">
          <p className="nq-exp-section__title nq-ctable__blockedtitle">
            Bị loại ({blocked.length}) — không được mời vì vi phạm ràng buộc cứng
          </p>
          <table>
            <thead>
              <tr>
                <th scope="col">Người</th>
                <th scope="col">Không đạt vì</th>
              </tr>
            </thead>
            <tbody>
              {blocked.map((c) => (
                <tr key={c.candidate_id} data-candidate={c.candidate_id} className="is-blocked">
                  <td className="nq-ctable__name">{c.nv_ten || "Nhân viên"}</td>
                  <td>
                    <ul className="nq-ctable__reasons nq-ctable__reasons--block">
                      {(c.reason_blocks ?? []).map((r, i) => (
                        <li key={i}>{eligibilityReasonLabel(r)}</li>
                      ))}
                    </ul>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
