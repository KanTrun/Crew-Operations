"use client";

/**
 * RuleEvidenceDrawer — bằng chứng trước khi tin câu luật.
 *
 * Bản trước in mã `candidate_id` ra tiêu đề và dùng ký tự `✕` thay vì icon.
 * Bằng chứng phải đọc được như lời kể: bao nhiêu quyết định, ai làm, ca nào —
 * và phản ví dụ là cảnh báo nổi bật, không phải dòng chữ nhỏ.
 */

import { useEffect, useState } from "react";
import { ApiError } from "../../../lib/api";
import { viError } from "../../../lib/present";
import { Icon } from "../../icons";
import { ExpEmpty } from "../exp-kit";

interface EvidenceView {
  candidate_id: string;
  repeated_decisions: number;
  actors: string[];
  affected_shifts: string[];
  counterexamples: string[];
  confidence: number;
}

interface Props {
  candidateId: string;
  onClose: () => void;
}

const COPY = {
  read: { doing: "đọc được bằng chứng của ứng viên luật này" },
} as const;

export default function RuleEvidenceDrawer({ candidateId, onClose }: Props) {
  const [data, setData] = useState<EvidenceView | null>(null);
  const [error, setError] = useState<unknown>(null);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  useEffect(() => {
    let cancelled = false;
    fetch(`${base}/api/v1/experience/rules/${candidateId}/evidence`, {
      headers: tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {},
    })
      .then((res) => {
        if (!res.ok) throw new ApiError(res.status);
        return res.json() as Promise<EvidenceView>;
      })
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e);
      });
    return () => {
      cancelled = true;
    };
  }, [base, candidateId, tokenStr]);

  return (
    <div className="nq-drawer" role="dialog" aria-modal="true" aria-label="Bằng chứng luật">
      <div className="nq-drawer__inner">
        <button type="button" className="nq-drawer__close" aria-label="Đóng" onClick={onClose}>
          <Icon name="close" size={18} />
        </button>
        <h2>Vì sao hệ thống đề xuất luật này</h2>

        {error ? (
          <div className="nq-alert nq-alert--error" role="alert">
            {viError(error, COPY.read)}
          </div>
        ) : null}
        {!data && !error ? (
          <p aria-busy="true">Đang đọc bằng chứng…</p>
        ) : null}

        {data ? (
          <div className="nq-evidence">
            <dl className="nq-evidence__summary">
              <div>
                <dt>Quyết định lặp lại</dt>
                <dd>{data.repeated_decisions}</dd>
              </div>
              <div>
                <dt>Độ tin cậy</dt>
                <dd>{(data.confidence * 100).toFixed(0)}%</dd>
              </div>
            </dl>

            {data.counterexamples.length ? (
              <div className="nq-alert nq-alert--error">
                <strong>Phản ví dụ:</strong> {data.counterexamples.join("; ")} — có
                trường hợp đi ngược lại luật này, cần xem kỹ trước khi ban hành.
              </div>
            ) : (
              <p className="nq-evidence__clean">
                <Icon name="check" size={13} />
                Không tìm thấy trường hợp nào đi ngược lại đề xuất này.
              </p>
            )}

            <h3>Người đã ra quyết định</h3>
            {data.actors.length ? (
              <ul className="nq-evidence__list">
                {data.actors.map((a) => (
                  <li key={a}>{a}</li>
                ))}
              </ul>
            ) : (
              <ExpEmpty icon="users" title="Không ghi nhận người ra quyết định" />
            )}

            <h3>Ca bị ảnh hưởng</h3>
            {data.affected_shifts.length ? (
              <ul className="nq-evidence__list">
                {data.affected_shifts.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            ) : (
              <ExpEmpty icon="calendar" title="Không ghi nhận ca nào bị ảnh hưởng" />
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}