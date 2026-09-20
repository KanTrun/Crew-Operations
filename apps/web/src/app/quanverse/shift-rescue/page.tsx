"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { getToken, isManager } from "../../../lib/session";
import { AuthGate, Loading } from "../../../ui/kit";

const ShiftRescuePanel = dynamic(
  () => import("../../../ui/experience/shift-rescue/ShiftRescuePanel"),
  { ssr: false, loading: () => <Loading>Đang tải Shift Rescue…</Loading> },
);

export default function ShiftRescuePage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    setReady(true);
  }, []);

  if (!ready) return <Loading>Đang kiểm tra phiên…</Loading>;
  if (!token) return <AuthGate />;
  if (!manager) {
    return (
      <div className="nq-alert nq-alert--error" role="alert">
        Shift Rescue yêu cầu vai trò Quản lý hoặc Chủ quán.
      </div>
    );
  }
  return <ShiftRescuePanel />;
}