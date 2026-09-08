"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet } from "../../lib/api";
import { actorLabel, formatLuc, hanhViLabel, viError } from "../../lib/present";
import { matchExact, matchSearch, matchTime, TIME_FILTER_OPTIONS, uniqueSorted, type TimeFilter } from "../../lib/list-filters";
import { getToken } from "../../lib/session";
import { subscribeRealtime } from "../../lib/realtime";
import { Alert, AuthGate, Empty, Loading, OpsCard, PageHeader } from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type Row = {
  id?: number;
  at?: string;
  ai?: string;
  hanh?: string;
  payload?: Record<string, unknown> | unknown;
  [key: string]: unknown;
};

function rowHaystack(it: Row): string {
  return [hanhViLabel(it.hanh), actorLabel(it.ai), it.at, JSON.stringify(it.payload ?? it)].filter(Boolean).join(" ");
}

function payloadEntries(row: Row): [string, string][] {
  const payload = row.payload ?? Object.fromEntries(
    Object.entries(row).filter(([key]) => !["id", "at", "ai", "hanh"].includes(key)),
  );
  if (payload && typeof payload === "object") {
    return Object.entries(payload as Record<string, unknown>).map(([key, value]) => [key, typeof value === "string" ? value : JSON.stringify(value)]);
  }
  return [["chi_tiet", String(payload)]];
}

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

  useEffect(() => {
    if (!token) return;
    return subscribeRealtime((packet) => {
      if (packet.event === "ops:changed") load();
    });
  }, [token, load]);

  const personOptions = useMemo(
    () => [{ value: "all", label: "Mọi người" }, ...uniqueSorted(items.map((i) => i.ai)).map((v) => ({ value: v, label: actorLabel(v) }))],
    [items],
  );

  const filtered = useMemo(() => {
    return items.filter((it) => {
      if (!matchSearch(rowHaystack(it), search)) return false;
      if (!matchExact(it.ai, personF)) return false;
      if (!matchTime(it.at, timeF)) return false;
      return true;
    });
  }, [items, search, personF, timeF]);

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
      {error ? <Alert>{error}</Alert> : null}

      <OpsCard eyebrow="Nhật ký" title="Các vết gần đây" count={filtered.length} countLabel="vết">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm hành vi, người thực hiện…"
          person={personF}
          onPersonChange={setPersonF}
          personOptions={personOptions}
          personLabel="Người thực hiện"
          time={timeF}
          onTimeChange={(v) => setTimeF(v as TimeFilter)}
          timeOptions={TIME_FILTER_OPTIONS}
          shown={filtered.length}
          total={items.length}
          filtered={filterActive}
        />

        {loading ? <Loading skeleton="list">Đang đọc vết hệ thống…</Loading> : null}
        {!loading && !error && items.length === 0 ? (
          <Empty title="Chưa có vết">Chuyển trạng thái lịch hoặc duyệt hộp thư sẽ sinh vết đầu tiên.</Empty>
        ) : null}
        {!loading && items.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}

        <div className="nq-list">
          {filtered.map((it, i) => (
            <article key={it.id ?? `${i}-${it.at ?? ""}`} className="nq-item">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="nq-item-title">{hanhViLabel(it.hanh)}</p>
                  <p className="nq-item-sub">
                    {actorLabel(it.ai)} · <span className="font-mono">{formatLuc(it.at)}</span>
                  </p>
                </div>
                {it.id ? <span className="font-mono text-[10px] text-[var(--nq-muted)]">#{it.id}</span> : null}
              </div>
              <dl className="mt-3 grid gap-x-4 gap-y-1 border-t border-[var(--nq-dim)]/50 pt-2 text-xs sm:grid-cols-2">
                {payloadEntries(it).map(([key, value]) => (
                  <div key={key} className="min-w-0">
                    <dt className="text-[10px] uppercase tracking-wide text-[var(--nq-muted)]">{key}</dt>
                    <dd className="break-words text-[var(--nq-fg)]">{value}</dd>
                  </div>
                ))}
              </dl>
            </article>
          ))}
        </div>
      </OpsCard>
    </div>
  );
}
