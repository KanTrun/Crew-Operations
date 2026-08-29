"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { formatNgay, khungLabel, safeText, viError, viTriLabel } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
    Alert,
    AuthGate,
    Btn,
    Empty,
    InlineActions,
    Loading,
    PageHeader
} from "../../ui/kit";

type Ca = {
  id: string;
  ngay: string;
  bat_dau: string;
  ket_thuc: string;
  vi_tri: string;
  khung?: string;
  trang_thai?: string;
  co_the_nha?: boolean;
  co_the_nhan?: boolean;
};

type ChannelStatus = {
  uu_tien?: string[];
  agent_mode?: string;
  zalo?: { connected?: boolean };
  telegram?: { connected?: boolean };
};

export default function ToiPage() {
  const [token, setToken] = useState("");
  const [ca, setCa] = useState<Ca[]>([]);
  const [week, setWeek] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [bindCode, setBindCode] = useState<string | null>(null);
  const [channels, setChannels] = useState<ChannelStatus | null>(null);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ tuan_iso?: string; items?: Ca[] }>("/api/v1/toi/lich")
      .then((d) => {
        setWeek(d.tuan_iso ?? "Tuần này");
        setCa(d.items ?? []);
      })
      .catch(() => setError("Không tải được lịch cá nhân."))
      .finally(() => setLoading(false));

    apiGet<ChannelStatus>("/api/v1/channels/status")
      .then((s) => setChannels(s))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function issueBind() {
    setBusy("bind");
    setError(null);
    setMsg(null);
    try {
      const res = await apiSend<{ code: string }>("/api/v1/channels/bind/issue", {});
      setBindCode(res.code);
    } catch {
      setError("Không tạo được mã kết nối.");
    } finally {
      setBusy(null);
    }
  }

  async function act(action: "nha" | "nhan", ca_id: string) {
    setBusy(ca_id);
    setError(null);
    setMsg(null);
    try {
      await apiSend(`/api/v1/ca/${action}`, { ca_id });
      setMsg(action === "nha" ? "Đã gửi yêu cầu nhả ca vào chợ đổi ca." : "Đã nhận ca thành công.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "nhả hoặc nhận ca" }));
    } finally {
      setBusy(null);
    }
  }

  if (!token) return <AuthGate />;

  const grouped: Record<string, Ca[]> = {};
  for (const c of ca) {
    const k = c.ngay ? formatNgay(c.ngay) : "Chưa rõ ngày";
    if (!grouped[k]) grouped[k] = [];
    grouped[k].push(c);
  }

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Cá nhân"
        title="Lịch của tôi"
        meta={`Lịch phân công tuần ${week} · Chỉ hiển thị ca bạn phụ trách`}
      />

      {error ? <Alert kind="err">{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      <div className="nq-card mb-8">
        <h2 className="text-xl font-black uppercase mb-2 text-[var(--nq-fg)]">Kết nối Zalo / Kênh ngoài</h2>
        <p className="text-sm text-[var(--nq-dim)] mb-4">
          Nhận thông báo ca, báo trễ, đổi ca qua Zalo cá nhân.
        </p>
        {bindCode ? (
          <div className="p-4 bg-[var(--nq-surface-hi)] border-2 border-[var(--nq-copper)] mb-4">
            <p className="text-sm font-mono text-[var(--nq-dim)] mb-1">Gửi tin nhắn này cho bot Zalo:</p>
            <p className="text-2xl font-black font-mono text-[var(--nq-copper)] tracking-wider select-all">
              /bind {bindCode}
            </p>
          </div>
        ) : null}
        <InlineActions>
          <Btn variant="primary" busy={busy === "bind"} busyLabel="Đang tạo mã…" onClick={issueBind}>
            {bindCode ? "Tạo mã mới" : "Lấy mã kết nối Zalo"}
          </Btn>
        </InlineActions>
      </div>

      {loading ? <Loading skeleton="rows" rows={4}>Đang tải lịch của bạn…</Loading> : null}
      {!loading && !error && ca.length === 0 ? (
        <Empty>Bạn chưa được xếp ca nào trong tuần này.</Empty>
      ) : null}

      {Object.keys(grouped)
        .sort()
        .map((ngay) => (
          <section key={ngay} style={{ marginTop: "1.25rem" }}>
            <p className="nq-kicker">{ngay}</p>
            <div className="nq-list">
              {(grouped[ngay] ?? []).map((c) => {
                const mine = c.trang_thai === "cua_toi";
                return (
                  <div key={c.id} className="nq-item">
                    <p className="nq-item-title">{viTriLabel(c.vi_tri)}</p>
                    <p className="nq-item-sub" style={{ fontFamily: "var(--nq-font-mono)" }}>
                      {safeText(c.bat_dau, "--:--")} – {safeText(c.ket_thuc, "--:--")}
                      {c.khung ? ` · ${khungLabel(c.khung)}` : ""}
                      {mine ? " · ca của bạn" : ""}
                    </p>
                    <div style={{ display: "flex", gap: "0.5rem", margin: 0 }}>
                      {(mine || c.co_the_nha) && (
                        <Btn
                          variant="danger"
                          disabled={busy === c.id}
                          onClick={() => act("nha", c.id)}
                        >
                          Nhả
                        </Btn>
                      )}
                      {(!mine || c.co_the_nhan) && (
                        <Btn
                          variant="primary"
                          disabled={busy === c.id}
                          onClick={() => act("nhan", c.id)}
                        >
                          Nhận
                        </Btn>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
    </div>
  );
}
