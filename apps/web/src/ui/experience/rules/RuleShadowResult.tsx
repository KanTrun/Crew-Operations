"use client";

/**
 * RuleShadowResult — kết quả chạy thử luật trên dữ liệu cũ: trước/sau thế nào.
 *
 * Không dùng emoji làm icon (design-guidelines §Icon) và không in số thô khi
 * thiếu dữ liệu — `undefined.toFixed()` cho ra chữ "undefined" trên UI.
 */

import { Icon } from "../../icons";

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

const DASH = "—";

function num(value: unknown, digits = 3): string {
  return typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(digits)
    : DASH;
}

export default function RuleShadowResult({ result }: { result: Record<string, unknown> }) {
  const s = result as ShadowResult;
  const constraintsOk = s.hard_constraints_ok !== false;
  const notes = s.notes ?? [];

  return (
    <div className="nq-shadow">
      <h4>Kết quả chạy thử</h4>
      <span className={`nq-chip ${constraintsOk ? "nq-chip--ok" : "nq-chip--warn"}`}>
        <Icon name={constraintsOk ? "check" : "warn"} size={12} />
        {constraintsOk
          ? "Ràng buộc cứng giữ nguyên"
          : "Ràng buộc cứng thay đổi — cần xem lại"}
      </span>
      <dl className="nq-shadow__deltas">
        <div>
          <dt>Công bằng delta</dt>
          <dd>{num(s.fairness_delta)}</dd>
        </div>
        <div>
          <dt>Tải việc delta</dt>
          <dd>{num(s.workload_delta)}</dd>
        </div>
        {typeof s.operational_delta === "number" ? (
          <div>
            <dt>Vận hành delta</dt>
            <dd>{num(s.operational_delta)}</dd>
          </div>
        ) : null}
      </dl>
      {notes.length ? (
        <ul className="nq-shadow__notes">
          {notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      ) : null}
      <p className="nq-shadow__warn">
        <Icon name="warn" size={13} />
        Không tự kích hoạt — chờ quản lý xác nhận.
      </p>
    </div>
  );
}