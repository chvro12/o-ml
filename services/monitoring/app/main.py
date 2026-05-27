from __future__ import annotations

from dataclasses import dataclass, field
from collections import deque
from threading import Lock
from typing import Any, Optional

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field


class MetricEvent(BaseModel):
    service: str = Field(min_length=1)
    latency_seconds: float = Field(ge=0)
    status_code: int = Field(ge=0, le=599)
    prediction: Optional[dict[str, Any]] = None


@dataclass
class MetricsStore:
    requests: int = 0
    errors: int = 0
    latency_total: float = 0.0
    latency_max: float = 0.0
    predictions: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=100))
    lock: Lock = field(default_factory=Lock)

    def record(self, event: MetricEvent) -> None:
        with self.lock:
            self.requests += 1
            if event.status_code >= 400 or event.status_code == 0:
                self.errors += 1
            self.latency_total += event.latency_seconds
            self.latency_max = max(self.latency_max, event.latency_seconds)
            if event.prediction is not None:
                self.predictions.append(event.prediction)

    def prometheus(self) -> str:
        with self.lock:
            average = self.latency_total / self.requests if self.requests else 0.0
            lines = [
                "# HELP inference_requests_total Total inference requests observed.",
                "# TYPE inference_requests_total counter",
                f"inference_requests_total {self.requests}",
                "# HELP inference_errors_total Requests returning an error.",
                "# TYPE inference_errors_total counter",
                f"inference_errors_total {self.errors}",
                "# HELP inference_latency_seconds_avg Average end-to-end latency.",
                "# TYPE inference_latency_seconds_avg gauge",
                f"inference_latency_seconds_avg {average:.6f}",
                "# HELP inference_latency_seconds_max Maximum end-to-end latency.",
                "# TYPE inference_latency_seconds_max gauge",
                f"inference_latency_seconds_max {self.latency_max:.6f}",
            ]
            return "\n".join(lines) + "\n"

    def recent_predictions(self) -> list[dict[str, Any]]:
        with self.lock:
            return list(self.predictions)


store = MetricsStore()
app = FastAPI(title="Text moderation monitoring service", version="1.0.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/events", status_code=202)
def record_event(event: MetricEvent) -> dict[str, str]:
    store.record(event)
    return {"status": "recorded"}


@app.get("/metrics", response_class=PlainTextResponse)
def metrics() -> str:
    return store.prometheus()


@app.get("/predictions")
def predictions() -> dict[str, list[dict[str, Any]]]:
    return {"predictions": store.recent_predictions()}
