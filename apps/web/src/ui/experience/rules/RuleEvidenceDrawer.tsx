"use client";

/** Evidence drawer — timeline bằng chứng trước khi hiện câu luật. */

import { useEffect, useState } from "react";
import { RoleChip } from "../exp-kit";

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

export default function RuleEvidenceDrawer({ candidateId, onClose }: Props) {
  const [data, setData] = useState<EvidenceView | null>(null);
  const [error, setError] = useState<string | null>(null);

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
        if (!res.ok) throw new Error(`api_${res.status}`);
        return res.json() as Promise<EvidenceView>;
      })
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Lỗi");
      });
    return () => {
      cancelled = true;
    };
  }, [base, candidateId, tokenStr]);

  return (
    <div className="nq-drawer" role="dialog" aria-modal="true" aria-label="Bằng chứng luật">
      <div className="nq-drawer__inner">
        <button type="button" className="nq-drawer__close" aria-label="Đóng" onClick={onClose}>
          ✕
        </button>
        <h2>Timeline bằng chứng</h2>
        {error ? <div className="nq-alert nq-alert--error">{error}</div> : null}
        {data ? (
          <div>
            <p>
              Quyết định lặp lại: <strong>{data.repeated_decisions}</strong> · độ tin cậy{" "}
              {data.confidence.toFixed(2)}
            </p>
            <h3>Người ra quyết định</h3>
            <ul>{data.actors.map((a) => <li key={a}>{a}</li>)}</ul>
            <h3>Ca bị ảnh hưởng</h3>
            <ul>{data.affected_shifts.map((s) => <li key={s}>{s}</li>)}</ul>
            {data.counterexamples.length ? (
              <div className="nq-alert nq-alert--error">
                Phản ví dụ: {data.counterexamples.join(", ")} — cần review cẩn thận.
              </div>
            ) : null}
            <RoleChip label="Dữ liệu đã kiểm chứng" />
          </div>
        ) : (
          <p aria-busy="true">Đang tải…</p>
        )}
      </div>
    </div>
  );
}