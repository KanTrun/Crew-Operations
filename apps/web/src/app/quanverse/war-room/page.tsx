"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { getToken, isManager } from "../../../lib/session";
import { AuthGate, Loading } from "../../../ui/kit";

const WarRoom = dynamic(
  () => import("../../../ui/experience/war-room/WarRoom"),
  { ssr: false, loading: () => <Loading>Đang tải War Room…</Loading> },
);

export default function WarRoomPage() {
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
        War Room yêu cầu vai trò Quản lý hoặc Chủ quán.
      </div>
    );
  }
  return <WarRoom />;
}