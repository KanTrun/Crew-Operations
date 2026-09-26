"use client";

/**
 * Rule Discovery — quán tự viết luật: bằng chứng trước → câu luật → shadow → quyết định.
 *
 * Hai lỗi nghiệp vụ ở bản trước:
 *   1. `candidates` khởi tạo rỗng và không nạp khi mount — mở lại trang là thấy
 *      trống dù máy chủ vẫn giữ ứng viên, người dùng tưởng mất dữ liệu.
 *   2. `revoke` có API nhưng không UI — luật đã vào hiệu lực thì không rút lại
 *      được, nghĩa là quán không sửa được luật của chính mình.
 *
 * Cũng bỏ việc in `candidate_id` ra thông báo: nói "ứng viên thứ N" theo vị trí
 * trong danh sách, và giữ mã trong `data-candidate` cho kiểm thử.
 */

import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../../lib/api";
import { viError } from "../../../lib/present";
import { Icon } from "../../icons";
import { ExpEmpty } from "../exp-kit";
import { playbookStatusLabel, ruleSentenceLabel } from "../exp-present";
import RuleEvidenceDrawer from "./RuleEvidenceDrawer";
import RuleShadowResult from "./RuleShadowResult";

interface CandidateItem {
  candidate_id: string;
  sentence: string;
  confidence: number;
  status: string;
  shadow_result?: Record<string, unknown> | null;
  playbook_status?: string | null;
}

const COPY = {
  list: { doing: "đọc được danh sách ứng viên luật" },
  discover: { doing: "tìm quyết định lặp lại" },
  shadow: { doing: "chạy thử luật trên dữ liệu cũ" },
  confirm: { doing: "đưa luật vào vòng đời" },
  reject: { doing: "từ chối ứng viên luật" },
  revoke: { doing: "thu hồi luật đã ban hành" },
} as const;

/**
 * Trạng thái ứng viên → nhãn đọc được.
 *
 * Nhánh `rejected` dùng "Bị từ chối" để khớp bảng nhãn chung; các mã của vòng đời
 * cẩm nang (`qua_vf_rule`, `cho_chu_quan`…) đi qua `playbookStatusLabel` —
 * `proposalStatusLabel` không chứa chúng nên sẽ in mã thô ra màn hình.
 */
function candidateStatusLabel(c: CandidateItem): string {
  if (c.status === "revoked") return "Đã thu hồi";
  if (c.status === "rejected") return "Bị từ chối";
  if (c.status === "confirmed") {
    // "Đã ban hành" đã bao hàm "đã qua kiểm chứng" — chỉ nói trạng thái sâu hơn
    // khi luật thật sự đang hiệu lực, tránh lặp hai lần cùng một ý.
    return c.playbook_status === "hieu_luc"
      ? "Đã ban hành · đang hiệu lực"
      : "Đã ban hành";
  }
  return playbookStatusLabel(c.status);
}

