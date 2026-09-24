"use client";

/**
 * SpatialMap3d — HỒN QUÁN dạng khối 3D, neo đặt đúng toạ độ mét của quán.
 *
 * Vì sao cần bản này: `SpatialMap` trước đây khai `useState(false)` và nhánh
 * `true` trả `null` — "3D progressive" chỉ là chú thích, không có code. Người
 * dùng có máy khoẻ vẫn chỉ thấy bản 2D, còn câu chuyện "không gian ký ức" thì
 * mất hẳn chiều sâu.
 *
 * Khác `LivingMap3d` ở chỗ neo là *điểm* chứ không phải khối khu vực, nên ở đây
 * dựng cột mốc: chiều cao cột mã hoá số ký ức đã xác nhận tại neo đó, màu mã
 * hoá loại neo. Neo đang chọn có vòng đồng.
 *
 * Xoay/zoom: OrbitControls của drei (đã có sẵn trong repo qua `@react-three/drei`
 * và `three-stdlib`). Canvas không Tab được, nên danh sách neo dạng chip ở
 * `SpatialMap` vẫn là đường vào thật cho bàn phím.
 */

import { OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useMemo, useState } from "react";
import type { Mesh } from "three";
import type { Tier3d } from "../useCapability3d";
import type { Anchor2D } from "./SpatialMap2dFallback";

/** Bán kính cột theo loại neo — thiết bị nhỏ, bàn rộng, khu vực lớn nhất. */
const KIND_RADIUS: Record<string, number> = {
  thiet_bi: 0.11,
  ban: 0.2,
  khu_vuc: 0.26,
};

function kindColor(kind: string): string {
  if (kind === "thiet_bi") return "#8fa8a0";
  if (kind === "ban") return "#c4a574";
  return "#e8d5b5";
}

interface Placement {
  px: number;
  pz: number;
  height: number;
}

/**
 * Quy toạ độ mét của quán về hệ toạ độ Three.js quanh gốc.
 *
 * Dùng đúng hộp bao dữ liệu như bản 2D, để hai lớp hình ảnh không bao giờ lệch
 * nhau khi fixture đổi.
 */
function buildPlacements(
  anchors: Anchor2D[],
  memoryCounts: Record<string, number>,
): Map<string, Placement> {
  const out = new Map<string, Placement>();
  if (!anchors.length) return out;

  const xs = anchors.map((a) => a.x);
  const ys = anchors.map((a) => a.y);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const spanX = maxX - minX || 1;
  const spanY = maxY - minY || 1;
  /** Trục dài nhất quyết định tỉ lệ — giữ đúng tỉ lệ vàng giữa hai trục. */
  const span = Math.max(spanX, spanY);
  /** Nửa cạnh sàn: toạ độ luôn nằm trong [-SITE/2, SITE/2]. */
  const SITE = 5.2;

  for (const a of anchors) {
    const memories = memoryCounts[a.anchor_id] ?? 0;
    out.set(a.anchor_id, {
      px: (((a.x - minX) / spanX) * 2 - 1) * (spanX / span) * (SITE / 2),
      pz: (((a.y - minY) / spanY) * 2 - 1) * (spanY / span) * (SITE / 2),
      height: 0.5 + Math.min(memories, 5) * 0.22,
    });
  }
  return out;
}

function Marker({
  anchor,
  place,
  selected,
  memoryCount,
  onSelect,
}: {
  anchor: Anchor2D;
  place: Placement;
  selected: boolean;
  memoryCount: number;
  onSelect: (id: string) => void;
}) {
  const [hovered, setHovered] = useState(false);
  const radius = KIND_RADIUS[anchor.kind] ?? 0.2;
  const color = kindColor(anchor.kind);
  const inactive = anchor.active === false;

  return (
    <group position={[place.px, 0, place.pz]}>
      {/* Cột mốc: chiều cao = số ký ức đã xác nhận. */}
      <mesh
        position={[0, place.height / 2, 0]}
        onPointerOver={(e) => {
          e.stopPropagation();
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "";
        }}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(anchor.anchor_id);
        }}
      >
        <cylinderGeometry args={[radius, radius, place.height, 20]} />
        <meshStandardMaterial
          color={inactive ? "#4a423a" : color}
          emissive={color}
          emissiveIntensity={(hovered ? 0.7 : 0.25) + Math.min(memoryCount, 5) * 0.08}
          metalness={0.42}
          roughness={0.48}
        />
      </mesh>
      {/* Đế neo — đọc được vị trí ngay cả khi cột bị che khuất một phần. */}
      <mesh position={[0, 0.015, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[radius * 1.5, radius * 2.1, 24]} />
        <meshBasicMaterial color={color} transparent opacity={inactive ? 0.25 : 0.6} />
      </mesh>
      {selected ? (
        <mesh position={[0, place.height / 2, 0]}>
          <cylinderGeometry
            args={[radius * 1.5, radius * 1.5, place.height * 1.06, 20]}
          />
          <meshBasicMaterial color="#e8d5b5" wireframe transparent opacity={0.85} />
        </mesh>
      ) : null}
      {/* Chấm ký ức — mỗi ký ức một điểm sáng trên đỉnh cột. */}
      {Array.from({ length: Math.min(memoryCount, 5) }, (_, i) => (
        <mesh
          key={i}
          position={[
            Math.cos((i / 5) * Math.PI * 2) * radius * 1.8,
            place.height + 0.08,
            Math.sin((i / 5) * Math.PI * 2) * radius * 1.8,
          ]}
        >
          <sphereGeometry args={[0.035, 10, 10]} />
          <meshBasicMaterial color="#c4a574" />
        </mesh>
      ))}
    </group>
  );
}

