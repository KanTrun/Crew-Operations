"use client";

/** SpatialMap — wrapper: dùng 2D fallback (progressive 3D giữ nguyên sau). */

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { Anchor2D } from "./SpatialMap2dFallback";

const SpatialMap2dFallback = dynamic(() => import("./SpatialMap2dFallback"), {
  ssr: false,
});

interface Props {
  anchors: Anchor2D[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  renderBadge?: (anchor: Anchor2D) => React.ReactNode;
}

export default function SpatialMap({ anchors, selectedId, onSelect, renderBadge }: Props) {
  // Progressive: nếu WebGL available → sau này swap sang 3D; MVP dùng 2D.
  const [webgl] = useState(false);

  if (!webgl) {
    return (
      <SpatialMap2dFallback
        anchors={anchors}
        selectedId={selectedId}
        onSelect={onSelect}
        renderBadge={renderBadge}
      />
    );
  }
  return null;
}