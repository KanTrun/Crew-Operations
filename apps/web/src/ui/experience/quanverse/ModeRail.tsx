"use client";

/** ModeRail — đề xuất chế độ quán; confirm manager. */

interface ModeItem {
  mode: string;
  active: boolean;
  proposal_status?: string | null;
}

interface Props {
  modes: ModeItem[];
  onConfirm: (mode: string) => Promise<void>;
  busy?: boolean;
}

const MODE_LABEL: Record<string, string> = {
  troi_mua: "Trời mưa",
  gio_cao_diem: "Giờ cao điểm",
  khach_doan: "Khách đoàn",
  thieu_nhan_su: "Thiếu nhân sự",
  quan_yen_tinh: "Quán yên tĩnh",
  dem_nhac: "Đêm nhạc",
};

export default function ModeRail({ modes, onConfirm, busy }: Props) {
  return (
    <section className="nq-moderail" aria-label="Chế độ quán">
      <h3>Chế độ quán</h3>
      <ul className="nq-moderail__list">
        {modes.map((m) => (
          <li key={m.mode} className={`nq-moderail__item${m.active ? " is-active" : ""}`}>
            <span className="nq-moderail__label">{MODE_LABEL[m.mode] ?? m.mode}</span>
            <span className="nq-moderail__state">
              {m.active ? "Đang bật" : m.proposal_status ? `Đề xuất ${m.proposal_status}` : "Tắt"}
            </span>
            {!m.active && (
              <button
                type="button"
                className="nq-btn nq-btn--primary"
                data-testid={`mode-confirm-${m.mode}`}
                disabled={busy}
                onClick={() => onConfirm(m.mode)}
              >
                Kích hoạt
              </button>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}