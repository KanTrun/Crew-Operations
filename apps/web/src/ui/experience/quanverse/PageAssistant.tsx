"use client";

/**
 * PageAssistant — panel dùng chung cho cả 5 trang Quánverse.
 *
 * Hai tab, và thứ tự này là CHỦ ĐÍCH:
 *   1. "Tóm tắt trang" — đọc `QuanverseBrief` (số do máy chủ tính, KHÔNG LLM).
 *      Luôn hiển thị được, kể cả khi không có API key. Đây là phần trả lời câu
 *      hỏi "trang này để làm gì, hôm nay có gì".
 *   2. "Hỏi trang này" — gửi câu hỏi tới `/ask`. Câu trả lời mang `grounded`
 *      + `citations`; khi KHÔNG có trích dẫn, UI nói rõ chứ không trình bày như
 *      kết luận (cùng hợp đồng với `VoiceDock`).
 *
 * Vì sao tách panel khỏi từng trang: cả 5 trang trước đây không có chỗ nào nói
 * "chuyện gì đang xảy ra" — người dùng phải tự đọc số. Một panel dùng chung giữ
 * cách trình bày nhất quán và chỉ có MỘT nơi phải sửa khi luật bằng chứng đổi.
 */

import { useCallback, useEffect, useRef, useState } from "react";

import { viError } from "../../../lib/present";
import { Icon } from "../../icons";
import {
  quanverseAsk,
  quanverseBrief,
  type QuanverseAskResponse,
  type QuanverseBrief,
  type QuanversePageId,
} from "../experience-api";

type Tab = "summary" | "ask";

interface Props {
  page: QuanversePageId;
  /** Số liệu đã có trên trang (nếu trang tự tải) — panel không tải lại lần hai. */
  brief?: QuanverseBrief | null;
  /** Tiêu đề panel; mặc định nói rõ đây là gì. */
  title?: string;
}

const TONE_CLASS: Record<string, string> = {
  ok: "nq-brief-metric--ok",
  warn: "nq-brief-metric--warn",
  danger: "nq-brief-metric--danger",
  default: "",
};

function formatMetricValue(value: number | null, unit: string): string {
  // `null` = CHƯA CÓ DỮ LIỆU → "—", tuyệt đối không in "0".
  if (value === null) return "—";
  const text = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return unit ? `${text} ${unit}` : text;
}

