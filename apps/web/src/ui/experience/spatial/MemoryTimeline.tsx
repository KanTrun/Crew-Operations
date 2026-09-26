"use client";

/**
 * MemoryTimeline — danh sách ký ức đọc được, có thể xoá khi có quyền.
 *
 * Ký ức là dữ liệu cá nhân: người xem phải thấy được trạng thái đồng thuận,
 * phạm vi hiển thị và hạn lưu, và phải xoá được ngay tại chỗ. `onRemove` là
 * tuỳ chọn để chỗ gọi không phải tự dựng lại toàn bộ danh sách.
 */

import { Icon } from "../../icons";
import {
  consentStatusLabel,
  memoryStatusLabel,
  visibilityLabel,
} from "../exp-present";

interface Memory {
  memory_id: string;
  content: string;
  status: string;
  consent_status: string;
  visibility: string;
  retention_until?: string | null;
}

interface Props {
  memories: Memory[];
  onRemove?: (memoryId: string) => void;
  busyId?: string | null;
}

/** Ngày hết hạn → chuỗi đọc được; không in mốc ISO thô lên UI. */
function retentionText(value?: string | null): string | null {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `lưu tới ${dd}/${mm}/${d.getFullYear()}`;
}

export default function MemoryTimeline({ memories, onRemove, busyId }: Props) {
  if (!memories.length) {
    return <p className="nq-timeline__empty">Chưa có ký ức nào cho khu vực này.</p>;
  }
  return (
    <ul className="nq-timeline" aria-label="Timeline ký ức">
      {memories.map((m) => {
        const retention = retentionText(m.retention_until);
        return (
          <li key={m.memory_id} className={`nq-timeline__item nq-timeline__item--${m.status}`}>
            <div className="nq-timeline__head">
              <span className="nq-timeline__status">{memoryStatusLabel(m.status)}</span>
              <span className="nq-timeline__consent">
                Đồng thuận: {consentStatusLabel(m.consent_status)}
              </span>
              {onRemove ? (
                <button
                  type="button"
                  className="nq-timeline__remove"
                  data-testid={`mem-remove-${m.memory_id}`}
                  disabled={busyId === m.memory_id}
                  aria-label="Xoá ký ức này"
                  onClick={() => onRemove(m.memory_id)}
                >
                  <Icon name="trash" size={14} />
                </button>
              ) : null}
            </div>
            <p className="nq-timeline__content">{m.content}</p>
            <p className="nq-timeline__meta">
              {visibilityLabel(m.visibility)}
              {retention ? ` · ${retention}` : ""}
            </p>
          </li>
        );
      })}
    </ul>
  );
}