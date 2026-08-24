"use client";

/**
 * Bảng Hôm nay — bento, mỗi ô một con số thật.
 *
 * Ô trống là lời hứa suông: người dùng thấy khung mà không thấy tin, rồi phải mở
 * trang khác để biết. Nên trang gọi thêm `/api/v1/viec-treo` để tách 18 việc
 * treo thành quá hạn / đang chờ — bảng tổng mà không nói việc nào gấp thì người
 * mở ca vẫn phải đi dò.
 *
 * Ô nào không có số thật thì không dựng ô đó, thay vì dựng ô rồi điền dấu gạch.
 */

import { useCallback, useEffect, useState, useRef } from "react";
import { motion } from "framer-motion";
import gsap from "gsap";
import { apiGet } from "../../lib/api";
import { formatNgay, safeText, treoLabel, viError } from "../../lib/present";
import { getToken, isManager, lifeLabel } from "../../lib/session";
import { todayHeroLine, todayMetaLine, todayTechnicalDetail } from "../../lib/status";
import {
  Alert,
  AuthGate,
  BentoTile,
  Btn,
  BtnLink,
  Loading,
  OpsCard,
  PageActions,
  Summary,
  TechnicalDrawer,
  EditorialBanner,
  PageHeader,
} from "../../ui/kit";

type Today = {
  ngay: string;
  lich: { trang_thai?: string; nguon?: string; tuan_iso?: string; solver?: { status?: string } };
  so_treo?: number;
  so_inbox_cho?: number;
  so_luat?: number;
  canh_bao_ton?: string[];
};

type ViecTreo = { id: string; trang_thai?: string; noi_dung?: string; han?: string };

/** Đếm an toàn: field thiếu hoặc rác thì coi như 0, không để "NaN" ra ô số. */
function soAnToan(v: unknown): number {
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) && n >= 0 ? n : 0;
}

export default function HomNayPage() {
  const [token, setToken] = useState("");
  const [data, setData] = useState<Today | null>(null);
  const [treo, setTreo] = useState<ViecTreo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [manager, setManager] = useState(false);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setError(null);
    apiGet<Today>("/api/v1/hom-nay")
      .then(setData)
      .catch((e) => setError(viError(e, { doing: "đọc được bảng hôm nay" })));
    // Việc treo tách theo trạng thái: bảng tổng phải nói được việc nào gấp.
    apiGet<{ items: ViecTreo[] }>("/api/v1/viec-treo")
      .then((d) => setTreo((d.items ?? []).filter((x) => x && typeof x.id === "string")))
      .catch(() => setTreo([]));
  }, []);

  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  useEffect(() => {
    if (data && containerRef.current) {
      gsap.fromTo(
        ".bento-item",
        { y: 50, opacity: 0, scale: 0.95 },
        { y: 0, opacity: 1, scale: 1, stagger: 0.05, duration: 0.6, ease: "back.out(1.5)" }
      );
    }
  }, [data]);

  if (!token) return <AuthGate />;

  const tongTreo = treo.length > 0 ? treo.length : soAnToan(data?.so_treo);
  const quaHan = treo.filter((v) => v.trang_thai === "qua_han").length;
  const dangCho = treo.filter((v) => v.trang_thai === "dang_cho").length;
  const xong = treo.filter((v) => v.trang_thai === "xong").length;
  const ngay = safeText(data?.ngay, "");
  const hero = data ? todayHeroLine(tongTreo, data.lich?.trang_thai) : "Đang đọc nhịp quán…";
  const meta = data && ngay ? todayMetaLine(ngay, data.lich?.nguon) : undefined;
  const canhBao = (data?.canh_bao_ton ?? []).map((x) => safeText(x, "")).filter(Boolean);
  const trangThaiLich = safeText(data?.lich?.trang_thai, "");
  // Ba việc quá hạn cũ nhất: cái người mở ca nên nhận ngay, không phải cuộn tìm.
  const gap = treo.filter((v) => v.trang_thai === "qua_han").slice(0, 3);

  return (
    <>
      <EditorialBanner status={hero} meta={meta} />
      <div className="nq-page nq-page--home">
        <PageHeader
          kicker="Ca hôm nay"
          title="Quán hôm nay"
          meta="Bảng gộp một màn: việc treo, mục chờ duyệt, cảnh báo tồn của ca hiện tại."
          tourId="hub-head"
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
            {treo.length > 0 ? (
              <Summary
                cells={[
                  { n: tongTreo, k: "việc treo" },
                  { n: quaHan, k: "quá hạn", tone: "danger" },
                  { n: dangCho, k: "đang chờ", tone: "warn" },
                  { n: xong, k: "xong", tone: "ok" },
                ]}
              />
            ) : null}

            <div className="nq-bento">
              <BentoTile
                large
                value={tongTreo}
                label={
                  quaHan > 0
                    ? `Việc treo · ${quaHan} quá hạn cần xử trước`
                    : "Việc treo · không việc nào quá hạn"
                }
                accent={quaHan > 0 ? "warn" : "default"}
                href="/treo"
              />
              <BentoTile
                value={quaHan}
                label="Quá hạn"
                accent={quaHan > 0 ? "warn" : "ok"}
                href="/treo"
              />
              {manager ? (
                <BentoTile
                  value={soAnToan(data.so_inbox_cho)}
                  label="Mục chờ bạn duyệt"
                  accent={soAnToan(data.so_inbox_cho) > 0 ? "warn" : "default"}
                  href="/inbox"
                />
              ) : (
                <BentoTile value={dangCho} label="Việc đang chờ làm" href="/treo" />
              )}
              <BentoTile value={soAnToan(data.so_luat)} label="Luật trong cẩm nang" href="/cam-nang" />
              <BentoTile
                value={trangThaiLich ? lifeLabel(trangThaiLich) : "—"}
                label={
                  data.lich?.tuan_iso ? `Lịch tuần ${safeText(data.lich.tuan_iso)}` : "Trạng thái lịch tuần"
                }
                href={manager ? "/roster" : "/toi"}
              />
            </div>

            {/* Các nút hành động */}
            <div className="mt-8 flex flex-wrap gap-4">
              {manager ? (
                <>
                  <BtnLink href="/roster" variant="primary">Xếp lịch tuần</BtnLink>
                  <BtnLink href="/inbox" variant="ghost">Duyệt hộp thư</BtnLink>
                  <BtnLink href="/cam-nang" variant="ghost">Đọc cẩm nang</BtnLink>
                </>
              ) : (
                <>
                  <BtnLink href="/phieu" variant="primary">Mở phiếu ca</BtnLink>
                  <BtnLink href="/toi" variant="ghost">Xem ca của tôi</BtnLink>
                  <BtnLink href="/treo" variant="ghost">Xem việc treo</BtnLink>
                </>
              )}
            </div>
            
            <div className="mt-8">
              <TechnicalDrawer lines={todayTechnicalDetail(data.lich ?? {})} />
            </div>
          </>
        ) : null}
      </div>
    </>
  );
}
