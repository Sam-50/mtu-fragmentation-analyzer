"""Basic API tests with mocked probes."""

from __future__ import annotations

from app.models import ProbeResult
from app.services import analysis as analysis_service


class FakeExecutor:
    def __init__(self) -> None:
        self._responses = {
            1200: True,
            1216: True,
            1232: False,
        }

    def run_probe(self, target: str, payload_size: int, timeout: float, sequence_no: int) -> ProbeResult:
        success = self._responses.get(payload_size, False)
        return ProbeResult(
            payload_size=payload_size,
            mtu_estimate=payload_size + 28,
            success=success,
            rtt_ms=18.5 if success else None,
            error_type=None if success else "fragmentation-needed",
            detail="mocked probe",
            method="fake",
            sequence_no=sequence_no,
        )


def test_health_endpoint(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_with_mocked_executor(client, monkeypatch) -> None:
    def fake_run_analysis(request, executor=None):
        return analysis_service.run_analysis(request, executor=FakeExecutor())

    monkeypatch.setattr("app.routes.api.run_analysis", fake_run_analysis)
    response = client.post(
        "/api/analyze",
        json={
            "target": "8.8.8.8",
            "payload_start": 1200,
            "payload_stop": 1232,
            "payload_step": 16,
            "probe_count": 1,
            "timeout": 1.0,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["inferred_path_mtu"] == 1244
    assert payload["recommended_mtu"] == 1236
    assert payload["recommended_mss"] == 1196
    assert len(payload["probes"]) == 3


def test_export_endpoints_with_mocked_executor(client, monkeypatch) -> None:
    def fake_run_analysis(request, executor=None):
        return analysis_service.run_analysis(request, executor=FakeExecutor())

    monkeypatch.setattr("app.routes.api.run_analysis", fake_run_analysis)
    response = client.post(
        "/api/analyze",
        json={
            "target": "8.8.8.8",
            "payload_start": 1200,
            "payload_stop": 1232,
            "payload_step": 16,
            "probe_count": 1,
            "timeout": 1.0,
        },
    )
    run_id = response.json()["run_id"]

    json_export = client.get(f"/api/runs/{run_id}/export/json")
    csv_export = client.get(f"/api/runs/{run_id}/export/csv")
    summary_export = client.get(f"/api/runs/{run_id}/summary")

    assert json_export.status_code == 200
    assert csv_export.status_code == 200
    assert "payload_size" in csv_export.text
    assert summary_export.status_code == 200
