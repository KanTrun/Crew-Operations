"use client";

/** Memory timeline — danh sách thật, không chỉ label nổi. */

interface Memory {
  memory_id: string;
  content: string;
  status: string;
  consent_status: string;
  visibility: string;
  retention_until?: string | null;
}

function statusLabel(status: string): string {
  if (status === "draft") return "Chờ xác nhận";
  if (status === "confirmed") return "Đã xác nhận";
  if (status === "superseded") return "Thay thế";
  return "Đã xoá";
}

export default function MemoryTimeline({ memories }: { memories: Memory[] }) {
  if (!memories.length) {
    return <p className="nq-timeline__empty">Chưa có ký ức đã xác nhận.</p>;
  }
  return (
    <ul className="nq-timeline" aria-label="Timeline ký ức">
      {memories.map((m) => (
        <li key={m.memory_id} className={`nq-timeline__item nq-timeline__item--${m.status}`}>
          <div className="nq-timeline__head">
            <span className="nq-timeline__status">{statusLabel(m.status)}</span>
            <span className="nq-timeline__consent">Đồng thuận: {m.consent_status}</span>
          </div>
          <p className="nq-timeline__content">{m.content}</p>
          <p className="nq-timeline__meta">
            {m.memory_id} · {m.visibility}
            {m.retention_until ? ` · hết hạn ${m.retention_until}` : ""}
          </p>
        </li>
      ))}
    </ul>
  );
}