"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { safeText, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  Hint,
  inputStyle,
  Loading,
  OpsCard,
  PageHeader,
} from "../../ui/kit";

type Cluster = { cau?: string; thu?: string; n?: number };

const THU_HOP_LE = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"];

export default function HaoPhiPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Cluster[]>([]);
  const [thu, setThu] = useState("T3");
  const [ghi, setGhi] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<{ items: Cluster[] }>("/api/v1/waste")
      .then((d) => {
        setItems(d.items ?? []);
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "đọc được cụm hao phí" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    if (!ghi.trim()) {
      setError("Ghi một câu về chỗ hao phí trước khi lưu.");
      return;
    }
    setBusy(true);
    try {
      await apiSend("/api/v1/waste", { thu, ghi_chu: ghi.trim() });
      setGhi("");
      setMsg("Đã ghi. Nhiều ghi chú giống nhau sẽ tự gom thành một cụm.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "ghi được ghi chú hao phí" }));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Gom cụm từ ghi chú ca"
        title="Hao phí"
        meta="Ghi chỗ hao trong ca bằng một câu. Ghi chú lặp lại sẽ gom thành cụm để quán thấy chỗ chảy máu."
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      <OpsCard eyebrow="Ghi trong ca" title="Ghi chú hao phí">
        <form onSubmit={onSubmit}>
          <Field label="Thứ trong tuần">
            <select value={thu} onChange={(e) => setThu(e.target.value)} style={inputStyle}>
              {THU_HOP_LE.map((t) => (
                <option key={t} value={t}>
                  {t === "CN" ? "Chủ nhật" : `Thứ ${t.slice(1)}`}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Hao ở đâu">
            <input
              value={ghi}
              onChange={(e) => setGhi(e.target.value)}
              placeholder="Ví dụ: đổ bỏ 2 ly sữa vì pha sai"
              style={inputStyle}
            />
          </Field>
          <Hint>Viết như nói với đồng nghiệp. Không cần số tiền.</Hint>
          <Btn type="submit" variant="primary" disabled={busy}>
            {busy ? "Đang ghi…" : "Ghi hao phí"}
          </Btn>
        </form>
      </OpsCard>
      <h2>Cụm đã gom</h2>
      {loading ? <Loading skeleton="list">Đang gom cụm hao phí…</Loading> : null}
      {!loading && !error && items.length === 0 ? (
        <Empty>Chưa đủ ghi chú để gom cụm. Ghi thêm vài lần trong ca.</Empty>
      ) : null}
      <div className="nq-list">
        {items.map((it, i) => (
          <article key={`${safeText(it.thu, "?")}-${i}`} className="nq-item">
            <p className="nq-item-title">{safeText(it.cau, "Chưa đủ mẫu để gom thành cụm")}</p>
            <p className="nq-item-sub">
              {safeText(it.thu, "chưa rõ thứ")} · {typeof it.n === "number" ? it.n : 0} lần
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
