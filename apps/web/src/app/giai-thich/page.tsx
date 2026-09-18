"use client";

import { useEffect, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Field, Loading, OpsCard, PageHeader } from "../../ui/kit";

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

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page space-y-6">
      <PageHeader
        kicker="Self-Explaining System"
        title="Hệ thống tự giải thích"
        meta="Hỏi 'tại sao' bằng ngôn ngữ tự nhiên — nhận câu trả lời tất định, có bằng chứng truy vết."
      />

      {error && <Alert kind="err">{error}</Alert>}

      <OpsCard title="Truy vết nhân quả">
        <div className="space-y-4">
          <Field label="Câu hỏi 'tại sao'">
            <input
              type="text"
              value={cauHoi}
              onChange={(e) => setCauHoi(e.target.value)}
              className="bg-neutral-800 text-white text-sm p-2 rounded border border-neutral-700 w-full"
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
          <div className="nq-card p-4 mb-4 bg-emerald-950/40 border-emerald-800/60">
            <p className="font-bold text-emerald-300">{chain.ket_luan}</p>
          </div>
          <div className="space-y-2">
            {chain.nodes.map((n) => (
              <div key={n.node_id} className="nq-card p-3 flex items-center justify-between gap-2">
                <div>
                  <span className="text-xs font-mono px-2 py-0.5 rounded bg-neutral-800 text-neutral-300 border border-neutral-700 mr-2">
                    {n.loai}
                  </span>
                  <span className="text-sm">{n.mo_ta}</span>
                </div>
                <span className="text-xs font-mono text-[var(--nq-ink-muted)]">{n.nguon}</span>
              </div>
            ))}
          </div>
        </OpsCard>
      )}

      <OpsCard title={`Lịch sử truy vết (${chains.length})`}>
        {chains.length === 0 ? (
          <Empty>Chưa có truy vết nào.</Empty>
        ) : (
          <div className="space-y-3">
            {chains.map((c) => (
              <div key={c.chain_id} className="nq-card p-4">
                <h4 className="font-bold">{c.cau_hoi}</h4>
                <p className="text-sm text-emerald-300 mt-1">{c.ket_luan}</p>
              </div>
            ))}
          </div>
        )}
      </OpsCard>
    </div>
  );
}