"use client";

/** LivingMap wrapper — 2D canonical; 3D/AR là progressive enhancement. */

import { useState } from "react";
import LivingMap2d, { type ZoneUI } from "./LivingMap2d";

interface Props {
  zones: ZoneUI[];
  onSelectZone?: (id: string) => void;
  renderBadge?: (zone: ZoneUI) => React.ReactNode;
}

export default function LivingMap({ zones, onSelectZone, renderBadge }: Props) {
  // MVP: 2D luôn là canonical. WebGL progressive bật sau (Phase 6 bonus).
  const [webgl] = useState(false);

  return (
    <LivingMap2d
      zones={zones}
      onSelectZone={onSelectZone}
      renderBadge={renderBadge}
    />
  );
}