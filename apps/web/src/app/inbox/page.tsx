"use client";

/**
 * Hộp thư ràng buộc — 14 mục, sáu ý định, ba trạng thái.
 *
 * Ba thứ trước đây thiếu, và thiếu cái nào thì người duyệt cũng phải mở trang
 * khác để bù:
 *  1. **Nhóm theo trạng thái.** Mục chờ duyệt lẫn giữa mục đã quyết thì người
 *     duyệt phải tự lọc bằng mắt. Chờ duyệt lên đầu vì đó là việc còn phải làm.
 *  2. **Chip ý định.** `xin_nghi` khác `doi_ca` khác `bao_tre` về hệ quả; biết
 *     loại trước khi đọc hết tóm tắt là tiết kiệm một nhịp.
 *  3. **Độ tin cậy.** Máy chủ trả `do_tin_cay` cho mỗi bản tóm tắt. Duyệt một
 *     bản tóm tắt 63% mà không biết nó 63% là duyệt mù.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiGet, apiSend } from "../../lib/api";
import {
  matchExact,
  matchSearch,
  matchTime,
  TIME_FILTER_OPTIONS,
  uniqueSorted,
  type TimeFilter,
} from "../../lib/list-filters";
import {
  agentLabel,
  formatLuc,
  inboxLabel,
  inboxTone,
  khungLabel,
  rangBuocLabel,
  safeText,
  thuLabel,
  viError,
  yDinhLabel,
} from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  BtnLink,
  Confidence,
  Empty,
  Group,
  Loading,
  NextSteps,
  Notice,
  PageHeader,
  Row,
  StatusChip,
  Summary,
  Toasts,
  useToasts,
} from "../../ui/kit";
import { FilteredEmpty, ListToolbar } from "../../ui/list-filters";

type Item = {
  id: string;
  tom_tat: string;
  trang_thai: string;
  agent: string;
  y_dinh?: string;
  do_tin_cay?: number;
  created_at?: string;
  rang_buoc?: { loai?: string; thu?: string; khung?: string };
};

/** Chờ duyệt trước — đó là việc còn phải làm; đã quyết chỉ để tra lại. */
const THU_TU = ["cho_duyet", "moi", "duyet", "tu_choi"];

const TEN_NHOM: Record<string, string> = {
  cho_duyet: "Chờ bạn quyết",
  moi: "Mới vào hộp thư",
  duyet: "Đã duyệt",
  tu_choi: "Đã từ chối",
};

