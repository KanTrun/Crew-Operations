"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getToken } from "../../lib/session";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const INPUT_RATE = 16000;
const OUTPUT_RATE = 24000;

export type VoiceState =
  | "idle"
  | "connecting"
  | "listening"
  | "processing"
  | "speaking"
  | "error"
  | "mic_denied"
  | "mic_not_found"
  | "superseded"
  | "idle_timeout";

export interface UseCopilotVoiceOptions {
  onTranscript?: (role: "user" | "copilot", text: string, isFinal: boolean) => void;
  onInterrupted?: () => void;
}

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

export function useCopilotVoice(options?: UseCopilotVoiceOptions) {
  const [state, setState] = useState<VoiceState>("idle");
  const optionsRef = useRef(options);
  optionsRef.current = options;
  const socketRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inputContextRef = useRef<AudioContext | null>(null);
  const outputContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const nextOutputTimeRef = useRef({ value: 0 });
  const outputSourcesRef = useRef(new Set<AudioBufferSourceNode>());
  const turnCompleteRef = useRef(false);
  const failedRef = useRef(false);
  const userStoppedRef = useRef(false);
  const tabHiddenRef = useRef(false);

  // Pause audio sending when tab is hidden for > 15s to save quota
  useEffect(() => {
    let hideTimer: ReturnType<typeof setTimeout> | null = null;
    const handleVisibilityChange = () => {
      if (document.hidden) {
        hideTimer = setTimeout(() => {
          tabHiddenRef.current = true;
        }, 15000);
      } else {
        if (hideTimer) clearTimeout(hideTimer);
        tabHiddenRef.current = false;
      }
    };
    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () => {
      if (hideTimer) clearTimeout(hideTimer);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  const stop = useCallback(() => {
    userStoppedRef.current = true;
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
    if (
      state !== "idle" &&
      state !== "error" &&
      state !== "mic_denied" &&
      state !== "mic_not_found" &&
      state !== "superseded" &&
      state !== "idle_timeout"
    ) {
      return;
    }
    const token = getToken();
    if (!token) {
      setState("error");
      return;
    }
    userStoppedRef.current = false;
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
          } else if (payload.event === "voice:ended") {
            if (payload.data?.code === "max_duration_reached") {
              stop();
            }
          } else if (payload.event === "voice:upstream") {
            const event = payload.data || {};
            const serverContent = event.serverContent || {};
            if (serverContent.interrupted === true) {
              for (const source of outputSourcesRef.current) source.stop();
              outputSourcesRef.current.clear();
              nextOutputTimeRef.current.value = outputContext.currentTime;
              turnCompleteRef.current = false;
              setState("listening");
              optionsRef.current?.onInterrupted?.();
              return;
            }

            const isTurnComplete = Boolean(serverContent.turnComplete);

            // User speech transcript from Gemini Live
            const inputTranscription = serverContent.inputAudioTranscription?.text;
            if (inputTranscription && optionsRef.current?.onTranscript) {
              optionsRef.current.onTranscript("user", inputTranscription, isTurnComplete);
            }

            // Assistant speech transcript
            const outputTranscription = serverContent.outputAudioTranscription?.text;
            if (outputTranscription && optionsRef.current?.onTranscript) {
              optionsRef.current.onTranscript("copilot", outputTranscription, isTurnComplete);
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
              if (part.text && !outputTranscription && optionsRef.current?.onTranscript) {
                optionsRef.current.onTranscript("copilot", part.text, isTurnComplete);
              }
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
        socket.onclose = (ev) => {
          if (userStoppedRef.current) {
            setState("idle");
          } else if (ev.code === 4002) {
            setState("superseded");
          } else if (ev.code === 4005) {
            setState("idle_timeout");
          } else if (!ready) {
            reject(new Error("voice_connection_closed"));
          } else if (!failedRef.current) {
            stop();
          }
        };
      });

      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 16000,
        },
      });
      if (socketRef.current !== socket || socket.readyState !== WebSocket.OPEN) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      await Promise.all([inputContext.resume(), outputContext.resume()]);
      const source = inputContext.createMediaStreamSource(stream);
      const processor = inputContext.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        if (socket.readyState === WebSocket.OPEN && !tabHiddenRef.current) {
          socket.send(pcm16AtRate(event.inputBuffer.getChannelData(0), inputContext.sampleRate, INPUT_RATE));
        }
      };
      source.connect(processor);
      // Mute node to prevent microphone feedback loop back into speakers
      const muteNode = inputContext.createGain();
      muteNode.gain.value = 0;
      processor.connect(muteNode);
      muteNode.connect(inputContext.destination);
      processorRef.current = processor;
    } catch (err: any) {
      if (userStoppedRef.current) return;
      failedRef.current = true;
      stop();
      if (err instanceof DOMException && err.name === "NotAllowedError") {
        setState("mic_denied");
      } else if (err instanceof DOMException && err.name === "NotFoundError") {
        setState("mic_not_found");
      } else {
        setState("error");
      }
    }
  }, [state, stop]);

  useEffect(() => stop, [stop]);

  return { state, start, stop };
}
