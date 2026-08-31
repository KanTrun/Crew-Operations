"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef, useState } from "react";
import type { Group, Points } from "three";

function Particles({ count = 140, pullX = 0, pullY = 0 }: { count?: number; pullX?: number; pullY?: number }) {
  const ref = useRef<Points>(null);
  const velocities = useMemo(() => new Float32Array(count), [count]);
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 5;
      arr[i * 3 + 1] = Math.random() * 2.4 - 1.2;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 2.5;
      velocities[i] = 0.1 + Math.random() * 0.08;
    }
    return arr;
  }, [count, velocities]);

  useFrame((_, delta) => {
    const mesh = ref.current;
    if (!mesh) return;
    const pos = mesh.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < count; i++) {
      pos[i * 3 + 1] += delta * velocities[i];
      pos[i * 3] += (pullX * 0.4 + Math.sin(Date.now() * 0.001 + i) * 0.015) * delta;
      pos[i * 3 + 2] += pullY * 0.25 * delta;
      if (pos[i * 3 + 1] > 1.5) {
        pos[i * 3 + 1] = -1.2;
        pos[i * 3] = (Math.random() - 0.5) * 5;
      }
    }
    mesh.geometry.attributes.position.needsUpdate = true;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.05} color="#d4b888" transparent opacity={0.75} sizeAttenuation depthWrite={false} />
    </points>
  );
}

function GlowRing({ active }: { active: boolean }) {
  const ref = useRef<Group>(null);
  useFrame((_, delta) => {
    if (!ref.current) return;
    ref.current.rotation.z += delta * (active ? 0.35 : 0.12);
    const s = active ? 1.08 : 1;
    ref.current.scale.setScalar(s + Math.sin(Date.now() * 0.002) * 0.02);
  });
  return (
    <group ref={ref}>
      <mesh>
        <torusGeometry args={[1.1, 0.018, 12, 64]} />
        <meshBasicMaterial color="#c4a574" transparent opacity={active ? 0.55 : 0.28} />
      </mesh>
    </group>
  );
}

function SceneInner() {
  const { pointer } = useThree();
  const group = useRef<Group>(null);
  const [active, setActive] = useState(false);

  useFrame((_, delta) => {
    if (!group.current) return;
    group.current.rotation.y += delta * 0.08;
    group.current.rotation.x += (pointer.y * 0.35 - group.current.rotation.x) * 0.08;
    group.current.position.x += (pointer.x * 0.45 - group.current.position.x) * 0.08;
  });

  return (
    <group
      ref={group}
      onPointerOver={() => setActive(true)}
      onPointerOut={() => setActive(false)}
    >
      <GlowRing active={active} />
      <Particles pullX={pointer.x} pullY={pointer.y} />
    </group>
  );
}

/** Hơi cà phê 3D — phản ứng chuột, desktop. */
export function SteamScene() {
  return (
    <div className="nq-dash-steam" aria-hidden>
      <p className="nq-dash-steam-hint">Di chuột để khám phá</p>
      <Canvas
        camera={{ position: [0, 0, 3.2], fov: 48 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.4} />
        <pointLight position={[2, 2, 2]} intensity={0.55} color="#d4b888" />
        <SceneInner />
      </Canvas>
    </div>
  );
}
