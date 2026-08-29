"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { FLOW, HUBS, PRINCIPLES, type Role } from "./map-data";
import { BtnLink, Kicker } from "../../ui/kit";

const ROLE_LABELS: Record<Role, string> = {
  all: "Tất cả",
  nv: "Nhân viên",
  ql: "Quản lý",
};

function roleMatch(pageRoles: Role[], active: Role) {
  return active === "all" || pageRoles.includes(active) || pageRoles.includes("all");
}

export default function MapGuide() {
  const [activeHub, setActiveHub] = useState(HUBS[0].id);
  const [role, setRole] = useState<Role>("all");
  const [tilt, setTilt] = useState({ x: 0, y: 0 });
  const sceneRef = useRef<HTMLDivElement>(null);

  const hub = HUBS.find((h) => h.id === activeHub) ?? HUBS[0];

  const onPointerMove = useCallback((e: React.PointerEvent) => {
    const el = sceneRef.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    const px = (e.clientX - r.left) / r.width - 0.5;
    const py = (e.clientY - r.top) / r.height - 0.5;
    setTilt({ x: py * -12, y: px * 18 });
  }, []);

  const onPointerLeave = useCallback(() => setTilt({ x: 0, y: 0 }), []);

  useEffect(() => {
    const nodes = document.querySelectorAll("[data-reveal]");
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((en) => {
          if (en.isIntersecting) en.target.classList.add("nq-map-visible");
        });
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    nodes.forEach((n) => io.observe(n));
    return () => io.disconnect();
  }, [activeHub, role]);

  return (
    <div className="nq-map-guide">
      <nav className="nq-map-topnav" aria-label="Điều hướng nhanh">
        <Link href="/" className="nq-map-topnav-brand">
          NHỊP QUÁN
        </Link>
        <div className="nq-map-topnav-links">
          <Link href="/login">Đăng nhập</Link>
          <Link href="/hom-nay">Hôm nay</Link>
        </div>
      </nav>

      <div className="nq-map-ambient" aria-hidden>
        <span className="nq-map-orb nq-map-orb--a" />
        <span className="nq-map-orb nq-map-orb--b" />
        <span className="nq-map-grid" />
      </div>

      <header className="nq-map-hero" data-reveal>
        <Kicker>Bản đồ hệ thống</Kicker>
        <h1 className="nq-map-title">
          Đi từ đầu
          <br />
          <span className="text-[var(--nq-copper)]">đến cuối</span>
        </h1>
        <p className="nq-map-lead">
          Bốn phòng vận hành, tám bước một ngày quán — chọn vai trò để lọc trang liên quan, bấm
          vào phòng để xem chi tiết và đường dẫn thật trong app.
        </p>
        <div className="nq-map-hero-actions">
          <BtnLink href="/login" variant="primary">
            Vào demo
          </BtnLink>
          <BtnLink href="/hom-nay" variant="ghost">
            Bỏ qua → Hôm nay
          </BtnLink>
        </div>
      </header>

      <section className="nq-map-section" aria-labelledby="role-heading">
        <h2 id="role-heading" className="nq-map-section-title" data-reveal>
          Bạn đang xem với vai trò
        </h2>
        <div className="nq-map-roles" data-reveal role="tablist">
          {(["all", "nv", "ql"] as Role[]).map((r) => (
            <button
              key={r}
              type="button"
              role="tab"
              aria-selected={role === r}
              className={`nq-map-role ${role === r ? "nq-map-role--on" : ""}`}
              onClick={() => setRole(r)}
            >
              {ROLE_LABELS[r]}
            </button>
          ))}
        </div>
      </section>

      <section className="nq-map-section nq-map-hub-section" aria-labelledby="hub-heading">
        <h2 id="hub-heading" className="nq-map-section-title" data-reveal>
          Bốn phòng — xoay để khám phá
        </h2>
        <p className="nq-map-hint" data-reveal>
          Di chuột trên vòng tròn để nghiêng · bấm phòng để mở danh sách trang
        </p>

        <div
          ref={sceneRef}
          className="nq-map-scene"
          onPointerMove={onPointerMove}
          onPointerLeave={onPointerLeave}
        >
          <div
            className="nq-map-orbit"
            style={{
              transform: `rotateX(${tilt.x}deg) rotateY(${tilt.y}deg)`,
            }}
          >
            {HUBS.map((h) => {
              const rad = (h.angle * Math.PI) / 180;
              const radius = 140;
              const x = Math.sin(rad) * radius;
              const z = Math.cos(rad) * radius;
              const isActive = h.id === activeHub;
              const dimmed = role !== "all" && !h.pages.some((p) => roleMatch(p.roles, role));
              return (
                <button
                  key={h.id}
                  type="button"
                  className={`nq-map-node ${isActive ? "nq-map-node--active" : ""} ${dimmed ? "nq-map-node--dim" : ""}`}
                  style={{
                    transform: `translate3d(${x}px, 0, ${z}px) rotateY(${-h.angle}deg)`,
                    ["--hub-color" as string]: h.color,
                  }}
                  onClick={() => setActiveHub(h.id)}
                  aria-pressed={isActive}
                >
                  <span className="nq-map-node-ring" />
                  <span className="nq-map-node-title">{h.title}</span>
                  <span className="nq-map-node-tag">{h.tagline}</span>
                </button>
              );
            })}
            <div className="nq-map-core" aria-hidden>
              <span>NHỊP</span>
              <span>QUÁN</span>
            </div>
          </div>
        </div>

        <div className="nq-map-detail" data-reveal>
          <div className="nq-map-detail-head" style={{ borderColor: hub.color }}>
            <h3>{hub.title}</h3>
            <p>{hub.tagline}</p>
          </div>
          <ul className="nq-map-pages">
            {hub.pages
              .filter((p) => roleMatch(p.roles, role))
              .map((p) => (
                <li key={p.href}>
                  <Link href={p.href} className="nq-map-page-link">
                    <span className="nq-map-page-label">
                      {p.label}
                      {p.agent ? (
                        <span className="nq-map-agent">{p.agent}</span>
                      ) : null}
                    </span>
                    <span className="nq-map-page-desc">{p.desc}</span>
                    <span className="nq-map-page-arrow" aria-hidden>
                      →
                    </span>
                  </Link>
                </li>
              ))}
          </ul>
          {hub.pages.filter((p) => roleMatch(p.roles, role)).length === 0 ? (
            <p className="nq-map-empty">Không có trang nào cho vai trò này trong phòng này.</p>
          ) : null}
        </div>
      </section>

      <section className="nq-map-section" aria-labelledby="flow-heading">
        <h2 id="flow-heading" className="nq-map-section-title" data-reveal>
          Một ngày của quán — từ đầu tới cuối
        </h2>
        <ol className="nq-map-flow">
          {FLOW.filter((s) => roleMatch(s.roles, role)).map((step, i, arr) => (
            <li key={step.id} className="nq-map-flow-step" data-reveal>
              <div className="nq-map-flow-marker">
                <span>{step.id}</span>
                {i < arr.length - 1 ? <span className="nq-map-flow-line" /> : null}
              </div>
              <div className="nq-map-flow-body">
                <div className="nq-map-flow-meta">
                  <span className="nq-map-flow-who">{step.who}</span>
                  {step.href ? (
                    <Link href={step.href} className="nq-map-flow-link">
                      Mở trang →
                    </Link>
                  ) : null}
                </div>
                <h3>{step.title}</h3>
                <p>{step.what}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section className="nq-map-section nq-map-principles" aria-labelledby="principles-heading">
        <h2 id="principles-heading" className="nq-map-section-title" data-reveal>
          Nguyên tắc nhớ nhanh
        </h2>
        <ul className="nq-map-principle-list">
          {PRINCIPLES.map((text, i) => (
            <li key={i} data-reveal>
              {text}
            </li>
          ))}
        </ul>
      </section>

      <footer className="nq-map-footer" data-reveal>
        <p>Đã hiểu luồng? Bắt đầu từ ca hôm nay hoặc đăng nhập demo.</p>
        <div className="nq-map-hero-actions">
          <BtnLink href="/hom-nay" variant="primary">
            Mở Hôm nay
          </BtnLink>
          <BtnLink href="/login" variant="ghost">
            Đăng nhập
          </BtnLink>
        </div>
      </footer>
    </div>
  );
}
