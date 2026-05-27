from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
from fastapi import FastAPI, HTTPException


MODEL_PATH = Path(os.getenv("MODEL_PATH", "/models/toxicity_bundle.joblib"))
TOXIC_THRESHOLD = float(os.getenv("TOXIC_THRESHOLD", "0.35"))
CATEGORY_THRESHOLD = float(os.getenv("CATEGORY_THRESHOLD", "0.35"))

app = FastAPI(title="Toxicity inference service", version="1.0.0")


@lru_cache(maxsize=1)
def get_models() -> dict[str, Any]:
    if not MODEL_PATH.exists():
        raise RuntimeError(f"Artefact modele absent: {MODEL_PATH}")
    return joblib.load(MODEL_PATH)


def run_prediction(text: str) -> dict[str, Any]:
    models = get_models()
    matrix = models["vectorizer"].transform([text])
    toxic_score = float(models["binary_model"].predict_proba(matrix)[0][1])
    categories: list[str] = []
    if toxic_score >= TOXIC_THRESHOLD:
        category_scores = models["category_model"].predict_proba(matrix)[0]
        categories = [
            name
            for name, score in zip(models["categories"], category_scores)
            if float(score) >= CATEGORY_THRESHOLD
        ]
        if not categories:
            categories = [models["categories"][int(category_scores.argmax())]]
    return {
        "label": "toxic" if toxic_score >= TOXIC_THRESHOLD else "non-toxic",
        "score": round(toxic_score, 6),
        "categories": categories,
    }


@app.get("/health")
def health() -> dict[str, str]:
    get_models()
    return {"status": "ok"}


@app.post("/infer")
def infer(payload: dict[str, Any]) -> dict[str, Any]:
    text = payload.get("text")
    if not isinstance(text, str) or not text.strip():
        raise HTTPException(status_code=422, detail="Texte absent")
    try:
        return run_prediction(text)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Inference impossible") from exc
