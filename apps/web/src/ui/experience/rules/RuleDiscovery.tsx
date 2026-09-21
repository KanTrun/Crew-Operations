"use client";

/** Rule Discovery — quán tự viết luật: evidence first → sentence → shadow → confirm. */

import { useCallback, useState } from "react";
import { proposalStatusLabel } from "../exp-present";
import { RoleChip } from "../exp-kit";
import RuleEvidenceDrawer from "./RuleEvidenceDrawer";
import RuleShadowResult from "./RuleShadowResult";

interface CandidateItem {
  candidate_id: string;
  sentence: string;
  confidence: number;
  status: string;
  shadow_result?: Record<string, unknown> | null;
}

interface EvidenceView {
  candidate_id: string;
  repeated_decisions: number;
  actors: string[];
  affected_shifts: string[];
  counterexamples: string[];
  confidence: number;
}

export default function RuleDiscovery() {
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [evidenceFor, setEvidenceFor] = useState<string | null>(null);
  const [shadowFor, setShadowFor] = useState<string | null>(null);

  const token =
    (typeof window !== "undefined" &&
      (window.sessionStorage.getItem("nq_token") ||
        window.localStorage.getItem("nq_token"))) ||
    "";
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

  const api = useCallback(
    async <T,>(path: string, method = "GET"): Promise<T> => {
      const res = await fetch(`${base}/api/v1${path}`, {
        method,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error((d as { detail?: string }).detail || `api_${res.status}`);
      }
      return (await res.json()) as T;
    },
    [base, token],
  );

  const discover = useCallback(async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const res = await api<{ discovered: string[]; count: number }>(
        "/experience/rules/discover",
        "POST",
      );
      setNotice(`Đã tìm ${res.count} ứng viên luật từ quyết định lặp lại (fixture).`);
      const list = await api<{ candidates: CandidateItem[] }>("/experience/rules/candidates");
      setCandidates(list.candidates);
      setShadowFor(res.discovered[0] ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi discover");
    } finally {
      setBusy(false);
    }
  }, [api]);

  const runShadow = useCallback(
    async (candidateId: string) => {
      setBusy(true);
      setError(null);
      try {
        const res = await api<{ shadow: Record<string, unknown> }>(
          `/experience/rules/${candidateId}/shadow-test`,
          "POST",
        );
        setCandidates((prev) =>
          prev.map((c) =>
            c.candidate_id === candidateId ? { ...c, shadow_result: res.shadow } : c,
          ),
        );
      } catch (e) {
        setError(e instanceof Error ? e.message : "Lỗi shadow test");
      } finally {
        setBusy(false);
      }
    },
    [api],
  );

  const confirm = useCallback(
    async (candidateId: string) => {
      setBusy(true);
      setError(null);
      setNotice(null);
      try {
        const res = await api<{ playbook_status: string; not_auto_activated: boolean }>(
          `/experience/rules/${candidateId}/confirm`,
          "POST",
        );
        setNotice(
          `Luật đã vào vòng đời playbook (${res.playbook_status}). AI đề xuất, quản lý quyết định — chưa tự kích hoạt.`,
        );
        setCandidates((prev) =>
          prev.map((c) =>
            c.candidate_id === candidateId ? { ...c, status: res.playbook_status } : c,
          ),
        );
      } catch (e) {
        setError(e instanceof Error ? e.message : "Lỗi confirm");
      } finally {
        setBusy(false);
      }
    },
    [api],
  );

  const reject = useCallback(
    async (candidateId: string) => {
      setBusy(true);
      setError(null);
      setNotice(null);
      try {
        await api(`/experience/rules/${candidateId}/reject`, "POST");
        setNotice(`Đã từ chối ứng viên ${candidateId}.`);
        setCandidates((prev) =>
          prev.map((c) => (c.candidate_id === candidateId ? { ...c, status: "rejected" } : c)),
        );
      } catch (e) {
        setError(e instanceof Error ? e.message : "Lỗi reject");
      } finally {
        setBusy(false);
      }
    },
    [api],
  );

  return (
    <div className="nq-rules">
      <header className="nq-rules__header">
        <h1>Quán tự viết luật</h1>
        <p>AI phát hiện quyết định lặp lại → đề xuất luật rõ ràng → quản lý quyết định.</p>
      </header>

      {error ? <div className="nq-alert nq-alert--error">{error}</div> : null}
      {notice ? <div className="nq-alert nq-alert--info">{notice}</div> : null}

      <div className="nq-rules__actions">
        <button
          type="button"
          className="nq-btn nq-btn-primary"
          data-testid="rules-discover"
          disabled={busy}
          onClick={discover}
        >
          {busy ? "Đang xử lý…" : "Tìm quyết định lặp lại"}
        </button>
      </div>

      <ul className="nq-rules__list">
        {candidates.map((c) => (
          <li key={c.candidate_id} className="nq-rules__item">
            <p className="nq-rules__sentence">{c.sentence}</p>
            <p className="nq-rules__meta">
              {proposalStatusLabel(c.status)} · độ tin cậy {(c.confidence * 100).toFixed(0)}%
            </p>
            {c.shadow_result ? <RuleShadowResult result={c.shadow_result} /> : null}
            <div className="nq-rules__actions-row">
              <button
                type="button"
                className="nq-btn"
                data-testid="evidence-btn"
                onClick={() => setEvidenceFor(c.candidate_id)}
              >
                Xem bằng chứng
              </button>
              <button
                type="button"
                className="nq-btn"
                data-testid="shadow-btn"
                disabled={busy}
                onClick={() => runShadow(c.candidate_id)}
              >
                Chạy shadow test
              </button>
              <button
                type="button"
                className="nq-btn nq-btn-primary"
                data-testid="confirm-btn"
                disabled={busy || !c.shadow_result}
                onClick={() => confirm(c.candidate_id)}
              >
                Xác nhận
              </button>
              <button
                type="button"
                className="nq-btn nq-btn-ghost"
                data-testid="reject-btn"
                disabled={busy}
                onClick={() => reject(c.candidate_id)}
              >
                Từ chối
              </button>
            </div>
              <RoleChip label="Đề xuất từ dữ liệu quán" />
          </li>
        ))}
      </ul>

      {evidenceFor ? (
        <RuleEvidenceDrawer
          candidateId={evidenceFor}
          onClose={() => setEvidenceFor(null)}
        />
      ) : null}
    </div>
  );
}