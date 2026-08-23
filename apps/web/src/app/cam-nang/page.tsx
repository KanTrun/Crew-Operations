"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken, isManager } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Loading, PageHeader, StatusChip } from "../../ui/kit";

type Luat = {
  id: string;
  cau?: string;
  trang_thai: string;
  tap_su_dung?: number;
  ap_dung?: number;
  ghi_de?: number;
  vf_rule?: string;
  bang_chung?: string[];
};

export default function CamNangPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Luat[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [soThat, setSoThat] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Luat[] }>("/api/v1/cam-nang")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không tải được cẩm nang."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function chay() {
    setError(null);
    try {
      const d = await apiSend<{ bi_loai?: { vf_rule?: string }; so_luat_that_quan?: number }>(
        "/api/v1/cam-nang/chay-8-buoc",
      );
      setSoThat(d.so_luat_that_quan ?? 0);
      setMsg(
        `Đã chạy 8 bước. VF-RULE loại: ${d.bi_loai?.vf_rule ?? "—"}. Luật từ người quán ngoài: ${d.so_luat_that_quan ?? 0}.`,
      );
      load();
    } catch {
      setError("Không chạy được. Cần quyền quản lý và đủ lần sửa.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Cẩm nang sống"
        title="Cẩm nang quán"
        meta={`Luật chỉ hiệu lực khi đủ bằng chứng sửa. Số luật quán thật: ${soThat ?? "chưa chạy"}.`}
      />
      {isManager() ? (
        <Btn variant="primary" onClick={chay}>
          Chạy 8 bước
        </Btn>
      ) : (
        <p className="nq-muted">Nhân viên chỉ xem. Quản lý chạy 8 bước.</p>
      )}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang mở cẩm nang…</Loading> : null}
      {!loading && items.length === 0 ? <Empty>Chưa có luật.</Empty> : null}
      <div className="nq-list">
        {items.map((luat) => (
          <article key={luat.id} className="nq-item">
            <p className="nq-item-title">{luat.cau ?? luat.id}</p>
            <p className="nq-item-sub">
              <StatusChip tone={luat.trang_thai === "hieu_luc" ? "ok" : "default"}>
                {luat.trang_thai}
              </StatusChip>
              {luat.tap_su_dung != null ? ` · tập sự ${luat.tap_su_dung}` : ""}
              {luat.ap_dung != null ? ` · áp dụng ${luat.ap_dung}` : ""}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
