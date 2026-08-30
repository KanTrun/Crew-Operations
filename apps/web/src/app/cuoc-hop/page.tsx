"use client";

import { useEffect, useRef, useState } from "react";
import { apiGet, apiSend, apiUpload } from "../../lib/api";
import { viError } from "../../lib/present";
import { getToken, isManager } from "../../lib/session";
import {
  Alert,
  AuthGate,
  Btn,
  Empty,
  Field,
  Loading,
  OpsCard,
  PageHeader,
  inputStyle,
  textareaStyle,
} from "../../ui/kit";

interface ActionItem {
  id: string;
  tieu_de: string;
  noi_dung_chi_tiet?: string;
  tinh_chat?: "bat_buoc" | "tuy_chon" | "khuyen_khich";
  ten_nguoi_giao?: string;
  nhan_vien_id?: string | null;
  ten_nguoi_nhan: string;
  pham_vi?: "ca_nhan" | "nhom";
  thoi_gian_bat_dau?: string;
  han_chot?: string;
  muc_do_uu_tien?: "cao" | "trung_binh" | "thap";
  do_tin_cay: number;
  da_chon?: boolean;
}

interface DeXuatPheDuyet {
  id: string;
  loai_de_xuat: "quy_trinh_sop" | "mua_sam_vat_tu" | "chinh_sach_nhan_su" | "khac";
  tieu_de: string;
  nguoi_de_xuat?: string;
  nguoi_phe_duyet?: string;
  noi_dung: string;
  ly_do?: string;
  trang_thai: "da_duyet" | "cho_duyet" | "tu_choi";
  quy_trinh_lien_quan?: string | null;
  buoc_so?: number | null;
}

interface DeXuatSop {
  quy_trinh_lien_quan: string;
  buoc_so?: number | null;
  noi_dung_thay_doi: string;
  ly_do?: string;
}

interface DoanThoai {
  nguoi_noi: string;
  bat_dau_s?: number;
  ket_thuc_s?: number;
  noi_dung: string;
}

interface VanDePhatSinh {
  van_de: string;
  trang_thai: "da_giai_quyet" | "can_hanh_dong" | "theo_doi";
  ghi_chu?: string;
}

interface GopYLuuY {
  id: string;
  nguoi_gop_y?: string;
  nguoi_nhan?: string;
  chu_de?: "thai_do_phuc_vu" | "ky_nang_pha_che" | "ve_sinh_an_toan" | "dong_vien_khen_ngoi" | "luu_y_chung";
  tinh_chat?: "nhac_nho" | "khen_ngoi" | "kinh_nghiem" | "gop_y";
  noi_dung: string;
  ghi_chu?: string;
}

interface TieuChiAudit {
  ma: string;
  ten_tieu_chi: string;
  dat: boolean;
  chi_tiet?: string;
}

interface AuditTuanThuSop {
  diem_tuan_thu: number;
  xep_hang: "A" | "B" | "C" | "D";
  tieu_chi: TieuChiAudit[];
  canh_bao_do?: string[];
  nhan_xet_chung?: string;
}

interface BanTinCaKhan {
  ban_vip?: string[];
  luu_y_di_ung_khach?: string[];
  su_co_thiet_bi_khan?: string[];
  danh_sach_mon_86?: string[];
  noi_dung_tin_nhan_gui_nhom?: string;
}

interface HuanLuyenQuanLy {
  ty_le_noi_quan_ly_pct: number;
  ty_le_noi_nhan_vien_pct: number;
  diem_tuong_tac_2_chieu: number;
  diem_truyen_cam_hung: number;
  phong_cach_dieu_hanh?: string;
  loi_khuyen_ai_coaching?: string[];
}

interface CuocHop {
  id: string;
  tieu_de: string;
  loai_hop: "giao_ca" | "hop_tuan" | "dao_tao" | "khac";
  thoi_gian?: string;
  nguon_am_thanh?: "google_meet_tab" | "microphone" | "file_upload" | "ghi_chep_tay";
  transcript_thoai?: DoanThoai[];
  khong_lien_quan?: boolean;
  tom_tat: string;
  van_de_phat_sinh?: VanDePhatSinh[];
  quyet_dinh?: string[];
  de_xuat_phe_duyet?: DeXuatPheDuyet[];
  action_items: ActionItem[];
  gop_y_luu_y?: GopYLuuY[];
  audit_sop?: AuditTuanThuSop;
  ban_tin_ca?: BanTinCaKhan;
  huan_luyen_quan_ly?: HuanLuyenQuanLy;
  de_xuat_sop?: DeXuatSop[];
  do_tin_cay_tong_the?: number;
  trang_thai?: "cho_duyet" | "da_duyet" | "tu_choi";
}





// Browser SpeechRecognition Type Definition
interface ISpeechRecognitionEvent {
  resultIndex: number;
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
      isFinal?: boolean;
    };
    length: number;
  };
}

interface ISpeechRecognition {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  onresult: ((event: ISpeechRecognitionEvent) => void) | null;
  onerror: ((event: unknown) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}

export default function MeetingPage() {
  const [token, setToken] = useState("");
  const [manager, setManager] = useState(false);
  const [inputMode, setInputMode] = useState<"meet" | "mic" | "upload" | "text">("mic");
  const [meetingType, setMeetingType] = useState<"giao_ca" | "hop_tuan" | "dao_tao">("giao_ca");

  // Recording & Live Subtitles State
  const [isRecording, setIsRecording] = useState(false);
  const [recordSeconds, setRecordSeconds] = useState(0);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [interimText, setInterimText] = useState("");
  const [volumeLevel, setVolumeLevel] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const speechRecognitionRef = useRef<ISpeechRecognition | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number | null>(null);

  // Manual Text / Upload State
  const [rawText, setRawText] = useState(
    "Quản lý: Chào ca chiều, máy pha số 2 đang bị rỉ nước ở ron cao su. Khách bàn 4 phàn nàn trà sữa đào ngọt gắt.\n" +
    "Tuấn: Dạ em sẽ thay ron máy pha và lau họng máy trước 16h.\n" +
    "Quản lý: Tốt. Từ nay đổi định lượng trà đào xuống còn 20ml syrup đào.\n" +
    "My: Dạ em sẽ dán bảng công thức mới ở quầy bar trước 17h.\n" +
    "Quản lý: Nhất trí. Tuấn nhớ kiểm tra thêm tủ đá trước 18h nhé."
  );
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Processing & Results
  const [busy, setBusy] = useState(false);
  const [statusMsg, setStatusMsg] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [meeting, setMeeting] = useState<CuocHop | null>(null);
  const [pastMeetings, setPastMeetings] = useState<CuocHop[]>([]);
  const [copiedBroadcast, setCopiedBroadcast] = useState(false);

  function handleCopyBroadcast(text: string) {
    if (!text) return;
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedBroadcast(true);
      setTimeout(() => setCopiedBroadcast(false), 3000);
    }
  }

  useEffect(() => {
    setToken(getToken());
    setManager(isManager());
    loadHistory();
  }, []);


  async function loadHistory() {
    try {
      const res = await apiGet<{ items: CuocHop[] }>("/api/v1/meetings");
      setPastMeetings(res.items || []);
    } catch {
      // Ignored if offline
    }
  }

