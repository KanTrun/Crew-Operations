"use client";

/**
 * LivingMap3d — sơ đồ quán dạng khối 3D ("diorama").
 *
 * Không phải trang trí: chiều cao khối mã hoá `load_signal`, độ sáng viền mã
 * hoá mức tải, và khối đang chọn có khung dây đồng. Người dùng xoay/zoom được
 * bằng chuột (OrbitControls-free: nhóm tự quay chậm) và bấm vào khối để chọn
 * khu vực — cùng hành vi với bản 2D.
 *
 * Vì sao vẫn có `tier`: máy yếu chỉ dựng sàn + khối (không bóng, không hạt
 * nước); máy khoẻ thêm bóng mềm và hạt hơi nước. Máy không có WebGL thật
 * không bao giờ vào component này — `useCapability3d` đã chặn.
 *
 * Canvas là bề mặt hình ảnh, KHÔNG phải bề mặt bàn phím: điều khiển chọn khu
 * vực luôn có bản DOM (chip dưới canvas) để người dùng Tab/Enter vẫn chọn được.
 */

import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import type { Group, Mesh, Points } from "three";
import type { ZoneUI } from "./quanverse-model";
import type { Tier3d } from "../useCapability3d";

/** Vị trí trên mặt bằng (mét) — gần đúng layout quán thật. */
const PLAN: Record<string, { x: number; z: number; w: number; d: number }> = {
  bar: { x: -1.55, z: -0.7, w: 1.9, d: 1.15 },
  cashier: { x: 1.85, z: -0.95, w: 1.35, d: 0.95 },
  window_table: { x: 1.7, z: 1.15, w: 1.55, d: 1.05 },
  entrance: { x: -1.6, z: 1.35, w: 1.15, d: 0.85 },
};

function placement(zone: ZoneUI, index: number) {
  const known = PLAN[zone.zone_id];
  if (known) return known;
  // Khu vực lạ (dữ liệu mới) → xếp thành hàng sau quầy, không vẽ chồng nhau.
  return { x: -1.6 + (index % 3) * 1.6, z: -1.7 - Math.floor(index / 3) * 1.1, w: 1.2, d: 0.8 };
}

function loadColor(load: number): string {
  if (load >= 0.7) return "#e0885f";
  if (load >= 0.4) return "#c4a574";
  return "#8fa8a0";
}

function ZoneBlock({
  zone,
  index,
  selected,
  onSelect,
}: {
  zone: ZoneUI;
  index: number;
  selected: boolean;
  onSelect: (id: string) => void;
}) {
  const place = placement(zone, index);
  const height = 0.28 + zone.load_signal * 0.85;
  const color = loadColor(zone.load_signal);
  const [hovered, setHovered] = useState(false);

  return (
    <group position={[place.x, height / 2, place.z]}>
      <mesh
        position={[0, 0, 0]}
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
          onSelect(zone.zone_id);
        }}
      >
        <boxGeometry args={[place.w, height, place.d]} />
        <meshStandardMaterial
          color={zone.active ? color : "#4a423a"}
          emissive={color}
          emissiveIntensity={(hovered ? 0.75 : 0.28) + zone.load_signal * 0.45}
          metalness={0.4}
          roughness={0.5}
        />
      </mesh>
      {/* Khung dây đồng = khu vực đang chọn (không dùng màu chữ để báo trạng thái) */}
      {selected ? (
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[place.w * 1.06, height * 1.08, place.d * 1.08]} />
          <meshBasicMaterial color="#e8d5b5" wireframe transparent opacity={0.9} />
        </mesh>
      ) : null}
      {/* Vạch tải ở mặt trước khối — đọc được mức tải từ xa */}
      <mesh position={[0, -height / 2 + 0.03, place.d / 2 + 0.01]}>
        <planeGeometry args={[place.w * 0.86 * zone.load_signal, 0.05]} />
        <meshBasicMaterial color="#f5ead8" transparent opacity={0.85} />
      </mesh>
    </group>
  );
}

