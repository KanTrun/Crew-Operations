"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import {
  actorLabel,
  formatLuc,
  ghiNhanLabel,
  safeText,
  treoLabel,
  treoTone,
  viError,
} from "../../lib/present";
import { getRole, getToken, isChuQuan, isManager } from "../../lib/session";
import { todayHeroLine, todayMetaLine, todayTechnicalDetail } from "../../lib/status";
import { SuaTimeline, TonBarChart, TreoDonutChart } from "../../ui/hom-nay/dashboard-charts";
import { KpiCard, StatusStrip } from "../../ui/hom-nay/kpi-card";
import { Alert, AuthGate, Btn, BtnLink, Loading, PageActions, StatusChip, TechnicalDrawer } from "../../ui/kit";

const SteamScene = dynamic(() => import("../../ui/hom-nay/steam-scene").then((m) => m.SteamScene), {
  ssr: false,
  loading: () => <div className="nq-dash-steam nq-dash-steam--placeholder" aria-hidden />,
});

type TreoPreview = { id: string; noi_dung: string; trang_thai?: string; nhan_vien?: string };
type SuaPreview = { loai?: string; luc?: string; ai?: string };
type TonRow = { hang?: string; so_luong?: number; duoi_nguong?: boolean };

type Today = {
  ngay: string;
  lich: { trang_thai?: string; nguon?: string; solver?: { status?: string } };
  so_treo?: number;
  so_inbox_cho?: number;
  so_luat?: number;
  canh_bao_ton?: string[];
  so_nhan_vien?: number;
  treo_preview?: TreoPreview[];
  sua_gan_day?: SuaPreview[];
  ton_tom_tat?: TonRow[];
};

function soAnToan(v: unknown): number {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

function useDesktop3d() {
  const [ok, setOk] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px) and (prefers-reduced-motion: no-preference)");
    const sync = () => setOk(mq.matches);
    sync();
    mq.addEventListener("change", sync);
    return () => mq.removeEventListener("change", sync);
  }, []);
  return ok;
}

export default function HomNayPage() {
  const [token, setToken] = useState("");
  const [data, setData] = useState<Today | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [manager, setManager] = useState(false);
  const [chuQuan, setChuQuan] = useState(false);
  const show3d = useDesktop3d();

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
  const preview = data?.treo_preview ?? [];
  const sua = data?.sua_gan_day ?? [];
  const ton = data?.ton_tom_tat ?? [];
  const tonThap = ton.filter((t) => t.duoi_nguong);
  const kpi2 = chuQuan ? soAnToan(data?.so_nhan_vien) : manager ? soAnToan(data?.so_inbox_cho) : soAnToan(data?.so_luat);
  const kpi2Label = chuQuan ? "Nhân viên chờ xem xét" : manager ? "Mục chờ duyệt" : "Luật cẩm nang";
  const kpi2Href = chuQuan ? "/nguoi" : manager ? "/inbox" : "/cam-nang";

  return (
    <div className="nq-page nq-page--dashboard">
      <div className="nq-dash-hero">
        <StatusStrip status={hero} meta={meta} />
        {show3d ? <SteamScene /> : null}
      </div>

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
          <div className="nq-dash-kpis nq-bento">
            <KpiCard value={treo} label="Việc treo" accent={treo > 0 ? "warn" : "default"} href="/treo" delay={0} />
            <KpiCard value={kpi2} label={kpi2Label} href={kpi2Href} delay={0.05} />
            <KpiCard
              value={canhBao.length || tonThap.length}
              label="Cảnh báo tồn"
              accent={canhBao.length > 0 ? "warn" : "default"}
              href="/tieu-thu"
              delay={0.1}
            />
            <KpiCard value={ngay ? ngay.slice(8, 10) : "—"} label={ngay ? `Tháng ${ngay.slice(5, 7)}` : "Ngày"} delay={0.15} />
          </div>

          <div className="nq-dash-body">
            <div className="nq-dash-main">
              <div className="nq-dash-charts">
                <TonBarChart rows={ton} />
                <TreoDonutChart items={preview} total={treo} />
              </div>

              {preview.length > 0 ? (
                <section className="nq-ops-card nq-dash-treo-list">
                  <div className="nq-dash-section-head">
                    <h2>Việc treo gần nhất</h2>
                    <Link href="/treo">Xem tất cả ({treo})</Link>
                  </div>
                  <div className="nq-list nq-dash-compact-list">
                    {preview.map((v) => (
                      <Link key={v.id} href="/treo" className="nq-item block hover:opacity-90">
                        <p className="nq-item-title">{v.noi_dung}</p>
                        <p className="nq-item-sub">
                          <StatusChip tone={treoTone(v.trang_thai)}>{treoLabel(v.trang_thai)}</StatusChip>
                        </p>
                      </Link>
                    ))}
                  </div>
                </section>
              ) : null}
            </div>

            <aside className="nq-dash-aside">
              {canhBao.length > 0 || tonThap.length > 0 ? (
                <Alert kind="info">
                  Tồn dưới ngưỡng: {(canhBao.length ? canhBao : tonThap.map((t) => t.hang)).join(", ")}.
                  <BtnLink href="/tieu-thu" variant="ghost">
                    Mở sổ tiêu thụ
                  </BtnLink>
                </Alert>
              ) : (
                <p className="nq-muted nq-dash-aside-note">Chưa có cảnh báo tồn từ sổ tiêu thụ.</p>
              )}

              <SuaTimeline
                items={sua}
                formatLuc={formatLuc}
                ghiNhanLabel={ghiNhanLabel}
                actorLabel={actorLabel}
              />

              {sua.length > 0 ? (
                <Link href="/treo" className="nq-dash-aside-link">
                  Tab ghi nhận sửa →
                </Link>
              ) : null}
            </aside>
          </div>

          <TechnicalDrawer lines={todayTechnicalDetail(data.lich ?? {})} />

          <div className="nq-dash-actions">
          <PageActions>
            {chuQuan ? (
              <>
                <BtnLink href="/nguoi">Quản lý người dùng</BtnLink>
                <BtnLink href="/cam-nang">Cẩm nang quán</BtnLink>
                <BtnLink href="/menu" variant="ghost">
                  Menu & giá
                </BtnLink>
                <BtnLink href="/vet" variant="ghost">
                  Xem vết hệ thống
                </BtnLink>
              </>
            ) : manager ? (
              <>
                <BtnLink href="/roster">Xếp lịch tuần</BtnLink>
                <BtnLink href="/inbox">Duyệt hộp thư</BtnLink>
                <BtnLink href="/cam-nang" variant="ghost">
                  Chạy cẩm nang
                </BtnLink>
                <BtnLink href="/treo" variant="ghost">
                  Xem việc treo
                </BtnLink>
              </>
            ) : (
              <>
                <BtnLink href="/phieu">Mở phiếu ca</BtnLink>
                <BtnLink href="/quay" variant="ghost">
                  Ghi đơn tại quầy
                </BtnLink>
                <BtnLink href="/toi" variant="ghost">
                  Ca của tôi
                </BtnLink>
                <BtnLink href="/sop" variant="ghost">
                  Hỏi cẩm nang
                </BtnLink>
              </>
            )}
          </PageActions>
          </div>
        </>
      ) : null}
    </div>
  );
}
