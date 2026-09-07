// CopilotPane: pane nổi, neo ổn định ở góc phải dưới và có thể thu nhỏ.
//
// Dùng được ở AppShell và các page riêng (controlled mode như trước).

"use client";

import React, {
  useCallback,
  useEffect,
  useState,
  type CSSProperties,
} from "react";
import { CopilotBody } from "./CopilotBody";
import { useCopilotChat } from "./useCopilotChat";
import type { Role } from "../../lib/session";

const POS_KEY = "ag_copilot_pane_pos_v2";

interface PaneState {
  /** 0 = collapsed (chỉ chip), 1 = small, 2 = large */
  size: 0 | 1 | 2;
  /** Size của pane khi size>0. */
  w: number;
  h: number;
}

const DEFAULT_STATE: PaneState = {
  size: 1,
  w: 380,
  h: 540,
};

function loadState(): PaneState {
  if (typeof window === "undefined") return DEFAULT_STATE;
  try {
    const raw = window.localStorage.getItem(POS_KEY);
    if (!raw) return DEFAULT_STATE;
    const s = JSON.parse(raw) as Partial<PaneState>;
    return { ...DEFAULT_STATE, ...s };
  } catch {
    return DEFAULT_STATE;
  }
}

function saveState(s: PaneState) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(POS_KEY, JSON.stringify(s));
  } catch {/* ignore */}
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v));
}

interface Props {
  /** Controlled mode: nếu truyền `open` thì pane dùng giá trị này. */
  open?: boolean;
  /** Controlled mode: callback đóng. */
  onClose?: () => void;
}

export function CopilotPane({ open, onClose }: Props = {}) {
  const isControlled = open !== undefined;
  const [internalOpen, setInternalOpen] = useState(false);
  const isOpen = isControlled ? Boolean(open) : internalOpen;

  const [state, setState] = useState<PaneState>(DEFAULT_STATE);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setState(loadState());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) saveState(state);
  }, [state, hydrated]);

  useEffect(() => {
    if (isControlled && open) {
      setState((current) => current.size === 0 ? { ...current, size: 1 } : current);
    }
  }, [isControlled, open]);

  const closePane = useCallback(() => {
    if (isControlled) onClose?.();
    else setInternalOpen(false);
  }, [isControlled, onClose]);

  // Phím tắt Ctrl/Cmd+K mở nhanh pane nếu user chưa mở.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const isToggle = (e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k";
      if (isToggle) {
        e.preventDefault();
        if (!isControlled) {
          setInternalOpen((v) => !v);
        } else if (isOpen) {
          onClose?.();
        }
        return;
      }
      if (e.key === "Escape" && isOpen) {
        // Thu nhỏ về chip thay vì đóng hẳn — mở lại nhanh.
        setState((s) => ({ ...s, size: 0 }));
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isControlled, isOpen, onClose]);

  // Neo pane ở một vị trí duy nhất; kích thước cũ vẫn được kẹp trong viewport.
  const style: CSSProperties = (() => {
    const viewportWidth = typeof window === "undefined" ? DEFAULT_STATE.w + 32 : window.innerWidth;
    const viewportHeight = typeof window === "undefined" ? DEFAULT_STATE.h + 32 : window.innerHeight;
    const maxWidth = Math.max(280, viewportWidth - 32);
    const maxHeight = Math.max(360, viewportHeight - 32);
    const w = state.size === 0 ? 56 : Math.min(state.w, maxWidth);
    const h = state.size === 0 ? 56 : Math.min(state.h, maxHeight);
    const margin = 16;
    return {
      right: margin,
      bottom: margin,
      width: w,
      height: h,
      zIndex: 50,
    };
  })();

  const chat = useCopilotChat("pane");

  // Chưa mở thì không render gì cả. (FAB/mở ngoài AppShell sẽ toggle.)
  if (!isOpen) return null;

  // Chế độ thu nhỏ (chip)
  if (state.size === 0) {
    return (
      <button
        onClick={() => setState((s) => ({ ...s, size: 1 }))}
        style={{
          ...style,
          position: "fixed",
          borderRadius: 9999,
        }}
        className="flex cursor-grab items-center justify-center border-2 border-[var(--nq-copper)] bg-[var(--nq-surface)] text-[var(--nq-copper)] shadow-[5px_5px_0_var(--nq-copper-dim)] transition hover:bg-[var(--nq-copper)] hover:text-[#0e0c0a] active:scale-95"
        title="Mở trợ lý vận hành"
      >
        <span className="text-sm font-black uppercase">Trợ lý</span>
      </button>
    );
  }

  return (
    <div
      style={{ ...style, position: "fixed" }}
      className="flex flex-col overflow-hidden rounded-xl border-2 border-[var(--nq-copper)] bg-[var(--nq-bg-elevated)] shadow-[0_8px_32px_rgba(0,0,0,0.55),8px_8px_0_var(--nq-copper-dim)]"
    >
      <div className="flex h-8 shrink-0 items-center justify-between border-b border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] px-2">
        <div className="h-0.5 w-10 bg-[var(--nq-dim)]" />
        <div className="flex gap-1" onMouseDown={(e) => e.stopPropagation()}>
          <button
            onClick={() => setState((s) => ({ ...s, size: 0 }))}
            title="Thu nhỏ về chip"
            className="border border-[var(--nq-dim)] bg-[var(--nq-surface)] px-2 py-0.5 text-[10px] leading-none text-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-fg)]"
          >
            –
          </button>
          <button
            onClick={() =>
              setState((s) => ({
                ...s,
                size: s.size === 2 ? 1 : 2,
                w: s.size === 2 ? 380 : Math.min(720, window.innerWidth - 40),
                h: s.size === 2 ? 540 : Math.min(820, window.innerHeight - 40),
              }))
            }
            title={state.size === 2 ? "Thu nhỏ" : "Phóng to"}
            className="border border-[var(--nq-dim)] bg-[var(--nq-surface)] px-2 py-0.5 text-[10px] leading-none text-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-fg)]"
          >
            {state.size === 2 ? "▢" : "▣"}
          </button>
        </div>
      </div>
      <div className="relative flex-1 min-h-0">
        <CopilotBody
          chat={chat}
          mode="pane"
          onClose={closePane}
          onOpenFullPage={() => window.open("/copilot", "_blank", "noopener")}
          onClearHistory={() => chat.clearHistory()}
        />
      </div>
    </div>
  );
}