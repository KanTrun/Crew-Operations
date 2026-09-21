"use client";

/** Memory timeline — danh sách thật, không chỉ label nổi. */

import { consentStatusLabel, memoryStatusLabel, visibilityLabel } from "../exp-present";

interface Memory {
  memory_id: string;
  content: string;
  status: string;
  consent_status: string;
  visibility: string;
  retention_until?: string | null;
}

export default function MemoryTimeline({ memories }: { memories: Memory[] }) {
  if (!memories.length) {
    return <p className="nq-timeline__empty">Chưa có ký ức cho khu vực này.</p>;
  }
  return (
    <ul className="nq-timeline" aria-label="Timeline ký ức">
      {memories.map((m) => (
        <li key={m.memory_id} className={`nq-timeline__item nq-timeline__item--${m.status}`}>
          <div className="nq-timeline__head">
            <span className="nq-timeline__status">{memoryStatusLabel(m.status)}</span>
            <span className="nq-timeline__consent">Đồng thuận: {consentStatusLabel(m.consent_status)}</span>
          </div>
          <p className="nq-timeline__content">{m.content}</p>
          <p className="nq-timeline__meta">
            {visibilityLabel(m.visibility)}
            {m.retention_until ? ` · hết hạn ${m.retention_until}` : ""}
          </p>
        </li>
      ))}
    </ul>
  );
}