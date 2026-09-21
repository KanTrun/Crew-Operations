"use client";

/** ModeRail — đề xuất chế độ quán; confirm manager. */

import { modeLabel, proposalStatusLabel } from "../exp-present";

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

export default function ModeRail({ modes, onConfirm, busy }: Props) {
  return (
    <section className="nq-moderail" aria-label="Chế độ quán">
      <h3>Chế độ quán</h3>
      <ul className="nq-moderail__list">
        {modes.map((m) => (
          <li key={m.mode} className={`nq-moderail__item${m.active ? " is-active" : ""}`}>
            <span className="nq-moderail__label">{modeLabel(m.mode)}</span>
            <span className="nq-moderail__state">
              {m.active ? "Đang bật" : m.proposal_status ? `Đề xuất: ${proposalStatusLabel(m.proposal_status)}` : "Tắt"}
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