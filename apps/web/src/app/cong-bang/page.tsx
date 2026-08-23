"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { safeNumber, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Empty,
  Loading,
  Notice,
  OpsCard,
  PageHeader,
  StatusChip,
} from "../../ui/kit";

const AXIS: Record<string, string> = {
  cuoi_tuan: "Ca cuối tuần",
  dem: "Ca đêm",
  gio: "Số giờ",
  vun: "Ca vụn",
};

type Body = {
  so_du?: Record<string, Record<string, number>>;
  means?: Record<string, number>;
  nv_id?: string;
  axes?: string[];
};

function axisLabel(a: string): string {
  return AXIS[a] ?? a;
}

/** Chênh so với trung bình nhóm — chỉ nói hướng, không nói ai hơn ai. */
function lech(mine: number, mean: number) {
  const d = mine - mean;
  if (Math.abs(d) < 0.05) return { tone: "ok" as const, text: "ngang nhóm" };
  if (d > 0) return { tone: "warn" as const, text: `nhận nhiều hơn ${safeNumber(d)}` };
  return { tone: "default" as const, text: `nhận ít hơn ${safeNumber(-d)}` };
}

export default function CongBangPage() {
  const [token, setToken] = useState("");
  const [mine, setMine] = useState<Record<string, number> | null>(null);
  const [means, setMeans] = useState<Record<string, number>>({});
  const [coNhieuNguoi, setCoNhieuNguoi] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    setLoading(true);
    apiGet<Body>("/api/v1/cong-bang")
      .then((d) => {
        const soDu = d.so_du ?? {};
        const me = typeof d.nv_id === "string" ? d.nv_id : "";
        // §13.4: chỉ giữ lại dòng của chính người đang xem. Máy chủ có thể trả
        // số dư của cả nhóm (vai quản lý) — UI chủ động bỏ, không xếp hạng ai.
        setMine(me && soDu[me] ? soDu[me] : null);
        setCoNhieuNguoi(Object.keys(soDu).length > 1);
        setMeans(d.means ?? {});
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "đọc được sổ công bằng" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    setToken(getToken());
    load();
  }, [load]);

  if (!token) return <AuthGate />;

  const axes = Object.keys(mine ?? means);

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="Sổ nợ bốn chiều"
        title="Công bằng"
        meta="Bạn thấy số dư của chính mình so với trung bình nhóm. Quán không xếp hạng tên người."
      />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang đọc sổ nợ…</Loading> : null}

      {!loading && !error && axes.length === 0 ? (
        <Empty>Chưa có phân công nào để tính nợ. Khi lịch tuần công bố, số dư sẽ hiện ở đây.</Empty>
      ) : null}

      {!loading && !error && axes.length > 0 ? (
        <OpsCard
          eyebrow="Số dư của bạn"
          title={mine ? "Bạn so với trung bình nhóm" : "Trung bình nhóm"}
        >
          {!mine ? (
            <p className="nq-muted">
              Tài khoản này chưa gắn với hồ sơ nhân viên nào, nên chỉ xem được mức trung bình nhóm.
            </p>
          ) : null}
          <ul className="nq-fair-grid">
            {axes.map((a) => {
              const mean = typeof means[a] === "number" ? means[a] : 0;
              const own = mine && typeof mine[a] === "number" ? mine[a] : null;
              const gap = own == null ? null : lech(own, mean);
              return (
                <li key={a} className="nq-fair-row">
                  <span className="nq-fair-axis">{axisLabel(a)}</span>
                  <span className="nq-fair-nums">
                    {own == null ? "—" : `bạn ${safeNumber(own)}`} · TB nhóm {safeNumber(mean)}
                  </span>
                  {gap ? <StatusChip tone={gap.tone}>{gap.text}</StatusChip> : <span />}
                </li>
              );
            })}
          </ul>
          <p className="nq-fair-note">
            Số dương nghĩa là bạn đang gánh nhiều hơn trung bình ở trục đó — lần xếp lịch sau hệ thống ưu
            tiên bù cho bạn.
          </p>
        </OpsCard>
      ) : null}

      {coNhieuNguoi ? (
        <Notice>
          Hồ sơ §13.4 không cho phép xếp hạng tên nhân viên, nên trang này không liệt kê số dư của từng
          người. Cần cân lại ca thì làm trên Lịch tuần.
        </Notice>
      ) : null}
    </div>
  );
}
