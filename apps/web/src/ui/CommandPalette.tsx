"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { canAccess } from "../lib/session";
import { Icon, iconForHref } from "./icons";

type CmdItem = { href: string; label: string; group: string };

export function CommandPalette({
  open,
  onClose,
  items,
  role,
}: {
  open: boolean;
  onClose: () => void;
  items: CmdItem[];
  role: string | null;
}) {
  const router = useRouter();
  const [q, setQ] = useState("");
  const [active, setActive] = useState(0);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const allowed = items.filter((it) => canAccess(role || "", it.href));
    if (!needle) return allowed.slice(0, 12);
    return allowed
      .filter((it) => `${it.label} ${it.group} ${it.href}`.toLowerCase().includes(needle))
      .slice(0, 12);
  }, [items, q, role]);

  useEffect(() => {
    if (!open) return;
    setQ("");
    setActive(0);
  }, [open]);

  useEffect(() => {
    setActive(0);
  }, [q]);

  useEffect(() => {
    if (!open) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive((i) => Math.min(i + 1, Math.max(filtered.length - 1, 0)));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive((i) => Math.max(i - 1, 0));
      } else if (e.key === "Enter") {
        const hit = filtered[active];
        if (hit) {
          e.preventDefault();
          router.push(hit.href);
          onClose();
        }
      }
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, filtered, active, onClose, router]);

  if (!open) return null;

  return (
    <div className="nq-cmdk-overlay" role="presentation" onClick={onClose}>
      <div
        className="nq-cmdk"
        role="dialog"
        aria-modal="true"
        aria-label="Tìm trang nhanh"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          className="nq-cmdk__input"
          autoFocus
          placeholder="Tìm trang hoặc việc… (Esc để đóng)"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <ul className="nq-cmdk__list" role="listbox">
          {filtered.length === 0 ? (
            <li className="nq-cmdk__item" aria-disabled="true">
              Không có kết quả
            </li>
          ) : (
            filtered.map((it, i) => (
              <li key={it.href} role="option" aria-selected={i === active}>
                <button
                  type="button"
                  className="nq-cmdk__item"
                  data-active={i === active ? "1" : "0"}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => {
                    router.push(it.href);
                    onClose();
                  }}
                >
                  <Icon name={iconForHref(it.href)} size={16} />
                  <span>{it.label}</span>
                  <span className="nq-cmdk__hint">{it.group}</span>
                </button>
              </li>
            ))
          )}
        </ul>
      </div>
    </div>
  );
}

/** Flat list from AppShell GROUPS for Cmd+K. */
export function flattenNavGroups(
  groups: { title: string; items: { href: string; label: string }[] }[],
): CmdItem[] {
  return groups.flatMap((g) => g.items.map((it) => ({ ...it, group: g.title })));
}
