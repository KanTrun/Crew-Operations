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
      <div className="nq-page flex min-h-screen items-center justify-center text-sm text-[var(--nq-dim)]">
        Đang mở trợ lý vận hành…
      </div>
    );
  }
  if (!role) return <AuthGate />;

  return (
    <div className="nq-page max-w-5xl mx-auto p-4 md:p-8">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-widest text-[var(--nq-copper)]">
            Trợ lý điều hành
          </p>
          <h1 className="text-2xl font-bold text-[var(--nq-fg)]">
            {chat.profile.label}
          </h1>
          <p className="mt-1 text-xs text-[var(--nq-dim)]">
            Đang đăng nhập với vai trò <b className="text-[var(--nq-fg)]">{roleLabel(role)}</b>.
            Bạn có thể dùng khung nổi để vừa trao đổi vừa thao tác trang chính.
          </p>
        </div>
        <Link
          href="/hom-nay"
          className="border-2 border-[var(--nq-dim)] px-3 py-1.5 text-xs text-[var(--nq-fg)] hover:border-[var(--nq-copper)] hover:text-[var(--nq-copper)]"
        >
          Về Hôm nay
        </Link>
      </div>

      <div
        className="overflow-hidden border-2 border-[var(--nq-dim)] bg-[var(--nq-bg)] shadow-[8px_8px_0_var(--nq-copper-dim)]"
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