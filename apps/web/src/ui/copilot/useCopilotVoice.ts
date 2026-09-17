"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getToken } from "../../lib/session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const INPUT_RATE = 16000;
const OUTPUT_RATE = 24000;

export type VoiceState = "idle" | "connecting" | "listening" | "processing" | "speaking" | "error";

function voiceUrl(): string {
  return `${API_BASE.replace(/^http/, "ws")}/api/v1/copilot/voice`;
}

function pcm16AtRate(input: Float32Array, sourceRate: number, targetRate: number): ArrayBuffer {
  const ratio = sourceRate / targetRate;
  const length = Math.max(1, Math.round(input.length / ratio));
  const output = new ArrayBuffer(length * 2);
  const view = new DataView(output);
  for (let index = 0; index < length; index += 1) {
    const sourceIndex = Math.min(input.length - 1, Math.floor(index * ratio));
    const sample = Math.max(-1, Math.min(1, input[sourceIndex] ?? 0));
    view.setInt16(index * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
  }
  return output;
}

function playPcm16(
  data: string,
  context: AudioContext,
  nextTime: { value: number },
  sources: Set<AudioBufferSourceNode>,
  onQueueEnded: () => void,
): void {
  const binary = atob(data);
  const samples = new Int16Array(binary.length / 2);
  for (let index = 0; index < samples.length; index += 1) {
    samples[index] = (binary.charCodeAt(index * 2) | (binary.charCodeAt(index * 2 + 1) << 8));
  }
  const buffer = context.createBuffer(1, samples.length, OUTPUT_RATE);
  const channel = buffer.getChannelData(0);
  for (let index = 0; index < samples.length; index += 1) channel[index] = samples[index] / 0x8000;
  const source = context.createBufferSource();
  source.buffer = buffer;
  source.connect(context.destination);
  sources.add(source);
  source.onended = () => {
    sources.delete(source);
    if (sources.size === 0) onQueueEnded();
  };
  nextTime.value = Math.max(nextTime.value, context.currentTime);
  source.start(nextTime.value);
  nextTime.value += buffer.duration;
}

export function useCopilotVoice() {
  const [state, setState] = useState<VoiceState>("idle");
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const outputContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const nextOutputTimeRef = useRef({ value: 0 });
  const outputSourcesRef = useRef(new Set<AudioBufferSourceNode>());
  const turnCompleteRef = useRef(false);
  const failedRef = useRef(false);

  const stop = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.onclose = null;
      socketRef.current.onmessage = null;
      socketRef.current.onerror = null;
      socketRef.current.onopen = null;
    }
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ event: "stop" }));
    }
    socketRef.current?.close();
    socketRef.current = null;
    processorRef.current?.disconnect();
    processorRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    for (const source of outputSourcesRef.current) source.stop();
    outputSourcesRef.current.clear();
    turnCompleteRef.current = false;
    nextOutputTimeRef.current.value = 0;
    void inputContextRef.current?.close();
    void outputContextRef.current?.close();
    inputContextRef.current = null;
    outputContextRef.current = null;
    setState("idle");
  }, []);

  const start = useCallback(async () => {
    if (state !== "idle" && state !== "error") return;
    const token = getToken();
    if (!token) {
      setState("error");
      return;
    }
    failedRef.current = false;
    setState("connecting");
    try {
      const socket = new WebSocket(voiceUrl());
      socket.binaryType = "arraybuffer";
      socketRef.current = socket;
      const inputContext = new AudioContext();
      const outputContext = new AudioContext();
      inputContextRef.current = inputContext;
      outputContextRef.current = outputContext;
      await new Promise<void>((resolve, reject) => {
        let ready = false;
        const fail = (reason: string) => {
          if (!ready) {
            reject(new Error(reason));
          } else {
            failedRef.current = true;
            stop();
            setState("error");
          }
        };
        socket.onopen = () => {
          socket.send(JSON.stringify({ event: "auth", token }));
        };
        socket.onmessage = (message) => {
          let payload: { event?: string; data?: any };
          try {
            payload = JSON.parse(String(message.data)) as { event?: string; data?: any };
          } catch {
            fail("voice_invalid_response");
            return;
          }
          if (payload.event === "voice:ready") {
            ready = true;
            setState("listening");
            resolve();
          } else if (payload.event === "voice:error") {
            fail(payload.data?.code || "voice_error");
          } else if (payload.event === "voice:upstream") {
            const event = payload.data || {};
            const serverContent = event.serverContent || {};
            if (serverContent.interrupted === true) {
              for (const source of outputSourcesRef.current) source.stop();
              outputSourcesRef.current.clear();
              nextOutputTimeRef.current.value = outputContext.currentTime;
              turnCompleteRef.current = false;
              setState("listening");
              return;
            }
            const status =
              serverContent.interactionStatus ||
              serverContent.interaction_status ||
              event.interactionStatus ||
              event.interaction_status;
            if (
              status === "thinking" ||
              status === "processing" ||
              status === "in_progress" ||
              status === "IN_PROGRESS"
            ) {
              turnCompleteRef.current = false;
              setState("processing");
            }
            if (serverContent.turnComplete === true) {
              turnCompleteRef.current = true;
              if (outputSourcesRef.current.size === 0) setState("listening");
            }
            const parts = serverContent.modelTurn?.parts || [];
            for (const part of parts) {
              const audio = part.inlineData?.data || part.inline_data?.data;
              if (audio) {
                setState("speaking");
                playPcm16(
                  audio,
                  outputContext,
                  nextOutputTimeRef.current,
                  outputSourcesRef.current,
                  () => {
                    if (turnCompleteRef.current) setState("listening");
                  },
                );
              }
            }
          }
        };
        socket.onerror = () => fail("voice_connection_failed");
        socket.onclose = () => {
          if (!ready) {
            reject(new Error("voice_connection_closed"));
          } else if (!failedRef.current) {
            stop();
          }
        };
      });

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      if (socketRef.current !== socket || socket.readyState !== WebSocket.OPEN) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      await Promise.all([inputContext.resume(), outputContext.resume()]);
      const source = inputContext.createMediaStreamSource(stream);
      const processor = inputContext.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(pcm16AtRate(event.inputBuffer.getChannelData(0), inputContext.sampleRate, INPUT_RATE));
        }
      };
      source.connect(processor);
      processor.connect(inputContext.destination);
      processorRef.current = processor;
    } catch {
      failedRef.current = true;
      stop();
      setState("error");
    }
  }, [state, stop]);

  useEffect(() => stop, [stop]);

  return { state, start, stop };
}
