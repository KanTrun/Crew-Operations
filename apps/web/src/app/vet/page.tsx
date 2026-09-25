"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "../../lib/api";
import { hanhViLabel, viError } from "../../lib/present";
import { matchExact, matchSearch, matchTime, TIME_FILTER_OPTIONS, uniqueSorted, type TimeFilter } from "../../lib/list-filters";
import { getToken } from "../../lib/session";
import { subscribeRealtime } from "../../lib/realtime";
import { useActorName } from "../../ui/ops-pickers";
import { Alert, AuthGate, Empty, Loading, OpsCard, PageGrid, PageHeader, Pagination, usePaged } from "../../ui/kit";
import { Icon } from "../../ui/icons";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type Row = {
  id?: number;
  at?: string;
  ai?: string;
  hanh?: string;
  payload?: Record<string, unknown> | unknown;
  actor_type?: string;
  agent_name?: string;
  controller_user_id?: string;
  [key: string]: unknown;
};

// ── Bản dịch ─────────────────────────────────────────────────────────────────

const ENTITY_TYPES: Record<string, string> = {
  schedule: "Lịch tuần",
  user: "Người dùng",
  session: "Phiên đăng nhập",
  meeting: "Phiên duyệt luật",
  rule: "Luật cẩm nang",
  swap: "Lệnh đổi ca",
  shift_swap: "Yêu cầu đổi ca",
  shift: "Ca làm việc",
  attendance: "Lượt điểm danh",
  operation: "Thao tác hệ thống",
};

// Khoá payload có giá trị là mã nhân viên — cần đổi thành tên thật khi render.
const STAFF_ID_KEYS = new Set(["nv_id", "selected_nv_id", "selected_candidate", "a", "b", "c"]);
const STAFF_ID_LIST_KEYS = new Set(["dong_y"]);

const PAYLOAD_KEYS: Record<string, string> = {
  entity_type: "Loại đối tượng",
  from: "Trạng thái cũ",
  to: "Trạng thái mới",
  ly_do: "Lý do",
  username: "Tên tài khoản",
  cap_quyen: "Cấp quyền",
  roster_id: "Mã lịch",
  old_solver: "Trợ lý ảo cũ",
  new_solver: "Trợ lý ảo mới",
  action: "Hành động",
  rule_id: "Mã luật",
  role: "Vai trò",
  q: "Quyết định",
  y: "Ý định",
  nv_id: "Nhân viên",
  ca_id: "Mã ca",
  meeting_id: "Mã cuộc họp",
  tieu_de: "Tiêu đề",
  tasks_created: "Việc đã tạo",
  sop_proposals: "Đề xuất SOP",
  schedule_adjustments: "Điều chỉnh lịch",
  inbox_leaves: "Đơn nghỉ",
  pins_created: "Lượt ghim ca",
  recalled_tasks: "Việc đã thu hồi",
  recalled_sop: "Đề xuất SOP đã thu hồi",
  recalled_leaves: "Đơn nghỉ đã thu hồi",
  selected_candidate: "Nhân viên được chọn",
  selected_nv_id: "Nhân viên được chọn",
  dong_y: "Người đã đồng ý",
  a: "Người nhả ca",
  b: "Người nhận ca",
  c: "Người xác nhận",
  trang_thai: "Trạng thái",
  reason: "Lý do",
  status: "Trạng thái",
  id: "Mã bản ghi",
  thread_id: "Mã hội thoại",
  text: "Nội dung",
  graph_sent: "Đã gửi Facebook",
  suggested: "Nội dung gợi ý",
  final: "Nội dung đã duyệt",
  diff_detected: "Có chỉnh sửa",
  count: "Số lượng",
  source: "Cách thực hiện",
  method: "Phương thức",
  route: "Chức năng",
  // entity_id ẩn theo từng loại — xử lý riêng bên dưới
};

const PAYLOAD_VALUES: Record<string, string> = {
  quan_ly: "Quản lý",
  chu_quan: "Chủ quán",
  nhan_vien: "Nhân viên",
  may_sinh: "Máy sinh",
  nhap: "Bản nháp",
  dang_giai: "Đang giải lịch",
  cho_duyet: "Chờ duyệt",
  da_duyet: "Đã duyệt",
  da_cong_bo: "Đã công bố",
  da_dong: "Đã đóng",
  duyet: "Duyệt",
  tu_choi: "Từ chối",
  chuyen_cap: "Chuyển cấp",
  sua_gui: "Sửa rồi gửi",
  cho_3_nhanh: "Chờ ba người đồng ý",
  dong_y: "Đã đủ người đồng ý",
  manual: "Điểm danh trực tiếp",
  qr: "Quét mã QR",
};

