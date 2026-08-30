"use client";

import { useEffect, useState, useCallback } from "react";
import { apiGet, apiSend } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Loading,
  PageHeader,
  useToasts,
} from "../../ui/kit";

type Status = {
  connected: boolean;
  page_name?: string;
  follower_count?: number;
  unread_thread_count?: number;
  unreviewed_draft_count?: number;
};

type Thread = {
  id: string;
  sender_name: string;
  sender_avatar?: string;
  last_message_at: string;
  is_within_24h: boolean;
  needs_action: boolean;
  suggested_reply?: string;
  messages: Array<{
    id: string;
    from_customer: boolean;
    text: string;
    sent_at: string;
  }>;
};

type Draft = {
  id: string;
  noi_dung: string;
  ngay_tao: string;
  nguoi_tao: string;
  trang_thai: "cho_duyet" | "da_duyet" | "tu_choi";
};

type StoreProfile = {
  name: string;
  address: string;
  phone: string;
  open_hours: string;
  wifi_password?: string;
  signature_drinks?: string[];
  signature_dishes?: string[];
  parking_info?: string;
  special_notes?: string;
};

type Promotion = {
  id: string;
  title: string;
  description: string;
  valid_until: string;
  active: boolean;
};

type TrendItem = {
  id: string;
  tieu_de: string;
  cum_tu_khoa_viral: string;
  nguon_goc: string;
  loai_xu_huong: string;
  danh_muc: string;
  vong_doi: string;
  diem_nhan_dac_biet: string;
  nguon_goc_chi_tiet: string;
  ngu_canh_su_dung: string;
  tam_ly_gioi_tre: string;
  toc_do_tang_truong_24h: number;
  diem_tiem_nang_viral: number;
  du_bao_thoi_gian: string;
  link_goc?: string;
  tiktok_url?: string;
  tiktok_tag_url?: string;
  thoi_gian_cao?: string;
  luot_tiep_can?: string;
  is_live_scraped?: boolean;
  trich_doan_noi_dung_that?: string;
  binh_luan_that_tiktok?: string[];
  nen_tang_lan_toa: string[];
  tu_khoa_hashtag: string[];
};

