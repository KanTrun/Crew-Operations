"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { safeNumber, safeText, viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  Hint,
  inputStyle,
  Loading,
  Notice,
  OpsCard,
  PageHeader,
  StatusChip,
} from "../../ui/kit";

type Row = { id: string; hang: string; so_luong: number; don_vi: string; duoi_nguong?: boolean };

export default function TieuThuPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [items, setItems] = useState<Row[]>([]);
  const [hang, setHang] = useState("sữa tươi");
  const [so, setSo] = useState("3");
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<{ items: Row[] }>("/api/v1/tieu-thu")
      .then((d) => {
        setItems((d.items ?? []).filter((x) => x && typeof x.id === "string"));
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "đọc được sổ tiêu thụ" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    const soLuong = Number(so.replace(",", "."));
    if (!hang.trim()) {
      setError("Ghi tên hàng trước khi lưu kiểm kê.");
      return;
    }
    if (!Number.isFinite(soLuong) || soLuong < 0) {
      setError("Số lượng phải là một số không âm, ví dụ 2 hoặc 2.5.");
      return;
    }
    setBusy(true);
    try {
      await apiSend("/api/v1/tieu-thu", { hang: hang.trim(), so_luong: soLuong, don_vi: "khay" });
      setMsg("Đã ghi lần kiểm kê.");
      load();
    } catch (e) {
      setError(
        viError(e, {
          doing: "ghi được lần kiểm kê",
          forbidden: "Chỉ quản lý hoặc chủ quán ghi được số lượng vào sổ.",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Số lượng · không kế toán"
        title="Sổ tiêu thụ"
        meta="Ghi số khay dùng trong ca. Hệ thống chỉ đếm, không tính tiền; dưới ngưỡng thì cảnh báo trên bảng Hôm nay."
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {manager ? (
        <OpsCard eyebrow="Ghi vào sổ" title="Lần kiểm kê mới">
          <form onSubmit={onSubmit}>
            <Field label="Tên hàng">
              <input value={hang} onChange={(e) => setHang(e.target.value)} style={inputStyle} />
            </Field>
            <Field label="Số khay còn lại">
              <input value={so} onChange={(e) => setSo(e.target.value)} inputMode="decimal" style={inputStyle} />
            </Field>
            <Hint>Đếm theo khay. Dưới 2 khay thì bảng Hôm nay hiện cảnh báo tồn.</Hint>
            <Btn type="submit" variant="primary" disabled={busy}>
              {busy ? "Đang ghi…" : "Ghi lần kiểm kê"}
            </Btn>
          </form>
        </OpsCard>
      ) : (
        <Notice>Bạn xem được sổ. Quản lý hoặc chủ quán mới ghi số lượng.</Notice>
      )}
      <h2>Những lần đã ghi</h2>
      {loading ? <Loading skeleton="list">Đang đọc sổ tiêu thụ…</Loading> : null}
      {!loading && !error && items.length === 0 ? (
        <Empty>Chưa có lần kiểm kê nào trong sổ.</Empty>
      ) : null}
      <div className="nq-list">
        {items.map((it) => (
          <article key={it.id} className="nq-item">
            <p className="nq-item-title">{safeText(it.hang, "Hàng chưa ghi tên")}</p>
            <p className="nq-item-sub" style={{ fontFamily: "var(--nq-font-mono)" }}>
              {safeNumber(it.so_luong)} {safeText(it.don_vi, "khay")}
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
