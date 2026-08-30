"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { matchSearch, matchTime, TIME_FILTER_OPTIONS, uniqueSorted, type TimeFilter } from "../../lib/list-filters";
import { getToken } from "../../lib/session";
import { Alert, AuthGate, Btn, Empty, Field, inputClassName, Loading, OpsCard, PageHeader } from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type Cluster = { cau?: string; thu?: string; n?: number; created_at?: string };

function clusterHaystack(it: Cluster): string {
  return [it.cau, it.thu, String(it.n ?? "")].filter(Boolean).join(" ");
}

export default function HaoPhiPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Cluster[]>([]);
  const [thu, setThu] = useState("T3");
  const [ghi, setGhi] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [thuF, setThuF] = useState("all");
  const [timeF, setTimeF] = useState<TimeFilter>("all");

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Cluster[] }>("/api/v1/waste")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không đọc được hao phí."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  const thuOptions = useMemo(
    () => [{ value: "all", label: "Mọi thứ" }, ...uniqueSorted(items.map((i) => i.thu)).map((v) => ({ value: v, label: v }))],
    [items],
  );

  const filtered = useMemo(() => {
    return items.filter((it) => {
      if (!matchSearch(clusterHaystack(it), search)) return false;
      if (thuF !== "all" && (it.thu ?? "") !== thuF) return false;
      if (!matchTime(it.created_at, timeF)) return false;
      return true;
    });
  }, [items, search, thuF, timeF]);

  const filterActive = search.length > 0 || thuF !== "all" || timeF !== "all";

  function clearFilters() {
    setSearch("");
    setThuF("all");
    setTimeF("all");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await apiSend("/api/v1/waste", { thu, ghi_chu: ghi });
      setGhi("");
      load();
    } catch {
      setError("Không ghi được ghi chú hao phí.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Gom cụm từ ghi chú ca"
        title="Hao phí"
        meta="Ghi chú trong ca được gom cụm — form ghi và danh sách cụm tách riêng."
      />
      {error ? <Alert>{error}</Alert> : null}

      <OpsCard eyebrow="Khu vực 1" title="Ghi chú mới">
        <form onSubmit={onSubmit}>
          <Field label="Thứ">
            <input className={inputClassName} value={thu} onChange={(e) => setThu(e.target.value)} />
          </Field>
          <Field label="Ghi chú">
            <input className={inputClassName} value={ghi} onChange={(e) => setGhi(e.target.value)} />
          </Field>
          <Btn type="submit" variant="primary">
            Ghi chú
          </Btn>
        </form>
      </OpsCard>

      <OpsCard eyebrow="Khu vực 2" title="Cụm đã gom" count={filtered.length} countLabel="cụm">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm nội dung cụm, thứ…"
          status={thuF}
          onStatusChange={setThuF}
          statusOptions={thuOptions}
          statusLabel="Thứ trong tuần"
          time={timeF}
          onTimeChange={(v) => setTimeF(v as TimeFilter)}
          timeOptions={TIME_FILTER_OPTIONS}
          shown={filtered.length}
          total={items.length}
          filtered={filterActive}
        />
        {loading ? <Loading skeleton="list">Đang tải cụm hao phí…</Loading> : null}
        {!loading && items.length === 0 ? <Empty title="Chưa có cụm">Chưa có ghi chú để gom cụm.</Empty> : null}
        {!loading && items.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
        <div className="nq-list">
          {filtered.map((it, i) => (
            <article key={i} className="nq-item">
              <p className="nq-item-title">{it.cau ?? "Chưa đủ mẫu để gom cụm"}</p>
              <p className="nq-item-sub">
                {it.thu} · {it.n ?? 0} lần
              </p>
            </article>
          ))}
        </div>
      </OpsCard>
    </div>
  );
}
