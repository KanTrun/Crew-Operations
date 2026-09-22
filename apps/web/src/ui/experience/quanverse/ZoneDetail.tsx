"use client";

/**
 * ZoneDetail — bảng chi tiết khu vực đang chọn trên Living Map.
 *
 * Vì sao cần: `page.tsx` trước đây truyền `onSelectZone={() => undefined}`, nên
 * khu vực trông như nút bấm được mà bấm không có gì xảy ra — một lời hứa sai
 * trên UI. Bảng này trả lời câu hỏi người dùng thật sự hỏi khi bấm vào quầy:
 * "khu này đang chịu tải bao nhiêu, vì sao, và tôi nên làm gì".
 *
 * Không tự bịa số: mọi dòng đều lấy từ `ZoneUI` + sự kiện của khu vực đó. Khi
 * không có sự kiện, nói thẳng là không có — không độn dữ liệu cho đẹp.
 */

import { Icon } from "../../icons";
import { ExpEmpty } from "../exp-kit";
import { eventStatusLabel, eventTypeLabel } from "../exp-present";
import type { ZoneUI } from "./quanverse-model";

export interface ZoneEventUI {
  event_id: string;
  event_type: string;
  status: string;
  summary: string;
  zone_id?: string | null;
}

const KIND_HINT: Record<string, string> = {
  quay: "Khu vực chế biến và phục vụ — tải tăng khi khách gọi món dồn.",
  phong_khach: "Khu vực ngồi của khách — tải phản ánh mức lấp chỗ.",
  loi_vao: "Lối vào — tải phản ánh nhịp khách ra vào.",
};

/** Gợi ý hành động suy từ mức tải. Ngưỡng nói rõ, không phải "AI cảm nhận". */
function advice(zone: ZoneUI): string {
  const pct = Math.round(zone.load_signal * 100);
  if (!zone.active) return "Khu vực đang đóng — không nhận tải.";
  if (zone.load_signal >= 0.7) return `Tải ${pct}% — nên san người hoặc bật chế độ giờ cao điểm.`;
  if (zone.load_signal >= 0.4) return `Tải ${pct}% — theo dõi thêm, còn dư chỗ xử lý.`;
  return `Tải ${pct}% — nhẹ, chưa cần can thiệp.`;
}

interface Props {
  zone: ZoneUI;
  events: ZoneEventUI[];
  onClose?: () => void;
}

export default function ZoneDetail({ zone, events, onClose }: Props) {
  const related = events.filter((e) => e.zone_id === zone.zone_id);
  const tone = zone.load_signal >= 0.7 ? "high" : zone.load_signal >= 0.4 ? "mid" : "low";

  return (
    <section className="nq-zone-detail" aria-label={`Chi tiết khu vực ${zone.label}`}>
      <header className="nq-zone-detail__head">
        <Icon name="location" size={16} />
        <h3>{zone.label}</h3>
        <span className={`nq-loadchip nq-loadchip--${tone}`}>{Math.round(zone.load_signal * 100)}%</span>
        <span className="nq-exp-section__spacer" />
        {onClose ? (
          <button type="button" className="nq-zdetail__close" aria-label="Đóng chi tiết khu vực" onClick={onClose}>
            <Icon name="x-mark" size={16} />
          </button>
        ) : null}
      </header>

      <p className="nq-zone-detail__hint">{KIND_HINT[zone.kind] ?? "Khu vực vận hành của quán."}</p>
      <p className={`nq-zone-detail__advice nq-zone-detail__advice--${tone}`}>{advice(zone)}</p>

      <div className="nq-zone-detail__meter" aria-hidden="true">
        <span className={`nq-loadbar nq-loadbar--${tone} nq-loadbar--wide`}>
          <span className="nq-loadbar__fill" style={{ height: `${Math.round(zone.load_signal * 100)}%` }} />
        </span>
        <span className="nq-loadbar__axis">0%</span>
        <span className="nq-loadbar__axis">50%</span>
        <span className="nq-loadbar__axis">100%</span>
      </div>

      <h4 className="nq-zone-detail__subhead">Sự kiện tại khu vực</h4>
      {related.length === 0 ? (
        <ExpEmpty
          icon="info"
          title="Chưa ghi nhận sự kiện ở khu vực này"
          hint="Sự kiện xuất hiện khi có ca cứu, đề xuất chế độ hoặc tín hiệu gắn với khu vực."
        />
      ) : (
        <ul className="nq-zone-detail__events">
          {related.map((e) => (
            <li key={e.event_id} className="nq-zone-detail__event">
              <span className="nq-zone-detail__etype">{eventTypeLabel(e.event_type)}</span>
              <span className="nq-zone-detail__esum">{e.summary}</span>
              <span className="nq-zone-detail__estatus">{eventStatusLabel(e.status)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
