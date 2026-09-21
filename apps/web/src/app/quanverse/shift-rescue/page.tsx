"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { getToken, isManager } from "../../../lib/session";
import { AuthGate } from "../../../ui/kit";
import { ExpSkeleton } from "../../../ui/experience/exp-kit";

const ShiftRescuePanel = dynamic(
  () => import("../../../ui/experience/shift-rescue/ShiftRescuePanel"),
  { ssr: false, loading: () => <ExpSkeleton rows={4} grid /> },
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

  if (!ready) return <ExpSkeleton rows={4} grid />;
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