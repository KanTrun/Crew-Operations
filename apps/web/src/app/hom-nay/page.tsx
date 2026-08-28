"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { safeText, viError } from "../../lib/present";
import { getRole, getToken, isChuQuan, isManager } from "../../lib/session";
import { todayHeroLine, todayMetaLine, todayTechnicalDetail } from "../../lib/status";
import {
  Alert,
  AuthGate,
  BentoTile,
  Btn,
  BtnLink,
  EditorialBanner,
  Loading,
  PageActions,
  PageHeader,
  TechnicalDrawer,
} from "../../ui/kit";

type Today = {
  ngay: string;
  lich: { trang_thai?: string; nguon?: string; solver?: { status?: string } };
  so_treo?: number;
  so_inbox_cho?: number;
  so_luat?: number;
  canh_bao_ton?: string[];
  so_nhan_vien?: number;
};

/** Đếm an toàn: field thiếu hoặc rác thì coi như 0, không để "NaN" ra ô số. */
function soAnToan(v: unknown): number {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

export default function HomNayPage() {
  const [token, setToken] = useState("");
  const [data, setData] = useState<Today | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manager, setManager] = useState(false);
  const [chuQuan, setChuQuan] = useState(false);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setChuQuan(isChuQuan(getRole()));
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setError(null);
    apiGet<Today>("/api/v1/hom-nay")
      .then(setData)
      .catch((e) => setError(viError(e, { doing: "đọc được bảng hôm nay" })));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  if (!token) return <AuthGate />;

  const treo = soAnToan(data?.so_treo);
  const ngay = safeText(data?.ngay, "");
  const hero = data ? todayHeroLine(treo, data.lich?.trang_thai) : "Đang đọc nhịp quán…";
  const meta = data && ngay ? todayMetaLine(ngay, data.lich?.nguon) : undefined;
  const canhBao = (data?.canh_bao_ton ?? []).map((x) => safeText(x, "")).filter(Boolean);

  return (
    <>
      <EditorialBanner status={hero} meta={meta} />
      <div className="nq-page">
        <PageHeader
          kicker="Ca hôm nay"
          title="Quán hôm nay"
          meta="Bảng gộp một màn: việc treo, mục chờ duyệt, cảnh báo tồn của ca hiện tại."
        />
        {error ? (
          <>
            <Alert>{error}</Alert>
            <PageActions>
              <Btn variant="ghost" onClick={load}>
                Tải lại bảng
              </Btn>
            </PageActions>
          </>
        ) : null}
        {!data && !error ? <Loading skeleton="bento">Đang tải bảng hôm nay…</Loading> : null}
        {data ? (
          <>
            <div className="nq-bento">
              <BentoTile
                large
                value={treo}
                label="Việc treo"
                accent={treo > 0 ? "warn" : "default"}
                href="/treo"
              />
              <BentoTile
                value={chuQuan ? soAnToan(data.so_nhan_vien) : manager ? soAnToan(data.so_inbox_cho) : soAnToan(data.so_luat)}
                label={chuQuan ? "Nhân viên chờ xem xét" : manager ? "Mục chờ duyệt" : "Luật cẩm nang"}
                href={chuQuan ? "/nguoi" : manager ? "/inbox" : "/cam-nang"}
              />
              <BentoTile
                value={ngay ? ngay.slice(8, 10) : "—"}
                label={ngay ? `Tháng ${ngay.slice(5, 7)}` : "Chưa rõ ngày"}
              />
            </div>

            <TechnicalDrawer lines={todayTechnicalDetail(data.lich ?? {})} />

            {canhBao.length > 0 ? (
              <Alert kind="info">
                Tồn dưới ngưỡng: {canhBao.join(", ")}. Mở Sổ tiêu thụ để ghi kiểm kê hoặc đặt thêm.
              </Alert>
            ) : (
              <p className="nq-muted">Chưa có cảnh báo tồn từ sổ tiêu thụ.</p>
            )}

            <PageActions>
              {chuQuan ? (
                <>
                  <BtnLink href="/nguoi">Quản lý người dùng</BtnLink>
                  <BtnLink href="/menu" variant="ghost">Menu & giá</BtnLink>
                  <BtnLink href="/vet" variant="ghost">Xem vết hệ thống</BtnLink>
                </>
              ) : manager ? (
                <>
                  <BtnLink href="/roster">Xếp lịch tuần</BtnLink>
                  <BtnLink href="/inbox" variant="ghost">
                    Duyệt hộp thư
                  </BtnLink>
                  <BtnLink href="/treo" variant="ghost">
                    Xem việc treo
                  </BtnLink>
                </>
              ) : (
                <>
                  <BtnLink href="/phieu">Mở phiếu ca</BtnLink>
                  <BtnLink href="/quay" variant="ghost">Ghi đơn tại quầy</BtnLink>
                  <BtnLink href="/toi" variant="ghost">
                    Xem ca của tôi
                  </BtnLink>
                  <BtnLink href="/treo" variant="ghost">
                    Xem việc treo
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