export default function PageAssistant({ page, brief: briefProp = null, title }: Props) {
  const [tab, setTab] = useState<Tab>("summary");
  const [brief, setBrief] = useState<QuanverseBrief | null>(briefProp);
  const [briefError, setBriefError] = useState<string | null>(null);
  const [briefBusy, setBriefBusy] = useState(false);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<QuanverseAskResponse | null>(null);
  const [askBusy, setAskBusy] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const loadBrief = useCallback(async () => {
    setBriefBusy(true);
    setBriefError(null);
    try {
      setBrief(await quanverseBrief(page));
    } catch (e) {
      setBriefError(viError(e, { doing: "đọc tóm tắt trang" }));
    } finally {
      setBriefBusy(false);
    }
  }, [page]);

  useEffect(() => {
    if (briefProp) {
      setBrief(briefProp);
      return;
    }
    void loadBrief();
  }, [briefProp, loadBrief]);

  // Đổi trang → bỏ câu trả lời cũ: câu trả lời gắn với MỘT trang, giữ lại là sai.
  useEffect(() => {
    setAnswer(null);
    setAskError(null);
    setQuestion("");
  }, [page]);

  async function ask() {
    const text = question.trim();
    if (!text) return;
    setAskBusy(true);
    setAskError(null);
    try {
      setAnswer(await quanverseAsk(page, text));
    } catch (e) {
      setAskError(viError(e, { doing: "hỏi trợ lý Quánverse" }));
    } finally {
      setAskBusy(false);
    }
  }

  const metrics = brief?.metrics ?? [];

  return (
    <section className="nq-assistant" data-testid="page-assistant" aria-label="Trợ lý Quánverse">
      <div className="nq-assistant__head">
        <Icon name="bot" size={16} />
        <h2 className="nq-assistant__title">{title ?? "Trợ lý Quánverse"}</h2>
        <span className="nq-assistant__spacer" />
        <div className="nq-assistant__tabs" role="group" aria-label="Chế độ trợ lý">
          <button
            type="button"
            className={`nq-assistant__tab${tab === "summary" ? " is-on" : ""}`}
            data-testid="assistant-tab-summary"
            aria-pressed={tab === "summary"}
            onClick={() => setTab("summary")}
          >
            Tóm tắt trang
          </button>
          <button
            type="button"
            className={`nq-assistant__tab${tab === "ask" ? " is-on" : ""}`}
            data-testid="assistant-tab-ask"
            aria-pressed={tab === "ask"}
            onClick={() => {
              setTab("ask");
              inputRef.current?.focus();
            }}
          >
            Hỏi trang này
          </button>
        </div>
      </div>

      {briefError ? (
        <div className="nq-alert nq-alert--error" role="alert">
          {briefError}
          <button type="button" className="nq-linkbtn" onClick={() => void loadBrief()}>
            Thử lại
          </button>
        </div>
      ) : null}

      {tab === "summary" ? (
        <div className="nq-brief" data-testid="brief-body">
          {briefBusy && !brief ? (
            <p className="nq-assistant__hint">Đang tổng hợp số liệu của trang…</p>
          ) : null}

          {brief ? (
            <>
              <p className="nq-brief__headline" data-testid="brief-headline">
                {brief.headline}
              </p>

              {metrics.length ? (
                <ul className="nq-brief__metrics" data-testid="brief-metrics">
                  {metrics.map((m) => (
                    <li
                      key={m.key}
                      className={`nq-brief-metric ${TONE_CLASS[m.tone] ?? ""}`.trim()}
                      data-metric={m.key}
                    >
                      <span className="nq-brief-metric__value">
                        {formatMetricValue(m.value, m.unit)}
                      </span>
                      <span className="nq-brief-metric__label">{m.label}</span>
                    </li>
                  ))}
                </ul>
              ) : null}

              {brief.risks.length ? (
                <div className="nq-brief__block nq-brief__block--risk">
                  <p className="nq-brief__block-title">Điểm cần chú ý</p>
                  <ul className="nq-brief__list" data-testid="brief-risks">
                    {brief.risks.map((r, i) => (
                      <li key={i}>{r}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="nq-brief__ok" data-testid="brief-no-risk">
                  Chưa thấy điểm bất thường nào trên trang này.
                </p>
              )}

              {brief.facts.length ? (
                <div className="nq-brief__block">
                  <p className="nq-brief__block-title">Dữ kiện</p>
                  <ul className="nq-brief__list" data-testid="brief-facts">
                    {brief.facts.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {brief.next_actions.length ? (
                <div className="nq-brief__block">
                  <p className="nq-brief__block-title">Việc nên làm</p>
                  <ul className="nq-brief__list nq-brief__list--action" data-testid="brief-next">
                    {brief.next_actions.map((a, i) => (
                      <li key={i}>{a}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {brief.grounded_refs.length ? (
                <p className="nq-assistant__refs" data-testid="brief-refs">
                  {`Dựa trên ${brief.grounded_refs.length} bản ghi của hệ thống`}
                </p>
              ) : (
                <p className="nq-assistant__refs nq-assistant__refs--none" data-testid="brief-no-refs">
                  Chưa có bản ghi nào để dẫn chứng — số liệu có thể đang trống.
                </p>
              )}

              {brief.data_quality.length ? (
                <ul className="nq-brief__quality" data-testid="brief-quality">
                  {brief.data_quality.map((q, i) => (
                    <li key={i} className={`nq-brief__quality--${q.level}`}>
                      {q.message}
                    </li>
                  ))}
                </ul>
              ) : null}
            </>
          ) : null}
        </div>
      ) : (
        <div className="nq-assistant__ask">
          <div className="nq-assistant__input">
            <input
              ref={inputRef}
              type="text"
              value={question}
              data-testid="assistant-input"
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && void ask()}
              placeholder="Hỏi về trang này — ví dụ: 'có gì cần xử lý ngay?'"
              aria-label="Hỏi trợ lý Quánverse"
            />
            <button
              type="button"
              className="nq-btn nq-btn-primary"
              data-testid="assistant-ask"
              disabled={askBusy || !question.trim()}
              onClick={() => void ask()}
            >
              <Icon name="send" size={15} />
              {askBusy ? "Đang trả lời…" : "Hỏi"}
            </button>
          </div>

          {askError ? (
            <div className="nq-alert nq-alert--error" role="alert">
              {askError}
            </div>
          ) : null}

          {answer ? (
            <div className="nq-assistant__answer" data-testid="assistant-answer" aria-live="polite">
              <p className="nq-assistant__answer-text">{answer.answer}</p>

              {/* Trích dẫn CHỈ hiện khi thật sự có bản ghi. Sự VẮNG MẶT của khối
                  này là bằng chứng máy kiểm được rằng câu trả lời không có căn
                  cứ — cùng lý do đã ghi ở `VoiceDock`. */}
              {answer.citations.length ? (
                <p className="nq-assistant__citations" data-testid="assistant-citations">
                  {`Dựa trên ${answer.citations.length} bản ghi của hệ thống`}
                </p>
              ) : (
                <p className="nq-assistant__citations nq-assistant__citations--none" data-testid="assistant-no-citations">
                  Câu trả lời này chưa có bản ghi nào hậu thuẫn — chỉ nên tham khảo.
                </p>
              )}

              {answer.unsupported_claims.length ? (
                <p className="nq-assistant__guard" data-testid="assistant-guard">
                  {`Đã lọc ${answer.unsupported_claims.length} chi tiết không có trong dữ liệu.`}
                </p>
              ) : null}
            </div>
          ) : null}
        </div>
      )}
    </section>
  );
}
