"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "../../lib/api";
import { matchExact, matchSearch, matchTime, TIME_FILTER_OPTIONS, uniqueSorted, type TimeFilter } from "../../lib/list-filters";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Empty, Loading, OpsCard, PageHeader, TabBar, TabButton } from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type ViecTreo = {
  id: string;
  phieu_id?: string;
  mau?: string;
  noi_dung: string;
  created_at?: string;
  nhan_vien?: string;
  trang_thai?: string;
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

  const activeList = tab === "treo" ? treo : sua;
  const personSource = tab === "treo" ? treo.map((t) => t.nhan_vien) : sua.map((s) => s.ai);
  const personOptions = useMemo(
    () => [{ value: "all", label: "Mọi người" }, ...uniqueSorted(personSource).map((v) => ({ value: v, label: v }))],
    [personSource, tab],
  );

  const filteredTreo = useMemo(() => {
    return treo.filter((v) => {
      if (!matchSearch(treoHaystack(v), search)) return false;
      if (!matchExact(v.nhan_vien, personF)) return false;
      if (!matchTime(v.created_at, timeF)) return false;
      return true;
    });
  }, [treo, search, personF, timeF]);

  const filteredSua = useMemo(() => {
    return sua.filter((g) => {
      if (!matchSearch(suaHaystack(g), search)) return false;
      if (!matchExact(g.ai, personF)) return false;
      if (!matchTime(g.luc, timeF)) return false;
      return true;
    });
  }, [sua, search, personF, timeF]);

  const filtered = tab === "treo" ? filteredTreo : filteredSua;
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
      <PageHeader
        kicker="Quản lý ca"
        title="Việc treo"
        meta="Việc kẹt từ phiếu ca và sổ những lần quán sửa lịch — tách hai khu vực để không lẫn."
      />
      {error ? <Alert>{error}</Alert> : null}

      <TabBar>
        <TabButton active={tab === "treo"} onClick={() => setTab("treo")}>
          Việc treo ({treo.length})
        </TabButton>
        <TabButton active={tab === "sua"} onClick={() => setTab("sua")}>
          Ghi nhận sửa ({sua.length})
        </TabButton>
      </TabBar>

      {tab === "treo" ? (
        <OpsCard eyebrow="Khu vực 1" title="Việc đang treo trong ca" count={filtered.length} countLabel="việc">
          <ListToolbar
            search={search}
            onSearchChange={setSearch}
            searchPlaceholder="Tìm nội dung treo, phiếu, nhân viên…"
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
          {loading ? <Loading skeleton="list">Đang tải việc treo…</Loading> : null}
          {!loading && treo.length === 0 ? <Empty title="Không có việc treo">Ca chạy sạch, không còn việc kẹt.</Empty> : null}
          {!loading && treo.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
          <div className="nq-list">
            {filteredTreo.map((v) => (
              <article key={v.id} className="nq-item nq-item--accent-danger">
                <p className="nq-item-title">{v.noi_dung}</p>
                <p className="nq-item-sub">
                  {v.nhan_vien ? `NV ${v.nhan_vien}` : ""}
                  {v.phieu_id ? ` · phiếu ${v.phieu_id}` : ""}
                  {v.created_at ? ` · ${new Date(v.created_at).toLocaleString("vi-VN")}` : ""}
                </p>
              </article>
            ))}
          </div>
        </OpsCard>
      ) : (
        <OpsCard eyebrow="Khu vực 2" title="Lần sửa lịch đã ghi" count={filtered.length} countLabel="lần">
          <ListToolbar
            search={search}
            onSearchChange={setSearch}
            searchPlaceholder="Tìm loại sửa, người thao tác…"
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
          {loading ? <Loading skeleton="list">Đang tải ghi nhận…</Loading> : null}
          {!loading && sua.length === 0 ? (
            <Empty title="Chưa có lần sửa">Nhả/nhận ca hoặc ghim ô sẽ ghi vào đây.</Empty>
          ) : null}
          {!loading && sua.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
          <div className="nq-list">
            {filteredSua.map((g, i) => (
              <article key={g.id ?? String(i)} className="nq-item">
                <p className="nq-item-title">{g.loai ?? "sửa"}</p>
                <p className="nq-item-sub font-mono text-sm">
                  {g.ai ? `${g.ai} · ` : ""}
                  {JSON.stringify(g.truoc)} → {JSON.stringify(g.sau)}
                  {g.luc ? ` · ${new Date(g.luc).toLocaleString("vi-VN")}` : ""}
                </p>
              </article>
            ))}
          </div>
        </OpsCard>
      )}
    </div>
  );
}
