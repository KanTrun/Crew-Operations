"use client";

/** HỒN QUÁN Spatial Memory — map 2D/3D + anchor details + timeline + voice + tour. */

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError } from "../../../lib/api";
import { getToken } from "../../../lib/session";
import { viError } from "../../../lib/present";
import { AuthGate } from "../../../ui/kit";
import { ExpEmpty, ExpSkeleton } from "../../../ui/experience/exp-kit";
import { Icon } from "../../../ui/icons";
import SpatialMap from "../../../ui/experience/spatial/SpatialMap";
import SpatialAnchorDetails from "../../../ui/experience/spatial/SpatialAnchorDetails";
import VoiceDock from "../../../ui/experience/spatial/VoiceDock";
import TourGuide from "../../../ui/experience/spatial/TourGuide";
import type { Anchor2D } from "../../../ui/experience/spatial/SpatialMap2dFallback";

const COPY = { read: { doing: "tải được bản đồ không gian quán" } } as const;

export default function SpatialMemoryPage() {
  const [token, setToken] = useState("");
  const [ready, setReady] = useState(false);
  const [anchors, setAnchors] = useState<Anchor2D[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  /** Lỗi tải giữ đối tượng gốc để `viError` đọc được mã HTTP. */
  const [error, setError] = useState<unknown>(null);
  const [rev, setRev] = useState(0);
  /**
   * Số ký ức đã xác nhận theo neo — cột 3D đọc trực tiếp từ đây.
   *
   * Gộp một lượt cho mọi neo thay vì gọi `/anchors/{id}` từng cái: 8 neo là 8
   * request, mà dữ liệu đã có sẵn ở `/memories`.
   */
  const [memoryCounts, setMemoryCounts] = useState<Record<string, number>>({});
  const [memoryDegraded, setMemoryDegraded] = useState(false);

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
      if (!res.ok) throw new ApiError(res.status);
      const body = (await res.json()) as { anchors: Anchor2D[] };
      setAnchors(body.anchors);
      setSelectedId((cur) =>
        cur && body.anchors.some((a) => a.anchor_id === cur)
          ? cur
          : (body.anchors[0]?.anchor_id ?? null),
      );
      setError(null);
    } catch (e) {
      setError(e);
    }
  }, [base, token]);

  const loadMemoryCounts = useCallback(async () => {
    try {
      const res = await fetch(`${base}/api/v1/experience/memories?status=confirmed`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new ApiError(res.status);
      const body = (await res.json()) as { memories: { anchor_id: string }[] };
      const counts: Record<string, number> = {};
      for (const m of body.memories) {
        counts[m.anchor_id] = (counts[m.anchor_id] ?? 0) + 1;
      }
      setMemoryCounts(counts);
      setMemoryDegraded(false);
    } catch {
      // Không chặn bản đồ vì thiếu số đếm — nhưng phải nói thật là chưa đọc được.
      setMemoryCounts({});
      setMemoryDegraded(true);
    }
  }, [base, token]);

  useEffect(() => {
    if (!token) return;
    void loadAnchors();
    void loadMemoryCounts();
  }, [token, loadAnchors, loadMemoryCounts, rev]);

  const selectedLabel = useMemo(
    () => anchors.find((a) => a.anchor_id === selectedId)?.label ?? "",
    [anchors, selectedId],
  );

  if (!ready) return <ExpSkeleton rows={6} />;
  if (!token) return <AuthGate />;

  return (
    <div className="nq-spatial">
      <header className="nq-spatial__header">
        <h1>HỒN QUÁN — Không gian ký ức</h1>
        <p>
          Gắn sự cố, quy trình, lời khen và ký ức vận hành vào bản đồ quán. Ký ức
          chỉ được dùng sau khi có đồng thuận, và luôn xoá được.
        </p>
      </header>

      {error ? (
        <div className="nq-alert nq-alert--error" role="alert">
          {viError(error, COPY.read)}
          <button type="button" className="nq-linkbtn" onClick={() => setRev((r) => r + 1)}>
            <Icon name="refresh" size={14} />
            Thử lại
          </button>
        </div>
      ) : null}
      {memoryDegraded ? (
        <div className="nq-alert nq-alert--warn" role="status">
          Chưa đọc được số ký ức theo neo — cột 3D tạm hiển thị mức cơ sở.
        </div>
      ) : null}

      {anchors.length === 0 && !error ? (
        <ExpEmpty
          icon="location"
          title="Chưa có neo nào trên bản đồ"
          hint="Neo xuất hiện khi quán khai báo khu vực, bàn hoặc thiết bị."
        />
      ) : (
        <div className="nq-spatial__layout">
          <SpatialMap
            anchors={anchors}
            selectedId={selectedId}
            onSelect={setSelectedId}
            memoryCounts={memoryCounts}
          />
          <div className="nq-spatial__side">
            {selectedId ? (
              <SpatialAnchorDetails
                anchorId={selectedId}
                anchorLabel={selectedLabel}
                onChanged={() => setRev((r) => r + 1)}
              />
            ) : null}
            <TourGuide anchorLabels={anchors} onFocusAnchor={setSelectedId} />
          </div>
        </div>
      )}

      <VoiceDock anchorId={selectedId} />
    </div>
  );
}