"use client";

/** LivingMap — bản đồ trạng thái quán theo vai trò (2D fallback). */

import type { ReactNode } from "react";

export interface ZoneUI {
  zone_id: string;
  label: string;
  kind: string;
  active: boolean;
  load_signal: number;
}

interface Props {
  zones: ZoneUI[];
  onSelectZone?: (id: string) => void;
  renderBadge?: (zone: ZoneUI) => ReactNode;
}

export default function LivingMap2d({ zones, onSelectZone, renderBadge }: Props) {
  return (
    <div className="nq-living-map" role="group" aria-label="Bản đồ trạng thái quán (2D)">
      <div className="nq-living-map__grid">
        {zones.map((z) => (
          <button
            key={z.zone_id}
            type="button"
            className={`nq-living-map__zone nq-living-map__zone--${z.kind}`}
            data-testid={`zone-${z.zone_id}`}
            disabled={!z.active}
            onClick={() => onSelectZone?.(z.zone_id)}
          >
            <span className="nq-living-map__label">{z.label}</span>
            <span className="nq-living-map__load" aria-label={`Tải ${Math.round(z.load_signal * 100)}%`}>
              {z.kind === "phong_khach" ? "Bàn" : z.kind === "loi_vao" ? "Cửa" : "Quầy"}
            </span>
            {renderBadge ? <span className="nq-living-map__badge">{renderBadge(z)}</span> : null}
          </button>
        ))}
      </div>
    </div>
  );
}