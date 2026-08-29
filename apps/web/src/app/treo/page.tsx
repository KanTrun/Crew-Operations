"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "../../lib/api";
import { matchExact, matchSearch, matchTime, TIME_FILTER_OPTIONS, uniqueSorted, type TimeFilter } from "../../lib/list-filters";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, btnGhost, btnPrimary, Empty, Kicker, Loading } from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type ViecTreo = {
  id: string;
  phieu_id?: string;
  mau?: string;
  noi_dung: string;
  created_at?: string;
  nhan_vien?: string;
};

type GhiNhan = {
  id?: string;
  loai?: string;
  truoc?: unknown;
  sau?: unknown;
  ai?: string;
  luc?: string;
};

function treoHaystack(v: ViecTreo): string {
  return [v.noi_dung, v.nhan_vien, v.phieu_id, v.mau].filter(Boolean).join(" ");
}

function suaHaystack(g: GhiNhan): string {
  return [g.loai, g.ai, JSON.stringify(g.truoc), JSON.stringify(g.sau)].filter(Boolean).join(" ");
}

export default function TreoPage() {
  const [token, setToken] = useState("");
  const [treo, setTreo] = useState<ViecTreo[]>([]);
  const [sua, setSua] = useState<GhiNhan[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"treo" | "sua">("treo");
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [personF, setPersonF] = useState("all");
  const [timeF, setTimeF] = useState<TimeFilter>("all");

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    Promise.all([
      apiGet<{ items: ViecTreo[] }>("/api/v1/viec-treo")
        .then((d) => setTreo(d.items ?? []))
        .catch(() => setError("Không tải được việc treo.")),
      apiGet<{ items: GhiNhan[] }>("/api/v1/ghi-nhan-sua")
        .then((d) => setSua(d.items ?? []))
        .catch(() => undefined),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  const personSource = tab === "treo" ? treo.map((t) => t.nhan_vien) : sua.map((s) => s.ai);

  const personOptions = useMemo(
    () => [{ value: "all", label: "Mọi người" }, ...uniqueSorted(personSource).map((v) => ({ value: v, label: v }))],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tab, treo, sua],
  );

  const filteredTreo = useMemo(
    () =>
      treo.filter((v) => {
        if (!matchSearch(treoHaystack(v), search)) return false;
        if (!matchExact(v.nhan_vien, personF)) return false;
        if (!matchTime(v.created_at, timeF)) return false;
        return true;
      }),
    [treo, search, personF, timeF],
  );

  const filteredSua = useMemo(
    () =>
      sua.filter((g) => {
        if (!matchSearch(suaHaystack(g), search)) return false;
        if (!matchExact(g.ai, personF)) return false;
        if (!matchTime(g.luc, timeF)) return false;
        return true;
      }),
    [sua, search, personF, timeF],
  );

  const filtered = tab === "treo" ? filteredTreo : filteredSua;
  const activeList = tab === "treo" ? treo : sua;
  const filterActive = search.length > 0 || personF !== "all" || timeF !== "all";

  function clearFilters() {
    setSearch("");
    setPersonF("all");
    setTimeF("all");
  }

  useEffect(() => {
    setSearch("");
    setPersonF("all");
    setTimeF("all");
  }, [tab]);

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <Kicker>Quản lý ca</Kicker>
      <h1>Việc treo</h1>
      {error ? <Alert>{error}</Alert> : null}
      <p style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
        <button onClick={() => setTab("treo")} style={tab === "treo" ? btnPrimary : btnGhost}>
          Việc treo ({treo.length})
        </button>
        <button onClick={() => setTab("sua")} style={tab === "sua" ? btnPrimary : btnGhost}>
          Ghi nhận sửa ({sua.length})
        </button>
      </p>
      <ListToolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder={tab === "treo" ? "Tìm nội dung treo, phiếu, nhân viên…" : "Tìm loại sửa, người thao tác…"}
        person={personF}
        onPersonChange={setPersonF}
        personOptions={personOptions}
        time={timeF}
        onTimeChange={(v) => setTimeF(v as TimeFilter)}
        timeOptions={TIME_FILTER_OPTIONS}
        shown={filtered.length}
        total={activeList.length}
        filtered={filterActive}
      />
      {tab === "treo" && (
        <div className="nq-list">
          {loading ? <Loading /> : null}
          {!loading && treo.length === 0 ? <Empty>Không có việc treo.</Empty> : null}
          {!loading && treo.length > 0 && filteredTreo.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
          {filteredTreo.map((v) => (
            <article key={v.id} className="nq-item" style={{ borderLeft: "3px solid var(--nq-danger)" }}>
              <p style={{ margin: 0, fontWeight: 600 }}>{v.noi_dung}</p>
              <p className="nq-muted" style={{ margin: "0.35rem 0 0", fontSize: "0.82rem" }}>
                {v.nhan_vien ? `NV ${v.nhan_vien}` : ""}
                {v.phieu_id ? ` · phiếu ${v.phieu_id}` : ""}
              </p>
            </article>
          ))}
        </div>
      )}
      {tab === "sua" && (
        <div className="nq-list">
          {loading ? <Loading /> : null}
          {!loading && sua.length === 0 ? (
            <Empty>Chưa có lần sửa. Nhả/nhận ca hoặc ghim ô sẽ ghi vào đây.</Empty>
          ) : null}
          {!loading && sua.length > 0 && filteredSua.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
          {filteredSua.map((g, i) => (
            <article key={g.id ?? String(i)} className="nq-item">
              <p style={{ margin: 0, fontWeight: 600 }}>{g.loai ?? "sửa"}</p>
              <p className="nq-muted" style={{ fontFamily: "var(--nq-font-mono)", fontSize: "0.8rem" }}>
                {JSON.stringify(g.truoc)} → {JSON.stringify(g.sau)}
              </p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
