"use client";

import { roleLabel } from "../../lib/session";
import type { TeamUser } from "../../lib/team-stats";
import { userInitials } from "../../lib/team-stats";
import { Btn, StatusChip } from "../kit";

function roleTone(role: string): "ok" | "warn" | "default" {
  if (role === "chu_quan") return "ok";
  if (role === "quan_ly") return "warn";
  return "default";
}

type UserCardProps = {
  user: TeamUser;
  canManage: boolean;
  busy: boolean;
  onPromote: (user: TeamUser) => void;
  onDemote: (user: TeamUser) => void;
};

export function UserCard({ user, canManage, busy, onPromote, onDemote }: UserCardProps) {
  const isOwner = user.role === "chu_quan";
  const isManager = user.role === "quan_ly";
  const isStaff = user.role === "nhan_vien";

  return (
    <article className="nq-nguoi-card">
      <div className="nq-nguoi-card__head">
        <span className="nq-user-avatar" aria-hidden="true">
          {userInitials(user.display_name)}
        </span>
        <div className="nq-nguoi-card__identity">
          <h3 className="nq-nguoi-card__name">{user.display_name}</h3>
          <p className="nq-nguoi-card__handle">@{user.username}</p>
        </div>
        <StatusChip tone={roleTone(user.role)}>{roleLabel(user.role)}</StatusChip>
      </div>

      <div className="nq-nguoi-card__foot">
        {canManage && isStaff ? (
          <Btn
            variant="ghost"
            busy={busy}
            busyLabel="Đang nâng…"
            className="nq-btn-compact"
            onClick={() => onPromote(user)}
          >
            <span className="nq-nguoi-card__action-full">Nâng lên quản lý ca</span>
            <span className="nq-nguoi-card__action-short">Nâng QL</span>
          </Btn>
        ) : null}
        {canManage && isManager ? (
          <Btn
            variant="ghost"
            busy={busy}
            busyLabel="Đang hạ…"
            className="nq-btn-compact nq-btn-compact--danger"
            onClick={() => onDemote(user)}
          >
            <span className="nq-nguoi-card__action-full">Hạ xuống nhân viên</span>
            <span className="nq-nguoi-card__action-short">Hạ NV</span>
          </Btn>
        ) : null}
        {isOwner ? (
          <span className="nq-nguoi-card__fixed" title="Vai trò chủ quán không đổi qua trang này">
            Chủ quán · vai trò cố định
          </span>
        ) : null}
        {!canManage && !isOwner ? <span className="nq-muted text-xs">Chỉ xem</span> : null}
      </div>
    </article>
  );
}
