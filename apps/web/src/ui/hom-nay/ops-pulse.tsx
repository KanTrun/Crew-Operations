"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import Link from "next/link";
import { useMemo, useRef } from "react";
import type { Group, Mesh, Points } from "three";
import type { OpsPulseModel } from "../../lib/ops-pulse";
import { severityColor } from "../../lib/ops-pulse";
import { OpsPulseCopy } from "./ops-pulse-lite";

function AiCore({ model }: { model: OpsPulseModel }) {
  const ref = useRef<Mesh>(null);
  const color = severityColor(model.severity);

  useFrame((_, delta) => {
    if (!ref.current) return;
    const speed = model.aiActive ? 1.8 : 0.4 + model.pressure * 0.6;
    ref.current.rotation.y += delta * speed;
    ref.current.rotation.x += delta * speed * 0.35;
    const pulse = 1 + Math.sin(Date.now() * 0.003) * 0.04 * (0.3 + model.pressure);
    ref.current.scale.setScalar(pulse);
  });

  return (
    <mesh ref={ref}>
      <icosahedronGeometry args={[0.55, 1]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={model.aiActive ? 0.65 : 0.25} metalness={0.35} roughness={0.45} />
    </mesh>
  );
}

function OrbitParticles({ count, active, color }: { count: number; active: boolean; color: string }) {
  const ref = useRef<Points>(null);
  const group = useRef<Group>(null);
  const n = Math.max(4, Math.min(count, 48));
  const positions = useMemo(() => {
    const arr = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2;
      const rad = 1.05 + (i % 3) * 0.08;
      arr[i * 3] = Math.cos(a) * rad;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 0.35;
      arr[i * 3 + 2] = Math.sin(a) * rad;
    }
    return arr;
  }, [n]);

  useFrame((_, delta) => {
    if (group.current) group.current.rotation.y += delta * (active ? 1.2 : 0.35);
    if (!ref.current) return;
    const pos = ref.current.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < n; i++) {
      pos[i * 3 + 1] += delta * (active ? 0.08 : 0.02);
      if (pos[i * 3 + 1] > 0.4) pos[i * 3 + 1] = -0.35;
    }
    ref.current.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <group ref={group}>
      <points ref={ref}>
        <bufferGeometry>
          <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        </bufferGeometry>
        <pointsMaterial size={0.06} color={color} transparent opacity={0.8} sizeAttenuation depthWrite={false} />
      </points>
    </group>
  );
}

function PulseScene({ model }: { model: OpsPulseModel }) {
  const color = severityColor(model.severity);
  return (
    <>
      <ambientLight intensity={0.45} />
      <pointLight position={[2, 2, 2]} intensity={0.7} color="#d4b888" />
      <pointLight position={[-2, -1, 1]} intensity={0.35} color={color} />
      <AiCore model={model} />
      <OrbitParticles count={model.particleCount} active={model.aiActive || model.severity !== "ok"} color={color} />
    </>
  );
}

/** Widget 3D gắn nhịp AI + áp lực ops — bấm để tới việc ưu tiên. */
export function OpsPulse({ model }: { model: OpsPulseModel }) {
  const color = severityColor(model.severity);

  return (
    <Link
      href={model.href}
      className={`nq-ops-pulse nq-ops-pulse--3d nq-ops-pulse--${model.severity}`}
      aria-label={model.ariaLabel}
      data-highlight={model.highlightKpi}
    >
      <div className="nq-ops-pulse__viz" style={{ ["--pulse-color" as string]: color }}>
        <Canvas camera={{ position: [0, 0, 3.4], fov: 42 }} dpr={[1, 2]} gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}>
          <PulseScene model={model} />
        </Canvas>
      </div>
      <OpsPulseCopy model={model} />
    </Link>
  );
}
