"use client";

/** Shift Rescue panel — báo vắng → danh sách người bù → propose/invite/confirm. */

import { useCallback, useState } from "react";
import { rescueStatusLabel } from "../exp-present";
import CandidateCard from "./CandidateCard";

interface Candidate {
  candidate_id: string;
  nv_id: string;
  nv_ten: string;
  safe: boolean;
  reason_passes: string[];
  reason_blocks: string[];
  fairness_delta: number;
  added_hours: number;
  skill_coverage: Record<string, boolean>;
  rank?: number;
}

interface CaseView {
  case_id: string;
  status: string;
  candidates: Candidate[];
  blocked: Candidate[];
  invited: string[];
}

export default function ShiftRescuePanel() {
  const [caseId, setCaseId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [caze, setCaze] = useState<CaseView | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const api = useCallback(
    async <T,>(path: string, body?: unknown, method = "POST"): Promise<T> => {
      const token =
        window.sessionStorage.getItem("nq_token") ||
        window.localStorage.getItem("nq_token") ||
        "";
      const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
      const res = await fetch(`${base}/api/v1${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error((detail as { detail?: string }).detail || `api_${res.status}`);
      }
      return (await res.json()) as T;
    },
    [],
  );

  const intake = useCallback(async () => {
    setBusy(true);
    setError(null);
    setCaze(null);
    setNotice(null);
    try {
      const res = await api<{ case_id: string }>(
        "/experience/shift-rescue/intake",
        {
          case_id: `rescue_demo_${Date.now()}`,
          absence_nv_id: "nv_absent_quan",
          shift_id: "t7_toi",
          reason: "Ốm đột xuất",
        },
      );
      setCaseId(res.case_id);
      await findCandidates(res.case_id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi intake");
    } finally {
      setBusy(false);
    }
  }, [api]);

  const findCandidates = useCallback(
    async (id: string) => {
      try {
        await api(`/experience/shift-rescue/${id}/candidates`);
        const view = await api<CaseView>(`/experience/shift-rescue/${id}`, undefined, "GET");
        setCaze(view);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Lỗi tìm người bù");
      }
    },
    [api],
  );

  const proposeAndInvite = useCallback(
    async (candidateId: string) => {
      if (!caseId) return;
      setBusy(true);
      setError(null);
      setNotice(null);
      try {
        await api(`/experience/shift-rescue/${caseId}/propose`, { candidate_id: candidateId });
        const inv = await api<{ invited: string[] }>(
          `/experience/shift-rescue/${caseId}/invite`,
          { candidate_ids: [candidateId] },
        );
        setSelected(candidateId);
        setNotice(`Đã mời ${candidateId}. Chờ phản hồi.`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Lỗi propose/invite");
      } finally {
        setBusy(false);
      }
    },
    [api, caseId],
  );

  return (
    <div className="nq-rescue">
      <header className="nq-rescue__header">
        <h1>AI Shift Rescue</h1>
        <p>Báo vắng đột xuất → danh sách người thay an toàn theo ràng buộc thật.</p>
      </header>

      {error ? <div className="nq-alert nq-alert--error">{error}</div> : null}
      {notice ? <div className="nq-alert nq-alert--info">{notice}</div> : null}

      <div className="nq-rescue__actions">
        <button
          type="button"
          className="nq-btn nq-btn--primary"
          data-testid="rescue-intake"
          disabled={busy}
          onClick={intake}
        >
          {busy ? "Đang xử lý…" : "Báo vắng (fixture: Quân ca tối T7)"}
        </button>
      </div>

      {caze ? (
        <div className="nq-rescue__case">
          <p className="nq-rescue__status">Trạng thái: {rescueStatusLabel(caze.status)}</p>
          <h2>An toàn ({caze.candidates.length})</h2>
          <div className="nq-rescue__cards">
            {caze.candidates.map((c) => (
              <CandidateCard
                key={c.candidate_id}
                candidate={c}
                onSelect={() => proposeAndInvite(c.candidate_id)}
                disabled={busy || (caze.invited ?? []).length > 0}
                selected={selected === c.candidate_id}
              />
            ))}
          </div>
          {caze.blocked?.length ? (
            <>
              <h2>Bị chặn ({caze.blocked.length})</h2>
              <div className="nq-rescue__cards">
                {caze.blocked.map((c) => (
                  <CandidateCard key={c.candidate_id} candidate={c} blocked />
                ))}
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}