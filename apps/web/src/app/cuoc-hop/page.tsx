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
  TabBar,
  TabButton,
  Textarea,
} from "../../ui/kit";
import { MeetingResults } from "./MeetingResults";

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
    <div className="nq-page nq-page--wide space-y-6">
      <PageHeader
        kicker="AI MEETING OS"
        title="Cuộc họp & Giao ca Thông minh"
        meta="Tự động bóc băng Google Meet / Giao ca với Gemini 3.5 Transcribe · Trích xuất việc cần làm · Đề xuất Cẩm nang."
      />

      {error && <Alert kind="err">{error}</Alert>}
      {success && <Alert kind="ok">{success}</Alert>}

      {/* 1. INPUT HUB */}
      <OpsCard title="Thu thập cuộc họp">
        <div className="space-y-4">
          <TabBar>
            <TabButton active={inputMode === "mic"} onClick={() => { setInputMode("mic"); setError(null); }}>
              Micro giao ca
            </TabButton>
            <TabButton active={inputMode === "meet"} onClick={() => { setInputMode("meet"); setError(null); }}>
              Google Meet
            </TabButton>
            <TabButton active={inputMode === "upload"} onClick={() => { setInputMode("upload"); setError(null); }}>
              Tải audio
            </TabButton>
            <TabButton active={inputMode === "text"} onClick={() => { setInputMode("text"); setError(null); }}>
              Dán ghi chép
            </TabButton>
          </TabBar>

          <div className="flex flex-wrap items-center gap-2 justify-end">
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

          {/* Mode 1: Microphone Live Recording */}
          {inputMode === "mic" && (
            <div className={`nq-meeting-input ${isRecording ? "nq-meeting-input--live" : ""} space-y-3`}>
              <div className="text-sm">
                <p className="font-bold">Ghi âm trực tiếp tại quầy</p>
                <p className="nq-muted mt-1 text-sm">
                  Bấm bắt đầu và nói tự nhiên. Lời nói chuyển thành văn bản thời gian thực trên màn hình.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-4 pt-2">
                {!isRecording ? (
                  <Btn variant="primary" onClick={startMicRecording} disabled={busy}>
                    Bắt đầu ghi âm giao ca
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
                      Hoàn tất & trích xuất
                    </Btn>
                  </div>
                )}
              </div>

              {/* Live Speech Recognition Subtitle Box */}
              {isRecording && (
                <div className="nq-meeting-live space-y-1">
                  <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-widest text-[var(--nq-copper)]">
                    <span className="h-2 w-2 rounded-full bg-[var(--nq-copper)]" />
                    Văn bản đang nói trực tiếp
                  </div>
                  <p className="min-h-[2.5rem] text-sm italic">
                    {liveTranscript} <span className="text-[var(--nq-copper)] underline">{interimText}</span>
                    {!liveTranscript && !interimText && "Đang lắng nghe giọng nói qua micro…"}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Mode 2: Google Meet Tab Audio Capture */}
          {inputMode === "meet" && (
            <div className={`nq-meeting-input ${isRecording ? "nq-meeting-input--live" : ""} space-y-3`}>
              <div className="text-sm">
                <p className="font-bold">Bắt âm thanh từ tab Google Meet</p>
                <p className="nq-muted mt-1 text-sm">
                  Khi bắt đầu, chọn tab <strong>Google Meet</strong> và tích{" "}
                  <strong>Chia sẻ âm thanh thẻ</strong>. Hệ thống gộp âm thanh phòng họp và giọng của bạn.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-4 pt-2">
                {!isRecording ? (
                  <Btn variant="primary" onClick={startMeetCapture} disabled={busy}>
                    Bắt đầu theo dõi Google Meet
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
                      Dừng & phân tích AI
                    </Btn>
                  </div>
                )}
              </div>

              {isRecording && (
                <div className="nq-meeting-live space-y-1">
                  <div className="flex items-center gap-2 text-xs font-mono font-bold uppercase tracking-widest text-[var(--nq-copper)]">
                    <span className="h-2 w-2 rounded-full bg-[var(--nq-copper)]" />
                    Văn bản thu từ cuộc họp
                  </div>
                  <p className="min-h-[2.5rem] text-sm italic">
                    {liveTranscript} <span className="text-[var(--nq-copper)] underline">{interimText}</span>
                    {!liveTranscript && !interimText && "Đang lắng nghe âm thanh từ Google Meet…"}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Mode 3: File Upload */}
          {inputMode === "upload" && (
            <div className="nq-meeting-input space-y-3">
              <Field label="Chọn file âm thanh (.mp3, .m4a, .wav, .webm)">
                <input
                  type="file"
                  accept="audio/*,.mp3,.m4a,.wav,.webm"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="text-sm text-neutral-300 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-copper file:text-white hover:file:opacity-90"
                />
              </Field>
              <Btn variant="primary" onClick={uploadFile} disabled={busy || !selectedFile}>
                Tải lên & phân tích
              </Btn>
            </div>
          )}

          {/* Mode 4: Text Input */}
          {inputMode === "text" && (
            <div className="nq-meeting-input space-y-4">
              <Field label="Nội dung ghi chép cuộc họp" hint="Dán biên bản hoặc nội dung trao đổi. Mỗi dòng nên ghi rõ người nói.">
                <Textarea
                  rows={10}
                  value={rawText}
                  onChange={(e) => setRawText(e.target.value)}
                  placeholder={"Quản lý: …\nNhân viên: …"}
                />
              </Field>
              <Btn variant="primary" onClick={analyzeText} disabled={busy}>
                Phân tích biên bản
              </Btn>
            </div>
          )}

          {busy && (
            <div className="nq-meeting-input flex items-center gap-3">
              <Loading />
              <span className="text-sm font-mono text-[var(--nq-ink-muted)]">{statusMsg || "Đang xử lý…"}</span>
            </div>
          )}
        </div>
      </OpsCard>

      {/* 2. RESULTS */}
      {meeting ? (
        <OpsCard title={`Kết quả phân tích: ${meeting.tieu_de}`}>
          <MeetingResults
            meeting={meeting}
            liveTranscript={liveTranscript}
            manager={manager}
            busy={busy}
            copiedBroadcast={copiedBroadcast}
            onCopyBroadcast={handleCopyBroadcast}
            onToggleAction={toggleActionItem}
            onUpdateAssignee={updateActionAssignee}
            onUpdateDue={updateActionDue}
            onApply={applyDecisions}
          />
        </OpsCard>
      ) : null}

      {/* 3. PAST MEETINGS HISTORY */}
      {pastMeetings.length > 0 && (
        <OpsCard title="Lịch sử cuộc họp đã duyệt">
          <div className="nq-meeting-list">
            {pastMeetings.map((m) => (
              <div key={m.id} className="nq-meeting-list__item flex items-center justify-between gap-4">
                <div>
                  <h4 className="nq-meeting-list__title">{m.tieu_de}</h4>
                  <p className="nq-meeting-list__meta line-clamp-1">{m.tom_tat}</p>
                  <div className="mt-1 flex flex-wrap gap-3 text-[11px] font-mono text-[var(--nq-ink-muted)]">
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
