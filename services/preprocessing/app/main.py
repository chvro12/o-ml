from __future__ import annotations

import os
import re
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException


INFERENCE_URL = os.getenv("INFERENCE_URL", "http://model:8000")
MONITORING_URL = os.getenv("MONITORING_URL", "http://monitoring:8002")
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "20000"))

app = FastAPI(title="Text preprocessing service", version="1.0.0")


def prepare_text(raw: dict[str, Any]) -> str:
    value = raw.get("text")
    if not isinstance(value, str):
        raise ValueError("Champ text requis")
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        raise ValueError("Texte vide")
    return text[:MAX_TEXT_LENGTH]


def publish_metric(
    latency_seconds: float, status_code: int, prediction: dict[str, Any] | None = None
) -> None:
    event = {
        "service": "preprocessing",
        "latency_seconds": latency_seconds,
        "status_code": status_code,
        "prediction": prediction,
    }
    try:
        httpx.post(f"{MONITORING_URL}/events", json=event, timeout=0.5)
    except httpx.HTTPError:
        pass


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/prepare")
def prepare(raw: dict[str, Any]) -> dict[str, str]:
    try:
        return {"text": prepare_text(raw)}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/predict")
def predict(raw: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    try:
        text = prepare_text(raw)
        response = httpx.post(
            f"{INFERENCE_URL}/infer", json={"text": text}, timeout=3.0
        )
        response.raise_for_status()
        result = response.json()
    except ValueError as exc:
        publish_metric(time.monotonic() - started, 422)
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        publish_metric(time.monotonic() - started, 502)
        raise HTTPException(status_code=502, detail="Inference indisponible") from exc
    publish_metric(time.monotonic() - started, 200, result)
    return result
