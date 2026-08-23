"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { maskCode, viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Field,
  Hint,
  inputStyle,
  MaskedCode,
  Notice,
  OpsCard,
  PageHeader,
} from "../../ui/kit";

export default function QrPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [nv, setNv] = useState("nv_03");
  const [ca, setCa] = useState("w1_c01");
  const [issued, setIssued] = useState("");
  const [useTok, setUseTok] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
  }, []);

  async function issue(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
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
          missing: "Mã nhân viên hoặc mã ca không có trong quán. Kiểm tra lại trên Lịch tuần.",
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
        meta="Quản lý phát mã dùng một lần, nhân viên dán mã để điểm danh vào ca."
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      {manager ? (
        <OpsCard eyebrow="Việc của quản lý" title="Phát mã cho một ca">
          <form onSubmit={issue}>
            <Field label="Mã nhân viên">
              <input value={nv} onChange={(e) => setNv(e.target.value)} style={inputStyle} />
            </Field>
            <Field label="Mã ca">
              <input value={ca} onChange={(e) => setCa(e.target.value)} style={inputStyle} />
            </Field>
            <Hint>Lấy mã nhân viên và mã ca trên Lịch tuần.</Hint>
            <Btn type="submit" variant="primary" disabled={busy}>
              {busy ? "Đang phát mã…" : "Phát mã điểm danh"}
            </Btn>
          </form>
          {/* Mã điểm danh là bí mật dùng-một-lần. In nguyên lên màn hình là để lộ
              credential cho bất cứ ai đứng cạnh quầy đọc được — chỉ hiện dạng che,
              nội dung thật đi qua clipboard. */}
          {issued ? <MaskedCode code={issued} masked={maskCode(issued)} /> : null}
        </OpsCard>
      ) : (
        <Notice>Bạn dán mã để điểm danh. Quản lý hoặc chủ quán mới phát mã.</Notice>
      )}

      <OpsCard eyebrow="Việc của nhân viên" title="Dùng mã để điểm danh">
        <form onSubmit={useCode}>
          <Field label="Mã một lần">
            <input
              value={useTok}
              onChange={(e) => setUseTok(e.target.value)}
              style={inputStyle}
              autoComplete="off"
            />
          </Field>
          <Btn type="submit" variant="primary" disabled={busy}>
            {busy ? "Đang điểm danh…" : "Điểm danh vào ca"}
          </Btn>
        </form>
      </OpsCard>
    </div>
  );
}
