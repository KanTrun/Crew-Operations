"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "../../lib/api";
import { actorLabel, hanhViLabel, viError } from "../../lib/present";
import { matchExact, matchSearch, matchTime, TIME_FILTER_OPTIONS, uniqueSorted, type TimeFilter } from "../../lib/list-filters";
import { getToken } from "../../lib/session";
import { subscribeRealtime } from "../../lib/realtime";
import { Alert, AuthGate, Empty, Loading, OpsCard, PageHeader } from "../../ui/kit";
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

function actorLabelEx(ai?: string | null): string {
  if (!ai || ai === "system" || ai === "unknown") return "Hệ thống";
  if (ai === "fb_policy_engine") return "Hệ thống chính sách Facebook";
  if (ai === "fb_moderation_block") return "Hệ thống kiểm duyệt Facebook";
  return actorLabel(ai);
}



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
  nv_id: "Mã nhân viên",
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

// Các trường ẩn khỏi payload (thông tin kỹ thuật / nhạy cảm)
const HIDDEN_KEYS = new Set(["entity_id"]);

// Ngoại lệ: entity_id hiển thị khi không phải session token
function shouldShowEntityId(payload: Record<string, unknown>): boolean {
  const et = payload.entity_type as string | undefined;
  if (et === "session") return false; // token 32 ký tự, không in ra
  const eid = payload.entity_id;
  // Ẩn nếu là hex dài hơn 20 ký tự (token)
  if (typeof eid === "string" && /^[a-f0-9]{20,}$/.test(eid)) return false;
  return eid != null;
}

function payloadValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "boolean") return value ? "Có" : "Không";
  if (typeof value === "string") return PAYLOAD_VALUES[value] ?? value;
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "—";
  try {
    return JSON.stringify(value) ?? "—";
  } catch {
    return "Không đọc được chi tiết";
  }
}

function payloadEntries(row: Row): Array<{ key: string; label: string; value: string; highlight?: boolean }> {
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
      // Ngoại lệ: entity_id hiển thị tùy trường hợp
      if (key === "entity_id" && !shouldShowEntityId(obj)) continue;
      if (key === "entity_id") {
        const et = obj.entity_type as string | undefined;
        const label = et === "user" ? "Tên tài khoản" : "Mã đối tượng";
        if (!(et === "user" && obj.username === value)) {
          entries.push({ key, label, value: payloadValue(value) });
        }
        continue;
      }
      continue;
    }

    let label = PAYLOAD_KEYS[key] ?? key.replace(/_/g, " ");
    let strValue = payloadValue(value);

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

function rowHaystack(it: Row): string {
  return [auditTitle(it), actorLabelEx(it.ai), it.at, JSON.stringify(it.payload ?? it)].filter(Boolean).join(" ");
}

function formatAuditTime(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "—";
  const p2 = (n: number) => String(n).padStart(2, "0");
  return `${p2(d.getDate())}/${p2(d.getMonth() + 1)}/${d.getFullYear()} ${p2(d.getHours())}:${p2(d.getMinutes())}:${p2(d.getSeconds())}`;
}

// ── Icon hành vi ─────────────────────────────────────────────────────────────
//
// Trả về TÊN ICON SVG, không trả ký tự. Bản trước trả ký tự (`✓`, `✕`, `📅`),
// trong đó `📅` là emoji — mà docs/design-guidelines.md cấm emoji làm icon, vì
// emoji do hệ điều hành vẽ nên hình dạng và màu khác nhau trên từng máy, không
// đổi màu theo `currentColor`, và trông không cùng một hệ với phần còn lại.
// Tên icon đi qua <Icon/> nên mọi dấu đều cùng nét, cùng cỡ, cùng ăn màu trạng thái.
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

