"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Field, inputStyle, Loading, PageHeader } from "../../ui/kit";

type Swap = { id: string; a: string; b: string; c: string; ca_id: string; trang_thai: string };

export default function DoiCaPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Swap[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [c, setC] = useState("");
  const [ca, setCa] = useState("w1_c01");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Swap[] }>("/api/v1/cho-doi-ca")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không tải được chợ đổi ca."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiSend("/api/v1/cho-doi-ca", { a, b, c, ca_id: ca });
      setA("");
      setB("");
      setC("");
      load();
    } catch {
      setError("Không mở được lệnh đổi ca.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--run">
      <PageHeader kicker="Ba nhánh phải đồng ý" title="Chợ đổi ca" />
      {error ? <Alert>{error}</Alert> : null}
      <form onSubmit={onSubmit}>
        <Field label="Người A">
          <input value={a} onChange={(e) => setA(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Người B">
          <input value={b} onChange={(e) => setB(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Người C">
          <input value={c} onChange={(e) => setC(e.target.value)} style={inputStyle} />
        </Field>
        <Field label="Mã ca">
          <input value={ca} onChange={(e) => setCa(e.target.value)} style={inputStyle} />
        </Field>
        <Btn type="submit" variant="primary">
          Mở lệnh đổi
        </Btn>
      </form>
      <h2>Lệnh đang mở</h2>
      {loading ? <Loading skeleton="list">Đang tải lệnh…</Loading> : null}
      {!loading && items.length === 0 ? <Empty>Chưa có lệnh đổi ca.</Empty> : null}
      <div className="nq-list">
        {items.map((it) => (
          <article key={it.id} className="nq-item">
            <p className="nq-item-title">
              {it.a} · {it.b} · {it.c}
            </p>
            <p className="nq-item-sub">
              Ca {it.ca_id} · {it.trang_thai}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
