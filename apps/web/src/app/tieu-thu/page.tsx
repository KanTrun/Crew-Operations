"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken, isManager } from "../../lib/session";
import { Alert, AuthGate, btnPrimary, Empty, Field, inputStyle, Kicker, Loading } from "../../ui/kit";

type Row = { id: string; hang: string; so_luong: number; don_vi: string; duoi_nguong?: boolean };

export default function TieuThuPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Row[]>([]);
  const [hang, setHang] = useState("sữa tươi");
  const [so, setSo] = useState("3");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Row[] }>("/api/v1/tieu-thu")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không đọc được sổ tiêu thụ."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await apiSend("/api/v1/tieu-thu", { hang, so_luong: Number(so), don_vi: "khay" });
      load();
    } catch {
      setError("Cần quyền quản lý để ghi số lượng.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <Kicker>Số lượng · không kế toán</Kicker>
      <h1>Sổ tiêu thụ</h1>
      <p className="nq-muted">Hệ thống ghi số, không tính tiền. Dưới 2 khay thì cảnh báo trên Hôm nay.</p>
      {error ? <Alert>{error}</Alert> : null}
      {isManager() ? (
        <form onSubmit={onSubmit}>
          <Field label="Hàng">
            <input value={hang} onChange={(e) => setHang(e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Số lượng">
            <input value={so} onChange={(e) => setSo(e.target.value)} inputMode="decimal" style={inputStyle} />
          </Field>
          <button type="submit" style={btnPrimary}>
            Ghi kiểm kê
          </button>
        </form>
      ) : null}
      <h2>Lần ghi</h2>
      {loading ? <Loading /> : null}
      {!loading && items.length === 0 ? <Empty>Chưa có lần kiểm kê.</Empty> : null}
      <div className="nq-list">
        {items.map((it) => (
          <article key={it.id} className="nq-item">
            <p style={{ margin: 0, fontWeight: 600 }}>{it.hang}</p>
            <p className="nq-muted" style={{ fontFamily: "var(--nq-font-mono)" }}>
              {it.so_luong} {it.don_vi}
              {it.duoi_nguong ? " · dưới ngưỡng" : ""}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
