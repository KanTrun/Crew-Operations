"use client";

/**
 * Phát hiện năng lực thiết bị cho lớp hình ảnh 3D của Trải nghiệm.
 *
 * Vì sao cần hook riêng thay vì `useState(false)`:
 * `LivingMap` khai `const [webgl] = useState(false)` nghĩa là nhánh 3D có code
 * nhưng không bao giờ chạy — người dùng chỉ thấy card chữ. Hook này trả về
 * "tier" thật, đo trên máy, và tự hạ cấp:
 *
 *   - `off`  → người dùng bật "giảm chuyển động" (tôn trọng lựa chọn hệ thống)
 *              hoặc không có WebGL thật (context tạo được nhưng là software).
 *   - `lite` → màn hẹp (< 900px) hoặc máy yếu: 3D chạy nhưng ít đối tượng,
 *              không bóng, không particle.
 *   - `full` → desktop rộng: bóng mềm + particle.
 *
 * Có `matchMedia` listener để đổi tier khi người dùng xoay máy hoặc đổi cài
 * đặt hệ thống giữa chừng. Không đọc WebGL từ module scope: mọi thứ chạy trong
 * effect nên không phá SSR/prerender.
 */

import { useEffect, useState } from "react";

export type Tier3d = "off" | "lite" | "full";

function hasRealWebGL(): boolean {
  if (typeof window === "undefined") return false;
  const canvas = document.createElement("canvas");
  let gl: WebGLRenderingContext | null = null;
  try {
    gl = (canvas.getContext("webgl2") ??
      canvas.getContext("webgl")) as WebGLRenderingContext | null;
  } catch {
    return false;
  }
  if (!gl) return false;
  try {
    // `WEBGL_debug_renderer_info` là cách duy nhất phát hiện renderer phần mềm
    // (SwiftShader). Không có bước này thì máy ảo/máy không GPU sẽ bật 3D rồi
    // treo ở khung hình 4–6 fps — tệ hơn hẳn 2D.
    const ext = gl.getExtension("WEBGL_debug_renderer_info");
    const renderer = ext
      ? String(gl.getParameter(ext.UNMASKED_RENDERER_WEBGL)).toLowerCase()
      : "";
    if (renderer.includes("swiftshader") || renderer.includes("llvmpipe")) return false;
    return true;
  } catch {
    return false;
  }
}

/** Có nên dùng 3D không, và ở mức nào. Chỉ gọi trong client component. */
export function useCapability3d(): Tier3d {
  const [tier, setTier] = useState<Tier3d>("off");

  useEffect(() => {
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const wide = window.matchMedia("(min-width: 900px)");

    const evaluate = () => {
      if (motion.matches || !hasRealWebGL()) {
        setTier("off");
        return;
      }
      setTier(wide.matches ? "full" : "lite");
    };

    evaluate();
    motion.addEventListener("change", evaluate);
    wide.addEventListener("change", evaluate);
    return () => {
      motion.removeEventListener("change", evaluate);
      wide.removeEventListener("change", evaluate);
    };
  }, []);

  return tier;
}

/** Người dùng có đang yêu cầu giảm chuyển động không (cho hiệu ứng CSS/JS). */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mq.matches);
    const onChange = () => setReduced(mq.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);
  return reduced;
}