export default function VetPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [personF, setPersonF] = useState("all");
  const [timeF, setTimeF] = useState<TimeFilter>("all");

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<{ items: Row[] }>("/api/v1/audit")
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

  const personOptions = useMemo(
    () => [{ value: "all", label: "Mọi người" }, ...uniqueSorted(items.map((i) => i.ai)).map((v) => ({ value: v, label: actorLabelEx(v) }))],
    [items],
  );

  const filtered = useMemo(() => {
    return items.filter((it) => {
      if (!matchSearch(rowHaystack(it), search)) return false;
      if (!matchExact(it.ai, personF)) return false;
      if (!matchTime(it.at, timeF)) return false;
      return true;
    });
  }, [items, search, personF, timeF]);

  const filterActive = search.length > 0 || personF !== "all" || timeF !== "all";

  function clearFilters() {
    setSearch("");
    setPersonF("all");
    setTimeF("all");
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Chỉ ghi thêm, không xóa"
        title="Vết hệ thống"
        meta="Mọi lần đổi lịch, duyệt ràng buộc, ghi sổ đều để lại vết ở đây — để tra lại khi cần đối chiếu."
      />
      {error ? <Alert>{error}</Alert> : null}

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

        <div className="nq-list">
          {filtered.map((it, i) => {
            const entries = payloadEntries(it);
            const color = hanhColor(it.hanh);
            const icon = hanhIcon(it.hanh);
            return (
              <article key={it.id ?? `${i}-${it.at ?? ""}`} className="nq-item" style={{ borderLeftWidth: 3, borderLeftColor: color }}>
                {/* Header */}
                <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "0.75rem" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", minWidth: 0 }}>
                    {/* Vòng tròn mang màu của HÀNH VI, icon bên trong cùng màu đó.
                        Dùng <Icon/> nên nét vẽ đồng nhất với phần còn lại của hệ. */}
                    <span
                      className="nq-vet-mark"
                      style={{ background: `color-mix(in srgb, ${color} 18%, transparent)`, color }}
                      aria-hidden="true"
                    >
                      <Icon name={icon} size={14} />
                    </span>
                    <div style={{ minWidth: 0 }}>
                      <p className="nq-item-title" style={{ margin: 0, fontSize: "0.9rem" }}>
                        {auditTitle(it)}
                      </p>
                      <p className="nq-item-sub" style={{ margin: 0 }}>
                        <strong style={{ color: "var(--nq-fg)", fontWeight: 600 }}>{actorLabelEx(it.ai)}</strong>
                        {it.actor_type === "agent" ? (
                          <span style={{
                            display: "inline-flex", alignItems: "center", gap: "0.25rem",
                            marginLeft: "0.4rem", padding: "0.05rem 0.4rem", borderRadius: "999px",
                            fontSize: "0.62rem", fontWeight: 600, letterSpacing: "0.03em",
                            background: "color-mix(in srgb, var(--nq-accent) 16%, transparent)",
                            color: "var(--nq-accent)",
                          }}>
                            AGENT
                          </span>
                        ) : null}
                        {it.controller_user_id && it.controller_user_id !== it.ai ? (
                          <span style={{
                            display: "inline-flex", alignItems: "center", gap: "0.25rem",
                            marginLeft: "0.4rem", fontSize: "0.68rem", color: "var(--nq-ink-muted)",
                          }}>
                            {"· do "}{actorLabel(it.controller_user_id)}
                          </span>
                        ) : null}
                        {" · "}
                        <time className="font-mono" dateTime={it.at}>{formatAuditTime(it.at)}</time>
                      </p>
                    </div>
                  </div>
                  {it.id ? (
                    <span className="font-mono" style={{ fontSize: "0.65rem", color: "var(--nq-accent-ink-text)", flexShrink: 0 }}>
                      #{it.id}
                    </span>
                  ) : null}
                </div>

                {/* Payload chi tiết */}
                {entries.length > 0 && (
                  <dl style={{
                    marginTop: "0.75rem",
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                    gap: "0.5rem 1rem",
                    borderTop: "1px solid color-mix(in srgb, var(--nq-ink-muted) 20%, transparent)",
                    paddingTop: "0.6rem",
                  }}>
                    {entries.map(({ key, label, value, highlight }) => (
                      <div key={key} style={{ minWidth: 0 }}>
                        <dt style={{
                          fontSize: "0.6rem", textTransform: "uppercase", letterSpacing: "0.08em",
                          color: "var(--nq-ink-muted)", marginBottom: "0.15rem",
                        }}>
                          {label}
                        </dt>
                        <dd style={{
                          margin: 0, fontSize: "0.82rem", wordBreak: "break-word",
                          color: highlight ? color : "var(--nq-fg)",
                          fontWeight: highlight ? 600 : 400,
                        }}>
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
      </OpsCard>
    </div>
  );
}
