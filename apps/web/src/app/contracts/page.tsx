"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Empty,
  Loading,
  OpsCard,
  PageActions,
  PageHeader,
  BtnLink,
  TechnicalDrawer,
} from "../../ui/kit";

/** Năm hợp đồng dữ liệu của quán, kèm câu tiếng Việt nói hợp đồng đó giữ gì. */
const HOP_DONG: Array<[string, string, string]> = [
  ["NhanVien", "Hồ sơ nhân viên", "Ai làm được vị trí nào, giới hạn giờ và ngày nghỉ."],
  ["Ca", "Một ca làm việc", "Ngày, khung giờ, vị trí cần người."],
  ["LichTuan", "Lịch tuần", "Ca nào ai đứng, và lịch đang ở bước nào trong vòng công bố."],
  ["PhieuMau", "Mẫu phiếu", "Các bước phải làm trong ca và bằng chứng cần chụp."],
  ["RangBuocTrichXuat", "Ràng buộc trích được", "Điều kiện lấy từ tin nhắn và bàn giao, chờ người duyệt."],
];

export default function ContractsPage() {
  const [token, setToken] = useState("");
  const [payload, setPayload] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    setLoading(true);
    apiGet<Record<string, unknown>>("/api/v1/contracts")
      .then((d) => {
        setPayload(d);
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "đọc được năm hợp đồng dữ liệu" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setToken(getToken());
    load();
  }, [load]);

  if (!token) return <AuthGate />;

  const co = HOP_DONG.filter(([key]) => payload != null && key in payload);

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Nền dữ liệu"
        title="Năm hợp đồng"
        meta="Năm khuôn dữ liệu mà cả quán dùng chung. Trang tra cứu — bản mô tả kỹ thuật nằm trong ngăn từng thẻ."
      />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang đọc hợp đồng dữ liệu…</Loading> : null}
      {!loading && !error && co.length === 0 ? (
        <Empty>Máy chủ chưa trả hợp đồng nào. Kiểm tra lại sau, hoặc báo quản lý.</Empty>
      ) : null}
      {co.map(([key, ten, mo_ta]) => (
        <OpsCard key={key} eyebrow="Hợp đồng dữ liệu" title={ten}>
          <p className="nq-muted">{mo_ta}</p>
          {/* JSON là chi tiết kỹ thuật: nằm trong ngăn, không phơi mặc định
              (docs/design-guidelines.md — Progressive disclosure). */}
          <TechnicalDrawer summary="Xem khuôn dữ liệu">
            <pre>{JSON.stringify(payload?.[key], null, 2)}</pre>
          </TechnicalDrawer>
        </OpsCard>
      ))}
      <PageActions>
        <BtnLink href="/hom-nay" variant="ghost">
          Về bảng hôm nay
        </BtnLink>
      </PageActions>
    </div>
  );
}
