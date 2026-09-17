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

export type VoiceInputMode = "open_mic" | "push_to_talk";

export interface MicDeviceInfo {
  deviceId: string;
  label: string;
}

export interface UseCopilotVoiceOptions {
  onTranscript?: (role: "user" | "copilot", text: string, isFinal: boolean) => void;
  onInterrupted?: () => void;
  inputMode?: VoiceInputMode;
  deviceId?: string;
  noiseFloor?: number;
}

export const DEFAULT_NOISE_FLOOR = 0.01;

function voiceUrl(): string {
  return `${API_BASE.replace(/^http/, "ws")}/api/v1/copilot/voice`;
}

function rms(frame: Float32Array): number {
  let sum = 0;
  for (let i = 0; i < frame.length; i += 1) {
    sum += frame[i] * frame[i];
  }
  return Math.sqrt(sum / frame.length);
}

async function acquireMicStream(deviceId?: string): Promise<MediaStream> {
  const baseConstraints: MediaTrackConstraints = {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    channelCount: 1,
    sampleRate: 16000,
    ...(deviceId ? { deviceId: { exact: deviceId } } : {}),
  };

  const chromeExtraConstraints = {
    ...baseConstraints,
    googNoiseSuppression: true,
    googHighpassFilter: true, // Cut AC hum, fan rumble
    googEchoCancellation: true,
  } as MediaTrackConstraints;

  try {
    return await navigator.mediaDevices.getUserMedia({ audio: chromeExtraConstraints });
  } catch {
    return await navigator.mediaDevices.getUserMedia({ audio: baseConstraints });
  }
}

async function enumerateMics(): Promise<MicDeviceInfo[]> {
  if (typeof navigator === "undefined" || !navigator.mediaDevices?.enumerateDevices) {
    return [];
  }
  try {
    const devices = await navigator.mediaDevices.enumerateDevices();
    return devices
      .filter((d) => d.kind === "audioinput")
      .map((d, index) => ({
        deviceId: d.deviceId,
        label: d.label || `Microphone ${index + 1}`,
      }));
  } catch {
    return [];
  }
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
  const inputModeRef = useRef<VoiceInputMode>(options?.inputMode || "open_mic");
  inputModeRef.current = options?.inputMode || "open_mic";
  const deviceIdRef = useRef<string | undefined>(options?.deviceId);
  deviceIdRef.current = options?.deviceId;
  const noiseFloorRef = useRef<number>(options?.noiseFloor ?? DEFAULT_NOISE_FLOOR);
  noiseFloorRef.current = options?.noiseFloor ?? DEFAULT_NOISE_FLOOR;
  const isPttSpeakingRef = useRef(false);
  const [availableMics, setAvailableMics] = useState<MicDeviceInfo[]>([]);
  const [isPttSpeaking, setIsPttSpeaking] = useState(false);

  useEffect(() => {
    void enumerateMics().then((mics) => {
      if (mics.length > 0) setAvailableMics(mics);
    });
  }, []);

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
    isPttSpeakingRef.current = false;
    setIsPttSpeaking(false);
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

      const stream = await acquireMicStream(deviceIdRef.current);
      void enumerateMics().then((mics) => {
        if (mics.length > 0) setAvailableMics(mics);
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
        if (socket.readyState !== WebSocket.OPEN || tabHiddenRef.current) {
          return;
        }
        // In push_to_talk mode, only stream audio when user is actively holding the button
        if (inputModeRef.current === "push_to_talk" && !isPttSpeakingRef.current) {
          return;
        }
        const channelData = event.inputBuffer.getChannelData(0);
        // Noise gate: skip near-silent / background hum frames
        if (rms(channelData) < noiseFloorRef.current) {
          return;
        }
        socket.send(pcm16AtRate(channelData, inputContext.sampleRate, INPUT_RATE));
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

  const startPttTalk = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      isPttSpeakingRef.current = true;
      setIsPttSpeaking(true);
      socketRef.current.send(JSON.stringify({ event: "activity_start" }));
    }
  }, []);

  const stopPttTalk = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      isPttSpeakingRef.current = false;
      setIsPttSpeaking(false);
      socketRef.current.send(JSON.stringify({ event: "activity_end" }));
    }
  }, []);

  const changeMic = useCallback(async (newDeviceId: string) => {
    deviceIdRef.current = newDeviceId;
    if (streamRef.current && inputContextRef.current && processorRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      try {
        const newStream = await acquireMicStream(newDeviceId);
        streamRef.current = newStream;
        const newSource = inputContextRef.current.createMediaStreamSource(newStream);
        newSource.connect(processorRef.current);
      } catch {
        // Leave existing if failed
      }
    }
  }, []);

  useEffect(() => stop, [stop]);

  return {
    state,
    start,
    stop,
    startPttTalk,
    stopPttTalk,
    isPttSpeaking,
    availableMics,
    changeMic,
  };
}
