"use client";

/**
 * ScenarioPicker — chọn kịch bản để mô phỏng. Đây là CÔNG CỤ CHỌN DUY NHẤT.
 *
 * Vì sao gộp về một: trước đây War Room có HAI chỗ chọn cùng 5 preset —
 * `ScenarioPicker` ở trên và `CrisisRoom` ở dưới — cả hai render đúng
 * `CRISIS_PRESETS`. Người dùng bấm một nơi, cuộn xuống thấy y hệt danh sách đó
 * lần nữa, và không hiểu hai chỗ khác nhau thế nào. Đó là nguồn của câu hỏi
 * "sao nó chỉ là bấm vô 2 mục".
 *
 * Mỗi thẻ nay trả lời được BA câu, không chỉ một câu mô tả:
 *   - **Điều gì xảy ra** — tình huống là gì.
 *   - **Số liệu giả định** — dịch `tham_so` (mã máy) ra chữ, để người dùng thấy
 *     mình đang giả định con số nào thay vì tin vào một hộp đen.
 *   - **Tác động tới đâu** — phần nào của quán sẽ bị ảnh hưởng.
 *
 * Không có gì bịa: mọi câu chữ lấy từ `CRISIS_PRESETS` (fixture khai tường minh)
 * và `affects` chỉ là bản đồ mã-loại-kịch-bản → tên vùng, không suy diễn số.
 */

import type { WarRoomScenarioInput } from "./war-room-model";
import { CRISIS_PRESETS } from "./war-room-model";

interface Props {
  selected: WarRoomScenarioInput[];
  onToggle: (scenario: WarRoomScenarioInput) => void;
  disabled?: boolean;
}

/** Dịch `tham_so` (mã máy) thành câu người đọc được. */
function paramLabels(scenario: WarRoomScenarioInput): string[] {
  const p = scenario.tham_so ?? {};
  const out: string[] = [];
  if (typeof p.ky_vong_giam_luot === "number") {
    out.push(`Lượt khách giảm ${Math.round((1 - p.ky_vong_giam_luot) * 100)}%`);
  }
  if (typeof p.ty_le_gia_tang === "number") {
    out.push(`Cầu tăng ${Math.round((p.ty_le_gia_tang - 1) * 100)}%`);
  }
  if (typeof p.khung_gio === "string") out.push(`Khung ${p.khung_gio}`);
  if (typeof p.so_them === "number") out.push(`Thêm ${p.so_them} người`);
  if (typeof p.thu === "string") out.push(`Thứ ${p.thu}`);
  if (typeof p.thiet_bi === "string") out.push(`Thiết bị ${p.thiet_bi}`);
  if (typeof p.thoi_gian_phuc_hoi_phut === "number") {
    out.push(`Gián đoạn ${p.thoi_gian_phuc_hoi_phut} phút`);
  }
  if (typeof p.so_khach === "number") out.push(`${p.so_khach} khách`);
  return out;
}

/** Kịch bản tác động tới phần nào của quán (bản đồ mã → chữ, không suy diễn). */
const AFFECTS: Record<string, string> = {
  heavy_rain: "Chỗ ngồi · lượng khách vào · món nóng",
  demand_surge: "Quầy pha chế · thu ngân · nhân sự",
  add_staff_to_shift: "Ca làm việc · phân công · công bằng",
  equipment_outage: "Năng lực pha chế · thời gian chờ",
  large_group_arrival: "Bàn lớn · kho · thứ tự phục vụ",
};

export default function ScenarioPicker({ selected, onToggle, disabled }: Props) {
  const selectedIds = new Set(selected.map((s) => s.scenario_id));

  return (
    <section className="nq-war-picker" aria-label="Chọn kịch bản War Room">
      <div className="nq-exp-section__head">
        <span className="nq-war-picker__glyph" aria-hidden="true">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8" />
          </svg>
        </span>
        <h2 className="nq-exp-section__title">Chọn tình huống để mô phỏng</h2>
        <span className="nq-exp-section__spacer" />
        <span className="nq-war-picker__count" data-testid="war-picker-count">
          Đã chọn {selected.length}/{CRISIS_PRESETS.length}
        </span>
      </div>
      <p className="nq-war-picker__hint">
        Chọn <strong>ít nhất 2</strong> để so sánh với nhau. Mỗi thẻ ghi rõ con số
        giả định và phần nào của quán bị tác động — mô phỏng <strong>không</strong>{" "}
        đổi lịch thật.
      </p>
      <div className="nq-war-picker__grid">
        {CRISIS_PRESETS.map((preset) => {
          const active = selectedIds.has(preset.scenario.scenario_id);
          const params = paramLabels(preset.scenario);
          const affects = AFFECTS[preset.scenario.loai];
          return (
            <button
              key={preset.id}
              type="button"
              className={`nq-war-picker__card${active ? " is-active" : ""}`}
              aria-pressed={active}
              disabled={disabled}
              data-scenario={preset.scenario.scenario_id}
              onClick={() => onToggle(preset.scenario)}
            >
              <span className="nq-war-picker__head">
                <span className="nq-war-picker__title">{preset.title}</span>
                <span className="nq-war-picker__check" aria-hidden="true">
                  {active ? "✓" : "+"}
                </span>
              </span>
              <span className="nq-war-picker__desc">{preset.description}</span>

              {params.length ? (
                <span className="nq-war-picker__params">
                  {params.map((t, i) => (
                    <span key={i} className="nq-war-picker__param">
                      {t}
                    </span>
                  ))}
                </span>
              ) : null}

              {/* Tác động tới vùng nào — trả lời "mô phỏng cái này để làm gì". */}
              {affects ? (
                <span className="nq-war-picker__affects">Tác động: {affects}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </section>
  );
}