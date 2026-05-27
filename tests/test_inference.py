import numpy as np
from fastapi.testclient import TestClient

from services.inference.app import main


class FakeVectorizer:
    def transform(self, _texts):
        return np.array([[1.0]])


class FakeBinaryModel:
    def __init__(self, score: float):
        self.score = score

    def predict_proba(self, _matrix):
        return np.array([[1.0 - self.score, self.score]])


class FakeCategoryModel:
    def __init__(self, scores):
        self.scores = scores

    def predict_proba(self, _matrix):
        return np.array([self.scores])


def models(score, category_scores=None):
    return {
        "vectorizer": FakeVectorizer(),
        "binary_model": FakeBinaryModel(score),
        "category_model": FakeCategoryModel(category_scores or [0.1, 0.1]),
        "categories": ["toxic", "insult"],
    }


def test_toxic_text_routes_to_fine_categories(monkeypatch):
    monkeypatch.setattr(main, "get_models", lambda: models(0.8, [0.7, 0.8]))
    result = main.run_prediction("toxic sentence")
    assert result["label"] == "toxic"
    assert result["categories"] == ["toxic", "insult"]


def test_non_toxic_text_skips_fine_categories(monkeypatch):
    monkeypatch.setattr(main, "get_models", lambda: models(0.1))
    result = main.run_prediction("normal sentence")
    assert result == {"label": "non-toxic", "score": 0.1, "categories": []}


def test_toxic_text_uses_best_category_if_threshold_not_reached(monkeypatch):
    monkeypatch.setattr(main, "get_models", lambda: models(0.8, [0.1, 0.2]))
    result = main.run_prediction("borderline categories")
    assert result["categories"] == ["insult"]


def test_infer_endpoint_rejects_missing_text():
    assert TestClient(main.app).post("/infer", json={}).status_code == 422


def test_infer_endpoint_returns_prediction(monkeypatch, text_payload):
    monkeypatch.setattr(main, "get_models", lambda: models(0.8, [0.7, 0.1]))
    response = TestClient(main.app).post("/infer", json=text_payload)
    assert response.status_code == 200
    assert response.json()["label"] == "toxic"