const ROUTE_AREAS: Array<[prefix: string, label: string]> = [
  ["/api/v1/lich-tuan", "Lịch tuần"],
  ["/api/v1/lich/lifecycle", "Trạng thái lịch tuần"],
  ["/api/v1/phieu", "Phiếu ca"],
  ["/api/v1/viec-treo", "Việc treo"],
  ["/api/v1/inbox", "Hộp thư vận hành"],
  ["/api/v1/tkb", "Lịch bận nhân viên"],
  ["/api/v1/ca/", "Ca làm việc"],
  ["/api/v1/import/nhan-vien", "Nhập danh sách nhân viên"],
  ["/api/v1/meeting", "Cuộc họp"],
  ["/api/v1/meetings", "Biên bản cuộc họp"],
  ["/api/v1/chat", "Chat nội bộ"],
  ["/api/v1/reservations", "Đặt bàn"],
  ["/api/v1/ai", "Vận hành AI"],
  ["/api/v1/page", "Page quán"],
  ["/api/v1/store", "Hồ sơ quán"],
  ["/api/v1/me/profile", "Hồ sơ cá nhân"],
  ["/api/v1/mail", "Gửi email"],
  ["/api/v1/gmail", "Quản lý Gmail"],
  ["/api/v1/copilot", "Trợ lý vận hành"],
  ["/api/v1/orc", "Điều phối tác vụ"],
  ["/api/v1/msg", "Phân loại tin nhắn"],
  ["/api/v1/channels", "Liên kết kênh"],
  ["/api/v1/skills", "Kỹ năng AI"],
  ["/api/v1/pricing", "Khảo sát giá"],
];

function routeArea(value: string): string {
  return ROUTE_AREAS.find(([prefix]) => value.startsWith(prefix))?.[1] ?? "Chức năng vận hành";
}

