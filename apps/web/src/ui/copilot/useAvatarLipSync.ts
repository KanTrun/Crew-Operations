"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Hook lip-sync cho avatar 2D.
 *
 * Nhận mức amplitude (0-1) của audio trợ lý đang phát và chuyển thành
 * mức mở miệng (mouthOpen 0-1) mượt mà. Dùng requestAnimationFrame để
 * làm mượt.
 *
 * Tối ưu: vòng lặp rAF chỉ chạy khi đang nói (active) hoặc khi miệng
 * chưa về 0 — tránh tốn CPU liên tục khi voice không hoạt động.
 */
export function useAvatarLipSync(audioLevel: number, active: boolean) {
  const [mouthOpen, setMouthOpen] = useState(0);
  const targetRef = useRef(0);
  const currentRef = useRef(0);
  const rafRef = useRef<number | null>(null);
  const activeRef = useRef(active);
  activeRef.current = active;
  const inFlightRef = useRef(false);

  // Cập nhật target từ audioLevel (chỉ khi đang nói).
  useEffect(() => {
    targetRef.current = active ? audioLevel : 0;
  }, [audioLevel, active]);

  // Vòng lặp làm mượt mouthOpen. Chạy khi cần, tự dừng khi miệng về 0.
  useEffect(() => {
    const shouldRun = active || Math.abs(currentRef.current) >= 0.005;
    if (!shouldRun || inFlightRef.current) return;

    inFlightRef.current = true;
    let cancelled = false;

    const tick = () => {
      if (cancelled) return;
      // Nội suy tuyến tính về phía target.
      currentRef.current += (targetRef.current - currentRef.current) * 0.35;
      if (Math.abs(currentRef.current - targetRef.current) < 0.005) {
        currentRef.current = targetRef.current;
      }
      const value = currentRef.current;
      setMouthOpen(value);
      // Dừng loop khi đã về 0 và không active.
      if (!activeRef.current && Math.abs(value) < 0.005) {
        inFlightRef.current = false;
        return;
      }
      rafRef.current = requestAnimationFrame(tick);
    };
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      cancelled = true;
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = null;
      }
      inFlightRef.current = false;
    };
  }, [active, audioLevel]);

  return mouthOpen;
}