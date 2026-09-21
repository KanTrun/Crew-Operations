"use client";

/** FlavorUniverse — khách nói khẩu vị → gợi ý có lý do. */

import { useState } from "react";

interface Rec {
  mon_id: string;
  ten: string;
  score: number;
  reasons: string[];
}

export default function FlavorUniverse() {
  const [do_ngot, setDoNgot] = useState("vua");
  const [co_sua, setCoSua] = useState(true);
  const [huong_tra, setHuongTra] = useState(false);
  const [allergy, setAllergy] = useState("");
  const [result, setResult] = useState<Rec[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  async function recommend() {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${base}/api/v1/experience/quanverse/flavor/recommend`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {}),
        },
        body: JSON.stringify({
          do_ngot,
          co_sua,
          huong_tra,
          dietary_allergy: allergy.trim() ? [allergy.trim()] : [],
        }),
      });
      if (!res.ok) throw new Error(`api_${res.status}`);
      const body = (await res.json()) as { recommendations: Rec[] };
      setResult(body.recommendations);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi recommend");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="nq-flavor" aria-label="Flavor Universe">
      <h3>Flavor Universe</h3>
      <p className="nq-flavor__note">Nói khẩu vị của bạn — hệ thống gợi ý có lý do.</p>

      <div className="nq-flavor__controls">
        <label>
          Độ ngọt
          <select value={do_ngot} data-testid="flavor-ngot" onChange={(e) => setDoNgot(e.target.value)}>
            <option value="it">Ít ngọt</option>
            <option value="vua">Vừa</option>
            <option value="ngot">Ngọt</option>
          </select>
        </label>
        <label className="nq-flavor__check">
          <input type="checkbox" checked={co_sua} data-testid="flavor-sua" onChange={(e) => setCoSua(e.target.checked)} />
          Có sữa
        </label>
        <label className="nq-flavor__check">
          <input type="checkbox" checked={huong_tra} data-testid="flavor-tra" onChange={(e) => setHuongTra(e.target.checked)} />
          Thơm trà
        </label>
        <label>
          Dị ứng (khai báo tường minh, không tự đoán)
          <input
            type="text"
            value={allergy}
            data-testid="flavor-allergy"
            placeholder="vd: sữa"
            onChange={(e) => setAllergy(e.target.value)}
          />
        </label>
        <button
          type="button"
          className="nq-btn nq-btn-primary"
          data-testid="flavor-go"
          disabled={busy}
          onClick={recommend}
        >
          Gợi ý
        </button>
      </div>

      {error ? <div className="nq-alert nq-alert--error">{error}</div> : null}

      {result ? (
        <ul className="nq-flavor__results" data-testid="flavor-results">
          {result.map((r) => (
            <li key={r.mon_id} className="nq-flavor__result">
              <span className="nq-flavor__name">{r.ten}</span>
              <ul className="nq-flavor__reasons">
                {r.reasons.map((reason, i) => (
                  <li key={i}>{reason}</li>
                ))}
              </ul>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}