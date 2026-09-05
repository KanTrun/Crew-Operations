// CopilotPane: pane nổi, KHÔNG overlay main content. Có thể kéo, thu nhỏ về
// chip, phóng to / đính vị trí 4 góc. Lưu vị trí + size vào localStorage đ
// giữa các lần mở.
//
// Dùng được ở AppShell và các page riêng (controlled mode như trước).

"use client";

import React, {
  useCallback,
  useEffect,
  useRef,
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
  /** Gắn vị trí: br | bl | tr | tl. */
  corner: "br" | "bl" | "tr" | "tl";
  /** Khi user kéo tự do, vị trí pixel (top, left). */
  x: number;
  y: number;
  /** Size của pane khi size>0. */
  w: number;
  h: number;
}

const DEFAULT_STATE: PaneState = {
  size: 1,
  corner: "br",
  x: -1,
  y: -1,
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
        if (isControlled) {
          if (!isOpen) onClose?.();
        } else {
          setInternalOpen((v) => !v);
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

  // Kéo pane
  const dragRef = useRef<{
    startX: number;
    startY: number;
    startPaneX: number;
    startPaneY: number;
  } | null>(null);

  const onDragMouseDown = useCallback(
    (e: React.MouseEvent) => {
      // Click phải / click vào nút → không kéo
      if (e.button !== 0) return;
      const target = e.target as HTMLElement;
      if (target.closest("button, input, a, textarea, select")) return;
      e.preventDefault();
      const r = paneRef.current?.getBoundingClientRect();
      if (!r) return;
      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        startPaneX: r.left,
        startPaneY: r.top,
      };
      const onMove = (ev: MouseEvent) => {
        const d = dragRef.current;
        if (!d) return;
        const maxX = window.innerWidth - 120;
        const maxY = window.innerHeight - 60;
        const nx = clamp(ev.clientX - d.startX + d.startPaneX, 0, maxX);
        const ny = clamp(ev.clientY - d.startY + d.startPaneY, 0, maxY);
        setState((s) => ({ ...s, x: nx, y: ny, corner: "br" }));
      };
      const onUp = () => {
        dragRef.current = null;
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    []
  );

  // Tính position pixel. Kẹp pane trong viewport để trạng thái cũ hoặc màn
  // hình nhỏ không làm pane trôi khỏi vùng thao tác.
  const paneRef = useRef<HTMLDivElement>(null);
  const style: CSSProperties = (() => {
    const maxWidth = Math.max(280, window.innerWidth - 32);
    const maxHeight = Math.max(360, window.innerHeight - 32);
    const w = state.size === 0 ? 56 : Math.min(state.w, maxWidth);
    const h = state.size === 0 ? 56 : Math.min(state.h, maxHeight);
    const margin = 16;
    let left: number;
    let top: number;
    if (state.x >= 0 && state.y >= 0 && state.size > 0) {
      // Tự do kéo
      left = clamp(state.x, 0, Math.max(0, window.innerWidth - w));
      top = clamp(state.y, 0, Math.max(0, window.innerHeight - h));
    } else {
      // Gắn theo corner
      const isLeft = state.corner === "bl" || state.corner === "tl";
      const isTop = state.corner === "tr" || state.corner === "tl";
      left = isLeft ? margin : window.innerWidth - w - margin;
      top = isTop ? margin : window.innerHeight - h - margin;
    }
    return {
      left,
      top,
      width: w,
      height: h,
      zIndex: 50,
    };
  })();

  // Resize khi kéo góc dưới-phải
  const resizeRef = useRef<{
    startX: number;
    startY: number;
    startW: number;
    startH: number;
  } | null>(null);

  const onResizeMouseDown = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    const r = paneRef.current?.getBoundingClientRect();
    if (!r) return;
    resizeRef.current = {
      startX: e.clientX,
      startY: e.clientY,
      startW: r.width,
      startH: r.height,
    };
    const onMove = (ev: MouseEvent) => {
      const d = resizeRef.current;
      if (!d) return;
      const nw = Math.max(280, ev.clientX + d.startW - d.startX);
      const nh = Math.max(360, ev.clientY + d.startH - d.startY);
      setState((s) => ({ ...s, w: nw, h: nh }));
    };
    const onUp = () => {
      resizeRef.current = null;
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }, []);

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
      ref={paneRef}
      style={{ ...style, position: "fixed" }}
      className="flex flex-col overflow-hidden border-2 border-[var(--nq-dim)] shadow-[8px_8px_0_var(--nq-copper-dim)]"
    >
      {/* Drag area: dùng header dưới dạng grab — đã có trong CopilotBody rồi,
          nhưng ta thêm 1 div kéo trên cùng để cả thanh tiêu đề kéo được. */}
      {/* Thanh kéo mỏng trên cùng — không chặn click vào chat */}
      <div
        onMouseDown={onDragMouseDown}
        className="flex h-3 shrink-0 cursor-grab items-center justify-center border-b border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] active:cursor-grabbing"
        title="Kéo để di chuyển"
      >
        <div className="h-0.5 w-10 bg-[var(--nq-dim)]" />
      </div>
      <div className="relative flex-1 min-h-0">
        <CopilotBody
          chat={chat}
          mode="pane"
          onClose={closePane}
          onOpenFullPage={() => window.open("/copilot", "_blank", "noopener")}
          onClearHistory={() => chat.clearHistory()}
        />
        {/* Controls góc trên-trái pane */}
        <div className="absolute top-2 left-2 z-20 flex gap-1">
          <button
            onClick={() => setState((s) => ({ ...s, size: 0 }))}
            title="Thu nhỏ về chip"
            className="border border-[var(--nq-dim)] bg-[var(--nq-surface)] px-2 py-1 text-[10px] text-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-fg)]"
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
            className="border border-[var(--nq-dim)] bg-[var(--nq-surface)] px-2 py-1 text-[10px] text-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-fg)]"
          >
            {state.size === 2 ? "▢" : "▣"}
          </button>
          <select
            value={state.corner}
            onChange={(e) =>
              setState((s) => ({
                ...s,
                corner: e.target.value as PaneState["corner"],
                x: -1,
                y: -1,
              }))
            }
            title="Gắn vị trí"
            className="border border-[var(--nq-dim)] bg-[var(--nq-surface)] px-1 text-[10px] text-[var(--nq-dim)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-fg)]"
          >
            <option value="br">BR</option>
            <option value="bl">BL</option>
            <option value="tr">TR</option>
            <option value="tl">TL</option>
          </select>
        </div>
        {/* Resize handle */}
        <div
          onMouseDown={onResizeMouseDown}
          className="absolute bottom-0 right-0 w-4 h-4 z-20 cursor-se-resize"
          style={{
            background:
              "linear-gradient(135deg, transparent 50%, rgba(255,255,255,0.25) 50%)",
          }}
          title="Kéo để đổi kích thước"
        />
      </div>
    </div>
  );
}