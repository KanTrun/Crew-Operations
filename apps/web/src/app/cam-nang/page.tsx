"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { luatLabel, luatTone, safeText, viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Loading,
  Notice,
  PageHeader,
  StatusChip,
  TechnicalDrawer,
} from "../../ui/kit";

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
  const [manager, setManager] = useState(false);
  const [items, setItems] = useState<Luat[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [soThat, setSoThat] = useState<number | null>(null);
  const [chiTiet, setChiTiet] = useState<string[]>([]);
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
    apiGet<{ items: Luat[] }>("/api/v1/cam-nang")
      .then((d) => {
        setItems((d.items ?? []).filter((x) => x && typeof x.id === "string"));
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "mở được cẩm nang quán" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function chay() {
    setError(null);
    setMsg(null);
    setBusy(true);
    try {
      const d = await apiSend<{ bi_loai?: { vf_rule?: string }; so_luat_that_quan?: number }>(
        "/api/v1/cam-nang/chay-8-buoc",
      );
      const that = typeof d.so_luat_that_quan === "number" ? d.so_luat_that_quan : 0;
      setSoThat(that);
      setMsg(
        that > 0
          ? `Đã chạy đủ 8 bước. Quán đang có ${that} luật sinh từ người thật.`
          : "Đã chạy đủ 8 bước. Chưa có luật nào sinh từ người quán thật — cần thêm lần sửa có bằng chứng.",
      );
      // Mã cổng VF là chi tiết kỹ thuật: để trong ngăn, không phơi lên thân trang.
      setChiTiet([`Cổng loại luật: ${safeText(d.bi_loai?.vf_rule, "không có luật nào bị loại")}`]);
      load();
    } catch (e) {
      setError(
        viError(e, {
          doing: "chạy được 8 bước cẩm nang",
          forbidden: "Chỉ quản lý hoặc chủ quán chạy được 8 bước.",
          conflict: "Chưa đủ lần sửa có bằng chứng để chạy 8 bước. Ghi thêm lần sửa rồi chạy lại.",
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
        kicker="Cẩm nang sống"
        title="Cẩm nang quán"
        meta={`Luật của quán chỉ có hiệu lực khi đủ bằng chứng từ lần sửa thật. Luật sinh từ người quán: ${
          soThat ?? "chưa chạy hôm nay"
        }.`}
      />
      {manager ? (
        <Btn variant="primary" disabled={busy} onClick={chay}>
          {busy ? "Đang chạy…" : "Chạy 8 bước xét luật"}
        </Btn>
      ) : (
        <Notice>Bạn xem được luật quán. Quản lý hoặc chủ quán mới chạy 8 bước xét luật.</Notice>
      )}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {error ? <Alert>{error}</Alert> : null}
      {chiTiet.length > 0 ? <TechnicalDrawer lines={chiTiet} /> : null}
      {loading ? <Loading skeleton="list">Đang mở cẩm nang…</Loading> : null}
      {!loading && !error && items.length === 0 ? (
        <Empty>Chưa có luật nào. Luật sinh ra từ lần sửa có bằng chứng trong ca.</Empty>
      ) : null}
      <div className="nq-list">
        {items.map((luat) => (
          <article key={luat.id} className="nq-item">
            <p className="nq-item-title">{safeText(luat.cau, "Luật chưa có câu diễn giải")}</p>
            <p className="nq-item-sub">
              <StatusChip tone={luatTone(luat.trang_thai)}>{luatLabel(luat.trang_thai)}</StatusChip>
              {typeof luat.tap_su_dung === "number" ? ` · tập sự ${luat.tap_su_dung} lượt` : ""}
              {typeof luat.ap_dung === "number" ? ` · đã áp dụng ${luat.ap_dung} lần` : ""}
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
