"use client";

/**
 * NowBrief — "bây giờ quán thế nào", đọc thẳng từ hệ thống.
 *
 * Vì sao có component này: War Room trước đây chỉ có 5 thẻ kịch bản cứng. Người
 * dùng phải tự đoán xem hôm nay có gì đáng lo rồi mới chọn kịch bản — tức là
 * quyết định trên nền tình hình mà trang không hề nói. Panel này vá đúng chỗ
 * đó, và nó KHÔNG bịa: mọi câu chữ đều lấy từ `GET /quanverse/brief/living_map`
 * (lớp tất định của ADR-021), tức là cùng nguồn với panel Trợ lý Quánverse.
 *
 * Ở chế độ replay (mặc định) endpoint trả lời tất định, không gọi mạng LLM.
 */

import { useCallback, useEffect, useState } from "react";

import { viError } from "../../../lib/present";
import { Icon } from "../../icons";
import { quanverseBrief, type QuanverseBrief } from "../experience-api";

const COPY = { read: { doing: "đọc được tình hình hiện tại của quán" } } as const;

const TONE_CLASS: Record<string, string> = {
  ok: "nq-now-metric--ok",
  warn: "nq-now-metric--warn",
  danger: "nq-now-metric--danger",
  default: "",
};

function fmt(value: number | null, unit: string): string {
  // `null` = CHƯA CÓ DỮ LIỆU → "—", không bao giờ in "0".
  if (value === null) return "—";
  const text = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return unit ? `${text} ${unit}` : text;
}

export default function NowBrief() {
  const [brief, setBrief] = useState<QuanverseBrief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [rev, setRev] = useState(0);

  const load = useCallback(async () => {
    setError(null);
    try {
      setBrief(await quanverseBrief("living_map"));
    } catch (e) {
      setError(viError(e, COPY.read));
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load, rev]);

  if (error) {
    return (
      <div className="nq-alert nq-alert--error" role="alert">
        {error}
        <button type="button" className="nq-linkbtn" onClick={() => setRev((r) => r + 1)}>
          <Icon name="refresh" size={14} />
          Thử lại
        </button>
      </div>
    );
  }

  if (!brief) {
    return <p className="nq-now__loading" aria-busy="true">Đang đọc tình hình quán…</p>;
  }

  return (
    <div className="nq-now" data-testid="war-now">
      <p className="nq-now__headline" data-testid="war-now-headline">
        {brief.headline}
      </p>

      {brief.metrics.length ? (
        <ul className="nq-now__metrics" data-testid="war-now-metrics">
          {brief.metrics.map((m) => (
            <li key={m.key} className={`nq-now-metric ${TONE_CLASS[m.tone] ?? ""}`.trim()} data-metric={m.key}>
              <span className="nq-now-metric__value">{fmt(m.value, m.unit)}</span>
              <span className="nq-now-metric__label">{m.label}</span>
            </li>
          ))}
        </ul>
      ) : null}

      <div className="nq-now__cols">
        <div className="nq-now__col">
          <p className="nq-now__coltitle">Điểm cần chú ý</p>
          {brief.risks.length ? (
            <ul className="nq-now__list nq-now__list--risk" data-testid="war-now-risks">
              {brief.risks.map((r, i) => (
                <li key={i}>{r}</li>
              ))}
            </ul>
          ) : (
            <p className="nq-now__ok" data-testid="war-now-no-risk">
              Chưa thấy điểm bất thường nào.
            </p>
          )}
        </div>

        <div className="nq-now__col">
          {/* Gợi ý kịch bản nên thử: dẫn xuất từ RỦI RO THẬT vừa đọc, không
              phải danh sách cứng. Đây là chỗ nối War Room với tình hình. */}
          <p className="nq-now__coltitle">Nên mô phỏng gì trước</p>
          {suggestedScenarios(brief).length ? (
            <ul className="nq-now__list" data-testid="war-now-suggest">
              {suggestedScenarios(brief).map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ul>
          ) : (
            <p className="nq-now__ok">
              Tình hình đang bình thường — chọn kịch bản bên dưới nếu muốn thử trước.
            </p>
          )}
        </div>
      </div>

      {brief.grounded_refs.length ? (
        <p className="nq-now__refs">{`Dựa trên ${brief.grounded_refs.length} bản ghi của hệ thống`}</p>
      ) : (
        <p className="nq-now__refs nq-now__refs--none">
          Chưa có bản ghi nào để dẫn chứng — số liệu có thể đang trống.
        </p>
      )}
    </div>
  );
}

/**
 * Gợi ý kịch bản từ RỦI RO THẬT — không phải danh sách cứng.
 *
 * Ghép từ khoá trong `risks` (do tầng tất định sinh) với đúng tên kịch bản mà
 * `CRISIS_PRESETS` cung cấp. Không có rủi ro thì không gợi ý gì — im lặng đúng
 * hơn là gợi ý bừa.
 */
function suggestedScenarios(brief: QuanverseBrief): string[] {
  const text = [...brief.risks, ...brief.facts, brief.headline].join(" ").toLowerCase();
  const out: string[] = [];
  if (/quá tải|vượt ngưỡng|cao điểm|đông/.test(text)) out.push("Giờ cao điểm — xem có cần thêm người không.");
  if (/mưa/.test(text)) out.push("Mưa lớn — xem lượt khách giảm thì xếp ca thế nào.");
  if (/khách đoàn|đoàn|12 người|nhóm/.test(text)) out.push("Khách đoàn — thử trước cách gom bàn và xếp đón.");
  if (/thiếu|vắng|bù ca|nhân sự/.test(text)) out.push("Thiếu nhân sự — thử phương án bù ca.");
  if (/hỏng|máy|thiết bị/.test(text)) out.push("Thiết bị hỏng — xem năng lực pha chế còn bao nhiêu.");
  return out;
}
