"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import { ActionRow, Alert, Btn, Empty, Field, Input, Loading, OpsCard, PageGrid, PageHeader, StatusChip } from "../../ui/kit";

type Dong = { ten: string; so_luong: number };
type Don = { id: string; trang_thai: "cho_pha" | "dang_pha" | "xong" | "huy"; dong: Dong[]; thanh_toan: string };

export default function PhaPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Don[]>([]);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [showCancel, setShowCancel] = useState<Record<string, boolean>>({});
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

  const choPha = items.filter((x) => x.trang_thai === "cho_pha");
  const dangPha = items.filter((x) => x.trang_thai === "dang_pha");

  function DonCard({ item, primary }: { item: Don; primary: "dang_pha" | "xong" }) {
    const cancelling = showCancel[item.id] === true;
    return (
      <article className="nq-card p-4">
        <p className="font-semibold">{item.dong.map((line) => `${line.ten} × ${line.so_luong}`).join(", ")}</p>
        <p className="nq-muted text-sm">Thanh toán: {item.thanh_toan}</p>
        <StatusChip tone={item.trang_thai === "dang_pha" ? "warn" : "default"}>{item.trang_thai.replace("_", " ")}</StatusChip>

        <ActionRow>
          <Btn busy={busyId === item.id} onClick={() => void transition(item.id, primary)}>
            {primary === "dang_pha" ? "Nhận pha" : "Hoàn tất"}
          </Btn>
          {!cancelling ? (
            <Btn variant="ghost" disabled={busyId === item.id} onClick={() => setShowCancel((s) => ({ ...s, [item.id]: true }))}>
              Hủy đơn
            </Btn>
          ) : null}
        </ActionRow>

        {cancelling ? (
          <div className="mt-3 border-t border-[var(--nq-line)] pt-3">
            <Field label="Lý do hủy">
              <Input
                value={reasons[item.id] ?? ""}
                onChange={(e) => setReasons((old) => ({ ...old, [item.id]: e.target.value }))}
                placeholder="Bắt buộc ghi lý do trước khi hủy…"
              />
            </Field>
            <ActionRow align="end">
              <Btn variant="ghost" disabled={busyId === item.id} onClick={() => setShowCancel((s) => ({ ...s, [item.id]: false }))}>
                Bỏ qua
              </Btn>
              <Btn variant="danger" busy={busyId === item.id} onClick={() => void transition(item.id, "huy")}>
                Xác nhận hủy
              </Btn>
            </ActionRow>
          </div>
        ) : null}
      </article>
    );
  }

  return (
    <section className="nq-page">
      <PageHeader
        kicker="KDS nội bộ"
        title="Màn hình pha chế"
        meta="Chỉ hiển thị đơn quầy của ca đang điểm danh; hoàn tất đơn sẽ ghi tiêu thụ BOM ước lượng."
      />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="rows">Đang tải hàng chờ pha…</Loading> : null}

      {!loading ? (
        <PageGrid
          main={
            <OpsCard eyebrow="Đang chờ" title="Chờ pha" count={choPha.length} countLabel="đơn" density="compact">
              {choPha.length === 0 ? (
                <Empty>Không có đơn đang chờ pha.</Empty>
              ) : (
                <div className="nq-columns" data-cols="2">
                  {choPha.map((item) => (
                    <DonCard key={item.id} item={item} primary="dang_pha" />
                  ))}
                </div>
              )}
            </OpsCard>
          }
          aside={
            <OpsCard eyebrow="Đang pha" title="Đang pha" count={dangPha.length} countLabel="đơn" density="compact">
              {dangPha.length === 0 ? (
                <Empty>Chưa có đơn đang pha.</Empty>
              ) : (
                <div className="space-y-3">
                  {dangPha.map((item) => (
                    <DonCard key={item.id} item={item} primary="xong" />
                  ))}
                </div>
              )}
            </OpsCard>
          }
        />
      ) : null}
    </section>
  );
}
