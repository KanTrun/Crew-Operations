"use client";

import { useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Field, inputStyle, PageHeader, textareaStyle } from "../../ui/kit";

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
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="Chỉ trả lời từ phiếu và luật đã duyệt"
        title="Hỏi SOP"
        meta="Đặt câu bằng tiếng Việt thường ngày. Hệ thống không bịa SOP."
      />
      <Field label="Câu hỏi">
        <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={3} style={textareaStyle} />
      </Field>
      <Btn variant="primary" onClick={ask}>
        Hỏi
      </Btn>
      {error ? <Alert>{error}</Alert> : null}
      {a ? (
        <article className="nq-item nq-sop-answer">
          <p>{a.cau_tra_loi}</p>
          {a.chua_co ? <Alert kind="info">Chưa có trong cẩm nang.</Alert> : null}
          <p className="nq-item-sub">Trích dẫn: {a.trich_dan.join(", ") || "không"}</p>
        </article>
      ) : (
        <Empty>Chưa có câu trả lời — hãy đặt câu hỏi.</Empty>
      )}
    </div>
  );
}
