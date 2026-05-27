from fastapi.testclient import TestClient

from services.monitoring.app.main import MetricEvent, MetricsStore, app


def test_metrics_store_exposes_counts_and_latencies():
    store = MetricsStore()
    store.record(
        MetricEvent(
            service="inference",
            latency_seconds=0.1,
            status_code=200,
            prediction={"label": "toxic", "score": 0.7, "categories": ["insult"]},
        )
    )
    store.record(MetricEvent(service="inference", latency_seconds=0.3, status_code=500))
    metrics = store.prometheus()
    assert "inference_requests_total 2" in metrics
    assert "inference_errors_total 1" in metrics
    assert "inference_latency_seconds_avg 0.200000" in metrics
    assert "inference_latency_seconds_max 0.300000" in metrics
    assert store.recent_predictions() == [
        {"label": "toxic", "score": 0.7, "categories": ["insult"]}
    ]


def test_monitoring_api_accepts_event_and_serves_metrics():
    client = TestClient(app)
    response = client.post(
        "/events",
        json={
            "service": "inference",
            "latency_seconds": 0.01,
            "status_code": 200,
            "prediction": {"label": "non-toxic", "score": 0.2, "categories": []},
        },
    )
    assert response.status_code == 202
    assert "inference_requests_total" in client.get("/metrics").text
    assert client.get("/predictions").json()["predictions"][-1]["label"] == "non-toxic"
    assert client.get("/health").json() == {"status": "ok"}
