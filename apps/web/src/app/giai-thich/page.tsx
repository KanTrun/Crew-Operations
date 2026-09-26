"use client";

import { useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Field, OpsCard, PageGrid, PageHeader, Pagination, usePaged } from "../../ui/kit";
import { AiInsightPanel } from "../../ui/ai/AiInsightPanel";
import { AskAiBox } from "../../ui/ai/AskAiBox";

interface CausalNode {
  node_id: string;
  loai: string;
  mo_ta: string;
  thoi_gian: string;
  nguon: string;
}

interface CausalLink {
  from_id: string;
  to_id: string;
  ly_do: string;
}

interface CausalChain {
  chain_id: string;
  cau_hoi: string;
  nodes: CausalNode[];
  links: CausalLink[];
  ket_luan: string;
}

const NODE_TYPE_LABEL: Record<string, string> = {
  su_kien: "Sự kiện",
  quyet_dinh: "Quyết định",
  luat: "Luật",
  ket_qua: "Kết quả",
};

const NODE_SOURCE_LABEL: Record<string, string> = {
  playbook: "Cẩm nang quán",
  audit: "Vết hệ thống",
  solver: "Máy xếp lịch",
};

export default function GiaiThichPage() {
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cauHoi, setCauHoi] = useState("Tại sao ca tối T6 có 2 pha chế?");
  const [chain, setChain] = useState<CausalChain | null>(null);
  const [chains, setChains] = useState<CausalChain[]>([]);

  useEffect(() => {
    setToken(getToken());
    loadChains();
  }, []);

  async function loadChains() {
    try {
      const res = await apiGet<{ items: CausalChain[] }>("/api/v1/ops/explain/chains");
      setChains(res.items || []);
    } catch (e) {
      setError(viError(e, { doing: "tải lịch sử giải thích" }));
    }
  }

  async function explain() {
    if (!cauHoi.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const res = await apiSend<{ ok: boolean; chain: CausalChain }>(
        "/api/v1/ops/explain",
        { cau_hoi: cauHoi.trim() }
      );
      if (res.ok) {
        setChain(res.chain);
        loadChains();
      }
    } catch (e) {
      setError(viError(e, { doing: "truy vết nhân quả" }));
    } finally {
      setBusy(false);
    }
  }

  const chainsPaged = usePaged(chains, 8);

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Self-Explaining System"
        title="Hệ thống tự giải thích"
        meta="Hỏi 'tại sao' bằng ngôn ngữ tự nhiên — nhận câu trả lời tất định, có bằng chứng truy vết."
      />

      {error && <Alert kind="err">{error}</Alert>}

      <PageGrid
        main={
          <>
            <OpsCard title="Truy vết nhân quả" density="compact">
              <div className="space-y-4">
                <Field label="Câu hỏi 'tại sao'">
                  <input
                    type="text"
                    value={cauHoi}
                    onChange={(e) => setCauHoi(e.target.value)}
                    className="nq-input"
                    placeholder="Tại sao ca tối T6 có 2 pha chế?"
                  />
                </Field>
                <Btn variant="primary" onClick={explain} disabled={busy}>
                  {busy ? "Đang truy vết..." : "Truy vết nhân quả"}
                </Btn>
              </div>
            </OpsCard>

            {chain && (
              <OpsCard title={`Kết luận: ${chain.cau_hoi}`}>
                <div className="nq-card p-4 mb-4 bg-[var(--nq-st-ok-soft)] border-[color-mix(in_srgb,var(--nq-st-ok)_46%,var(--nq-line))]">
                  <p className="font-bold text-[var(--nq-st-ok-ink)]">{chain.ket_luan}</p>
                </div>
                <div className="space-y-2">
                  {chain.nodes.map((n) => (
                    <div key={n.node_id} className="nq-card p-3 flex items-center justify-between gap-2">
                      <div>
                        <span className="text-xs px-2 py-0.5 rounded bg-[var(--nq-surface)] text-[var(--nq-ink)] border border-[var(--nq-line)] mr-2">
                          {NODE_TYPE_LABEL[n.loai] ?? n.loai}
                        </span>
                        <span className="text-sm">{n.mo_ta}</span>
                      </div>
                      <span className="text-xs text-[var(--nq-ink-muted)]">{NODE_SOURCE_LABEL[n.nguon] ?? n.nguon}</span>
                    </div>
                  ))}
                </div>
              </OpsCard>
            )}

            <OpsCard title="Lịch sử truy vết" count={chains.length} countLabel="câu hỏi">
              {chains.length === 0 ? (
                <Empty>Chưa có truy vết nào.</Empty>
              ) : (
                <>
                  <div className="space-y-3">
                    {chainsPaged.shown.map((c) => (
                      <div key={c.chain_id} className="nq-card p-4">
                        <h4 className="font-bold">{c.cau_hoi}</h4>
                        <p className="text-sm text-[var(--nq-st-ok-ink)] mt-1">{c.ket_luan}</p>
                      </div>
                    ))}
                  </div>
                  <Pagination
                    page={chainsPaged.page}
                    totalPages={chainsPaged.totalPages}
                    onChange={chainsPaged.setPage}
                    from={chainsPaged.from}
                    to={chainsPaged.to}
                    total={chainsPaged.total}
                  />
                </>
              )}
            </OpsCard>
          </>
        }
        aside={
          <>
            <AiInsightPanel page="giai-thich" />
            <AskAiBox page="giai-thich" />
          </>
        }
      />
    </div>
  );
}