/** Hạt hơi nước bốc lên từ khu vực đang tải — motif "steam-line" của quán. */
function Steam({ zones, tier }: { zones: ZoneUI[]; tier: Tier3d }) {
  const ref = useRef<Points>(null);
  const group = useRef<Group>(null);
  const count = tier === "full" ? 36 : 16;

  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      const source = zones[i % Math.max(1, zones.length)];
      const place = source ? placement(source, i) : { x: 0, z: 0, w: 1, d: 1 };
      arr[i * 3] = place.x + (Math.random() - 0.5) * place.w;
      arr[i * 3 + 1] = 0.4 + Math.random() * 1.6;
      arr[i * 3 + 2] = place.z + (Math.random() - 0.5) * place.d;
    }
    return arr;
  }, [count, zones]);

  useFrame((_, delta) => {
    if (ref.current) {
      const pos = ref.current.geometry.attributes.position.array as Float32Array;
      for (let i = 0; i < count; i++) {
        pos[i * 3 + 1] += delta * 0.24;
        if (pos[i * 3 + 1] > 2.4) pos[i * 3 + 1] = 0.35;
      }
      ref.current.geometry.attributes.position.needsUpdate = true;
    }
    if (group.current) group.current.rotation.y += delta * 0.05;
  });

  return (
    <group ref={group}>
      <points ref={ref}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        </bufferGeometry>
        <pointsMaterial
          size={0.055}
          color="#d4b888"
          transparent
          opacity={0.7}
          sizeAttenuation
          depthWrite={false}
        />
      </points>
    </group>
  );
}

/** Lõi đồng giữa quán — nhịp sáng theo tổng tải. */
function Core({ load }: { load: number }) {
  const ref = useRef<Mesh>(null);
  useFrame((_, delta) => {
    if (!ref.current) return;
    ref.current.rotation.y += delta * (0.3 + load * 0.7);
    const pulse = 1 + Math.sin(Date.now() * 0.002) * 0.05;
    ref.current.scale.setScalar(pulse);
  });
  const scale = 0.5 + load * 0.12;
  return (
    <mesh ref={ref} position={[0, 1.15, -0.1]} scale={scale}>
      <icosahedronGeometry args={[0.42, 1]} />
      <meshStandardMaterial
        color="#c4a574"
        emissive="#c4a574"
        emissiveIntensity={0.35 + load * 0.55}
        metalness={0.5}
        roughness={0.35}
      />
    </mesh>
  );
}

interface Props {
  zones: ZoneUI[];
  selectedId?: string | null;
  onSelect?: (id: string) => void;
  tier: Tier3d;
}

export default function LivingMap3d({ zones, selectedId = null, onSelect, tier }: Props) {
  const avgLoad = zones.length
    ? zones.reduce((sum, z) => sum + z.load_signal, 0) / zones.length
    : 0;

  return (
    <div className="nq-living-map__canvas" aria-hidden="true">
      <Canvas
        camera={{ position: [0, 3.6, 5.4], fov: 40 }}
        dpr={tier === "full" ? [1, 2] : [1, 1.5]}
        gl={{ antialias: tier === "full", alpha: true, powerPreference: "low-power" }}
      >
        <ambientLight intensity={0.4} />
        <pointLight position={[3, 4, 2]} intensity={0.85} color="#d4b888" />
        <pointLight position={[-3, 2, -2]} intensity={0.4} color="#8fa8a0" />

        {/* Sàn quán */}
        <mesh position={[0, -0.07, 0]} receiveShadow={tier === "full"}>
          <boxGeometry args={[6.2, 0.14, 4.6]} />
          <meshStandardMaterial color="#171310" metalness={0.2} roughness={0.85} />
        </mesh>
        {/* Viền sàn đồng */}
        <mesh position={[0, 0.005, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[3.02, 3.16, 64]} />
          <meshBasicMaterial color="#c4a574" transparent opacity={0.35} />
        </mesh>

        <Core load={avgLoad} />

        {zones.map((z, i) => (
          <ZoneBlock
            key={z.zone_id}
            zone={z}
            index={i}
            selected={z.zone_id === selectedId}
            onSelect={(id) => onSelect?.(id)}
          />
        ))}

        <Steam zones={zones} tier={tier} />
      </Canvas>
    </div>
  );
}
