"use client";

import React from "react";

/**
 * Avatar 2D cho AG-COPILOT — vẽ bằng SVG inline (không cần file ảnh).
 *
 * Miệng mở/đóng theo `mouthOpen` (0-1) để tạo hiệu ứng lip-sync khi
 * trợ lý đang nói. Có vòng tròn trạng thái phía sau và badge trạng thái.
 */
export function Avatar2D({
  mouthOpen,
  speaking,
  listening,
  size = 96,
}: {
  mouthOpen: number;
  speaking: boolean;
  listening: boolean;
  size?: number;
}) {
  // Clamp mouthOpen 0-1.
  const open = Math.max(0, Math.min(1, mouthOpen));
  // Chiều cao miệng: từ 2px (ngậm) đến 14px (mở tối đa).
  const mouthHeight = 2 + open * 12;
  const mouthY = 62 - mouthHeight / 2;

  return (
    <div
      className="relative shrink-0"
      style={{ width: size, height: size }}
      aria-hidden="true"
    >
      {/* Vòng tròn trạng thái phía sau */}
      <div
        className={`absolute inset-0 rounded-full transition-colors ${
          speaking
            ? "bg-[var(--nq-accent)]/20"
            : listening
            ? "bg-emerald-500/15"
            : "bg-[var(--nq-dim)]/10"
        }`}
      />
      {speaking && (
        <div className="absolute inset-0 animate-ping rounded-full bg-[var(--nq-accent)]/10" />
      )}

      {/* Khuôn mặt SVG */}
      <svg
        viewBox="0 0 100 100"
        className="absolute inset-0 h-full w-full"
        style={{ filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.3))" }}
      >
        {/* Đầu */}
        <circle cx="50" cy="50" r="38" fill="#e8b98a" stroke="#c99a6a" strokeWidth="1.5" />
        {/* Tóc */}
        <path
          d="M12 50 a38 38 0 0 1 76 0 l0 -6 a38 38 0 0 0 -76 0 z"
          fill="#3a2a1a"
        />
        {/* Mắt trái */}
        <ellipse cx="38" cy="46" rx="4.5" ry="5" fill="#ffffff" />
        <circle cx="38" cy="47" r="2.2" fill="#2a1a0a" />
        {/* Mắt phải */}
        <ellipse cx="62" cy="46" rx="4.5" ry="5" fill="#ffffff" />
        <circle cx="62" cy="47" r="2.2" fill="#2a1a0a" />
        {/* Lông mày */}
        <path d="M32 38 q6 -4 12 0" stroke="#3a2a1a" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        <path d="M56 38 q6 -4 12 0" stroke="#3a2a1a" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        {/* Mũi */}
        <path d="M50 50 q2 4 0 7" stroke="#c99a6a" strokeWidth="1.5" fill="none" strokeLinecap="round" />
        {/* Miệng — mở/đóng theo mouthOpen.
            Cập nhật mượt qua rAF (useAvatarLipSync), nên không cần CSS
            transition trên thuộc tính SVG (không được hỗ trợ đồng nhất). */}
        <rect
          x="42"
          y={mouthY}
          width="16"
          height={mouthHeight}
          rx={mouthHeight / 2}
          fill="#7a3a2a"
        />
        {/* Tai */}
        <circle cx="12" cy="52" r="4" fill="#e8b98a" stroke="#c99a6a" strokeWidth="1" />
        <circle cx="88" cy="52" r="4" fill="#e8b98a" stroke="#c99a6a" strokeWidth="1" />
      </svg>

      {/* Badge trạng thái */}
      <div
        className={`absolute -bottom-1 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full border px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide ${
          speaking
            ? "border-[var(--nq-accent)] bg-[var(--nq-bg)] text-[var(--nq-accent)]"
            : listening
            ? "border-emerald-500/50 bg-[var(--nq-bg)] text-emerald-400"
            : "border-[var(--nq-dim)] bg-[var(--nq-bg)] text-[var(--nq-dim)]"
        }`}
      >
        {speaking ? "Đang nói" : listening ? "Đang nghe" : "Trợ lý"}
      </div>
    </div>
  );
}