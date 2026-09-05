"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getToken } from "../../lib/session";
import { caHumanLabel, nvLabel, nvTenHienThi, safeText, swapLabel, viError } from "../../lib/present";
import { matchExact, matchSearch, uniqueSorted } from "../../lib/list-filters";
import { useOpsPickers } from "../../lib/ops-context";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Loading,
  OpsCard,
  PageHeader,
  StatusChip,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";
import { PersonSelect, ShiftSelect } from "../../ui/ops-pickers";
import { CopilotPane } from "../../ui/copilot/CopilotPane";

type Swap = {
  id: string;
  a: string;
  b: string;
  c: string;
  ca_id: string;
  trang_thai: string;
  dong_y?: string[];
};

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
  const [ca, setCa] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusF, setStatusF] = useState("all");
  const [personF, setPersonF] = useState("all");
  const [copilotOpen, setCopilotOpen] = useState(false);
  const { data: pickers } = useOpsPickers(!!token);
  const meNv = pickers?.me_nv_id ?? null;

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
      setError("Chọn đủ ba người và một ca rồi mới mở được lệnh đổi.");
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
          missing: "Ca hoặc người không hợp lệ. Chọn lại từ danh sách.",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  async function dongY(id: string) {
    setBusy(true);
    setError(null);
    try {
      await apiSend(`/api/v1/cho-doi-ca/${encodeURIComponent(id)}/dong-y`, {});
      setMsg("Đã ghi nhận đồng ý của bạn.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "ghi nhận đồng ý đổi ca" }));
    } finally {
      setBusy(false);
    }
  }

  async function tuChoi(id: string) {
    setBusy(true);
    setError(null);
    try {
      await apiSend(`/api/v1/cho-doi-ca/${encodeURIComponent(id)}/tu-choi`, {});
      setMsg("Đã từ chối lệnh đổi ca.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "từ chối đổi ca" }));
    } finally {
      setBusy(false);
    }
  }

  function caLabel(caId: string) {
    const hit = pickers?.ca.find((x) => x.id === caId);
    return caHumanLabel(hit, caId);
  }

  function personLabel(id: string) {
    const hit = pickers?.nhan_vien.find((x) => x.id === id);
    return hit ? nvTenHienThi(hit.ten, id) : nvLabel(id);
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="Ba nhánh phải đồng ý"
        title="Chợ đổi ca"
        meta="Chọn người nhả, người nhận, người xác nhận và ca — mỗi nhánh bấm đồng ý trên lệnh."
      />
      <Btn variant="ghost" onClick={() => setCopilotOpen(true)}>
        Hỏi trợ lý vận hành
      </Btn>
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      <OpsCard eyebrow="Khu vực 1" title="Mở lệnh mới">
        <form onSubmit={onSubmit}>
          <PersonSelect value={a} onChange={setA} label="Người nhả ca" staff={pickers?.nhan_vien} />
          <PersonSelect value={b} onChange={setB} label="Người nhận ca" staff={pickers?.nhan_vien} />
          <PersonSelect value={c} onChange={setC} label="Người xác nhận" staff={pickers?.nhan_vien} />
          <ShiftSelect value={ca} onChange={setCa} label="Ca cần đổi" shifts={pickers?.ca} />
          {meNv ? (
            <p className="nq-muted text-sm mb-3">
              Gợi ý: bạn có thể chọn mình làm một trong ba nhánh nếu tham gia đổi ca.
            </p>
          ) : null}
          <Btn type="submit" variant="primary" disabled={busy}>
            {busy ? "Đang mở lệnh…" : "Mở lệnh đổi ca"}
          </Btn>
        </form>
      </OpsCard>

      <OpsCard eyebrow="Khu vực 2" title="Lệnh đang mở" count={filtered.length} countLabel="lệnh">
        <ListToolbar
          search={search}
          onSearchChange={setSearch}
          searchPlaceholder="Tìm người, ca, trạng thái…"
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
          {filtered.map((it) => {
            const agreed = new Set(it.dong_y ?? []);
            const parties = [it.a, it.b, it.c];
            const canAgree = meNv && parties.includes(meNv) && !agreed.has(meNv) && it.trang_thai !== "dong_y";
            return (
              <article key={it.id} className="nq-item">
                <p className="nq-item-title">
                  {personLabel(it.a)} nhả · {personLabel(it.b)} nhận · {personLabel(it.c)} xác nhận
                </p>
                <p className="nq-item-sub">
                  <StatusChip tone={it.trang_thai === "dong_y" ? "ok" : "warn"}>
                    {swapLabel(it.trang_thai)}
                  </StatusChip>
                  {it.ca_id ? ` · ${caLabel(it.ca_id)}` : ""}
                </p>
                <p className="nq-item-sub text-xs mt-2">
                  Đồng ý: {parties.map((p) => (agreed.has(p) ? `✓ ${personLabel(p)}` : `○ ${personLabel(p)}`)).join(" · ")}
                </p>
                {canAgree ? (
                  <div className="flex gap-2 mt-2">
                    <Btn variant="primary" busy={busy} onClick={() => void dongY(it.id)}>
                      Tôi đồng ý
                    </Btn>
                    <Btn variant="danger" disabled={busy} onClick={() => void tuChoi(it.id)}>
                      Từ chối
                    </Btn>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      </OpsCard>
      <CopilotPane open={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </div>
  );
}
