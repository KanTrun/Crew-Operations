"use client";

/** SpatialAnchorDetails — trạng thái anchor + timeline + related. */

import { useEffect, useState } from "react";
import MemoryTimeline from "./MemoryTimeline";

interface AnchorDetail {
  anchor: { anchor_id: string; label: string; kind: string };
  confirmed_memories: Memory[];
  pending_memories: Memory[];
}

interface Memory {
  memory_id: string;
  content: string;
  status: string;
  consent_status: string;
  visibility: string;
  retention_until?: string | null;
}

interface Props {
  anchorId: string;
}

export default function SpatialAnchorDetails({ anchorId }: Props) {
  const [data, setData] = useState<AnchorDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  useEffect(() => {
    let cancelled = false;
    setData(null);
    fetch(`${base}/api/v1/experience/anchors/${anchorId}`, {
      headers: tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {},
    })
      .then((r) => {
        if (!r.ok) throw new Error(`api_${r.status}`);
        return r.json() as Promise<AnchorDetail>;
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
  }, [base, anchorId, tokenStr]);

  if (error) return <div className="nq-alert nq-alert--error">{error}</div>;
  if (!data) return <p aria-busy="true">Đang tải chi tiết anchor…</p>;

  return (
    <section className="nq-anchor" aria-label={`Chi tiết ${data.anchor.label}`}>
      <h3>{data.anchor.label}</h3>
      <span className="nq-fixture-chip">Fixture replay</span>

      <h4>Ký ức đã xác nhận</h4>
      <MemoryTimeline memories={data.confirmed_memories} />

      {data.pending_memories.length ? (
        <>
          <h4>Chờ xác nhận</h4>
          <MemoryTimeline memories={data.pending_memories} />
        </>
      ) : null}
    </section>
  );
}