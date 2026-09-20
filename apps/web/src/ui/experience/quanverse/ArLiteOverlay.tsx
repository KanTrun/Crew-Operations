"use client";

/** ArLiteOverlay — capability gate; QR anchor path, fallback map/text. */

import { useState } from "react";

export default function ArLiteOverlay() {
  const [qr, setQr] = useState("");
  const [result, setResult] = useState<{ anchor_target: string; fallback: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  async function start() {
    if (!qr.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`${base}/api/v1/experience/quanverse/ar-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {}),
        },
        body: JSON.stringify({ qr: qr.trim() }),
      });
      if (!res.ok) throw new Error(`api_${res.status}`);
      setResult((await res.json()) as { anchor_target: string; fallback: string });
    } catch {
      // camera/WebXR fail → fallback map/QR/text
      setResult({ anchor_target: qr, fallback: "map_or_qr_text" });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="nq-ar" aria-label="AR-lite">
      <h3>AR-lite</h3>
      <p className="nq-ar__note">Không nhận diện khuôn mặt / SLAM tự động. Chỉ QR + anchor chọn tay.</p>
      <div className="nq-ar__row">
        <input
          type="text"
          value={qr}
          data-testid="ar-qr"
          placeholder="vd: blender-02"
          onChange={(e) => setQr(e.target.value)}
        />
        <button
          type="button"
          className="nq-btn"
          data-testid="ar-start"
          disabled={busy || !qr.trim()}
          onClick={start}
        >
          Mở AR overlay
        </button>
      </div>
      {result ? (
        <p className="nq-ar__result" data-testid="ar-result">
          Anchor {result.anchor_target} · fallback: {result.fallback}
        </p>
      ) : null}
    </section>
  );
}