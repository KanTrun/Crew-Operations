"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { maskCode, viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Hint,
  MaskedCode,
  Notice,
  OpsCard,
  PageHeader,
} from "../../ui/kit";
import { PersonSelect, ShiftSelect } from "../../ui/ops-pickers";
import { CopilotPane } from "../../ui/copilot/CopilotPane";

export default function QrPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [nv, setNv] = useState("");
  const [ca, setCa] = useState("");
  const [issued, setIssued] = useState("");
  const [useTok, setUseTok] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copilotOpen, setCopilotOpen] = useState(false);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
  }, []);

  async function issue(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    if (!nv.trim() || !ca.trim()) {
      setError("Chọn nhân viên và ca trước khi phát mã.");
      return;
    }
    setBusy(true);
    try {
      const d = await apiSend<{ token: string }>("/api/v1/qr", { nv_id: nv.trim(), ca_id: ca.trim() });
      setIssued(typeof d.token === "string" ? d.token : "");
      setMsg("Đã phát mã một lần. Bấm sao chép rồi gửi riêng cho nhân viên.");
    } catch (e) {
      setError(
        viError(e, {
          doing: "phát được mã điểm danh",
          forbidden: "Chỉ quản lý hoặc chủ quán phát được mã điểm danh.",
          missing: "Ca hoặc nhân viên không hợp lệ. Chọn lại từ danh sách.",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  async function useCode(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    if (!useTok.trim()) {
      setError("Dán mã một lần vào ô trước khi bấm điểm danh.");
      return;
    }
    setBusy(true);
    try {
      await apiSend(`/api/v1/qr/${encodeURIComponent(useTok.trim())}`);
      setMsg("Đã điểm danh xong. Mã vừa dùng không dùng lại được nữa.");
      setUseTok("");
    } catch (e) {
      setError(
        viError(e, {
          doing: "điểm danh bằng mã này",
          missing: "Mã không đúng hoặc đã dùng rồi. Nhờ quản lý phát mã mới.",
          conflict: "Mã này đã dùng rồi. Nhờ quản lý phát mã mới.",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="Một lần · hết hạn khi dùng"
        title="Điểm danh QR"
        meta="Quản lý chọn người và ca rồi phát mã; nhân viên dán mã để vào ca."
      />
      <Btn variant="ghost" onClick={() => setCopilotOpen(true)}>
        Hỏi trợ lý vận hành
      </Btn>
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      {manager ? (
        <OpsCard eyebrow="Việc của quản lý" title="Phát mã cho một ca">
          <form onSubmit={issue}>
            <PersonSelect value={nv} onChange={setNv} label="Nhân viên" />
            <ShiftSelect value={ca} onChange={setCa} label="Ca" hint="Chọn ca trên lịch tuần của quán." />
            <Hint>Mã chỉ dùng một lần. Sao chép và gửi riêng cho nhân viên — không chiếu lên màn hình chung.</Hint>
            <Btn type="submit" variant="primary" disabled={busy}>
              {busy ? "Đang phát mã…" : "Phát mã điểm danh"}
            </Btn>
          </form>
          {issued ? <MaskedCode code={issued} masked={maskCode(issued)} /> : null}
        </OpsCard>
      ) : (
        <Notice>Bạn dán mã để điểm danh. Quản lý hoặc chủ quán mới phát mã.</Notice>
      )}

      <OpsCard eyebrow="Việc của nhân viên" title="Dùng mã để điểm danh">
        <form onSubmit={useCode}>
          <label className="nq-field">
            <span className="nq-label">Mã một lần</span>
            <input
              className="nq-input"
              value={useTok}
              onChange={(e) => setUseTok(e.target.value)}
              autoComplete="off"
              placeholder="Dán mã quản lý gửi…"
            />
          </label>
          <Btn type="submit" variant="primary" disabled={busy}>
            {busy ? "Đang điểm danh…" : "Điểm danh vào ca"}
          </Btn>
        </form>
      </OpsCard>
      <CopilotPane open={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </div>
  );
}
