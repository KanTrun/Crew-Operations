"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
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
  StatusChip,
  TechnicalDrawer,
} from "../../ui/kit";

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
  const preview = data?.treo_preview ?? [];
  const sua = data?.sua_gan_day ?? [];
  const ton = data?.ton_tom_tat ?? [];
  const tonThap = ton.filter((t) => t.duoi_nguong);

  return (
    <>
      <EditorialBanner status={hero} meta={meta} />
      <div className="nq-page">
        <PageHeader
          kicker="Ca hôm nay"
          title="Quán hôm nay"
          meta="Bảng gộp một màn: việc treo, mục chờ duyệt, cảnh báo tồn, và việc cần làm ngay."
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
                value={canhBao.length || tonThap.length}
                label="Cảnh báo tồn"
                accent={canhBao.length > 0 ? "warn" : "default"}
                href="/tieu-thu"
              />
              <BentoTile
                value={ngay ? ngay.slice(8, 10) : "—"}
                label={ngay ? `Tháng ${ngay.slice(5, 7)}` : "Chưa rõ ngày"}
              />
            </div>

            {preview.length > 0 ? (
              <section className="nq-ops-card mt-6">
                <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
                  <h2 className="text-sm font-mono uppercase tracking-widest text-[var(--nq-copper)]">
                    Việc treo gần nhất
                  </h2>
                  <Link href="/treo" className="text-xs text-[var(--nq-copper)] underline">
                    Xem tất cả ({treo})
                  </Link>
                </div>
                <div className="nq-list">
                  {preview.map((v) => (
                    <Link key={v.id} href="/treo" className="nq-item block hover:opacity-90">
                      <p className="nq-item-title">{v.noi_dung}</p>
                      <p className="nq-item-sub flex flex-wrap gap-2">
                        <StatusChip tone={treoTone(v.trang_thai)}>{treoLabel(v.trang_thai)}</StatusChip>
                      </p>
                    </Link>
                  ))}
                </div>
              </section>
            ) : null}

            {canhBao.length > 0 || tonThap.length > 0 ? (
              <Alert kind="info">
                Tồn dưới ngưỡng: {(canhBao.length ? canhBao : tonThap.map((t) => t.hang)).join(", ")}.
                <BtnLink href="/tieu-thu" variant="ghost">
                  Mở sổ tiêu thụ
                </BtnLink>
              </Alert>
            ) : (
              <p className="nq-muted">Chưa có cảnh báo tồn từ sổ tiêu thụ.</p>
            )}

            {sua.length > 0 ? (
              <section className="nq-ops-card mt-6">
                <div className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
                  <h2 className="text-sm font-mono uppercase tracking-widest text-[var(--nq-copper)]">
                    Sửa lịch gần đây
                  </h2>
                  <Link href="/treo" className="text-xs text-[var(--nq-copper)] underline">
                    Tab ghi nhận sửa
                  </Link>
                </div>
                <div className="nq-list">
                  {sua.map((g, i) => (
                    <article key={i} className="nq-item">
                      <p className="nq-item-title">{ghiNhanLabel(g.loai)}</p>
                      <p className="nq-item-sub">
                        {actorLabel(g.ai)} · {formatLuc(g.luc)}
                      </p>
                    </article>
                  ))}
                </div>
              </section>
            ) : null}

            <TechnicalDrawer lines={todayTechnicalDetail(data.lich ?? {})} />

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
          </>
        ) : null}
      </div>
    </>
  );
}
