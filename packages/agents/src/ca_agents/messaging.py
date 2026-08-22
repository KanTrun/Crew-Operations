"""Messaging ports — Telegram / Zalo stub / console. Env switch, not business logic."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SendResult:
    ok: bool
    backend: str
    detail: str


class MessagePort:
    name = "base"

    def send(self, to: str, text: str) -> SendResult:
        raise NotImplementedError


class ConsolePort(MessagePort):
    name = "console"

    def send(self, to: str, text: str) -> SendResult:
        print(f"[console->{to}] {text}")
        return SendResult(ok=True, backend="console", detail="printed")


class TelegramPort(MessagePort):
    name = "telegram"

    def send(self, to: str, text: str) -> SendResult:
        _ = (to, text)
        return SendResult(ok=False, backend="telegram", detail="stub_no_network_not_sent")


class ZaloPort(MessagePort):
    name = "zalo"

    def send(self, to: str, text: str) -> SendResult:
        return SendResult(
            ok=False,
            backend="zalo",
            detail="chua_kiem_chung_phi_R8",
        )


def get_port(name: str | None) -> MessagePort:
    key = (name or "console").lower()
    if key == "telegram":
        return TelegramPort()
    if key == "zalo":
        return ZaloPort()
    return ConsolePort()
