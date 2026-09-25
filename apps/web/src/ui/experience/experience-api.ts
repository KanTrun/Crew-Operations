/** Typed client cho Grand AI Experience API (Phase 02 War Room). */

import { apiGet, apiSend } from "../../lib/api";
import type {
  WarRoomComparison,
  WarRoomScenario,
  WarRoomOption,
} from "../../lib/contracts";
import type { WarRoomScenarioInput } from "./war-room/war-room-model";

export interface WarRoomSimulateRequest {
  request_id: string;
  baseline_snapshot: string;
  scenarios: WarRoomScenarioInput[];
  requested_by: string;
}

export interface WarRoomSimulateResponse extends WarRoomComparison {
  replayable: boolean;
  simulation_id: string;
  baseline_snapshot_hash: string;
  baseline: Record<string, string | number | boolean>;
  options: WarRoomOption[];
}

export interface WarRoomProposeResponse {
  proposal: {
    proposal_id: string;
    status: string;
    snapshot_hash: string;
    evidence_refs: string[];
  };
  status: string;
  replayable: boolean;
}

export function warRoomSimulate(
  req: WarRoomSimulateRequest,
): Promise<WarRoomSimulateResponse> {
  return apiSend<WarRoomSimulateResponse>(
    "/api/v1/experience/war-room/simulate",
    req,
  );
}

export function warRoomGetScenarios(
  simulationId: string,
): Promise<WarRoomComparison> {
  return apiGet<WarRoomComparison>(
    `/api/v1/experience/war-room/scenarios/${simulationId}`,
  );
}

export function warRoomPropose(
  simulationId: string,
  optionId: string,
  expectedSnapshotHash: string,
): Promise<WarRoomProposeResponse> {
  return apiSend<WarRoomProposeResponse>(
    `/api/v1/experience/war-room/${simulationId}/propose`,
    { option_id: optionId, expected_snapshot_hash: expectedSnapshotHash },
  );
}

export function warRoomConfirm(
  simulationId: string,
  optionId?: string,
): Promise<{ confirmed: boolean; mutation: string; treo_id?: string; note?: string }> {
  return apiSend(`/api/v1/experience/war-room/${simulationId}/confirm`, {
    option_id: optionId ?? null,
  });
}

export function formatVnd(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "—";
  }
  return new Intl.NumberFormat("vi-VN", {
    style: "currency",
    currency: "VND",
    maximumFractionDigits: 0,
  }).format(value);
}

export function optionLabel(option: { option_id: string }): string {
  return option.option_id;
}