"use client";

import { useEffect, useState } from "react";
import { apiGet } from "../../lib/api";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Empty, Loading, PageHeader } from "../../ui/kit";

const AXIS: Record<string, string> = {
  cuoi_tuan: "Cuối tuần",
  dem: "Đêm",
  gio: "Giờ",
  vun: "Ca vụn",
};

export default function CongBangPage() {
  const [token, setToken] = useState("");
  const [soDu, setSoDu] = useState<Record<string, Record<string, number>>>({});
  const [means, setMeans] = useState<Record<string, number>>({});
  const [me, setMe] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) {
      setLoading(false);
      return;
    }
    apiGet<{ so_du: Record<string, Record<string, number>>; means: Record<string, number>; nv_id: string }>(
      "/api/v1/cong-bang",
    )
      .then((d) => {
        setSoDu(d.so_du ?? {});
        setMeans(d.means ?? {});
        setMe(d.nv_id ?? "");
      })
      .catch(() => setError("Không đọc được sổ công bằng."))
      .finally(() => setLoading(false));
  }, []);

  if (!token) return <AuthGate />;

  const ids = Object.keys(soDu);

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Sổ nợ bốn chiều · không xếp hạng tên"
        title="Công bằng"
        meta="Chỉ số dư theo trục — không bảng xếp hạng tên."
      />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang đọc sổ nợ…</Loading> : null}
      {!loading && ids.length === 0 ? <Empty>Chưa có phân công để tính nợ.</Empty> : null}
      <div className="nq-list">
        {ids.map((id) => (
          <article key={id} className="nq-item">
            <p className="nq-item-title">{id === me ? "Bạn" : "Nhân viên"}</p>
            <ul className="nq-fairness-list">
              {Object.entries(soDu[id] || {}).map(([a, v]) => (
                <li key={a}>
                  {AXIS[a] ?? a}: {Number(v).toFixed(1)} · TB nhóm {(means[a] ?? 0).toFixed(1)}
                </li>
              ))}
            </ul>
          </article>
        ))}
      </div>
    </div>
  );
}
