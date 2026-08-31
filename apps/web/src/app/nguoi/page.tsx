"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { matchSearch } from "../../lib/list-filters";
import { viError } from "../../lib/present";
import {
  computeTeamInsight,
  countRoles,
  roleBreakdown,
  technicalUserLines,
  type TeamUser,
} from "../../lib/team-stats";
import { getRole, getToken, isChuQuan, roleLabel } from "../../lib/session";
import { RoleDonutChart } from "../../ui/nguoi/role-donut";
import { UserCard } from "../../ui/nguoi/user-card";
import {
  Alert,
  AuthGate,
  ConfirmDialog,
  Empty,
  Loading,
  PageHeader,
  Summary,
  TechnicalDrawer,
  Toasts,
  useToasts,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type RoleFilter = "all" | "chu_quan" | "quan_ly" | "nhan_vien";
type PendingAction = { kind: "promote" | "demote"; user: TeamUser };

const ROLE_ORDER: Record<string, number> = {
  chu_quan: 0,
  quan_ly: 1,
  nhan_vien: 2,
};

function userHaystack(u: TeamUser): string {
  return [u.display_name, u.username, roleLabel(u.role)].join(" ");
}

export default function NguoiPage() {
  const [token, setToken] = useState("");
  const [myRole, setMyRole] = useState("");
  const [items, setItems] = useState<TeamUser[]>([]);
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
      const out = await apiGet<{ items: TeamUser[] }>("/api/v1/nguoi");
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

  const counts = useMemo(() => countRoles(items), [items]);
  const slices = useMemo(() => roleBreakdown(counts), [counts]);
  const insight = useMemo(() => computeTeamInsight(counts), [counts]);

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
          meta="Quản lý vai trò nhân sự: nâng nhân viên lên quản lý ca hoặc hạ quản lý xuống nhân viên."
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

        {!loading && items.length > 0 ? (
          <div className="nq-nguoi-cockpit">
            <RoleDonutChart slices={slices} total={counts.all} />
            <div
              className={`nq-nguoi-insight nq-nguoi-insight--${insight.severity}`}
              role="status"
              aria-live="polite"
            >
              <p className="nq-nguoi-insight__label">Cơ cấu đội</p>
              <p className="nq-nguoi-insight__text">{insight.message}</p>
            </div>
          </div>
        ) : null}

        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm tên hoặc @tài khoản…"
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
          <div className="nq-nguoi-grid">
            {filtered.map((user) => (
              <UserCard
                key={user.username}
                user={user}
                canManage={canManage}
                busy={busy === user.username}
                onPromote={(u) => setPending({ kind: "promote", user: u })}
                onDemote={(u) => setPending({ kind: "demote", user: u })}
              />
            ))}
          </div>
        ) : null}

        {!loading && items.length > 0 ? (
          <TechnicalDrawer summary="Mã nhân viên nội bộ" lines={technicalUserLines(items)} />
        ) : null}
      </section>
    </>
  );
}