/** Sàn quán + lưới mờ: cho mắt một hệ quy chiếu thay vì neo trôi trong hư không. */
function Floor({ sizeX, sizeZ }: { sizeX: number; sizeZ: number }) {
  return (
    <group>
      <mesh position={[0, -0.04, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[sizeX, sizeZ]} />
        <meshStandardMaterial color="#171310" metalness={0.2} roughness={0.85} />
      </mesh>
      <mesh position={[0, -0.03, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <ringGeometry args={[Math.min(sizeX, sizeZ) / 2 - 0.06, Math.min(sizeX, sizeZ) / 2, 64]} />
        <meshBasicMaterial color="#c4a574" transparent opacity={0.3} />
      </mesh>
    </group>
  );
}

/**
 * Sàn quán, đứng yên.
 *
 * Bản trước là `BreathingFloor`: sàn trôi lên xuống ±1.5cm theo chu kỳ ~15 giây,
 * với chú thích tự nhận "chỉ là một lớp chuyển động nền". Đã bỏ vì ba lẽ:
 *
 *  1. Biên độ 1.5cm ở khoảng cách camera ~7m chiếu ra dưới **2 pixel** — dưới
 *     ngưỡng đọc được. Không ai nhận ra nó đang động; chỉ đo mới biết.
 *  2. Sàn là **hệ quy chiếu** cho mọi cột mốc đứng trên nó. Cho hệ quy chiếu
 *     trôi trong khi các neo đứng yên tương đối với nó nghĩa là toàn bộ không
 *     gian lặng lẽ nhấp nhô — đúng thứ gây khó chịu mà không gọi tên được.
 *  3. `useFrame` chạy ở 60 hình/giây và ghi lại `position.y` mỗi khung, tức
 *     dựng lại ma trận của cả nhóm sàn vô ích. Trên máy yếu, một widget 3D
 *     đứng yên là widget không tốn CPU.
 *
 * Chuyển động **có mã hoá thông tin** trong widget này vốn đã đủ: chiều cao cột
 * là số ký ức, màu là loại neo, vòng đồng là neo đang chọn, điểm sáng là từng
 * ký ức. Thêm một lớp động không nói gì chỉ làm loãng những lớp đang nói.
 *
 * Ghi chú kỹ thuật còn nguyên giá trị: mọi thứ gọi `useFrame` phải nằm TRONG
 * `<Canvas>` — hook của react-three-fiber ném "Hooks can only be used within the
 * Canvas component!" nếu ở component bao ngoài, và lỗi đó từng làm trắng cả
 * trang HỒN QUÁN.
 */

interface Props {
  anchors: Anchor2D[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  memoryCounts?: Record<string, number>;
  tier: Tier3d;
}

export default function SpatialMap3d({
  anchors,
  selectedId,
  onSelect,
  memoryCounts = {},
  tier,
}: Props) {
  const placements = useMemo(
    () => buildPlacements(anchors, memoryCounts),
    [anchors, memoryCounts],
  );

  const full = tier === "full";

  return (
    <div
      className="nq-map3d"
      data-testid="spatial-3d"
      role="img"
      aria-label={`Không gian 3D quán với ${anchors.length} neo`}
    >
      <Canvas
        camera={{ position: [0, 4.6, 6.2], fov: 42 }}
        dpr={full ? [1, 2] : [1, 1.5]}
        gl={{ antialias: full, alpha: true, powerPreference: "low-power" }}
        shadows={full}
      >
        <ambientLight intensity={0.55} />
        <hemisphereLight args={["#e8d5b5", "#171310", 0.5]} />
        <pointLight
          position={[4, 5.5, 3]}
          intensity={1.6}
          distance={20}
          decay={1.2}
          color="#d4b888"
          castShadow={full}
        />
        <pointLight
          position={[-4, 3, -3]}
          intensity={0.7}
          distance={18}
          decay={1.2}
          color="#8fa8a0"
        />
        <Floor sizeX={6.2} sizeZ={5.2} />
        {anchors.map((a) => {
          const place = placements.get(a.anchor_id);
          if (!place) return null;
          return (
            <Marker
              key={a.anchor_id}
              anchor={a}
              place={place}
              selected={a.anchor_id === selectedId}
              memoryCount={memoryCounts[a.anchor_id] ?? 0}
              onSelect={onSelect}
            />
          );
        })}
        {/* Người dùng tự xoay/zoom; giới hạn góc để không chui xuống sàn. */}
        <OrbitControls
          enablePan
          enableZoom
          minDistance={3.5}
          maxDistance={14}
          maxPolarAngle={Math.PI / 2.15}
          target={[0, 0.5, 0]}
        />
      </Canvas>
    </div>
  );
}
