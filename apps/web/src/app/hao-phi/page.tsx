"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Field, inputStyle, Loading, PageHeader } from "../../ui/kit";

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
      <PageHeader kicker="Gom cụm từ ghi chú ca" title="Hao phí" />
      {error ? <Alert>{error}</Alert> : null}
      <form onSubmit={onSubmit}>
        <Field label="Thứ">
          <input value={thu} onChange={(e) => setThu(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Ghi chú">
          <input value={ghi} onChange={(e) => setGhi(e.target.value)} style={inputStyle} />
        </Field>
        <Btn type="submit" variant="primary">
          Ghi chú
        </Btn>
      </form>
      <h2>Cụm</h2>
      {loading ? <Loading skeleton="list">Đang gom cụm…</Loading> : null}
      {!loading && items.length === 0 ? <Empty>Chưa có ghi chú để gom cụm.</Empty> : null}
      <div className="nq-list">
        {items.map((it, i) => (
          <article key={i} className="nq-item">
            <p className="nq-item-title">{it.cau ?? "Chưa đủ mẫu để gom cụm"}</p>
            <p className="nq-item-sub">
              {it.thu} · {it.n ?? 0} lần
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
