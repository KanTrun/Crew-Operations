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
  Input,
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

const THU: Record<number, string> = {
  0: "CN",
  1: "T2",
  2: "T3",
  3: "T4",
  4: "T5",
  5: "T6",
  6: "T7",
};

function dayLabel(isoDate: string): string {
  const d = new Date(`${isoDate}T12:00:00`);
  if (Number.isNaN(d.getTime())) return isoDate;
  const thu = THU[d.getDay()] ?? "";
  return `${thu} · ${isoDate}`;
}

export default function ToiPage() {
  const [token, setToken] = useState("");
  const [ca, setCa] = useState<Ca[]>([]);
  const [week, setWeek] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [profileEmail, setProfileEmail] = useState("");
  const [emailInput, setEmailInput] = useState("");
  const [emailMsg, setEmailMsg] = useState<string | null>(null);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [emailBusy, setEmailBusy] = useState(false);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
    const requestedWeek =
      typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("tuan") ?? "" : "";
    if (/^\d{4}-W\d{2}$/.test(requestedWeek)) setWeek(requestedWeek);
  }, []);

  const load = useCallback(
    (targetWeek?: string) => {
      if (!getToken()) return;
      const w = targetWeek !== undefined ? targetWeek : week;
      const url = w ? `/api/v1/toi/lich?tuan=${encodeURIComponent(w)}` : "/api/v1/toi/lich";
      apiGet<{ ca?: Ca[]; tuan_iso?: string; trang_thai?: string } | Ca[]>(url)
        .then((d) => {
          const list = Array.isArray(d) ? d : d.ca ?? [];
          setCa(list);
          if (!Array.isArray(d) && d.tuan_iso) setWeek(d.tuan_iso);
        })
        .catch(() => setError("Không tải được lịch của bạn."))
        .finally(() => setLoading(false));

      apiGet<{ email?: string; username?: string }>("/api/v1/me/profile")
        .then((p) => {
          const em = p.email || "";
          setProfileEmail(em);
          setEmailInput(em);
        })
        .catch(() => {});
    },
    [week],
  );

  async function saveEmail(e: React.FormEvent) {
    e.preventDefault();
    setEmailBusy(true);
    setEmailMsg(null);
    setEmailError(null);
    try {
      await apiSend("/api/v1/me/profile/email", { email: emailInput.trim() }, "PATCH");
      setProfileEmail(emailInput.trim());
      setEmailMsg("Đã lưu email nhận thông báo.");
    } catch {
      setEmailError("Không cập nhật được email. Vui lòng kiểm tra lại định dạng.");
    } finally {
      setEmailBusy(false);
    }
  }

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

  const days = useMemo(() => Object.keys(grouped).sort(), [grouped]);

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

      <OpsCard density="compact" eyebrow="Hồ sơ" title="Email nhận thông báo ca">
        <form onSubmit={saveEmail} className="nq-list">
          <p className="text-sm text-[var(--nq-ink-muted)]">
            Gmail để nhận thông báo phân ca, đổi ca và nhắc việc từ quán.
          </p>
          {emailMsg ? <Alert kind="ok">{emailMsg}</Alert> : null}
          {emailError ? <Alert>{emailError}</Alert> : null}
          <div className="mt-2 flex flex-col gap-2 sm:flex-row">
            <Input
              type="email"
              placeholder="nhan_vien@gmail.com"
              value={emailInput}
              onChange={(e) => setEmailInput(e.target.value)}
              required
              className="flex-1"
            />
            <Btn
              variant="primary"
              type="submit"
              disabled={emailBusy || !emailInput.trim() || emailInput.trim() === profileEmail}
            >
              {emailBusy ? "Đang lưu…" : "Lưu Gmail"}
            </Btn>
          </div>
        </form>
      </OpsCard>

      {loading ? <Loading skeleton="list">Đang tải lịch của bạn…</Loading> : null}
      {!loading && ca.length === 0 && !error ? (
        <Empty title="Chưa có ca">Chưa có ca trong tuần này, hoặc lịch chưa công bố.</Empty>
      ) : null}

      {!loading && days.length > 0 ? (
        <OpsCard density="compact" eyebrow="Tuần này" title="Ca của bạn" count={ca.length} countLabel="ca">
          <div className="space-y-4">
            {days.map((ngay) => (
              <section key={ngay} className="min-w-0">
                <header className="mb-2 flex items-baseline justify-between gap-2 border-b border-[var(--nq-line)] pb-1.5">
                  <h3 className="text-sm font-semibold text-[var(--nq-fg)]">{dayLabel(ngay)}</h3>
                  <span className="font-mono text-2xs text-[var(--nq-dim)]">
                    {(grouped[ngay] ?? []).length} ca
                  </span>
                </header>
                <ul className="space-y-2">
                  {(grouped[ngay] ?? []).map((c) => {
                    const mine = c.trang_thai === "cua_toi";
                    return (
                      <li
                        key={c.id}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--nq-line)] bg-[var(--nq-surface)] px-3 py-2.5"
                      >
                        <div className="min-w-0">
                          <p className="font-semibold text-[var(--nq-fg)]">{viTriLabel(c.vi_tri)}</p>
                          <p className="font-mono text-xs text-[var(--nq-dim)]">
                            {c.bat_dau} – {c.ket_thuc}
                            {c.khung ? ` · ${khungLabel(c.khung)}` : ""}
                            {mine ? (
                              <>
                                {" "}
                                · <StatusChip tone="ok">Ca của bạn</StatusChip>
                              </>
                            ) : null}
                          </p>
                        </div>
                        <div className="flex shrink-0 flex-wrap gap-2">
                          {(mine || c.co_the_nha) && (
                            <Btn size="sm" variant="danger" disabled={busy === c.id} onClick={() => act("nha", c.id)}>
                              Nhả
                            </Btn>
                          )}
                          {(!mine || c.co_the_nhan) && (
                            <Btn
                              size="sm"
                              variant="primary"
                              disabled={busy === c.id}
                              onClick={() => act("nhan", c.id)}
                            >
                              Nhận
                            </Btn>
                          )}
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </section>
            ))}
          </div>
        </OpsCard>
      ) : null}
    </div>
  );
}
