"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getRole, getToken, roleLabel } from "../../lib/session";
import { Alert, Btn, Empty, Loading, PageHeader, StatusChip } from "../../ui/kit";

type User = { username: string; role: string; nv_id: string; display_name: string };
type RoleFilter = "all" | "chu_quan" | "quan_ly" | "nhan_vien";

export default function NguoiPage() {
  const [token, setToken] = useState("");
  const [myRole, setMyRole] = useState("");
  const [items, setItems] = useState<User[]>([]);
  const [filter, setFilter] = useState<RoleFilter>("all");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

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

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((u) => u.role === filter);
  }, [filter, items]);

  async function promote(username: string) {
    if (!confirm(`Nâng @${username} lên quản lý ca?`)) return;
    setBusy(username);
    setError(null);
    try {
      await apiSend(`/api/v1/nguoi/${username}/nang-vai`, {});
      setMsg(`Đã nâng ${username} lên quản lý.`);
      await load();
    } catch (e) {
      setError(viError(e, { doing: "nâng vai người dùng" }));
    } finally {
      setBusy("");
    }
  }

  async function demote(username: string) {
    if (!confirm(`Hạ @${username} xuống nhân viên? Quyền quản lý sẽ bị thu hồi.`)) return;
    setBusy(username);
    setError(null);
    try {
      await apiSend(`/api/v1/nguoi/${username}/ha-vai`, {});
      setMsg(`Đã hạ ${username} xuống nhân viên.`);
      await load();
    } catch (e) {
      setError(viError(e, { doing: "hạ vai người dùng" }));
    } finally {
      setBusy("");
    }
  }

  if (!token) return null;

  const tabs: { id: RoleFilter; label: string }[] = [
    { id: "all", label: "Tất cả" },
    { id: "chu_quan", label: "Chủ quán" },
    { id: "quan_ly", label: "Quản lý" },
    { id: "nhan_vien", label: "Nhân viên" },
  ];

  return (
    <section className="nq-page">
      <PageHeader
        kicker="Admin quán"
        title="Người dùng"
        meta="Chủ quán quản lý vai trò: nâng nhân viên lên quản lý hoặc hạ quản lý xuống nhân viên. Không đổi được chủ quán."
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      <div className="nq-filter-tabs" role="tablist" aria-label="Lọc vai trò">
        {tabs.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={filter === t.id}
            className={`nq-filter-tab ${filter === t.id ? "nq-filter-tab--on" : ""}`}
            onClick={() => setFilter(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading ? <Loading skeleton="list">Đang tải người dùng…</Loading> : null}
      {!loading && filtered.length === 0 ? <Empty>Không có người dùng trong nhóm này.</Empty> : null}

      {!loading && filtered.length > 0 ? (
        <div className="nq-data-table-wrap">
          <table className="nq-data-table">
            <thead>
              <tr>
                <th>Tên hiển thị</th>
                <th>Tài khoản</th>
                <th>Mã NV</th>
                <th>Vai trò</th>
                <th>Hành động</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((user) => (
                <tr key={user.username}>
                  <td>
                    <strong>{user.display_name}</strong>
                  </td>
                  <td className="nq-muted font-mono text-xs">@{user.username}</td>
                  <td className="nq-muted font-mono text-xs">{user.nv_id}</td>
                  <td>
                    <StatusChip
                      tone={
                        user.role === "chu_quan" ? "ok" : user.role === "quan_ly" ? "warn" : "default"
                      }
                    >
                      {roleLabel(user.role)}
                    </StatusChip>
                  </td>
                  <td>
                    {myRole === "chu_quan" && user.role === "nhan_vien" ? (
                      <Btn busy={busy === user.username} onClick={() => void promote(user.username)}>
                        Nâng QL
                      </Btn>
                    ) : null}
                    {myRole === "chu_quan" && user.role === "quan_ly" ? (
                      <Btn variant="ghost" busy={busy === user.username} onClick={() => void demote(user.username)}>
                        Hạ NV
                      </Btn>
                    ) : null}
                    {user.role === "chu_quan" ? (
                      <span className="nq-muted text-xs">—</span>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}
