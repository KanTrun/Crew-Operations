"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getRole, getToken } from "../../lib/session";
import { caHumanLabel, nvLabel, nvTenHienThi, safeText, swapLabel, viError } from "../../lib/present";
import { matchExact, matchSearch, uniqueSorted } from "../../lib/list-filters";
import { useOpsPickers } from "../../lib/ops-context";
import {
  Alert,
  AuthGate,
  Btn,
  BtnLink,
  Empty,
  Loading,
  OpsCard,
  PageHeader,
  StatusChip,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";
import { ShiftSelect } from "../../ui/ops-pickers";
import { CopilotPane } from "../../ui/copilot/CopilotPane";

type Swap = {
  id: string;
  a: string;
  b: string;
  ca_id: string;
  trang_thai: string;
  dong_y?: string[];
};

type OpenShift = {
  id: string;
  tuan_iso: string;
  ca_id: string;
  deadline_at: string;
};

function currentISOWeek(): string {
  const now = new Date();
  const date = new Date(now);
  date.setHours(0, 0, 0, 0);
  date.setDate(date.getDate() + 3 - ((date.getDay() + 6) % 7));
  const weekOne = new Date(date.getFullYear(), 0, 4);
  const week = 1 + Math.round(((date.getTime() - weekOne.getTime()) / 86400000 - 3 + ((weekOne.getDay() + 6) % 7)) / 7);
  return `${date.getFullYear()}-W${String(week).padStart(2, "0")}`;
}

function swapHaystack(it: Swap): string {
  return [it.id, it.a, it.b, it.ca_id, swapLabel(it.trang_thai), nvLabel(it.a), nvLabel(it.b)].join(" ");
}

export default function DoiCaPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Swap[]>([]);
  const [openShifts, setOpenShifts] = useState<OpenShift[]>([]);
  const [openShiftWeek, setOpenShiftWeek] = useState(currentISOWeek());
  const [claimingShift, setClaimingShift] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [msg, setMsg] = useState<string | null>(null);
  const [b, setB] = useState("");
  const [ca, setCa] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusF, setStatusF] = useState("all");
  const [personF, setPersonF] = useState("all");
  const [copilotOpen, setCopilotOpen] = useState(false);
  const { data: pickers } = useOpsPickers(!!token);
  const meNv = pickers?.me_nv_id ?? null;
  const employeeMode = getRole() === "nhan_vien";

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

  const loadOpenShifts = useCallback(() => {
    if (!getToken()) return;
    apiGet<{ items: OpenShift[] }>(`/api/v1/open-shifts?tuan_iso=${encodeURIComponent(openShiftWeek)}`)
      .then((payload) => setOpenShifts(payload.items ?? []))
      .catch((e) => setError(viError(e, { doing: "tải ca đang cần người" })));
  }, [openShiftWeek]);

  useEffect(() => {
    if (token) loadOpenShifts();
  }, [token, loadOpenShifts]);

  const statusOptions = useMemo(() => {
    const statuses = uniqueSorted(items.map((i) => i.trang_thai));
    return [{ value: "all", label: "Mọi trạng thái" }, ...statuses.map((s) => ({ value: s, label: swapLabel(s) }))];
  }, [items]);

  const personOptions = useMemo(() => {
    const people = uniqueSorted(items.flatMap((i) => [i.a, i.b]));
    return [{ value: "all", label: "Mọi người" }, ...people.map((p) => ({ value: p, label: nvLabel(p) }))];
  }, [items]);

  const available = useMemo(() => {
    if (!meNv) return [];
    return items.filter((it) => it.trang_thai !== "dong_y" && (it.b === meNv || it.b === "all"));
  }, [items, meNv]);

  const filtered = useMemo(() => {
    return available.filter((it) => {
      if (!matchSearch(swapHaystack(it), search)) return false;
      if (!matchExact(it.trang_thai, statusF)) return false;
      if (personF !== "all" && ![it.a, it.b].includes(personF)) return false;
      return true;
    });
  }, [available, search, statusF, personF]);

  const filterActive = search.length > 0 || statusF !== "all" || personF !== "all";

  function clearFilters() {
    setSearch("");
    setStatusF("all");
    setPersonF("all");
  }

  const dayDu = meNv && b.trim() && ca.trim();

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMsg(null);
    if (!dayDu) {
      setError("Chọn người nhận và ca rồi mới mở được lệnh đổi.");
      return;
    }
    setBusy(true);
    try {
      await apiSend("/api/v1/cho-doi-ca", { a: meNv, b: b.trim(), ca_id: ca.trim() });
      setB("");
      setMsg("Đã mở phiếu đổi ca.");
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

  async function claimOpenShift(openShift: OpenShift) {
    setClaimingShift(openShift.id);
    setError(null);
    setMsg(null);
    try {
      await apiSend("/api/v1/open-shifts/claim", { open_shift_id: openShift.id });
      setMsg("Bạn đã nhận ca thành công. Quản lý sẽ thấy thay đổi khi chạy lại lịch.");
      loadOpenShifts();
    } catch (e) {
      setError(viError(e, { doing: "nhận ca mở" }));
    } finally {
      setClaimingShift(null);
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
        kicker="Đổi ca giữa hai người"
        title="Chợ đổi ca"
        meta="Bạn nhả ca, một người nhận ca chốt phiếu."
      />
      <Btn variant="ghost" onClick={() => setCopilotOpen(true)}>
        Hỏi trợ lý vận hành
      </Btn>
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      <OpsCard eyebrow="Ca mở" title="Ca đang cần người" count={openShifts.length} countLabel="ca">
        <label className="mb-4 block max-w-xs text-sm text-[var(--nq-dim)]">
          Tuần ISO
          <input
            type="week"
            value={openShiftWeek}
            onChange={(event) => setOpenShiftWeek(event.target.value)}
            className="mt-1 block min-h-10 w-full border border-[var(--nq-line)] bg-[var(--nq-panel)] px-3 text-[var(--nq-text)]"
          />
        </label>
        {openShifts.length === 0 ? <Empty title="Không có ca mở">Tuần này chưa có ca nào đang chờ nhận.</Empty> : null}
        <div className="nq-list">
          {openShifts.map((openShift) => (
            <article key={openShift.id} className="nq-item">
              <p className="nq-item-title">{caLabel(openShift.ca_id)}</p>
              <p className="nq-item-sub">Hạn nhận: {new Date(openShift.deadline_at).toLocaleString("vi-VN")}</p>
              {employeeMode ? (
                <div className="mt-2">
                  <Btn
                    variant="primary"
                    busy={claimingShift === openShift.id}
                    disabled={claimingShift !== null}
                    onClick={() => void claimOpenShift(openShift)}
                  >
                    Nhận ca này
                  </Btn>
                </div>
              ) : null}
            </article>
          ))}
        </div>
      </OpsCard>

      <OpsCard eyebrow="Khu vực 1" title="Mở lệnh mới">
        <form onSubmit={onSubmit}>
          <p className="nq-muted mb-3">Người nhả ca: {meNv ? personLabel(meNv) : "Đang tải tài khoản…"}</p>
          <select className="nq-select mb-3" value={b} onChange={(e) => setB(e.target.value)} aria-label="Người nhận ca">
            <option value="">Chọn người nhận…</option>
            <option value="all">Mọi người</option>
            {(pickers?.nhan_vien ?? []).map((n) => (
              <option key={n.id} value={n.id}>{nvTenHienThi(n.ten, n.id)}</option>
            ))}
          </select>
          <ShiftSelect value={ca} onChange={setCa} label="Ca cần đổi" shifts={pickers?.ca} />
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
          total={available.length}
          filtered={filterActive}
        />
        {loading ? <Loading skeleton="list">Đang tải lệnh đổi ca…</Loading> : null}
        {!loading && !error && available.length === 0 ? (
          <Empty title="Chưa có lệnh">Chưa có lệnh đổi ca nào đang mở.</Empty>
        ) : null}
        {!loading && available.length > 0 && filtered.length === 0 ? <FilteredEmpty onClear={clearFilters} /> : null}
        <div className="nq-list">
          {filtered.map((it) => {
            const agreed = new Set(it.dong_y ?? []);
            const recipient = it.b === "all" || it.b === meNv;
            const canAgree = meNv && recipient && it.a !== meNv && !agreed.has(meNv);
            return (
              <article key={it.id} className="nq-item">
                <p className="nq-item-title">
                  {personLabel(it.a)} nhả · {it.b === "all" ? "Mọi người" : `${personLabel(it.b)} nhận`}
                </p>
                <p className="nq-item-sub">
                  <StatusChip tone={it.trang_thai === "dong_y" ? "ok" : "warn"}>
                    {swapLabel(it.trang_thai)}
                  </StatusChip>
                  {it.ca_id ? ` · ${caLabel(it.ca_id)}` : ""}
                </p>
                <p className="nq-item-sub text-xs mt-2">
                  {agreed.size > 0 ? `Đã có người nhận: ${[...agreed].map(personLabel).join(", ")}` : "Chưa có ai nhận ca"}
                </p>
                {canAgree ? (
                  <div className="flex gap-2 mt-2">
                    <Btn variant="primary" busy={busy} onClick={() => {
                      if (window.confirm(`Bạn nhận ca do ${personLabel(it.a)} nhả ra không?`)) void dongY(it.id);
                    }}>
                      Tôi nhận ca
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

      <OpsCard eyebrow="Đổi ca giữa hai người" title="Phiếu được chốt thế nào?">
        <p className="mb-3 text-sm text-[var(--nq-dim)]">
          Người <strong>nhả</strong> mở phiếu cho một người nhận hoặc mọi người. Người nhận xem tên người
          nhả ca trước khi nhận. Phiếu đã có người nhận sẽ không còn hiện trong chợ.
        </p>
        <div className="flex flex-wrap gap-3">
          <BtnLink href="/inbox">Hộp thư duyệt →</BtnLink>
          <BtnLink href="/cong-bang" variant="ghost">Xem công bằng</BtnLink>
        </div>
      </OpsCard>
      <CopilotPane open={copilotOpen} onClose={() => setCopilotOpen(false)} />
    </div>
  );
}
