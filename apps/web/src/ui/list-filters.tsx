"use client";

import { ReactNode } from "react";
import { filterSummary } from "../lib/list-filters";

export type FilterOption = { value: string; label: string };

export type ListToolbarProps = {
  search: string;
  onSearchChange: (value: string) => void;
  searchPlaceholder?: string;
  status?: string;
  onStatusChange?: (value: string) => void;
  statusOptions?: FilterOption[];
  statusLabel?: string;
  person?: string;
  onPersonChange?: (value: string) => void;
  personOptions?: FilterOption[];
  personLabel?: string;
  time?: string;
  onTimeChange?: (value: string) => void;
  timeOptions?: FilterOption[];
  timeLabel?: string;
  shown?: number;
  total?: number;
  filtered?: boolean;
  children?: ReactNode;
};

function SelectFilter({
  id,
  label,
  value,
  options,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  options: FilterOption[];
  onChange: (v: string) => void;
}) {
  if (!options.length) return null;
  return (
    <label className="nq-filter-field" htmlFor={id}>
      <span className="nq-filter-label">{label}</span>
      <select id={id} className="nq-select" value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function ListToolbar({
  search,
  onSearchChange,
  searchPlaceholder = "Tìm trong danh sách…",
  status = "all",
  onStatusChange,
  statusOptions = [],
  statusLabel = "Trạng thái",
  person = "all",
  onPersonChange,
  personOptions = [],
  personLabel = "Người liên quan",
  time = "all",
  onTimeChange,
  timeOptions = [],
  timeLabel = "Thời gian",
  shown,
  total,
  filtered = false,
  children,
}: ListToolbarProps) {
  const countText =
    typeof shown === "number" && typeof total === "number"
      ? filterSummary(shown, total, filtered)
      : null;

  return (
    <div className="nq-list-toolbar" role="search">
      <div className="nq-list-toolbar-row">
        <label className="nq-filter-field nq-filter-field--grow" htmlFor="nq-list-search">
          <span className="nq-filter-label">Tìm kiếm</span>
          <input
            id="nq-list-search"
            type="search"
            className="nq-input"
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder={searchPlaceholder}
            autoComplete="off"
          />
        </label>
        {onStatusChange ? (
          <SelectFilter
            id="nq-filter-status"
            label={statusLabel}
            value={status}
            options={statusOptions}
            onChange={onStatusChange}
          />
        ) : null}
        {onPersonChange ? (
          <SelectFilter
            id="nq-filter-person"
            label={personLabel}
            value={person}
            options={personOptions}
            onChange={onPersonChange}
          />
        ) : null}
        {onTimeChange ? (
          <SelectFilter
            id="nq-filter-time"
            label={timeLabel}
            value={time}
            options={timeOptions}
            onChange={onTimeChange}
          />
        ) : null}
      </div>
      {(countText || children) && (
        <div className="nq-list-toolbar-meta">
          {countText ? <span className="nq-filter-count">{countText}</span> : null}
          {children}
        </div>
      )}
    </div>
  );
}

export function FilteredEmpty({ onClear }: { onClear?: () => void }) {
  return (
    <div className="nq-filtered-empty">
      <p className="nq-filtered-empty-title">Không có mục khớp bộ lọc</p>
      <p className="nq-muted">Thử đổi từ khóa hoặc mở rộng trạng thái / thời gian.</p>
      {onClear ? (
        <button type="button" className="nq-filter-clear" onClick={onClear}>
          Xóa bộ lọc
        </button>
      ) : null}
    </div>
  );
}
