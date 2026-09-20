"use client";

/** HỒN QUÁN Spatial Memory — map 2D + anchor details + timeline + voice + tour. */

import { useCallback, useEffect, useState } from "react";
import { getToken } from "../../../lib/session";
import { AuthGate, Loading } from "../../../ui/kit";
import SpatialMap from "../../../ui/experience/spatial/SpatialMap";
import SpatialAnchorDetails from "../../../ui/experience/spatial/SpatialAnchorDetails";
import VoiceDock from "../../../ui/experience/spatial/VoiceDock";
import TourGuide from "../../../ui/experience/spatial/TourGuide";
import type { Anchor2D } from "../../../ui/experience/spatial/SpatialMap2dFallback";

export default function SpatialMemoryPage() {
  const [token, setToken] = useState("");
  const [ready, setReady] = useState(false);
  const [anchors, setAnchors] = useState<Anchor2D[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

  useEffect(() => {
    setToken(getToken());
    setReady(true);
  }, []);

  const loadAnchors = useCallback(async () => {
    try {
      const res = await fetch(`${base}/api/v1/experience/map`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`api_${res.status}`);
      const body = (await res.json()) as { anchors: Anchor2D[] };
      setAnchors(body.anchors);
      setSelectedId(body.anchors[0]?.anchor_id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải bản đồ");
    }
  }, [base, token]);

  useEffect(() => {
    if (token) loadAnchors();
  }, [token, loadAnchors]);

  if (!ready) return <Loading>Đang kiểm tra phiên…</Loading>;
  if (!token) return <AuthGate />;

  return (
    <div className="nq-spatial">
      <header className="nq-spatial__header">
        <h1>HỒN QUÁN — Không gian ký ức</h1>
        <p>Gắn sự cố, quy trình, lời khen và ký ức vận hành vào bản đồ quán.</p>
      </header>

      {error ? <div className="nq-alert nq-alert--error">{error}</div> : null}

      <div className="nq-spatial__layout">
        <SpatialMap
          anchors={anchors}
          selectedId={selectedId}
          onSelect={setSelectedId}
        />
        <div className="nq-spatial__side">
          {selectedId ? <SpatialAnchorDetails anchorId={selectedId} /> : null}
          <TourGuide />
        </div>
      </div>

      <VoiceDock anchorId={selectedId} />
    </div>
  );
}