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
import { ContactShadows, Html, OrbitControls, RoundedBox } from "@react-three/drei";
import { useEffect, useMemo, useRef, useState } from "react";
import type { Mesh, Points } from "three";
import type { ZoneUI } from "./quanverse-model";
import type { Tier3d } from "../useCapability3d";
import { livingPlacement } from "./living-plan";

function placement(zone: ZoneUI, index: number) {
  return livingPlacement(zone.zone_id, index);
}

function loadColor(load: number): string {
  if (load >= 0.7) return "#f59e0b";
  if (load >= 0.4) return "#b8942f";
  return "#7c8a99";
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

  useEffect(() => {
    return () => {
      document.body.style.cursor = "";
    };
  }, []);

  return (
    <group position={[place.x, height / 2, place.z]}>
      {/* Bo góc thay khối vuông cứng — cùng một khối nhưng đỡ "thùng carton". */}
      <RoundedBox
        args={[place.w, height, place.d]}
        radius={Math.min(0.06, place.w * 0.08, height * 0.12)}
        smoothness={4}
        castShadow
        receiveShadow
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
        <meshStandardMaterial
          color={color}
          emissive={selected || hovered ? color : "#000000"}
          emissiveIntensity={selected ? 0.45 : hovered ? 0.22 : 0}
          metalness={0.35}
          roughness={0.45}
        />
      </RoundedBox>
      <Html
        position={[0, height / 2 + 0.18, 0]}
        center
        distanceFactor={8}
        style={{ pointerEvents: "none", whiteSpace: "nowrap" }}
      >
        <span
          style={{
            fontSize: "11px",
            fontFamily: "var(--nq-font-mono)",
            color: selected ? "#e8d48a" : "#c8d0d8",
            textShadow: "0 1px 4px rgba(0,0,0,.85)",
            letterSpacing: "0.04em",
          }}
        >
          {zone.label || zone.zone_id}
        </span>
      </Html>
      {/* Khung dây vàng = khu vực đang chọn */}
      {selected ? (
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[place.w * 1.06, height * 1.08, place.d * 1.08]} />
          <meshBasicMaterial color="#e8d48a" wireframe transparent opacity={0.9} />
        </mesh>
      ) : null}
      {/* Vạch tải ở mặt trước khối */}
      <mesh position={[0, -height / 2 + 0.03, place.d / 2 + 0.01]}>
        <planeGeometry args={[place.w * 0.86 * zone.load_signal, 0.05]} />
        <meshBasicMaterial color="#e6edf3" transparent opacity={0.85} />
      </mesh>
    </group>
  );
}

/**
 * Hạt hơi nước bốc lên từ khu vực **đang tải** — motif "steam-line" của quán.
 *
 * `zones` ở đây đã được lọc còn khu vực đang tải, và `LivingMap3d` KHÔNG vẽ lớp
 * này khi không còn khu vực nào. Trước đây bản gốc nhận `zones` chưa lọc nên hạt
 * bốc lên từ mọi khu vực kể cả khu vực trống — hình ảnh nói ngược với dữ liệu,
 * đúng loại lỗi khó thấy vì cảnh vẫn đẹp.
 */
function Steam({ zones, tier }: { zones: ZoneUI[]; tier: Tier3d }) {
  const ref = useRef<Points>(null);
  const count = tier === "full" ? 36 : 16;

  /**
   * Rải hạt theo số khu vực đang tải, không quay vòng qua danh sách.
   *
   * Bản trước dùng `zones[i % zones.length]` nên khi chỉ có 1 khu vực đang tải
   * thì CẢ 36 hạt dồn vào đúng một khối — trông như khối đó bốc cháy, không phải
   * như quán đang có một khu vực bận. Chia đều theo chỉ số hạt giữ mật độ hạt
   * trên mỗi khu vực ổn định, nên số khu vực đọc ra được từ lượng hơi.
   */
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    const n = Math.max(1, zones.length);
    const perZone = Math.ceil(count / n);
    for (let i = 0; i < count; i++) {
      const source = zones[Math.floor(i / perZone) % n];
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
  });

  return (
    <group>
      <points ref={ref}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        </bufferGeometry>
        <pointsMaterial
          size={0.055}
          color="#d4af37"
          transparent
          opacity={0.7}
          sizeAttenuation
          depthWrite={false}
        />
      </points>
    </group>
  );
}

