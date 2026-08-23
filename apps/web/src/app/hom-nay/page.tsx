"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { getToken, isManager, lifeLabel } from "../../lib/session";
import {
  Alert,
  AuthGate,
  BtnLink,
  EditorialBanner,
  Kicker,
  Loading,
  PageActions,
} from "../../ui/kit";

type Today = {
  ngay: string;
  lich: { trang_thai?: string; nguon?: string; solver?: { status?: string } };
  so_treo?: number;
  so_inbox_cho?: number;
  so_luat?: number;
  canh_bao_ton?: string[];
};

export default function HomNayPage() {
  const [token, setToken] = useState("");
  const [data, setData] = useState<Today | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manager, setManager] = useState(false);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<Today>("/api/v1/hom-nay")
      .then(setData)
      .catch(() => setError("Không đọc được bảng hôm nay. Kiểm tra API đang chạy."));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!token) return <AuthGate />;

  const life = data?.lich.trang_thai ?? "…";
  const bannerStatus = data
    ? `Ca ${lifeLabel(life).toLowerCase()} · ${data.so_treo ?? 0} việc treo`
    : "Đang đọc nhịp quán…";

  return (
    <>
      <EditorialBanner
        status={bannerStatus}
        meta={
          data
            ? `Ngày ${data.ngay}${data.lich.solver?.status ? ` · solver ${data.lich.solver.status}` : ""}`
            : undefined
        }
      />
      <div className="nq-page">
        <Kicker>Ca hôm nay</Kicker>
        <h1>Quán hôm nay</h1>
        {error ? <Alert>{error}</Alert> : null}
        {!data && !error ? <Loading skeleton="tiles">Đang tải bảng hôm nay…</Loading> : null}
        {data ? (
          <>
            <p className="nq-muted">
              Ngày {data.ngay} · lịch {lifeLabel(life)} · nguồn quán
              {data.lich.solver?.status ? ` · solver ${data.lich.solver.status}` : ""}
            </p>
            <div className="nq-row" style={{ margin: "1rem 0 1.25rem" }}>
              <div className="nq-tile">
                <strong>{data.so_treo ?? 0}</strong>
                <span>Việc treo</span>
              </div>
              <div className="nq-tile">
                <strong>{manager ? (data.so_inbox_cho ?? 0) : (data.so_luat ?? 0)}</strong>
                <span>{manager ? "Chờ duyệt" : "Luật cẩm nang"}</span>
              </div>
            </div>
            {data.canh_bao_ton && data.canh_bao_ton.length > 0 ? (
              <Alert kind="info">Tồn dưới ngưỡng: {data.canh_bao_ton.join(", ")}</Alert>
            ) : (
              <p className="nq-muted">Chưa có cảnh báo tồn từ sổ tiêu thụ.</p>
            )}
            <PageActions>
              {manager ? (
                <>
                  <BtnLink href="/roster">Lịch tuần</BtnLink>
                  <BtnLink href="/inbox" variant="ghost">
                    Hộp thư
                  </BtnLink>
                  <BtnLink href="/treo" variant="ghost">
                    Việc treo
                  </BtnLink>
                </>
              ) : (
                <>
                  <BtnLink href="/phieu">Mở phiếu</BtnLink>
                  <BtnLink href="/toi" variant="ghost">
                    Ca của tôi
                  </BtnLink>
                  <BtnLink href="/treo" variant="ghost">
                    Việc treo
                  </BtnLink>
                </>
              )}
            </PageActions>
          </>
        ) : null}
      </div>
    </>
  );
}
