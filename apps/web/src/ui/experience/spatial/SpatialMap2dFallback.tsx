"use client";

/**
 * SpatialMap2dFallback — sơ đồ neo nhìn từ trên xuống (bản canonical, không WebGL).
 *
 * Neo là *điểm* trong không gian quán, nên chiếu thẳng trục (x→ngang, y→dọc) là
 * cách đọc đúng nhất: khoảng cách và vị trí tương đối giữ nguyên tỉ lệ như toạ
 * độ mét mà fixture khai. Bản 3D (`SpatialMap3d`) mới là chỗ có phối cảnh.
 *
 * Mọi thứ ở đây là SVG có `tabIndex` + `onKeyDown`, nên bàn phím chọn được neo
 * y như bản 3D — hai lớp hình ảnh không lệch nhau về khả năng truy cập.
 */

import type { ReactNode } from "react";

export interface Anchor2D {
  anchor_id: string;
  khu_vuc: string;
  label: string;
  x: number;
  y: number;
  kind: string;
  active?: boolean;
}

interface Props {
  anchors: Anchor2D[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  renderBadge?: (anchor: Anchor2D) => ReactNode;
}

export default function SpatialMap2dFallback({
  anchors,
  selectedId,
  onSelect,
  renderBadge,
}: Props) {
  const W = 1000;
  const H = 700;
  const pad = 90;

  /**
   * Chiếu toạ độ mét của quán sang pixel.
   *
   * Bản trước hardcode `cx/cy = 500/450` rồi trừ thêm `-800` ở trục dọc, nên
   * với toạ độ fixture (0..9) mọi neo rơi vào khoảng y ∈ [-500, 10] — nằm hoàn
   * toàn ngoài viewBox 900px. Bản đồ trông như rỗng dù API trả đủ 8 neo.
   *
   * Cách đúng: chuẩn hoá theo hộp bao toạ độ thật của chính dữ liệu đang vẽ,
   * nên đổi fixture hay thêm neo mới cũng không cần chỉnh hằng số.
   */
  const xs = anchors.map((a) => a.x);
  const ys = anchors.map((a) => a.y);
  const minX = xs.length ? Math.min(...xs) : 0;
  const maxX = xs.length ? Math.max(...xs) : 1;
  const minY = ys.length ? Math.min(...ys) : 0;
  const maxY = ys.length ? Math.max(...ys) : 1;
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;

  const usableW = W - pad * 2;
  const usableH = H - pad * 2;

  /** Toạ độ quán → pixel, giữ đúng tỉ lệ giữa hai trục. */
  const project = (x: number, y: number): { px: number; py: number } => {
    const nx = (x - minX) / spanX; // 0..1 theo trục x của quán
    const ny = (y - minY) / spanY; // 0..1 theo trục y của quán
    return {
      px: pad + nx * usableW,
      py: pad + ny * usableH,
    };
  };

  const corners = [
    project(minX, minY),
    project(maxX, minY),
    project(maxX, maxY),
    project(minX, maxY),
  ];
  const floorPath = `M ${corners.map((c) => `${c.px} ${c.py}`).join(" L ")} Z`;

  return (
    <div className="nq-map2d" role="group" aria-label="Bản đồ không gian quán (2D)">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        aria-hidden="true"
        className="nq-map2d__svg"
      >
        <path
          d={floorPath}
          fill="var(--nq-surface-hi)"
          stroke="var(--nq-dim)"
          strokeWidth="2"
        />
        {/* Lưới mờ theo bước 1 mét — mắt đọc được khoảng cách giữa các neo. */}
        {Array.from({ length: Math.max(0, Math.round(spanX)) }, (_, i) => {
          const gx = minX + i + 1;
          if (gx >= maxX) return null;
          const a0 = project(gx, minY);
          const a1 = project(gx, maxY);
          return (
            <line
              key={`gx-${i}`}
              x1={a0.px}
              y1={a0.py}
              x2={a1.px}
              y2={a1.py}
              stroke="var(--nq-line)"
              strokeWidth="1"
              opacity="0.5"
            />
          );
        })}
        {Array.from({ length: Math.max(0, Math.round(spanY)) }, (_, i) => {
          const gy = minY + i + 1;
          if (gy >= maxY) return null;
          const a0 = project(minX, gy);
          const a1 = project(maxX, gy);
          return (
            <line
              key={`gy-${i}`}
              x1={a0.px}
              y1={a0.py}
              x2={a1.px}
              y2={a1.py}
              stroke="var(--nq-line)"
              strokeWidth="1"
              opacity="0.5"
            />
          );
        })}
        {anchors.map((a) => {
          const { px, py } = project(a.x, a.y);
          const selected = a.anchor_id === selectedId;
          return (
            <g
              key={a.anchor_id}
              transform={`translate(${px} ${py})`}
              onClick={() => onSelect(a.anchor_id)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSelect(a.anchor_id);
                }
              }}
              tabIndex={0}
              role="button"
              aria-label={a.label}
              data-anchor={a.anchor_id}
              className={`nq-map2d__anchor${selected ? " is-selected" : ""}${a.active === false ? " is-inactive" : ""}`}
            >
              {selected ? (
                /* Vòng nhấn ngoài — tách khỏi hình dạng để không đổi kích thước. */
                <circle r="34" fill="none" stroke="var(--nq-copper)" strokeWidth="2" opacity="0.6" />
              ) : null}
              <circle
                r="26"
                fill={selected ? "var(--nq-copper)" : "var(--nq-surface-hi)"}
                stroke="var(--nq-copper)"
                strokeWidth="2"
              />
              {a.kind === "thiet_bi" ? (
                /* Gear đơn giản — SVG thay emoji (guideline: không emoji icon). */
                <g fill="none" stroke="currentColor" strokeWidth="2" opacity="0.9">
                  <circle r="8" strokeWidth="2.5" />
                  {[0, 60, 120].map((deg) => {
                    const rad = (deg * Math.PI) / 180;
                    const cos = Math.cos(rad);
                    const sin = Math.sin(rad);
                    return (
                      <rect
                        key={deg}
                        x={-10 * cos - 2}
                        y={-10 * sin - 2}
                        width="4"
                        height="4"
                        rx="1"
                        transform={`rotate(${deg})`}
                      />
                    );
                  })}
                </g>
              ) : a.kind === "ban" ? (
                /* Bàn — hình chữ nhật bo góc, khác hẳn "khu vực". */
                <rect x="-11" y="-8" width="22" height="16" rx="3" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.9" />
              ) : (
                /* Vùng — hình vuông bo góc. */
                <rect x="-10" y="-10" width="20" height="20" rx="4" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.9" />
              )}
              <text y="44" textAnchor="middle" className="nq-map2d__label">
                {a.label}
              </text>
              {a.active === false ? (
                <text y="60" textAnchor="middle" className="nq-map2d__label nq-map2d__label--muted">
                  Ngừng dùng
                </text>
              ) : null}
              {renderBadge ? <g>{renderBadge(a)}</g> : null}
            </g>
          );
        })}
      </svg>
    </div>
  );
}