"use client";

import { useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { safeText, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  Loading,
  PageHeader,
  textareaStyle,
} from "../../ui/kit";

type Ans = { cau_tra_loi: string; trich_dan: string[]; chua_co: boolean };

export default function SopPage() {
  const [token, setToken] = useState("");
  const [q, setQ] = useState("Nhiệt độ tủ lạnh bao nhiêu là được?");
  const [a, setA] = useState<Ans | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setToken(getToken());
  }, []);

  async function ask() {
    setError(null);
    if (!q.trim()) {
      setError("Nhập câu hỏi trước khi bấm hỏi.");
      return;
    }
    setBusy(true);
    try {
      const d = await apiSend<Ans>("/api/v1/sop", { question: q.trim() });
      setA(d);
    } catch (e) {
      setError(viError(e, { doing: "hỏi được cẩm nang quán" }));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  const trichDan = (a?.trich_dan ?? []).map((x) => safeText(x, "")).filter(Boolean);

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="Chỉ trả lời từ phiếu và luật đã duyệt"
        title="Hỏi SOP"
        meta="Đặt câu bằng tiếng Việt thường ngày. Hệ thống chỉ dẫn lại phiếu và luật quán, không bịa."
      />
      <Field label="Câu hỏi">
        <textarea value={q} onChange={(e) => setQ(e.target.value)} rows={3} style={textareaStyle} />
      </Field>
      <Btn variant="primary" disabled={busy} onClick={ask}>
        {busy ? "Đang tra cẩm nang…" : "Hỏi cẩm nang"}
      </Btn>
      {error ? <Alert>{error}</Alert> : null}
      {busy && !a ? <Loading skeleton="text">Đang tra cẩm nang…</Loading> : null}
      {a ? (
        <article className="nq-item nq-sop-answer">
          <p>{safeText(a.cau_tra_loi, "Cẩm nang chưa có câu trả lời cho câu này.")}</p>
          {a.chua_co ? (
            <Alert kind="info">
              Chưa có trong cẩm nang. Làm theo cách quán đang làm, rồi nhờ quản lý ghi thành luật.
            </Alert>
          ) : null}
          <p className="nq-item-sub">
            {trichDan.length > 0 ? `Dẫn từ: ${trichDan.join(", ")}` : "Chưa có nguồn dẫn kèm câu này."}
          </p>
        </article>
      ) : (
        !busy && !error && <Empty>Chưa có câu trả lời — đặt câu hỏi để tra cẩm nang.</Empty>
      )}
    </div>
  );
}
