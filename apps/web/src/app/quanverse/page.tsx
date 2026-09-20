"use client";

/** QUANVERSE — Living Cafe OS: Living Map + role projection + modes + flavor. */

import { useCallback, useEffect, useState } from "react";
import { getToken, getRole } from "../../lib/session";
import { AuthGate, Loading } from "../../ui/kit";
import LivingMap from "../../ui/experience/quanverse/LivingMap";
import RoleProjection, { type RoleId } from "../../ui/experience/quanverse/RoleProjection";
import ModeRail from "../../ui/experience/quanverse/ModeRail";
import HorizonTimeline from "../../ui/experience/quanverse/HorizonTimeline";
import FlavorUniverse from "../../ui/experience/quanverse/FlavorUniverse";
import PreferenceConsent from "../../ui/experience/quanverse/PreferenceConsent";
import ArLiteOverlay from "../../ui/experience/quanverse/ArLiteOverlay";
import type { LiveSnapshotUI } from "../../ui/experience/quanverse/quanverse-model";

const ALL_ROLES: RoleId[] = ["khach", "nhan_vien", "quan_ly", "chu_quan"];

export default function QuanversePage() {
  const [token, setToken] = useState("");
  const [role, setRole] = useState<RoleId>("quan_ly");
  const [ready, setReady] = useState(false);
  const [snap, setSnap] = useState<LiveSnapshotUI | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [replayMode, setReplayMode] = useState(true); // fixture/demo

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

  useEffect(() => {
    setToken(getToken());
    const r = getRole() as RoleId;
    if (ALL_ROLES.includes(r)) setRole(r);
    setReady(true);
  }, []);

  const loadSnapshot = useCallback(async (forRole: RoleId) => {
    try {
      const qs = replayMode ? `?replay_role=${forRole}` : "";
      const res = await fetch(`${base}/api/v1/experience/quanverse/snapshot${qs}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`api_${res.status}`);
      setSnap((await res.json()) as LiveSnapshotUI);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải snapshot");
    }
  }, [base, token, replayMode]);

  useEffect(() => {
    if (token && ready) loadSnapshot(role);
  }, [token, ready, role, loadSnapshot]);

  const confirmMode = useCallback(async (mode: string) => {
    try {
      await fetch(`${base}/api/v1/experience/quanverse/modes/${mode}/confirm`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      await loadSnapshot(role);
    } catch {
      // giữ nguyên state — chỉ thông báo
    }
  }, [base, token, role, loadSnapshot]);

  if (!ready) return <Loading>Đang kiểm tra phiên…</Loading>;
  if (!token) return <AuthGate />;

  return (
    <div className="nq-quanverse">
      <header className="nq-quanverse__header">
        <h1>QUÁNVERSE — Quán sống của bạn</h1>
        <p>Một trạng thái quán, bốn bản chiếu theo vai trò.</p>
      </header>

      {error ? <div className="nq-alert nq-alert--error">{error}</div> : null}

      {/* Role switch CHỈ trong replay/demo fixture — production từ session */}
      <div className="nq-quanverse__roleswitcher">
        {ALL_ROLES.map((r) => (
          <button
            key={r}
            type="button"
            className={`nq-btn${role === r ? " nq-btn--primary" : ""}`}
            data-testid={`role-${r}`}
            onClick={() => replayMode && setRole(r)}
            disabled={!replayMode}
          >
            {r === "khach" ? "Khách" : r === "nhan_vien" ? "Nhân viên" : r === "quan_ly" ? "Quản lý" : "Chủ quán"}
          </button>
        ))}
        <span className="nq-fixture-chip">{replayMode ? "Role switch chỉ trong demo" : ""}</span>
      </div>

      {snap ? (
        <RoleProjection role={snap.role}>
          <div className="nq-quanverse__layout">
            <LivingMap
              zones={snap.zones}
              onSelectZone={() => undefined}
            />
            <div className="nq-quanverse__right">
              <HorizonTimeline items={snap.next_horizon ?? []} />
              <ModeRail modes={snap.modes ?? []} onConfirm={confirmMode} />
              <FlavorUniverse />
              <PreferenceConsent />
              <ArLiteOverlay />
            </div>
          </div>
          {/* Event/action list theo bản chiếu */}
          <section className="nq-quanverse__events" aria-label="Sự kiện trạng thái">
            <h3>Sự kiện</h3>
            <ul>
              {(snap.events ?? []).map(
                (ev: { event_id: string; event_type: string; summary: string; status: string }) => (
                  <li key={ev.event_id} className="nq-quanverse__event">
                    <span>{ev.event_type}</span> · {ev.summary} · {ev.status}
                  </li>
                ),
              )}
              {(snap.events ?? []).length === 0 && <li>Không có sự kiện vận hành cho bản chiếu này.</li>}
            </ul>
          </section>
        </RoleProjection>
      ) : (
        <p aria-busy="true">Đang tải snapshot…</p>
      )}
    </div>
  );
}