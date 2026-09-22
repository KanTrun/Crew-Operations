"use client";

/**
 * ModeRail — chế độ quán: đang bật, đang chờ duyệt, hay tắt.
 *
 * Bản trước in mọi chế độ bằng một danh sách như nhau, nút "Kích hoạt" cùng cỡ
 * với nút chính của trang (min-height 48px) nên bốn dòng thành một bức tường
 * pill, và bấm xong không có phản hồi nào ngoài viền đổi màu. Bản này: một
 * công tắc thật (switch) cho trạng thái, hàng đợi duyệt tách khỏi hàng đang
 * bật, nút nhỏ đúng cỡ hàng, và một dòng trấn an trong lúc chờ máy chủ.
 *
 * `busy` trước đây được khai báo mà không ai truyền — nay nó điều khiển khoá
 * nút và hiện trạng thái "Đang gửi…", nên người dùng không bấm hai lần.
 */

import { useState } from "react";
import { Icon, type IconName } from "../../icons";
import { modeLabel, proposalStatusLabel } from "../exp-present";

interface ModeItem {
  mode: string;
  active: boolean;
  proposal_status?: string | null;
}

/** Mỗi chế độ có một biểu tượng riêng — mắt nhận ra trước khi đọc chữ. */
const MODE_ICON: Record<string, IconName> = {
  troi_mua: "cloud-rain",
  gio_cao_diem: "zap",
  khach_doan: "users",
  thieu_nhan_su: "users",
  quan_yen_tinh: "volume-off",
  dem_nhac: "music",
};

/** Vì sao bật chế độ này — nói cho người bấm biết hệ quả, không chỉ tên. */
const MODE_EFFECT: Record<string, string> = {
  troi_mua: "Dồn chỗ ngồi trong nhà, ưu tiên món nóng.",
  gio_cao_diem: "Bật gợi ý san ca và cảnh báo quầy quá tải.",
  khach_doan: "Gom bàn, chuẩn bị đón đoàn và xếp trước.",
  thieu_nhan_su: "Mở luồng cứu ca và xếp hạng người bù.",
  quan_yen_tinh: "Giảm nhạc, hạn chế thông báo không khẩn.",
  dem_nhac: "Bật lịch nhạc, giữ khu vực sân khấu.",
};

interface Props {
  modes: ModeItem[];
  onConfirm: (mode: string) => Promise<void>;
  busy?: boolean;
}

export default function ModeRail({ modes, onConfirm, busy }: Props) {
  const [pending, setPending] = useState<string | null>(null);

  const active = modes.filter((m) => m.active);
  const inactive = modes.filter((m) => !m.active);

  async function confirm(mode: string) {
    setPending(mode);
    try {
      await onConfirm(mode);
    } finally {
      setPending(null);
    }
  }

  return (
    <section className="nq-moderail" aria-label="Chế độ quán">
      <div className="nq-exp-section__head">
        <Icon name="zap" size={16} />
        <h3 className="nq-exp-section__title">Chế độ quán</h3>
        <span className="nq-exp-section__spacer" />
        <span className="nq-moderail__count">
          {active.length}/{modes.length} đang bật
        </span>
      </div>

      <ul className="nq-moderail__list">
        {modes.map((m) => {
          const icon = MODE_ICON[m.mode] ?? "zap";
          const isPending = pending === m.mode;
          const waiting = !m.active && m.proposal_status && m.proposal_status !== "confirmed";
          return (
            <li key={m.mode} className={`nq-moderail__item${m.active ? " is-active" : ""}`}>
              <span className="nq-moderail__glyph" aria-hidden="true">
                <Icon name={icon} size={18} />
              </span>
              <span className="nq-moderail__text">
                <span className="nq-moderail__label">{modeLabel(m.mode)}</span>
                <span className="nq-moderail__effect">{MODE_EFFECT[m.mode] ?? "Thay đổi cách quán vận hành."}</span>
              </span>

              {/* Công tắc: trạng thái là hình dạng, không chỉ là chữ "Đang bật". */}
              <span
                className={`nq-switch${m.active ? " is-on" : ""}`}
                role="img"
                aria-label={m.active ? "Đang bật" : "Đang tắt"}
              >
                <span className="nq-switch__dot" />
              </span>
              <span className="nq-moderail__state">
                {m.active
                  ? "Đang bật"
                  : waiting
                    ? `Đang chờ duyệt · ${proposalStatusLabel(m.proposal_status)}`
                    : "Đang tắt"}
              </span>

              {!m.active ? (
                <button
                  type="button"
                  className="nq-btn-compact nq-modebtn"
                  data-testid={`mode-confirm-${m.mode}`}
                  disabled={busy || isPending}
                  onClick={() => confirm(m.mode)}
                >
                  {isPending ? "Đang gửi…" : "Kích hoạt"}
                </button>
              ) : null}
            </li>
          );
        })}
      </ul>
      {inactive.length > 0 ? (
        <p className="nq-moderail__note">
          Kích hoạt một chế độ là thay đổi cách quán vận hành — thao tác được ghi lại kèm người duyệt.
        </p>
      ) : null}
    </section>
  );
}