export default function PageQuanPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [status, setStatus] = useState<Status | null>(null);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [draftText, setDraftText] = useState("");
  const [replyDraft, setReplyDraft] = useState<Record<string, string>>({});
  const [tab, setTab] = useState<"threads" | "drafts" | "trends" | "config">("trends");
  const [profile, setProfile] = useState<StoreProfile | null>(null);
  const [promotions, setPromotions] = useState<Promotion[]>([]);

  // Trend Intelligence State
  const [trends, setTrends] = useState<TrendItem[]>([]);
  const [regionFilter, setRegionFilter] = useState<string>("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [selectedTrend, setSelectedTrend] = useState<TrendItem | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatusText, setScanStatusText] = useState("");

  // Keyword / Topic Filter State (Chức năng 1)
  const [keywordInput, setKeywordInput] = useState("");
  const [activeKeyword, setActiveKeyword] = useState("");

  // Bookmark / Saved Trends State (Chức năng 3)
  const [savedTrends, setSavedTrends] = useState<TrendItem[]>([]);
  const [showSavedOnly, setShowSavedOnly] = useState(false);

  // Auto-Scan State (Chức năng 4)
  const [autoScanEnabled, setAutoScanEnabled] = useState(false);
  const [scanIntervalMinutes, setScanIntervalMinutes] = useState(30);
  const [customMinutesInput, setCustomMinutesInput] = useState("30");
  const [countdownSeconds, setCountdownSeconds] = useState(30 * 60);

  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { toasts, push, dismiss } = useToasts();

  // Load Saved Trends from localStorage
  useEffect(() => {
    try {
      const stored = localStorage.getItem("nhp_saved_trends_v2");
      if (stored) {
        setSavedTrends(JSON.parse(stored));
      }
    } catch {
      // Ignore localstorage errors
    }
  }, []);

  const toggleSaveTrend = (item: TrendItem, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSavedTrends((prev) => {
      const exists = prev.some((t) => t.id === item.id);
      let updated: TrendItem[];
      if (exists) {
        updated = prev.filter((t) => t.id !== item.id);
        push(`Đã bỏ lưu xu hướng "${item.cum_tu_khoa_viral}"`);
      } else {
        updated = [item, ...prev];
        push(`⭐ Đã lưu xu hướng "${item.cum_tu_khoa_viral}" vào kế hoạch quán!`);
      }
      try {
        localStorage.setItem("nhp_saved_trends_v2", JSON.stringify(updated));
      } catch {
        // Ignore
      }
      return updated;
    });
  };

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    if (!getToken()) setLoading(false);
  }, []);

  // Fetch Trends function (Quét xong 100% mới cập nhật 1 lượt)
  const fetchTrendsData = useCallback(
    async (region: string, category: string, kw: string, showToast = false) => {
      setIsScanning(true);
      const sourceName =
        region === "tiktok_vn"
          ? "TikTok Việt Nam"
          : region === "threads_vn"
          ? "Threads & Gen Z"
          : region === "google_vn"
          ? "Google Trends VN"
          : region === "star_vn"
          ? "Showbiz & KOLs"
          : region === "tiktok_global"
          ? "Quốc tế (Global)"
          : "Tất cả nguồn";

      setScanStatusText(
        kw.trim()
          ? `⏳ Đang quét chuyên sâu chủ đề "${kw.trim()}" từ ${sourceName}...`
          : `⏳ Đang cào dữ liệu độc quyền thời gian thực từ ${sourceName}...`
      );

      try {
        const queryParams = new URLSearchParams({
          region,
          category,
          keyword: kw.trim(),
        });
        const res = await apiGet<{ trends: TrendItem[]; total: number }>(`/api/v1/trends/radar?${queryParams.toString()}`);
        const freshTrends = res.trends ?? [];
        
        // Quét xong hết mới nạp dữ liệu lên 1 lượt
        setTrends(freshTrends);
        if (freshTrends.length > 0) {
          setSelectedTrend((curr) => {
            const stillExists = freshTrends.find((t) => t.id === curr?.id);
            return stillExists || freshTrends[0];
          });
        } else {
          setSelectedTrend(null);
        }
        setError(null);
        setScanStatusText(`✅ Quét hoàn tất: Đã nạp ${freshTrends.length} xu hướng thật!`);
        if (showToast) {
          push(`⚡ Đã cào thành công ${freshTrends.length} xu hướng từ ${sourceName}!`);
        }
      } catch (e) {
        setError(viError(e, { doing: "cào dữ liệu xu hướng" }));
        setScanStatusText("❌ Lỗi khi cào dữ liệu. Vui lòng thử lại.");
      } finally {
        setIsScanning(false);
      }
    },
    [push]
  );

  const load = useCallback(() => {
    if (!getToken()) return;
    setLoading(true);
    Promise.all([
      apiGet<Status>("/api/v1/page/status"),
      apiGet<{ items: Thread[] }>("/api/v1/page/threads"),
      apiGet<{ items: Draft[] }>("/api/v1/page/drafts"),
      apiGet<StoreProfile>("/api/v1/store/profile").catch(() => null),
      apiGet<Promotion[]>("/api/v1/store/promotions").catch(() => []),
    ])
      .then(([st, th, dr, prof, promos]) => {
        setStatus(st);
        setThreads(th.items ?? []);
        setDrafts(dr.items ?? []);
        if (prof) setProfile(prof);
        if (promos) setPromotions(promos);
        setError(null);
      })
      .catch((e) => setError(viError(e, { doing: "mở được Page quán" })))
      .finally(() => setLoading(false));

    fetchTrendsData(regionFilter, categoryFilter, activeKeyword);
  }, [regionFilter, categoryFilter, activeKeyword, fetchTrendsData]);

  useEffect(() => {
    if (token) load();
  }, [token, load]);

  // Bộ đếm Tự Động Quét theo chu kỳ tùy chỉnh (Chức năng 4)
  useEffect(() => {
    if (!autoScanEnabled || !token) return;

    setCountdownSeconds(scanIntervalMinutes * 60);

    const timer = setInterval(() => {
      // Chỉ chạy khi tab đang hiển thị (Tab Visibility Check để chống quá tải)
      if (document.hidden) return;

      setCountdownSeconds((prev) => {
        if (prev <= 1) {
          fetchTrendsData(regionFilter, categoryFilter, activeKeyword, true);
          return scanIntervalMinutes * 60;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [autoScanEnabled, scanIntervalMinutes, regionFilter, categoryFilter, activeKeyword, token, fetchTrendsData]);

  const handleApplyKeywordSearch = (kw: string) => {
    setActiveKeyword(kw);
    setKeywordInput(kw);
    setShowSavedOnly(false);
    fetchTrendsData(regionFilter, categoryFilter, kw, true);
  };

  const handleClearKeyword = () => {
    setKeywordInput("");
    setActiveKeyword("");
    fetchTrendsData(regionFilter, categoryFilter, "", true);
  };

  const handleRegionChange = (newRegion: string) => {
    setRegionFilter(newRegion);
    setShowSavedOnly(false);
    fetchTrendsData(newRegion, categoryFilter, activeKeyword, true);
  };

  const handleCategoryChange = (newCategory: string) => {
    setCategoryFilter(newCategory);
    fetchTrendsData(regionFilter, newCategory, activeKeyword, true);
  };

  // Messenger Thread operations
  async function reply(id: string) {
    const text = (replyDraft[id] ?? "").trim();
    if (!text) return;
    try {
      await apiSend(`/api/v1/page/threads/${id}/reply`, { text });
      push("Đã gửi trả lời.");
      setReplyDraft((m) => ({ ...m, [id]: "" }));
      load();
    } catch (e) {
      setError(viError(e, { doing: "gửi được trả lời" }));
    }
  }

  async function approveSuggestion(th: Thread) {
    const text = (replyDraft[th.id] || th.suggested_reply || "").trim();
    if (!text) return;
    try {
      await apiSend(`/api/v1/page/threads/${th.id}/approve`, {
        final_reply: text,
        tag: !th.is_within_24h ? "CONFIRMED_EVENT_UPDATE" : undefined,
      });
      push("Đã duyệt & gửi câu trả lời.");
      setReplyDraft((m) => ({ ...m, [th.id]: "" }));
      load();
    } catch (e) {
      setError(viError(e, { doing: "duyệt trả lời" }));
    }
  }

  async function saveProfile() {
    if (!profile) return;
    try {
      await apiSend("/api/v1/store/profile", profile, "PUT");
      push("Đã lưu thông tin quán.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "lưu thông tin quán" }));
    }
  }

  async function createDraft() {
    if (!draftText.trim()) return;
    try {
      await apiSend("/api/v1/page/drafts", { noi_dung: draftText.trim() });
      setDraftText("");
      push("Đã lưu nháp bài.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "lưu được nháp bài", forbidden: "Chỉ quản lý mới soạn bài page." }));
    }
  }

  async function decideDraft(id: string, quyet_dinh: "duyet" | "tu_choi") {
    try {
      await apiSend(`/api/v1/page/drafts/${id}`, { quyet_dinh });
      push(quyet_dinh === "duyet" ? "Đã duyệt & Đăng bài." : "Đã từ chối nháp.");
      load();
    } catch (e) {
      setError(viError(e, { doing: "quyết được nháp bài" }));
    }
  }

  if (!token) return <AuthGate />;

  const connected = Boolean(status?.connected);

  const formatCountdown = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  const displayedTrends = showSavedOnly ? savedTrends : trends;

  const currentSourceLabel =
    regionFilter === "tiktok_vn"
      ? "TikTok VN"
      : regionFilter === "threads_vn"
      ? "Threads & Gen Z"
      : regionFilter === "google_vn"
      ? "Google Trends VN"
      : regionFilter === "star_vn"
      ? "Showbiz & KOLs"
      : regionFilter === "tiktok_global"
      ? "Quốc tế"
      : "Tất cả nguồn";

  return (
    <div className="nq-page">
      <PageHeader
        kicker="Trí Tuệ Thị Trường & Kênh Khách Hàng"
        title="Radar Trí Tuệ Xu Hướng & Bắt Sóng Từ Khóa Viral"
        meta="Cào độc quyền từng nền tảng, quét chủ đề ngách F&B, lưu trữ kịch bản marketing và bắt nhịp video/bình luận triệu view."
      />

      {error ? <Alert>{error}</Alert> : null}
      {loading ? <Loading skeleton="list">Đang đọc dữ liệu xu hướng…</Loading> : null}

      <div className="mb-6 flex flex-wrap gap-2 border-b-2 border-[var(--nq-dim)] pb-2">
        <Btn variant={tab === "trends" ? "primary" : "ghost"} onClick={() => setTab("trends")}>
          📡 Radar Trí Tuệ Xu Hướng ({showSavedOnly ? `${savedTrends.length} đã lưu` : trends.length})
        </Btn>
        <Btn variant={tab === "threads" ? "primary" : "ghost"} onClick={() => setTab("threads")}>
          Hội thoại Messenger ({threads.length})
        </Btn>
        <Btn variant={tab === "drafts" ? "primary" : "ghost"} onClick={() => setTab("drafts")}>
          Nháp bài Fanpage ({drafts.length})
        </Btn>
        {manager ? (
          <Btn variant={tab === "config" ? "primary" : "ghost"} onClick={() => setTab("config")}>
            Cấu hình Thông tin quán
          </Btn>
        ) : null}
      </div>

      {/* TAB 1: RADAR TRÍ TUỆ XU HƯỚNG & GIẢI MÃ TỪ KHÓA VIRAL */}
      {tab === "trends" && (
        <div className="space-y-6">
          {/* KHỐI 1: TÙY CHỈNH TỰ ĐỘNG QUÉT & BẢO VỆ CHỐNG QUÁ TẢI (Chức năng 4) */}
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] p-4">
            <div className="flex items-center gap-3">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoScanEnabled}
                  onChange={(e) => {
                    setAutoScanEnabled(e.target.checked);
                    if (e.target.checked) {
                      push(`⏱️ Đã bật tự động quét mỗi ${scanIntervalMinutes} phút.`);
                    } else {
                      push("⏸️ Đã tắt tự động quét.");
                    }
                  }}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-[var(--nq-dim)] peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
              </label>
              <div>
                <span className="text-xs font-bold text-[var(--nq-primary)]">
                  ⏱️ Tự động quét định kỳ:{" "}
                  <strong className={autoScanEnabled ? "text-emerald-400" : "text-[var(--nq-muted)]"}>
                    {autoScanEnabled ? "ĐANG BẬT" : "TẮT"}
                  </strong>
                </span>
                {autoScanEnabled && (
                  <p className="text-[11px] text-emerald-400/90 font-mono">
                    Quét lại sau: <strong>{formatCountdown(countdownSeconds)}</strong> (Tự ngủ khi ẩn tab)
                  </p>
                )}
              </div>
            </div>

            {/* Tùy chỉnh số phút quét */}
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-[var(--nq-muted)] font-medium">Chu kỳ quét:</span>
              {[5, 15, 30, 60].map((mins) => (
                <button
                  key={mins}
                  onClick={() => {
                    setScanIntervalMinutes(mins);
                    setCustomMinutesInput(mins.toString());
                    setCountdownSeconds(mins * 60);
                    push(`Đã đổi chu kỳ quét sang ${mins} phút.`);
                  }}
                  className={`rounded px-2.5 py-1 text-xs font-bold transition cursor-pointer ${
                    scanIntervalMinutes === mins
                      ? "bg-[var(--nq-copper)] text-white shadow-sm"
                      : "bg-[var(--nq-surface)] text-[var(--nq-muted)] hover:bg-[var(--nq-dim)]"
                  }`}
                >
                  {mins} phút
                </button>
              ))}

              <div className="flex items-center gap-1 ml-2">
                <input
                  type="number"
                  min="1"
                  max="720"
                  value={customMinutesInput}
                  onChange={(e) => setCustomMinutesInput(e.target.value)}
                  className="w-14 rounded border border-[var(--nq-dim)] bg-[var(--nq-surface)] px-1.5 py-1 text-center text-xs text-[var(--nq-primary)]"
                />
                <button
                  onClick={() => {
                    const val = parseInt(customMinutesInput, 10);
                    if (val > 0 && val <= 720) {
                      setScanIntervalMinutes(val);
                      setCountdownSeconds(val * 60);
                      push(`Đã áp dụng chu kỳ quét tùy chỉnh: ${val} phút.`);
                    }
                  }}
                  className="rounded bg-[var(--nq-dim)] px-2 py-1 text-[11px] font-bold text-[var(--nq-primary)] hover:bg-[var(--nq-muted)] hover:text-black transition cursor-pointer"
                >
                  Đặt phút
                </button>
              </div>
            </div>
          </div>

          {/* KHỐI 2: CÀO THEO CHỦ ĐỀ / TỪ KHÓA NGÁCH QUAN TÂM (Chức năng 1) */}
          <div className="space-y-3 rounded-lg border-2 border-amber-500/30 bg-amber-500/5 p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="text-xs font-bold uppercase tracking-wider text-amber-400">
                🎯 Quét Sâu Chủ Đề / Từ Khóa Bạn Quan Tâm (F&B, Cà phê, Trà sữa...)
              </span>
              {activeKeyword && (
                <span className="text-xs text-amber-300 font-mono bg-amber-500/20 px-2 py-0.5 rounded border border-amber-500/40">
                  Đang lọc từ khóa: &quot;{activeKeyword}&quot;
                </span>
              )}
            </div>

            <div className="flex flex-wrap gap-2">
              <div className="flex-1 min-w-[240px] flex items-center gap-2">
                <input
                  type="text"
                  placeholder="Nhập chủ đề muốn quét (VD: matcha, cà phê muối, trà mãng cầu, checkin...)"
                  value={keywordInput}
                  onChange={(e) => setKeywordInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleApplyKeywordSearch(keywordInput);
                  }}
                  className="w-full rounded border border-[var(--nq-dim)] bg-[var(--nq-surface)] px-3 py-2 text-xs text-[var(--nq-primary)] placeholder:text-[var(--nq-muted)] focus:border-amber-400 focus:outline-none"
                />
              </div>
              <button
                onClick={() => handleApplyKeywordSearch(keywordInput)}
                disabled={isScanning}
                className="inline-flex items-center gap-1 rounded bg-amber-600 px-4 py-2 text-xs font-bold text-white hover:bg-amber-500 transition shadow cursor-pointer disabled:opacity-50"
              >
                <span>🔍</span> Quét Chủ Đề Này
              </button>
              {activeKeyword && (
                <button
                  onClick={handleClearKeyword}
                  className="rounded border border-[var(--nq-dim)] bg-[var(--nq-surface)] px-3 py-2 text-xs font-bold text-[var(--nq-muted)] hover:text-white transition cursor-pointer"
                >
                  ✕ Xóa Lọc
                </button>
              )}
            </div>

            {/* Quick Keyword Chips */}
            <div className="flex flex-wrap items-center gap-1.5 pt-1 text-xs">
              <span className="text-[11px] text-[var(--nq-muted)] font-medium">Gợi ý nhanh cho quán:</span>
              {[
                { tag: "matcha", label: "🍵 #matcha" },
                { tag: "cà phê muối", label: "☕ #cà phê muối" },
                { tag: "trà sữa", label: "🧋 #trà sữa" },
                { tag: "check in quán", label: "📸 #check-in" },
                { tag: "đồ ăn vặt", label: "🥪 #đồ ăn vặt" },
                { tag: "drama", label: "🔥 #drama" },
                { tag: "gen z", label: "🌿 #gen z" },
              ].map((k) => (
                <button
                  key={k.tag}
                  onClick={() => handleApplyKeywordSearch(k.tag)}
                  className="rounded bg-[var(--nq-surface)] px-2 py-0.5 text-[11px] font-mono text-[var(--nq-primary)] hover:border-amber-400 hover:text-amber-300 border border-[var(--nq-dim)] transition cursor-pointer"
                >
                  {k.label}
                </button>
              ))}
            </div>
          </div>

          {/* KHỐI 3: BỘ LỌC NGUỒN CÀO ĐỘC QUYỀN (Targeted Scraping) & BOOKMARK */}
          <div className="space-y-3 rounded-lg border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] p-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--nq-dim)] pb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--nq-copper)]">
                📡 Nền Tảng Cào Dữ Liệu (Chọn Độc Quyền Theo Nhu Cầu):
              </span>

              {/* Nút Cào Độc Quyền theo Nguồn */}
              <button
                onClick={() => fetchTrendsData(regionFilter, categoryFilter, activeKeyword, true)}
                disabled={isScanning}
                className="inline-flex items-center gap-1.5 rounded bg-emerald-600 px-4 py-1.5 text-xs font-bold text-white shadow-md hover:bg-emerald-500 transition-all cursor-pointer disabled:opacity-50"
              >
                <span>⚡</span> Cào Dữ Liệu {currentSourceLabel}
              </button>
            </div>

            {/* Thanh trạng thái loading toàn bộ dữ liệu */}
            {isScanning && (
              <div className="rounded border border-emerald-500/40 bg-emerald-500/10 p-3 text-xs text-emerald-400 font-mono flex items-center justify-between animate-pulse">
                <span>{scanStatusText}</span>
                <span className="text-[11px]">Đang tải trọn gói...</span>
              </div>
            )}

            {/* Nút Lọc Theo Nền Tảng */}
            <div className="flex flex-wrap gap-2 pt-1">
              {[
                { id: "all", label: "🌐 Tất cả nguồn" },
                { id: "tiktok_vn", label: "🎵 TikTok VN (Video & Comment)" },
                { id: "threads_vn", label: "🧵 Threads & Gen Z" },
                { id: "google_vn", label: "🔥 Google Trends VN" },
                { id: "star_vn", label: "✨ Showbiz & KOLs" },
                { id: "tiktok_global", label: "🌐 Quốc tế (Global)" },
              ].map((p) => (
                <button
                  key={p.id}
                  onClick={() => handleRegionChange(p.id)}
                  className={`rounded px-3 py-1.5 text-xs font-bold transition-all cursor-pointer ${
                    regionFilter === p.id && !showSavedOnly
                      ? "bg-[var(--nq-primary)] text-black shadow-md"
                      : "bg-[var(--nq-surface)] text-[var(--nq-muted)] hover:bg-[var(--nq-dim)] hover:text-white"
                  }`}
                >
                  {p.label}
                </button>
              ))}

              {/* Tab Đã Lưu (Bookmark - Chức năng 3) */}
              <button
                onClick={() => {
                  setShowSavedOnly(true);
                  if (savedTrends.length > 0) {
                    setSelectedTrend(savedTrends[0]);
                  }
                }}
                className={`rounded px-3 py-1.5 text-xs font-bold transition-all cursor-pointer border ${
                  showSavedOnly
                    ? "bg-amber-400 text-black border-amber-300 shadow-md"
                    : "bg-amber-500/10 text-amber-300 border-amber-500/30 hover:bg-amber-500/20"
                }`}
              >
                ⭐ Xu Hướng Đã Lưu ({savedTrends.length})
              </button>
            </div>

            {/* Nút Lọc Theo Lĩnh Vực */}
            {!showSavedOnly && (
              <div className="flex flex-wrap items-center gap-2 border-t border-[var(--nq-dim)] pt-3 text-xs">
                <span className="font-bold text-[var(--nq-muted)]">🏷️ Lĩnh vực:</span>
                {[
                  { id: "all", label: "Tất cả lĩnh vực" },
                  { id: "am_thuc_fnb", label: "☕ Ẩm thực & Đồ uống F&B" },
                  { id: "tam_ly_lifestyle", label: "🌿 Tâm lý & Lifestyle Gen Z" },
                  { id: "meme_cau_noi", label: "🎭 Meme & Câu cửa miệng" },
                  { id: "trao_luu_pop_culture", label: "🔥 Pop Culture & Showbiz" },
                ].map((c) => (
                  <button
                    key={c.id}
                    onClick={() => handleCategoryChange(c.id)}
                    className={`rounded px-2.5 py-1 transition-all cursor-pointer ${
                      categoryFilter === c.id
                        ? "bg-[var(--nq-copper)] font-bold text-white shadow-sm"
                        : "bg-[var(--nq-surface)] text-[var(--nq-muted)] hover:bg-[var(--nq-dim)]"
                    }`}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* GRID HIỂN THỊ DANH SÁCH & PHÂN TÍCH CHUYÊN SÂU */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
            {/* Cột Trái: Danh sách Trend */}
            <div className="space-y-3 lg:col-span-5 max-h-[820px] overflow-y-auto pr-1">
              <div className="flex items-center justify-between sticky top-0 bg-[var(--nq-bg)] py-1 z-10">
                <h3 className="text-sm font-bold uppercase tracking-wider text-[var(--nq-copper)]">
                  {showSavedOnly
                    ? `Danh Sách Đã Lưu (${savedTrends.length})`
                    : `Tín Hiệu Cào Thật (${displayedTrends.length})`}
                </h3>
                <span className="text-xs text-emerald-400 font-mono">
                  {showSavedOnly ? "⭐ Kế hoạch quán" : "● Dữ liệu cào độc quyền"}
                </span>
              </div>

              {displayedTrends.length === 0 ? (
                <Empty>
                  {showSavedOnly
                    ? "Chưa có xu hướng nào được lưu. Hãy bấm dấu ⭐ trên các xu hướng để lưu vào đây!"
                    : "Không tìm thấy xu hướng nào theo bộ lọc hoặc từ khóa đã chọn."}
                </Empty>
              ) : (
                displayedTrends.map((t) => {
                  const isSelected = selectedTrend?.id === t.id;
                  const isBookmarked = savedTrends.some((st) => st.id === t.id);

                  const platformBadge =
                    t.nguon_goc === "threads_vn"
                      ? "🧵 Threads"
                      : t.nguon_goc === "tiktok_vn"
                      ? "🎵 TikTok VN"
                      : t.nguon_goc === "google_vn"
                      ? "🔥 Google VN"
                      : t.nguon_goc === "star_vn"
                      ? "✨ Showbiz"
                      : "🌐 Global";

                  const lifecycleBadge =
                    t.vong_doi === "moi_nhu"
                      ? { text: "🔥 MỚI NỔI 24H", cls: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30" }
                      : t.vong_doi === "dang_dinh"
                      ? { text: "⚡ ĐANG ĐỈNH CAO", cls: "bg-amber-500/20 text-amber-400 border-amber-500/30" }
                      : { text: "🧊 BÃO HÒA", cls: "bg-slate-500/20 text-slate-400 border-slate-500/30" };

                  return (
                    <div
                      key={t.id}
                      onClick={() => setSelectedTrend(t)}
                      className={`cursor-pointer border-2 p-4 transition-all rounded relative ${
                        isSelected
                          ? "border-[var(--nq-primary)] bg-[var(--nq-surface-hi)] shadow-md ring-1 ring-[var(--nq-primary)]"
                          : "border-[var(--nq-dim)] bg-[var(--nq-surface)] hover:border-[var(--nq-muted)]"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <span className="font-bold text-[var(--nq-primary)] text-sm">{t.tieu_de}</span>
                        <div className="flex flex-col items-end gap-1 shrink-0">
                          <span className="inline-block rounded px-2 py-0.5 text-xs font-mono font-bold bg-[var(--nq-dim)] text-[var(--nq-primary)]">
                            {platformBadge}
                          </span>
                          <span className={`inline-block rounded border px-1.5 py-0.2 text-[10px] font-bold ${lifecycleBadge.cls}`}>
                            {lifecycleBadge.text}
                          </span>
                        </div>
                      </div>

                      {/* Tag Từ khóa cửa miệng */}
                      <div className="mt-2 inline-flex items-center gap-1 rounded bg-[var(--nq-dim)] px-2 py-0.5 text-xs font-mono font-bold text-[var(--nq-copper)]">
                        🔑 &quot;{t.cum_tu_khoa_viral}&quot;
                      </div>

                      <p className="mt-2 text-xs text-[var(--nq-muted)] line-clamp-2">{t.diem_nhan_dac_biet}</p>

                      <div className="mt-3 flex items-center justify-between border-t border-[var(--nq-dim)] pt-2 text-xs">
                        <span className="font-mono text-emerald-500 font-bold">
                          +{t.toc_do_tang_truong_24h}% tăng trưởng
                        </span>
                        
                        <div className="flex items-center gap-2">
                          <button
                            onClick={(e) => toggleSaveTrend(t, e)}
                            className={`px-2 py-0.5 rounded text-xs font-bold transition cursor-pointer ${
                              isBookmarked
                                ? "bg-amber-400 text-black"
                                : "bg-[var(--nq-dim)] text-[var(--nq-muted)] hover:text-amber-300"
                            }`}
                            title={isBookmarked ? "Bỏ lưu" : "Lưu vào kế hoạch quán"}
                          >
                            {isBookmarked ? "⭐ Đã lưu" : "☆ Lưu"}
                          </button>
                          <span className="rounded bg-[var(--nq-surface-hi)] px-2 py-0.5 text-[var(--nq-primary)] font-bold">
                            Viral: {t.diem_tiem_nang_viral}/100
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Cột Phải: Bảng Phân Tích Chuyên Sâu Cốt Lõi Trend */}
            <div className="space-y-4 border-2 border-[var(--nq-dim)] bg-[var(--nq-surface-hi)] p-6 lg:col-span-7">
              {selectedTrend ? (
                <>
                  {/* Header: Cụm từ khóa cửa miệng cốt lõi & Nút Bookmark */}
                  <div className="rounded border-2 border-[var(--nq-copper)] bg-[var(--nq-surface)] p-4 shadow-sm">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold uppercase tracking-wider text-[var(--nq-copper)]">
                        🔑 Cụm Từ Khóa Cửa Miệng Viral (Bắt Sóng Ngay)
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => toggleSaveTrend(selectedTrend)}
                          className={`px-2.5 py-1 rounded text-xs font-bold transition cursor-pointer flex items-center gap-1 ${
                            savedTrends.some((st) => st.id === selectedTrend.id)
                              ? "bg-amber-400 text-black shadow"
                              : "bg-[var(--nq-dim)] text-amber-300 hover:bg-amber-400 hover:text-black"
                          }`}
                        >
                          <span>⭐</span>
                          {savedTrends.some((st) => st.id === selectedTrend.id) ? "Đã Lưu Kế Hoạch" : "Lưu Xu Hướng Này"}
                        </button>
                        <span className="text-xs font-bold text-amber-400 font-mono">
                          {selectedTrend.du_bao_thoi_gian}
                        </span>
                      </div>
                    </div>
                    <div className="mt-2 text-2xl font-black text-[var(--nq-copper)]">
                      &quot;{selectedTrend.cum_tu_khoa_viral}&quot;
                    </div>
                    <p className="mt-1 text-xs text-[var(--nq-muted)]">
                      Chỉ cần nhắc đến cụm từ này trong video, bài viết hoặc comment là cộng đồng mạng hiểu ngay ngữ cảnh.
                    </p>
                  </div>

                  {/* Banner Bằng Chứng & Link Gốc từ Internet */}
                  {selectedTrend.link_goc && (
                    <div className="rounded border border-emerald-500/40 bg-emerald-500/10 p-3 shadow-sm space-y-2">
                      <div className="flex items-center justify-between text-xs text-emerald-400">
                        <span className="font-bold flex items-center gap-1">
                          🌐 Bằng Chứng & Dữ Liệu Gốc Cào Thật Từ Internet
                        </span>
                        <span className="text-[11px] opacity-80">
                          🕒 {selectedTrend.thoi_gian_cao || "Vừa cập nhật"} | {selectedTrend.luot_tiep_can || "Lưu lượng cao"}
                        </span>
                      </div>

                      <div className="flex flex-wrap gap-2 pt-1 border-t border-emerald-500/20">
                        <a
                          href={selectedTrend.link_goc}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 rounded bg-[var(--nq-surface)] px-3 py-1 text-xs font-bold text-[var(--nq-primary)] border border-[var(--nq-dim)] hover:bg-[var(--nq-dim)] transition"
                        >
                          🔗 Xem Nguồn Gốc ↗
                        </a>
                        {selectedTrend.tiktok_url && (
                          <a
                            href={selectedTrend.tiktok_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded bg-[#fe2c55] px-3 py-1 text-xs font-bold text-white hover:bg-[#e0264b] transition"
                          >
                            🎬 Mở Trên TikTok ↗
                          </a>
                        )}
                        {selectedTrend.tiktok_tag_url && (
                          <a
                            href={selectedTrend.tiktok_tag_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 rounded bg-[var(--nq-surface)] px-3 py-1 text-xs font-bold text-[var(--nq-primary)] border border-[var(--nq-dim)] hover:bg-[var(--nq-dim)] transition"
                          >
                            🏷️ Hashtag TikTok ↗
                          </a>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Khối 1: Điểm nhấn đặc biệt & Nguồn gốc */}
                  <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                    <div className="space-y-1 rounded border border-[var(--nq-dim)] bg-[var(--nq-surface)] p-3.5">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--nq-muted)]">
                        ⚡ Điểm Nhấn / Thống Kê Thật
                      </h4>
                      <p className="text-sm font-semibold text-[var(--nq-primary)]">
                        {selectedTrend.diem_nhan_dac_biet}
                      </p>
                    </div>

                    <div className="space-y-1 rounded border border-[var(--nq-dim)] bg-[var(--nq-surface)] p-3.5">
                      <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--nq-muted)]">
                        📍 Nguồn Gốc Xuất Phát
                      </h4>
                      <p className="text-sm text-[var(--nq-primary)]">
                        {selectedTrend.nguon_goc_chi_tiet}
                      </p>
                    </div>
                  </div>

                  {/* Khối 2: Trích Đoạn Nội Dung Gốc Cào Thật */}
                  {selectedTrend.trich_doan_noi_dung_that && (
                    <div className="space-y-2 rounded border border-emerald-500/30 bg-emerald-500/5 p-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                          📰 Nội Dung & Trích Đoạn Gốc Cào Thật Từ Internet
                        </h4>
                        <span className="text-[10px] text-emerald-400/80 font-mono">100% Dữ liệu cào thật</span>
                      </div>
                      <p className="text-sm leading-relaxed text-[var(--nq-primary)] italic">
                        &quot;{selectedTrend.trich_doan_noi_dung_that}&quot;
                      </p>
                    </div>
                  )}

                  {/* Khối 3: TOP BÌNH LUẬN THẬT CÀO TRỰC TIẾP TỪ TIKTOK */}
                  {selectedTrend.binh_luan_that_tiktok && selectedTrend.binh_luan_that_tiktok.length > 0 && (
                    <div className="space-y-2 rounded border border-emerald-500/40 bg-emerald-500/5 p-4">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold uppercase tracking-wider text-emerald-400">
                          💬 Top Bình Luận Thật Cào Trực Tiếp Từ Video TikTok
                        </h4>
                        <span className="text-[10px] text-emerald-400/90 font-mono bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/30">
                          100% Cào từ TikTok
                        </span>
                      </div>
                      <div className="space-y-1.5">
                        {selectedTrend.binh_luan_that_tiktok.map((cmt, idx) => (
                          <div
                            key={idx}
                            className="rounded border border-[var(--nq-dim)] bg-[var(--nq-surface)] p-2.5 text-xs text-[var(--nq-primary)] font-mono"
                          >
                            {cmt}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Khối 4: Giải Mã Tâm Lý Giới Trẻ */}
                  <div className="space-y-1 rounded border border-purple-500/30 bg-purple-500/5 p-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-purple-400">
                      🧠 Giải Mã Tâm Lý Giới Trẻ / Gen Z
                    </h4>
                    <p className="text-sm leading-relaxed text-[var(--nq-primary)]">
                      {selectedTrend.tam_ly_gioi_tre}
                    </p>
                  </div>

                  {/* Khối 5: Ngữ Cảnh Sử Dụng & Gợi Ý Cho Quán */}
                  <div className="space-y-1 rounded border border-blue-500/30 bg-blue-500/5 p-4">
                    <h4 className="text-xs font-bold uppercase tracking-wider text-blue-400">
                      💡 Ngữ Cảnh Sử Dụng & Gợi Ý Bắt Trend Tại Quán
                    </h4>
                    <p className="text-sm leading-relaxed text-[var(--nq-primary)]">
                      {selectedTrend.ngu_canh_su_dung}
                    </p>
                  </div>

                  {/* Hashtag & Nền tảng */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--nq-dim)] pt-4 text-xs">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <span className="font-bold text-[var(--nq-muted)]">Hashtags:</span>
                      {selectedTrend.tu_khoa_hashtag.map((tag, idx) => (
                        <span
                          key={idx}
                          className="rounded bg-[var(--nq-surface)] px-2 py-0.5 font-mono text-[var(--nq-primary)] border border-[var(--nq-dim)]"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>

                    <div className="flex items-center gap-1.5 text-[var(--nq-muted)]">
                      <span>Nền tảng lan tỏa:</span>
                      <strong className="text-[var(--nq-primary)]">
                        {selectedTrend.nen_tang_lan_toa.join(", ")}
                      </strong>
                    </div>
                  </div>
                </>
              ) : (
                <Empty>Chọn một xu hướng ở danh sách bên trái để xem phân tích chi tiết.</Empty>
              )}
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: HỘI THOẠI MESSENGER */}
      {tab === "threads" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-[var(--nq-muted)]">
              {connected ? "🟢 Đã nối Page Messenger" : "⚪ Chưa nối Fanpage"}
            </span>
            <Btn variant="ghost" onClick={load}>
              Làm mới
            </Btn>
          </div>

          {threads.length === 0 ? (
            <Empty>Không có hội thoại nào cần xử lý.</Empty>
          ) : (
            <div className="space-y-4">
              {threads.map((th) => (
                <div
                  key={th.id}
                  className={`border-2 p-4 ${
                    th.needs_action ? "border-[var(--nq-copper)] bg-[var(--nq-surface-hi)]" : "border-[var(--nq-dim)]"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-[var(--nq-primary)]">{th.sender_name}</span>
                    <span className="text-xs text-[var(--nq-muted)]">
                      {th.is_within_24h ? "Trong 24h" : "Hết 24h (cần tag)"}
                    </span>
                  </div>

                  <div className="my-3 max-h-48 space-y-2 overflow-y-auto border border-[var(--nq-dim)] p-2">
                    {th.messages.map((m) => (
                      <div
                        key={m.id}
                        className={`text-xs ${
                          m.from_customer ? "text-[var(--nq-primary)]" : "text-right text-[var(--nq-copper)]"
                        }`}
                      >
                        <span className="font-bold">{m.from_customer ? "Khách: " : "Quán: "}</span>
                        {m.text}
                      </div>
                    ))}
                  </div>

                  {th.suggested_reply ? (
                    <div className="mb-2 rounded bg-[var(--nq-surface)] p-2 text-xs">
                      <span className="font-bold text-[var(--nq-copper)]">Gợi ý trả lời: </span>
                      {th.suggested_reply}
                    </div>
                  ) : null}

                  <div className="flex gap-2">
                    <input
                      type="text"
                      className="nq-input flex-1 text-xs"
                      placeholder="Nhập nội dung trả lời..."
                      value={replyDraft[th.id] ?? th.suggested_reply ?? ""}
                      onChange={(e) => setReplyDraft({ ...replyDraft, [th.id]: e.target.value })}
                    />
                    <Btn variant="primary" onClick={() => reply(th.id)}>
                      Gửi
                    </Btn>
                    {th.suggested_reply ? (
                      <Btn variant="ghost" onClick={() => approveSuggestion(th)}>
                        Duyệt gợi ý
                      </Btn>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: NHÁP BÀI FANPAGE */}
      {tab === "drafts" && (
        <div className="space-y-4">
          <div className="border-2 border-[var(--nq-dim)] p-4">
            <h3 className="mb-2 text-sm font-bold">Soạn nháp bài đăng mới</h3>
            <textarea
              className="nq-input mb-2 w-full text-xs"
              rows={4}
              placeholder="Nhập nội dung bài đăng..."
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
            />
            <Btn variant="primary" onClick={createDraft}>
              Lưu nháp
            </Btn>
          </div>

          <div className="space-y-2">
            <h3 className="text-sm font-bold">Danh sách nháp bài ({drafts.length})</h3>
            {drafts.length === 0 ? (
              <Empty>Chưa có bài nháp nào.</Empty>
            ) : (
              drafts.map((d) => (
                <div key={d.id} className="border border-[var(--nq-dim)] p-3">
                  <div className="flex items-center justify-between text-xs text-[var(--nq-muted)]">
                    <span>Người tạo: {d.nguoi_tao}</span>
                    <span>Trạng thái: {d.trang_thai}</span>
                  </div>
                  <p className="my-2 text-xs text-[var(--nq-primary)]">{d.noi_dung}</p>
                  {manager && d.trang_thai === "cho_duyet" ? (
                    <div className="flex gap-2">
                      <Btn variant="primary" onClick={() => decideDraft(d.id, "duyet")}>
                        Duyệt & Đăng
                      </Btn>
                      <Btn variant="ghost" onClick={() => decideDraft(d.id, "tu_choi")}>
                        Từ chối
                      </Btn>
                    </div>
                  ) : null}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 4: CẤU HÌNH THÔNG TIN QUÁN */}
      {tab === "config" && manager && (
        <div className="space-y-4 border-2 border-[var(--nq-dim)] p-4">
          <h3 className="text-sm font-bold">Cấu hình thông tin trả lời khách</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <div>
              <label className="text-xs text-[var(--nq-muted)]">Tên quán</label>
              <input
                type="text"
                className="nq-input w-full text-xs"
                value={profile?.name ?? ""}
                onChange={(e) => setProfile((p) => (p ? { ...p, name: e.target.value } : null))}
              />
            </div>
            <div>
              <label className="text-xs text-[var(--nq-muted)]">Địa chỉ</label>
              <input
                type="text"
                className="nq-input w-full text-xs"
                value={profile?.address ?? ""}
                onChange={(e) => setProfile((p) => (p ? { ...p, address: e.target.value } : null))}
              />
            </div>
            <div>
              <label className="text-xs text-[var(--nq-muted)]">Số điện thoại</label>
              <input
                type="text"
                className="nq-input w-full text-xs"
                value={profile?.phone ?? ""}
                onChange={(e) => setProfile((p) => (p ? { ...p, phone: e.target.value } : null))}
              />
            </div>
            <div>
              <label className="text-xs text-[var(--nq-muted)]">Giờ mở cửa</label>
              <input
                type="text"
                className="nq-input w-full text-xs"
                value={profile?.open_hours ?? ""}
                onChange={(e) => setProfile((p) => (p ? { ...p, open_hours: e.target.value } : null))}
              />
            </div>
          </div>
          <Btn variant="primary" onClick={saveProfile}>
            Lưu cấu hình
          </Btn>
        </div>
      )}
    </div>
  );
}
