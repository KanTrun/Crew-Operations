"use client";

import { Canvas, type CanvasProps } from "@react-three/fiber";
import {
  Component,
  type ErrorInfo,
  type ReactNode,
  useEffect,
  useState,
} from "react";

type Props = CanvasProps & {
  children: ReactNode;
  className?: string;
  fallback?: ReactNode;
  /** Khi idle, giảm tải GPU. */
  demand?: boolean;
};

class SceneErrorBoundary extends Component<
  { fallback: ReactNode; children: ReactNode; onError?: () => void },
  { failed: boolean }
> {
  state = { failed: false };

  static getDerivedStateFromError() {
    return { failed: true };
  }

  componentDidCatch(_err: Error, _info: ErrorInfo) {
    this.props.onError?.();
  }

  render() {
    if (this.state.failed) return this.props.fallback;
    return this.props.children;
  }
}

/** Wrapper R3F an toàn: ErrorBoundary, context lost → fallback, pause khi tab ẩn. */
export function Scene3d({
  children,
  className = "",
  fallback = null,
  demand = true,
  ...canvasProps
}: Props) {
  const [lost, setLost] = useState(false);
  const [hidden, setHidden] = useState(false);

  useEffect(() => {
    function onVis() {
      setHidden(document.hidden);
    }
    document.addEventListener("visibilitychange", onVis);
    return () => {
      document.removeEventListener("visibilitychange", onVis);
      document.body.style.cursor = "";
    };
  }, []);

  if (lost) return <>{fallback}</>;

  return (
    <SceneErrorBoundary fallback={fallback} onError={() => setLost(true)}>
      <div className={className}>
        <Canvas
          frameloop={hidden ? "never" : demand ? "demand" : "always"}
          onCreated={({ gl }) => {
            const el = gl.domElement;
            const onLost = (e: Event) => {
              e.preventDefault();
              setLost(true);
            };
            el.addEventListener("webglcontextlost", onLost, false);
            gl.toneMappingExposure = 1.05;
          }}
          {...canvasProps}
        >
          {children}
        </Canvas>
      </div>
    </SceneErrorBoundary>
  );
}
