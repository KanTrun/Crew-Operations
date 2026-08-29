"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { nvLabel, safeText, swapLabel, viError } from "../../lib/present";
import { matchExact, matchSearch, uniqueSorted } from "../../lib/list-filters";
import { getToken } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  Hint,
  inputClassName,
  Loading,
  OpsCard,
  PageHeader,
  StatusChip,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type Swap = { id: string; a: string; b: string; c: string; ca_id: string; trang_thai: string };

function swapHaystack(it: Swap): string {
  return [it.id, it.a, it.b, it.c, it.ca_id, swapLabel(it.trang_thai), nvLabel(it.a), nvLabel(it.b), nvLabel(it.c)].join(" ");
}

export default function DoiCaPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Swap[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [a, setA] = useState("");
  const [b, setB] = useState("");
  const [c, setC] = useState("");
  const [ca, setCa] = useState("w1_c01");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusF, setStatusF] = useState("all");
  const [personF, setPersonF] = useState("all");

  useEffect(() => {
    setToken(getToken());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<{ items: Swap[] }>("/api/v1/cho-doi-ca")
      .then((d) => {
        setItems((d.items ?? []).filter((x) => x && typeof x.id === "string"));
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "tải được chợ đổi ca" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  const statusOptions = useMemo(() => {
    const statuses = uniqueSorted(items.map((i) => i.trang_thai));
    return [{ value: "all", label: "Mọi trạng thái" }, ...statuses.map((s) => ({ value: s, label: swapLabel(s) }))];
  }, [items]);

  const personOptions = useMemo(() => {
    const people = uniqueSorted(items.flatMap((i) => [i.a, i.b, i.c]));
    return [{ value: "all", label: "Mọi người" }, ...people.map((p) => ({ value: p, label: nvLabel(p) }))];
  }, [items]);

  const filtered = useMemo(() => {
    return items.filter((it) => {
      if (!matchSearch(swapHaystack(it), search)) return false;
      if (!matchExact(it.trang_thai, statusF)) return false;
      if (personF !== "all" && ![it.a, it.b, it.c].includes(personF)) return false;
      return true;
    });
  }, [items, search, statusF, personF]);

  const filterActive = search.length > 0 || statusF !== "all" || personF !== "all";

  function clearFilters() {
    setSearch("");
    setStatusF("all");
    setPersonF("all");
  }

  const dayDu = a.trim() && b.trim() && c.trim() && ca.trim();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    if (!dayDu) {
      setError("Điền cả ba người và mã ca rồi mới mở được lệnh đổi.");
      return;
    }
    setBusy(true);
    try {
      await apiSend("/api/v1/cho-doi-ca", { a: a.trim(), b: b.trim(), c: c.trim(), ca_id: ca.trim() });
      setA("");
      setB("");
      setC("");
      setMsg("Đã mở lệnh đổi. Lệnh chỉ chốt khi cả ba nhánh đồng ý.");
      load();
    } catch (e) {
      setError(
        viError(e, {
          doing: "mở được lệnh đổi ca",
          missing: "Mã ca hoặc mã người không có trong quán. Kiểm tra lại trên Lịch tuần rồi nhập lại.",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="Ba nhánh phải đồng ý"
        title="Chợ đổi ca"
        meta="Đổi ca chỉ thành khi người nhả, người nhận và quản lý cùng đồng ý."
      />
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      <OpsCard eyebrow="Khu vực 1" title="Mở lệnh mới">
        <form onSubmit={onSubmit}>
          <Field label="Người nhả ca">
            <input className={inputClassName} value={a} onChange={(e) => setA(e.target.value)} />
          </Field>
          <Field label="Người nhận ca">
            <input className={inputClassName} value={b} onChange={(e) => setB(e.target.value)} />
          </Field>
          <Field label="Người xác nhận">
            <input className={inputClassName} value={c} onChange={(e) => setC(e.target.value)} />
          </Field>
          <Hint>Nhập mã nhân viên như trên Lịch tuần, ví dụ nv_01.</Hint>
          <Field label="Mã ca cần đổi">
            <input className={inputClassName} value={ca} onChange={(e) => setCa(e.target.value)} />
          </Field>
          <Btn type="submit" variant="primary" disabled={busy}>
            {busy ? "Đang mở lệnh…" : "Mở lệnh đổi ca"}
          </Btn>
        </form>
      </OpsCard>

      <OpsCard eyebrow="Khu vực 2" title="Lệnh đang mở" count={filtered.length} countLabel="lệnh">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm người, mã ca, trạng thái…"
          status={statusF}
          onStatusChange={setStatusF}
          statusOptions={statusOptions}
          person={personF}
          onPersonChange={setPersonF}
          personOptions={personOptions}
          shown={filtered.length}
          total={items.length}
          filtered={filterActive}
        />
        {loading ? <Loading skeleton="list">Đang tải lệnh đổi ca…</Loading> : null}
        {!loading && !error && items.length === 0 ? (
          <Empty title="Chưa có lệnh">Chưa có lệnh đổi ca nào đang mở.</Empty>
        ) : null}
        {!loading && items.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
        <div className="nq-list">
          {filtered.map((it) => (
            <article key={it.id} className="nq-item">
              <p className="nq-item-title">
                {nvLabel(it.a)} nhả · {nvLabel(it.b)} nhận · {nvLabel(it.c)} xác nhận
              </p>
              <p className="nq-item-sub">
                <StatusChip tone={it.trang_thai === "dong_y" ? "ok" : "warn"}>
                  {swapLabel(it.trang_thai)}
                </StatusChip>
                {it.ca_id ? ` · ca ${safeText(it.ca_id)}` : ""}
              </p>
            </article>
          ))}
        </div>
      </OpsCard>
    </div>
  );
}
