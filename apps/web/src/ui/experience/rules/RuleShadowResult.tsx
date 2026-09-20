"use client";

/** Shadow result — trước/sau trade-off, không tự kích hoạt. */

interface ShadowResult {
  before?: Record<string, number>;
  after?: Record<string, number>;
  diffs?: Record<string, number>;
  hard_constraints_ok?: boolean;
  fairness_delta?: number;
  workload_delta?: number;
  operational_delta?: number;
  notes?: string[];
}

export default function RuleShadowResult({ result }: { result: Record<string, unknown> }) {
  const s = result as ShadowResult;
  return (
    <div className="nq-shadow">
      <h4>Kết quả shadow test</h4>
      {s.hard_constraints_ok === false ? (
        <span className="nq-chip nq-chip--warn">Ràng buộc cứng sau khi áp dụng có thay đổi</span>
      ) : (
        <span className="nq-chip nq-chip--ok">Ràng buộc cứng giữ nguyên</span>
      )}
      <dl className="nq-shadow__deltas">
        <div>
          <dt>Công bằng delta</dt>
          <dd>{s.fairness_delta?.toFixed(3)}</dd>
        </div>
        <div>
          <dt>Tải việc delta</dt>
          <dd>{s.workload_delta?.toFixed(3)}</dd>
        </div>
      </dl>
      <p className="nq-shadow__notes">
        {(s.notes ?? []).map((n, i) => (
          <span key={i}>{n}; </span>
        ))}
      </p>
      <p className="nq-shadow__warn">⚠ Không tự kích hoạt — chờ quản lý xác nhận.</p>
    </div>
  );
}