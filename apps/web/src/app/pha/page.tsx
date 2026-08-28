"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import { Alert, Btn, Empty, Field, Loading, PageHeader, StatusChip } from "../../ui/kit";

type Dong = { ten: string; so_luong: number };
type Don = { id: string; trang_thai: "cho_pha" | "dang_pha" | "xong" | "huy"; dong: Dong[]; thanh_toan: string };

export default function PhaPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Don[]>([]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getToken()) return;
    setLoading(true);
    try {
      const out = await apiGet<{ items: Don[] }>("/api/v1/quay/don");
      setItems((out.items ?? []).filter((x) => x.trang_thai === "cho_pha" || x.trang_thai === "dang_pha"));
      setError(null);
    } catch (e) {
      setError(viError(e, { doing: "mở màn hình pha", forbidden: "Cần điểm danh ca trước khi mở màn hình pha." }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => setToken(getToken()), []);
  useEffect(() => { if (token) void load(); }, [load, token]);

  async function transition(id: string, trang_thai: "dang_pha" | "xong" | "huy") {
    if (trang_thai === "huy" && !reasons[id]?.trim()) {
      setError("Cần ghi lý do trước khi hủy đơn.");
      return;
    }
    setBusyId(id);
    try {
      await apiSend(`/api/v1/quay/don/${id}/chuyen`, { trang_thai, ly_do_huy: reasons[id] ?? "" });
      await load();
    } catch (e) {
      setError(viError(e, { doing: "chuyển trạng thái đơn" }));
    } finally {
      setBusyId("");
    }
  }

  if (!token) return null;
  return (
    <section className="nq-page">
      <PageHeader kicker="KDS nội bộ" title="Màn hình pha chế" meta="Chỉ hiển thị đơn quầy của ca đang điểm danh; hoàn tất đơn sẽ ghi tiêu thụ BOM ước lượng." />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="rows">Đang tải hàng chờ pha…</Loading> : null}
      {!loading && items.length === 0 ? <Empty>Không có đơn đang chờ pha.</Empty> : null}
      <div className="nq-list">
        {items.map((item) => (
          <article key={item.id} className="nq-item">
            <div>
              <p><strong>{item.dong.map((line) => `${line.ten} × ${line.so_luong}`).join(", ")}</strong></p>
              <p className="nq-muted">Thanh toán: {item.thanh_toan}</p>
              <StatusChip tone={item.trang_thai === "dang_pha" ? "warn" : "default"}>{item.trang_thai.replace("_", " ")}</StatusChip>
            </div>
            <div className="flex flex-col gap-2">
              {item.trang_thai === "cho_pha" ? <Btn busy={busyId === item.id} onClick={() => void transition(item.id, "dang_pha")}>Nhận pha</Btn> : null}
              {item.trang_thai === "dang_pha" ? <Btn busy={busyId === item.id} onClick={() => void transition(item.id, "xong")}>Hoàn tất</Btn> : null}
              <Field label="Lý do hủy">
                <input value={reasons[item.id] ?? ""} onChange={(e) => setReasons((old) => ({ ...old, [item.id]: e.target.value }))} />
              </Field>
              <Btn variant="danger" busy={busyId === item.id} onClick={() => void transition(item.id, "huy")}>Hủy đơn</Btn>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