const OPERATION_TITLES: Record<string, string> = {
  "PATCH /api/v1/lich-tuan/khung-gio": "Điều chỉnh khung giờ lịch tuần",
  "POST /api/v1/lich-tuan/nv-status": "Cập nhật trạng thái nhân viên trên lịch",
  "POST /api/v1/lich-tuan/xac-nhan-lich": "Xác nhận lịch làm việc",
  "POST /api/v1/phieu/start": "Mở phiếu ca",
  "POST /api/v1/phieu/{phieu_id}/buoc": "Hoàn thành bước trong phiếu ca",
  "POST /api/v1/phieu/{phieu_id}/minh-chung": "Thêm minh chứng vào phiếu ca",
  "POST /api/v1/phieu/{phieu_id}/treo": "Tạo việc treo từ phiếu ca",
  "PATCH /api/v1/viec-treo/{treo_id}": "Cập nhật việc treo",
  "POST /api/v1/inbox": "Gửi nội dung vào hộp thư vận hành",
  "POST /api/v1/msg/classify": "Phân loại tin nhắn vận hành",
  "POST /api/v1/tkb/extract": "Đọc lịch bận nhân viên",
  "POST /api/v1/tkb/upload": "Tải ảnh lịch bận",
  "POST /api/v1/tkb/confirm": "Xác nhận lịch bận",
  "POST /api/v1/ca/nha": "Nhả ca làm việc",
  "POST /api/v1/ca/nhan": "Nhận ca làm việc",
  "POST /api/v1/import/nhan-vien": "Nhập danh sách nhân viên",
  "POST /api/v1/meeting/transcribe": "Chuyển ghi âm giao ca thành văn bản",
  "POST /api/v1/meeting/analyze": "Phân tích nội dung giao ca",
  "POST /api/v1/meeting/process-audio": "Ghi âm giao ca",
  "POST /api/v1/meeting/clarify-actions": "Làm rõ việc cần làm sau giao ca",
  "PUT /api/v1/meetings/{meeting_id}/draft": "Sửa biên bản giao ca",
  "PATCH /api/v1/me/profile/email": "Cập nhật email cá nhân",
  "POST /api/v1/mail/send": "Gửi email",
  "POST /api/v1/gmail/accounts": "Thêm tài khoản Gmail",
  "PATCH /api/v1/gmail/accounts/{account_id}": "Cập nhật tài khoản Gmail",
  "DELETE /api/v1/gmail/accounts/{account_id}": "Xoá tài khoản Gmail",
  "POST /api/v1/gmail/oauth/callback": "Kết nối Gmail qua Google",
  "POST /api/v1/gmail/oauth/revoke": "Thu hồi quyền truy cập Gmail",
  "POST /api/v1/gmail/sync": "Đồng bộ hộp thư Gmail",
  "POST /api/v1/gmail/accounts/{account_id}/send": "Gửi email qua Gmail API",
  "POST /api/v1/gmail/accounts/{account_id}/labels": "Tạo nhãn Gmail",
  "DELETE /api/v1/gmail/accounts/{account_id}/labels/{label_id}": "Xoá nhãn Gmail",
  "POST /api/v1/gmail/accounts/{account_id}/filters": "Tạo bộ lọc Gmail",
  "DELETE /api/v1/gmail/accounts/{account_id}/filters/{filter_id}": "Xoá bộ lọc Gmail",
  "POST /api/v1/gmail/accounts/{account_id}/messages/{message_id}/read": "Đánh dấu email đã đọc",
  "POST /api/v1/gmail/accounts/{account_id}/messages/{message_id}/star": "Gắn sao email",
  "POST /api/v1/chat/conversations": "Tạo cuộc trò chuyện nội bộ",
  "POST /api/v1/chat/conversations/{conv_id}/messages": "Gửi tin nhắn nội bộ",
  "POST /api/v1/chat/messages/{message_id}/pin": "Ghim tin nhắn nội bộ",
  "PATCH /api/v1/chat/messages/{message_id}": "Sửa tin nhắn nội bộ",
  "DELETE /api/v1/chat/messages/{message_id}": "Thu hồi tin nhắn nội bộ",
  "POST /api/v1/chat/messages/{message_id}/treo": "Tạo việc treo từ tin nhắn",
  "POST /api/v1/chat/messages/{message_id}/reactions": "Bày tỏ cảm xúc với tin nhắn",
  "POST /api/v1/chat/conversations/{conv_id}/mute": "Đổi chế độ thông báo cuộc trò chuyện",
  "POST /api/v1/reservations/{res_id}/check-in": "Xác nhận khách đến bàn",
  "POST /api/v1/reservations/{res_id}/no-show": "Ghi nhận khách không đến",
  "POST /api/v1/reservations/{res_id}/complete": "Hoàn tất lượt đặt bàn",
  "POST /api/v1/reservations/{res_id}/cancel": "Hủy lượt đặt bàn",
  "POST /api/v1/channels/bind/issue": "Tạo mã liên kết kênh",
  "POST /api/v1/channels/replay": "Chạy lại sự kiện từ kênh",
  "POST /api/v1/page/sync": "Đồng bộ Page quán",
  "POST /api/v1/page/drafts/ai-generate": "Tạo bản nháp Page bằng AI",
  "POST /api/v1/page/drafts/{draft_id}": "Cập nhật bản nháp Page",
  "POST /api/v1/page/treo": "Tạo việc treo từ Page quán",
  "POST /api/v1/ai/feedback": "Gửi phản hồi cho AI",
  "POST /api/v1/ai/operations/circuit-breaker": "Thay đổi trạng thái vận hành AI",
  "POST /api/v1/ai/reflection/gmail/run": "Chạy tự đánh giá AI Gmail",
  "POST /api/v1/ai/reflection/facebook/run": "Chạy tự đánh giá AI Facebook",
  "POST /api/v1/copilot/upload": "Tải tệp cho trợ lý vận hành",
  "POST /api/v1/copilot/message": "Gửi yêu cầu cho trợ lý vận hành",
  "POST /api/v1/copilot/execute-action": "Thực thi đề xuất của trợ lý",
};

