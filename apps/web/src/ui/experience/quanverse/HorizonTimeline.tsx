"use client";

/**
 * HorizonTimeline — 15 phút tới, dạng trục thời gian.
 *
 * Bản trước là danh sách chữ: không có mốc giờ, không biết việc nào gần hơn.
 * Bản này vẽ một trục dọc, chấm mốc đặt theo thứ tự thời gian thật và giờ
 * `starts_at` hiển thị cạnh mỗi mục — nên "còn 12 phút" là thứ nhìn ra ngay.
 */

import { Icon, type IconName } from "../../icons";
import { ExpEmpty } from "../exp-kit";
import { horizonKindLabel } from "../exp-present";

interface HorizonItem {
  item_id: string;
  kind: string;
  title: string;
  starts_at: string;
  source: string;
}

const KIND_ICON: Record<string, IconName> = {
  event: "calendar",
  signal: "bell",
  handover: "doi-ca",
  mode_proposal: "zap",
};

/** Giờ:phút từ mốc ISO; trả "" khi mốc không đọc được (không in "Invalid Date"). */
function clock(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${hh}:${mm}`;
}

/** Số phút còn lại tới mốc — âm nghĩa là đã qua. */
function minutesUntil(iso: string): number | null {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return Math.round((d.getTime() - Date.now()) / 60_000);
}

function relative(min: number | null): string {
  if (min === null) return "Không rõ thời điểm";
  if (min < 0) return "Đã qua";
  if (min === 0) return "Ngay bây giờ";
  if (min < 60) return `Còn ${min} phút`;
  return `Còn ${Math.floor(min / 60)} giờ ${min % 60} phút`;
}

export default function HorizonTimeline({ items }: { items: HorizonItem[] }) {
  if (!items.length) {
    return (
      <section className="nq-horizon" aria-label="Tầm nhìn 15 phút tới">
        <div className="nq-exp-section__head">
          <Icon name="clock" size={16} />
          <h3 className="nq-exp-section__title">15 phút tới</h3>
        </div>
        <ExpEmpty
          icon="clock"
          title="Chưa có gì trong 15 phút tới"
          hint="Khi có khách đoàn, chế độ chờ duyệt hay ca bàn giao, mốc sẽ hiện ở đây."
        />
      </section>
    );
  }

  // Sắp theo thời gian thật, để trục luôn đọc từ trên xuống như thời gian trôi.
  const sorted = [...items].sort(
    (a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime(),
  );

  return (
    <section className="nq-horizon" aria-label="Tầm nhìn 15 phút tới">
      <div className="nq-exp-section__head">
        <Icon name="clock" size={16} />
        <h3 className="nq-exp-section__title">15 phút tới</h3>
        <span className="nq-exp-section__spacer" />
        <span className="nq-horizon__count">{sorted.length} mốc</span>
      </div>
      <ol className="nq-horizon__list">
        {sorted.map((h, i) => {
          const min = minutesUntil(h.starts_at);
          const urgent = min !== null && min >= 0 && min <= 15;
          return (
            <li
              key={h.item_id}
              className={`nq-horizon__item nq-horizon__item--${h.kind}${urgent ? " is-urgent" : ""}`}
              style={{ ["--nq-hz-i" as string]: i }}
            >
              <span className="nq-horizon__time">{clock(h.starts_at) || "—"}</span>
              <span className="nq-horizon__rail" aria-hidden="true">
                <span className="nq-horizon__dot">
                  <Icon name={KIND_ICON[h.kind] ?? "clock"} size={12} />
                </span>
              </span>
              <span className="nq-horizon__text">
                <span className="nq-horizon__title">{h.title}</span>
                <span className="nq-horizon__meta">
                  {horizonKindLabel(h.kind)} · {relative(min)}
                </span>
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}