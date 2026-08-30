"use client";

import type { ReactNode } from "react";
import { Btn, Empty, StatusChip, TabBar, TabButton, inputClassName } from "../../ui/kit";

export type ResultTab = "overview" | "vanhanh" | "bantin" | "viec" | "coaching";

export function MeetingSection({
  title,
  hint,
  count,
  children,
}: {
  title: string;
  hint?: string;
  count?: number;
  children: ReactNode;
}) {
  return (
    <section className="nq-meeting-section">
      <header className="nq-meeting-section__head">
        <div>
          <h3 className="nq-meeting-section__title">{title}</h3>
          {hint ? <p className="nq-meeting-section__hint">{hint}</p> : null}
        </div>
        {typeof count === "number" ? (
          <span className="nq-meeting-section__count">{count}</span>
        ) : null}
      </header>
      {children}
    </section>
  );
}

export function MeetingResultTabs({
  active,
  onChange,
  counts,
}: {
  active: ResultTab;
  onChange: (tab: ResultTab) => void;
  counts: Partial<Record<ResultTab, number>>;
}) {
  const tabs: { id: ResultTab; label: string }[] = [
    { id: "overview", label: "Tổng quan" },
    { id: "vanhanh", label: "Vấn đề & SOP" },
    { id: "bantin", label: "Bản tin ca" },
    { id: "viec", label: "Việc giao" },
    { id: "coaching", label: "Góp ý & Huấn luyện" },
  ];

  return (
    <TabBar>
      {tabs.map((tab) => (
        <TabButton key={tab.id} active={active === tab.id} onClick={() => onChange(tab.id)}>
          {tab.label}
          {counts[tab.id] ? ` (${counts[tab.id]})` : ""}
        </TabButton>
      ))}
    </TabBar>
  );
}

export function MeetingMetaRow({ items }: { items: { label: string; value: ReactNode }[] }) {
  return (
    <dl className="nq-meeting-meta">
      {items.map((item) => (
        <div key={item.label} className="nq-meeting-meta__item">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

export function MeetingList({ children }: { children: ReactNode }) {
  return <ul className="nq-meeting-list">{children}</ul>;
}

export function MeetingListItem({
  title,
  meta,
  badge,
  children,
}: {
  title: ReactNode;
  meta?: ReactNode;
  badge?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <li className="nq-meeting-list__item">
      <div className="nq-meeting-list__main">
        <div className="nq-meeting-list__row">
          <p className="nq-meeting-list__title">{title}</p>
          {badge}
        </div>
        {meta ? <p className="nq-meeting-list__meta">{meta}</p> : null}
        {children}
      </div>
    </li>
  );
}

export function vanDeTone(trang_thai: string): "ok" | "warn" | "danger" | "default" {
  if (trang_thai === "da_giai_quyet") return "ok";
  if (trang_thai === "theo_doi") return "warn";
  return "danger";
}

export function vanDeLabel(trang_thai: string): string {
  if (trang_thai === "da_giai_quyet") return "Đã giải quyết trong họp";
  if (trang_thai === "theo_doi") return "Cần theo đội thêm";
  return "Cần hành động sau họp";
}

export function propTone(trang_thai: string): "ok" | "warn" | "danger" | "default" {
  if (trang_thai === "da_duyet") return "ok";
  if (trang_thai === "tu_choi") return "danger";
  return "warn";
}

export function propLabel(trang_thai: string): string {
  if (trang_thai === "da_duyet") return "Đã duyệt tại họp";
  if (trang_thai === "tu_choi") return "Bị từ chối";
  return "Chờ quản lý duyệt";
}

export function sopRankTone(rank: string): "ok" | "warn" | "danger" | "default" {
  if (rank === "A") return "ok";
  if (rank === "B") return "default";
  if (rank === "C") return "warn";
  return "danger";
}

export { Btn, Empty, StatusChip, inputClassName };
