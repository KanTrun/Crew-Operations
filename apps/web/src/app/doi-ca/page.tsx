"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { getRole, getToken } from "../../lib/session";
import { caHumanLabel, nvLabel, nvTenHienThi, safeText, swapLabel, thuLabel, viError } from "../../lib/present";
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
  schedule_run_id: string;
  tuan_iso: string;
  ca_id: string;
  status: string;
  deadline_at: string;
  claimed_by?: string | null;
  claimed_at?: string | null;
  escalated_at?: string | null;
};

const OPEN_SHIFT_STATUS: Record<string, string> = {
  open: "Đang chờ người nhận",
  claimed: "Đã có người nhận",
  resolved: "Đã xử lý",
};

function isoWeekMonday(week: string): Date | null {
  const match = /^(\d{4})-W(\d{2})$/.exec(week);
  if (!match) return null;
  const year = Number(match[1]);
  const weekNumber = Number(match[2]);
  const januaryFourth = new Date(year, 0, 4);
  const monday = new Date(januaryFourth);
  monday.setHours(0, 0, 0, 0);
  monday.setDate(januaryFourth.getDate() - ((januaryFourth.getDay() + 6) % 7) + (weekNumber - 1) * 7);
  return monday;
}

function openShiftDate(week: string, weekday?: string): string {
  const offsets: Record<string, number> = { T2: 0, T3: 1, T4: 2, T5: 3, T6: 4, T7: 5, CN: 6 };
  const monday = isoWeekMonday(week);
  const offset = weekday ? offsets[weekday] : undefined;
  if (!monday || offset === undefined) return "Ngày chưa xác định";
  monday.setDate(monday.getDate() + offset);
  return monday.toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric" });
}

