"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../../lib/api";
import { safeText, viError } from "../../../lib/present";
import { getToken, isChuQuan, isManager } from "../../../lib/session";
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
    <div className="nq-page">
      <PageHeader
        kicker="Vận hành ca trực · Tự động & Thông minh"
        title="Sơ đồ bàn & Lịch đặt bàn"
        meta="Quản lý sơ đồ 10 bàn, theo dõi đơn đặt bàn AI và nhận thông báo ca trực theo thời gian thực."
      />

      {error && <Notice>{error}</Notice>}

      {/* Cảnh báo ca trực có thông báo chưa đọc */}
      {unreadNotifs.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          <Alert kind="info">
            <div style={{ fontWeight: 600, marginBottom: 6 }}>
              🔔 Bạn có {unreadNotifs.length} thông báo đặt bàn mới trong ca trực cần xác nhận:
            </div>
            {unreadNotifs.map((n) => (
              <div
                key={n.id}
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  padding: "8px 12px",
                  background: "#fff",
                  borderRadius: 6,
                  marginTop: 6,
                  border: "1px solid #f39c12",
                }}
              >
                <div>
                  <div style={{ fontWeight: 600 }}>{n.tieu_de}</div>
                  <div style={{ fontSize: "0.85rem", color: "#555", whiteSpace: "pre-line" }}>{n.noi_dung}</div>
                </div>
                <Btn variant="primary" onClick={() => handleAckNotification(n.id)}>
                  Đã xem (Ack)
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
          {/* SƠ ĐỒ BÀN THỜI GIAN THỰC */}
          <div style={{ marginBottom: 30 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700 }}>
                🗺️ Sơ Đồ Bàn Hiện Tại ({tables.length} bàn)
              </h3>
              <div style={{ display: "flex", gap: 12, fontSize: "0.85rem" }}>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 12, height: 12, borderRadius: 3, background: "#27ae60" }} /> Trống
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 12, height: 12, borderRadius: 3, background: "#f39c12" }} /> Đã đặt (AI)
                </span>
                <span style={{ display: "flex", alignItems: "center", gap: 4 }}>
                  <span style={{ width: 12, height: 12, borderRadius: 3, background: "#e74c3c" }} /> Khách đang ngồi
                </span>
              </div>
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))",
                gap: 12,
              }}
            >
              {tables.map((t) => {
                const booking = occupiedTableMap[t.id];
                let bgColor = "#27ae60"; // Trống
                let statusTxt = "Sẵn sàng đón khách";

                if (booking) {
                  if (booking.status === "seated") {
                    bgColor = "#e74c3c";
                    statusTxt = `Khách đang ngồi (${booking.customer_name})`;
                  } else {
                    bgColor = "#f39c12";
                    statusTxt = `Đã đặt: ${booking.booking_time.slice(11, 16)} (${booking.party_size} ng)`;
                  }
                }

                return (
                  <div
                    key={t.id}
                    style={{
                      background: "#fff",
                      borderTop: `4px solid ${bgColor}`,
                      borderRadius: 8,
                      padding: "12px",
                      boxShadow: "0 1px 4px rgba(0,0,0,0.08)",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                      <strong style={{ fontSize: "1.1rem" }}>{t.ten_ban}</strong>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          padding: "2px 6px",
                          borderRadius: 4,
                          background: "#eee",
                          fontWeight: 600,
                        }}
                      >
                        {t.suc_chua} chỗ
                      </span>
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "#666", marginTop: 4 }}>📍 {t.vi_tri}</div>
                    {t.can_combine_with && t.can_combine_with.length > 0 && (
                      <div style={{ fontSize: "0.75rem", color: "#888", marginTop: 2 }}>
                        🔗 Ghép được: {t.can_combine_with.join(", ")}
                      </div>
                    )}
                    <div
                      style={{
                        marginTop: 8,
                        fontSize: "0.8rem",
                        fontWeight: 600,
                        color: bgColor,
                      }}
                    >
                      {statusTxt}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* DANH SÁCH ĐƠN ĐẶT BÀN */}
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
              <h3 style={{ margin: 0, fontSize: "1.2rem", fontWeight: 700 }}>
                📋 Danh Sách Đặt Bàn ({filteredReservations.length})
              </h3>
              <div style={{ display: "flex", gap: 8 }}>
                {["all", "confirmed", "seated", "completed", "cancelled", "no_show"].map((st) => (
                  <button
                    key={st}
                    onClick={() => setFilterStatus(st)}
                    style={{
                      padding: "4px 10px",
                      borderRadius: 6,
                      border: "1px solid #ddd",
                      background: filterStatus === st ? "#2c3e50" : "#fff",
                      color: filterStatus === st ? "#fff" : "#333",
                      fontSize: "0.8rem",
                      cursor: "pointer",
                      fontWeight: 600,
                    }}
                  >
                    {st === "all" ? "Tất cả" : STATUS_MAP[st]?.label || st}
                  </button>
                ))}
                <Btn variant="ghost" onClick={loadData}>
                  Tải lại
                </Btn>
              </div>
            </div>

            {filteredReservations.length === 0 ? (
              <Empty title="Không có đơn đặt bàn">Không có đơn đặt bàn nào thỏa mãn điều kiện lọc.</Empty>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {filteredReservations.map((r) => {
                  const stConfig = STATUS_MAP[r.status] || { label: r.status, tone: "default" as const };
                  return (
                    <div
                      key={r.id}
                      style={{
                        background: "#fff",
                        borderRadius: 8,
                        padding: "14px",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        flexWrap: "wrap",
                        gap: 12,
                      }}
                    >
                      <div>
                        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <strong style={{ fontSize: "1.05rem" }}>{r.customer_name}</strong>
                          <span style={{ fontSize: "0.85rem", color: "#555" }}>📞 {r.phone}</span>
                          <StatusChip tone={stConfig.tone}>{stConfig.label}</StatusChip>
                          {r.source === "ai_auto" && (
                            <span
                              style={{
                                fontSize: "0.75rem",
                                background: "#e8f8f5",
                                color: "#16a085",
                                padding: "2px 6px",
                                borderRadius: 4,
                                fontWeight: 600,
                              }}
                            >
                              🤖 AI Auto
                            </span>
                          )}
                        </div>
                        <div style={{ fontSize: "0.85rem", color: "#555", marginTop: 4 }}>
                          🕒 Giờ hẹn: <strong>{r.booking_time.slice(0, 16).replace("T", " ")}</strong> (
                          {r.duration_minutes} phút) | 👥 Số khách: <strong>{r.party_size} người</strong> | 🪑 Bàn:{" "}
                          <strong>{(r.table_ids || []).join(", ") || "Chưa gán"}</strong>
                        </div>
                        {r.notified_nv_id && (
                          <div style={{ fontSize: "0.75rem", color: "#888", marginTop: 2 }}>
                            👤 Ca trực phụ trách: {r.notified_nv_id}{" "}
                            {r.notification_acked_at ? "• Đã xác nhận" : "• Chưa xem"}
                          </div>
                        )}
                      </div>

                      {/* Các nút thao tác */}
                      <div style={{ display: "flex", gap: 6 }}>
                        {r.status === "confirmed" && (
                          <>
                            <Btn
                              variant="primary"
                              disabled={busyId === r.id}
                              onClick={() => handleAction(r.id, "check-in")}
                            >
                              Vào bàn
                            </Btn>
                            <Btn
                              variant="danger"
                              disabled={busyId === r.id}
                              onClick={() => handleAction(r.id, "no-show")}
                            >
                              No-Show
                            </Btn>
                            <Btn
                              variant="ghost"
                              disabled={busyId === r.id}
                              onClick={() => handleAction(r.id, "cancel")}
                            >
                              Hủy
                            </Btn>
                          </>
                        )}
                        {r.status === "seated" && (
                          <Btn
                            variant="primary"
                            disabled={busyId === r.id}
                            onClick={() => handleAction(r.id, "complete")}
                          >
                            Hoàn tất (Trả bàn)
                          </Btn>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
