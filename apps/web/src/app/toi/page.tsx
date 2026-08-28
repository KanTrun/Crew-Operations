"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
<<<<<<< Updated upstream
import { getToken } from "../../lib/session";
import { Alert, AuthGate, btnDanger, btnPrimary, Empty, Kicker, Loading } from "../../ui/kit";
=======
import { formatNgay, khungLabel, safeText, viError, viTriLabel } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  InlineActions,
  Kicker,
  Loading,
  Notice,
  PageHeader,
} from "../../ui/kit";
>>>>>>> Stashed changes

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
<<<<<<< Updated upstream
    apiGet<{ ca?: Ca[]; tuan_iso?: string } | Ca[]>("/api/v1/toi/lich")
      .then((d) => {
        const list = Array.isArray(d) ? d : d.ca ?? [];
        setCa(list);
        if (!Array.isArray(d)) setWeek(d.tuan_iso ?? "");
=======
    setLoading(true);
    Promise.all([
      apiGet<{ ca?: Ca[]; tuan_iso?: string } | Ca[]>("/api/v1/toi/lich"),
      apiGet<ChannelStatus>("/api/v1/channels/status").catch(() => null),
    ])
      .then(([d, st]) => {
        const list = Array.isArray(d) ? d : d.ca ?? [];
        setCa(list.filter((c) => c && typeof c.id === "string"));
        if (!Array.isArray(d)) setWeek(safeText(d.tuan_iso, ""));
        setChannels(st);
        setError(null);
>>>>>>> Stashed changes
      })
      .catch(() => setError("Không tải được lịch của bạn."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function layMaBind() {
    setError(null);
    setMsg(null);
    try {
      const r = await apiSend<{ code: string; huong_dan: string }>("/api/v1/channels/bind/issue", {});
      setBindCode(r.code);
      setMsg(r.huong_dan);
    } catch (e) {
      setError(viError(e, { doing: "lấy được mã nối Zalo/Telegram" }));
    }
  }

  async function act(kind: "nha" | "nhan", id: string) {
    setBusy(id);
    setError(null);
    setMsg(null);
    try {
      await apiSend(`/api/v1/ca/${kind}`, { ca_id: id });
      setMsg(kind === "nha" ? "Đã nhả ca." : "Đã nhận ca.");
      load();
    } catch {
      setError(kind === "nha" ? "Không nhả được ca." : "Không nhận được ca.");
    } finally {
      setBusy(null);
    }
  }

  if (!token) return <AuthGate />;

  const grouped: Record<string, Ca[]> = {};
  for (const c of ca) (grouped[c.ngay] ??= []).push(c);

  return (
    <div className="nq-page">
      <Kicker>Ca của tôi</Kicker>
      <h1>Lịch của tôi</h1>
      {week ? <p className="nq-muted">Tuần {week}</p> : null}
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
<<<<<<< Updated upstream
      {loading ? <Loading>Đang tải lịch của bạn…</Loading> : null}
=======

      <section className="mb-10 border-2 border-[var(--nq-dim)] p-4 md:p-6">
        <h2 className="mb-2 text-lg font-black uppercase tracking-tighter text-[var(--nq-copper)]">
          Nối Zalo / Telegram
        </h2>
        <p className="mb-3 text-sm text-[var(--nq-dim)]">
          Ưu tiên Zalo OA (quán VN). Lấy mã → nhắn OA/bot:{" "}
          <span className="font-mono text-[var(--nq-fg)]">/bind &lt;mã&gt;</span>. AI chỉ hiểu tin thật khi quán bật{" "}
          <span className="font-mono">CA_AGENT_MODE=live</span>.
        </p>
        {channels ? (
          <p className="mb-3 font-mono text-xs text-[var(--nq-dim)]">
            Zalo: {channels.zalo?.connected ? "đã nối" : "chưa nối"} · Telegram:{" "}
            {channels.telegram?.connected ? "đã nối" : "chưa nối"} · AI: {safeText(channels.agent_mode, "replay")}
          </p>
        ) : null}
        {bindCode ? (
          <Notice>
            Mã của bạn: <strong className="font-mono text-[var(--nq-copper)]">{bindCode}</strong>
          </Notice>
        ) : null}
        <Btn variant="primary" onClick={layMaBind}>
          Lấy mã bind
        </Btn>
      </section>

      {loading ? <Loading skeleton="list">Đang tải lịch của bạn…</Loading> : null}
>>>>>>> Stashed changes
      {!loading && ca.length === 0 && !error ? (
        <Empty>Chưa có ca trong tuần này, hoặc lịch chưa công bố.</Empty>
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
<<<<<<< Updated upstream
                    <p style={{ margin: 0, fontWeight: 600 }}>{c.vi_tri}</p>
                    <p className="nq-muted" style={{ margin: "0.2rem 0 0.6rem", fontFamily: "var(--nq-font-mono)" }}>
                      {c.bat_dau} – {c.ket_thuc}
                      {c.khung ? ` · ${c.khung}` : ""}
=======
                    <p className="nq-item-title">{viTriLabel(c.vi_tri)}</p>
                    <p className="nq-item-sub" style={{ fontFamily: "var(--nq-font-mono)" }}>
                      {safeText(c.bat_dau, "--:--")} – {safeText(c.ket_thuc, "--:--")}
                      {khung ? ` · ${khung}` : ""}
>>>>>>> Stashed changes
                      {mine ? " · ca của bạn" : ""}
                    </p>
                    <p style={{ display: "flex", gap: "0.5rem", margin: 0 }}>
                      {(mine || c.co_the_nha) && (
                        <button disabled={busy === c.id} onClick={() => act("nha", c.id)} style={btnDanger}>
                          Nhả
                        </button>
                      )}
                      {(!mine || c.co_the_nhan) && (
                        <button disabled={busy === c.id} onClick={() => act("nhan", c.id)} style={btnPrimary}>
                          Nhận
                        </button>
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
    </div>
  );
}
