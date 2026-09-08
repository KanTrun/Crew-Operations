"use client";

import { API } from "./api";
import { getToken } from "./session";

type Packet = { event?: string; data?: any };
type Listener = (packet: Packet) => void;

let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let backoff = 1000;
let connected = false;
const listeners = new Set<Listener>();
const statusListeners = new Set<(value: boolean) => void>();

function notifyStatus(value: boolean) {
  connected = value;
  for (const listener of statusListeners) listener(value);
}

function scheduleReconnect() {
  if (reconnectTimer || listeners.size === 0) return;
  const delay = Math.min(backoff, 10000);
  backoff = Math.min(backoff * 1.5, 10000);
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, delay);
}

function connect() {
  if (typeof window === "undefined" || !getToken()) return;
  if (socket && (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING)) return;

  const websocketApi = API.replace(/\/$/, "").replace(/^https:/, "wss:").replace(/^http:/, "ws:");
  socket = new WebSocket(`${websocketApi}/ws/chat`);
  socket.onopen = () => {
    const token = getToken();
    if (!token) {
      socket?.close();
      return;
    }
    socket?.send(JSON.stringify({ event: "auth", token }));
  };
  socket.onmessage = (event) => {
    try {
      const packet = JSON.parse(event.data) as Packet;
      if (packet.event === "auth:ack") {
        backoff = 1000;
        notifyStatus(true);
      }
      if (packet.event === "ops:changed" && typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("nq:ops-changed", { detail: packet.data }));
      }
      for (const listener of listeners) listener(packet);
    } catch {
      // Ignore malformed server packets.
    }
  };
  socket.onerror = () => socket?.close();
  socket.onclose = () => {
    socket = null;
    notifyStatus(false);
    scheduleReconnect();
  };
}

export function subscribeRealtime(listener: Listener, onStatus?: (value: boolean) => void) {
  listeners.add(listener);
  if (onStatus) {
    statusListeners.add(onStatus);
    onStatus(connected);
  }
  connect();
  return () => {
    listeners.delete(listener);
    if (onStatus) statusListeners.delete(onStatus);
    if (listeners.size === 0) {
      if (reconnectTimer) clearTimeout(reconnectTimer);
      reconnectTimer = null;
      socket?.close();
      socket = null;
      notifyStatus(false);
    }
  };
}

export function sendRealtime(packet: Packet): boolean {
  if (!connected || socket?.readyState !== WebSocket.OPEN) return false;
  socket.send(JSON.stringify(packet));
  return true;
}

export function isRealtimeConnected() {
  return connected;
}
