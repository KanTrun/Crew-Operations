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
      <div className="nq-copilot-page nq-copilot-page--loading" role="status">
        Đang mở trợ lý vận hành…
      </div>
    );
  }
  if (!role) return <AuthGate />;

  return (
    <div className="nq-copilot-page" style={{ ["--accent" as string]: chat.profile.accent }}>
      <header className="nq-copilot-page__head">
        <div>
          <p className="nq-copilot-page__kicker">Trợ lý · {roleLabel(role)}</p>
          <h1 className="nq-copilot-page__title">{chat.profile.label}</h1>
        </div>
        <Link href="/hom-nay" className="nq-btn nq-btn-ghost nq-btn-sm">
          Về Hôm nay
        </Link>
      </header>

      <div className="nq-copilot-page__frame">
        <CopilotBody chat={chat} mode="page" onClearHistory={() => chat.clearHistory()} />
      </div>
    </div>
  );
}
