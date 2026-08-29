"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import {
  agentLabel,
  formatLuc,
  inboxLabel,
  inboxTone,
  kenhLabel,
  khungLabel,
  rangBuocLabel,
  safeText,
  thuLabel,
  viError,
  yDinhLabel,
} from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Confidence,
  Empty,
  Group,
  Kicker,
  Loading,
  Notice,
  Row,
  StatusChip,
} from "../../ui/kit";

type Item = {
  id: string;
  tom_tat: string;
  trang_thai: string;
  agent: string;
  y_dinh?: string;
  do_tin_cay?: number;
  created_at?: string;
  nguon?: string;
  noi_dung_goc?: string;
  nv_id?: string;
  hieu_luc?: { loai?: string; ghi?: string; swap_id?: string };
  rang_buoc?: { loai?: string; thu?: string; khung?: string };
};

/** Chờ duyệt trước — đó là việc còn phải làm; đã quyết chỉ để tra lại. */
const THU_TU = ["cho_duyet", "moi", "duyet", "tu_choi"];

const TEN_NHOM: Record<string, string> = {
  cho_duyet: "Chờ bạn quyết",
  moi: "Mới vào hộp thư",
  duyet: "Đã duyệt",
  tu_choi: "Đã từ chối",
};

export default function InboxPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [manager, setManager] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Item[] }>("/api/v1/inbox/rang-buoc")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không tải được hộp thư."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function decide(id: string, quyet_dinh: string) {
    setBusy(id);
    setError(null);
    setMsg(null);
    try {
      await apiSend(`/api/v1/inbox/rang-buoc/${id}`, { quyet_dinh });
      setMsg(
        quyet_dinh === "duyet"
          ? "Đã duyệt. Hệ thống ghi hiệu lực (chợ đổi ca / chờ xếp lịch) — không sửa lịch âm thầm."
          : "Đã từ chối. Ràng buộc này không vào lượt xếp lịch.",
      );
      load();
    } catch {
      setError("Cần quyền quản lý để duyệt.");
    } finally {
      setBusy(null);
    }
  }

  if (!token) return <AuthGate />;

  const nhom: [string, Item[]][] = THU_TU.map((tt): [string, Item[]] => [
    tt,
    items.filter((it) => it.trang_thai === tt),
  ]).filter((entry): entry is [string, Item[]] => entry[1].length > 0);

  return (
    <div className="nq-page">
      <Kicker>Người duyệt · hệ thống không tự chọn</Kicker>
      <h1>Hộp thư ràng buộc</h1>
      <p className="nq-muted">Khi hai claim mâu thuẫn, người quyết. Không tự chọn hộ.</p>
      {error ? <Alert kind="err">{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {!manager ? <Notice>Bạn xem được nội dung. Quản lý hoặc chủ quán mới bấm duyệt.</Notice> : null}
      {loading ? <Loading skeleton="rows" rows={4} groups={3}>Đang mở hộp thư…</Loading> : null}
      {!loading && !error && items.length === 0 ? (
        <Empty>Hộp thư sạch — không có ràng buộc nào chờ người quyết.</Empty>
      ) : null}

      {!loading &&
        nhom.map(([tt, list]) => (
          <Group key={tt} title={TEN_NHOM[tt] ?? inboxLabel(tt)} count={list.length} countLabel="mục">
            {list.map((it) => (
              <Row
                key={it.id}
                title={safeText(it.tom_tat, "Ràng buộc chưa có tóm tắt")}
                sub={
                  <>
                    {kenhLabel(it.nguon)} · {agentLabel(it.agent)}
                    {it.nv_id ? ` · ${it.nv_id}` : ""}
                    {it.rang_buoc?.loai ? ` · ràng buộc ${rangBuocLabel(it.rang_buoc.loai).toLowerCase()}` : ""}
                    {it.rang_buoc?.thu ? ` · ${thuLabel(it.rang_buoc.thu)}` : ""}
                    {it.rang_buoc?.khung ? ` ${khungLabel(it.rang_buoc.khung).toLowerCase()}` : ""}
                    {it.created_at ? ` · ${formatLuc(it.created_at)}` : ""}
                    {it.noi_dung_goc ? ` · gốc: ${safeText(it.noi_dung_goc).slice(0, 80)}` : ""}
                    {it.hieu_luc?.ghi ? ` · ${it.hieu_luc.ghi}` : ""}
                  </>
                }
                side={
                  <>
                    <StatusChip tone={inboxTone(it.trang_thai)}>{inboxLabel(it.trang_thai)}</StatusChip>
                    <StatusChip>{kenhLabel(it.nguon)}</StatusChip>
                    <StatusChip>{yDinhLabel(it.y_dinh)}</StatusChip>
                    <Confidence value={it.do_tin_cay} />
                  </>
                }
                actions={
                  it.trang_thai === "cho_duyet" && manager ? (
                    <>
                      <Btn
                        variant="primary"
                        busy={busy === it.id}
                        busyLabel="Đang ghi quyết định…"
                        onClick={() => decide(it.id, "duyet")}
                      >
                        Duyệt ràng buộc
                      </Btn>
                      <Btn
                        variant="danger"
                        disabled={busy === it.id}
                        onClick={() => decide(it.id, "tu_choi")}
                      >
                        Từ chối
                      </Btn>
                    </>
                  ) : undefined
                }
              />
            ))}
          </Group>
        ))}
    </div>
  );
}