export default function RuleDiscovery() {
  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [evidenceFor, setEvidenceFor] = useState<string | null>(null);

  const token =
    (typeof window !== "undefined" &&
      (window.sessionStorage.getItem("nq_token") ||
        window.localStorage.getItem("nq_token"))) ||
    "";
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

  const api = useCallback(
    async <T,>(path: string, method = "GET"): Promise<T> => {
      const res = await fetch(`${base}/api/v1${path}`, {
        method,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      if (!res.ok) throw new ApiError(res.status);
      return (await res.json()) as T;
    },
    [base, token],
  );

  const loadCandidates = useCallback(async () => {
    setLoading(true);
    try {
      const list = await api<{ candidates: CandidateItem[] }>(
        "/experience/rules/candidates",
      );
      setCandidates(list.candidates ?? []);
      setError(null);
    } catch (e) {
      setError(viError(e, COPY.list));
    } finally {
      setLoading(false);
    }
  }, [api]);

  // Nạp sẵn khi mở trang — không để người dùng nhìn màn trống rồi đoán.
  useEffect(() => {
    void loadCandidates();
  }, [loadCandidates]);

  const discover = useCallback(async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const res = await api<{ discovered: string[]; count: number }>(
        "/experience/rules/discover",
        "POST",
      );
      const list = await api<{ candidates: CandidateItem[] }>(
        "/experience/rules/candidates",
      );
      setCandidates(list.candidates ?? []);
      setNotice(
        res.count > 0
          ? `Đã tìm ${res.count} ứng viên luật từ quyết định lặp lại.`
          : "Chưa có quyết định nào lặp đủ để thành luật — cần thêm dữ liệu vận hành.",
      );
    } catch (e) {
      setError(viError(e, COPY.discover));
    } finally {
      setBusy(false);
    }
  }, [api]);

  const runShadow = useCallback(
    async (candidateId: string) => {
      setBusy(true);
      setError(null);
      try {
        const res = await api<{ shadow: Record<string, unknown> }>(
          `/experience/rules/${candidateId}/shadow-test`,
          "POST",
        );
        setCandidates((prev) =>
          prev.map((c) =>
            c.candidate_id === candidateId ? { ...c, shadow_result: res.shadow } : c,
          ),
        );
        setNotice("Đã chạy thử trên dữ liệu cũ — xem thay đổi ở phần kết quả shadow.");
      } catch (e) {
        setError(viError(e, COPY.shadow));
      } finally {
        setBusy(false);
      }
    },
    [api],
  );

  const confirm = useCallback(
    async (candidateId: string) => {
      setBusy(true);
      setError(null);
      setNotice(null);
      try {
        const res = await api<{
          playbook_status: string;
          playbook_id?: string;
          not_auto_activated: boolean;
        }>(`/experience/rules/${candidateId}/confirm`, "POST");
        setCandidates((prev) =>
          prev.map((c) =>
            c.candidate_id === candidateId
              ? { ...c, status: "confirmed", playbook_status: res.playbook_status }
              : c,
          ),
        );
        setNotice(
          `Luật đã vào vòng đời cẩm nang (${playbookStatusLabel(res.playbook_status)}). AI đề xuất, quản lý quyết định — chưa tự kích hoạt.`,
        );
      } catch (e) {
        setError(viError(e, COPY.confirm));
      } finally {
        setBusy(false);
      }
    },
    [api],
  );

  const reject = useCallback(
    async (candidateId: string) => {
      setBusy(true);
      setError(null);
      setNotice(null);
      try {
        await api(`/experience/rules/${candidateId}/reject`, "POST");
        setCandidates((prev) =>
          prev.map((c) =>
            c.candidate_id === candidateId ? { ...c, status: "rejected" } : c,
          ),
        );
        setNotice("Đã từ chối ứng viên luật này.");
      } catch (e) {
        setError(viError(e, COPY.reject));
      } finally {
        setBusy(false);
      }
    },
    [api],
  );

  /** Thu hồi luật đã hiệu lực — nhánh mà bản trước hoàn toàn thiếu. */
  const revoke = useCallback(
    async (candidateId: string) => {
      setBusy(true);
      setError(null);
      setNotice(null);
      try {
        await api(`/experience/rules/${candidateId}/revoke`, "POST");
        setCandidates((prev) =>
          prev.map((c) =>
            c.candidate_id === candidateId
              ? { ...c, status: "revoked", playbook_status: null }
              : c,
          ),
        );
        setNotice(
          "Đã thu hồi luật. Luật này ngừng áp dụng từ bước tiếp theo — cần ghi lý do vào biên bản.",
        );
      } catch (e) {
        setError(viError(e, COPY.revoke));
      } finally {
        setBusy(false);
      }
    },
    [api],
  );

  return (
    <div className="nq-rules">
      <header className="nq-rules__header">
        <h1>Quán tự viết luật</h1>
        <p>
          AI phát hiện quyết định lặp lại → đề xuất luật rõ ràng → quản lý quyết
          định. Luật đã ban hành vẫn thu hồi được.
        </p>
      </header>

      {error ? (
        <div className="nq-alert nq-alert--error" role="alert">
          {error}
        </div>
      ) : null}
      {notice ? (
        <div className="nq-alert nq-alert--info" role="status">
          {notice}
        </div>
      ) : null}

      <div className="nq-rules__actions">
        <button
          type="button"
          className="nq-btn nq-btn-primary"
          data-testid="rules-discover"
          disabled={busy}
          onClick={discover}
        >
          <Icon name="bot" size={16} />
          {busy ? "Đang xử lý…" : "Tìm quyết định lặp lại"}
        </button>
      </div>

      {/* VÌ SAO TRANG NÀY TỒN TẠI — người dùng hỏi "khác gì cẩm nang".
          Cẩm nang là nơi LUẬT ĐÃ VIẾT nằm; trang này là nơi luật được SINH RA
          từ chính các quyết định lặp lại của quán, kèm bằng chứng và bước chạy
          thử. Khối này nói rõ ranh giới đó để không ai nhầm là trùng chức năng. */}
      <section className="nq-rules__why" data-testid="rules-why">
        <div className="nq-exp-section__head">
          <Icon name="info" size={16} />
          <h2 className="nq-exp-section__title">Trang này khác Cẩm nang ở đâu</h2>
        </div>
        <div className="nq-rules__whycols">
          <div>
            <p className="nq-rules__whyhead">Cẩm nang</p>
            <p className="nq-rules__whybody">
              Nơi <strong>đọc và chạy</strong> những luật đã được chốt. Ai cũng
              tra được quy trình.
            </p>
          </div>
          <div>
            <p className="nq-rules__whyhead">Quán tự viết luật</p>
            <p className="nq-rules__whybody">
              Nơi luật được <strong>sinh ra</strong>: máy đọc lịch sử đổi ca, tìm
              quyết định lặp lại, dựng bằng chứng, chạy thử trên dữ liệu cũ — rồi
              mới đề xuất. Chỉ quản lý/chủ quán ban hành.
            </p>
          </div>
        </div>
        <ul className="nq-rules__whysteps">
          <li><strong>1. Tìm</strong> — máy quét lịch sử, đề xuất câu luật kèm mức tin cậy.</li>
          <li><strong>2. Xem bằng chứng</strong> — những lần việc này lặp lại, ai làm, ca nào.</li>
          <li><strong>3. Chạy thử (shadow)</strong> — áp thử lên dữ liệu cũ, so trước/sau.</li>
          <li><strong>4. Xác nhận</strong> — vào vòng đời; thu hồi được bất cứ lúc nào.</li>
        </ul>
        {candidates.length > 0 ? (
          <p className="nq-rules__whynotice" data-testid="rules-why-count">
            Hiện có <strong>{candidates.length}</strong> ứng viên
            {candidates.filter((c) => c.status === "confirmed").length
              ? `, trong đó ${candidates.filter((c) => c.status === "confirmed").length} đã ban hành`
              : ""}
            . Bấm “Tìm quyết định lặp lại” nếu muốn máy rà lại từ đầu.
          </p>
        ) : null}
      </section>

      {loading ? (
        <p aria-busy="true">Đang đọc danh sách ứng viên…</p>
      ) : candidates.length === 0 ? (
        <ExpEmpty
          icon="clipboard"
          title="Chưa có ứng viên luật nào"
          hint="Bấm “Tìm quyết định lặp lại” — hệ thống chỉ đề xuất khi có đủ bằng chứng lặp lại."
        />
      ) : (
        <ul className="nq-rules__list" data-testid="rules-list">
          {candidates.map((c) => {
            const revoked = c.status === "revoked";
            const published = c.status === "confirmed";
            return (
              <li
                key={c.candidate_id}
                className={`nq-rules__item${revoked ? " is-revoked" : ""}`}
                data-candidate={c.candidate_id}
              >
                <p className="nq-rules__sentence">{ruleSentenceLabel(c.sentence)}</p>
                <p className="nq-rules__meta">
                  {candidateStatusLabel(c)} · độ tin cậy{" "}
                  {(c.confidence * 100).toFixed(0)}%
                </p>
                {c.shadow_result ? <RuleShadowResult result={c.shadow_result} /> : null}
                <div className="nq-rules__actions-row">
                  <button
                    type="button"
                    className="nq-btn-compact nq-modebtn"
                    data-testid="evidence-btn"
                    onClick={() => setEvidenceFor(c.candidate_id)}
                  >
                    <Icon name="info" size={13} />
                    Xem bằng chứng
                  </button>
                  <button
                    type="button"
                    className="nq-btn-compact nq-modebtn"
                    data-testid="shadow-btn"
                    disabled={busy || revoked}
                    onClick={() => runShadow(c.candidate_id)}
                  >
                    <Icon name="play" size={13} />
                    {c.shadow_result ? "Chạy lại shadow test" : "Chạy shadow test"}
                  </button>
                  {!published && !revoked ? (
                    <>
                      <button
                        type="button"
                        className="nq-btn nq-btn-primary"
                        data-testid="confirm-btn"
                        disabled={busy || !c.shadow_result}
                        onClick={() => confirm(c.candidate_id)}
                      >
                        <Icon name="check" size={15} />
                        Xác nhận
                      </button>
                      <button
                        type="button"
                        className="nq-linkbtn"
                        data-testid="reject-btn"
                        disabled={busy}
                        onClick={() => reject(c.candidate_id)}
                      >
                        Từ chối
                      </button>
                    </>
                  ) : null}
                  {published ? (
                    <button
                      type="button"
                      className="nq-linkbtn"
                      data-testid="revoke-btn"
                      disabled={busy}
                      onClick={() => revoke(c.candidate_id)}
                    >
                      <Icon name="trash" size={14} />
                      Thu hồi luật
                    </button>
                  ) : null}
                </div>
                {!c.shadow_result && !published && !revoked ? (
                  <p className="nq-rules__hint">
                    Cần chạy shadow test trước khi xác nhận — luật chưa thử thì chưa
                    duyệt được.
                  </p>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}

      {evidenceFor ? (
        <RuleEvidenceDrawer
          candidateId={evidenceFor}
          onClose={() => setEvidenceFor(null)}
        />
      ) : null}
    </div>
  );
}