function auditTitle(row: Row): string {
  if (row.hanh !== "operation.mutation") return hanhViLabel(row.hanh);
  const payload = row.payload;
  if (!payload || typeof payload !== "object") return hanhViLabel(row.hanh);
  const details = payload as Record<string, unknown>;
  const method = typeof details.method === "string" ? details.method.toUpperCase() : "";
  const route = typeof details.route === "string" ? details.route : "";
  const exact = OPERATION_TITLES[`${method} ${route}`];
  if (exact) return exact;
  const verb = method === "DELETE" ? "Xóa" : method === "POST" ? "Thực hiện" : "Cập nhật";
  return `${verb} ${routeArea(route).toLocaleLowerCase("vi-VN")}`;
}

function eventArea(row: Row): string {
  const payload = row.payload;
  if (payload && typeof payload === "object") {
    const route = (payload as Record<string, unknown>).route;
    if (typeof route === "string" && route) return routeArea(route);
    const entityType = (payload as Record<string, unknown>).entity_type;
    if (typeof entityType === "string" && ENTITY_TYPES[entityType]) return ENTITY_TYPES[entityType];
  }
  const hanh = row.hanh ?? "";
  if (hanh.startsWith("schedule.") || hanh.startsWith("shift_swap.") || hanh.startsWith("constraint.")) return "Lịch tuần";
  if (hanh.startsWith("attendance.")) return "Điểm danh QR";
  if (hanh.startsWith("meeting.")) return "Họp & giao ca";
  if (hanh.startsWith("user.") || hanh.startsWith("role.")) return "Người dùng";
  return "Vận hành chung";
}

// Các trường ẩn khỏi payload (thông tin kỹ thuật / nhạy cảm)
const HIDDEN_KEYS = new Set(["entity_id"]);

function shouldShowEntityId(payload: Record<string, unknown>): boolean {
  const et = payload.entity_type as string | undefined;
  if (et === "session") return false; // token 32 ký tự, không in ra
  const eid = payload.entity_id;
  if (typeof eid === "string" && /^[a-f0-9]{20,}$/.test(eid)) return false;
  return eid != null;
}

function payloadValue(value: unknown, key: string, resolveStaff: (id: string) => string): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "string") {
    if (STAFF_ID_KEYS.has(key) && /^nv_\d+$/i.test(value)) return resolveStaff(value);
    return PAYLOAD_VALUES[value] ?? value;
  }
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "—";
  if (Array.isArray(value)) {
    if (value.length === 0) return "—";
    if (STAFF_ID_LIST_KEYS.has(key)) {
      return value
        .map((v) => (typeof v === "string" && /^nv_\d+$/i.test(v) ? resolveStaff(v) : String(v)))
        .join(", ");
    }
    if (value.every((v) => v == null || typeof v !== "object")) return value.map(String).join(", ");
    return `${value.length} mục`;
  }
  if (typeof value === "object") {
    const keys = Object.keys(value as object);
    return keys.length
      ? keys
          .map((k) => `${PAYLOAD_KEYS[k] ?? k.replace(/_/g, " ")}: ${payloadValue((value as Record<string, unknown>)[k], k, resolveStaff)}`)
          .join(" · ")
      : "—";
  }
  return String(value);
}

function payloadEntries(
  row: Row,
  resolveStaff: (id: string) => string,
): Array<{ key: string; label: string; value: string; highlight?: boolean }> {
  const payload = row.payload ?? Object.fromEntries(
    Object.entries(row).filter(([key]) => !["id", "at", "ai", "hanh"].includes(key)),
  );
  if (!payload || typeof payload !== "object") {
    return [{ key: "chi_tiet", label: "Chi tiết", value: String(payload) }];
  }
  const obj = payload as Record<string, unknown>;
  const entries: Array<{ key: string; label: string; value: string; highlight?: boolean }> = [];

  for (const [key, value] of Object.entries(obj)) {
    if (HIDDEN_KEYS.has(key)) {
      if (key === "entity_id" && !shouldShowEntityId(obj)) continue;
      if (key === "entity_id") {
        const et = obj.entity_type as string | undefined;
        const label = et === "user" ? "Tên tài khoản" : "Mã đối tượng";
        if (!(et === "user" && obj.username === value)) {
          entries.push({ key, label, value: payloadValue(value, key, resolveStaff) });
        }
        continue;
      }
      continue;
    }

    const label = PAYLOAD_KEYS[key] ?? key.replace(/_/g, " ");
    let strValue = payloadValue(value, key, resolveStaff);

    if (key === "entity_type") {
      strValue = ENTITY_TYPES[strValue] ?? strValue;
    } else if (key === "route") {
      strValue = routeArea(strValue);
    }

    const highlight = key === "ly_do" || key === "to" || key === "action";
    entries.push({ key, label, value: strValue, highlight });
  }

  return entries;
}

