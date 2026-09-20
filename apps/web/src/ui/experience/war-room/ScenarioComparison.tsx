"use client";

/** So sánh baseline + options. Mọi số phải có nhãn Mô phỏng/Ước tính. */

import { formatVnd } from "../experience-api";
import type { WarRoomOption } from "./war-room-model";

interface Props {
  baseline: Record<string, string | number | boolean>;
  options: WarRoomOption[];
  selectedOptionId: string | null;
  onSelect: (optionId: string) => void;
  onPropose: (optionId: string) => void;
  onShowEvidence: (option: WarRoomOption) => void;
  proposing: boolean;
}

export default function ScenarioComparison({
  baseline,
  options,
  selectedOptionId,
  onSelect,
  onPropose,
  onShowEvidence,
  proposing,
}: Props) {
  return (
    <section className="nq-war-compare" aria-label="So sánh phương án">
      <div className="nq-war-compare__baseline">
        <h3>Baseline (dữ liệu hiện có)</h3>
        <dl>
          <dt>Nhân viên khả dụng</dt>
          <dd>{String(baseline.nhan_vien_available ?? "—")}</dd>
          <dt>Doanh thu TB ca</dt>
          <dd>{formatVnd(Number(baseline.doanh_thu_tb_ca ?? 0))}</dd>
        </dl>
        <span className="nq-fixture-chip">Fixture replay</span>
      </div>

      <div className="nq-war-compare__rail">
        {options.map((opt) => {
          const blocked = (opt.constraint_violations?.length ?? 0) > 0;
          return (
            <div
              key={opt.option_id}
              className={`nq-war-compare__option${selectedOptionId === opt.option_id ? " is-selected" : ""}${blocked ? " is-blocked" : ""}`}
            >
              <button
                type="button"
                className="nq-war-compare__head"
                aria-pressed={selectedOptionId === opt.option_id}
                onClick={() => onSelect(opt.option_id)}
              >
                {opt.option_id}
              </button>
              <span className="nq-war-compare__num">
                Doanh thu: {formatVnd(opt.outputs?.doanh_thu_du_kien ?? null)}
              </span>
              <span className="nq-war-compare__num">
                Công bằng delta: {opt.fairness_impact?.delta?.toFixed(2) ?? "—"}
              </span>
              {blocked ? (
                <span className="nq-war-compare__blocked">Vi phạm ràng buộc cứng</span>
              ) : (
                <span className="nq-war-compare__sim">Mô phỏng</span>
              )}
              {opt.stale_data ? <span className="nq-war-compare__stale">Dữ liệu cũ</span> : null}
              <div className="nq-war-compare__actions">
                <button
                  type="button"
                  className="nq-war-compare__evidence"
                  data-testid="why-btn"
                  onClick={() => onShowEvidence(opt)}
                >
                  Vì sao
                </button>
                <button
                  type="button"
                  className="nq-btn nq-btn--primary"
                  data-testid="propose-btn"
                  disabled={blocked || proposing}
                  onClick={() => onPropose(opt.option_id)}
                >
                  {proposing ? "Đang xử lý…" : "Đề xuất"}
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}