/** Lõi vàng giữa quán — nhịp sáng theo tổng tải. */
function Core({ load }: { load: number }) {
  const ref = useRef<Mesh>(null);
  useFrame((state, delta) => {
    if (!ref.current) return;
    ref.current.rotation.y += delta * (0.3 + load * 0.7);
    // Nhịp phải tính theo đồng hồ của vòng vẽ, KHÔNG theo `Date.now()`: đồng hồ
    // hệ thống là mốc tuyệt đối nên pha nhịp phụ thuộc vào thời điểm trang được
    // mở — hai người xem cùng dữ liệu thấy hai pha khác nhau, và tải lại trang
    // là nhịp nhảy sang chỗ khác. `state.clock.elapsedTime` là mốc của chính
    // khung hình đang vẽ nên nhịp liền mạch và giống nhau ở mọi máy.
    const pulse = 1 + Math.sin(state.clock.elapsedTime * 2) * 0.05;
    ref.current.scale.setScalar(pulse);
  });
  const scale = 0.5 + load * 0.12;
  return (
    <mesh ref={ref} position={[0, 1.15, -0.1]} scale={scale}>
      <icosahedronGeometry args={[0.42, 1]} />
      <meshStandardMaterial
        color="#d4af37"
        emissive="#d4af37"
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

  /**
   * Chỉ khu vực ĐANG tải mới có hơi nước — và không khu vực nào thì không vẽ
   * lớp hơi nước. Ngưỡng 0.4 khớp với `loadColor` (dưới 0.4 là màu "nhẹ"), nên
   * hơi nước và màu khối luôn nói cùng một điều.
   */
  const loadedZones = useMemo(() => zones.filter((z) => z.load_signal >= 0.4), [zones]);

  return (
    <div className="nq-living-map__canvas" aria-hidden="true">
      <Canvas
        shadows={tier === "full"}
        camera={{ position: [0, 4.1, 6.2], fov: 38 }}
        dpr={tier === "full" ? [1, 2] : [1, 1.5]}
        gl={{ antialias: tier === "full", alpha: true, powerPreference: "low-power" }}
        frameloop="always"
      >
        {/* Kéo để xoay, cuộn để zoom — trước đây góc máy cố định nên cảnh trông
            như một bức ảnh tĩnh dù có hoạt hình bên trong. Giới hạn góc/khoảng
            cách để không lật xuống dưới sàn hoặc zoom ra khỏi mô hình. */}
        <OrbitControls
          enablePan={false}
          minDistance={3.2}
          maxDistance={9}
          minPolarAngle={Math.PI / 6}
          maxPolarAngle={Math.PI / 2.25}
          enableDamping
          dampingFactor={0.12}
          target={[0, 0.6, 0]}
        />
        <ambientLight intensity={0.55} />
        <hemisphereLight args={["#e8d48a", "#0b141b", 0.55]} />
        <pointLight
          position={[3, 4, 2]}
          intensity={1.5}
          distance={18}
          decay={1.3}
          color="#b8942f"
          castShadow={tier === "full"}
        />
        <pointLight position={[-3, 2, -2]} intensity={0.7} distance={16} decay={1.3} color="#e8d48a" />

        <mesh position={[0, -0.07, 0]} receiveShadow>
          <boxGeometry args={[6.2, 0.14, 4.6]} />
          <meshStandardMaterial color="#0e1b22" metalness={0.25} roughness={0.8} />
        </mesh>
        <gridHelper args={[6.2, 12, "#3d3418", "#26260f"]} position={[0, 0.005, 0]} />
        <mesh position={[0, 0.005, 0]} rotation={[-Math.PI / 2, 0, 0]}>
          <ringGeometry args={[3.02, 3.16, 64]} />
          <meshBasicMaterial color="#b8942f" transparent opacity={0.5} />
        </mesh>

        {tier === "full" ? <ContactShadows position={[0, 0.01, 0]} opacity={0.45} scale={8} blur={2.5} far={4} /> : null}

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

        {loadedZones.length > 0 ? <Steam zones={loadedZones} tier={tier} /> : null}
      </Canvas>
    </div>
  );
}
