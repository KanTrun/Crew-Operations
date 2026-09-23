"""Sensors — cảm biến tín hiệu xác suất (Jev) và tất định (regex).

Jev là cảm biến xác suất đứng *trước* máy trạng thái tất định, không bao giờ
đứng *trong* nó (ADR-002). Xem `port.py` cho hợp đồng cổng.
"""

from ca_agents.sensors.fb_questions import (
    FB_QUESTIONS,
    INJECTION_QUESTIONS,
    anonymize_state,
)
from ca_agents.sensors.jev_sensor import JevSensor
from ca_agents.sensors.msg_questions import MSG_QUESTIONS
from ca_agents.sensors.port import SensorResult, Signal, SignalSensor
from ca_agents.sensors.regex_sensor import RegexSensor
from ca_agents.sensors.sensor_chain import CombinedResult, SensorChain
from ca_agents.sensors.voc_questions import VOC_QUESTIONS

__all__ = [
    "CombinedResult",
    "FB_QUESTIONS",
    "INJECTION_QUESTIONS",
    "JevSensor",
    "MSG_QUESTIONS",
    "RegexSensor",
    "SensorChain",
    "SensorResult",
    "Signal",
    "SignalSensor",
    "VOC_QUESTIONS",
    "anonymize_state",
]