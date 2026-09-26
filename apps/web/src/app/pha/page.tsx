"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { donThanhToanLabel, donTrangThaiLabel, donTrangThaiTone, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import { ActionRow, Alert, Btn, Columns, Empty, Field, Input, Loading, OpsCard, PageHeader, StatusChip } from "../../ui/kit";

type Dong = { ten: string; so_luong: number };
type Don = {
  id: string;
  trang_thai: "cho_pha" | "dang_pha" | "xong" | "huy";
  dong: Dong[];
  thanh_toan: string;
  luc?: string;
};

/** Giờ vào đơn, rút gọn HH:MM — nhân viên pha nhìn mốc để biết đơn nào tới trước. */
function gioVao(luc?: string): string {
  if (!luc) return "";
  const d = new Date(luc);
  if (Number.isNaN(d.getTime())) return "";
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

/** Mã đơn rút gọn để gọi tên phiếu trên bàn pha, không lộ UUID dài. */
function maDon(id: string): string {
  const raw = id.replace(/^dq_/, "");
  return raw.slice(-4).toUpperCase();
}

function PhieuCard({
  item,
  primary,
  busy,
  onTransition,
}: {
  item: Don;
  primary: "dang_pha" | "xong";
  busy: boolean;
  onTransition: (trang_thai: "dang_pha" | "xong" | "huy", ly_do: string) => void;
}) {
  const [cancelling, setCancelling] = useState(false);
  const [lyDo, setLyDo] = useState("");
  const gio = gioVao(item.luc);

  return (
    <article className={`nq-phieu ${item.trang_thai === "dang_pha" ? "nq-phieu--dang_pha" : ""}`}>
      <header className="nq-phieu__head">
        <span className="nq-phieu__ma">Đơn {maDon(item.id)}</span>
        {gio ? <span className="nq-phieu__gio">{gio}</span> : null}
      </header>

      <div className="nq-phieu__body">
        {item.dong.map((line, i) => (
          <div key={`${item.id}-${i}`} className="nq-phieu__dong">
            <span className="nq-phieu__ten">{line.ten}</span>
            <span className="nq-phieu__so">× {line.so_luong}</span>
          </div>
        ))}
        {cancelling ? (
          <div className="nq-phieu__ly-do">
            <Field label="Lý do hủy">
              <Input
                value={lyDo}
                onChange={(e) => setLyDo(e.target.value)}
                placeholder="Bắt buộc ghi lý do trước khi hủy…"
              />
            </Field>
            <ActionRow align="end">
              <Btn variant="ghost" disabled={busy} onClick={() => setCancelling(false)}>
                Bỏ qua
              </Btn>
              <Btn variant="danger" busy={busy} onClick={() => onTransition("huy", lyDo)}>
                Xác nhận hủy
              </Btn>
            </ActionRow>
          </div>
        ) : null}
      </div>

      <footer className="nq-phieu__foot">
        <StatusChip tone={donTrangThaiTone(item.trang_thai)}>{donTrangThaiLabel(item.trang_thai)}</StatusChip>
        <span className="nq-muted text-xs">{donThanhToanLabel(item.thanh_toan)}</span>
        {!cancelling ? (
          <div className="ml-auto flex flex-wrap gap-2">
            <Btn variant="ghost" disabled={busy} onClick={() => setCancelling(true)}>
              Hủy đơn
            </Btn>
            <Btn busy={busy} onClick={() => onTransition(primary, "")}>
              {primary === "dang_pha" ? "Nhận pha" : "Hoàn tất"}
            </Btn>
          </div>
        ) : null}
      </footer>
    </article>
  );
}

export default function PhaPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Don[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!getToken()) return;
    setLoading(true);
    try {
      const out = await apiGet<{ items: Don[] }>("/api/v1/quay/don");
      setItems(out.items ?? []);
      setError(null);
    } catch (e) {
      setError(viError(e, { doing: "mở màn hình pha", forbidden: "Cần điểm danh ca trước khi mở màn hình pha." }));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => setToken(getToken()), []);
  useEffect(() => {
    if (token) void load();
  }, [load, token]);

  async function transition(id: string, trang_thai: "dang_pha" | "xong" | "huy", ly_do: string) {
    if (trang_thai === "huy" && !ly_do.trim()) {
      setError("Cần ghi lý do trước khi hủy đơn.");
      return;
    }
    setBusyId(id);
    try {
      await apiSend(`/api/v1/quay/don/${id}/chuyen`, { trang_thai, ly_do_huy: ly_do });
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
  const daXong = items.filter((x) => x.trang_thai === "xong");

  return (
    <section className="nq-page nq-page--wide">
      <PageHeader
        kicker="KDS nội bộ"
        title="Màn hình pha chế"
        meta="Ba cột theo dòng chảy: chờ pha → đang pha → đã xong. Hoàn tất đơn sẽ ghi tiêu thụ BOM ước lượng."
      />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="rows">Đang tải hàng chờ pha…</Loading> : null}

      {!loading ? (
        <Columns cols={3}>
          <OpsCard eyebrow="Bước 1" title="Chờ pha" count={choPha.length} countLabel="đơn" density="compact">
            {choPha.length === 0 ? (
              <Empty>Không có đơn đang chờ pha.</Empty>
            ) : (
              <div className="space-y-3">
                {choPha.map((item) => (
                  <PhieuCard
                    key={item.id}
                    item={item}
                    primary="dang_pha"
                    busy={busyId === item.id}
                    onTransition={(tt, lyDo) => void transition(item.id, tt, lyDo)}
                  />
                ))}
              </div>
            )}
          </OpsCard>

          <OpsCard eyebrow="Bước 2" title="Đang pha" count={dangPha.length} countLabel="đơn" density="compact">
            {dangPha.length === 0 ? (
              <Empty>Chưa có đơn đang pha.</Empty>
            ) : (
              <div className="space-y-3">
                {dangPha.map((item) => (
                  <PhieuCard
                    key={item.id}
                    item={item}
                    primary="xong"
                    busy={busyId === item.id}
                    onTransition={(tt, lyDo) => void transition(item.id, tt, lyDo)}
                  />
                ))}
              </div>
            )}
          </OpsCard>

          <OpsCard eyebrow="Bước 3" title="Đã xong trong ca" count={daXong.length} countLabel="đơn" density="compact">
            {daXong.length === 0 ? (
              <Empty>Trong ca chưa có đơn nào hoàn tất.</Empty>
            ) : (
              <div className="space-y-3">
                {daXong.map((item) => (
                  <article key={item.id} className="nq-phieu">
                    <header className="nq-phieu__head">
                      <span className="nq-phieu__ma">Đơn {maDon(item.id)}</span>
                      {gioVao(item.luc) ? <span className="nq-phieu__gio">{gioVao(item.luc)}</span> : null}
                    </header>
                    <div className="nq-phieu__body">
                      {item.dong.map((line, i) => (
                        <div key={`${item.id}-${i}`} className="nq-phieu__dong">
                          <span className="nq-phieu__ten">{line.ten}</span>
                          <span className="nq-phieu__so">× {line.so_luong}</span>
                        </div>
                      ))}
                    </div>
                    <footer className="nq-phieu__foot">
                      <StatusChip tone="ok">{donTrangThaiLabel(item.trang_thai)}</StatusChip>
                    </footer>
                  </article>
                ))}
              </div>
            )}
          </OpsCard>
        </Columns>
      ) : null}
    </section>
  );
}

