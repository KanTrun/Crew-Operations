"use client";

/**
 * LivingMap — mặt bằng quán với hai lớp hình ảnh.
 *
 * 2D là canonical (luôn có, không phụ thuộc máy). 3D là *tăng cường luỹ tiến*:
 * chỉ bật khi máy thật sự chạy được WebGL, và người dùng luôn có công tắc quay
 * về 2D. Trước đây file này khai `useState(false)` nên nhánh 3D là code chết —
 * ba/@react-three đã có sẵn trong repo và đang chạy ở trang Hôm nay.
 */

import dynamic from "next/dynamic";
import { useState } from "react";
import { Icon } from "../../icons";
import { useCapability3d } from "../useCapability3d";
import LivingMap2d, { type ZoneUI } from "./LivingMap2d";

const LivingMap3d = dynamic(() => import("./LivingMap3d"), {
  ssr: false,
  loading: () => <div className="nq-living-map__canvas nq-living-map__canvas--loading" aria-busy="true" />,
});

interface Props {
  zones: ZoneUI[];
  selectedId?: string | null;
  onSelectZone?: (id: string) => void;
  renderBadge?: (zone: ZoneUI) => React.ReactNode;
}

export default function LivingMap({ zones, selectedId, onSelectZone, renderBadge }: Props) {
  const tier = useCapability3d();
  // Lựa chọn của người dùng ghi đè năng lực máy: có máy khoẻ nhưng vẫn muốn 2D
  // là chuyện bình thường, nên công tắc này thắng `tier`.
  const [prefer2d, setPrefer2d] = useState(false);
  const canRender3d = tier !== "off" && !prefer2d;

  return (
    <div className="nq-living-map__shell">
      <div className="nq-living-map__topbar">
        <span className="nq-rolechip">
          <Icon name={canRender3d ? "cube" : "map"} size={13} />
          {canRender3d ? "Không gian 3D" : "Mặt bằng 2D"}
        </span>
        {tier !== "off" ? (
          <button
            type="button"
            className="nq-viewtoggle"
            data-testid="living-map-toggle"
            aria-pressed={canRender3d}
            onClick={() => setPrefer2d((v) => !v)}
          >
            <Icon name={canRender3d ? "map" : "cube"} size={14} />
            {canRender3d ? "Xem dạng mặt bằng" : "Xem dạng 3D"}
          </button>
        ) : null}
      </div>

      {canRender3d ? (
        <>
          <LivingMap3d zones={zones} selectedId={selectedId} onSelect={onSelectZone} tier={tier} />
          <p className="nq-living-map__legend-hint" style={{ margin: "0.15rem 0 0" }}>
            Kéo để xoay · Cuộn để phóng to/nhỏ · Bấm vào khối để chọn khu vực
          </p>
          {/* Điều khiển bằng bàn phím cho lớp 3D: canvas không Tab được, nên
              chip DOM dưới đây là đường vào thật cho người dùng keyboard. */}
          <div className="nq-living-map__chips" role="group" aria-label="Chọn khu vực trên không gian 3D">
            {zones.map((z) => (
              <button
                key={z.zone_id}
                type="button"
                className={`nq-zchip${z.zone_id === selectedId ? " is-selected" : ""}`}
                disabled={!z.active}
                onClick={() => onSelectZone?.(z.zone_id)}
              >
                {z.label} · {Math.round(z.load_signal * 100)}%
              </button>
            ))}
          </div>
        </>
      ) : (
        <LivingMap2d
          zones={zones}
          selectedId={selectedId}
          onSelectZone={onSelectZone}
          renderBadge={renderBadge}
        />
      )}
    </div>
  );
}