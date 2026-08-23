"use client";

import { useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, btnPrimary, Empty, Field, inputStyle, Kicker } from "../../ui/kit";

type Ans = { cau_tra_loi: string; trich_dan: string[]; chua_co: boolean };

export default function SopPage() {
  const [token, setToken] = useState("");
  const [q, setQ] = useState("Nhiệt độ tủ lạnh bao nhiêu là được?");
  const [a, setA] = useState<Ans | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setToken(getToken());
  }, []);

  async function ask() {
    setError(null);
    try {
      const d = await apiSend<Ans>("/api/v1/sop", { question: q });
      setA(d);
    } catch {
      setError("Không hỏi được SOP. Cần đăng nhập.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <Kicker>Chỉ trả lời từ phiếu và luật đã duyệt</Kicker>
      <h1>Hỏi SOP</h1>
      <Field label="Câu hỏi">
        <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={3} style={inputStyle} />
      </Field>
      <button onClick={ask} style={btnPrimary}>
        Hỏi
      </button>
      {error ? <Alert>{error}</Alert> : null}
      {a ? (
        <article className="nq-item" style={{ marginTop: "1rem" }}>
          <p>{a.cau_tra_loi}</p>
          {a.chua_co ? <Alert kind="info">Chưa có trong cẩm nang.</Alert> : null}
          <p className="nq-muted" style={{ fontSize: "0.85rem" }}>
            Trích dẫn: {a.trich_dan.join(", ") || "không"}
          </p>
        </article>
      ) : (
        <Empty>Đặt câu bằng tiếng Việt thường ngày. Hệ thống không bịa SOP.</Empty>
      )}
    </div>
  );
}
