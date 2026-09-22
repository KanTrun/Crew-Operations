/** QUANVERSE model — types + role switch (replay only). */

export type RoleId = "khach" | "nhan_vien" | "quan_ly" | "chu_quan";

export interface ZoneUI {
  zone_id: string;
  label: string;
  kind: string;
  active: boolean;
  load_signal: number;
}

export interface PublicEventUI {
  event_id: string;
  event_type: string;
  status: string;
  occurred_at: string;
  source: string;
  summary: string;
  /** Khu vực sự kiện gắn vào; `null` nghĩa là sự kiện toàn quán. */
  zone_id?: string | null;
}

export interface ModeUI {
  mode: string;
  active: boolean;
  proposal_status?: string | null;
}

export interface HorizonUI {
  item_id: string;
  kind: string;
  title: string;
  starts_at: string;
  source: string;
}

export interface LiveSnapshotUI {
  snapshot_id: string;
  store_id: string;
  role: RoleId;
  zones: ZoneUI[];
  events: PublicEventUI[];
  modes: ModeUI[];
  next_horizon: HorizonUI[];
  data_quality: { code: string; level: string; message: string }[];
}