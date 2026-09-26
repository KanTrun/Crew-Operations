/** Mặt bằng quán dùng chung 2D/3D — toạ độ mét. */

export type PlanRect = { x: number; z: number; w: number; d: number };

/** Vị trí trên mặt bằng (mét) — gần đúng layout quán thật. */
export const LIVING_PLAN: Record<string, PlanRect> = {
  bar: { x: -1.55, z: -0.7, w: 1.9, d: 1.15 },
  cashier: { x: 1.85, z: -0.95, w: 1.35, d: 0.95 },
  window_table: { x: 1.7, z: 1.15, w: 1.55, d: 1.05 },
  entrance: { x: -1.6, z: 1.35, w: 1.15, d: 0.85 },
};

export function livingPlacement(
  zoneId: string,
  index: number,
): PlanRect {
  const known = LIVING_PLAN[zoneId];
  if (known) return known;
  return {
    x: -1.6 + (index % 3) * 1.6,
    z: -1.7 - Math.floor(index / 3) * 1.1,
    w: 1.2,
    d: 0.8,
  };
}

/** Hộp bao mặt bằng để chiếu SVG. */
export const LIVING_SITE = { minX: -3.1, maxX: 3.1, minZ: -2.3, maxZ: 2.3 };

export function planToSvg(
  place: PlanRect,
  viewW = 640,
  viewH = 420,
): { x: number; y: number; w: number; h: number } {
  const { minX, maxX, minZ, maxZ } = LIVING_SITE;
  const spanX = maxX - minX;
  const spanZ = maxZ - minZ;
  const left = place.x - place.w / 2;
  const top = place.z - place.d / 2;
  return {
    x: ((left - minX) / spanX) * viewW,
    y: ((top - minZ) / spanZ) * viewH,
    w: (place.w / spanX) * viewW,
    h: (place.d / spanZ) * viewH,
  };
}
