"use client";

import { type ReactNode } from "react";
import { nvTenHienThi } from "../lib/present";
import { type ShiftOption, type StaffOption, useOpsPickers } from "../lib/ops-context";
import { Field, Hint, Loading, Select } from "./kit";

type BaseProps = {
  label?: string;
  hint?: ReactNode;
  disabled?: boolean;
  placeholder?: string;
};

export function PersonSelect({
  value,
  onChange,
  label = "Nhân viên",
  hint,
  disabled,
  placeholder = "Chọn nhân viên…",
  staff,
}: BaseProps & {
  value: string;
  onChange: (id: string) => void;
  staff?: StaffOption[];
}) {
  const { data, loading, error } = useOpsPickers(!staff);
  const options = staff ?? data?.nhan_vien ?? [];

  return (
    <Field label={label}>
      {loading && !staff ? <Loading skeleton="text">Đang tải danh sách…</Loading> : null}
      {error && !staff ? <p className="nq-muted text-sm">{error}</p> : null}
      <Select
        value={value}
        disabled={disabled || (loading && !staff)}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((n) => (
          <option key={n.id} value={n.id}>
            {nvTenHienThi(n.ten, n.id)}
          </option>
        ))}
      </Select>
      {hint ? <Hint>{hint}</Hint> : null}
    </Field>
  );
}

export function ShiftSelect({
  value,
  onChange,
  label = "Ca",
  hint,
  disabled,
  placeholder = "Chọn ca…",
  shifts,
}: BaseProps & {
  value: string;
  onChange: (id: string) => void;
  shifts?: ShiftOption[];
}) {
  const { data, loading, error } = useOpsPickers(!shifts);
  const options = shifts ?? data?.ca ?? [];

  return (
    <Field label={label}>
      {loading && !shifts ? <Loading skeleton="text">Đang tải ca…</Loading> : null}
      {error && !shifts ? <p className="nq-muted text-sm">{error}</p> : null}
      <Select
        value={value}
        disabled={disabled || (loading && !shifts)}
        onChange={(e) => onChange(e.target.value)}
      >
        <option value="">{placeholder}</option>
        {options.map((c) => (
          <option key={c.id} value={c.id}>
            {c.label}
          </option>
        ))}
      </Select>
      {hint ? <Hint>{hint}</Hint> : null}
    </Field>
  );
}

const THU_OPTIONS = ["T2", "T3", "T4", "T5", "T6", "T7", "CN"] as const;

export function DayOfWeekSelect({
  value,
  onChange,
  label = "Thứ",
}: {
  value: string;
  onChange: (v: string) => void;
  label?: string;
}) {
  return (
    <Field label={label}>
      <Select value={value} onChange={(e) => onChange(e.target.value)}>
        {THU_OPTIONS.map((t) => (
          <option key={t} value={t}>
            {t}
          </option>
        ))}
      </Select>
    </Field>
  );
}

/** Trả về nv_id của phiên hiện tại (nếu có). */
export function useMeNvId(): string | null {
  const { data } = useOpsPickers(true);
  return data?.me_nv_id ?? null;
}
