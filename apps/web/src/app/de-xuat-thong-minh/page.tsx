"use client";

import { useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Loading, OpsCard, PageHeader } from "../../ui/kit";

interface SuccessPattern {
  pattern_id: string;
  loai: string;
  mo_ta: string;
  do_tin_cay: number;
  bang_chung: string[];
  nguon: string;
}

interface PositiveRule {
  id: string;
  cau: string;
  dieu_kien: Record<string, unknown>;
  bang_chung: string[];
  do_tin_cay: number;
  trang_thai: string;
}

export default function DeXuatThongMinhPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [patterns, setPatterns] = useState<SuccessPattern[]>([]);
  const [rules, setRules] = useState<PositiveRule[]>([]);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    loadSuggestions();
  }, []);

  async function loadSuggestions() {
    try {
      const res = await apiGet<{ suggestions: PositiveRule[]; patterns: SuccessPattern[] }>(
        "/api/v1/ops/predict/suggestions"
      );
      setRules(res.suggestions || []);
      setPatterns(res.patterns || []);
    } catch (e) {
      setError(viError(e, { doing: "tải đề xuất thông minh" }));
    }
  }

  async function runPredict() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await apiSend<{ ok: boolean; patterns: SuccessPattern[]; suggestions: PositiveRule[] }>(
        "/api/v1/ops/predict/run",
        {
          doanh_thu_by_ca: {
            T2_sang: 100, T2_chieu: 110, T2_toi: 105,
            T6_toi: 500, T7_toi: 480,
          },
          doanh_thu_by_mon: {},
          ton_kho_by_time: {},
        }
      );
      if (res.ok) {
        setPatterns(res.patterns || []);
        setRules(res.suggestions || []);
        setSuccess(`Đã phát hiện ${res.patterns.length} mẫu thành công, đề xuất ${res.suggestions.length} luật tích cực.`);
      }
    } catch (e) {
      setError(viError(e, { doing: "chạy phát hiện mẫu thành công" }));
    } finally {
      setBusy(false);
    }
  }

  async function approveRule(id: string) {
    setBusy(true);
    setError(null);
    try {
      await apiSend(`/api/v1/ops/predict/${encodeURIComponent(id)}/approve`, null, "POST");
      setSuccess("Đã duyệt luật tích cực!");
      loadSuggestions();
    } catch (e) {
      setError(viError(e, { doing: "duyệt luật tích cực" }));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page space-y-6">
      <PageHeader
        kicker="Predictive Playbook"
        title="Đề xuất thông minh"
        meta="Hệ thống tự phát hiện mẫu thành công và đề xuất luật tích cực — luôn cần người duyệt."
      />

      {error && <Alert kind="err">{error}</Alert>}
      {success && <Alert kind="ok">{success}</Alert>}

      <OpsCard title="Phát hiện mẫu thành công">
        <p className="nq-muted text-sm mb-4">
          Chạy phân tích dữ liệu lịch sử để tìm ca doanh thu cao, món bán chạy, giờ cao điểm.
        </p>
        <Btn variant="primary" onClick={runPredict} disabled={busy}>
          {busy ? "Đang phân tích..." : "Chạy phát hiện mẫu thành công"}
        </Btn>
      </OpsCard>

      <OpsCard title={`Mẫu thành công (${patterns.length})`}>
        {patterns.length === 0 ? (
          <Empty>Chưa có mẫu thành công. Bấm "Chạy phát hiện" để bắt đầu.</Empty>
        ) : (
          <div className="space-y-3">
            {patterns.map((p) => (
              <div key={p.pattern_id} className="nq-card p-4">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-bold">{p.mo_ta}</h4>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-800/60">
                    {Math.round(p.do_tin_cay * 100)}%
                  </span>
                </div>
                <p className="text-xs font-mono text-[var(--nq-ink-muted)] mt-1">
                  Loại: {p.loai} · Nguồn: {p.nguon}
                </p>
              </div>
            ))}
          </div>
        )}
      </OpsCard>

      <OpsCard title={`Luật tích cực đề xuất (${rules.length})`}>
        {rules.length === 0 ? (
          <Empty>Chưa có luật tích cực.</Empty>
        ) : (
          <div className="space-y-3">
            {rules.map((r) => (
              <div key={r.id} className="nq-card p-4">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-bold">{r.cau}</h4>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 border border-neutral-700">
                    {r.trang_thai}
                  </span>
                </div>
                <p className="text-xs font-mono text-[var(--nq-ink-muted)] mt-1">
                  Độ tin cậy: {Math.round(r.do_tin_cay * 100)}% · Bằng chứng: {r.bang_chung.join(", ")}
                </p>
                {manager && r.trang_thai === "de_xuat" && (
                  <div className="mt-3">
                    <Btn variant="primary" onClick={() => approveRule(r.id)} disabled={busy}>
                      Duyệt luật
                    </Btn>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </OpsCard>
    </div>
  );
}