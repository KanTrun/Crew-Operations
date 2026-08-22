"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, btnPrimary, Empty, Field, inputStyle, Kicker, Loading } from "../../ui/kit";

type Cluster = { cau?: string; thu?: string; n?: number };

export default function HaoPhiPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Cluster[]>([]);
  const [thu, setThu] = useState("T3");
  const [ghi, setGhi] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Cluster[] }>("/api/v1/waste")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không đọc được hao phí."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await apiSend("/api/v1/waste", { thu, ghi_chu: ghi });
      setGhi("");
      load();
    } catch {
      setError("Không ghi được ghi chú hao phí.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <Kicker>Gom cụm từ ghi chú ca</Kicker>
      <h1>Hao phí</h1>
      {error ? <Alert>{error}</Alert> : null}
      <form onSubmit={onSubmit}>
        <Field label="Thứ">
          <input value={thu} onChange={(e) => setThu(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Ghi chú">
          <input value={ghi} onChange={(e) => setGhi(e.target.value)} style={inputStyle} />
        </Field>
        <button type="submit" style={btnPrimary}>
          Ghi chú
        </button>
      </form>
      <h2>Cụm</h2>
      {loading ? <Loading /> : null}
      {!loading && items.length === 0 ? <Empty>Chưa có ghi chú để gom cụm.</Empty> : null}
      <div className="nq-list">
        {items.map((it, i) => (
          <article key={i} className="nq-item">
            <p style={{ margin: 0, fontWeight: 600 }}>{it.cau ?? "Chưa đủ mẫu để gom cụm"}</p>
            <p className="nq-muted">
              {it.thu} · {it.n ?? 0} lần
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