  // Setup Live Web Speech Recognition (Vietnamese)
  function initLiveSpeechRecognition() {
    if (typeof window === "undefined") return;
    const SpeechRecognitionClass =
      (window as unknown as { SpeechRecognition?: new () => ISpeechRecognition }).SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: new () => ISpeechRecognition }).webkitSpeechRecognition;

    if (!SpeechRecognitionClass) return;

    try {
      const recognition = new SpeechRecognitionClass();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = "vi-VN";

      recognition.onresult = (event: ISpeechRecognitionEvent) => {
        let finalStr = "";
        let interimStr = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          const transcriptChunk = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalStr += transcriptChunk + " ";
          } else {
            interimStr += transcriptChunk;
          }
        }
        if (finalStr) {
          setLiveTranscript((prev) => (prev ? prev + " " + finalStr.trim() : finalStr.trim()));
        }
        setInterimText(interimStr);
      };

      recognition.onerror = () => {
        // Fallback gracefully
      };

      speechRecognitionRef.current = recognition;
      recognition.start();
    } catch {
      // Browser does not support Web Speech API
    }
  }

  // Setup Volume Meter Visualizer
  function setupAudioMeter(stream: MediaStream) {
    try {
      const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      audioContextRef.current = audioCtx;
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      const source = audioCtx.createMediaStreamSource(stream);
      source.connect(analyser);

      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateMeter = () => {
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        setVolumeLevel(Math.min(100, Math.round((avg / 128) * 100)));
        animFrameRef.current = requestAnimationFrame(updateMeter);
      };
      updateMeter();
    } catch {
      // Ignored if audio context not permitted
    }
  }

  // 1. Google Meet Tab Audio Capture
  async function startMeetCapture() {
    setError(null);
    setSuccess(null);
    audioChunksRef.current = [];
    setLiveTranscript("");
    setInterimText("");

    try {
      const displayStream = await navigator.mediaDevices.getDisplayMedia({
        video: true,
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
        } as MediaTrackConstraints,
      });

      let micStream: MediaStream | null = null;
      try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch {
        // Continue with tab audio only
      }

      const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
      const dest = audioCtx.createMediaStreamDestination();

      const tabAudioTracks = displayStream.getAudioTracks();
      if (tabAudioTracks.length === 0) {
        throw new Error("Bạn chưa tích chọn 'Chia sẻ âm thanh của thẻ (Share tab audio)' khi chọn tab Google Meet.");
      }

      const tabSource = audioCtx.createMediaStreamSource(new MediaStream(tabAudioTracks));
      tabSource.connect(dest);

      if (micStream && micStream.getAudioTracks().length > 0) {
        const micSource = audioCtx.createMediaStreamSource(micStream);
        micSource.connect(dest);
      }

      const mixedStream = dest.stream;
      setupAudioMeter(mixedStream);
      initLiveSpeechRecognition();

      const recorder = new MediaRecorder(mixedStream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm",
        audioBitsPerSecond: 32000,
      });

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        displayStream.getTracks().forEach((t) => t.stop());
        if (micStream) micStream.getTracks().forEach((t) => t.stop());
        if (audioContextRef.current) audioContextRef.current.close();
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
        if (speechRecognitionRef.current) {
          try { speechRecognitionRef.current.stop(); } catch {}
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await handleAudioBlob(audioBlob, "google_meet_tab");
      };

      mediaRecorderRef.current = recorder;
      recorder.start(1000);
      setIsRecording(true);
      setRecordSeconds(0);

      timerRef.current = setInterval(() => {
        setRecordSeconds((s) => s + 1);
      }, 1000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Không thể bắt luồng âm thanh Google Meet.");
    }
  }

  // 2. Microphone Recording
  async function startMicRecording() {
    setError(null);
    setSuccess(null);
    audioChunksRef.current = [];
    setLiveTranscript("");
    setInterimText("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setupAudioMeter(stream);
      initLiveSpeechRecognition();

      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm",
        audioBitsPerSecond: 32000,
      });

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        if (audioContextRef.current) audioContextRef.current.close();
        if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
        if (speechRecognitionRef.current) {
          try { speechRecognitionRef.current.stop(); } catch {}
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await handleAudioBlob(audioBlob, "microphone");
      };

      mediaRecorderRef.current = recorder;
      recorder.start(1000);
      setIsRecording(true);
      setRecordSeconds(0);

      timerRef.current = setInterval(() => {
        setRecordSeconds((s) => s + 1);
      }, 1000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Không thể mở Microphone trên thiết bị.");
    }
  }

  function stopRecording() {
    if (timerRef.current) clearInterval(timerRef.current);
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }

  // Handle Audio Blob Upload
  async function handleAudioBlob(blob: Blob, source: "google_meet_tab" | "microphone") {
    setBusy(true);
    setStatusMsg("Đang truyền âm thanh & bóc băng thoại với Gemini 3.5 Transcribe...");
    try {
      const form = new FormData();
      form.append("file", blob, "meeting_recording.webm");
      form.append("meeting_type", meetingType);
      form.append("audio_source", source);
      form.append("live_transcript", liveTranscript);

      setStatusMsg("Đang phân tích Action Items & Đề xuất Cẩm nang quán...");
      const res = await apiUpload<CuocHop>("/api/v1/meeting/process-audio", form);
      
      // If the backend transcript is empty, fallback to captured live browser speech
      if ((!res.transcript_thoai || res.transcript_thoai.length === 0) && liveTranscript.trim()) {
        res.transcript_thoai = [{ nguoi_noi: "Giao ca", noi_dung: liveTranscript.trim() }];
      }


      setMeeting(res);
      setSuccess("Bóc băng và phân tích cuộc họp hoàn tất!");
    } catch (e) {
      setError(viError(e, { doing: "xử lý âm thanh cuộc họp" }));
    } finally {
      setBusy(false);
      setStatusMsg("");
    }
  }

  // 3. Analyze Free Text
  async function analyzeText() {
    if (!rawText.trim()) {
      setError("Vui lòng nhập nội dung cuộc họp.");
      return;
    }
    setError(null);
    setSuccess(null);
    setBusy(true);
    setStatusMsg("AG-MEETING đang bóc tách việc và quyết định...");
    try {
      const res = await apiSend<CuocHop>("/api/v1/meeting/analyze", {
        text: rawText.trim(),
        meeting_type: meetingType,
        audio_source: "ghi_chep_tay",
      });
      setMeeting(res);
      setSuccess("Phân tích cuộc họp hoàn tất!");
    } catch (e) {
      setError(viError(e, { doing: "phân tích văn bản cuộc họp" }));
    } finally {
      setBusy(false);
      setStatusMsg("");
    }
  }

  // 4. Upload Audio File
  async function uploadFile() {
    if (!selectedFile) {
      setError("Vui lòng chọn file âm thanh.");
      return;
    }
    setError(null);
    setSuccess(null);
    setBusy(true);
    setStatusMsg("Đang tải file lên & gọi Gemini 3.5 Transcribe...");
    try {
      const form = new FormData();
      form.append("file", selectedFile);
      form.append("meeting_type", meetingType);
      form.append("audio_source", "file_upload");

      const res = await apiUpload<CuocHop>("/api/v1/meeting/process-audio", form);
      setMeeting(res);
      setSuccess("Bóc băng file âm thanh thành công!");
    } catch (e) {
      setError(viError(e, { doing: "xử lý file âm thanh" }));
    } finally {
      setBusy(false);
      setStatusMsg("");
    }
  }

  // 5. Apply Decisions (Human-in-the-loop)
  async function applyDecisions() {
    if (!meeting) return;
    setError(null);
    setSuccess(null);
    setBusy(true);
    setStatusMsg("Đang đẩy việc treo vào ca & cập nhật Cẩm nang...");
    try {
      const res = await apiSend<{ ok: boolean; tasks_created: number; sop_proposals: number }>(
        "/api/v1/meeting/apply",
        meeting,
      );
      if (res.ok) {
        setSuccess(`Đã duyệt! Tạo thành công ${res.tasks_created} việc treo vào ca và ${res.sop_proposals} đề xuất Cẩm nang.`);
        loadHistory();
      }
    } catch (e) {
      setError(viError(e, { doing: "phê duyệt cuộc họp" }));
    } finally {
      setBusy(false);
      setStatusMsg("");
    }
  }

  function toggleActionItem(id: string) {
    if (!meeting) return;
    setMeeting({
      ...meeting,
      action_items: meeting.action_items.map((it) =>
        it.id === id ? { ...it, da_chon: !it.da_chon } : it
      ),
    });
  }

  function updateActionAssignee(id: string, name: string) {
    if (!meeting) return;
    setMeeting({
      ...meeting,
      action_items: meeting.action_items.map((it) =>
        it.id === id ? { ...it, ten_nguoi_nhan: name } : it
      ),
    });
  }

  function updateActionDue(id: string, due: string) {
    if (!meeting) return;
    setMeeting({
      ...meeting,
      action_items: meeting.action_items.map((it) =>
        it.id === id ? { ...it, han_chot: due } : it
      ),
    });
  }

  const formatTimer = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  if (!token) return <AuthGate />;

  return (
    <div className="nq-page nq-page--run max-w-5xl mx-auto p-4 space-y-6">
      <PageHeader
        kicker="AI MEETING OS"
        title="Cuộc họp & Giao ca Thông minh"
        meta="Tự động bóc băng Google Meet / Giao ca với Gemini 3.5 Transcribe · Trích xuất việc cần làm · Đề xuất Cẩm nang."
      />

      {error && <Alert kind="err">{error}</Alert>}
      {success && <Alert kind="ok">{success}</Alert>}

      {/* 1. INPUT HUB */}
      <OpsCard title="1. Thu thập & Tiếp nhận Cuộc họp">
        <div className="space-y-4">
          <div className="flex flex-wrap gap-2 items-center justify-between">
            <div className="flex gap-2">
              <Btn
                variant={inputMode === "mic" ? "primary" : "ghost"}
                onClick={() => { setInputMode("mic"); setError(null); }}
              >
                🎙️ Micro Giao ca
              </Btn>
              <Btn
                variant={inputMode === "meet" ? "primary" : "ghost"}
                onClick={() => { setInputMode("meet"); setError(null); }}
              >
                🌐 Google Meet Tab
              </Btn>
              <Btn
                variant={inputMode === "upload" ? "primary" : "ghost"}
                onClick={() => { setInputMode("upload"); setError(null); }}
              >
                📁 Tải File Audio
              </Btn>
              <Btn
                variant={inputMode === "text" ? "primary" : "ghost"}
                onClick={() => { setInputMode("text"); setError(null); }}
              >
                📝 Dán Ghi chép
              </Btn>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs opacity-75 font-mono uppercase">Loại họp:</span>
              <select
                value={meetingType}
                onChange={(e) => setMeetingType(e.target.value as "giao_ca" | "hop_tuan" | "dao_tao")}
                className="bg-neutral-800 text-white text-sm p-1.5 rounded border border-neutral-700 font-mono"
              >
                <option value="giao_ca">Họp Giao ca (Standup)</option>
                <option value="hop_tuan">Họp Tuần / Vận hành</option>
                <option value="dao_tao">Đào tạo / Phổ biến SOP</option>
              </select>
            </div>
          </div>

          {/* Mode 1: Microphone Live Recording */}
          {inputMode === "mic" && (
            <div className="border border-amber-500/30 bg-amber-950/20 p-4 rounded-lg space-y-3">
              <div className="flex items-start gap-3">
                <span className="text-2xl">🎙️</span>
                <div className="text-sm">
                  <p className="font-bold text-amber-300">Ghi âm trực tiếp tại Quầy quán (Hiển thị chữ thời gian thực)</p>
                  <p className="opacity-80">
                    Bấm bắt đầu và nói tự nhiên. Lời nói sẽ tự động chuyển thành văn bản và chạy trực tiếp trên màn hình.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4 pt-2">
                {!isRecording ? (
                  <Btn variant="primary" onClick={startMicRecording} disabled={busy}>
                    🎙️ Bắt đầu ghi âm giao ca
                  </Btn>
                ) : (
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="animate-ping w-3 h-3 rounded-full bg-red-500 inline-block" />
                    <span className="font-mono text-red-400 font-bold text-lg">ĐANG THU: {formatTimer(recordSeconds)}</span>
                    
                    {/* Audio Level Indicator */}
                    <div className="flex items-center gap-1.5 bg-neutral-900/80 px-3 py-1.5 rounded border border-neutral-800">
                      <span className="text-xs font-mono opacity-60">ÂM LƯỢNG:</span>
                      <div className="w-20 bg-neutral-800 h-2 rounded overflow-hidden">
                        <div
                          className="bg-emerald-500 h-full transition-all duration-100"
                          style={{ width: `${volumeLevel}%` }}
                        />
                      </div>
                    </div>

                    <Btn variant="danger" onClick={stopRecording}>
                      ⏹️ Hoàn tất & Trích xuất
                    </Btn>
                  </div>
                )}
              </div>

              {/* Live Speech Recognition Subtitle Box */}
              {isRecording && (
                <div className="mt-3 p-3 bg-neutral-900/90 rounded border border-amber-500/40 space-y-1 animate-pulse">
                  <div className="flex items-center gap-2 text-xs font-mono text-amber-400 font-bold">
                    <span className="w-2 h-2 rounded-full bg-amber-400" />
                    VĂN BẢN ĐANG NÓI TRỰC TIẾP (LIVE SPEECH-TO-TEXT):
                  </div>
                  <p className="text-sm text-neutral-100 font-sans italic min-h-[2.5rem]">
                    {liveTranscript} <span className="text-amber-300 underline">{interimText}</span>
                    {!liveTranscript && !interimText && "Đang lắng nghe giọng nói của bạn qua Micro..."}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Mode 2: Google Meet Tab Audio Capture */}
          {inputMode === "meet" && (
            <div className="border border-cyan-500/30 bg-cyan-950/20 p-4 rounded-lg space-y-3">
              <div className="flex items-start gap-3">
                <span className="text-2xl">🌐</span>
                <div className="text-sm">
                  <p className="font-bold text-cyan-300">Bắt âm thanh trực tiếp từ Tab Google Meet (0đ / Miễn phí)</p>
                  <p className="opacity-80">
                    Khi bấm bắt đầu, chọn tab <strong>Google Meet</strong> và nhớ tích ô <strong>"Chia sẻ âm thanh thẻ (Share tab audio)"</strong>.
                    Hệ thống sẽ tự động gộp âm thanh người nói trong phòng và giọng của bạn.
                  </p>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-4 pt-2">
                {!isRecording ? (
                  <Btn variant="primary" onClick={startMeetCapture} disabled={busy}>
                    🚀 Bắt đầu theo dõi Google Meet
                  </Btn>
                ) : (
                  <div className="flex items-center gap-3 flex-wrap">
                    <span className="animate-ping w-3 h-3 rounded-full bg-red-500 inline-block" />
                    <span className="font-mono text-red-400 font-bold text-lg">ĐANG GHI ÂM: {formatTimer(recordSeconds)}</span>

                    <div className="flex items-center gap-1.5 bg-neutral-900/80 px-3 py-1.5 rounded border border-neutral-800">
                      <span className="text-xs font-mono opacity-60">ÂM LƯỢNG:</span>
                      <div className="w-20 bg-neutral-800 h-2 rounded overflow-hidden">
                        <div
                          className="bg-cyan-500 h-full transition-all duration-100"
                          style={{ width: `${volumeLevel}%` }}
                        />
                      </div>
                    </div>

                    <Btn variant="danger" onClick={stopRecording}>
                      ⏹️ Dừng & Phân tích AI
                    </Btn>
                  </div>
                )}
              </div>

              {isRecording && (
                <div className="mt-3 p-3 bg-neutral-900/90 rounded border border-cyan-500/40 space-y-1 animate-pulse">
                  <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 font-bold">
                    <span className="w-2 h-2 rounded-full bg-cyan-400" />
                    VĂN BẢN ĐANG THU THẬP TRỰC TIẾP TỪ CUỘC HỌP:
                  </div>
                  <p className="text-sm text-neutral-100 font-sans italic min-h-[2.5rem]">
                    {liveTranscript} <span className="text-cyan-300 underline">{interimText}</span>
                    {!liveTranscript && !interimText && "Đang lắng nghe âm thanh từ Google Meet..."}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Mode 3: File Upload */}
          {inputMode === "upload" && (
            <div className="border border-neutral-700 bg-neutral-900/40 p-4 rounded-lg space-y-3">
              <Field label="Chọn file âm thanh (.mp3, .m4a, .wav, .webm)">
                <input
                  type="file"
                  accept="audio/*,.mp3,.m4a,.wav,.webm"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="text-sm text-neutral-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-copper file:text-white hover:file:opacity-90"
                />
              </Field>
              <Btn variant="primary" onClick={uploadFile} disabled={busy || !selectedFile}>
                📤 Tải lên & Xử lý với Gemini 3.5 Transcribe
              </Btn>
            </div>
          )}

          {/* Mode 4: Text Input */}
          {inputMode === "text" && (
            <div className="space-y-3">
              <Field label="Nội dung ghi chép cuộc họp">
                <textarea
                  style={textareaStyle}
                  rows={6}
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder="Dán biên bản hoặc nội dung trao đổi tại đây..."
                />
              </Field>
              <Btn variant="primary" onClick={analyzeText} disabled={busy}>
                ⚡ Phân tích Biên bản
              </Btn>
            </div>
          )}

          {busy && (
            <div className="p-4 bg-neutral-800/80 rounded border border-neutral-700 flex items-center gap-3">
              <Loading />
              <span className="text-sm text-cyan-300 font-mono animate-pulse">{statusMsg || "Đang xử lý..."}</span>
            </div>
          )}
        </div>
      </OpsCard>

      {/* 2. RESULTS & HUMAN-IN-THE-LOOP APPROVAL */}
      {meeting && (
        <div className="space-y-6">
          <OpsCard title={`2. Kết quả Phân tích: ${meeting.tieu_de}`}>
            <div className="space-y-6">

              {/* PROMINENT TRANSCRIPT SECTION */}
              <div className="p-4 bg-neutral-900/90 rounded border border-neutral-700 space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-cyan-300 font-bold flex items-center gap-2">
                    🎙️ Bản Bóc Băng Thoại Cuộc Họp (Speaker Diarization)
                  </h4>
                  <span className="text-xs font-mono px-2 py-0.5 bg-neutral-800 text-neutral-400 rounded">
                    Nguồn: {meeting.nguon_am_thanh}
                  </span>
                </div>

                {meeting.transcript_thoai && meeting.transcript_thoai.length > 0 ? (
                  <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                    {meeting.transcript_thoai.map((t, idx) => (
                      <div key={idx} className="p-2.5 bg-neutral-950/70 rounded border border-neutral-800 flex gap-3 items-start">
                        <span className="font-bold text-xs font-mono uppercase px-2 py-1 rounded bg-cyan-950 text-cyan-300 border border-cyan-800 shrink-0">
                          {t.nguoi_noi || "Người nói"}
                        </span>
                        <p className="text-sm text-neutral-200 leading-relaxed">{t.noi_dung}</p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-neutral-400 italic">
                    {liveTranscript ? liveTranscript : "Đã trích xuất nội dung từ ghi chú cuộc họp."}
                  </p>
                )}
              </div>

              {/* Summary & Decisions */}
              <div className="grid md:grid-cols-2 gap-4">
                <div className="p-4 bg-neutral-900/60 rounded border border-neutral-800">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-cyan-400 font-bold mb-2">
                    📋 Tóm tắt Cuộc họp
                  </h4>
                  <p className="text-sm leading-relaxed">{meeting.tom_tat}</p>
                </div>

                <div className="p-4 bg-neutral-900/60 rounded border border-neutral-800">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-emerald-400 font-bold mb-2">
                    ✅ Quyết định đã chốt trong họp
                  </h4>
                  {meeting.quyet_dinh && meeting.quyet_dinh.length > 0 ? (
                    <ul className="text-sm space-y-1.5 list-none">
                      {meeting.quyet_dinh.map((q, idx) => (
                        <li key={idx} className="flex gap-2 items-start">
                          <span className="text-emerald-400 shrink-0 mt-0.5">✓</span>
                          <span>{q}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-neutral-400 italic">Duy trì đúng quy trình vận hành ca.</p>
                  )}
                </div>
              </div>

              {/* Van De Phat Sinh — v2 */}
              {meeting.van_de_phat_sinh && meeting.van_de_phat_sinh.length > 0 && (
                <div className="space-y-2">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-rose-400 font-bold">
                    🔍 Vấn đề Phát sinh — Tình trạng Giải quyết
                  </h4>
                  <div className="space-y-2">
                    {meeting.van_de_phat_sinh.map((vd, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded border flex gap-3 items-start ${
                          vd.trang_thai === "da_giai_quyet"
                            ? "bg-emerald-950/20 border-emerald-800/40"
                            : vd.trang_thai === "theo_doi"
                            ? "bg-amber-950/20 border-amber-800/40"
                            : "bg-rose-950/20 border-rose-800/40"
                        }`}
                      >
                        <span className="text-lg shrink-0">
                          {vd.trang_thai === "da_giai_quyet" ? "✅" : vd.trang_thai === "theo_doi" ? "👁️" : "⚠️"}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 flex-wrap">
                            <p className="text-sm font-semibold">{vd.van_de}</p>
                            <span
                              className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                                vd.trang_thai === "da_giai_quyet"
                                  ? "bg-emerald-900/60 text-emerald-300"
                                  : vd.trang_thai === "theo_doi"
                                  ? "bg-amber-900/60 text-amber-300"
                                  : "bg-rose-900/60 text-rose-300"
                              }`}
                            >
                              {vd.trang_thai === "da_giai_quyet"
                                ? "Đã giải quyết trong họp"
                                : vd.trang_thai === "theo_doi"
                                ? "Cần theo dõi thêm"
                                : "Cần hành động sau họp"}
                            </span>
                          </div>
                          {vd.ghi_chu && (
                            <p className="text-xs text-neutral-400 mt-1 italic">{vd.ghi_chu}</p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* BLOCK A: SOP AUDIT & COMPLIANCE REPORT */}
              {meeting.audit_sop && (
                <div className="space-y-3 p-4 bg-emerald-950/20 rounded border border-emerald-700/40">
                  <div className="flex flex-wrap justify-between items-center gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xl">🛡️</span>
                      <div>
                        <h4 className="text-xs font-mono uppercase tracking-wider text-emerald-300 font-bold">
                          Báo Cáo Kiểm Soát Tuân Thủ SOP Ca (SOP Audit Report)
                        </h4>
                        <p className="text-[11px] text-neutral-400">
                          AI tự động đối soát nội dung briefing với 5 tiêu chuẩn vàng vận hành quán
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-mono font-bold px-2.5 py-1 rounded border uppercase ${
                          meeting.audit_sop.xep_hang === "A"
                            ? "bg-emerald-900/80 text-emerald-200 border-emerald-500"
                            : meeting.audit_sop.xep_hang === "B"
                            ? "bg-blue-900/80 text-blue-200 border-blue-500"
                            : meeting.audit_sop.xep_hang === "C"
                            ? "bg-amber-900/80 text-amber-200 border-amber-500"
                            : "bg-rose-900/80 text-rose-200 border-rose-500"
                        }`}
                      >
                        Xếp Hạng: Hạng {meeting.audit_sop.xep_hang}
                      </span>
                      <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-neutral-900 border border-neutral-700 text-emerald-400">
                        {meeting.audit_sop.diem_tuan_thu}/100 Điểm
                      </span>
                    </div>
                  </div>

                  {/* Red Flags / Cảnh báo đỏ */}
                  {meeting.audit_sop.canh_bao_do && meeting.audit_sop.canh_bao_do.length > 0 && (
                    <div className="p-2.5 bg-rose-950/40 border border-rose-600/60 rounded space-y-1">
                      <p className="text-xs font-bold text-rose-300 flex items-center gap-1.5">
                        <span>🚨</span> CẢNH BÁO ĐỎ TỪ BAN KIỂM SOÁT:
                      </p>
                      <ul className="list-disc list-inside text-xs text-rose-200 space-y-0.5 pl-2">
                        {meeting.audit_sop.canh_bao_do.map((cb, i) => (
                          <li key={i}>{cb}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* 5 Tiêu chuẩn checklist */}
                  {meeting.audit_sop.tieu_chi && meeting.audit_sop.tieu_chi.length > 0 && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-1">
                      {meeting.audit_sop.tieu_chi.map((tc, idx) => (
                        <div
                          key={idx}
                          className={`p-2.5 rounded border text-xs flex items-start gap-2 ${
                            tc.dat
                              ? "bg-emerald-950/20 border-emerald-800/40 text-neutral-200"
                              : "bg-neutral-900/60 border-neutral-800 text-neutral-400"
                          }`}
                        >
                          <span className="text-sm shrink-0 mt-0.5">
                            {tc.dat ? "✅" : "❌"}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between gap-1">
                              <span className={`font-bold ${tc.dat ? "text-emerald-300" : "text-neutral-300"}`}>
                                {tc.ten_tieu_chi}
                              </span>
                              <span
                                className={`text-[10px] font-mono px-1 rounded uppercase ${
                                  tc.dat ? "bg-emerald-900/60 text-emerald-300" : "bg-neutral-800 text-neutral-500"
                                }`}
                              >
                                {tc.dat ? "Đạt" : "Bỏ sót"}
                              </span>
                            </div>
                            {tc.chi_tiet && (
                              <p className="text-[11px] text-neutral-400 mt-0.5 italic">
                                {tc.chi_tiet}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {meeting.audit_sop.nhan_xet_chung && (
                    <p className="text-xs text-neutral-300 italic pt-1 border-t border-emerald-900/30">
                      💡 <strong>Nhận xét:</strong> {meeting.audit_sop.nhan_xet_chung}
                    </p>
                  )}
                </div>
              )}

              {/* BLOCK B: SHIFT BROADCAST & QUICK SYNC (Bản tin ca khẩn cấp) */}
              {meeting.ban_tin_ca && (
                <div className="space-y-3 p-4 bg-amber-950/20 rounded border border-amber-600/40">
                  <div className="flex flex-wrap justify-between items-center gap-2">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">📢</span>
                      <div>
                        <h4 className="text-xs font-mono uppercase tracking-wider text-amber-300 font-bold">
                          Bản Tin Ca Khẩn Cấp (Shift Broadcast & Sync)
                        </h4>
                        <p className="text-[11px] text-neutral-400">
                          Tổng hợp lưu ý sống còn: VIP, dị ứng, món hết, sự cố máy móc để bắn vào nhóm ca
                        </p>
                      </div>
                    </div>

                    {meeting.ban_tin_ca.noi_dung_tin_nhan_gui_nhom && (
                      <button
                        type="button"
                        onClick={() => handleCopyBroadcast(meeting.ban_tin_ca?.noi_dung_tin_nhan_gui_nhom || "")}
                        className={`text-xs font-mono font-bold px-3 py-1.5 rounded transition-all flex items-center gap-1.5 ${
                          copiedBroadcast
                            ? "bg-emerald-600 text-white"
                            : "bg-amber-600 hover:bg-amber-500 text-neutral-950"
                        }`}
                      >
                        <span>{copiedBroadcast ? "✅" : "📋"}</span>
                        {copiedBroadcast ? "Đã sao chép tin nhắn!" : "Sao chép Bản Tin Ca (Zalo/Telegram)"}
                      </button>
                    )}
                  </div>

                  {/* Highlights Grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
                    {/* VIP */}
                    <div className="p-2 rounded bg-neutral-900/80 border border-neutral-800 space-y-1">
                      <span className="text-[11px] font-bold text-amber-400 flex items-center gap-1">
                        🌟 Bàn VIP / Đặt trước
                      </span>
                      {meeting.ban_tin_ca.ban_vip && meeting.ban_tin_ca.ban_vip.length > 0 ? (
                        <ul className="text-xs text-neutral-200 space-y-0.5">
                          {meeting.ban_tin_ca.ban_vip.map((v, i) => (
                            <li key={i}>• {v}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-[11px] text-neutral-500 italic">Không có</p>
                      )}
                    </div>

                    {/* Dị ứng */}
                    <div className="p-2 rounded bg-neutral-900/80 border border-neutral-800 space-y-1">
                      <span className="text-[11px] font-bold text-rose-400 flex items-center gap-1">
                        ⚠️ Khách dị ứng / Lưu ý
                      </span>
                      {meeting.ban_tin_ca.luu_y_di_ung_khach && meeting.ban_tin_ca.luu_y_di_ung_khach.length > 0 ? (
                        <ul className="text-xs text-rose-200 space-y-0.5">
                          {meeting.ban_tin_ca.luu_y_di_ung_khach.map((v, i) => (
                            <li key={i}>• {v}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-[11px] text-neutral-500 italic">Không có</p>
                      )}
                    </div>

                    {/* Sự cố */}
                    <div className="p-2 rounded bg-neutral-900/80 border border-neutral-800 space-y-1">
                      <span className="text-[11px] font-bold text-orange-400 flex items-center gap-1">
                        🔧 Sự cố thiết bị khẩn
                      </span>
                      {meeting.ban_tin_ca.su_co_thiet_bi_khan && meeting.ban_tin_ca.su_co_thiet_bi_khan.length > 0 ? (
                        <ul className="text-xs text-orange-200 space-y-0.5">
                          {meeting.ban_tin_ca.su_co_thiet_bi_khan.map((v, i) => (
                            <li key={i}>• {v}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-[11px] text-neutral-500 italic">Bình thường</p>
                      )}
                    </div>

                    {/* Món 86 */}
                    <div className="p-2 rounded bg-neutral-900/80 border border-neutral-800 space-y-1">
                      <span className="text-[11px] font-bold text-red-400 flex items-center gap-1">
                        🚫 Món hết (86 List)
                      </span>
                      {meeting.ban_tin_ca.danh_sach_mon_86 && meeting.ban_tin_ca.danh_sach_mon_86.length > 0 ? (
                        <ul className="text-xs text-red-200 space-y-0.5">
                          {meeting.ban_tin_ca.danh_sach_mon_86.map((v, i) => (
                            <li key={i}>• {v}</li>
                          ))}
                        </ul>
                      ) : (
                        <p className="text-[11px] text-neutral-500 italic">Đủ món</p>
                      )}
                    </div>
                  </div>

                  {/* Preformatted text preview */}
                  {meeting.ban_tin_ca.noi_dung_tin_nhan_gui_nhom && (
                    <div className="p-2.5 bg-neutral-950/80 rounded border border-neutral-800 font-mono text-xs text-amber-200/90 whitespace-pre-wrap">
                      {meeting.ban_tin_ca.noi_dung_tin_nhan_gui_nhom}
                    </div>
                  )}
                </div>
              )}

              {/* SECTION 1: PROPOSALS & APPROVALS (Đề xuất & Phê duyệt) */}
              {meeting.de_xuat_phe_duyet && meeting.de_xuat_phe_duyet.length > 0 && (
                <div className="space-y-3 p-4 bg-purple-950/20 rounded border border-purple-800/40">
                  <div className="flex justify-between items-center">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-purple-300 font-bold flex items-center gap-2">
                      📌 Đề Xuất Cần Phê Duyệt (Proposals & Approvals)
                    </h4>
                    <span className="text-xs font-mono px-2 py-0.5 bg-purple-900/60 text-purple-200 rounded">
                      {meeting.de_xuat_phe_duyet.length} đề xuất
                    </span>
                  </div>


                  <div className="space-y-2.5">
                    {meeting.de_xuat_phe_duyet.map((prop) => (
                      <div
                        key={prop.id}
                        className={`p-3.5 rounded border transition-all ${
                          prop.trang_thai === "da_duyet"
                            ? "bg-emerald-950/20 border-emerald-700/50"
                            : prop.trang_thai === "tu_choi"
                            ? "bg-rose-950/20 border-rose-800/50"
                            : "bg-amber-950/20 border-amber-800/50"
                        }`}
                      >
                        <div className="flex flex-wrap items-start justify-between gap-2">
                          <div className="space-y-1 flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="font-bold text-sm text-neutral-100">{prop.tieu_de}</span>
                              <span
                                className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                                  prop.trang_thai === "da_duyet"
                                    ? "bg-emerald-800/80 text-emerald-200 border border-emerald-600"
                                    : prop.trang_thai === "tu_choi"
                                    ? "bg-rose-800/80 text-rose-200 border border-rose-600"
                                    : "bg-amber-800/80 text-amber-200 border border-amber-600"
                                }`}
                              >
                                {prop.trang_thai === "da_duyet"
                                  ? "✅ ĐÃ DUYỆT TẠI HỌP"
                                  : prop.trang_thai === "tu_choi"
                                  ? "❌ BỊ TỪ CHỐI"
                                  : "⏳ CHỜ QUẢN LÝ DUYỆT"}
                              </span>
                              <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-300">
                                Loại: {prop.loai_de_xuat === "quy_trinh_sop" ? "Quy trình SOP" : prop.loai_de_xuat === "mua_sam_vat_tu" ? "Mua sắm / Vật tư" : prop.loai_de_xuat === "chinh_sach_nhan_su" ? "Nhân sự" : "Khác"}
                              </span>
                            </div>

                            <p className="text-xs text-neutral-300 leading-relaxed mt-1">
                              <strong>Nội dung:</strong> {prop.noi_dung}
                            </p>
                            {prop.ly_do && (
                              <p className="text-xs text-neutral-400 italic">
                                <strong>Lý do:</strong> {prop.ly_do}
                              </p>
                            )}

                            <div className="flex flex-wrap gap-3 text-[11px] font-mono text-neutral-400 pt-1">
                              {prop.nguoi_de_xuat && (
                                <span>👤 Người đề xuất: <strong className="text-neutral-200">{prop.nguoi_de_xuat}</strong></span>
                              )}
                              {prop.nguoi_phe_duyet && (
                                <span>👑 Người duyệt: <strong className="text-emerald-300">{prop.nguoi_phe_duyet}</strong></span>
                              )}
                              {prop.quy_trinh_lien_quan && (
                                <span>📖 Quy trình liên quan: <strong className="text-purple-300">{prop.quy_trinh_lien_quan}</strong></span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* SECTION 2: MANDATORY ACTION ITEMS (Công việc được giao bắt buộc) */}
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-amber-400 font-bold flex items-center gap-2">
                    🎯 Công Việc Được Giao Bắt Buộc (Mandatory Action Items)
                  </h4>
                  <span className="text-xs font-mono opacity-60">
                    Độ tin cậy AI: {Math.round((meeting.do_tin_cay_tong_the || 0.9) * 100)}%
                  </span>
                </div>

                {meeting.action_items.length === 0 ? (
                  <Empty title="Không có việc giao phát sinh">Không phát hiện công việc giao bắt buộc.</Empty>
                ) : (
                  <div className="space-y-2.5">
                    {meeting.action_items.map((it) => (
                      <div
                        key={it.id}
                        className={`p-3.5 rounded border transition-all ${
                          it.da_chon
                            ? "border-amber-700/50 bg-amber-950/15"
                            : "border-neutral-800 bg-neutral-900/30 opacity-50"
                        }`}
                      >
                        <div className="flex gap-3 items-start">
                          <input
                            type="checkbox"
                            checked={it.da_chon}
                            onChange={() => toggleActionItem(it.id)}
                            className="w-4 h-4 rounded cursor-pointer accent-copper mt-1 shrink-0"
                          />
                          <div className="flex-1 min-w-0 space-y-2">
                            {/* Row 1: Title + badges */}
                            <div className="flex flex-wrap items-center gap-2">
                              <p className="text-sm font-bold text-neutral-100">{it.tieu_de}</p>
                              
                              {/* Tinh chat: Bat buoc vs Khuyen khich */}
                              <span
                                className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-bold ${
                                  it.tinh_chat === "bat_buoc" || !it.tinh_chat
                                    ? "bg-rose-900/70 text-rose-200 border border-rose-600"
                                    : "bg-blue-900/70 text-blue-200 border border-blue-600"
                                }`}
                              >
                                {it.tinh_chat === "bat_buoc" || !it.tinh_chat ? "🔴 Bắt buộc" : "🔵 Khuyến khích"}
                              </span>

                              <span
                                className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded shrink-0 ${
                                  it.pham_vi === "ca_nhan"
                                    ? "bg-blue-900/60 text-blue-300 border border-blue-700"
                                    : "bg-violet-900/60 text-violet-300 border border-violet-700"
                                }`}
                              >
                                {it.pham_vi === "ca_nhan" ? "👤 Cá nhân" : "👥 Nhóm ca"}
                              </span>

                              {it.muc_do_uu_tien === "cao" && (
                                <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-red-900/60 text-red-300 border border-red-700 shrink-0 font-bold">
                                  🔥 Ưu tiên cao
                                </span>
                              )}
                            </div>

                            {/* Row 2: Detail description */}
                            {it.noi_dung_chi_tiet && (
                              <p className="text-xs text-neutral-200 bg-neutral-900/80 p-2.5 rounded border border-neutral-800 leading-relaxed">
                                📝 <strong>Chi tiết thực hiện:</strong> {it.noi_dung_chi_tiet}
                              </p>
                            )}

                            {/* Row 3: Giao tu ai -> Ai nhan + Thoi gian bat dau / Han chot */}
                            <div className="flex flex-wrap gap-4 items-center pt-1 text-xs">
                              {it.ten_nguoi_giao && (
                                <div className="flex items-center gap-1 text-neutral-400 font-mono">
                                  <span>Giao từ:</span>
                                  <strong className="text-neutral-200">{it.ten_nguoi_giao}</strong>
                                  <span className="text-amber-400">➔</span>
                                </div>
                              )}
                              <div className="flex items-center gap-1.5">
                                <span className="font-mono text-neutral-400">Giao cho:</span>
                                <input
                                  type="text"
                                  style={inputStyle}
                                  value={it.ten_nguoi_nhan}
                                  onChange={(e) => updateActionAssignee(it.id, e.target.value)}
                                  className="text-xs py-0.5 px-2 w-32 font-bold text-neutral-100"
                                />
                              </div>

                              {it.thoi_gian_bat_dau && (
                                <div className="flex items-center gap-1 text-neutral-400 font-mono">
                                  <span>Bắt đầu:</span>
                                  <strong className="text-cyan-300">{it.thoi_gian_bat_dau}</strong>
                                </div>
                              )}

                              <div className="flex items-center gap-1.5">
                                <span className="font-mono text-neutral-400">Hạn chót:</span>
                                <input
                                  type="text"
                                  style={inputStyle}
                                  value={it.han_chot || ""}
                                  onChange={(e) => updateActionDue(it.id, e.target.value)}
                                  className="text-xs py-0.5 px-2 w-28 text-amber-300 font-bold"
                                />
                              </div>

                              <span
                                className={`text-[10px] font-mono px-1.5 py-0.5 rounded ml-auto ${
                                  it.do_tin_cay >= 0.9
                                    ? "bg-emerald-900/40 text-emerald-400"
                                    : it.do_tin_cay >= 0.75
                                    ? "bg-amber-900/40 text-amber-400"
                                    : "bg-red-900/40 text-red-400"
                                }`}
                              >
                                {Math.round(it.do_tin_cay * 100)}% tin cậy
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* SECTION 3: TEAM FEEDBACK & COACHING NOTES (Góp ý & Nhắc nhở nội bộ) */}
              {meeting.gop_y_luu_y && meeting.gop_y_luu_y.length > 0 && (
                <div className="space-y-3 p-4 bg-teal-950/20 rounded border border-teal-800/40">
                  <div className="flex justify-between items-center">
                    <h4 className="text-xs font-mono uppercase tracking-wider text-teal-300 font-bold flex items-center gap-2">
                      💬 Góp Ý, Nhắc Nhở & Lưu Ý Nội Bộ (Team Feedback & Reminders)
                    </h4>
                    <span className="text-xs font-mono px-2 py-0.5 bg-teal-900/60 text-teal-200 rounded">
                      {meeting.gop_y_luu_y.length} lưu ý
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {meeting.gop_y_luu_y.map((fb) => (
                      <div
                        key={fb.id}
                        className={`p-3 rounded border transition-all ${
                          fb.tinh_chat === "khen_ngoi"
                            ? "bg-emerald-950/20 border-emerald-700/40"
                            : fb.tinh_chat === "nhac_nho"
                            ? "bg-amber-950/20 border-amber-700/40"
                            : "bg-teal-950/20 border-teal-700/40"
                        }`}
                      >
                        <div className="flex items-start gap-2.5">
                          <span className="text-base shrink-0 mt-0.5">
                            {fb.tinh_chat === "khen_ngoi"
                              ? "🌟"
                              : fb.tinh_chat === "nhac_nho"
                              ? "🔔"
                              : fb.tinh_chat === "kinh_nghiem"
                              ? "💡"
                              : "💬"}
                          </span>
                          <div className="flex-1 min-w-0 space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span
                                className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded font-bold ${
                                  fb.tinh_chat === "khen_ngoi"
                                    ? "bg-emerald-900/70 text-emerald-200 border border-emerald-600"
                                    : fb.tinh_chat === "nhac_nho"
                                    ? "bg-amber-900/70 text-amber-200 border border-amber-600"
                                    : "bg-teal-900/70 text-teal-200 border border-teal-600"
                                }`}
                              >
                                {fb.tinh_chat === "khen_ngoi"
                                  ? "Khen ngợi / Động viên"
                                  : fb.tinh_chat === "nhac_nho"
                                  ? "Nhắc nhở nhẹ"
                                  : fb.tinh_chat === "kinh_nghiem"
                                  ? "Chia sẻ kinh nghiệm"
                                  : "Góp ý cải thiện"}
                              </span>

                              <span className="text-[10px] font-mono uppercase px-1.5 py-0.5 rounded bg-neutral-800 text-neutral-300">
                                {fb.chu_de === "thai_do_phuc_vu"
                                  ? "Thái độ phục vụ"
                                  : fb.chu_de === "ky_nang_pha_che"
                                  ? "Kỹ năng pha chế"
                                  : fb.chu_de === "ve_sinh_an_toan"
                                  ? "Vệ sinh & An toàn"
                                  : fb.chu_de === "dong_vien_khen_ngoi"
                                  ? "Động viên"
                                  : "Lưu ý chung"}
                              </span>

                              {fb.nguoi_gop_y && (
                                <span className="text-xs font-mono text-neutral-400">
                                  Từ: <strong className="text-neutral-200">{fb.nguoi_gop_y}</strong>
                                </span>
                              )}
                              {fb.nguoi_nhan && (
                                <span className="text-xs font-mono text-neutral-400">
                                  ➔ Gửi đến: <strong className="text-teal-300">{fb.nguoi_nhan}</strong>
                                </span>
                              )}
                            </div>

                            <p className="text-xs text-neutral-200 leading-relaxed pt-0.5">
                              {fb.noi_dung}
                            </p>

                            {fb.ghi_chu && (
                              <p className="text-[11px] text-neutral-400 italic">
                                Ghi chú: {fb.ghi_chu}
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* BLOCK C: MANAGER COACHING & SPEAKING DYNAMICS */}
              {meeting.huan_luyen_quan_ly && (
                <div className="space-y-3 p-4 bg-indigo-950/20 rounded border border-indigo-700/40">
                  <div className="flex flex-wrap justify-between items-center gap-2">
                    <div className="flex items-center gap-2.5">
                      <span className="text-xl">🎓</span>
                      <div>
                        <h4 className="text-xs font-mono uppercase tracking-wider text-indigo-300 font-bold">
                          Đào Tạo & Đánh Giá Năng Lực Quản Lý (Manager Coaching)
                        </h4>
                        <p className="text-[11px] text-neutral-400">
                          Phân tích tương tác 2 chiều, tỷ lệ nói và đề xuất huấn luyện kỹ năng lãnh đạo ca
                        </p>
                      </div>
                    </div>

                    <span className="text-xs font-mono font-bold px-2.5 py-1 rounded bg-indigo-900/60 text-indigo-200 border border-indigo-600">
                      Phong cách: {meeting.huan_luyen_quan_ly.phong_cach_dieu_hanh || "Chuẩn mực & Tương tác"}
                    </span>
                  </div>

                  {/* Row 1: Talk-to-Listen Ratio Bar */}
                  <div className="space-y-1.5 p-3 rounded bg-neutral-900/70 border border-neutral-800">
                    <div className="flex justify-between items-center text-xs font-mono">
                      <span className="text-indigo-300">
                        👤 Quản lý nói: <strong>{meeting.huan_luyen_quan_ly.ty_le_noi_quan_ly_pct}%</strong>
                      </span>
                      <span className="text-teal-300">
                        👥 Nhân viên phản hồi: <strong>{meeting.huan_luyen_quan_ly.ty_le_noi_nhan_vien_pct}%</strong>
                      </span>
                    </div>

                    {/* Visual 2-color Progress Bar */}
                    <div className="w-full h-3 bg-neutral-800 rounded-full overflow-hidden flex">
                      <div
                        style={{ width: `${meeting.huan_luyen_quan_ly.ty_le_noi_quan_ly_pct}%` }}
                        className="bg-indigo-600 h-full transition-all duration-500"
                        title={`Quản lý: ${meeting.huan_luyen_quan_ly.ty_le_noi_quan_ly_pct}%`}
                      />
                      <div
                        style={{ width: `${meeting.huan_luyen_quan_ly.ty_le_noi_nhan_vien_pct}%` }}
                        className="bg-teal-500 h-full transition-all duration-500"
                        title={`Nhân viên: ${meeting.huan_luyen_quan_ly.ty_le_noi_nhan_vien_pct}%`}
                      />
                    </div>

                    <p className="text-[11px] text-neutral-400 italic">
                      {meeting.huan_luyen_quan_ly.ty_le_noi_quan_ly_pct > 85
                        ? "⚠️ Quản lý đang nói quá nhiều (>85%), ca họp mang tính áp đặt 1 chiều. Cần đặt thêm câu hỏi cho nhân viên."
                        : meeting.huan_luyen_quan_ly.ty_le_noi_quan_ly_pct < 50
                        ? "⚠️ Quản lý nói ít (<50%), chưa đủ dẫn dắt và định hướng rõ ràng mục tiêu cho ca."
                        : "✅ Tỷ lệ giao tiếp cân bằng lý tưởng giữa giao việc và lắng nghe phản hồi của đội ngũ."}
                    </p>
                  </div>

                  {/* Row 2: Metrics Scores */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <div className="p-2.5 rounded bg-neutral-900/60 border border-neutral-800 flex items-center justify-between">
                      <div>
                        <p className="text-xs font-bold text-neutral-200">🗣️ Mức độ tương tác 2 chiều</p>
                        <p className="text-[11px] text-neutral-400">Khả năng hỏi han & lắng nghe ý kiến</p>
                      </div>
                      <span className="text-sm font-mono font-bold px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                        {meeting.huan_luyen_quan_ly.diem_tuong_tac_2_chieu}/10
                      </span>
                    </div>

                    <div className="p-2.5 rounded bg-neutral-900/60 border border-neutral-800 flex items-center justify-between">
                      <div>
                        <p className="text-xs font-bold text-neutral-200">🔥 Điểm truyền cảm hứng & Động viên</p>
                        <p className="text-[11px] text-neutral-400">Khen ngợi & tạo năng lượng tích cực</p>
                      </div>
                      <span className="text-sm font-mono font-bold px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                        {meeting.huan_luyen_quan_ly.diem_truyen_cam_hung}/10
                      </span>
                    </div>
                  </div>

                  {/* Row 3: AI Coaching Recommendations */}
                  {meeting.huan_luyen_quan_ly.loi_khuyen_ai_coaching && meeting.huan_luyen_quan_ly.loi_khuyen_ai_coaching.length > 0 && (
                    <div className="p-3 bg-neutral-900/80 rounded border border-indigo-800/40 space-y-1.5">
                      <p className="text-xs font-bold text-indigo-300 flex items-center gap-1">
                        <span>💡</span> LỜI KHUYÊN AI COACHING CHO CỬA HÀNG TRƯỞNG:
                      </p>
                      <ul className="space-y-1 text-xs text-neutral-300">
                        {meeting.huan_luyen_quan_ly.loi_khuyen_ai_coaching.map((tip, idx) => (
                          <li key={idx} className="flex items-start gap-1.5">
                            <span className="text-indigo-400 font-bold shrink-0">•</span>
                            <span>{tip}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* SOP Proposals (Legacy fallback if de_xuat_phe_duyet is not present) */}
              {(!meeting.de_xuat_phe_duyet || meeting.de_xuat_phe_duyet.length === 0) && meeting.de_xuat_sop && meeting.de_xuat_sop.length > 0 && (
                <div className="p-4 bg-purple-950/20 border border-purple-800/40 rounded space-y-2">
                  <h4 className="text-xs font-mono uppercase tracking-wider text-purple-300 font-bold">
                    📖 Đề xuất Sửa đổi Cẩm nang Vận hành (Playbook Patch)
                  </h4>
                  {meeting.de_xuat_sop.map((sop, idx) => (
                    <div key={idx} className="text-sm bg-neutral-900/80 p-3 rounded border border-neutral-800 space-y-1">
                      <p className="font-bold text-purple-200">
                        Quy trình: {sop.quy_trinh_lien_quan} {sop.buoc_so ? `(Bước ${sop.buoc_so})` : ""}
                      </p>
                      <p className="text-neutral-300">Nội dung sửa: {sop.noi_dung_thay_doi}</p>
                      {sop.ly_do && <p className="text-xs text-neutral-400 italic">Lý do: {sop.ly_do}</p>}
                    </div>
                  ))}
                </div>
              )}



              {/* Khong lien quan warning */}
              {meeting.khong_lien_quan && (
                <Alert kind="info">
                  ⚠️ Nội dung bản bóc băng không liên quan đến vận hành quán. AI đã tự động phát hiện và không tạo Action Items. Vui lòng kiểm tra lại nguồn âm thanh.
                </Alert>
              )}


              {/* Execution Bar */}
              <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-neutral-800">
                <div className="text-xs opacity-75">
                  Sau khi duyệt, việc cần làm sẽ tự động đẩy vào <strong>OpsEngine (Việc treo ca)</strong> và đề xuất Cẩm nang sẽ được ghi vào <strong>Playbook</strong>.
                </div>
                <Btn variant="primary" onClick={applyDecisions} disabled={busy || !manager}>
                  ✨ {manager ? "Duyệt & Phân công vào Ca" : "Cần quyền Quản lý để duyệt"}
                </Btn>
              </div>
            </div>
          </OpsCard>
        </div>
      )}


      {/* 3. PAST MEETINGS HISTORY */}
      {pastMeetings.length > 0 && (
        <OpsCard title="3. Lịch sử Cuộc họp & Giao ca đã duyệt">
          <div className="space-y-3">
            {pastMeetings.map((m) => (
              <div
                key={m.id}
                className="p-3 bg-neutral-900/60 rounded border border-neutral-800 flex items-center justify-between gap-4 hover:border-neutral-700 transition-colors"
              >
                <div>
                  <h4 className="font-bold text-sm text-neutral-200">{m.tieu_de}</h4>
                  <p className="text-xs text-neutral-400 line-clamp-1">{m.tom_tat}</p>
                  <div className="flex gap-3 text-[11px] font-mono text-neutral-500 mt-1">
                    <span>Loại: {m.loai_hop}</span>
                    <span>Việc: {m.action_items?.length || 0}</span>
                    <span>Nguồn: {m.nguon_am_thanh}</span>
                  </div>
                </div>
                <Btn
                  variant="ghost"
                  onClick={() => {
                    setMeeting(m);
                    window.scrollTo({ top: 400, behavior: "smooth" });
                  }}
                >
                  Xem lại
                </Btn>
              </div>
            ))}
          </div>
        </OpsCard>
      )}
    </div>
  );
}
