"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { apiGet, apiSend } from "../../lib/api";
import { luatLabel, safeText, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  Loading,
  PageHeader,
  StatusChip,
  Textarea,
} from "../../ui/kit";

type Ans = { cau_tra_loi: string; trich_dan: string[]; chua_co: boolean };
type Luat = { id: string; cau?: string; trang_thai: string };

const GOI_Y_MAC_DINH = [
  "Nhiệt độ tủ lạnh bao nhiêu là được?",
  "Mở quán phải kiểm kê những gì?",
  "Khi nào phải đặt thêm sữa tươi?",
];

export default function SopPage() {
  const [token, setToken] = useState("");
  const [q, setQ] = useState("");
  const [a, setA] = useState<Ans | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [luat, setLuat] = useState<Luat[]>([]);
  const [history, setHistory] = useState<string[]>([]);

  useEffect(() => {
    setToken(getToken());
    try {
      const raw = localStorage.getItem("nq_sop_history");
      if (raw) setHistory(JSON.parse(raw) as string[]);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    if (!token) return;
    apiGet<{ items: Luat[] }>("/api/v1/cam-nang")
      .then((d) => setLuat((d.items ?? []).filter((x) => x.trang_thai === "hieu_luc").slice(0, 6)))
      .catch(() => undefined);
  }, [token]);

  const chips = useMemo(() => {
    const fromLuat = luat.map((l) => safeText(l.cau, "")).filter((c) => c.length > 8 && c.length < 80);
    return [...new Set([...fromLuat, ...GOI_Y_MAC_DINH])].slice(0, 8);
  }, [luat]);

  const ask = useCallback(async (question: string) => {
    setError(null);
    const text = question.trim();
    if (!text) {
      setError("Nhập câu hỏi trước khi bấm hỏi.");
      return;
    }
    setBusy(true);
    try {
      const d = await apiSend<Ans>("/api/v1/sop", { question: text });
      setA(d);
      setHistory((prev) => {
        const next = [text, ...prev.filter((x) => x !== text)].slice(0, 10);
        localStorage.setItem("nq_sop_history", JSON.stringify(next));
        return next;
      });
    } catch (e) {
      setError(viError(e, { doing: "hỏi được cẩm nang quán" }));
    } finally {
      setBusy(false);
    }
  }, []);

  if (!token) return <AuthGate />;

  const trichDan = (a?.trich_dan ?? []).map((x) => safeText(x, "")).filter(Boolean);

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="Chỉ trả lời từ phiếu và luật đã duyệt"
        title="Hỏi SOP"
        meta="Đặt câu bằng tiếng Việt thường ngày. Hệ thống chỉ dẫn lại phiếu và luật quán, không bịa."
      />

      {chips.length > 0 ? (
        <div className="flex flex-wrap gap-2 mb-4">
          {chips.map((c) => (
            <button
              key={c}
              type="button"
              className="nq-chip"
              onClick={() => {
                setQ(c);
                void ask(c);
              }}
            >
              {c}
            </button>
          ))}
        </div>
      ) : null}

      <Field label="Câu hỏi">
        <Textarea
          value={q}
          onChange={(e) => setQ(e.target.value)}
          rows={4}
          placeholder="Ví dụ: Nhiệt độ tủ lạnh bao nhiêu là được?"
        />
      </Field>
      <Btn variant="primary" disabled={busy} onClick={() => void ask(q)}>
        {busy ? "Đang tra cẩm nang…" : "Hỏi cẩm nang"}
      </Btn>

      {history.length > 0 ? (
        <div className="mt-4">
          <p className="text-xs font-mono uppercase tracking-widest text-[var(--nq-copper)] mb-2">Câu gần đây</p>
          <div className="flex flex-wrap gap-2">
            {history.map((h) => (
              <button key={h} type="button" className="nq-chip" onClick={() => void ask(h)}>
                {h.length > 48 ? `${h.slice(0, 48)}…` : h}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {error ? <Alert>{error}</Alert> : null}
      {busy && !a ? <Loading skeleton="text">Đang tra cẩm nang…</Loading> : null}
      {a ? (
        <article className="nq-item nq-sop-answer mt-4">
          <p>{safeText(a.cau_tra_loi, "Cẩm nang chưa có câu trả lời cho câu này.")}</p>
          {a.chua_co ? (
            <Alert kind="info">
              Chưa có trong cẩm nang.{" "}
              <Link href="/cam-nang" className="underline">
                Mở cẩm nang
              </Link>{" "}
              để đề xuất luật mới.
            </Alert>
          ) : null}
          {trichDan.length > 0 ? (
            <div className="mt-3 flex flex-wrap gap-2">
              {trichDan.map((t) => (
                <StatusChip key={t} tone="default">
                  Dẫn từ: {t}
                </StatusChip>
              ))}
            </div>
          ) : (
            <p className="nq-item-sub">Chưa có nguồn dẫn kèm câu này.</p>
          )}
        </article>
      ) : (
        !busy && !error && <Empty>Chưa có câu trả lời — đặt câu hỏi hoặc chọn gợi ý ở trên.</Empty>
      )}

      {luat.length > 0 ? (
        <section className="mt-8">
          <p className="text-xs font-mono uppercase tracking-widest text-[var(--nq-copper)] mb-2">Luật đang hiệu lực</p>
          <div className="nq-list">
            {luat.map((l) => (
              <article key={l.id} className="nq-item">
                <p className="nq-item-title nq-clamp-2">{safeText(l.cau, "Luật")}</p>
                <p className="nq-item-sub">
                  <StatusChip tone="ok">{luatLabel(l.trang_thai)}</StatusChip>
                </p>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
