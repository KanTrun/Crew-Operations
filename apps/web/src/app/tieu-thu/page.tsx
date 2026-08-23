"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken, isManager } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Field, inputStyle, Loading, PageHeader, StatusChip } from "../../ui/kit";

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
      <PageHeader
        kicker="Số lượng · không kế toán"
        title="Sổ tiêu thụ"
        meta="Hệ thống ghi số, không tính tiền. Dưới 2 khay thì cảnh báo trên Hôm nay."
      />
      {error ? <Alert>{error}</Alert> : null}
      {isManager() ? (
        <form onSubmit={onSubmit}>
          <Field label="Hàng">
            <input value={hang} onChange={(e) => setHang(e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Số lượng">
            <input value={so} onChange={(e) => setSo(e.target.value)} inputMode="decimal" style={inputStyle} />
          </Field>
          <Btn type="submit" variant="primary">
            Ghi kiểm kê
          </Btn>
        </form>
      ) : null}
      <h2>Lần ghi</h2>
      {loading ? <Loading skeleton="list">Đang đọc sổ…</Loading> : null}
      {!loading && items.length === 0 ? <Empty>Chưa có lần kiểm kê.</Empty> : null}
      <div className="nq-list">
        {items.map((it) => (
          <article key={it.id} className="nq-item">
            <p className="nq-item-title">{it.hang}</p>
            <p className="nq-item-sub" style={{ fontFamily: "var(--nq-font-mono)" }}>
              {it.so_luong} {it.don_vi}
              {it.duoi_nguong ? (
                <>
                  {" "}
                  <StatusChip tone="warn">dưới ngưỡng</StatusChip>
                </>
              ) : null}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
