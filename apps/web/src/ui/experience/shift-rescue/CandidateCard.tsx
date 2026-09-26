"use client";

/**
 * CandidateCard — thẻ một người có thể bù ca: an toàn hay bị chặn, và vì sao.
 *
 * Không in `candidate_id` / `nv_id`: người dùng cần biết *ai* và *vì sao*, không
 * cần mã nội bộ. Mã vẫn đi qua `data-candidate` để kiểm thử bám vào.
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
  rank?: number;
}

interface Props {
  candidate: Candidate;
  onSelect?: () => void;
  disabled?: boolean;
  selected?: boolean;
  blocked?: boolean;
}

export default function CandidateCard({
  candidate,
  onSelect,
  disabled,
  selected,
  blocked,
}: Props) {
  const c = candidate;
  const isBlocked = blocked || !c.safe;
  return (
    <article
      className={`nq-candidate${isBlocked ? " is-blocked" : ""}${selected ? " is-selected" : ""}`}
      data-candidate={c.candidate_id}
    >
      <div className="nq-candidate__head">
        <span className="nq-candidate__name">{c.nv_ten || "Nhân viên"}</span>
        <span className={`nq-candidate__chip${isBlocked ? " is-blocked" : ""}`}>
          {isBlocked ? (
            <>
              <Icon name="warn" size={12} />
              Bị chặn
            </>
          ) : (
            <>
              <Icon name="check" size={12} />
              {c.rank ? `An toàn · hạng ${c.rank}` : "An toàn"}
            </>
          )}
        </span>
      </div>

      {!isBlocked ? (
        <dl className="nq-candidate__stats">
          <div>
            <dt>Công bằng delta</dt>
            <dd>{c.fairness_delta.toFixed(2)}</dd>
          </div>
          <div>
            <dt>Giờ thêm</dt>
            <dd>{c.added_hours} h</dd>
          </div>
        </dl>
      ) : null}

      {c.reason_blocks?.length ? (
        <>
          <p className="nq-candidate__reasonlabel">Không đạt vì</p>
          <ul className="nq-candidate__reasons nq-candidate__reasons--block">
            {c.reason_blocks.map((r, i) => (
              <li key={i}>{eligibilityReasonLabel(r)}</li>
            ))}
          </ul>
        </>
      ) : null}
      {!isBlocked && c.reason_passes?.length ? (
        <>
          <p className="nq-candidate__reasonlabel">Đạt được</p>
          <ul className="nq-candidate__reasons">
            {c.reason_passes.slice(0, 4).map((r, i) => (
              <li key={i}>{passReasonLabel(r)}</li>
            ))}
          </ul>
        </>
      ) : null}

      {onSelect && !isBlocked ? (
        <button
          type="button"
          className="nq-btn nq-btn-primary"
          data-testid="invite-btn"
          disabled={disabled}
          onClick={onSelect}
        >
          <Icon name="send" size={15} />
          {selected ? "Đã mời" : "Chọn & mời"}
        </button>
      ) : null}
    </article>
  );
}