"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import { useMemo, useRef } from "react";
import type { Points } from "three";

function Particles({ count = 100 }: { count?: number }) {
  const ref = useRef<Points>(null);
  const positions = useMemo(() => {
    const arr = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 5;
      arr[i * 3 + 1] = Math.random() * 2.4 - 1.2;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 2.5;
    }
    return arr;
  }, [count]);

  useFrame((_, delta) => {
    const mesh = ref.current;
    if (!mesh) return;
    const pos = mesh.geometry.attributes.position.array as Float32Array;
    for (let i = 0; i < count; i++) {
      pos[i * 3 + 1] += delta * (0.12 + (i % 5) * 0.02);
      pos[i * 3] += Math.sin(Date.now() * 0.001 + i) * delta * 0.02;
      if (pos[i * 3 + 1] > 1.4) pos[i * 3 + 1] = -1.2;
    }
    mesh.geometry.attributes.position.needsUpdate = true;
    mesh.rotation.y += delta * 0.04;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial size={0.045} color="#c4a574" transparent opacity={0.65} sizeAttenuation depthWrite={false} />
    </points>
  );
}

/** Hạt hơi đồng — accent 3D desktop, nền trong suốt. */
export function SteamScene() {
  return (
    <div className="nq-dash-steam" aria-hidden>
      <Canvas
        camera={{ position: [0, 0, 3.2], fov: 48 }}
        dpr={[1, 2]}
        gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
        style={{ background: "transparent" }}
      >
        <ambientLight intensity={0.35} />
        <pointLight position={[2, 2, 2]} intensity={0.5} color="#d4b888" />
        <Particles />
      </Canvas>
    </div>
  );
}
