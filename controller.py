"""Pure local gesture-controller state and safety boundaries."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import math
import secrets
import time
from typing import Any


COMMANDS = {"next", "previous", "select", "scroll-up", "scroll-down", "search", "pause"}


@dataclass
class CalibrationProfile:
    handedness: str = "right"
    orientation: str = "upright"
    confidence_threshold: float = 0.78
    dwell_ms: int = 450
    debounce_ms: int = 900
    lighting_confidence: float = 1.0

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def from_json(cls, value: str) -> "CalibrationProfile":
        data = json.loads(value)
        if not isinstance(data, dict):
            raise ValueError("calibration must be an object")
        profile = cls(**data)
        if profile.handedness not in {"left", "right"} or profile.orientation not in {"upright", "inverted"}:
            raise ValueError("unsupported calibration")
        if not 0.5 <= profile.confidence_threshold <= 1 or not 50 <= profile.dwell_ms <= 3000:
            raise ValueError("unsafe calibration thresholds")
        return profile


@dataclass
class GestureObservation:
    gesture: str
    confidence: float
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class SessionMetric:
    observations: int = 0
    commands: int = 0
    false_activations: int = 0
    total_latency_ms: float = 0
    started_at: float = field(default_factory=time.time)

    def snapshot(self) -> dict[str, Any]:
        elapsed = max(time.time() - self.started_at, 0.001)
        return {**asdict(self), "average_latency_ms": round(self.total_latency_ms / max(self.commands, 1), 1), "fps": round(self.observations / elapsed, 1)}


class GestureRecognizer:
    """Recognize five intentionally small gestures from normalized landmarks.

    Landmark order follows the common 21-point hand layout. Coordinates are
    normalized to the camera frame and are never persisted.
    """

    def __init__(self, profile: CalibrationProfile | None = None) -> None:
        self.profile = profile or CalibrationProfile()

    def recognize(self, landmarks: list[tuple[float, float]], confidence: float) -> GestureObservation | None:
        if len(landmarks) != 21 or confidence < self.profile.confidence_threshold:
            return None
        wrist = landmarks[0]
        tips = [landmarks[i] for i in (4, 8, 12, 16, 20)]
        joints = [landmarks[i] for i in (3, 6, 10, 14, 18)]
        extended = [self._distance(wrist, tip) > self._distance(wrist, joint) * 1.15 for tip, joint in zip(tips, joints)]
        if all(extended[1:]) and not extended[0]:
            return GestureObservation("point", confidence)
        if all(extended):
            return GestureObservation("next", confidence)
        if not any(extended):
            return GestureObservation("pause", confidence)
        if extended[0] and not any(extended[1:]):
            return GestureObservation("previous", confidence)
        if extended[0] and extended[1] and not any(extended[2:]):
            return GestureObservation("search", confidence)
        return None

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])


class Controller:
    def __init__(self, profile: CalibrationProfile | None = None, clock=time.monotonic) -> None:
        self.profile = profile or CalibrationProfile()
        self.clock = clock
        self.paused = True
        self._candidate: tuple[str, float] | None = None
        self._last_command: tuple[str, float] | None = None
        self._command_id = 0
        self._command: dict[str, Any] | None = None
        self.metric = SessionMetric()
        self.events: list[dict[str, Any]] = []

    def resume(self) -> None:
        self.paused = False
        self._log("system", "resumed", 1)

    def pause(self) -> None:
        self.paused = True
        self._candidate = None
        self._log("system", "paused", 1)

    def observe(self, observation: GestureObservation) -> str | None:
        self.metric.observations += 1
        if self.paused or observation.confidence < self.profile.confidence_threshold:
            return None
        now = self.clock()
        if self._candidate is None or self._candidate[0] != observation.gesture:
            self._candidate = (observation.gesture, now)
            return None
        if (now - self._candidate[1]) * 1000 < self.profile.dwell_ms:
            return None
        if self._last_command and self._last_command[0] == observation.gesture and (now - self._last_command[1]) * 1000 < self.profile.debounce_ms:
            return None
        command = observation.gesture
        if command not in COMMANDS:
            return None
        self._last_command = (command, now)
        self._candidate = None
        self.execute(command, "gesture", observation.confidence)
        self.metric.total_latency_ms += max((now - observation.timestamp) * 1000, 0)
        return command

    def execute(self, command: str, kind: str = "manual", confidence: float = 1) -> None:
        if command not in COMMANDS:
            raise ValueError("unsupported command")
        self._command_id += 1
        self._command = {"id": self._command_id, "name": command}
        self.metric.commands += 1
        self._log(kind, command, confidence)
        if command == "pause":
            self.paused = True
            self._candidate = None

    def _log(self, kind: str, value: str, confidence: float) -> None:
        self.events.append({"time": time.strftime("%H:%M:%S"), "kind": kind, "value": value, "confidence": round(confidence, 2)})
        del self.events[:-100]

    def snapshot(self) -> dict[str, Any]:
        return {"paused": self.paused, "calibration": asdict(self.profile), "metrics": self.metric.snapshot(), "events": self.events, "command": self._command}


def new_channel_token() -> str:
    return secrets.token_urlsafe(24)
