"use client";

/** Crisis Room — presets mô phỏng tình huống (fixture label rõ ràng). */

import type { WarRoomScenarioInput } from "./war-room-model";
import { CRISIS_PRESETS } from "./war-room-model";

interface Props {
  onRunPreset: (scenario: WarRoomScenarioInput) => void;
  busy: boolean;
}

export default function CrisisRoom({ onRunPreset, busy }: Props) {
  return (
    <section className="nq-crisis" aria-label="Crisis Room">
      <h2>Crisis Room</h2>
      <p className="nq-crisis__note">
        Preset tình huống dùng dữ liệu fixture — không cảm nhận thời tiết/IoT thật.
      </p>
      <ul className="nq-crisis__list">
        {CRISIS_PRESETS.map((preset) => (
          <li key={preset.id}>
            <button
              type="button"
              className="nq-crisis__item"
              disabled={busy}
              onClick={() => onRunPreset(preset.scenario)}
            >
              <span className="nq-crisis__title">{preset.title}</span>
              <span className="nq-crisis__desc">{preset.description}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}