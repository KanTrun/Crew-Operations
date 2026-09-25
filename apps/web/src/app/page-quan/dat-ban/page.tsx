"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../../lib/api";
import { safeText, viError } from "../../../lib/present";
import { getToken, isChuQuan, isManager } from "../../../lib/session";
import { Icon } from "../../../ui/icons";
import { useStaffNameMap } from "../../../ui/ops-pickers";
import {
  Alert,
  AuthGate,
  Btn,
  ConfirmDialog,
  Empty,
  Loading,
  Notice,
  PageHeader,
  Pagination,
  StatusChip,
  Toasts,
  usePaged,
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

/** Nhãn tiếng Việt cho mã hành động, dùng trong toast thành công và câu lỗi. */
const ACTION_LABELS: Record<"check-in" | "complete" | "no-show" | "cancel", string> = {
  "check-in": "cho khách vào bàn",
  complete: "hoàn tất và trả bàn",
  "no-show": "đánh dấu khách không đến",
  cancel: "hủy đơn đặt bàn",
};

/** Chu kỳ làm mới nền. Trang ghi "theo thời gian thực" nên phải tự cập nhật. */
const AUTO_REFRESH_MS = 30_000;

export default function DatBanPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [chuQuan, setChuQuan] = useState(false);
  const staffName = useStaffNameMap();

  const [tables, setTables] = useState<Table[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  // Huỷ đơn là hành động không lấy lại được → hỏi lý do trước khi gọi API,
  // thay vì hardcode "Nhân viên hủy trực tiếp trên giao diện" (lịch sử mất
  // thông tin thật để đối soát sau này).
  const [cancelTarget, setCancelTarget] = useState<Reservation | null>(null);
  const [cancelReason, setCancelReason] = useState("");
  const [lastSync, setLastSync] = useState<Date | null>(null);
  // Form đặt bàn thủ công: khách gọi điện / tới trực tiếp thì quản lý phải
  // nhập được vào hệ thống, nếu không đơn đó tồn tại ngoài sổ và dễ trùng bàn.
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    customer_name: "",
    phone: "",
    booking_time: "",
    party_size: "2",
  });
  const { toasts, push, dismiss } = useToasts();

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setChuQuan(isChuQuan());
    if (!getToken()) setLoading(false);
  }, []);

  /**
   * `silent=true` dùng cho làm mới tự động: không bật `loading` (tránh nháy
   * toàn trang mỗi 30 giây) và không xoá `error` cũ hiển thị chớp nhoáng.
   */
  const loadData = useCallback((opts?: { silent?: boolean }) => {
    if (!getToken()) return;
    const silent = opts?.silent === true;
    if (!silent) {
      setLoading(true);
      setError(null);
    }

    Promise.all([
      apiGet<{ tables: Table[] }>("/api/v1/reservations/tables"),
      apiGet<{ items: Reservation[] }>("/api/v1/reservations?limit=100"),
      apiGet<{ notifications: NotificationItem[] }>("/api/v1/reservations/notifications/me"),
    ])
      .then(([tblRes, resRes, notifRes]) => {
        setTables(tblRes.tables || []);
        setReservations(resRes.items || []);
        setNotifications(notifRes.notifications || []);
        setError(null);
        setLastSync(new Date());
      })
      .catch((e) => {
        // Làm mới nền thất bại thì im lặng — dữ liệu cũ vẫn đang hiển thị, báo
        // lỗi mỗi 30 giây sẽ gây nhiễu. Lỗi ở lần tải đầu thì vẫn phải báo.
        if (!silent) setError(viError(e, { doing: "tải dữ liệu sơ đồ bàn" }));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) loadData();
  }, [token, loadData]);

  // Làm mới tự động: trang ghi "theo thời gian thực" nên phải thật sự cập nhật,
  // không chỉ khi bấm nút. 30 giây đủ nhanh cho ca trực mà không spam API.
  // Dừng khi tab bị ẩn để không tốn request vô ích.
  useEffect(() => {
    if (!token || !manager) return;
    const id = window.setInterval(() => {
      if (document.visibilityState === "visible") loadData({ silent: true });
    }, AUTO_REFRESH_MS);
    return () => window.clearInterval(id);
  }, [token, manager, loadData]);

  const handleAction = async (
    resId: string,
    action: "check-in" | "complete" | "no-show" | "cancel",
    reason?: string,
  ) => {
    setBusyId(resId);
    // Nhãn tiếng Việt cho thông báo: mã hành động ("check-in", "no-show") đọc
    // lên câu tiếng Việt sẽ vỡ ngữ pháp nếu ghép thẳng vào chuỗi.
    const actionLabel = ACTION_LABELS[action];
    try {
      if (action === "cancel") {
        await apiSend(`/api/v1/reservations/${resId}/cancel`, {
          reason: reason?.trim() || "Nhân viên hủy trực tiếp trên giao diện",
        });
        push("Đã hủy đơn đặt bàn thành công", "ok");
      } else {
        await apiSend(`/api/v1/reservations/${resId}/${action}`);
        push(`Đã ${actionLabel} thành công`, "ok");
      }
      loadData({ silent: true });
    } catch (e) {
      push(viError(e, { doing: actionLabel }), "err");
    } finally {
      setBusyId(null);
    }
  };

  /** Xác nhận huỷ đơn đã chọn trong hộp thoại, kèm lý do. */
  const confirmCancel = async () => {
    if (!cancelTarget) return;
    const target = cancelTarget;
    const reason = cancelReason;
    setCancelTarget(null);
    setCancelReason("");
    await handleAction(target.id, "cancel", reason);
  };

  const handleAckNotification = async (notifId: string) => {
    try {
      await apiSend(`/api/v1/reservations/notifications/${notifId}/ack`);
      push("Đã xác nhận xem thông báo ca trực", "ok");
      loadData({ silent: true });
    } catch (e) {
      push(viError(e, { doing: "xác nhận thông báo" }), "err");
    }
  };

  /** Tạo đơn thủ công. Trường giờ dùng `datetime-local` nên gửi thẳng ISO. */
  const handleCreate = async () => {
    if (!form.customer_name.trim() || !form.phone.trim() || !form.booking_time) {
      push("Cần nhập tên khách, số điện thoại và giờ đến.", "err");
      return;
    }
    setCreating(true);
    try {
      await apiSend("/api/v1/reservations", {
        customer_name: form.customer_name.trim(),
        phone: form.phone.trim(),
        booking_time: form.booking_time,
        party_size: Number(form.party_size) || 2,
      });
      push("Đã tạo đơn đặt bàn", "ok");
      setShowCreate(false);
      setForm({ customer_name: "", phone: "", booking_time: "", party_size: "2" });
      loadData({ silent: true });
    } catch (e) {
      push(viError(e, { doing: "tạo đơn đặt bàn" }), "err");
    } finally {
      setCreating(false);
    }
  };

  const filteredReservations = reservations.filter((r) => {
    if (filterStatus === "all") return true;
    return r.status === filterStatus;
  });

  const tableNameById: Record<string, string> = {};
  for (const t of tables) tableNameById[t.id] = t.ten_ban || t.id;
  const tableNames = (ids?: string[]) =>
    ids && ids.length ? ids.map((id) => tableNameById[id] || id).join(", ") : "Chưa gán bàn";

  const reservationsPaged = usePaged(filteredReservations, 10);

  const unreadNotifs = notifications.filter((n) => !n.da_xem);

  // Trạng thái đang chiếm bàn — phải khớp backend
  // (`table_reservation_service.atomic_hold_or_book_table` lọc
  // `status IN ('held','confirmed','seated')`). Thiếu `held` thì bàn đang giữ
  // tạm cho khách vẫn hiện "Trống", nhân viên dễ xếp nhầm khách vào.
  const activeBookings = reservations.filter((r) => ["held", "confirmed", "seated"].includes(r.status));
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

      <Toasts toasts={toasts} onDismiss={dismiss} />

      {error && <Notice>{error}</Notice>}

      {lastSync && (
        <p className="nq-booking-synced" aria-live="polite">
          <Icon name="refresh" size={13} /> Cập nhật lúc{" "}
          {lastSync.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })} · tự động
          mỗi {AUTO_REFRESH_MS / 1000} giây
        </p>
      )}

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
                  : booking?.status === "held"
                    ? `Đang giữ tạm · ${booking.customer_name}`
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
                  ["held", "Giữ tạm"],
                  ["confirmed", "Đã chốt"],
                  ["seated", "Đang ngồi"],
                  ["needs_review", "Cần duyệt tay"],
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
                <button
                  type="button"
                  className="nq-booking-refresh"
                  onClick={() => loadData()}
                  aria-label="Tải lại dữ liệu"
                >
                  <Icon name="refresh" size={17} /> Tải lại
                </button>
                <button
                  type="button"
                  className="nq-booking-refresh"
                  onClick={() => setShowCreate((v) => !v)}
                  aria-expanded={showCreate}
                  aria-label="Thêm đơn đặt bàn"
                >
                  <Icon name="clipboard" size={17} /> Thêm đơn
                </button>
              </div>
            </div>

            {showCreate && (
              <div className="nq-booking-create">
                <div className="nq-booking-create-grid">
                  <label>
                    Tên khách
                    <input
                      value={form.customer_name}
                      onChange={(e) => setForm({ ...form, customer_name: e.target.value })}
                      placeholder="VD: Anh Nam"
                    />
                  </label>
                  <label>
                    Số điện thoại
                    <input
                      value={form.phone}
                      onChange={(e) => setForm({ ...form, phone: e.target.value })}
                      placeholder="VD: 0901234567"
                      inputMode="tel"
                    />
                  </label>
                  <label>
                    Giờ đến
                    <input
                      type="datetime-local"
                      value={form.booking_time}
                      onChange={(e) => setForm({ ...form, booking_time: e.target.value })}
                    />
                  </label>
                  <label>
                    Số người
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={form.party_size}
                      onChange={(e) => setForm({ ...form, party_size: e.target.value })}
                    />
                  </label>
                </div>
                <div className="nq-booking-create-actions">
                  <Btn variant="primary" busy={creating} onClick={handleCreate}>
                    Tạo đơn
                  </Btn>
                  <Btn variant="ghost" disabled={creating} onClick={() => setShowCreate(false)}>
                    Đóng
                  </Btn>
                </div>
              </div>
            )}

            {filteredReservations.length === 0 ? (
              <Empty title="Không có đơn đặt bàn">Không có đơn đặt bàn nào thỏa mãn điều kiện lọc.</Empty>
            ) : (
              <div className="nq-booking-reservations">
                {reservationsPaged.shown.map((reservation) => {
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
                          <span><Icon name="coffee" size={15} /> <strong>{tableNames(reservation.table_ids)}</strong></span>
                        </div>
                        {reservation.notified_nv_id && (
                          <div className="nq-booking-assignee">
                            <Icon name="users" size={14} /> Ca trực: {staffName(reservation.notified_nv_id)} · {reservation.notification_acked_at ? "Đã xác nhận" : "Chưa xem"}
                          </div>
                        )}
                      </div>

                      <div className="nq-booking-actions">
                        {reservation.status === "confirmed" && (
                          <>
                            <Btn variant="primary" disabled={busyId === reservation.id} onClick={() => handleAction(reservation.id, "check-in")}>Vào bàn</Btn>
                            <Btn variant="danger" disabled={busyId === reservation.id} onClick={() => handleAction(reservation.id, "no-show")}>No-show</Btn>
                            <Btn variant="ghost" disabled={busyId === reservation.id} onClick={() => { setCancelTarget(reservation); setCancelReason(""); }}>Hủy</Btn>
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
            <Pagination
              page={reservationsPaged.page}
              totalPages={reservationsPaged.totalPages}
              onChange={reservationsPaged.setPage}
              from={reservationsPaged.from}
              to={reservationsPaged.to}
              total={reservationsPaged.total}
            />
          </section>
        </>
      )}

      <ConfirmDialog
        open={cancelTarget !== null}
        title="Hủy đơn đặt bàn?"
        body={
          <div>
            <p>
              Đơn của <strong>{cancelTarget?.customer_name}</strong>{" "}
              ({cancelTarget?.phone}) lúc{" "}
              <strong>{cancelTarget?.booking_time.slice(0, 16).replace("T", " ")}</strong> sẽ bị hủy
              và bàn được giải phóng. Thao tác này không khôi phục được.
            </p>
            <label className="nq-booking-cancel-reason">
              Lý do hủy
              <input
                value={cancelReason}
                onChange={(e) => setCancelReason(e.target.value)}
                placeholder="VD: khách gọi báo bận, quán quá tải…"
                aria-label="Lý do hủy đơn"
              />
            </label>
          </div>
        }
        confirmLabel="Hủy đơn"
        cancelLabel="Giữ đơn"
        variant="danger"
        busy={busyId === cancelTarget?.id}
        onConfirm={confirmCancel}
        onCancel={() => {
          setCancelTarget(null);
          setCancelReason("");
        }}
      />
    </div>
  );
}
