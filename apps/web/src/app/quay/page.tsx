"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiError, apiGet, apiSend } from "../../lib/api";
import { menuImageUrl } from "../../lib/menu-image";
import { viError } from "../../lib/present";
import { getRole, getToken, isManager } from "../../lib/session";
import { Alert, Btn, Empty, Loading, PageHeader, StatusChip } from "../../ui/kit";

type Mon = { id: string; ten: string; gia: number; hinh_url?: string };
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

function PosThumb({ mon }: { mon: Mon }) {
  const [err, setErr] = useState(false);
  return (
    <div className="h-14 w-14 shrink-0 overflow-hidden rounded-md border border-[var(--nq-line)] bg-[var(--nq-surface-hi)]">
      {!err ? (
        <img
          src={menuImageUrl(mon.id, mon.hinh_url)}
          alt=""
          className="h-full w-full object-cover"
          onError={() => setErr(true)}
        />
      ) : (
        <div className="flex h-full items-center justify-center text-lg font-black text-[var(--nq-copper)]">
          {mon.ten.slice(0, 1)}
        </div>
      )}
    </div>
  );
}

function QtyStepper({
  qty,
  onMinus,
  onPlus,
  label,
}: {
  qty: number;
  onMinus: () => void;
  onPlus: () => void;
  label: string;
}) {
  return (
    <div className="nq-stepper" aria-label={label}>
      <button type="button" className="nq-stepper__btn" onClick={onMinus} disabled={qty < 1} aria-label={`Bớt ${label}`}>
        −
      </button>
      <span className="nq-stepper__qty" aria-live="polite">
        {qty}
      </span>
      <button type="button" className="nq-stepper__btn nq-stepper__btn--add" onClick={onPlus} aria-label={`Thêm ${label}`}>
        +
      </button>
    </div>
  );
}

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
    <section className="nq-page nq-page--wide">
      <PageHeader
        kicker="Quầy nội bộ"
        title="Ghi đơn tại quầy"
        meta="Chạm món để thêm — giỏ cố định bên phải. Đơn do nhân viên đang ca ghi."
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {!checkedIn ? (
        <Alert kind="info">
          Chưa điểm danh ca nên quầy đang khóa.{" "}
          <Btn onClick={() => void checkIn()} busy={busy}>
            Điểm danh để mở quầy
          </Btn>
        </Alert>
      ) : null}
      {loading ? <Loading skeleton="bento">Đang tải menu quầy…</Loading> : null}
      {!loading ? (
        <div className="nq-pos-shell">
          <div>
            <h2 className="mb-3 text-sm font-mono uppercase tracking-widest text-[var(--nq-dim)]">Menu đang bán</h2>
            {menu.length === 0 ? <Empty>Chủ quán chưa mở món nào trong menu.</Empty> : null}
            <div className="nq-pos-menu">
              {menu.map((mon) => {
                const qty = cart[mon.id] ?? 0;
                return (
                  <article key={mon.id} className={`nq-pos-row ${qty ? "nq-pos-row--on" : ""}`}>
                    <PosThumb mon={mon} />
                    <div className="nq-pos-row__info">
                      <strong className="nq-pos-row__name">{mon.ten}</strong>
                      <p className="nq-pos-row__price">{MONEY.format(mon.gia)}</p>
                    </div>
                    <QtyStepper
                      qty={qty}
                      label={mon.ten}
                      onMinus={() => changeQty(mon.id, -1)}
                      onPlus={() => changeQty(mon.id, 1)}
                    />
                  </article>
                );
              })}
            </div>
          </div>

          <aside className="nq-pos-cart space-y-4">
            <h2 className="text-sm font-mono uppercase tracking-widest">Đơn mới</h2>
            {lines.length === 0 ? <p className="nq-muted text-sm">Chọn món từ menu bên trái.</p> : null}
            <ul className="space-y-2 text-sm">
              {lines.map((line) => (
                <li key={line.id} className="flex justify-between gap-2 border-b border-[var(--nq-line)] pb-2">
                  <span>
                    {line.ten} × {line.so_luong}
                  </span>
                  <span className="font-mono">{MONEY.format(line.gia * line.so_luong)}</span>
                </li>
              ))}
            </ul>
            <p className="text-lg font-black">
              Tổng: <span className="text-[var(--nq-copper)]">{MONEY.format(total)}</span>
            </p>
            <label className="block text-sm">
              <span className="mb-1 block font-mono text-xs uppercase tracking-widest text-[var(--nq-dim)]">Thanh toán</span>
              <select className="nq-select w-full" value={payment} onChange={(e) => setPayment(e.target.value as Don["thanh_toan"])}>
                <option value="chua_thu">Chưa thu</option>
                <option value="tien_mat">Tiền mặt</option>
                <option value="da_ck">Đã chuyển khoản</option>
              </select>
            </label>
            <Btn type="button" onClick={() => void createOrder()} busy={busy} disabled={!checkedIn || !lines.length} block>
              Gửi sang pha chế
            </Btn>
          </aside>
        </div>
      ) : null}

      {report && role !== "nhan_vien" ? (
        <section className="nq-item mt-8" aria-label="Tổng quầy">
          <h2 className="text-sm font-mono uppercase tracking-widest">Tổng ca</h2>
          <p className="nq-muted mt-2 text-sm">
            {report.so_don} đơn · {report.tong_ly} ly · {MONEY.format(report.tong_tien)} · chưa thu {MONEY.format(report.chua_thu)}
          </p>
        </section>
      ) : null}

      <h2 className="mb-3 mt-10 text-sm font-mono uppercase tracking-widest text-[var(--nq-dim)]">Đơn của ca</h2>
      {!loading && orders.length === 0 ? <Empty>Chưa có đơn nào trong ca của bạn.</Empty> : null}
      <div className="nq-card-grid">
        {orders.map((order) => (
          <article key={order.id} className="nq-item">
            <p className="text-sm font-bold">{order.dong.map((line) => `${line.ten} × ${line.so_luong}`).join(", ")}</p>
            <p className="nq-muted mt-1 text-xs">{order.thanh_toan.replace("_", " ")}</p>
            <StatusChip tone={order.trang_thai === "xong" ? "ok" : order.trang_thai === "huy" ? "danger" : "warn"}>
              {order.trang_thai.replace("_", " ")}
            </StatusChip>
          </article>
        ))}
      </div>
    </section>
  );
}
