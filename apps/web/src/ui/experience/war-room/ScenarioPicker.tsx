"use client";

/** Chọn kịch bản War Room — keyboard-selectable, có nhãn rõ ràng. */

import type { WarRoomScenarioInput } from "./war-room-model";
import { CRISIS_PRESETS } from "./war-room-model";

interface Props {
  selected: WarRoomScenarioInput[];
  onToggle: (scenario: WarRoomScenarioInput) => void;
  disabled?: boolean;
}

export default function ScenarioPicker({ selected, onToggle, disabled }: Props) {
  const selectedIds = new Set(selected.map((s) => s.scenario_id));

  return (
    <div className="nq-war-picker" role="group" aria-label="Chọn kịch bản War Room">
      <p className="nq-war-picker__hint">Chọn ít nhất 2 kịch bản để so sánh với baseline.</p>
      <div className="nq-war-picker__grid">
        {CRISIS_PRESETS.map((preset) => {
          const active = selectedIds.has(preset.scenario.scenario_id);
          return (
            <button
              key={preset.id}
              type="button"
              className={`nq-war-picker__card${active ? " is-active" : ""}`}
              aria-pressed={active}
              disabled={disabled}
              onClick={() => onToggle(preset.scenario)}
            >
              <span className="nq-war-picker__title">{preset.title}</span>
              <span className="nq-war-picker__desc">{preset.description}</span>
              <span className="nq-war-picker__chip">Mô phỏng</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}