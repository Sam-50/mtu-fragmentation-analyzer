"""Tests for MTU/MSS helper and recommendation logic."""

from __future__ import annotations

from app.services.pmtud import mtu_to_mss, payload_to_mtu
from app.services.recommendations import build_recommendations


def test_payload_to_mtu_uses_ipv4_overhead() -> None:
    assert payload_to_mtu(1472) == 1500


def test_mtu_to_mss_for_common_ethernet_path() -> None:
    assert mtu_to_mss(1500) == 1460


def test_recommendation_engine_returns_safe_mtu_and_mss() -> None:
    probes = [
        {"payload_size": 1400, "success": True, "error_type": None},
        {"payload_size": 1472, "success": False, "error_type": "fragmentation-needed"},
    ]
    measurement = {"loss_rate": 0.5}
    findings = []

    recommended_mtu, recommended_mss, recommendations = build_recommendations(
        inferred_path_mtu=1428,
        probes=probes,
        measurement=measurement,
        findings=findings,
    )

    assert recommended_mtu == 1420
    assert recommended_mss == 1380
    assert any(item["title"] == "Likely safe MTU" for item in recommendations)
    assert any(item["title"] == "Suggested TCP MSS clamp" for item in recommendations)
