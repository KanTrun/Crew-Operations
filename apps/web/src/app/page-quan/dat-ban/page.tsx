"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../../lib/api";
import { safeText, viError } from "../../../lib/present";
import { getToken, isChuQuan, isManager } from "../../../lib/session";
import { Icon } from "../../../ui/icons";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Loading,
  Notice,
  PageHeader,
  StatusChip,
  useToasts,
} from "../../../ui/kit";

type Table = {
  id: string;
  store_id: string;
  ten_ban: string;
  suc_chua: number;
  vi_tri: string;
  can_combine_with: string[];
  trang_thai_hoat_dong: number;
};

type Reservation = {
  id: string;
  store_id: string;
  psid: string;
  customer_name: string;
  phone: string;
  booking_time: string;
  duration_minutes: number;
  party_size: number;
  table_ids: string[];
  status: string;
  source: string;
  notes: string;
  notified_nv_id?: string | null;
  notification_acked_at?: string | null;
  created_at: string;
};

type NotificationItem = {
  id: string;
  store_id: string;
  dat_ban_id: string;
  tieu_de: string;
  noi_dung: string;
  da_xem: number;
  created_at: string;
};

const STATUS_MAP: Record<string, { label: string; tone: "default" | "ok" | "warn" | "danger" }> = {
  held: { label: "Giữ tạm 5p", tone: "warn" },
  confirmed: { label: "Đã chốt (AI)", tone: "ok" },
  seated: { label: "Đang ngồi", tone: "default" },
  completed: { label: "Hoàn tất", tone: "default" },
  cancelled: { label: "Đã hủy", tone: "danger" },
  no_show: { label: "Không đến", tone: "danger" },
  needs_review: { label: "Cần duyệt tay", tone: "warn" },
};

