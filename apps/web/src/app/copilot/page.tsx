"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { CopilotBody } from "../../ui/copilot/CopilotBody";
import { useCopilotChat } from "../../ui/copilot/useCopilotChat";
import { getRole, roleLabel, type Role } from "../../lib/session";
import { AuthGate } from "../../ui/kit";

export default function CopilotPage() {
  const [role, setRole] = useState<Role | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    setRole(getRole());
    setChecked(true);
  }, []);

  const chat = useCopilotChat("page");

  if (!checked) {
    return (
      <div className="nq-page flex items-center justify-center min-h-screen text-sm text-zinc-500">
        Đang mở AG-COPILOT…
      </div>
    );
  }
  if (!role) return <AuthGate />;

  return (
    <div className="nq-page max-w-5xl mx-auto p-4 md:p-8">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-widest text-zinc-500">
            Trợ lý điều hành
          </p>
          <h1 className="text-2xl font-bold text-zinc-100">
            {chat.profile.label}
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Đang đăng nhập với vai trò <b className="text-zinc-200">{roleLabel(role)}</b>.
            Mở pane nổi ở góc phải để vừa chat vừa thao tác trang chính.
          </p>
        </div>
        <Link
          href="/hom-nay"
          className="text-xs px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-zinc-200"
        >
          ← Về Hôm nay
        </Link>
      </div>

      <div
        className="rounded-2xl border border-zinc-800 overflow-hidden bg-zinc-950"
        style={{
          height: "calc(100vh - 220px)",
          minHeight: 540,
          ["--accent" as any]: chat.profile.accent,
        }}
      >
        <CopilotBody
          chat={chat}
          mode="page"
          onClearHistory={() => chat.clearHistory()}
        />
      </div>
    </div>
  );
}