function rowHaystack(it: Row, actorName: (a?: string | null) => string): string {
  return [auditTitle(it), actorName(it.ai), eventArea(it), it.at, JSON.stringify(it.payload ?? it)]
    .filter(Boolean)
    .join(" ");
}

function formatAuditTime(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const p2 = (n: number) => String(n).padStart(2, "0");
  return `${p2(d.getHours())}:${p2(d.getMinutes())}`;
}

function formatDayHeading(value?: string | null): string {
  if (!value) return "Không rõ ngày";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "Không rõ ngày";
  const today = new Date();
  const isSameDay = (a: Date, b: Date) => a.toDateString() === b.toDateString();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (isSameDay(d, today)) return "Hôm nay";
  if (isSameDay(d, yesterday)) return "Hôm qua";
  const p2 = (n: number) => String(n).padStart(2, "0");
  return `${p2(d.getDate())}/${p2(d.getMonth() + 1)}/${d.getFullYear()}`;
}

function dayKey(value?: string | null): string {
  if (!value) return "unknown";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "unknown";
  return d.toDateString();
}

// ── Icon hành vi ─────────────────────────────────────────────────────────────
type VetIcon = "x-mark" | "arrow-right" | "refresh" | "calendar" | "check" | "warn" | "zap" | "info";

function hanhIcon(hanh?: string | null): VetIcon {
  if (!hanh) return "info";
  if (hanh.startsWith("user.login_failed")) return "x-mark";
  if (hanh.startsWith("user.login")) return "arrow-right";
  if (hanh.startsWith("role.promote") || hanh.startsWith("role.demote")) return "warn";
  if (hanh.startsWith("schedule.lifecycle_reopen")) return "refresh";
  if (hanh.startsWith("schedule.")) return "calendar";
  if (hanh.startsWith("shift_swap.")) return "refresh";
  if (hanh.startsWith("attendance.")) return "check";
  if (hanh.startsWith("meeting.approve")) return "check";
  if (hanh.startsWith("meeting.reject") || hanh.startsWith("meeting.rollback")) return "x-mark";
  if (hanh.startsWith("meeting.")) return "zap";
  return "info";
}

function hanhColor(hanh?: string | null): string {
  if (!hanh) return "var(--nq-accent)";
  if (hanh.includes("failed") || hanh.includes("reject") || hanh.includes("demote")) return "var(--nq-danger)";
  if (hanh.includes("approve") || hanh.includes("login") || hanh.includes("promote")) return "var(--nq-ok)";
  if (hanh.includes("reopen") || hanh.includes("rollback")) return "var(--nq-warn)";
  return "var(--nq-accent)";
}

// ── Component chính ───────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

