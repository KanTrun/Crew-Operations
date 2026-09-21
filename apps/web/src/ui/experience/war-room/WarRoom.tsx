"use client";

/** War Room container — quản lý chọn preset, chạy simulate, propose. */

import { useCallback, useState } from "react";
import { eligibilityReasonLabel, proposalStatusLabel, warOptionTitle } from "../exp-present";
import CrisisRoom from "./CrisisRoom";
import ScenarioComparison from "./ScenarioComparison";
import ScenarioPicker from "./ScenarioPicker";
import {
  snapshotHashForScenario,
  type WarRoomOption,
  type WarRoomScenarioInput,
} from "./war-room-model";
import {
  warRoomPropose,
  warRoomSimulate,
} from "../experience-api";

type SimResult = {
  simulation_id: string;
  baseline_snapshot_hash: string;
  baseline: Record<string, string | number | boolean>;
  options: WarRoomOption[];
};

export default function WarRoom() {
  const [scenarios, setScenarios] = useState<WarRoomScenarioInput[]>([]);
  const [result, setResult] = useState<SimResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedOptionId, setSelectedOptionId] = useState<string | null>(null);
  const [evidenceOption, setEvidenceOption] = useState<WarRoomOption | null>(null);
  const [proposing, setProposing] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const toggleScenario = useCallback((scenario: WarRoomScenarioInput) => {
    setScenarios((prev) => {
      const exists = prev.some((s) => s.scenario_id === scenario.scenario_id);
      if (exists) return prev.filter((s) => s.scenario_id !== scenario.scenario_id);
      return [...prev, scenario];
    });
    setResult(null);
  }, []);

  const runPreset = useCallback((scenario: WarRoomScenarioInput) => {
    setScenarios([scenario]);
    setResult(null);
  }, []);

  const simulate = useCallback(async () => {
    if (scenarios.length < 2) {
      setError("Chọn ít nhất 2 kịch bản để so sánh.");
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const snap = snapshotHashForScenario(scenarios[0]);
      const resp = await warRoomSimulate({
        request_id: `wr_${Date.now()}`,
        baseline_snapshot: snap,
        scenarios,
        requested_by: "quan_ly_demo",
      });
      setResult({
        simulation_id: resp.simulation_id,
        baseline_snapshot_hash: resp.baseline_snapshot_hash,
        baseline: resp.baseline ?? {},
        options: resp.options ?? [],
      });
      setSelectedOptionId(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi khi chạy War Room");
    } finally {
      setBusy(false);
    }
  }, [scenarios]);

  const propose = useCallback(
    async (optionId: string) => {
      if (!result || !result.options?.length) return;
      const opt = result.options.find((o) => o.option_id === optionId);
      if (!opt) return;
      setProposing(true);
      setNotice(null);
      try {
        const res = await warRoomPropose(
          result.simulation_id,
          optionId,
          result.baseline_snapshot_hash,
        );
        setNotice(`Đã tạo đề xuất (${proposalStatusLabel(res.proposal.status)}). Chờ quản lý xác nhận — mô phỏng không đổi lịch thật.`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Lỗi khi tạo đề xuất");
      } finally {
        setProposing(false);
      }
    },
    [result],
  );

  return (
    <div className="nq-war">
      <header className="nq-war__header">
        <h1>War Room — Phòng điều hành</h1>
        <p>
          So sánh các phương án “nếu… thì…” dựa trên mô phỏng tất định. Không
          thay đổi lịch thật.
        </p>
      </header>

      {error ? <div className="nq-alert nq-alert--error">{error}</div> : null}
      {notice ? <div className="nq-alert nq-alert--info">{notice}</div> : null}

      <ScenarioPicker selected={scenarios} onToggle={toggleScenario} disabled={busy} />

      <div className="nq-war__actions">
        <button
          type="button"
          className="nq-btn nq-btn-primary"
          disabled={busy || scenarios.length < 2}
          onClick={simulate}
        >
          {busy ? "Đang mô phỏng…" : "Chạy mô phỏng"}
        </button>
      </div>

      {result ? (
        <ScenarioComparison
          baseline={result.baseline}
          options={result.options ?? []}
          selectedOptionId={selectedOptionId}
          onSelect={setSelectedOptionId}
          onPropose={propose}
          onShowEvidence={setEvidenceOption}
          proposing={proposing}
        />
      ) : null}

      <CrisisRoom onRunPreset={runPreset} busy={busy} />

      {evidenceOption ? (
        <div
          className="nq-drawer"
          role="dialog"
          aria-modal="true"
          aria-label="Vì sao phương án này"
        >
          <div className="nq-drawer__inner">
            <button
              type="button"
              className="nq-drawer__close"
              aria-label="Đóng"
              onClick={() => setEvidenceOption(null)}
            >
              ✕
            </button>
            <h2>Vì sao: {warOptionTitle(evidenceOption.option_id, evidenceOption.option_id)}</h2>
            <p className="nq-drawer__risk">Rủi ro: {evidenceOption.risk || "—"}</p>
            <h3>Nguồn dữ liệu</h3>
            <ul className="nq-drawer__refs">
              {(evidenceOption.evidence_refs ?? []).map(
                (ref: string, i: number) => (
                  <li key={i}>{ref}</li>
                ),
              )}
            </ul>
            {evidenceOption.constraint_violations?.length ? (
              <div className="nq-alert nq-alert--error">
                Ràng buộc cứng chưa đạt: {evidenceOption.constraint_violations.map(eligibilityReasonLabel).join("; ")}
              </div>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}