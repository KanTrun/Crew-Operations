"use client";

import React, { useEffect, useRef, useState } from "react";
import { Icon } from "../icons";

interface VoiceRecorderProps {
  onSendVoice: (audioBlob: Blob, durationSec: number) => Promise<void>;
  onCancel?: () => void;
  disabled?: boolean;
}

export function VoiceRecorder({ onSendVoice, onCancel, disabled }: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const [isSending, setIsSending] = useState(false);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const mimeTypeRef = useRef("audio/webm");
  const durationRef = useRef(0);

  const startRecording = async () => {
    if (disabled || isRecording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const supportedMimeType = ["audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4", "audio/webm"]
        .find((mimeType) => MediaRecorder.isTypeSupported(mimeType));
      if (!supportedMimeType) {
        stream.getTracks().forEach((track) => track.stop());
        throw new Error("Trình duyệt không hỗ trợ ghi âm.");
      }
      mimeTypeRef.current = supportedMimeType;
      const mediaRecorder = new MediaRecorder(stream, { mimeType: supportedMimeType });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      mediaRecorder.start(100);
      setIsRecording(true);
      setDuration(0);
      durationRef.current = 0;

      timerRef.current = setInterval(() => {
        setDuration((prev) => {
          const nextDuration = prev + 1;
          durationRef.current = nextDuration;
          if (nextDuration >= 180) {
            stopAndSend();
            return 180;
          }
          return nextDuration;
        });
      }, 1000);
    } catch {
      alert("Không thể ghi âm trên trình duyệt này. Vui lòng cấp quyền microphone hoặc dùng trình duyệt khác.");
    }
  };

  const cleanup = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setIsRecording(false);
    setDuration(0);
    durationRef.current = 0;
    mediaRecorderRef.current = null;
    audioChunksRef.current = [];
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
    cleanup();
    if (onCancel) onCancel();
  };

  const stopAndSend = () => {
    const mediaRecorder = mediaRecorderRef.current;
    if (!mediaRecorder || mediaRecorder.state !== "recording") return;

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: mimeTypeRef.current });
      setIsSending(true);
      try {
        await onSendVoice(audioBlob, durationRef.current);
      } finally {
        setIsSending(false);
        cleanup();
      }
    };
    mediaRecorder.stop();
  };

  useEffect(() => {
    return () => {
      if (mediaRecorderRef.current?.state === "recording") mediaRecorderRef.current.stop();
      cleanup();
    };
  }, []);

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  if (isRecording) {
    return (
      <div className="flex items-center gap-3 bg-[var(--nq-card)] border border-[var(--nq-copper)] px-3 py-1.5 rounded-full animate-pulse shadow-sm">
        <span className="w-3 h-3 rounded-full bg-red-500 animate-ping" />
        <span className="font-mono text-xs font-bold text-red-500">{formatTime(duration)}</span>
        <div className="flex items-center gap-1 h-4">
          <span className="w-1 h-2 bg-red-400 rounded animate-bounce" />
          <span className="w-1 h-4 bg-red-500 rounded animate-bounce delay-75" />
          <span className="w-1 h-3 bg-red-400 rounded animate-bounce delay-150" />
        </div>
        <button
          type="button"
          onClick={cancelRecording}
          disabled={isSending}
          className="text-xs text-[var(--nq-muted)] hover:text-red-500 px-2 py-0.5 rounded transition"
          title="Hủy ghi âm"
        >
          <Icon name="close" size={14} /> Hủy
        </button>
        <button
          type="button"
          onClick={stopAndSend}
          disabled={isSending}
          className="text-xs bg-[var(--nq-copper)] text-white px-3 py-1 rounded-full font-bold shadow hover:opacity-90 transition"
        >
          {isSending ? "Đang gửi…" : <><Icon name="send" size={14} /> Gửi</>}
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={startRecording}
      disabled={disabled}
      title="Ghi âm tin nhắn thoại"
      className="p-2 text-[var(--nq-muted)] hover:text-[var(--nq-copper)] hover:bg-[var(--nq-card)] rounded-full transition"
    >
      <Icon name="microphone" size={20} />
    </button>
  );
}

export function VoicePlayer({ url, durationSec }: { url: string; durationSec?: number }) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const togglePlay = () => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
      return;
    }
    void audioRef.current.play().then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
  };

  const handleTimeUpdate = () => {
    if (!audioRef.current) return;
    const current = audioRef.current.currentTime;
    const total = audioRef.current.duration || durationSec || 1;
    setProgress((current / total) * 100);
  };

  const handleEnded = () => {
    setIsPlaying(false);
    setProgress(0);
  };

  return (
    <div className="flex items-center gap-2.5 py-1 px-2 rounded-lg bg-black/10 dark:bg-white/10 min-w-[160px]">
      <audio
        ref={audioRef}
        src={url}
        onTimeUpdate={handleTimeUpdate}
        onEnded={handleEnded}
        preload="metadata"
      />
      <button
        type="button"
        onClick={togglePlay}
        className="w-8 h-8 flex items-center justify-center rounded-full bg-[var(--nq-copper)] text-white hover:opacity-90 transition shrink-0"
      >
        <Icon name={isPlaying ? "pause" : "play"} size={16} />
      </button>
      <div className="flex-1 flex flex-col justify-center gap-1">
        <div className="w-full bg-black/20 dark:bg-white/20 h-1.5 rounded-full overflow-hidden">
          <div
            className="bg-[var(--nq-copper)] h-full transition-all duration-100"
            style={{ width: `${progress}%` }}
          />
        </div>
        <div className="flex justify-between text-[10px] opacity-75 font-mono">
          <span>{isPlaying ? "Đang phát" : "Voice note"}</span>
          <span>{durationSec ? `${Math.floor(durationSec / 60)}:${durationSec % 60 < 10 ? "0" : ""}${durationSec % 60}` : "0:00"}</span>
        </div>
      </div>
    </div>
  );
}
