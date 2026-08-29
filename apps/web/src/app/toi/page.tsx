"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { khungLabel, viTriLabel } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Loading,
  OpsCard,
  PageHeader,
  StatusChip,
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

export default function ToiPage() {
  const [token, setToken] = useState("");
  const [ca, setCa] = useState<Ca[]>([]);
  const [week, setWeek] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ ca?: Ca[]; tuan_iso?: string } | Ca[]>("/api/v1/toi/lich")
      .then((d) => {
        const list = Array.isArray(d) ? d : d.ca ?? [];
        setCa(list);
        if (!Array.isArray(d)) setWeek(d.tuan_iso ?? "");
      })
      .catch(() => setError("Không tải được lịch của bạn."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

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

  const grouped = useMemo(() => {
    const g: Record<string, Ca[]> = {};
    for (const c of ca) (g[c.ngay] ??= []).push(c);
    return g;
  }, [ca]);

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Ca của tôi"
        title="Lịch của tôi"
        meta={week ? `Tuần ${week} — nhả/nhận ca khi lịch đã công bố.` : "Đang đọc tuần hiện tại…"}
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang tải lịch của bạn…</Loading> : null}
      {!loading && ca.length === 0 && !error ? (
        <Empty title="Chưa có ca">Chưa có ca trong tuần này, hoặc lịch chưa công bố.</Empty>
      ) : null}

      {Object.keys(grouped)
        .sort()
        .map((ngay) => (
          <OpsCard key={ngay} eyebrow="Ngày" title={ngay} count={(grouped[ngay] ?? []).length} countLabel="ca">
            <div className="nq-list">
              {(grouped[ngay] ?? []).map((c) => {
                const mine = c.trang_thai === "cua_toi";
                return (
                  <article key={c.id} className="nq-item">
                    <p className="nq-item-title">{viTriLabel(c.vi_tri)}</p>
                    <p className="nq-item-sub font-mono">
                      {c.bat_dau} – {c.ket_thuc}
                      {c.khung ? ` · ${khungLabel(c.khung)}` : ""}
                      {mine ? (
                        <>
                          {" "}
                          · <StatusChip tone="ok">Ca của bạn</StatusChip>
                        </>
                      ) : null}
                    </p>
                    <div className="flex flex-wrap gap-2 mt-3">
                      {(mine || c.co_the_nha) && (
                        <Btn variant="danger" disabled={busy === c.id} onClick={() => act("nha", c.id)}>
                          Nhả
                        </Btn>
                      )}
                      {(!mine || c.co_the_nhan) && (
                        <Btn variant="primary" disabled={busy === c.id} onClick={() => act("nhan", c.id)}>
                          Nhận
                        </Btn>
                      )}
                    </div>
                  </article>
                );
              })}
            </div>
          </OpsCard>
        ))}
    </div>
  );
}
