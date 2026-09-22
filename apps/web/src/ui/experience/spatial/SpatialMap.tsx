"use client";

/**
 * SpatialMap — chọn lớp hình ảnh cho HỒN QUÁN: 2D canonical, 3D tăng cường.
 *
 * Bản trước: `const [webgl] = useState(false)` và nhánh `true` trả `null`, nên
 * 3D không tồn tại — chỉ là một chú thích nói rằng "sau này sẽ có". Giờ dùng
 * cùng cách đã kiểm chứng ở `LivingMap`: đo năng lực máy thật qua
 * `useCapability3d`, luôn có công tắc quay về 2D, và giữ một danh sách chip DOM
 * để người dùng bàn phím chọn được neo (canvas không Tab được).
 *
 * Neo đang chọn nằm ở `SpatialMemoryPage` nên hai lớp hình ảnh chia sẻ đúng một
 * nguồn trạng thái — bấm ở 3D rồi chuyển sang 2D vẫn giữ nguyên neo.
 */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { Icon } from "../../icons";
import { useCapability3d } from "../useCapability3d";
import SpatialMap2dFallback, { type Anchor2D } from "./SpatialMap2dFallback";

const SpatialMap3d = dynamic(() => import("./SpatialMap3d"), {
  ssr: false,
  loading: () => <div className="nq-map3d nq-map3d--loading" aria-busy="true" />,
});

interface Props {
  anchors: Anchor2D[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  renderBadge?: (anchor: Anchor2D) => React.ReactNode;
  /** Số ký ức đã xác nhận theo neo — chiều cao cột 3D đọc từ đây. */
  memoryCounts?: Record<string, number>;
}

export default function SpatialMap({
  anchors,
  selectedId,
  onSelect,
  renderBadge,
  memoryCounts,
}: Props) {
  const tier = useCapability3d();
  const [prefer2d, setPrefer2d] = useState(false);
  const canRender3d = tier !== "off" && !prefer2d;

  // Neo mặc định: chọn neo đầu khi có dữ liệu mà chưa chọn gì, để khung chi
  // tiết bên cạnh không trống ngay lần mở đầu tiên.
  useEffect(() => {
    if (!selectedId && anchors.length) onSelect(anchors[0].anchor_id);
  }, [anchors, onSelect, selectedId]);

  return (
    <div className="nq-spatial-map">
      <div className="nq-living-map__topbar">
        <span className="nq-rolechip">
          <Icon name={canRender3d ? "cube" : "map"} size={13} />
          {canRender3d ? "Không gian 3D" : "Sơ đồ 2D"}
        </span>
        <span className="nq-spatial-map__count">{anchors.length} neo</span>
        {tier !== "off" ? (
          <button
            type="button"
            className="nq-viewtoggle"
            data-testid="spatial-map-toggle"
            aria-pressed={canRender3d}
            onClick={() => setPrefer2d((v) => !v)}
          >
            <Icon name={canRender3d ? "map" : "cube"} size={14} />
            {canRender3d ? "Xem dạng sơ đồ" : "Xem dạng 3D"}
          </button>
        ) : null}
      </div>

      {canRender3d ? (
        <>
          <SpatialMap3d
            anchors={anchors}
            selectedId={selectedId}
            onSelect={onSelect}
            memoryCounts={memoryCounts}
            tier={tier}
          />
          {/* Đường vào cho bàn phím: canvas 3D không Tab được. */}
          <div
            className="nq-living-map__chips"
            role="group"
            aria-label="Chọn neo trên không gian 3D"
          >
            {anchors.map((a) => (
              <button
                key={a.anchor_id}
                type="button"
                className={`nq-zchip${a.anchor_id === selectedId ? " is-selected" : ""}`}
                onClick={() => onSelect(a.anchor_id)}
              >
                {a.label}
                {memoryCounts?.[a.anchor_id] ? ` · ${memoryCounts[a.anchor_id]} ký ức` : ""}
              </button>
            ))}
          </div>
        </>
      ) : (
        <SpatialMap2dFallback
          anchors={anchors}
          selectedId={selectedId}
          onSelect={onSelect}
          renderBadge={renderBadge}
        />
      )}
    </div>
  );
}