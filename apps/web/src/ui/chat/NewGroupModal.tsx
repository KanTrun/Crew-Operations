"use client";

import React, { useState } from "react";
import { apiSend } from "../../lib/api";
import { useOpsPickers } from "../../lib/ops-context";
import { getNvId } from "../../lib/session";

interface NewGroupModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreated: (convId: string) => void;
}

export function NewGroupModal({ isOpen, onClose, onCreated }: NewGroupModalProps) {
  const { data: opsData } = useOpsPickers();
  const currentNvId = getNvId();
  const staffList = (opsData?.nhan_vien || []).filter((s) => s.id !== currentNvId);

  const [groupName, setGroupName] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]
    );
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!groupName.trim()) {
      setError("Vui lòng nhập tên nhóm.");
      return;
    }
    if (selectedIds.length === 0) {
      setError("Vui lòng chọn ít nhất 1 thành viên.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await apiSend<{ id: string }>("/api/v1/chat/conversations", {
        conv_type: "group",
        display_name: groupName.trim(),
        participant_nv_ids: selectedIds,
      });
      onCreated(res.id);
      onClose();
    } catch (err: any) {
      setError(err?.detail || "Không thể tạo nhóm");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-fade-in">
      <div className="bg-[var(--nq-card)] border border-[var(--nq-dim)] w-full max-w-md rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        <div className="p-4 border-b border-[var(--nq-dim)] flex items-center justify-between">
          <h3 className="font-bold text-base text-[var(--nq-fg)] flex items-center gap-2">
            <span>👥</span> Tạo nhóm chat mới
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-[var(--nq-muted)] hover:text-[var(--nq-fg)] text-lg px-2"
          >
            ✕
          </button>
        </div>

        <form onSubmit={handleCreate} className="p-4 flex flex-col gap-4 flex-1 overflow-hidden">
          {error && <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-500 font-medium">{error}</div>}

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-[var(--nq-muted)] mb-1">
              Tên nhóm
            </label>
            <input
              type="text"
              value={groupName}
              onChange={(e) => setGroupName(e.target.value)}
              placeholder="Vd: Tổ Barista, Team Ca Sáng…"
              className="w-full px-3 py-2 rounded-xl bg-[var(--nq-bg)] border border-[var(--nq-dim)] focus:border-[var(--nq-copper)] outline-none text-sm text-[var(--nq-fg)]"
              autoFocus
            />
          </div>

          <div className="flex-1 flex flex-col overflow-hidden">
            <label className="block text-xs font-bold uppercase tracking-wider text-[var(--nq-muted)] mb-1.5">
              Chọn thành viên ({selectedIds.length})
            </label>
            <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
              {staffList.length === 0 ? (
                <p className="text-xs text-[var(--nq-muted)] italic py-2">Không tìm thấy danh sách nhân sự khác.</p>
              ) : (
                staffList.map((staff) => {
                  const isChecked = selectedIds.includes(staff.id);
                  return (
                    <label
                      key={staff.id}
                      className={`flex items-center gap-3 p-2.5 rounded-xl cursor-pointer transition border ${
                        isChecked
                          ? "bg-[var(--nq-copper-dim)]/20 border-[var(--nq-copper)]"
                          : "bg-[var(--nq-bg)] border-transparent hover:border-[var(--nq-dim)]"
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => toggleSelect(staff.id)}
                        className="rounded accent-[var(--nq-copper)] w-4 h-4"
                      />
                      <div className="w-7 h-7 rounded-full bg-[var(--nq-dim)] text-xs flex items-center justify-center font-bold text-[var(--nq-copper)]">
                        {staff.ten.charAt(0).toUpperCase()}
                      </div>
                      <span className="text-sm font-medium text-[var(--nq-fg)] flex-1">{staff.ten}</span>
                    </label>
                  );
                })
              )}
            </div>
          </div>

          <div className="flex gap-2 pt-2 border-t border-[var(--nq-dim)] justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-xs font-bold text-[var(--nq-muted)] hover:text-[var(--nq-fg)] rounded-xl transition"
            >
              Hủy
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 text-xs font-bold uppercase tracking-wider bg-[var(--nq-copper)] text-white rounded-xl shadow-md hover:opacity-90 disabled:opacity-50 transition"
            >
              {loading ? "Đang tạo…" : "Tạo nhóm"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
