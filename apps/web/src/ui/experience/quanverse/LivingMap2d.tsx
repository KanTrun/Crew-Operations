"use client";

/**
 * LivingMap2d — mặt bằng quán (bản canonical, không phụ thuộc WebGL).
 *
 * Trước đây khu vực là bốn card chữ giống hệt nhau: mắt không đọc được khu nào
 * đang tải, khu nào là cửa, khu nào là bàn. Bản này vẽ mặt bằng thật:
 * hình dạng khối theo `kind`, icon theo `kind`, và một cột tải dọc lấy trực
 * tiếp từ `load_signal` — nên "đang tải nhiều" là thứ nhìn thấy, không phải
 * con số phải đọc.
 *
 * Chú thích: mọi thứ ở đây là DOM (không SVG) để bấm/Tab được như nút thật;
 * `role="group"` giữ nguyên để e2e và trình đọc màn hình không đổi hành vi.
 */

import type { ReactNode } from "react";
import { Icon, type IconName } from "../../icons";

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
};

const KIND_LABEL: Record<string, string> = {
  quay: "Quầy",
  phong_khach: "Bàn",
  loi_vao: "Cửa",
};

function loadTone(load: number): "low" | "mid" | "high" {
  if (load >= 0.7) return "high";
  if (load >= 0.4) return "mid";
  return "low";
}

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
      <div className="nq-living-map__grid">
        {zones.map((z) => {
          const tone = loadTone(z.load_signal);
          const pct = Math.round(z.load_signal * 100);
          const kindIcon = KIND_ICON[z.kind] ?? "coffee";
          return (
            <button
              key={z.zone_id}
              type="button"
              className={
                "nq-living-map__zone" +
                ` nq-living-map__zone--${z.kind}` +
                ` nq-living-map__zone--load-${tone}` +
                (z.zone_id === selectedId ? " is-selected" : "")
              }
              data-testid={`zone-${z.zone_id}`}
              aria-pressed={z.zone_id === selectedId}
              disabled={!z.active}
              onClick={() => onSelectZone?.(z.zone_id)}
            >
              <span className="nq-living-map__glyph" aria-hidden="true">
                <Icon name={kindIcon} size={22} />
              </span>
              <span className="nq-living-map__body">
                <span className="nq-living-map__label">{z.label}</span>
                <span className="nq-living-map__meta">
                  <span className="nq-living-map__kind">{KIND_LABEL[z.kind] ?? z.kind}</span>
                  <span className="nq-living-map__loadt" data-testid={`zone-load-${z.zone_id}`}>
                    <Icon name="gauge" size={13} />
                    Tải {pct}%
                  </span>
                </span>
                {renderBadge ? <span className="nq-living-map__badge">{renderBadge(z)}</span> : null}
              </span>
              {/* Cột tải: chiều cao = tải thực. Bề mặt thị giác, không đọc nhãn. */}
              <span className={`nq-loadbar nq-loadbar--${tone}`} aria-hidden="true">
                <span className="nq-loadbar__fill" style={{ height: `${Math.max(6, pct)}%` }} />
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
        <span className="nq-living-map__legend-hint">Bấm một khu vực để xem chi tiết</span>
      </p>
    </div>
  );
}