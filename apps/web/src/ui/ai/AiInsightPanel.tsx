"use client";

import { useCallback, useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { Alert, Btn, OpsCard } from "../kit";

type Insight = {
  tom_tat: string;
  diem_chinh: string[];
  khuyen_nghi: string[];
  canh_bao: string[];
  ai_generated: boolean;
  provider?: string;
};

/**
 * Khung "AI phân tích" gắn ở cột phụ của các trang AI tất định (đề xuất,
 * giải thích, thử nghiệm an toàn, cẩm nang…) — đọc CÙNG dữ liệu đã hiện trên
 * trang, kể lại bằng lời tự nhiên qua LLM (`POST /api/v1/ai/insight`), thay
 * cho việc trang chỉ có chữ liệt kê thô trên nền tối.
 */
export function AiInsightPanel({ page }: { page: string }) {
  const [insight, setInsight] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    apiSend<{ ok: boolean; insight: Insight }>("/api/v1/ai/insight", { page })
      .then((d) => setInsight(d.insight))
      .catch((e) => setError(viError(e, { doing: "tạo được phân tích AI cho trang này" })))
      .finally(() => setLoading(false));
  }, [page]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <OpsCard
      eyebrow={insight?.ai_generated ? "AI phân tích" : "Tóm tắt"}
      title="Trợ lý đọc giúp trang này"
      density="compact"
      action={
        <Btn variant="ghost" size="sm" busy={loading} onClick={load}>
          Phân tích lại
        </Btn>
      }
    >
      {error ? <Alert kind="err">{error}</Alert> : null}
      {loading && !insight ? (
        <p className="nq-muted text-sm">Đang đọc dữ liệu trang và tóm tắt…</p>
      ) : insight ? (
        <div className="space-y-3">
          <p className="text-sm text-[var(--nq-fg)]">{insight.tom_tat}</p>

          {insight.diem_chinh.length > 0 ? (
            <ul className="space-y-1.5">
              {insight.diem_chinh.map((point, i) => (
                <li key={i} className="flex gap-2 text-sm text-[var(--nq-ink)]">
                  <span className="text-[var(--nq-accent)]" aria-hidden="true">
                    •
                  </span>
                  <span>{point}</span>
                </li>
              ))}
            </ul>
          ) : null}

          {insight.khuyen_nghi.length > 0 ? (
            <div>
              <p className="mb-1 text-2xs font-bold uppercase tracking-wider text-[var(--nq-ink-muted)]">
                Nên làm tiếp
              </p>
              <ul className="space-y-1.5">
                {insight.khuyen_nghi.map((rec, i) => (
                  <li
                    key={i}
                    className="rounded border border-[color-mix(in_srgb,var(--nq-st-ok)_40%,var(--nq-line))] bg-[var(--nq-st-ok-soft)] px-2.5 py-1.5 text-sm text-[var(--nq-st-ok-ink)]"
                  >
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {insight.canh_bao.length > 0 ? (
            <div>
              <p className="mb-1 text-2xs font-bold uppercase tracking-wider text-[var(--nq-ink-muted)]">
                Cần chú ý
              </p>
              <ul className="space-y-1.5">
                {insight.canh_bao.map((warn, i) => (
                  <li
                    key={i}
                    className="rounded border border-[color-mix(in_srgb,var(--nq-st-warn)_46%,var(--nq-line))] bg-[var(--nq-st-warn-soft)] px-2.5 py-1.5 text-sm text-[var(--nq-st-warn-ink)]"
                  >
                    {warn}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {!insight.ai_generated ? (
            <p className="text-2xs italic text-[var(--nq-ink-muted)]">
              Chưa nối được AI trực tiếp — đây là tóm tắt đếm từ dữ liệu thật, không phải văn AI.
            </p>
          ) : null}
        </div>
      ) : null}
    </OpsCard>
  );
}
