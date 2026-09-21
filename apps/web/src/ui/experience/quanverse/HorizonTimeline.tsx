"use client";

/** HorizonTimeline — 15 phút tới. */

import { horizonKindLabel } from "../exp-present";

interface HorizonItem {
  item_id: string;
  kind: string;
  title: string;
  starts_at: string;
  source: string;
}

export default function HorizonTimeline({ items }: { items: HorizonItem[] }) {
  if (!items.length) {
    return <p className="nq-horizon__empty">Chưa có sự kiện trong 15 phút tới.</p>;
  }
  return (
    <section className="nq-horizon" aria-label="Tầm nhìn 15 phút tới">
      <h3>15 phút tới</h3>
      <ul className="nq-horizon__list">
        {items.map((h) => (
          <li key={h.item_id} className={`nq-horizon__item nq-horizon__item--${h.kind}`}>
            <span className="nq-horizon__kind">{horizonKindLabel(h.kind)}</span>
            <span className="nq-horizon__title">{h.title}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}