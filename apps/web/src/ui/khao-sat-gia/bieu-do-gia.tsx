"use client";

/**
 * Biểu đồ giá cho `/khao-sat-gia` (plan `260913-1455` mục 6.1–6.2).
 *
 * Hai ràng buộc thiết kế chép thẳng từ plan, không phải sở thích:
 *  - Mục 6.2: KHÔNG dùng màu đỏ/xanh nhị phân "rẻ = tốt / đắt = xấu". Giá cao hơn
 *    AMBI vẫn có thể hợp lý nếu có yếu tố bù đắp → dùng thang liên tục (gradient).
 *  - Mục 6.2: `sample_size` phải hiện cạnh MỌI con số thống kê, và Sweet Spot
 *    không bao giờ là một số đơn lẻ — luôn là khoảng `low_display`–`high_display`.
 */

import { motion, useReducedMotion } from "framer-motion";
import { danhMucLabel, giaVnd } from "../../lib/present";

export type PhanVi = {
  p25: number;
  p50: number;
  p75: number;
  sample_size: number;
  insufficient_data: boolean;
};

export type HangPhanVi = { ten: string; stats: PhanVi; laCore?: boolean };

function chartMotion(reduced: boolean) {
  return reduced
    ? {}
    : {
        initial: { opacity: 0, y: 8 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.48, ease: [0.22, 1, 0.36, 1] as [number, number, number, number] },
      };
}

/**
 * Cột phổ giá P25–P75 của core và từng nhóm thay thế, trên MỘT thang chung.
 *
 * Vạch giữa là P50. Thanh là khoảng tứ phân vị, không phải "độ lớn" — đọc như
 * cột 0→giá sẽ khiến chủ quán tưởng nhóm thay thế nào dài hơn là nhóm đó tốt hơn.
 */
export function PhanViBars({ rows }: { rows: HangPhanVi[] }) {
  const reduced = useReducedMotion() ?? false;
  const duLieu = rows.filter((r) => r.stats && !r.stats.insufficient_data);

  if (duLieu.length === 0) {
    return (
      <div className="nq-dash-chart">
        <h3 className="nq-dash-chart-title">Món chính so với món thay thế</h3>
        <p className="nq-dash-chart-empty">
          Chưa nhóm nào đủ mẫu tối thiểu để vẽ phổ giá. Con số chỉ đáng tin khi có từ 5 mức giá trở lên.
        </p>
      </div>
    );
  }

  const caoNhat = Math.max(...duLieu.map((r) => r.stats.p75), 1);
  const thapNhat = Math.min(...duLieu.map((r) => r.stats.p25), caoNhat);
  const span = Math.max(caoNhat - thapNhat, 1);
  /** Đổi giá thành % trên thang [thapNhat, caoNhat] — mọi hàng dùng chung một thước. */
  const pct = (v: number) => Math.min(100, Math.max(0, ((v - thapNhat) / span) * 100));

  return (
    <motion.div className="nq-dash-chart nq-dash-chart--interactive" {...chartMotion(reduced)}>
      <h3 className="nq-dash-chart-title">Món chính so với món thay thế</h3>
      <p className="nq-dash-chart-hint">
        Thanh là khoảng giá P25–P75, vạch đậm là mức giữa P50. Tính trên giá gốc — giá khuyến mãi
        không được gộp vào.
      </p>
      <ul className="nq-dash-bars" role="list">
        {duLieu.map((row, i) => {
          const { p25, p50, p75, sample_size } = row.stats;
          const trai = pct(p25);
          const rong = Math.max(pct(p75) - trai, 1.5);
          return (
            <motion.li
              key={`${row.ten}-${i}`}
              className="nq-dash-bar-row"
              initial={reduced ? {} : { opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.05, duration: 0.4 }}
              title={`${danhMucLabel(row.ten)}: P25 ${giaVnd(p25)} · P50 ${giaVnd(p50)} · P75 ${giaVnd(p75)} · ${sample_size} mẫu`}
            >
              <span className="nq-dash-bar-label">
                {danhMucLabel(row.ten)}
                {row.laCore ? <span className="nq-dash-bar-unit">món chính</span> : null}
              </span>
              <div className="nq-dash-bar-track" style={{ position: "relative", overflow: "visible" }}>
                <span
                  style={{
                    position: "absolute",
                    left: `${trai}%`,
                    width: `${rong}%`,
                    top: 0,
                    bottom: 0,
                    borderRadius: "var(--nq-radius-pill)",
                    background: row.laCore
                      ? "linear-gradient(90deg, color-mix(in srgb, var(--nq-copper) 55%, transparent), var(--nq-copper))"
                      : "linear-gradient(90deg, color-mix(in srgb, var(--nq-ok) 45%, transparent), color-mix(in srgb, var(--nq-ok) 80%, transparent))",
                  }}
                />
                <span
                  aria-hidden="true"
                  style={{
                    position: "absolute",
                    left: `${pct(p50)}%`,
                    top: "-3px",
                    bottom: "-3px",
                    width: "2px",
                    background: "var(--nq-ink)",
                    transform: "translateX(-1px)",
                  }}
                />
              </div>
              <span className="nq-dash-bar-val">
                {giaVnd(p50)} <span className="nq-dash-bar-unit">{sample_size} mẫu</span>
              </span>
            </motion.li>
          );
        })}
      </ul>
      {rows.some((r) => r.stats?.insufficient_data) ? (
        <p className="nq-dash-chart-empty" style={{ marginTop: "var(--nq-s3)" }}>
          Một số nhóm bị ẩn vì chưa đủ mẫu tối thiểu — không suy ra từ dữ liệu mỏng.
        </p>
      ) : null}
    </motion.div>
  );
}

