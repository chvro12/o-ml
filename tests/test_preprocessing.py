import httpx
from fastapi.testclient import TestClient

from services.preprocessing.app import main
from services.preprocessing.app.main import app, prepare_text


client = TestClient(app)


def test_prepare_text_normalizes_whitespace():
    assert prepare_text({"text": " hello\n\tworld "}) == "hello world"


def test_prepare_endpoint_rejects_missing_text():
    response = client.post("/prepare", json={})
    assert response.status_code == 422


def test_predict_forwards_prepared_text_and_records_prediction(monkeypatch, text_payload):
    calls = []

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"label": "toxic", "score": 0.9, "categories": ["insult"]}

    def post(url, json, timeout):
        calls.append((url, json))
        return Response()

    monkeypatch.setattr(main.httpx, "post", post)
    response = client.post("/predict", json=text_payload)
    assert response.status_code == 200
    assert response.json()["label"] == "toxic"
    assert calls[0][0].endswith("/infer")
    assert calls[1][0].endswith("/events")
    assert calls[1][1]["prediction"]["categories"] == ["insult"]


def test_predict_reports_unavailable_inference(monkeypatch, text_payload):
    monkeypatch.setattr(
        main.httpx,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(httpx.ConnectError("absent")),
    )
    response = client.post("/predict", json=text_payload)
    assert response.status_code == 502


def test_publish_metric_does_not_break_prediction(monkeypatch):
    monkeypatch.setattr(
        main.httpx,
        "post",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(httpx.ConnectError("absent")),
    )
    main.publish_metric(0.01, 200, {"label": "non-toxic"})


def test_health_endpoint():
    assert client.get("/health").json() == {"status": "ok"}


def test_frontend_is_served():
    response = client.get("/")
    assert response.status_code == 200
    assert "Tester le modele de toxicite" in response.text
