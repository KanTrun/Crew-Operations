"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { getToken, isManager } from "../../../lib/session";
import { AuthGate } from "../../../ui/kit";
import { ExpSkeleton } from "../../../ui/experience/exp-kit";
import PageAssistant from "../../../ui/experience/quanverse/PageAssistant";

const WarRoom = dynamic(
  () => import("../../../ui/experience/war-room/WarRoom"),
  { ssr: false, loading: () => <ExpSkeleton rows={5} grid /> },
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

  if (!ready) return <ExpSkeleton rows={5} grid />;
  if (!token) return <AuthGate />;
  if (!manager) {
    return (
      <div className="nq-alert nq-alert--error" role="alert">
        War Room yêu cầu vai trò Quản lý hoặc Chủ quán.
      </div>
    );
  }
  return (
    <div className="nq-quanverse-sub">
      <WarRoom />
      {/* Trợ lý Quánverse: phương án nào dùng được, cảnh báo ràng buộc. */}
      <PageAssistant page="war_room" />
    </div>
  );
}