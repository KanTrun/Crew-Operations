"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { matchSearch } from "../../lib/list-filters";
import { viError } from "../../lib/present";
import { getRole, getToken, isChuQuan, roleLabel } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  ConfirmDialog,
  Empty,
  Loading,
  Notice,
  PageHeader,
  StatusChip,
  Summary,
  Toasts,
  useToasts,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type User = { username: string; role: string; nv_id: string; display_name: string };
type RoleFilter = "all" | "chu_quan" | "quan_ly" | "nhan_vien";
type PendingAction = { kind: "promote" | "demote"; user: User };

const ROLE_ORDER: Record<string, number> = {
  chu_quan: 0,
  quan_ly: 1,
  nhan_vien: 2,
};

function userHaystack(u: User): string {
  return [u.display_name, u.username, u.nv_id, roleLabel(u.role)].join(" ");
}

function userInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function roleTone(role: string): "ok" | "warn" | "default" {
  if (role === "chu_quan") return "ok";
  if (role === "quan_ly") return "warn";
  return "default";
}

export default function NguoiPage() {
  const [token, setToken] = useState("");
  const [myRole, setMyRole] = useState("");
  const [items, setItems] = useState<User[]>([]);
  const [filter, setFilter] = useState<RoleFilter>("all");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingAction | null>(null);
  const { toasts, push, dismiss } = useToasts();

  const load = useCallback(async () => {
    if (!getToken()) return;
    setLoading(true);
    try {
      const out = await apiGet<{ items: User[] }>("/api/v1/nguoi");
      setItems(out.items ?? []);
      setError(null);
    } catch (e) {
      setError(viError(e, { doing: "mở danh sách người dùng" }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setToken(getToken());
    setMyRole(getRole());
  }, []);
  useEffect(() => {
    if (token) void load();
  }, [load, token]);

  const counts = useMemo(() => {
    const c = { all: items.length, chu_quan: 0, quan_ly: 0, nhan_vien: 0 };
    for (const u of items) {
      if (u.role === "chu_quan") c.chu_quan += 1;
      else if (u.role === "quan_ly") c.quan_ly += 1;
      else if (u.role === "nhan_vien") c.nhan_vien += 1;
    }
    return c;
  }, [items]);

  const filtered = useMemo(() => {
    const roleFiltered = filter === "all" ? items : items.filter((u) => u.role === filter);
    const searched = roleFiltered.filter((u) => matchSearch(userHaystack(u), search));
    return [...searched].sort((a, b) => {
      const ra = ROLE_ORDER[a.role] ?? 9;
      const rb = ROLE_ORDER[b.role] ?? 9;
      if (ra !== rb) return ra - rb;
      return a.display_name.localeCompare(b.display_name, "vi");
    });
  }, [filter, items, search]);

  const filteredActive = filter !== "all" || search.trim().length > 0;
  const canManage = isChuQuan(myRole);

  async function runPending() {
    if (!pending) return;
    const { kind, user } = pending;
    setBusy(user.username);
    setError(null);
    try {
      if (kind === "promote") {
        await apiSend(`/api/v1/nguoi/${user.username}/nang-vai`, {});
        push(`Đã nâng @${user.username} lên quản lý ca.`);
      } else {
        await apiSend(`/api/v1/nguoi/${user.username}/ha-vai`, {});
        push(`Đã hạ @${user.username} xuống nhân viên.`);
      }
      setPending(null);
      await load();
    } catch (e) {
      setError(viError(e, { doing: kind === "promote" ? "nâng vai người dùng" : "hạ vai người dùng" }));
    } finally {
      setBusy("");
    }
  }

  function clearFilters() {
    setFilter("all");
    setSearch("");
  }

  if (!token) return <AuthGate />;

  const tabs: { id: RoleFilter; label: string }[] = [
    { id: "all", label: "Tất cả" },
    { id: "chu_quan", label: "Chủ quán" },
    { id: "quan_ly", label: "Quản lý" },
    { id: "nhan_vien", label: "Nhân viên" },
  ];

  return (
    <>
      <Toasts toasts={toasts} onDismiss={dismiss} />
      <ConfirmDialog
        open={pending !== null}
        title={pending?.kind === "promote" ? "Nâng lên quản lý ca" : "Hạ xuống nhân viên"}
        body={
          pending ? (
            <>
              <p>
                {pending.kind === "promote" ? (
                  <>
                    Bạn sắp nâng <strong>@{pending.user.username}</strong> ({pending.user.display_name}) lên{" "}
                    <strong>quản lý ca</strong>. Người này sẽ duyệt inbox, chỉnh lịch và xem báo cáo quán.
                  </>
                ) : (
                  <>
                    Bạn sắp hạ <strong>@{pending.user.username}</strong> ({pending.user.display_name}) xuống{" "}
                    <strong>nhân viên</strong>. Quyền quản lý inbox và lịch tuần sẽ bị thu hồi ngay.
                  </>
                )}
              </p>
              <p className="nq-muted text-xs mt-3">Vai trò chủ quán không thể đổi qua trang này.</p>
            </>
          ) : null
        }
        confirmLabel={pending?.kind === "promote" ? "Nâng quản lý" : "Hạ nhân viên"}
        variant={pending?.kind === "demote" ? "danger" : "primary"}
        busy={Boolean(busy)}
        onConfirm={() => void runPending()}
        onCancel={() => !busy && setPending(null)}
      />

      <section className="nq-page nq-page--nguoi">
        <PageHeader
          kicker="Admin quán"
          title="Người dùng"
          meta="Quản lý vai trò nhân sự: nâng nhân viên lên quản lý ca hoặc hạ quản lý xuống nhân viên. Chỉ chủ quán thực hiện được thay đổi."
        />

        {error ? <Alert>{error}</Alert> : null}

        {!loading ? (
          <Summary
            cells={[
              { n: counts.all, k: "Tổng tài khoản" },
              { n: counts.chu_quan, k: "Chủ quán", tone: "ok" },
              { n: counts.quan_ly, k: "Quản lý ca", tone: "warn" },
              { n: counts.nhan_vien, k: "Nhân viên" },
            ]}
          />
        ) : null}

        {!canManage ? (
          <Notice>Bạn đang xem danh sách ở chế độ chỉ đọc. Chỉ chủ quán mới nâng hoặc hạ vai trò.</Notice>
        ) : null}

        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm tên, @tài khoản hoặc mã NV…"
          shown={filtered.length}
          total={items.length}
          filtered={filteredActive}
        />

        <div className="nq-filter-tabs nq-filter-tabs--counts" role="tablist" aria-label="Lọc vai trò">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={filter === t.id}
              className={`nq-filter-tab ${filter === t.id ? "nq-filter-tab--on" : ""}`}
              onClick={() => setFilter(t.id)}
            >
              <span>{t.label}</span>
              <span className="nq-filter-tab__count" aria-hidden="true">
                {counts[t.id]}
              </span>
            </button>
          ))}
        </div>

        {loading ? <Loading skeleton="table" rows={5}>Đang tải người dùng…</Loading> : null}

        {!loading && items.length === 0 ? (
          <Empty title="Chưa có người dùng">Danh sách trống — nhân viên đăng ký sẽ xuất hiện ở đây.</Empty>
        ) : null}

        {!loading && items.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}

        {!loading && filtered.length > 0 ? (
          <div className="nq-data-table-wrap nq-user-table-wrap">
            <table className="nq-data-table nq-user-table">
              <caption className="sr-only">Danh sách người dùng và vai trò</caption>
              <thead>
                <tr>
                  <th scope="col">Nhân sự</th>
                  <th scope="col" className="nq-user-table__hide-sm">
                    Mã NV
                  </th>
                  <th scope="col">Vai trò</th>
                  <th scope="col" className="nq-user-table__actions-head">
                    {canManage ? "Thay đổi vai" : "Ghi chú"}
                  </th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((user) => (
                  <tr key={user.username} className="nq-user-row">
                    <td>
                      <div className="nq-user-cell">
                        <span className="nq-user-avatar" aria-hidden="true">
                          {userInitials(user.display_name)}
                        </span>
                        <div className="nq-user-cell__text">
                          <strong className="nq-user-cell__name">{user.display_name}</strong>
                          <span className="nq-user-cell__meta font-mono">@{user.username}</span>
                          <span className="nq-user-cell__meta nq-user-cell__meta--sm font-mono">{user.nv_id}</span>
                        </div>
                      </div>
                    </td>
                    <td className="nq-muted font-mono text-xs nq-user-table__hide-sm">{user.nv_id}</td>
                    <td>
                      <StatusChip tone={roleTone(user.role)}>{roleLabel(user.role)}</StatusChip>
                    </td>
                    <td className="nq-user-table__actions">
                      {canManage && user.role === "nhan_vien" ? (
                        <Btn
                          variant="ghost"
                          busy={busy === user.username}
                          busyLabel="Đang nâng…"
                          className="nq-btn-compact"
                          onClick={() => setPending({ kind: "promote", user })}
                        >
                          Nâng QL
                        </Btn>
                      ) : null}
                      {canManage && user.role === "quan_ly" ? (
                        <Btn
                          variant="ghost"
                          busy={busy === user.username}
                          busyLabel="Đang hạ…"
                          className="nq-btn-compact nq-btn-compact--danger"
                          onClick={() => setPending({ kind: "demote", user })}
                        >
                          Hạ NV
                        </Btn>
                      ) : null}
                      {user.role === "chu_quan" ? (
                        <span className="nq-user-protected" title="Vai trò chủ quán không đổi được">
                          Bảo vệ
                        </span>
                      ) : null}
                      {!canManage && user.role !== "chu_quan" ? (
                        <span className="nq-muted text-xs">Chỉ xem</span>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </>
  );
}
