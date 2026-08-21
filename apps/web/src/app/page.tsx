import Link from "next/link";

export default function HomePage() {
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "2rem",
      }}
    >
      <div style={{ maxWidth: 520, width: "100%" }}>
        <p
          style={{
            letterSpacing: "0.28em",
            textTransform: "uppercase",
            fontSize: "0.75rem",
            color: "var(--nq-ink-muted)",
            marginBottom: "0.75rem",
          }}
        >
          Sprint 1 · demo
        </p>
        <h1
          style={{
            fontFamily: "var(--nq-font-display)",
            fontSize: "clamp(2.4rem, 7vw, 3.6rem)",
            fontWeight: 400,
            margin: "0 0 0.75rem",
            lineHeight: 1.05,
          }}
        >
          NHỊP QUÁN
        </h1>
        <p style={{ color: "var(--nq-ink-muted)", marginBottom: "1.75rem" }}>
          Đăng nhập để xem năm hợp đồng dữ liệu từ máy chủ giả.
        </p>
        <Link
          href="/login"
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            minHeight: 44,
            minWidth: 160,
            padding: "0.75rem 1.25rem",
            background: "var(--nq-accent)",
            color: "var(--nq-accent-ink)",
            textDecoration: "none",
            fontWeight: 600,
            borderRadius: 2,
          }}
        >
          Đăng nhập
        </Link>
      </div>
    </main>
  );
}
