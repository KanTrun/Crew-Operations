"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { matchSearch, matchTime, TIME_FILTER_OPTIONS, type TimeFilter } from "../../lib/list-filters";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  inputClassName,
  Loading,
  Notice,
  OpsCard,
  PageHeader,
  StatusChip,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type Row = { id: string; hang: string; so_luong: number; don_vi: string; duoi_nguong?: boolean; created_at?: string };

function rowHaystack(it: Row): string {
  return [it.hang, String(it.so_luong), it.don_vi, it.duoi_nguong ? "dưới ngưỡng" : ""].join(" ");
}

export default function TieuThuPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Row[]>([]);
  const [hang, setHang] = useState("sữa tươi");
  const [so, setSo] = useState("3");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusF, setStatusF] = useState("all");
  const [timeF, setTimeF] = useState<TimeFilter>("all");

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: Row[] }>("/api/v1/tieu-thu")
      .then((d) => setItems(d.items ?? []))
      .catch(() => setError("Không đọc được sổ tiêu thụ."))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  const statusOptions = useMemo(
    () => [
      { value: "all", label: "Mọi trạng thái" },
      { value: "ok", label: "Đủ ngưỡng" },
      { value: "low", label: "Dưới ngưỡng" },
    ],
    [],
  );

  const filtered = useMemo(() => {
    return items.filter((it) => {
      if (!matchSearch(rowHaystack(it), search)) return false;
      if (statusF === "low" && !it.duoi_nguong) return false;
      if (statusF === "ok" && it.duoi_nguong) return false;
      if (!matchTime(it.created_at, timeF)) return false;
      return true;
    });
  }, [items, search, statusF, timeF]);

  const filterActive = search.length > 0 || statusF !== "all" || timeF !== "all";

  function clearFilters() {
    setSearch("");
    setStatusF("all");
    setTimeF("all");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    try {
      await apiSend("/api/v1/tieu-thu", { hang, so_luong: Number(so), don_vi: "khay" });
      load();
    } catch {
      setError("Cần quyền quản lý để ghi số lượng.");
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Số lượng · không kế toán"
        title="Sổ tiêu thụ"
        meta="Hệ thống ghi số, không tính tiền. Dưới 2 khay thì cảnh báo trên Hôm nay."
      />
      {error ? <Alert>{error}</Alert> : null}

      {isManager() ? (
        <OpsCard eyebrow="Khu vực 1" title="Ghi kiểm kê mới">
          <form onSubmit={onSubmit}>
            <Field label="Hàng">
              <input className={inputClassName} value={hang} onChange={(e) => setHang(e.target.value)} />
            </Field>
            <Field label="Số lượng">
              <input
                className={inputClassName}
                value={so}
                onChange={(e) => setSo(e.target.value)}
                inputMode="decimal"
              />
            </Field>
            <Btn type="submit" variant="primary">
              Ghi kiểm kê
            </Btn>
          </form>
        </OpsCard>
      ) : (
        <Notice>Chỉ quản lý mới ghi số lượng. Bạn vẫn xem được lịch sử kiểm kê bên dưới.</Notice>
      )}

      <OpsCard eyebrow="Khu vực 2" title="Lần ghi" count={filtered.length} countLabel="lần">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm tên hàng, số lượng…"
          status={statusF}
          onStatusChange={setStatusF}
          statusOptions={statusOptions}
          statusLabel="Ngưỡng"
          time={timeF}
          onTimeChange={(v) => setTimeF(v as TimeFilter)}
          timeOptions={TIME_FILTER_OPTIONS}
          shown={filtered.length}
          total={items.length}
          filtered={filterActive}
        />
        {loading ? <Loading skeleton="list">Đang tải sổ tiêu thụ…</Loading> : null}
        {!loading && items.length === 0 ? <Empty title="Chưa có lần ghi">Chưa có lần kiểm kê nào.</Empty> : null}
        {!loading && items.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
        <div className="nq-list">
          {filtered.map((it) => (
            <article key={it.id} className={`nq-item ${it.duoi_nguong ? "nq-item--accent-warn" : ""}`}>
              <p className="nq-item-title">{it.hang}</p>
              <p className="nq-item-sub font-mono">
                {it.so_luong} {it.don_vi}
                {it.duoi_nguong ? (
                  <>
                    {" "}
                    · <StatusChip tone="warn">Dưới ngưỡng</StatusChip>
                  </>
                ) : null}
                {it.created_at ? ` · ${new Date(it.created_at).toLocaleString("vi-VN")}` : ""}
              </p>
            </article>
          ))}
        </div>
      </OpsCard>
    </div>
  );
}
