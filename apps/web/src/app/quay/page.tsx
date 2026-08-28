"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getRole, getToken, isManager } from "../../lib/session";
import { Alert, Btn, Empty, Loading, PageHeader, StatusChip } from "../../ui/kit";

type Mon = { id: string; ten: string; gia: number };
type Dong = { mon_id: string; ten: string; so_luong: number; gia: number };
type Don = {
  id: string;
  trang_thai: "cho_pha" | "dang_pha" | "xong" | "huy";
  thanh_toan: "tien_mat" | "da_ck" | "chua_thu";
  dong: Dong[];
  ly_do_huy?: string | null;
};
type BaoCao = { so_don: number; tong_ly: number; tong_tien: number; chua_thu: number };

const MONEY = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND", maximumFractionDigits: 0 });

export default function QuayPage() {
  const [token, setToken] = useState("");
  const [role, setRole] = useState("");
  const [menu, setMenu] = useState<Mon[]>([]);
  const [orders, setOrders] = useState<Don[]>([]);
  const [cart, setCart] = useState<Record<string, number>>({});
  const [payment, setPayment] = useState<Don["thanh_toan"]>("chua_thu");
  const [report, setReport] = useState<BaoCao | null>(null);
  const [checkedIn, setCheckedIn] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getToken()) return;
    setLoading(true);
    try {
      const [menuOut, orderOut] = await Promise.all([
        apiGet<{ items: Mon[] }>("/api/v1/menu"),
        apiGet<{ items: Don[] }>("/api/v1/quay/don"),
      ]);
      setMenu(menuOut.items ?? []);
      setOrders(orderOut.items ?? []);
      setCheckedIn(true);
      if (isManager(getRole())) {
        apiGet<BaoCao>("/api/v1/quay/bao-cao").then(setReport).catch(() => setReport(null));
      }
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        setCheckedIn(false);
        try {
          const menuOut = await apiGet<{ items: Mon[] }>("/api/v1/menu");
          setMenu(menuOut.items ?? []);
        } catch {
          setError(viError(e, { doing: "mở quầy" }));
        }
      } else {
        setError(viError(e, { doing: "mở quầy" }));
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setToken(getToken());
    setRole(getRole());
  }, []);
  useEffect(() => {
    if (token) void load();
  }, [token, load]);

  const lines = useMemo(
    () => menu.filter((m) => cart[m.id]).map((m) => ({ ...m, so_luong: cart[m.id] })),
    [cart, menu],
  );
  const total = lines.reduce((sum, line) => sum + line.gia * line.so_luong, 0);

  function changeQty(id: string, delta: number) {
    setCart((old) => {
      const next = Math.max(0, (old[id] ?? 0) + delta);
      const copy = { ...old };
      if (next) copy[id] = next;
      else delete copy[id];
      return copy;
    });
  }

  async function checkIn() {
    setBusy(true);
    setError(null);
    try {
      await apiSend("/api/v1/diem-danh");
      setMsg("Đã điểm danh ca. Bạn có thể ghi đơn tại quầy.");
      await load();
    } catch (e) {
      setError(viError(e, { doing: "điểm danh ca" }));
    } finally {
      setBusy(false);
    }
  }

  async function createOrder() {
    if (!lines.length) return;
    setBusy(true);
    setError(null);
    try {
      await apiSend("/api/v1/quay/don", {
        dong: lines.map((line) => ({ mon_id: line.id, so_luong: line.so_luong })),
        thanh_toan: payment,
      });
      setCart({});
      setMsg("Đơn đã vào hàng chờ pha.");
      await load();
    } catch (e) {
      setError(viError(e, { doing: "ghi đơn quầy", forbidden: "Cần điểm danh ca trước khi ghi đơn." }));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return null;
  return (
    <section className="nq-page">
      <PageHeader kicker="Quầy nội bộ" title="Ghi đơn tại quầy" meta="Đơn do nhân viên đang ca ghi. Đây không phải app khách hoặc số Grab." />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {!checkedIn ? (
        <Alert kind="info">
          Chưa điểm danh ca nên quầy đang khóa. <Btn onClick={() => void checkIn()} busy={busy}>Điểm danh để mở quầy</Btn>
        </Alert>
      ) : null}
      {loading ? <Loading skeleton="bento">Đang tải menu quầy…</Loading> : null}
      {!loading ? (
        <div className="grid gap-8 lg:grid-cols-[1.5fr_1fr]">
          <div>
            <h2>Menu đang bán</h2>
            {menu.length === 0 ? <Empty>Chủ quán chưa mở món nào trong menu.</Empty> : null}
            <div className="nq-list">
              {menu.map((mon) => (
                <article key={mon.id} className="nq-item">
                  <div>
                    <strong>{mon.ten}</strong>
                    <p className="nq-muted">{MONEY.format(mon.gia)}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Btn variant="ghost" onClick={() => changeQty(mon.id, -1)} title={`Bớt ${mon.ten}`}>−</Btn>
                    <span aria-label={`Số lượng ${mon.ten}`}>{cart[mon.id] ?? 0}</span>
                    <Btn onClick={() => changeQty(mon.id, 1)} title={`Thêm ${mon.ten}`}>+</Btn>
                  </div>
                </article>
              ))}
            </div>
          </div>
          <aside className="nq-item">
            <h2>Đơn mới</h2>
            {lines.length === 0 ? <p className="nq-muted">Chọn món từ menu.</p> : null}
            {lines.map((line) => <p key={line.id}>{line.ten} × {line.so_luong} — {MONEY.format(line.gia * line.so_luong)}</p>)}
            <p><strong>Tổng tạm tính: {MONEY.format(total)}</strong></p>
            <label>
              Thanh toán
              <select value={payment} onChange={(e) => setPayment(e.target.value as Don["thanh_toan"])}>
                <option value="chua_thu">Chưa thu</option>
                <option value="tien_mat">Tiền mặt</option>
                <option value="da_ck">Đã chuyển khoản</option>
              </select>
            </label>
            <p><Btn type="button" onClick={() => void createOrder()} busy={busy} disabled={!checkedIn || !lines.length}>Gửi sang pha chế</Btn></p>
          </aside>
        </div>
      ) : null}
      {report && role !== "nhan_vien" ? (
        <section className="nq-item" aria-label="Tổng quầy">
          <h2>Tổng ca</h2>
          <p>{report.so_don} đơn · {report.tong_ly} ly · {MONEY.format(report.tong_tien)} · chưa thu {MONEY.format(report.chua_thu)}</p>
        </section>
      ) : null}
      <h2>Đơn của ca</h2>
      {!loading && orders.length === 0 ? <Empty>Chưa có đơn nào trong ca của bạn.</Empty> : null}
      <div className="nq-list">
        {orders.map((order) => (
          <article key={order.id} className="nq-item">
            <div><strong>{order.dong.map((line) => `${line.ten} × ${line.so_luong}`).join(", ")}</strong><p className="nq-muted">{order.thanh_toan}</p></div>
            <StatusChip tone={order.trang_thai === "xong" ? "ok" : order.trang_thai === "huy" ? "danger" : "warn"}>{order.trang_thai.replace("_", " ")}</StatusChip>
          </article>
        ))}
      </div>
    </section>
  );
}