function validDate(value?: string | null): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function dateTimeLabel(value?: string | null): string {
  return validDate(value)?.toLocaleString("vi-VN") ?? "Chưa có thời gian";
}

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
  const [openShiftLoading, setOpenShiftLoading] = useState(true);
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
    setOpenShiftLoading(true);
    apiGet<{ items: OpenShift[] }>(`/api/v1/open-shifts?tuan_iso=${encodeURIComponent(openShiftWeek)}`)
      .then((payload) => {
        setOpenShifts((payload.items ?? []).filter((item) => item && typeof item.id === "string"));
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "tải ca đang cần người" })))
      .finally(() => setOpenShiftLoading(false));
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

  function openShiftSchedule(openShift: OpenShift) {
    const shift = pickers?.ca.find((item) => item.id === openShift.ca_id);
    return {
      date: openShiftDate(openShift.tuan_iso, shift?.thu),
      weekday: shift?.thu ? thuLabel(shift.thu) : "Chưa rõ thứ",
    };
  }

  function personLabel(id: string) {
    const hit = pickers?.nhan_vien.find((x) => x.id === id);
    return hit ? nvTenHienThi(hit.ten, id) : nvLabel(id);
  }

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--run">
      <PageHeader
        kicker="Điều phối nhân sự"
        title="Ca mở & đổi ca"
        meta="Ca thiếu do hệ thống mở và phiếu đổi giữa nhân viên là hai quy trình riêng."
      />
      <Btn variant="ghost" onClick={() => setCopilotOpen(true)}>
        Hỏi trợ lý vận hành
      </Btn>
      {error ? <Alert>{error}</Alert> : null}
      {msg ? <Alert kind="ok">{msg}</Alert> : null}

      <OpsCard eyebrow="Hệ thống tự động mở" title="Ca thiếu người" count={openShifts.length} countLabel="ca">
        <div className="mb-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_minmax(12rem,18rem)] sm:items-end">
          <p className="text-sm text-[var(--nq-dim)]">
            Các ca này phát sinh khi lịch tự động chưa đủ người. Đây không phải phiếu một nhân viên nhả ca cho người khác.
          </p>
          <label className="block text-sm text-[var(--nq-dim)]">
          Tuần cần xem
          <input
            type="week"
            value={openShiftWeek}
            onChange={(event) => setOpenShiftWeek(event.target.value)}
            className="mt-1 block min-h-10 w-full border border-[var(--nq-line)] bg-[var(--nq-panel)] px-3 text-[var(--nq-text)]"
          />
          </label>
        </div>
        {openShiftLoading ? <Loading skeleton="list">Đang tải ca thiếu người…</Loading> : null}
        {!openShiftLoading && openShifts.length === 0 ? (
          <Empty title="Không có ca thiếu người">Tuần này không còn ca tự động mở cần xử lý.</Empty>
        ) : null}
        {!openShiftLoading ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {openShifts.map((openShift) => {
              const schedule = openShiftSchedule(openShift);
              const deadline = validDate(openShift.deadline_at);
              const expired = deadline ? deadline.getTime() <= Date.now() : false;
              const escalated = Boolean(openShift.escalated_at);
              const claimed = openShift.status === "claimed";
              const actionable = employeeMode && openShift.status === "open" && !expired && !escalated;
              const statusTone = claimed ? "ok" : expired || escalated ? "danger" : "warn";
              return (
                <article key={openShift.id} className="nq-item min-w-0">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="nq-item-title">{caLabel(openShift.ca_id)}</p>
                      <p className="nq-item-sub">
                        Tuần {openShift.tuan_iso} · {schedule.weekday}, {schedule.date}
                      </p>
                    </div>
                    <StatusChip tone={statusTone}>
                      {escalated ? "Quá hạn · đã báo quản lý" : expired ? "Đã hết hạn" : OPEN_SHIFT_STATUS[openShift.status] ?? safeText(openShift.status, "Chưa rõ")}
                    </StatusChip>
                  </div>

                  <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
                    <div>
                      <dt className="text-xs text-[var(--nq-dim)]">Hạn nhận ca</dt>
                      <dd className={expired ? "font-semibold text-[var(--nq-red)]" : "font-semibold"}>
                        {dateTimeLabel(openShift.deadline_at)}
                      </dd>
                    </div>
                    <div>
                      <dt className="text-xs text-[var(--nq-dim)]">Trạng thái xử lý</dt>
                      <dd className="font-semibold">
                        {claimed
                          ? `${openShift.claimed_by ? personLabel(openShift.claimed_by) : "Đã có nhân viên"} nhận lúc ${dateTimeLabel(openShift.claimed_at)}`
                          : escalated
                            ? `Chờ quản lý xử lý từ ${dateTimeLabel(openShift.escalated_at)}`
                            : expired
                              ? "Hết thời gian tự nhận, cần quản lý xử lý"
                              : "Đang trong thời gian nhân viên nhận ca"}
                      </dd>
                    </div>
                  </dl>

                  <div className="mt-3 border-t border-[var(--nq-line)] pt-3">
                    {actionable ? (
                      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                        <p className="text-xs text-[var(--nq-dim)]">
                          Bạn có thể nhận nếu đã xác nhận khả dụng tuần này và chưa được xếp vào ca.
                        </p>
                        <Btn
                          variant="primary"
                          busy={claimingShift === openShift.id}
                          disabled={claimingShift !== null}
                          onClick={() => void claimOpenShift(openShift)}
                        >
                          Nhận ca này
                        </Btn>
                      </div>
                    ) : (
                      <p className="text-xs font-semibold text-[var(--nq-dim)]">
                        {claimed
                          ? "Quản lý cần chốt nhân sự và chạy lại lịch để giải quyết ca thiếu."
                          : expired || escalated
                            ? "Không còn nhận trực tiếp. Quản lý cần phân công và xử lý trên lịch tuần."
                            : employeeMode
                              ? "Ca này hiện không thể nhận."
                              : "Chỉ tài khoản nhân viên mới có thể nhận ca đang mở."}
                      </p>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        ) : null}
      </OpsCard>

      <OpsCard eyebrow="Nhân viên đổi với nhau · Khu vực 1" title="Mở phiếu đổi ca">
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

      <OpsCard eyebrow="Nhân viên đổi với nhau · Khu vực 2" title="Phiếu đổi đang mở" count={filtered.length} countLabel="phiếu">
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
