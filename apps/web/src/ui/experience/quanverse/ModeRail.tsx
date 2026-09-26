"use client";

/**
 * ModeRail — vòng đời đầy đủ của chế độ quán: đề xuất → duyệt → tắt.
 *
 * Bản trước chỉ có nút "Kích hoạt" và bỏ qua hoàn toàn endpoint `propose`; một
 * chế độ bật rồi thì ở lại mãi, nên quán kẹt ở chế độ cũ sau khi tình huống đã
 * qua. Bản này dựng đúng ba trạng thái:
 *
 *   đang tắt  → [Đề xuất]       ghi đề xuất, chờ người có quyền quyết
 *   chờ duyệt → [Duyệt] [Bỏ]    duyệt thì bật, bỏ thì rút đề xuất
 *   đang bật  → [Tắt]           đưa quán về trạng thái thường
 *
 * Vai trò không có quyền thấy đúng sự thật: "Chỉ quản lý đổi được", thay vì nút
 * bấm được rồi máy chủ trả 403.
 */

import { useState } from "react";
import { Icon, type IconName } from "../../icons";
import { modeLabel, proposalStatusLabel } from "../exp-present";

export interface ModeItem {
  mode: string;
  active: boolean;
  proposal_status?: string | null;
  proposed_by?: string | null;
  /** Câu hệ quả do máy chủ trả — cùng nguồn với `mode_affects`. */
  effect?: string;
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
  onAction: (mode: string, action: ModeAction) => Promise<void>;
  busy?: boolean;
  /** Vai trò hiện tại có được duyệt/kích hoạt chế độ không (máy chủ quyết định). */
  canActivate?: boolean;
}

export type ModeAction = "propose" | "confirm" | "deactivate";

/** Chế độ đang có đề xuất nhưng chưa bật. */
function isWaiting(m: ModeItem): boolean {
  return Boolean(m.proposal_status && m.proposal_status !== "confirmed");
}

export default function ModeRail({ modes, onAction, busy, canActivate = true }: Props) {
  const [pending, setPending] = useState<string | null>(null);

  const active = modes.filter((m) => m.active);
  const waiting = modes.filter((m) => !m.active && isWaiting(m));
  const off = modes.filter((m) => !m.active && !isWaiting(m));

  async function run(mode: string, action: ModeAction) {
    setPending(`${mode}:${action}`);
    try {
      await onAction(mode, action);
    } finally {
      setPending(null);
    }
  }

  function stateLabel(m: ModeItem): string {
    if (m.active) return "Đang bật";
    if (isWaiting(m)) return `Chờ duyệt · ${proposalStatusLabel(m.proposal_status)}`;
    return "Đang tắt";
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

      {/* Chờ duyệt xếp lên trên: đây là việc cần người quyết định. */}
      {waiting.length > 0 ? (
        <p className="nq-moderail__sectionlabel">Chờ quyết định · {waiting.length}</p>
      ) : null}

      <ul className="nq-moderail__list">
        {[...waiting, ...active, ...off].map((m) => {
          const icon = MODE_ICON[m.mode] ?? "zap";
          const waitingNow = !m.active && isWaiting(m);
          return (
            <li
              key={m.mode}
              className={
                "nq-moderail__item" +
                (m.active ? " is-active" : "") +
                (waitingNow ? " is-waiting" : "")
              }
              data-testid={`mode-item-${m.mode}`}
            >
              <span className="nq-moderail__glyph" aria-hidden="true">
                <Icon name={icon} size={18} />
              </span>
              <span className="nq-moderail__text">
                <span className="nq-moderail__label">{modeLabel(m.mode)}</span>
                <span className="nq-moderail__effect">
                  {m.effect ?? MODE_EFFECT[m.mode] ?? "Thay đổi cách quán vận hành."}
                </span>
              </span>

              {/* Công tắc: trạng thái là hình dạng, không chỉ là chữ "Đang bật". */}
              <span
                className={`nq-switch${m.active ? " is-on" : ""}${waitingNow ? " is-waiting" : ""}`}
                role="img"
                aria-label={
                  m.active ? "Đang bật" : waitingNow ? "Đang chờ duyệt" : "Đang tắt"
                }
              >
                <span className="nq-switch__dot" />
              </span>
              <span className="nq-moderail__state">{stateLabel(m)}</span>

              <span className="nq-moderail__actions">
                {!canActivate ? (
                  <span className="nq-moderail__readonly">Chỉ quản lý đổi được</span>
                ) : m.active ? (
                  <button
                    type="button"
                    className="nq-btn-compact nq-modebtn"
                    data-testid={`mode-deactivate-${m.mode}`}
                    disabled={busy || pending !== null}
                    onClick={() => run(m.mode, "deactivate")}
                  >
                    <Icon name="pause" size={13} />
                    {pending === `${m.mode}:deactivate` ? "Đang tắt…" : "Tắt"}
                  </button>
                ) : waitingNow ? (
                  <>
                    <button
                      type="button"
                      className="nq-btn-compact nq-modebtn"
                      data-testid={`mode-confirm-${m.mode}`}
                      disabled={busy || pending !== null}
                      onClick={() => run(m.mode, "confirm")}
                    >
                      <Icon name="check" size={13} />
                      {pending === `${m.mode}:confirm` ? "Đang duyệt…" : "Duyệt"}
                    </button>
                    <button
                      type="button"
                      className="nq-linkbtn"
                      data-testid={`mode-drop-${m.mode}`}
                      disabled={busy || pending !== null}
                      onClick={() => run(m.mode, "deactivate")}
                    >
                      Bỏ đề xuất
                    </button>
                  </>
                ) : (
                  <button
                    type="button"
                    className="nq-btn-compact nq-modebtn"
                    data-testid={`mode-propose-${m.mode}`}
                    disabled={busy || pending !== null}
                    onClick={() => run(m.mode, "propose")}
                  >
                    <Icon name="plus" size={13} />
                    {pending === `${m.mode}:propose` ? "Đang gửi…" : "Đề xuất"}
                  </button>
                )}
              </span>
            </li>
          );
        })}
      </ul>

      {off.length > 0 && canActivate ? (
        <p className="nq-moderail__note">
          Kích hoạt một chế độ là thay đổi cách quán vận hành — thao tác được ghi lại kèm người duyệt.
        </p>
      ) : null}
    </section>
  );
}