export default function DatBanPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [chuQuan, setChuQuan] = useState(false);

  const [tables, setTables] = useState<Table[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const { push } = useToasts();

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setChuQuan(isChuQuan());
    if (!getToken()) setLoading(false);
  }, []);

  const loadData = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    setError(null);

    Promise.all([
      apiGet<{ tables: Table[] }>("/api/v1/reservations/tables"),
      apiGet<{ items: Reservation[] }>("/api/v1/reservations?limit=100"),
      apiGet<{ notifications: NotificationItem[] }>("/api/v1/reservations/notifications/me"),
    ])
      .then(([tblRes, resRes, notifRes]) => {
        setTables(tblRes.tables || []);
        setReservations(resRes.items || []);
        setNotifications(notifRes.notifications || []);
      })
      .catch((e) => setError(viError(e, { doing: "tải dữ liệu sơ đồ bàn" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) loadData();
  }, [token, loadData]);

  const handleAction = async (resId: string, action: "check-in" | "complete" | "no-show" | "cancel") => {
    setBusyId(resId);
    try {
      if (action === "cancel") {
        await apiSend(`/api/v1/reservations/${resId}/cancel`, {
          reason: "Nhân viên hủy trực tiếp trên giao diện",
        });
        push("Đã hủy đơn đặt bàn thành công", "ok");
      } else {
        await apiSend(`/api/v1/reservations/${resId}/${action}`);
        push(`Cập nhật trạng thái sang ${action} thành công`, "ok");
      }
      loadData();
    } catch (e) {
      push(viError(e, { doing: `thực hiện ${action}` }), "err");
    } finally {
      setBusyId(null);
    }
  };

  const handleAckNotification = async (notifId: string) => {
    try {
      await apiSend(`/api/v1/reservations/notifications/${notifId}/ack`);
      push("Đã xác nhận xem thông báo ca trực", "ok");
      loadData();
    } catch (e) {
      push(viError(e, { doing: "xác nhận thông báo" }), "err");
    }
  };

  const filteredReservations = reservations.filter((r) => {
    if (filterStatus === "all") return true;
    return r.status === filterStatus;
  });

  const unreadNotifs = notifications.filter((n) => !n.da_xem);

  // Determine current table occupancy
  const activeBookings = reservations.filter((r) => ["confirmed", "seated"].includes(r.status));
  const occupiedTableMap: Record<string, Reservation> = {};
  for (const b of activeBookings) {
    for (const tid of b.table_ids || []) {
      occupiedTableMap[tid] = b;
    }
  }

  if (!token) return <AuthGate />;
  if (!manager) {
    return (
      <div className="nq-page">
        <PageHeader kicker="Đặt bàn" title="Không đủ quyền truy cập" />
        <Notice>Bạn cần là Quản lý hoặc Chủ quán để xem sơ đồ đặt bàn.</Notice>
      </div>
    );
  }

  return (
    <div className="nq-page nq-booking-page">
      <PageHeader
        kicker="Vận hành ca trực · Tự động & Thông minh"
        title="Sơ đồ bàn & Lịch đặt bàn"
        meta="Quản lý sơ đồ 10 bàn, theo dõi đơn đặt bàn AI và nhận thông báo ca trực theo thời gian thực."
      />

      {error && <Notice>{error}</Notice>}

      {/* Cảnh báo ca trực có thông báo chưa đọc */}
      {unreadNotifs.length > 0 && (
        <div className="nq-booking-alerts">
          <Alert kind="info">
            <div className="nq-booking-alert-title">
              <Icon name="bell" size={18} />
              Bạn có {unreadNotifs.length} thông báo đặt bàn mới trong ca trực cần xác nhận
            </div>
            {unreadNotifs.map((n) => (
              <div key={n.id} className="nq-booking-alert-item">
                <div>
                  <strong>{n.tieu_de}</strong>
                  <p>{n.noi_dung}</p>
                </div>
                <Btn variant="primary" onClick={() => handleAckNotification(n.id)}>
                  Đã xem
                </Btn>
              </div>
            ))}
          </Alert>
        </div>
      )}

      {loading ? (
        <Loading />
      ) : (
        <>
          <section className="nq-booking-section">
            <div className="nq-booking-section-head">
              <h2>
                <Icon name="table-map" size={20} />
                Sơ đồ bàn hiện tại <span>{tables.length} bàn</span>
              </h2>
              <div className="nq-booking-legend" aria-label="Chú giải trạng thái bàn">
                <span><i data-tone="ready" /> Trống</span>
                <span><i data-tone="reserved" /> Đã đặt</span>
                <span><i data-tone="seated" /> Đang phục vụ</span>
              </div>
            </div>

            <div className="nq-booking-table-grid">
              {tables.map((table) => {
                const booking = occupiedTableMap[table.id];
                const tone = booking?.status === "seated" ? "seated" : booking ? "reserved" : "ready";
                const statusText = booking?.status === "seated"
                  ? `Đang phục vụ · ${booking.customer_name}`
                  : booking
                    ? `Đặt lúc ${booking.booking_time.slice(11, 16)} · ${booking.party_size} khách`
                    : "Sẵn sàng đón khách";

                return (
                  <article key={table.id} className="nq-booking-table" data-tone={tone}>
                    <div className="nq-booking-table-head">
                      <strong>{table.ten_ban}</strong>
                      <span>{table.suc_chua} chỗ</span>
                    </div>
                    <div className="nq-booking-table-meta">
                      <span><Icon name="location" size={15} /> {table.vi_tri}</span>
                      {table.can_combine_with?.length > 0 && (
                        <span><Icon name="link" size={15} /> Ghép: {table.can_combine_with.join(", ")}</span>
                      )}
                    </div>
                    <p className="nq-booking-table-status">{statusText}</p>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="nq-booking-section">
            <div className="nq-booking-section-head nq-booking-list-head">
              <h2>
                <Icon name="clipboard" size={20} />
                Danh sách đặt bàn <span>{filteredReservations.length} đơn</span>
              </h2>
              <div className="nq-booking-filters" role="group" aria-label="Lọc trạng thái đặt bàn">
                {[
                  ["all", "Tất cả"],
                  ["confirmed", "Đã chốt"],
                  ["seated", "Đang ngồi"],
                  ["completed", "Hoàn tất"],
                  ["cancelled", "Đã hủy"],
                  ["no_show", "Không đến"],
                ].map(([status, label]) => (
                  <button
                    key={status}
                    type="button"
                    aria-pressed={filterStatus === status}
                    onClick={() => setFilterStatus(status)}
                  >
                    {label}
                  </button>
                ))}
                <button type="button" className="nq-booking-refresh" onClick={loadData} aria-label="Tải lại dữ liệu">
                  <Icon name="refresh" size={17} />
                </button>
              </div>
            </div>

            {filteredReservations.length === 0 ? (
              <Empty title="Không có đơn đặt bàn">Không có đơn đặt bàn nào thỏa mãn điều kiện lọc.</Empty>
            ) : (
              <div className="nq-booking-reservations">
                {filteredReservations.map((reservation) => {
                  const statusConfig = STATUS_MAP[reservation.status] || { label: reservation.status, tone: "default" as const };
                  return (
                    <article key={reservation.id} className="nq-booking-reservation">
                      <div className="nq-booking-reservation-main">
                        <div className="nq-booking-reservation-title">
                          <strong>{reservation.customer_name}</strong>
                          <span><Icon name="phone" size={15} /> {reservation.phone}</span>
                          <StatusChip tone={statusConfig.tone}>{statusConfig.label}</StatusChip>
                          {reservation.source === "ai_auto" && (
                            <span className="nq-booking-ai"><Icon name="bot" size={14} /> AI Auto</span>
                          )}
                        </div>
                        <div className="nq-booking-reservation-meta">
                          <span><Icon name="clock" size={15} /> <strong>{reservation.booking_time.slice(0, 16).replace("T", " ")}</strong> · {reservation.duration_minutes} phút</span>
                          <span><Icon name="users" size={15} /> <strong>{reservation.party_size}</strong> người</span>
                          <span><Icon name="coffee" size={15} /> <strong>{reservation.table_ids?.join(", ") || "Chưa gán bàn"}</strong></span>
                        </div>
                        {reservation.notified_nv_id && (
                          <div className="nq-booking-assignee">
                            <Icon name="users" size={14} /> Ca trực: {reservation.notified_nv_id} · {reservation.notification_acked_at ? "Đã xác nhận" : "Chưa xem"}
                          </div>
                        )}
                      </div>

                      <div className="nq-booking-actions">
                        {reservation.status === "confirmed" && (
                          <>
                            <Btn variant="primary" disabled={busyId === reservation.id} onClick={() => handleAction(reservation.id, "check-in")}>Vào bàn</Btn>
                            <Btn variant="danger" disabled={busyId === reservation.id} onClick={() => handleAction(reservation.id, "no-show")}>No-show</Btn>
                            <Btn variant="ghost" disabled={busyId === reservation.id} onClick={() => handleAction(reservation.id, "cancel")}>Hủy</Btn>
                          </>
                        )}
                        {reservation.status === "seated" && (
                          <Btn variant="primary" disabled={busyId === reservation.id} onClick={() => handleAction(reservation.id, "complete")}>Hoàn tất · Trả bàn</Btn>
                        )}
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
