"use client";

/**
 * QUANVERSE — Living Cafe OS.
 *
 * Một trạng thái quán, bốn bản chiếu theo vai trò. Bố cục:
 *   hàng vai trò → mặt bằng (2D/3D) + trục 15 phút/chế độ → chi tiết khu vực
 *   → ba lane khách (hương vị · sở thích · AR) → dòng sự kiện.
 *
 * Nguyên tắc giữ từ bản trước: server đã strip dữ liệu theo vai trò, client
 * không tự lọc lại; mọi mã nội bộ đi qua bảng nhãn `exp-present`.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { getRole, getToken } from "../../lib/session";
import { Icon } from "../../ui/icons";
import { AuthGate } from "../../ui/kit";
import { ExpSkeleton } from "../../ui/experience/exp-kit";
import {
  dataQualityLabel,
  dataQualityLevelLabel,
  eventStatusLabel,
  eventTypeLabel,
} from "../../ui/experience/exp-present";
import LivingMap from "../../ui/experience/quanverse/LivingMap";
import RoleProjection, { type RoleId } from "../../ui/experience/quanverse/RoleProjection";
import ModeRail from "../../ui/experience/quanverse/ModeRail";
import HorizonTimeline from "../../ui/experience/quanverse/HorizonTimeline";
import FlavorUniverse from "../../ui/experience/quanverse/FlavorUniverse";
import PreferenceConsent from "../../ui/experience/quanverse/PreferenceConsent";
import ArLiteOverlay from "../../ui/experience/quanverse/ArLiteOverlay";
import ZoneDetail from "../../ui/experience/quanverse/ZoneDetail";
import type { LiveSnapshotUI } from "../../ui/experience/quanverse/quanverse-model";

const ALL_ROLES: RoleId[] = ["khach", "nhan_vien", "quan_ly", "chu_quan"];
const ROLE_NAME: Record<RoleId, string> = {
  khach: "Khách",
  nhan_vien: "Nhân viên",
  quan_ly: "Quản lý",
  chu_quan: "Chủ quán",
};

export default function QuanversePage() {
  const [token, setToken] = useState("");
  const [role, setRole] = useState<RoleId>("quan_ly");
  const [ready, setReady] = useState(false);
  const [snap, setSnap] = useState<LiveSnapshotUI | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const [busyMode, setBusyMode] = useState(false);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

  useEffect(() => {
    setToken(getToken());
    const r = getRole() as RoleId;
    if (ALL_ROLES.includes(r)) setRole(r);
    setReady(true);
  }, []);

  const loadSnapshot = useCallback(async (forRole: RoleId) => {
    setError(null);
    try {
      const qs = `?replay_role=${forRole}`;
      const res = await fetch(`${base}/api/v1/experience/quanverse/snapshot${qs}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`api_${res.status}`);
      setSnap((await res.json()) as LiveSnapshotUI);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Lỗi tải snapshot");
    }
  }, [base, token]);

  useEffect(() => {
    if (token && ready) loadSnapshot(role);
  }, [token, ready, role, loadSnapshot]);

  const confirmMode = useCallback(async (mode: string) => {
    setBusyMode(true);
    try {
      const res = await fetch(`${base}/api/v1/experience/quanverse/modes/${mode}/confirm`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new Error(`api_${res.status}`);
      await loadSnapshot(role);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không kích hoạt được chế độ");
    } finally {
      setBusyMode(false);
    }
  }, [base, token, role, loadSnapshot]);

  // Khi đổi vai trò, khu vực đang chọn có thể không còn trong bản chiếu mới.
  useEffect(() => {
    setSelectedZone((cur) => {
      if (!cur) return null;
      return snap?.zones?.some((z) => z.zone_id === cur) ? cur : null;
    });
  }, [snap]);

  const selected = useMemo(
    () => snap?.zones?.find((z) => z.zone_id === selectedZone) ?? null,
    [snap, selectedZone],
  );

  if (!ready) return <ExpSkeleton rows={6} />;
  if (!token) return <AuthGate />;

  const quality = snap?.data_quality ?? [];
  const events = snap?.events ?? [];
  const activeModes = (snap?.modes ?? []).filter((m) => m.active).length;

  return (
    <div className="nq-quanverse">
      <header className="nq-exp-header">
        <h1>QUÁNVERSE — Quán sống của bạn</h1>
        <p>
          Một trạng thái quán, bốn bản chiếu theo vai trò. Bản chiếu do máy chủ cắt
          theo quyền — đổi vai trò để thấy phần dữ liệu tương ứng được mở ra hoặc che đi.
        </p>
      </header>

      {error ? <div className="nq-alert nq-alert--error" role="alert">{error}</div> : null}

      {/* Chuyển bản chiếu theo vai trò — vai trò đang xem được đánh dấu rõ */}
      <div className="nq-rolebar" role="group" aria-label="Chọn vai trò xem">
        {ALL_ROLES.map((r) => (
          <button
            key={r}
            type="button"
            className={`nq-rolebtn${role === r ? " is-on" : ""}`}
            data-testid={`role-${r}`}
            aria-pressed={role === r}
            onClick={() => setRole(r)}
          >
            {ROLE_NAME[r]}
          </button>
        ))}
        <span className="nq-rolechip">
          <Icon name="refresh" size={13} />
          Bản chiếu trực tiếp
        </span>
      </div>

      {!snap ? (
        <ExpSkeleton rows={6} grid />
      ) : (
        <RoleProjection role={snap.role}>
          {/* Tóm tắt trạng thái — bốn con số đọc được trong một lần liếc */}
          <ul className="nq-summary" data-testid="quanverse-summary">
            <li className="nq-statcard">
              <span className="nq-statcard__num">{snap.zones?.length ?? 0}</span>
              <span className="nq-statcard__label">Khu vực trong bản chiếu</span>
            </li>
            <li className="nq-statcard">
              <span className="nq-statcard__num">{activeModes}</span>
              <span className="nq-statcard__label">Chế độ đang bật</span>
            </li>
            <li className="nq-statcard">
              <span className="nq-statcard__num">{snap.next_horizon?.length ?? 0}</span>
              <span className="nq-statcard__label">Mốc trong 15 phút tới</span>
            </li>
            <li className="nq-statcard">
              <span className="nq-statcard__num">{events.length}</span>
              <span className="nq-statcard__label">Sự kiện vận hành</span>
            </li>
          </ul>

          {quality.length > 0 ? (
            <ul className="nq-quality" aria-label="Chất lượng dữ liệu">
              {quality.map((q) => (
                <li key={q.code} className={`nq-quality__item nq-quality__item--${q.level}`}>
                  <Icon name={q.level === "info" ? "info" : "warn"} size={14} />
                  <strong>{dataQualityLevelLabel(q.level)}</strong>
                  <span>{dataQualityLabel(q.code)}</span>
                </li>
              ))}
            </ul>
          ) : null}

          <div className="nq-quanverse__layout">
            <LivingMap
              zones={snap.zones ?? []}
              selectedId={selectedZone}
              onSelectZone={setSelectedZone}
            />
            <div className="nq-quanverse__right">
              <HorizonTimeline items={snap.next_horizon ?? []} />
              <ModeRail modes={snap.modes ?? []} onConfirm={confirmMode} busy={busyMode} />
            </div>
          </div>

          {/* Bấm một khu vực có kết quả thật: bảng chi tiết ngay dưới mặt bằng */}
          {selected ? (
            <ZoneDetail
              zone={selected}
              events={events}
              onClose={() => setSelectedZone(null)}
            />
          ) : (
            <p className="nq-quanverse__hint">
              <Icon name="location" size={14} />
              Chọn một khu vực trên mặt bằng để xem tải, gợi ý hành động và sự kiện tại chỗ.
            </p>
          )}

          {/* Không gian khách: Hương vị · Sở thích · AR */}
          <div className="nq-quanverse__guests">
            <FlavorUniverse />
            <PreferenceConsent />
            <ArLiteOverlay />
          </div>

          {/* Event/action list theo bản chiếu */}
          <section className="nq-quanverse__events" aria-label="Sự kiện trạng thái">
            <div className="nq-exp-section__head">
              <Icon name="bell" size={16} />
              <h3 className="nq-exp-section__title">Sự kiện</h3>
              <span className="nq-exp-section__spacer" />
              <span className="nq-quanverse__eventcount">{events.length} mục</span>
            </div>
            <ul>
              {events.map((ev) => (
                <li key={ev.event_id} className="nq-quanverse__event">
                  <span className="nq-quanverse__eventtype">{eventTypeLabel(ev.event_type)}</span>
                  <span className="nq-quanverse__eventsum">{ev.summary}</span>
                  <span className="nq-quanverse__eventstatus">{eventStatusLabel(ev.status)}</span>
                </li>
              ))}
              {events.length === 0 && (
                <li className="nq-quanverse__event nq-quanverse__event--empty">
                  Không có sự kiện vận hành cho bản chiếu này.
                </li>
              )}
            </ul>
          </section>
        </RoleProjection>
      )}
    </div>
  );
}