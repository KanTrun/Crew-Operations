"use client";

/** Candidate card — safe/blocked rõ ràng + lý do tối thiểu an toàn privacy. */

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
  return (
    <article
      className={`nq-candidate${blocked || !c.safe ? " is-blocked" : ""}${selected ? " is-selected" : ""}`}
    >
      <div className="nq-candidate__head">
        <span className="nq-candidate__name">{c.nv_ten || c.nv_id}</span>
        <span className="nq-candidate__chip">
          {!c.safe || blocked ? "Bị chặn" : `An toàn · hạng ${c.rank ?? "?"}`}
        </span>
      </div>

      {c.safe && !blocked ? (
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
        <ul className="nq-candidate__reasons nq-candidate__reasons--block">
          {c.reason_blocks.map((r, i) => (
            <li key={i}>{eligibilityReasonLabel(r)}</li>
          ))}
        </ul>
      ) : null}
      {c.safe && c.reason_passes?.length ? (
        <ul className="nq-candidate__reasons">
          {c.reason_passes.slice(0, 4).map((r, i) => (
            <li key={i}>{passReasonLabel(r)}</li>
          ))}
        </ul>
      ) : null}

      {onSelect && c.safe ? (
        <button
          type="button"
          className="nq-btn nq-btn-primary"
          data-testid="invite-btn"
          disabled={disabled}
          onClick={onSelect}
        >
          {selected ? "Đã mời" : "Chọn & mời"}
        </button>
      ) : null}
    </article>
  );
}