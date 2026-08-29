"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "../../lib/api";
import { matchExact, matchSearch, matchTime, TIME_FILTER_OPTIONS, uniqueSorted, type TimeFilter } from "../../lib/list-filters";
import { actorLabel, formatLuc, hanhViLabel, viError } from "../../lib/present";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Empty, Loading, PageHeader } from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type Row = { at?: string; ai?: string; hanh?: string };

export default function VetPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Row[]>([]);
  const [error, setError] = useState<string | null>(null);
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
    setLoading(true);
    apiGet<{ items: Row[] }>("/api/v1/audit")
      .then((d) => {
        setItems(d.items ?? []);
        setError(null);
      })
      .catch((e) =>
        setError(
          viError(e, {
            doing: "đọc được vết hệ thống",
            forbidden: "Chỉ quản lý hoặc chủ quán đọc được vết hệ thống.",
          }),
        ),
      )
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  const personOptions = useMemo(
    () => [
      { value: "all", label: "Mọi người" },
      ...uniqueSorted(items.map((i) => i.ai)).map((v) => ({ value: v, label: actorLabel(v) })),
    ],
    [items],
  );

  const filtered = useMemo(
    () =>
      items.filter((it) => {
        if (!matchSearch([hanhViLabel(it.hanh), actorLabel(it.ai)].join(" "), search)) return false;
        if (!matchExact(it.ai, personF)) return false;
        if (!matchTime(it.at, timeF)) return false;
        return true;
      }),
    [items, search, personF, timeF],
  );

  const filterActive = search.length > 0 || personF !== "all" || timeF !== "all";

  function clearFilters() {
    setSearch("");
    setPersonF("all");
    setTimeF("all");
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Chỉ ghi thêm, không xóa"
        title="Vết hệ thống"
        meta="Mọi lần đổi lịch, duyệt ràng buộc, ghi sổ đều để lại vết ở đây — để tra lại khi cần đối chiếu."
      />
      <ListToolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Tìm hành vi, người thực hiện…"
        person={personF}
        onPersonChange={setPersonF}
        personOptions={personOptions}
        time={timeF}
        onTimeChange={(v) => setTimeF(v as TimeFilter)}
        timeOptions={TIME_FILTER_OPTIONS}
        shown={filtered.length}
        total={items.length}
        filtered={filterActive}
      />
      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang đọc vết hệ thống…</Loading> : null}
      {!loading && !error && items.length === 0 ? (
        <Empty>Chưa có vết nào. Chuyển trạng thái lịch hoặc duyệt hộp thư sẽ sinh vết đầu tiên.</Empty>
      ) : null}
      {!loading && items.length > 0 && filtered.length === 0 ? (
        <FilteredEmpty onClear={clearFilters} />
      ) : null}
      <div className="nq-list">
        {filtered.map((it, i) => (
          <article key={`${i}-${it.at ?? ""}`} className="nq-item">
            <p className="nq-item-title">{hanhViLabel(it.hanh)}</p>
            <p className="nq-item-sub">
              {actorLabel(it.ai)} · <span style={{ fontFamily: "var(--nq-font-mono)" }}>{formatLuc(it.at)}</span>
            </p>
          </article>
        ))}
      </div>
    </div>
  );
}
