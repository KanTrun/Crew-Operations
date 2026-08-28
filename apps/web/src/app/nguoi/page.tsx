"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken, roleLabel } from "../../lib/session";
import { Alert, Btn, Empty, Loading, PageHeader, StatusChip } from "../../ui/kit";

type User = { username: string; role: string; nv_id: string; display_name: string };

export default function NguoiPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<User[]>([]);
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

  useEffect(() => setToken(getToken()), []);
  useEffect(() => { if (token) void load(); }, [load, token]);

  async function promote(username: string) {
    setBusy(username);
    setError(null);
    try {
      await apiSend(`/api/v1/nguoi/${username}/nang-vai`, {});
      setMsg(`Đã nâng ${username} lên vai trò quản lý.`);
      await load();
    } catch (e) {
      setError(viError(e, { doing: "nâng vai người dùng" }));
    } finally {
      setBusy("");
    }
  }

  if (!token) return null;
  return (
    <section className="nq-page">
      <PageHeader kicker="Admin quán" title="Người dùng" meta="Tài khoản tự đăng ký luôn là nhân viên. Chỉ chủ quán mới có thể nâng nhân viên lên quản lý." />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang tải người dùng…</Loading> : null}
      {!loading && items.length === 0 ? <Empty>Chưa có người dùng.</Empty> : null}
      <div className="nq-list">
        {items.map((user) => (
          <article key={user.username} className="nq-item">
            <div><strong>{user.display_name}</strong><p className="nq-muted">@{user.username} · {user.nv_id}</p></div>
            <div className="flex items-center gap-3">
              <StatusChip tone={user.role === "chu_quan" ? "ok" : user.role === "quan_ly" ? "warn" : "default"}>{roleLabel(user.role)}</StatusChip>
              {user.role === "nhan_vien" ? <Btn busy={busy === user.username} onClick={() => void promote(user.username)}>Nâng quản lý</Btn> : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
