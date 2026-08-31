"use client";

import { useState } from "react";
import { apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import type { KhungGio } from "../../lib/roster";
import { Alert, Btn } from "../../ui/kit";

const SLOTS: { key: string; label: string }[] = [
  { key: "sang", label: "Ca sáng" },
  { key: "chieu", label: "Ca chiều" },
  { key: "toi", label: "Ca tối" },
];

type Props = {
  template: KhungGio;
  disabled?: boolean;
  onSaved: () => void;
};

export function KhungConfigPanel({ template, disabled, onSaved }: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<KhungGio>(template);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  function openPanel() {
    setDraft(template);
    setError(null);
    setMsg(null);
    setOpen(true);
  }

  async function save() {
    setBusy(true);
    setError(null);
    try {
      await apiSend(
        "/api/v1/lich-tuan/khung-gio",
        {
          sang: draft.sang,
          chieu: draft.chieu,
          toi: draft.toi,
        },
        "PATCH",
      );
      setMsg("Đã lưu khung giờ. Nên rà lại lịch trước khi công bố.");
      onSaved();
    } catch (e) {
      setError(viError(e, { doing: "lưu khung giờ ca" }));
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <div className="nq-roster-khung-bar">
        <p className="nq-muted text-xs">
          Khung giờ quán:{" "}
          {SLOTS.map((s) => {
            const g = template[s.key];
            return g ? `${s.label} ${g.bat_dau}–${g.ket_thuc}` : s.label;
          }).join(" · ")}
        </p>
        <Btn variant="ghost" className="nq-btn-compact" disabled={disabled} onClick={openPanel}>
          Chỉnh khung giờ
        </Btn>
      </div>
    );
  }

  return (
    <div className="nq-roster-khung-panel">
      <div className="nq-roster-khung-panel__head">
        <h2 className="text-sm font-bold uppercase tracking-widest text-[var(--nq-copper)]">
          Cài khung giờ quán
        </h2>
        <p className="nq-muted text-xs mt-1">
          Áp dụng cho cả 3 khung mỗi ngày. Đổi giờ không tự chạy lại solver — rà trùng lịch trước khi duyệt.
        </p>
      </div>
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      <div className="nq-roster-khung-grid">
        {SLOTS.map((s) => (
          <fieldset key={s.key} className="nq-roster-khung-field">
            <legend>{s.label}</legend>
            <label className="nq-filter-field">
              <span className="nq-filter-label">Bắt đầu</span>
              <input
                type="time"
                className="nq-input"
                value={draft[s.key]?.bat_dau ?? ""}
                disabled={disabled || busy}
                onChange={(e) =>
                  setDraft((v) => ({
                    ...v,
                    [s.key]: { ...v[s.key], bat_dau: e.target.value, ket_thuc: v[s.key]?.ket_thuc ?? "12:00" },
                  }))
                }
              />
            </label>
            <label className="nq-filter-field">
              <span className="nq-filter-label">Kết thúc</span>
              <input
                type="time"
                className="nq-input"
                value={draft[s.key]?.ket_thuc ?? ""}
                disabled={disabled || busy}
                onChange={(e) =>
                  setDraft((v) => ({
                    ...v,
                    [s.key]: { bat_dau: v[s.key]?.bat_dau ?? "07:00", ket_thuc: e.target.value },
                  }))
                }
              />
            </label>
          </fieldset>
        ))}
      </div>
      <div className="flex flex-wrap gap-2 justify-end mt-4">
        <Btn variant="ghost" className="nq-btn-compact" disabled={busy} onClick={() => setOpen(false)}>
          Đóng
        </Btn>
        <Btn className="nq-btn-compact" busy={busy} disabled={disabled} onClick={() => void save()}>
          Lưu khung giờ
        </Btn>
      </div>
    </div>
  );
}
