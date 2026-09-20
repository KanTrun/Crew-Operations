"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { getToken, isManager } from "../../../lib/session";
import { AuthGate, Loading } from "../../../ui/kit";

const RuleDiscovery = dynamic(
  () => import("../../../ui/experience/rules/RuleDiscovery"),
  { ssr: false, loading: () => <Loading>Đang tải Quán tự viết luật…</Loading> },
);

export default function RulesPage() {
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
        Quán tự viết luật yêu cầu vai trò Quản lý hoặc Chủ quán.
      </div>
    );
  }
  return <RuleDiscovery />;
}