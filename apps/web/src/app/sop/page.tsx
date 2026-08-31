"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { apiGet, apiSend } from "../../lib/api";
import { luatLabel, safeText, trichDanLabel, viError } from "../../lib/present";
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

type Ans = {
  cau_tra_loi: string;
  trich_dan: string[];
  chua_co: boolean;
  mode?: string;
  provider?: string;
  do_tin?: number;
};
type Luat = { id: string; cau?: string; trang_thai: string };

const GOI_Y_MAC_DINH = [
  "Nhiệt độ tủ lạnh bao nhiêu là được?",
  "Mở quán phải kiểm kê những gì?",
  "Bồn rửa mấy giờ phải vệ sinh?",
  "Khi nào phải đặt thêm sữa tươi?",
];

const BUOC_TEN: Record<string, string> = {
  nhiet_do_tu_lanh: "Ghi nhiệt độ tủ lạnh",
  nhiet_do_tu_dong: "Ghi nhiệt độ tủ đông",
  ve_sinh_quay: "Vệ sinh quầy pha",
  ve_sinh_ban: "Lau bàn khách",
  kiem_ke_dau_ca: "Kiểm kê đầu ca",
  kiem_ke_cuoi_ca: "Kiểm kê cuối ca",
  ban_giao_ca: "Bàn giao ca",
};

function modeLabel(mode?: string, provider?: string): string {
  if (mode === "live") return provider ? `AI · ${provider}` : "AI trực tiếp";
  return "Từ khóa cẩm nang";
}

export default function SopPage() {
  const [token, setToken] = useState("");
  const [q, setQ] = useState("");
  const [a, setA] = useState<Ans | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [luat, setLuat] = useState<Luat[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const answerRef = useRef<HTMLElement | null>(null);

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
      .then((d) => setLuat((d.items ?? []).filter((x) => x.trang_thai === "hieu_luc")))
      .catch(() => undefined);
  }, [token]);

  useEffect(() => {
    if (!a || busy) return;
    answerRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [a, busy]);

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
    setQ(text);
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
  const labelOpts = { luat, buocTen: BUOC_TEN };

  return (
    <div className="nq-page nq-page--run nq-sop-copilot">
      <PageHeader
        kicker="SOP Copilot"
        title="Hỏi quy trình quán"
        meta="Một câu trả lời rõ ràng từ phiếu và luật đã duyệt — không bịa, có nguồn dẫn."
      />

      <div className="nq-sop-copilot__grid">
        <section className="nq-sop-copilot__ask" aria-label="Đặt câu hỏi">
          {chips.length > 0 ? (
            <div className="nq-sop-copilot__chips">
              {chips.map((c) => (
                <button
                  key={c}
                  type="button"
                  className="nq-chip"
                  disabled={busy}
                  onClick={() => void ask(c)}
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
              onKeyDown={(e) => {
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void ask(q);
              }}
            />
          </Field>
          <Btn variant="primary" disabled={busy} onClick={() => void ask(q)}>
            {busy ? "Đang tra cẩm nang…" : "Hỏi cẩm nang"}
          </Btn>
          <p className="nq-sop-copilot__hint">Ctrl+Enter để gửi nhanh</p>

          {history.length > 0 ? (
            <div className="nq-sop-copilot__history">
              <p className="nq-sop-copilot__section-label">Câu gần đây</p>
              <div className="flex flex-wrap gap-2">
                {history.map((h) => (
                  <button
                    key={h}
                    type="button"
                    className="nq-chip"
                    disabled={busy}
                    onClick={() => void ask(h)}
                  >
                    {h.length > 48 ? `${h.slice(0, 48)}…` : h}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {error ? <Alert>{error}</Alert> : null}
        </section>

        <section className="nq-sop-copilot__answer" aria-label="Câu trả lời" ref={answerRef}>
          {busy && !a ? <Loading skeleton="text">Đang tra cẩm nang…</Loading> : null}
          {a ? (
            <article className="nq-item nq-sop-answer">
              <div className="nq-sop-copilot__answer-head">
                <StatusChip tone={a.chua_co ? "warn" : "ok"}>
                  {a.chua_co ? "Chưa có trong cẩm nang" : "Có trong cẩm nang"}
                </StatusChip>
                <StatusChip tone="default">{modeLabel(a.mode, a.provider)}</StatusChip>
                {!a.chua_co && typeof a.do_tin === "number" && a.do_tin > 0 ? (
                  <span className="nq-sop-copilot__confidence">
                    Tin cậy {Math.round(a.do_tin * 100)}%
                  </span>
                ) : null}
              </div>
              <p className="nq-sop-copilot__answer-text">
                {safeText(a.cau_tra_loi, "Cẩm nang chưa có câu trả lời cho câu này.")}
              </p>
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
                <div className="nq-sop-copilot__sources">
                  <p className="nq-sop-copilot__section-label">Nguồn dẫn</p>
                  <ul className="nq-sop-copilot__source-list">
                    {trichDan.map((t) => (
                      <li key={t}>
                        <span className="nq-sop-copilot__source-type">
                          {trichDanLabel(t, labelOpts).startsWith("Luật") ? "Luật" : "Phiếu"}
                        </span>
                        {trichDanLabel(t, labelOpts)}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="nq-item-sub">Chưa có nguồn dẫn kèm câu này.</p>
              )}
            </article>
          ) : (
            !busy &&
            !error && (
              <Empty>
                Chọn gợi ý hoặc gõ câu hỏi — câu trả lời hiện ở đây, kèm nguồn phiếu/luật.
              </Empty>
            )
          )}
        </section>
      </div>

      {luat.length > 0 ? (
        <section className="nq-sop-copilot__laws">
          <p className="nq-sop-copilot__section-label">Luật đang hiệu lực ({luat.length})</p>
          <div className="nq-sop-copilot__law-strip">
            {luat.slice(0, 6).map((l) => (
              <button
                key={l.id}
                type="button"
                className="nq-sop-copilot__law-pill"
                disabled={busy}
                onClick={() => void ask(safeText(l.cau, ""))}
              >
                <StatusChip tone="ok">{luatLabel(l.trang_thai)}</StatusChip>
                <span className="nq-clamp-2">{safeText(l.cau, "Luật")}</span>
              </button>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
