"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { getToken, isManager } from "../../lib/session";
import { todayHeroLine, todayMetaLine, todayTechnicalDetail } from "../../lib/status";
import {
  Alert,
  AuthGate,
  BentoTile,
  BtnLink,
  EditorialBanner,
  Kicker,
  Loading,
  PageActions,
  TechnicalDrawer,
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

  const treo = data?.so_treo ?? 0;
  const hero = data ? todayHeroLine(treo, data.lich.trang_thai) : "Đang đọc nhịp quán…";
  const meta = data ? todayMetaLine(data.ngay, data.lich.nguon) : undefined;

  return (
    <>
      <EditorialBanner status={hero} meta={meta} />
      <div className="nq-page">
        <Kicker>Ca hôm nay</Kicker>
        <h1>Quán hôm nay</h1>
        {error ? <Alert>{error}</Alert> : null}
        {!data && !error ? <Loading skeleton="bento">Đang tải bảng hôm nay…</Loading> : null}
        {data ? (
          <>
            <p className="nq-meta-strip">{todayMetaLine(data.ngay, data.lich.nguon)}</p>

            <div className="nq-bento">
              <BentoTile
                large
                value={treo}
                label="Việc treo"
                accent={treo > 0 ? "warn" : "default"}
                href="/treo"
              />
              <BentoTile
                value={manager ? (data.so_inbox_cho ?? 0) : (data.so_luat ?? 0)}
                label={manager ? "Chờ duyệt" : "Luật cẩm nang"}
                href={manager ? "/inbox" : "/cam-nang"}
              />
              <BentoTile value={data.ngay.slice(8, 10)} label={`Tháng ${data.ngay.slice(5, 7)}`} />
            </div>

            <TechnicalDrawer lines={todayTechnicalDetail(data.lich)} />

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
