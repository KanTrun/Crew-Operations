"use client";

import { useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Field, Loading, OpsCard, PageHeader } from "../../ui/kit";
import { Icon } from "../../ui/icons";

interface TwinScenario {
  scenario_id: string;
  loai: string;
  tham_so: Record<string, unknown>;
  baseline: Record<string, unknown>;
  ket_qua: Record<string, unknown>;
  rui_ro: string;
}

export default function ThuNghiemAnToanPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [scenarios, setScenarios] = useState<TwinScenario[]>([]);

  // Form state
  const [loai, setLoai] = useState("tang_gia");
  const [giaCu, setGiaCu] = useState("25000");
  const [giaMoi, setGiaMoi] = useState("30000");
  const [luongCu, setLuongCu] = useState("100");
  const [chiPhi, setChiPhi] = useState("50000");
  const [doanhThuTang, setDoanhThuTang] = useState("200000");
  const [chiPhiNhanSu, setChiPhiNhanSu] = useState("150000");

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    loadScenarios();
  }, []);

  async function loadScenarios() {
    try {
      const res = await apiGet<{ items: TwinScenario[] }>("/api/v1/ops/twin/scenarios");
      setScenarios(res.items || []);
    } catch (e) {
      setError(viError(e, { doing: "tải kịch bản mô phỏng" }));
    }
  }

  async function simulate() {
    setBusy(true);
    setError(null);
    setSuccess(null);
    let thamSo: Record<string, unknown> = {};
    if (loai === "tang_gia" || loai === "giam_gia") {
      thamSo = {
        gia_cu: Number(giaCu),
        gia_moi: Number(giaMoi),
        luong_ban_cu: Number(luongCu),
        chi_phi_bien_doi: Number(chiPhi),
        he_so_co_gian: -0.5,
      };
    } else if (loai === "them_nhan_su" || loai === "bot_nhan_su") {
      thamSo = {
        doanh_thu_tang_them: Number(doanhThuTang),
        chi_phi_nhan_su: Number(chiPhiNhanSu),
      };
    }
    try {
      const res = await apiSend<{ ok: boolean; scenario: TwinScenario }>(
        "/api/v1/ops/twin/simulate",
        {
          scenario_id: `sc_${Date.now().toString().slice(-6)}`,
          loai,
          tham_so: thamSo,
        }
      );
      if (res.ok) {
        setSuccess("Mô phỏng hoàn tất!");
        loadScenarios();
      }
    } catch (e) {
      setError(viError(e, { doing: "chạy mô phỏng" }));
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page space-y-6">
      <PageHeader
        kicker="Digital Twin"
        title="Thử nghiệm an toàn"
        meta="Mô phỏng 'nếu... thì...' trên bản sao số trước khi áp dụng thật."
      />

      {error && <Alert kind="err">{error}</Alert>}
      {success && <Alert kind="ok">{success}</Alert>}

      <OpsCard title="Chạy mô phỏng">
        <div className="space-y-4">
          <Field label="Loại kịch bản">
            <select
              value={loai}
              onChange={(e) => setLoai(e.target.value)}
              className="bg-[var(--nq-surface)] text-white text-sm p-2 rounded border border-[var(--nq-line)]"
            >
              <option value="tang_gia">Tăng giá</option>
              <option value="giam_gia">Giảm giá</option>
              <option value="them_nhan_su">Thêm nhân sự</option>
              <option value="bot_nhan_su">Bớt nhân sự</option>
            </select>
          </Field>

          {(loai === "tang_gia" || loai === "giam_gia") && (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Giá cũ (đ)">
                <input type="number" value={giaCu} onChange={(e) => setGiaCu(e.target.value)} className="bg-[var(--nq-surface)] text-white text-sm p-2 rounded border border-[var(--nq-line)]" />
              </Field>
              <Field label="Giá mới (đ)">
                <input type="number" value={giaMoi} onChange={(e) => setGiaMoi(e.target.value)} className="bg-[var(--nq-surface)] text-white text-sm p-2 rounded border border-[var(--nq-line)]" />
              </Field>
              <Field label="Lượng bán cũ">
                <input type="number" value={luongCu} onChange={(e) => setLuongCu(e.target.value)} className="bg-[var(--nq-surface)] text-white text-sm p-2 rounded border border-[var(--nq-line)]" />
              </Field>
              <Field label="Chi phí biến đổi (đ)">
                <input type="number" value={chiPhi} onChange={(e) => setChiPhi(e.target.value)} className="bg-[var(--nq-surface)] text-white text-sm p-2 rounded border border-[var(--nq-line)]" />
              </Field>
            </div>
          )}

          {(loai === "them_nhan_su" || loai === "bot_nhan_su") && (
            <div className="grid grid-cols-2 gap-3">
              <Field label="Doanh thu tăng thêm (đ)">
                <input type="number" value={doanhThuTang} onChange={(e) => setDoanhThuTang(e.target.value)} className="bg-[var(--nq-surface)] text-white text-sm p-2 rounded border border-[var(--nq-line)]" />
              </Field>
              <Field label="Chi phí nhân sự (đ)">
                <input type="number" value={chiPhiNhanSu} onChange={(e) => setChiPhiNhanSu(e.target.value)} className="bg-[var(--nq-surface)] text-white text-sm p-2 rounded border border-[var(--nq-line)]" />
              </Field>
            </div>
          )}

          <Btn variant="primary" onClick={simulate} disabled={busy}>
            {busy ? "Đang mô phỏng..." : "Chạy mô phỏng"}
          </Btn>
        </div>
      </OpsCard>

      <OpsCard title={`Kịch bản đã chạy (${scenarios.length})`}>
        {scenarios.length === 0 ? (
          <Empty>Chưa có kịch bản nào.</Empty>
        ) : (
          <div className="space-y-3">
            {scenarios.map((s) => (
              <div key={s.scenario_id} className="nq-card p-4">
                <div className="flex items-center justify-between gap-2">
                  <h4 className="font-bold">{s.loai}</h4>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-[var(--nq-surface)] text-[var(--nq-ink)] border border-[var(--nq-line)]">
                    {s.scenario_id}
                  </span>
                </div>
                <pre className="text-xs font-mono text-[var(--nq-ink-muted)] mt-2 whitespace-pre-wrap">
                  {JSON.stringify(s.ket_qua, null, 2)}
                </pre>
                {s.rui_ro && (
                  <p className="text-xs text-[var(--nq-st-warn-ink)] mt-2 flex items-start gap-1.5">
                <Icon name="warn" size={13} />
                <span>{s.rui_ro}</span>
              </p>
                )}
              </div>
            ))}
          </div>
        )}
      </OpsCard>
    </div>
  );
}