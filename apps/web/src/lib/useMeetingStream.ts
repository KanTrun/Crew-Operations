"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API } from "./api";
import { getToken } from "./session";

type TranscriptListener = (text: string, isFinal: boolean) => void;

/**
 * Hook quản lý WebSocket streaming cuộc họp realtime.
 * Gửi audio chunk PCM16 16kHz lên server → nhận transcript realtime.
 */
export function useMeetingStream() {
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const listenersRef = useRef<Set<TranscriptListener>>(new Set());

  const onTranscript = useCallback((listener: TranscriptListener) => {
    listenersRef.current.add(listener);
    return () => {
      listenersRef.current.delete(listener);
    };
  }, []);

  const connect = useCallback(() => {
    if (typeof window === "undefined") return;
    const token = getToken();
    if (!token) {
      setError("Chưa đăng nhập");
      return;
    }
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) return;

    const websocketApi = API.replace(/\/$/, "").replace(/^https:/, "wss:").replace(/^http:/, "ws:");
    const socket = new WebSocket(`${websocketApi}/api/v1/meeting/stream`);
    socketRef.current = socket;

    socket.onopen = () => {
      socket.send(JSON.stringify({ event: "auth", token }));
    };
    socket.onmessage = (event) => {
      try {
        const packet = JSON.parse(event.data);
        if (packet.event === "ready") {
          setConnected(true);
          setError(null);
        } else if (packet.event === "transcript") {
          const text = packet.data?.text || "";
          const isFinal = !!packet.data?.isFinal;
          for (const listener of listenersRef.current) {
            listener(text, isFinal);
          }
        } else if (packet.event === "error") {
          setError(packet.data?.code || "stream_error");
          setConnected(false);
        }
      } catch {
        // ignore malformed
      }
    };
    socket.onclose = () => {
      setConnected(false);
      socketRef.current = null;
    };
    socket.onerror = () => {
      setError("stream_connection_error");
    };
  }, []);

  const sendAudio = useCallback((pcm16: ArrayBuffer) => {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(pcm16);
    }
  }, []);

  const stop = useCallback(() => {
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ event: "stop" }));
      socket.close();
    }
    socketRef.current = null;
    setConnected(false);
  }, []);

  useEffect(() => {
    return () => {
      const socket = socketRef.current;
      if (socket) socket.close();
      socketRef.current = null;
    };
  }, []);

  return { connected, error, connect, sendAudio, stop, onTranscript };
}