export default function InboxPage() {
  const [token, setToken] = useState("");
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [manager, setManager] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusF, setStatusF] = useState("all");
  const [personF, setPersonF] = useState("all");
  const [timeF, setTimeF] = useState<TimeFilter>("all");
  const { toasts, push, dismiss } = useToasts();

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    apiGet<{ items: Item[] }>("/api/v1/inbox/rang-buoc")
      .then((d) => {
        setItems((d.items ?? []).filter((x) => x && typeof x.id === "string"));
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "mở được hộp thư ràng buộc" })))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  async function decide(id: string, quyet_dinh: "duyet" | "tu_choi") {
    setBusy(id);
    setError(null);
    try {
      await apiSend(`/api/v1/inbox/rang-buoc/${id}`, { quyet_dinh });
      push(
        quyet_dinh === "duyet"
          ? "Đã duyệt. Ràng buộc này vào lượt xếp lịch tới."
          : "Đã từ chối. Ràng buộc này không vào lượt xếp lịch.",
      );
      load();
    } catch (e) {
      setError(
        viError(e, {
          doing: quyet_dinh === "duyet" ? "duyệt được mục này" : "từ chối được mục này",
          forbidden: "Chỉ quản lý hoặc chủ quán mới quyết được mục trong hộp thư.",
          missing: "Mục này không còn trong hộp thư — có thể người khác đã quyết. Tải lại hộp thư.",
        }),
      );
    } finally {
      setBusy(null);
    }
  }

  const personOptions = useMemo(
    () => [
      { value: "all", label: "Mọi agent" },
      ...uniqueSorted(items.map((i) => i.agent)).map((v) => ({ value: v, label: agentLabel(v) })),
    ],
    [items],
  );

  const statusOptions = useMemo(
    () => [{ value: "all", label: "Mọi trạng thái" }, ...THU_TU.map((s) => ({ value: s, label: TEN_NHOM[s] ?? inboxLabel(s) }))],
    [],
  );

  const filtered = useMemo(
    () =>
      items.filter((it) => {
        if (!matchSearch([it.tom_tat, it.agent, it.rang_buoc?.loai ?? ""].join(" "), search)) return false;
        if (!matchExact(it.trang_thai, statusF)) return false;
        if (!matchExact(it.agent, personF)) return false;
        if (!matchTime(it.created_at, timeF)) return false;
        return true;
      }),
    [items, search, statusF, personF, timeF],
  );

  const filterActive = search.length > 0 || statusF !== "all" || personF !== "all" || timeF !== "all";

  function clearFilters() {
    setSearch("");
    setStatusF("all");
    setPersonF("all");
    setTimeF("all");
  }

  const nhom = useMemo(() => {
    const m = new Map<string, Item[]>();
    for (const it of filtered) {
      const k = safeText(it.trang_thai, "moi");
      m.set(k, [...(m.get(k) ?? []), it]);
    }
    const keys = [...THU_TU, ...Array.from(m.keys()).filter((k) => !THU_TU.includes(k))];
    return keys.filter((k) => (m.get(k) ?? []).length > 0).map((k) => [k, m.get(k) ?? []] as const);
  }, [filtered]);

  const dem = useCallback(
    (tt: string) => items.filter((x) => safeText(x.trang_thai, "moi") === tt).length,
    [items],
  );

  /** Số ý định khác nhau đang có trong hộp — cho thấy hộp thư đang gánh loại việc gì. */
  const soYDinh = useMemo(
    () => new Set(items.map((x) => safeText(x.y_dinh, "khac"))).size,
    [items],
  );

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Người duyệt · hệ thống không tự chọn"
        title="Hộp thư ràng buộc"
        meta="Nơi xử những ràng buộc mâu thuẫn nhau: người đọc rồi quyết, hệ thống không chọn hộ."
      />

      {items.length > 0 ? (
        <Summary
          cells={[
            { n: items.length, k: "mục trong hộp" },
            { n: dem("cho_duyet"), k: "chờ quyết", tone: "warn" },
            { n: dem("duyet"), k: "đã duyệt", tone: "ok" },
            { n: dem("tu_choi"), k: "đã từ chối", tone: "danger" },
            { n: soYDinh, k: "loại ý định" },
          ]}
        />
      ) : null}

      {error ? <Alert>{error}</Alert> : null}
      {!manager ? <Notice>Bạn xem được nội dung. Quản lý hoặc chủ quán mới bấm duyệt.</Notice> : null}

      <ListToolbar
        search={search}
        onSearchChange={setSearch}
        searchPlaceholder="Tìm tóm tắt, agent, ràng buộc…"
        status={statusF}
        onStatusChange={setStatusF}
        statusOptions={statusOptions}
        person={personF}
        onPersonChange={setPersonF}
        personOptions={personOptions}
        personLabel="Agent"
        time={timeF}
        onTimeChange={(v) => setTimeF(v as TimeFilter)}
        timeOptions={TIME_FILTER_OPTIONS}
        shown={filtered.length}
        total={items.length}
        filtered={filterActive}
      />

      {loading ? <Loading skeleton="rows" rows={4} groups={3}>Đang mở hộp thư…</Loading> : null}
      {!loading && !error && items.length === 0 ? (
        <Empty>Hộp thư sạch — không có ràng buộc nào chờ người quyết.</Empty>
      ) : null}
      {!loading && items.length > 0 && filtered.length === 0 ? (
        <FilteredEmpty onClear={clearFilters} />
      ) : null}

      {!loading &&
        nhom.map(([tt, list]) => (
          <Group key={tt} title={TEN_NHOM[tt] ?? inboxLabel(tt)} count={list.length} countLabel="mục">
            {list.map((it) => (
              <Row
                key={it.id}
                title={safeText(it.tom_tat, "Ràng buộc chưa có tóm tắt")}
                sub={
                  <>
                    {agentLabel(it.agent)} · ràng buộc {rangBuocLabel(it.rang_buoc?.loai).toLowerCase()}
                    {it.rang_buoc?.thu ? ` · ${thuLabel(it.rang_buoc.thu)}` : ""}
                    {it.rang_buoc?.khung ? ` ${khungLabel(it.rang_buoc.khung).toLowerCase()}` : ""}
                    {it.created_at ? ` · ${formatLuc(it.created_at)}` : ""}
                  </>
                }
                side={
                  <>
                    <StatusChip tone={inboxTone(it.trang_thai)}>{inboxLabel(it.trang_thai)}</StatusChip>
                    <StatusChip>{yDinhLabel(it.y_dinh)}</StatusChip>
                    <Confidence value={it.do_tin_cay} />
                  </>
                }
                actions={
                  it.trang_thai === "cho_duyet" && manager ? (
                    <>
                      <Btn
                        variant="primary"
                        busy={busy === it.id}
                        busyLabel="Đang ghi quyết định…"
                        onClick={() => decide(it.id, "duyet")}
                      >
                        Duyệt ràng buộc
                      </Btn>
                      <Btn
                        variant="danger"
                        disabled={busy === it.id}
                        onClick={() => decide(it.id, "tu_choi")}
                      >
                        Từ chối
                      </Btn>
                    </>
                  ) : undefined
                }
              />
            ))}
          </Group>
        ))}

      {!loading && items.length > 0 ? (
        <p className="nq-table-note">
          Thanh bên phải là độ tin cậy của bản tóm tắt do agent đọc từ tin nhắn trong ca. Dưới 70% thì
          mở tin gốc đọc lại trước khi quyết.
        </p>
      ) : null}

      <NextSteps note="Ràng buộc đã duyệt chỉ có tác dụng ở lượt xếp lịch kế tiếp.">
        <BtnLink href="/roster">Xếp lịch tuần</BtnLink>
        <BtnLink href="/vet" variant="ghost">
          Xem vết các quyết định
        </BtnLink>
        <Btn variant="ghost" onClick={load}>
          Tải lại hộp thư
        </Btn>
      </NextSteps>

      <Toasts toasts={toasts} onDismiss={dismiss} />
    </div>
  );
}
