"use client";

/**
 * SpatialAnchorDetails — chi tiết neo: ký ức đã xác nhận + ký ức chờ duyệt.
 *
 * Bản trước chỉ đọc và in: ký ức `draft` treo vĩnh viễn vì API có đường cấp
 * đồng thuận và đường xoá nhưng không UI nào gọi. Bản này nối đủ ba hành động
 * nghiệp vụ — đồng ý, từ chối, xoá — và làm mới số đếm ở trang cha sau mỗi lần
 * đổi, để cột 3D và danh sách không lệch nhau.
 */

import { useCallback, useEffect, useState } from "react";
import { ApiError, apiSend } from "../../../lib/api";
import { viError } from "../../../lib/present";
import { Icon } from "../../icons";
import { ExpEmpty } from "../exp-kit";
import MemoryTimeline from "./MemoryTimeline";

interface AnchorDetail {
  anchor: { anchor_id: string; label: string; kind: string };
  confirmed_memories: Memory[];
  pending_memories: Memory[];
}

interface Memory {
  memory_id: string;
  content: string;
  status: string;
  consent_status: string;
  visibility: string;
  retention_until?: string | null;
}

interface Props {
  anchorId: string;
  /** Nhãn đọc được của neo — dùng khi bản đồ chưa kịp nạp chi tiết. */
  anchorLabel?: string;
  onChanged?: () => void;
}

const KIND_LABEL: Record<string, string> = {
  khu_vuc: "Khu vực",
  ban: "Bàn",
  thiet_bi: "Thiết bị",
};

/** Câu lỗi cho từng thao tác trên ký ức — giữ tiếng Việt ở một chỗ. */
const COPY = {
  read: { doing: "đọc được ký ức của khu vực này" },
  decide: { doing: "đổi đồng thuận cho ký ức này" },
  remove: { doing: "xoá ký ức này" },
} as const;

export default function SpatialAnchorDetails({ anchorId, anchorLabel, onChanged }: Props) {
  const [data, setData] = useState<AnchorDetail | null>(null);
  /** Lỗi tải giữ nguyên đối tượng để `viError` đọc được mã HTTP. */
  const [loadError, setLoadError] = useState<unknown>(null);
  /** Lỗi thao tác đã dịch sẵn — hiện ngay cạnh nút vừa bấm. */
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [rev, setRev] = useState(0);

  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
  const token =
    typeof window !== "undefined" &&
    (window.sessionStorage.getItem("nq_token") ||
      window.localStorage.getItem("nq_token"));
  const tokenStr = typeof token === "string" ? token : "";

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setLoadError(null);
    fetch(`${base}/api/v1/experience/anchors/${anchorId}`, {
      headers: tokenStr ? { Authorization: `Bearer ${tokenStr}` } : {},
    })
      .then((r) => {
        if (!r.ok) throw new ApiError(r.status);
        return r.json() as Promise<AnchorDetail>;
      })
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch((e) => {
        if (!cancelled) setLoadError(e);
      });
    return () => {
      cancelled = true;
    };
  }, [base, anchorId, tokenStr, rev]);

  /** Cấp hoặc thu hồi đồng thuận — quyết định của người có quyền, có ghi vết. */
  const decide = useCallback(
    async (memoryId: string, grant: boolean) => {
      setBusyId(memoryId);
      setNotice(null);
      setActionError(null);
      try {
        await apiSend(`/api/v1/experience/memories/${memoryId}/consent`, { grant });
        setNotice(
          grant
            ? "Đã cấp đồng thuận — ký ức được dùng cho lần sau."
            : "Đã thu hồi đồng thuận — ký ức ngừng được dùng.",
        );
        setRev((r) => r + 1);
        onChanged?.();
      } catch (e) {
        setActionError(viError(e, COPY.decide));
      } finally {
        setBusyId(null);
      }
    },
    [onChanged],
  );

  const remove = useCallback(
    async (memoryId: string) => {
      setBusyId(memoryId);
      setNotice(null);
      setActionError(null);
      try {
        await apiSend(`/api/v1/experience/memories/${memoryId}`, undefined, "DELETE");
        setNotice("Đã xoá ký ức — thao tác có lưu vết kiểm toán.");
        setRev((r) => r + 1);
        onChanged?.();
      } catch (e) {
        setActionError(viError(e, COPY.remove));
      } finally {
        setBusyId(null);
      }
    },
    [onChanged],
  );

  if (loadError && !data) {
    return (
      <div className="nq-alert nq-alert--error" role="alert">
        {viError(loadError, COPY.read)}
        <button type="button" className="nq-linkbtn" onClick={() => setRev((r) => r + 1)}>
          <Icon name="refresh" size={14} />
          Thử lại
        </button>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="nq-anchor nq-anchor--loading" aria-busy="true">
        <p>Đang tải chi tiết neo…</p>
      </div>
    );
  }

  const pending = data.pending_memories ?? [];
  const confirmed = data.confirmed_memories ?? [];

  return (
    <section className="nq-anchor" aria-label={`Chi tiết ${data.anchor.label}`}>
      <header className="nq-anchor__head">
        <Icon name="location" size={16} />
        <h3>{data.anchor.label || anchorLabel}</h3>
        <span className="nq-rolechip">
          {KIND_LABEL[data.anchor.kind] ?? "Neo không gian"}
        </span>
      </header>

      {notice ? (
        <p className="nq-pref__notice" role="status">
          {notice}
        </p>
      ) : null}
      {actionError ? (
        <div className="nq-alert nq-alert--error" role="alert">
          {actionError}
        </div>
      ) : null}

      {/* Ký ức chờ duyệt đặt TRƯỚC: đây là việc cần người quyết định. */}
      <h4 className="nq-anchor__subhead">
        Chờ quyết định
        {pending.length ? <span className="nq-anchor__count">{pending.length}</span> : null}
      </h4>
      {pending.length === 0 ? (
        <ExpEmpty
          icon="check"
          title="Không có ký ức nào chờ duyệt ở khu vực này"
          hint="Ký ức xuất hiện khi có người đề xuất ghi nhớ điều gì đó tại neo này."
        />
      ) : (
        <ul className="nq-memlist" data-testid="pending-memories">
          {pending.map((m) => (
            <li key={m.memory_id} className="nq-memlist__item">
              <p className="nq-memlist__content">{m.content}</p>
              <div className="nq-memlist__actions">
                <button
                  type="button"
                  className="nq-btn-compact nq-modebtn"
                  data-testid={`mem-grant-${m.memory_id}`}
                  disabled={busyId === m.memory_id}
                  onClick={() => decide(m.memory_id, true)}
                >
                  <Icon name="check" size={14} />
                  Đồng ý lưu
                </button>
                <button
                  type="button"
                  className="nq-btn-compact nq-modebtn"
                  data-testid={`mem-revoke-${m.memory_id}`}
                  disabled={busyId === m.memory_id}
                  onClick={() => decide(m.memory_id, false)}
                >
                  <Icon name="close" size={14} />
                  Từ chối
                </button>
                <button
                  type="button"
                  className="nq-linkbtn"
                  data-testid={`mem-delete-${m.memory_id}`}
                  disabled={busyId === m.memory_id}
                  onClick={() => remove(m.memory_id)}
                >
                  <Icon name="trash" size={14} />
                  Xoá
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <h4 className="nq-anchor__subhead">
        Ký ức đã xác nhận
        {confirmed.length ? <span className="nq-anchor__count">{confirmed.length}</span> : null}
      </h4>
      <MemoryTimeline memories={confirmed} onRemove={remove} busyId={busyId} />
    </section>
  );
}