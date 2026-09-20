"use client";

/** TourGuide — chuỗi anchor deterministic + narration grounded. */

import { useEffect, useState } from "react";

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

export default function TourGuide() {
  const [tour, setTour] = useState<Tour | null>(null);
  const [error, setError] = useState<string | null>(null);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  useEffect(() => {
    let cancelled = false;
    fetch(`${base}/api/v1/experience/tour/start`, {
      method: "POST",
      headers: tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {},
    })
      .then((r) => {
        if (!r.ok) throw new Error(`api_${r.status}`);
        return r.json() as Promise<Tour>;
      })
      .then((d) => {
        if (!cancelled) setTour(d);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Lỗi");
      });
    return () => {
      cancelled = true;
    };
  }, [base, tokenStr]);

  if (error) return <div className="nq-alert nq-alert--error">{error}</div>;
  if (!tour) return <p aria-busy="true">Đang dựng tour…</p>;

  return (
    <section className="nq-tour" aria-label="AI Tour Guide">
      <h3>Tour mở quán</h3>
      <ol className="nq-tour__steps">
        {tour.steps.map((s) => (
          <li key={s.step_id} className="nq-tour__step">
            <span className="nq-tour__anchor">{s.anchor_id}</span>
            <span className="nq-tour__narrative">{s.narrative}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}