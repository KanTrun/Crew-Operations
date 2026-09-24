"use client";

/**
 * TourGuide — chuỗi neo tất định kèm lời dẫn có căn cứ.
 *
 * Bản trước chỉ in `anchor_id` rồi `narrative` thành hai cột chữ, và mỗi neo
 * trong tour chỉ là một mã khô. Bản này đánh số bước, hiện nhãn đọc được của
 * neo, và cho bấm để nhảy sang neo đó trên bản đồ — tour phải dẫn người xem đi,
 * không chỉ liệt kê.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "../../../lib/api";
import { viError } from "../../../lib/present";
import { Icon } from "../../icons";
import { ExpEmpty } from "../exp-kit";
import type { Anchor2D } from "./SpatialMap2dFallback";

interface TourStepUI {
  step_id: string;
  anchor_id: string;
  narrative: string;
  citation_memory_ids: string[];
}

interface Tour {
  tour_id: string;
  steps: TourStepUI[];
  grounded: boolean;
}

interface Props {
  /** Nhãn neo đọc được — để bước tour không chỉ có mã. */
  anchorLabels?: Anchor2D[];
  onFocusAnchor?: (anchorId: string) => void;
}

const COPY = {
  read: {
    doing: "dựng được tour mở quán",
    missing: "Chưa có tour nào để dẫn. Thử lại sau khi quán có neo và ký ức.",
  },
} as const;

export default function TourGuide({ anchorLabels, onFocusAnchor }: Props) {
  const [tour, setTour] = useState<Tour | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [rev, setRev] = useState(0);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  const labelFor = useMemo(() => {
    const map = new Map<string, string>();
    for (const a of anchorLabels ?? []) map.set(a.anchor_id, a.label);
    return (id: string) => map.get(id) ?? id;
  }, [anchorLabels]);

  const load = useCallback(async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${base}/api/v1/experience/tour/start`, {
        method: "POST",
        headers: tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {},
      });
      if (!res.ok) throw new ApiError(res.status);
      setTour((await res.json()) as Tour);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }, [base, tokenStr]);

  useEffect(() => {
    void load();
  }, [load, rev]);

  if (error && !tour) {
    return (
      <section className="nq-tour" aria-label="AI Tour Guide">
        <div className="nq-exp-section__head">
          <Icon name="map" size={16} />
          <h3 className="nq-exp-section__title">Tour mở quán</h3>
        </div>
        <div className="nq-alert nq-alert--error" role="alert">
          {viError(error, COPY.read)}
          <button type="button" className="nq-linkbtn" onClick={() => setRev((r) => r + 1)}>
            <Icon name="refresh" size={14} />
            Dựng lại tour
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="nq-tour" aria-label="AI Tour Guide">
      <div className="nq-exp-section__head">
        <Icon name="map" size={16} />
        <h3 className="nq-exp-section__title">Tour mở quán</h3>
        <span className="nq-exp-section__spacer" />
        <span className="nq-rolechip">
          <Icon name={tour?.grounded ? "check" : "info"} size={13} />
          {tour?.grounded ? "Có căn cứ từ ký ức" : "Chưa gắn ký ức"}
        </span>
      </div>

      {busy && !tour ? (
        <p aria-busy="true">Đang dựng tour…</p>
      ) : !tour || tour.steps.length === 0 ? (
        <ExpEmpty
          icon="map"
          title="Chưa dựng được bước nào"
          hint="Tour cần ít nhất một neo đang dùng và một ký ức đã xác nhận để dẫn."
        />
      ) : (
        <ol className="nq-tour__steps">
          {tour.steps.map((s) => (
            <li key={s.step_id} className="nq-tour__step">
              <span className="nq-tour__anchor">
                {onFocusAnchor ? (
                  <button
                    type="button"
                    className="nq-tour__anchorbtn"
                    data-testid={`tour-go-${s.anchor_id}`}
                    onClick={() => onFocusAnchor(s.anchor_id)}
                  >
                    <Icon name="location" size={13} />
                    {labelFor(s.anchor_id)}
                  </button>
                ) : (
                  labelFor(s.anchor_id)
                )}
              </span>
              <span className="nq-tour__narrative">{s.narrative}</span>
              {s.citation_memory_ids?.length ? (
                <span className="nq-tour__cite">
                  <Icon name="pin" size={12} />
                  Dựa trên {s.citation_memory_ids.length} ký ức đã xác nhận
                </span>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}