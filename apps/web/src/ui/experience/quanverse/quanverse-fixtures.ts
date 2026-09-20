/** QUANVERSE fixtures — replay-only dữ liệu demo (không phải production). */

import type { ZoneUI } from "./quanverse-model";

export const FIXTURE_ZONES: ZoneUI[] = [
  { zone_id: "bar", label: "Quầy pha chế", kind: "quay", active: true, load_signal: 0.6 },
  { zone_id: "cashier", label: "Thu ngân", kind: "quay", active: true, load_signal: 0.4 },
  { zone_id: "window_table", label: "Bàn cửa sổ", kind: "phong_khach", active: true, load_signal: 0.3 },
  { zone_id: "entrance", label: "Cửa vào", kind: "loi_vao", active: true, load_signal: 0.1 },
];