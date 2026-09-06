"use client";

import React, { useEffect, useRef, useState } from "react";

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

  const startRecording = async () => {
    if (disabled || isRecording) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
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

      timerRef.current = setInterval(() => {
        setDuration((prev) => {
          // Giới hạn tối đa 3 phút (180s)
          if (prev >= 180) {
            stopAndSend();
            return prev;
          }
          return prev + 1;
        });
      }, 1000);
    } catch {
      alert("Không thể truy cập microphone. Vui lòng cấp quyền trong trình duyệt.");
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
  };

  const cancelRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
    }
    cleanup();
    if (onCancel) onCancel();
  };

  const stopAndSend = () => {
    if (!mediaRecorderRef.current || !isRecording) return;

    mediaRecorderRef.current.onstop = async () => {
      const audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
      setIsSending(true);
      try {
        await onSendVoice(audioBlob, duration);
      } finally {
        setIsSending(false);
        cleanup();
      }
    };
    mediaRecorderRef.current.stop();
  };

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
          ✕ Hủy
        </button>
        <button
          type="button"
          onClick={stopAndSend}
          disabled={isSending}
          className="text-xs bg-[var(--nq-copper)] text-white px-3 py-1 rounded-full font-bold shadow hover:opacity-90 transition"
        >
          {isSending ? "Đang gửi…" : "Gửi ➤"}
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
      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
        />
      </svg>
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
    } else {
      audioRef.current.play();
    }
    setIsPlaying(!isPlaying);
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
        {isPlaying ? (
          <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
            <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
          </svg>
        ) : (
          <svg className="w-4 h-4 fill-current translate-x-0.5" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        )}
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