export default function VetPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [personF, setPersonF] = useState("all");
  const [timeF, setTimeF] = useState<TimeFilter>("all");
  const actorName = useActorName();

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<{ items: Row[] }>("/api/v1/audit?limit=500")
      .then((d) => {
        setItems(d.items ?? []);
        setError(null);
      })
      .catch((e) =>
        setError(
          viError(e, {
            doing: "đọc được vết hệ thống",
            forbidden: "Chỉ quản lý và chủ quán mới có quyền đọc nhật ký vết hệ thống bảo mật.",
          }),
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  useEffect(() => {
    if (!token) return;
    return subscribeRealtime((packet) => {
      if (packet.event === "ops:changed") load();
    });
  }, [token, load]);

  const resolveStaff = useCallback((id: string) => actorName(id), [actorName]);

  const personOptions = useMemo(
    () => [{ value: "all", label: "Mọi người" }, ...uniqueSorted(items.map((i) => i.ai)).map((v) => ({ value: v, label: actorName(v) }))],
    [items, actorName],
  );

  const filtered = useMemo(() => {
    return items.filter((it) => {
      if (!matchSearch(rowHaystack(it, actorName), search)) return false;
      if (!matchExact(it.ai, personF)) return false;
      if (!matchTime(it.at, timeF)) return false;
      return true;
    });
  }, [items, search, personF, timeF, actorName]);

  const filterActive = search.length > 0 || personF !== "all" || timeF !== "all";

  function clearFilters() {
    setSearch("");
    setPersonF("all");
    setTimeF("all");
  }

  // Bảng "Hoạt động theo người" — ai chạm vào hệ thống nhiều nhất, ở khu vực nào.
  const activitySummary = useMemo(() => {
    const byActor = new Map<string, { name: string; count: number; areas: Map<string, number> }>();
    for (const it of items) {
      const key = it.ai ?? "unknown";
      const name = actorName(it.ai);
      const entry = byActor.get(key) ?? { name, count: 0, areas: new Map<string, number>() };
      entry.count += 1;
      const area = eventArea(it);
      entry.areas.set(area, (entry.areas.get(area) ?? 0) + 1);
      byActor.set(key, entry);
    }
    return Array.from(byActor.values())
      .sort((a, b) => b.count - a.count)
      .slice(0, 8)
      .map((e) => ({
        name: e.name,
        count: e.count,
        topArea: Array.from(e.areas.entries()).sort((a, b) => b[1] - a[1])[0]?.[0] ?? "—",
      }));
  }, [items, actorName]);

  const grouped = useMemo(() => {
    const groups = new Map<string, { heading: string; rows: Row[] }>();
    for (const it of filtered) {
      const key = dayKey(it.at);
      const g = groups.get(key) ?? { heading: formatDayHeading(it.at), rows: [] };
      g.rows.push(it);
      groups.set(key, g);
    }
    return Array.from(groups.values());
  }, [filtered]);

  const { page, setPage, totalPages, shown, total, from, to } = usePaged(grouped, PAGE_SIZE);

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Chỉ ghi thêm, không xóa"
        title="Vết hệ thống"
        meta="Ai đã làm gì, ở trang nào, lúc nào — viết bằng câu thường, không mã nội bộ."
      />
      {error ? <Alert>{error}</Alert> : null}

      <PageGrid
        main={
          <OpsCard eyebrow="Nhật ký" title="Các vết gần đây" count={filtered.length} countLabel="vết">
            <ListToolbar
              search={search}
              onSearchChange={setSearch}
              searchPlaceholder="Tìm hành vi, người thực hiện…"
              person={personF}
              onPersonChange={setPersonF}
              personOptions={personOptions}
              personLabel="Người thực hiện"
              time={timeF}
              onTimeChange={(v) => setTimeF(v as TimeFilter)}
              timeOptions={TIME_FILTER_OPTIONS}
              shown={filtered.length}
              total={items.length}
              filtered={filterActive}
            />

            {loading ? <Loading skeleton="list">Đang đọc vết hệ thống…</Loading> : null}
            {!loading && !error && items.length === 0 ? (
              <Empty title="Chưa có vết">Chuyển trạng thái lịch hoặc duyệt hộp thư sẽ sinh vết đầu tiên.</Empty>
            ) : null}
            {!loading && items.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}

            {shown.map((group) => (
              <div key={group.heading + group.rows[0]?.id} className="nq-vet-day-group">
                <h3 className="nq-vet-day-heading">{group.heading}</h3>
                <div className="nq-list">
                  {group.rows.map((it, i) => {
                    const entries = payloadEntries(it, resolveStaff);
                    const color = hanhColor(it.hanh);
                    const icon = hanhIcon(it.hanh);
                    const actor = actorName(it.ai);
                    const area = eventArea(it);
                    return (
                      <article key={it.id ?? `${i}-${it.at ?? ""}`} className="nq-item" style={{ borderLeftWidth: 3, borderLeftColor: color }}>
                        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "0.75rem" }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", minWidth: 0 }}>
                            <span
                              className="nq-vet-mark"
                              style={{ background: `color-mix(in srgb, ${color} 18%, transparent)`, color }}
                              aria-hidden="true"
                            >
                              <Icon name={icon} size={14} />
                            </span>
                            <div style={{ minWidth: 0 }}>
                              <p className="nq-item-title" style={{ margin: 0, fontSize: "0.92rem" }}>
                                <strong style={{ color: "var(--nq-fg)", fontWeight: 700 }}>{actor}</strong>{" "}
                                <span style={{ color: "var(--nq-ink-muted)", fontWeight: 400 }}>đã</span>{" "}
                                {auditTitle(it).toLocaleLowerCase("vi-VN")}
                              </p>
                              <p className="nq-item-sub" style={{ margin: "0.15rem 0 0" }}>
                                <span
                                  style={{
                                    display: "inline-flex",
                                    alignItems: "center",
                                    padding: "0.05rem 0.5rem",
                                    borderRadius: "999px",
                                    fontSize: "0.68rem",
                                    fontWeight: 600,
                                    background: "color-mix(in srgb, var(--nq-accent) 12%, transparent)",
                                    color: "var(--nq-accent)",
                                  }}
                                >
                                  {area}
                                </span>
                                {it.actor_type === "agent" ? (
                                  <span
                                    style={{
                                      display: "inline-flex",
                                      alignItems: "center",
                                      gap: "0.25rem",
                                      marginLeft: "0.4rem",
                                      padding: "0.05rem 0.4rem",
                                      borderRadius: "999px",
                                      fontSize: "0.62rem",
                                      fontWeight: 600,
                                      letterSpacing: "0.03em",
                                      background: "color-mix(in srgb, var(--nq-ok) 16%, transparent)",
                                      color: "var(--nq-ok)",
                                    }}
                                  >
                                    AI TỰ ĐỘNG
                                  </span>
                                ) : null}
                                {it.controller_user_id && it.controller_user_id !== it.ai ? (
                                  <span style={{ marginLeft: "0.4rem", fontSize: "0.72rem", color: "var(--nq-ink-muted)" }}>
                                    · do {actorName(it.controller_user_id)}
                                  </span>
                                ) : null}
                                <time className="font-mono" dateTime={it.at} style={{ marginLeft: "0.4rem", fontSize: "0.72rem", color: "var(--nq-ink-muted)" }}>
                                  · {formatAuditTime(it.at)}
                                </time>
                              </p>
                            </div>
                          </div>
                          {it.id ? (
                            <span className="font-mono" style={{ fontSize: "0.65rem", color: "var(--nq-accent-ink-text)", flexShrink: 0 }}>
                              #{it.id}
                            </span>
                          ) : null}
                        </div>

                        {entries.length > 0 && (
                          <dl
                            style={{
                              marginTop: "0.75rem",
                              display: "grid",
                              gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
                              gap: "0.5rem 1rem",
                              borderTop: "1px solid color-mix(in srgb, var(--nq-ink-muted) 20%, transparent)",
                              paddingTop: "0.6rem",
                            }}
                          >
                            {entries.map(({ key, label, value, highlight }) => (
                              <div key={key} style={{ minWidth: 0 }}>
                                <dt
                                  style={{
                                    fontSize: "0.6rem",
                                    textTransform: "uppercase",
                                    letterSpacing: "0.08em",
                                    color: "var(--nq-ink-muted)",
                                    marginBottom: "0.15rem",
                                  }}
                                >
                                  {label}
                                </dt>
                                <dd
                                  style={{
                                    margin: 0,
                                    fontSize: "0.82rem",
                                    wordBreak: "break-word",
                                    color: highlight ? color : "var(--nq-fg)",
                                    fontWeight: highlight ? 600 : 400,
                                  }}
                                >
                                  {value}
                                </dd>
                              </div>
                            ))}
                          </dl>
                        )}
                      </article>
                    );
                  })}
                </div>
              </div>
            ))}

            <Pagination page={page} totalPages={totalPages} onChange={setPage} from={from} to={to} total={total} />
          </OpsCard>
        }
        aside={
          <OpsCard eyebrow="Tổng hợp" title="Hoạt động theo người" density="compact">
            {activitySummary.length === 0 ? (
              <p className="nq-muted text-sm">Chưa có dữ liệu để tổng hợp.</p>
            ) : (
              <div className="nq-list">
                {activitySummary.map((row) => (
                  <div key={row.name} className="nq-surface-row nq-surface-row--between">
                    <div style={{ minWidth: 0 }}>
                      <p style={{ margin: 0, fontWeight: 600, fontSize: "0.85rem" }}>{row.name}</p>
                      <p className="nq-muted" style={{ margin: 0, fontSize: "0.72rem" }}>
                        Nhiều nhất ở {row.topArea.toLocaleLowerCase("vi-VN")}
                      </p>
                    </div>
                    <span className="font-mono" style={{ fontSize: "0.78rem", color: "var(--nq-accent)" }}>
                      {row.count}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </OpsCard>
        }
      />
    </div>
  );
}
