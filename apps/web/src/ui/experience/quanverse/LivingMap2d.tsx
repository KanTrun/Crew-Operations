"use client";

/**
 * LivingMap2d — mặt bằng SVG cùng toạ độ PLAN với LivingMap3d.
 */

import type { ReactNode } from "react";
import { Icon, type IconName } from "../../icons";
import { livingPlacement, planToSvg } from "./living-plan";

export interface ZoneUI {
  zone_id: string;
  label: string;
  kind: string;
  active: boolean;
  load_signal: number;
}

const KIND_ICON: Record<string, IconName> = {
  quay: "coffee",
  phong_khach: "table-map",
  loi_vao: "door",
  bar: "coffee",
  cashier: "users",
  window_table: "table-map",
  entrance: "door",
};

const KIND_LABEL: Record<string, string> = {
  quay: "Quầy",
  phong_khach: "Bàn",
  loi_vao: "Cửa",
  bar: "Quầy bar",
  cashier: "Thu ngân",
  window_table: "Bàn cửa sổ",
  entrance: "Lối vào",
};

function loadTone(load: number): "low" | "mid" | "high" {
  if (load >= 0.7) return "high";
  if (load >= 0.4) return "mid";
  return "low";
}

const VIEW_W = 640;
const VIEW_H = 420;

interface Props {
  zones: ZoneUI[];
  selectedId?: string | null;
  onSelectZone?: (id: string) => void;
  renderBadge?: (zone: ZoneUI) => ReactNode;
}

export default function LivingMap2d({
  zones,
  selectedId = null,
  onSelectZone,
  renderBadge,
}: Props) {
  return (
    <div className="nq-living-map" role="group" aria-label="Bản đồ trạng thái quán (mặt bằng)">
      <svg
        className="nq-living-map__svg"
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        role="img"
        aria-hidden="false"
      >
        <rect x="0" y="0" width={VIEW_W} height={VIEW_H} className="nq-living-map__floor" rx="12" />
        {zones.map((z, i) => {
          const place = livingPlacement(z.zone_id, i);
          const box = planToSvg(place, VIEW_W, VIEW_H);
          const tone = loadTone(z.load_signal);
          const selected = z.zone_id === selectedId;
          return (
            <g
              key={z.zone_id}
              className={`nq-living-map__zone-g nq-living-map__zone-g--${tone}${selected ? " is-selected" : ""}`}
              data-testid={`zone-${z.zone_id}`}
              role="button"
              tabIndex={z.active ? 0 : -1}
              aria-pressed={selected}
              aria-disabled={!z.active}
              aria-label={`${z.label}, tải ${Math.round(z.load_signal * 100)}%`}
              onClick={() => z.active && onSelectZone?.(z.zone_id)}
              onKeyDown={(e) => {
                if (!z.active) return;
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelectZone?.(z.zone_id);
                }
              }}
            >
              <rect
                x={box.x}
                y={box.y}
                width={box.w}
                height={box.h}
                rx="8"
                className="nq-living-map__zone-rect"
              />
              <rect
                x={box.x + 4}
                y={box.y + box.h - 10}
                width={Math.max(4, box.w * z.load_signal - 8)}
                height="4"
                rx="2"
                className="nq-living-map__zone-load"
              />
              <text
                x={box.x + box.w / 2}
                y={box.y + box.h / 2}
                textAnchor="middle"
                dominantBaseline="middle"
                className="nq-living-map__zone-text"
              >
                {z.label}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="nq-living-map__chips" aria-label="Chọn khu vực">
        {zones.map((z) => {
          const tone = loadTone(z.load_signal);
          const pct = Math.round(z.load_signal * 100);
          const kindIcon = KIND_ICON[z.kind] ?? KIND_ICON[z.zone_id] ?? "coffee";
          return (
            <button
              key={z.zone_id}
              type="button"
              className={
                "nq-living-map__zone" +
                ` nq-living-map__zone--load-${tone}` +
                (z.zone_id === selectedId ? " is-selected" : "")
              }
              data-testid={`zone-chip-${z.zone_id}`}
              aria-pressed={z.zone_id === selectedId}
              disabled={!z.active}
              onClick={() => onSelectZone?.(z.zone_id)}
            >
              <span className="nq-living-map__glyph" aria-hidden="true">
                <Icon name={kindIcon} size={18} />
              </span>
              <span className="nq-living-map__body">
                <span className="nq-living-map__label">{z.label}</span>
                <span className="nq-living-map__meta">
                  <span className="nq-living-map__kind">{KIND_LABEL[z.kind] ?? KIND_LABEL[z.zone_id] ?? z.kind}</span>
                  <span className="nq-living-map__loadt" data-testid={`zone-load-${z.zone_id}`}>
                    <Icon name="gauge" size={13} />
                    Tải {pct}%
                  </span>
                </span>
                {renderBadge ? <span className="nq-living-map__badge">{renderBadge(z)}</span> : null}
              </span>
            </button>
          );
        })}
      </div>

      <p className="nq-living-map__legend">
        <span className="nq-loadbar__key nq-loadbar__key--low" aria-hidden="true" />
        Nhẹ
        <span className="nq-loadbar__key nq-loadbar__key--mid" aria-hidden="true" />
        Vừa
        <span className="nq-loadbar__key nq-loadbar__key--high" aria-hidden="true" />
        Tải cao
        <span className="nq-living-map__legend-hint">Bấm một khu vực trên sơ đồ hoặc chip bên dưới</span>
      </p>
    </div>
  );
}
