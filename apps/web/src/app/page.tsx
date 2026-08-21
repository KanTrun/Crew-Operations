async function fetchHealth(): Promise<string> {
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  try {
    const res = await fetch(`${base}/health`, { cache: "no-store" });
    if (!res.ok) return "api-unreachable";
    const data = (await res.json()) as { status?: string };
    return data.status ?? "unknown";
  } catch {
    return "api-unreachable";
  }
}

export default async function HomePage() {
  const health = await fetchHealth();
  return (
    <main
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        padding: "2rem",
      }}
    >
      <div style={{ maxWidth: 640, textAlign: "center" }}>
        <p
          style={{
            letterSpacing: "0.35em",
            textTransform: "uppercase",
            fontSize: "0.75rem",
            opacity: 0.7,
            marginBottom: "1rem",
          }}
        >
          HUTECH 2026
        </p>
        <h1
          style={{
            fontSize: "clamp(2.5rem, 8vw, 4.5rem)",
            fontWeight: 400,
            margin: "0 0 1rem",
            lineHeight: 1.05,
          }}
        >
          NHỊP QUÁN
        </h1>
        <p style={{ fontSize: "1.125rem", opacity: 0.85, marginBottom: "2rem" }}>
          Ca làm việc là hạt nhân. Cẩm nang tự viết là bộ nhớ.
        </p>
        <p
          style={{
            display: "inline-block",
            border: "1px solid rgba(243,230,212,0.35)",
            padding: "0.75rem 1.25rem",
            borderRadius: 2,
            fontFamily: "ui-monospace, monospace",
            fontSize: "0.875rem",
          }}
        >
          API /health → {health}
        </p>
      </div>
    </main>
  );
}