export type GaugeInput = {
  ambi: number;
  sweetLow: number;
  sweetHigh: number;
  minViablePrice?: number | null;
  /** Giá quán đang bán — UI nhập tại chỗ, KHÔNG gửi lên máy chủ. */
  giaQuan?: number | null;
  sampleSize?: number;
};

/**
 * Đồng hồ đo vị trí giá quán so với AMBI và Sweet Spot (plan mục 6.1).
 *
 * Thang là gradient liên tục: không có vùng nào bị tô đỏ "sai". Sweet Spot luôn
 * vẽ thành KHOẢNG (mục 6.2) và `min_viable_price` — nếu chủ quán có khai giá vốn —
 * hiện thành vạch riêng để tự đối chiếu.
 */
export function GiaGauge({ ambi, sweetLow, sweetHigh, minViablePrice, giaQuan, sampleSize }: GaugeInput) {
  const reduced = useReducedMotion() ?? false;
  const candidates = [ambi, sweetLow, sweetHigh, minViablePrice ?? NaN, giaQuan ?? NaN].filter(
    (v) => Number.isFinite(v) && v > 0,
  );
  if (candidates.length === 0) return null;

  const nho = Math.min(...candidates);
  const lon = Math.max(...candidates);
  const bien = Math.max((lon - nho) * 0.35, lon * 0.08, 1000);
  const lo = Math.max(0, nho - bien);
  const hi = lon + bien;
  const span = Math.max(hi - lo, 1);
  const pct = (v: number) => Math.min(100, Math.max(0, ((v - lo) / span) * 100));

  const markers: Array<{ giaTri: number; nhan: string; mau: string; net?: boolean }> = [
    { giaTri: ambi, nhan: `AMBI ${giaVnd(ambi)}`, mau: "var(--nq-copper)" },
  ];
  if (minViablePrice != null && Number.isFinite(minViablePrice)) {
    markers.push({ giaTri: minViablePrice, nhan: `Ngưỡng có lời tối thiểu ${giaVnd(minViablePrice)}`, mau: "var(--nq-warn)", net: true });
  }
  if (giaQuan != null && Number.isFinite(giaQuan) && giaQuan > 0) {
    markers.push({ giaTri: giaQuan, nhan: `Giá quán bạn ${giaVnd(giaQuan)}`, mau: "var(--nq-ink)", net: true });
  }

  return (
    <motion.div className="nq-dash-chart" {...chartMotion(reduced)}>
      <h3 className="nq-dash-chart-title">Giá quán bạn đứng đâu so với khu vực</h3>
      <p className="nq-dash-chart-hint">
        Vùng đồng là Sweet Spot {giaVnd(sweetLow)}–{giaVnd(sweetHigh)}
        {typeof sampleSize === "number" ? ` · ${sampleSize} mẫu` : ""}. Đây là khoảng tham chiếu,
        không phải một mức giá đúng duy nhất.
      </p>

      <div style={{ position: "relative", paddingTop: "2.6rem", paddingBottom: "1.6rem" }}>
        {/* Vạch đánh dấu đặt TRƯỚC để dải Sweet Spot đè lên chân vạch, chữ vẫn đọc được. */}
        {markers.map((m) => (
          <div
            key={m.nhan}
            style={{ position: "absolute", left: `${pct(m.giaTri)}%`, top: 0, bottom: 0, transform: "translateX(-1px)" }}
          >
            <span
              aria-hidden="true"
              style={{
                display: "block",
                width: "2px",
                height: "100%",
                background: m.mau,
                borderStyle: m.net ? "dashed" : undefined,
              }}
            />
            <span
              style={{
                position: "absolute",
                top: 0,
                left: "4px",
                whiteSpace: "nowrap",
                fontFamily: "var(--nq-font-mono)",
                fontSize: "0.68rem",
                color: m.mau,
              }}
            >
              {m.nhan}
            </span>
          </div>
        ))}

        <div
          role="img"
          aria-label={`Sweet Spot từ ${giaVnd(sweetLow)} đến ${giaVnd(sweetHigh)}, AMBI ${giaVnd(ambi)}`}
          style={{
            position: "relative",
            height: "0.9rem",
            borderRadius: "var(--nq-radius-pill)",
            background:
              "linear-gradient(90deg, color-mix(in srgb, var(--nq-ok) 70%, transparent), var(--nq-copper) 55%, color-mix(in srgb, var(--nq-warn) 80%, transparent))",
            overflow: "visible",
          }}
        >
          <span
            style={{
              position: "absolute",
              left: `${pct(sweetLow)}%`,
              width: `${Math.max(pct(sweetHigh) - pct(sweetLow), 1)}%`,
              top: "-4px",
              bottom: "-4px",
              border: "2px solid var(--nq-ink)",
              borderRadius: "var(--nq-radius-pill)",
              background: "color-mix(in srgb, var(--nq-bg-elevated) 35%, transparent)",
            }}
          />
        </div>

        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            display: "flex",
            justifyContent: "space-between",
            fontFamily: "var(--nq-font-mono)",
            fontSize: "0.66rem",
            color: "var(--nq-ink-muted)",
          }}
        >
          <span>{giaVnd(lo)}</span>
          <span>{giaVnd(hi)}</span>
        </div>
      </div>

      {giaQuan != null && Number.isFinite(giaQuan) && giaQuan > 0 ? (
        <p className="nq-dash-chart-empty">
          {giaQuan < sweetLow
            ? "Giá quán bạn đang thấp hơn vùng Sweet Spot của khu vực."
            : giaQuan > sweetHigh
              ? "Giá quán bạn đang cao hơn vùng Sweet Spot — vẫn có thể hợp lý nếu không gian, khẩu phần hoặc thương hiệu bù lại."
              : "Giá quán bạn đang nằm trong vùng Sweet Spot của khu vực."}
        </p>
      ) : null}
    </motion.div>
  );
}
