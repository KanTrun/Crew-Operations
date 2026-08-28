"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { formatNgay, khungLabel, safeText, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  InlineActions,
  Kicker,
  Loading,
  PageHeader,
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
    setLoading(true);
    apiGet<{ ca?: Ca[]; tuan_iso?: string } | Ca[]>("/api/v1/toi/lich")
      .then((d) => {
        const list = Array.isArray(d) ? d : d.ca ?? [];
        setCa(list.filter((c) => c && typeof c.id === "string"));
        if (!Array.isArray(d)) setWeek(safeText(d.tuan_iso, ""));
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "tải được lịch của bạn" })))
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
      setMsg(
        kind === "nha"
          ? "Đã nhả ca. Ca này sang chợ đổi ca để người khác nhận."
          : "Đã nhận ca. Ca này giờ nằm trong lịch của bạn.",
      );
      load();
    } catch (e) {
      setError(
        viError(e, {
          doing: kind === "nha" ? "nhả được ca này" : "nhận được ca này",
          conflict:
            kind === "nha"
              ? "Ca này vừa được xếp lại nên không nhả được nữa. Tải lại lịch rồi xem lại."
              : "Người khác vừa nhận ca này trước. Tải lại lịch để xem ca còn trống.",
        }),
      );
    } finally {
      setBusy(null);
    }
  }

  if (!token) return <AuthGate />;

  const grouped: Record<string, Ca[]> = {};
  for (const c of ca) (grouped[safeText(c.ngay, "Chưa rõ ngày")] ??= []).push(c);

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Ca của tôi"
        title="Lịch của tôi"
        meta={`Ca bạn đang giữ trong tuần${week ? ` ${week}` : " này"} — nhả ca hoặc nhận thêm ngay tại đây.`}
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang tải lịch của bạn…</Loading> : null}
      {!loading && ca.length === 0 && !error ? (
        <Empty>
          Chưa có ca nào trong tuần này. Lịch có thể chưa công bố — xem chợ đổi ca hoặc hỏi quản lý.
        </Empty>
      ) : null}
      {Object.keys(grouped)
        .sort()
        .map((ngay) => (
          <section key={ngay} className="nq-section-day">
            <Kicker>Ngày {formatNgay(ngay)}</Kicker>
            <div className="nq-list">
              {(grouped[ngay] ?? []).map((c) => {
                const mine = c.trang_thai === "cua_toi";
                const khung = khungLabel(c.khung);
                return (
                  <div key={c.id} className="nq-item">
                    <p className="nq-item-title">{safeText(c.vi_tri, "Vị trí chưa ghi")}</p>
                    <p className="nq-item-sub" style={{ fontFamily: "var(--nq-font-mono)" }}>
                      {safeText(c.bat_dau, "--:--")} – {safeText(c.ket_thuc, "--:--")}
                      {khung ? ` · ${khung}` : ""}
                      {mine ? " · ca của bạn" : ""}
                    </p>
                    <InlineActions>
                      {(mine || c.co_the_nha) && (
                        <Btn variant="danger" disabled={busy === c.id} onClick={() => act("nha", c.id)}>
                          Nhả ca này
                        </Btn>
                      )}
                      {(!mine || c.co_the_nhan) && (
                        <Btn variant="primary" disabled={busy === c.id} onClick={() => act("nhan", c.id)}>
                          Nhận ca này
                        </Btn>
                      )}
                    </InlineActions>
                  </div>
                );
              })}
            </div>
          </section>
        ))}
    </div>
  );
}
