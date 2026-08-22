"use client";

import { FormEvent, useEffect, useState } from "react";
import { apiSend } from "../../lib/api";
import { getToken, isManager } from "../../lib/session";
import { Alert, AuthGate, btnPrimary, Field, inputStyle, Kicker } from "../../ui/kit";

export default function QrPage() {
  const [token, setToken] = useState("");
  const [nv, setNv] = useState("nv_03");
  const [ca, setCa] = useState("w1_c01");
  const [issued, setIssued] = useState("");
  const [useTok, setUseTok] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setToken(getToken());
  }, []);

  async function issue(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const d = await apiSend<{ token: string }>("/api/v1/qr", { nv_id: nv, ca_id: ca });
      setIssued(d.token);
      setMsg("Mã một lần đã tạo. Đưa nhân viên quét hoặc dán bên dưới.");
    } catch {
      setError("Chỉ quản lý phát mã.");
    }
  }

  async function useCode(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiSend(`/api/v1/qr/${useTok}`);
      setMsg("Đã điểm danh. Mã không dùng lại được.");
    } catch {
      setError("Mã không đúng hoặc đã dùng.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <Kicker>Một lần · hết hạn khi dùng</Kicker>
      <h1>Điểm danh QR</h1>
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}
      {isManager() ? (
        <form onSubmit={issue}>
          <Field label="Mã nhân viên">
            <input value={nv} onChange={(e) => setNv(e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Mã ca">
            <input value={ca} onChange={(e) => setCa(e.target.value)} style={inputStyle} />
          </Field>
          <button type="submit" style={btnPrimary}>
            Phát mã
          </button>
        </form>
      ) : (
        <p className="nq-muted">Nhân viên chỉ dùng mã. Quản lý phát mã.</p>
      )}
      {issued ? (
        <p className="nq-item" style={{ marginTop: "1rem", fontFamily: "var(--nq-font-mono)", wordBreak: "break-all" }}>
          {issued}
        </p>
      ) : null}
      <h2>Dùng mã</h2>
      <form onSubmit={useCode}>
        <Field label="Mã một lần">
          <input value={useTok} onChange={(e) => setUseTok(e.target.value)} style={inputStyle} />
        </Field>
        <button type="submit" style={btnPrimary}>
          Điểm danh
        </button>
      </form>
    </div>
  );
}
